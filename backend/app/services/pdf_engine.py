"""
Application PDF Generation Engine (Phase 6).

Turns customer-confirmed application form data into professional banking
application PDFs, for every one of the 59 prototype services, from a single
reusable template engine driven by the existing form configurations
(form_engine.get_service_fields) and document checklists (document_engine).

Engine choice:
    ReportLab (5.1.0) was evaluated first. It renders PDFs, but it has no
    OpenType/complex-text shaping: Devanagari and Telugu conjuncts and
    pre-base matras render in logical (visually wrong) order - e.g. "विभाग"
    shows the i-matra hook to the right of व instead of the left. The spec
    requires Telugu/Hindi to render correctly, so the engine is built on
    PyMuPDF (MuPDF 1.28) instead: its Story/HTML layout engine performs
    HarfBuzz complex-script shaping (reph over ण, Telugu vattu subscripts
    and pre-base i-matra were visually verified in this repo).

Design guarantees:
    - PDFs are built from customer-confirmed data only: gating is computed
      upstream (form_service.completion_status -> pdf_ready) and enforced
      again in the generation service.
    - Values are printed exactly as confirmed by the customer (identifiers
      are already masked by the OCR layer).
    - Prototype identification: every page carries the prototype banner and
      the compliance disclaimers; no official bank logos, seals or
      signatures; original visual identity only.
    - Generated files live in backend/generated_pdfs/{session_key}/ and are
      purged when their session is deleted or expires (retention below).
    - Personal data is never written to logs.

Multilingual: en / te / hi with Noto fonts (SIL OFL) in backend/fonts/.
"""

import re as _re
import shutil
import time as _time
import html as _html
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pymupdf

from app.services.form_engine import (
    FORM_FIELD_TYPES,
    get_service_fields,
)
from app.services.form_service import (
    FormApplicationError,
    _normalize_state,
    completion_status,
)
from app.services.document_engine import (
    get_application_checklist,
    get_document_by_id,
)

# ---------------------------------------------------------------------------
# Paths, page geometry, retention
# ---------------------------------------------------------------------------

BACKEND_ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = BACKEND_ROOT / "fonts"
_FONT_CACHE_DIR = FONT_DIR / "derived"


def _font_archive_path() -> str:
    """
    Font directory used for embedding: the originals, or a cached
    "de-ligatured" copy where the Latin 'liga' feature was disabled.

    Why: HarfBuzz (used for Indic shaping) also applies Latin ligatures, so
    "affiliated" renders as a?fb03liated internally; extraction then yields
    legacy ligature codepoints, breaking text search of plain 'fi'/'ffi'
    words. Renaming the 'liga' tag disables that feature while leaving all
    Indic shaping features (akhn/pres/half/...) untouched.
    """
    wanted = [
        "NotoSans-Regular.ttf", "NotoSans-Bold.ttf",
        "NotoSansDevanagari-Regular.ttf", "NotoSansDevanagari-Bold.ttf",
        "NotoSansTelugu-Regular.ttf", "NotoSansTelugu-Bold.ttf",
    ]
    origin = str(FONT_DIR)
    if not FONT_DIR.is_dir():
        raise PdfGenerationError(500, "Prototype fonts are missing (backend/fonts).")
    if all((FONT_DIR / f).is_file() for f in wanted):
        # build the de-ligatured cache once
        try:
            from fontTools.ttLib import TTFont
        except ImportError:
            return str(FONT_DIR)
        try:
            skip = False
            if all((_FONT_CACHE_DIR / f).is_file() for f in wanted):
                return str(_FONT_CACHE_DIR)
            _FONT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            for name in wanted:
                font = TTFont(str(FONT_DIR / name))
                gsub = font.get("GSUB")
                if gsub and gsub.table.FeatureList:
                    for rec in gsub.table.FeatureList.FeatureRecord:
                        if rec.FeatureTag in ("liga", "hlig", "dlig"):
                            # unknown tags are ignored by the shaper
                            rec.FeatureTag = "ligaX"
                font.save(str(_FONT_CACHE_DIR / name))
            return str(_FONT_CACHE_DIR)
        except Exception:
            return str(FONT_DIR)  # degraded search is better than no PDF
    return str(FONT_DIR)
PDF_ROOT = BACKEND_ROOT / "generated_pdfs"
# Same retention window as the scan temp files.
PDF_RETENTION_HOURS = 6

_A4 = pymupdf.paper_rect("a4")
PAGE_W, PAGE_H = _A4.width, _A4.height          # 595 x 842 pt
BAND_H = 46.0                                    # header band height
TOP = BAND_H + 16.0                              # body area top
BOTTOM = PAGE_H - 50.0                           # body area bottom
SIDE = 48.0                                      # side margins
BODY_W = PAGE_W - 2 * SIDE
_ROWS_PER_CHUNK = 6

_GREEN = (0.05, 0.48, 0.22)      # customer-confirmed
_AMBER = (0.72, 0.47, 0.0)       # customer-edited
_PRIMARY = (0.075, 0.29, 0.40)   # slate-teal band (original identity)
_ACCENT = (0.79, 0.40, 0.06)     # warm accent stripe
_GRAY = (0.42, 0.47, 0.51)


class PdfGenerationError(Exception):
    """Domain error with an HTTP-ready status code."""

    def __init__(self, status_code: int, detail: str, reason: Optional[str] = None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.reason = reason


PROTOTYPE_BANNER = "EDUCATIONAL PROTOTYPE — NOT AN OFFICIAL BANK DOCUMENT"

PDF_READY_BLOCK_MESSAGES = {
    "review_required": (
        "PDF generation is blocked: low-confidence or conflicting fields still "
        "need customer review in the application form."
    ),
    "unconfirmed_fields": (
        "PDF generation is blocked: every populated field must be reviewed and "
        "confirmed (or edited) by the customer first."
    ),
    "no_confirmation": (
        "PDF generation is blocked: at least one customer-confirmed field is "
        "required before a PDF can be generated."
    ),
    "unknown": "PDF generation is blocked until the application is confirmed.",
}

# ---------------------------------------------------------------------------
# Localized strings for the PDF chrome
# ---------------------------------------------------------------------------

_LANG_NAME = {"en": "English", "te": "Telugu (తెలుగు)", "hi": "Hindi (हिन्दी)"}

PDF_STRINGS: Dict[str, Dict[str, Any]] = {
    "en": {
        "doc_title": "Banking Service Application Form",
        "subtitle": "Multilingual AI-Powered ATM Banking Assistant — Educational Prototype",
        "banner_subtitle": "Not affiliated with or issued by HDFC Bank",
        "disclaimers": [
            "This document is not affiliated with or issued by HDFC Bank.",
            "It is not valid for actual banking transactions.",
            "It is not valid for KYC verification.",
            "No application has been submitted to a bank.",
        ],
        "sec_meta": "Application Details",
        "lbl_ref": "Application Reference No.",
        "lbl_form": "Prototype Form No.",
        "lbl_service": "Banking Service",
        "lbl_generated": "Generated On (UTC)",
        "lbl_language": "Document Language",
        "lbl_conf_status": "Customer Confirmation Status",
        "conf_status_value": "Recorded — customer-reviewed data (details below)",
        "conf_status_none": "Not recorded",
        "sec_applicant": "Applicant Information",
        "sec_contact": "Contact Information",
        "sec_address": "Address Information",
        "sec_account": "Account Information",
        "sec_service": "Service-Specific Information",
        "sec_documents": "Uploaded Document Checklist",
        "sec_declarations": "Customer Declarations",
        "sec_confirmation": "Customer Confirmation",
        "th_field": "Field",
        "th_value": "Details as Confirmed",
        "th_status": "Customer Review",
        "st_confirmed": "Customer-confirmed",
        "st_edited": "Customer-edited",
        "st_missing": "Not provided",
        "not_provided_marker": "— not provided —",
        "docs_caption": "Document",
        "docs_note": (
            "Listed from the service's document-requirement checklist; statuses "
            "reflect what was scanned in this session only."
        ),
        "doc_status": {
            "pending": "Pending",
            "uploaded": "Uploaded",
            "readable": "Readable",
            "needs_rescan": "Needs rescan",
            "optional": "Optional",
            "not_applicable": "Not applicable",
        },
        "doc_mandatory": "(required)",
        "doc_conditional": "(conditional)",
        "decl_intro": "By proceeding below, the customer declares that:",
        "declarations": [
            "The information provided in this form is true and correct to the best of the customer's knowledge.",
            "Every field marked \u201cCustomer-confirmed\u201d or \u201cCustomer-edited\u201d was reviewed and approved by the customer in the prototype application session.",
            "The customer understands this is an educational prototype document and that no application has been, or can be, submitted to any bank.",
        ],
        "conf_p1": (
            "The data in this PDF was generated exclusively from values that the "
            "customer reviewed and confirmed (or personally edited) during the "
            "prototype session."
        ),
        "conf_p2": "Fields marked \u201cNot provided\u201d were left blank in the prototype form.",
        "conf_counts": "{filled} of {total} form fields contain customer-reviewed information; {missing} field(s) were not provided.",
        "lbl_signature": "Customer signature / mark:",
        "lbl_sign_date": "Date:",
        "retention": (
            "Generated PDFs are stored only in the prototype's temporary session "
            "storage and are deleted automatically when the session expires or "
            "is cleared."
        ),
    },
    "te": {
        "doc_title": "బ్యాంకింగ్ సేవా దరఖాస్తు ఫారం",
        "subtitle": "బహుభాషా AI ATM బ్యాంకింగ్ సహాయకుడు — విద్యాపరమైన ప్రోటోటైప్",
        "banner_subtitle": "HDFC బ్యాంక్‌తో సంబంధం లేదు / HDFC బ్యాంక్ వారిచే జారీ చేయబడలేదు",
        "disclaimers": [
            "ఈ పత్రం HDFC బ్యాంక్‌తో సంబంధం కలిగి లేదు, వారిచే జారీ చేయబడలేదు.",
            "ఇది వాస్తవ బ్యాంకింగ్ లావాదేవీలకు చెల్లదు.",
            "ఇది KYC ధృవీకరణకు చెల్లదు.",
            "ఏ బ్యాంకులోనూ దరఖాస్తు దాఖలు చేయబడలేదు.",
        ],
        "sec_meta": "దరఖాస్తు వివరాలు",
        "lbl_ref": "దరఖాస్తు సూచిక సంఖ్య",
        "lbl_form": "ప్రోటోటైప్ ఫారం నంబర్",
        "lbl_service": "బ్యాంకింగ్ సేవ",
        "lbl_generated": "తయారయిన తేదీ (UTC)",
        "lbl_language": "పత్ర భాష",
        "lbl_conf_status": "వినియోగదారు ధృవీకరణ స్థితి",
        "conf_status_value": "నమోదైనది — వినియోగదారు సమీక్షించిన సమాచారం (వివరాలు క్రింద)",
        "conf_status_none": "నమోదు కాలేదు",
        "sec_applicant": "దరఖాస్తుదారు సమాచారం",
        "sec_contact": "సంప్రదింపు సమాచారం",
        "sec_address": "చిరునామా సమాచారం",
        "sec_account": "ఖాతా సమాచారం",
        "sec_service": "సేవా ఆధారిత సమాచారం",
        "sec_documents": "అప్‌లోడ్ చేసిన పత్రాల జాబితా",
        "sec_declarations": "వినియోగదారు ప్రకటనలు",
        "sec_confirmation": "వినియోగదారు ధృవీకరణ",
        "th_field": "ఫీల్డ్",
        "th_value": "ధృవీకరించిన వివరాలు",
        "th_status": "వినియోగదారు సమీక్ష",
        "st_confirmed": "ధృవీకరించబడింది",
        "st_edited": "సవరించబడింది",
        "st_missing": "అందించలేదు",
        "not_provided_marker": "— అందించలేదు —",
        "docs_caption": "పత్రం",
        "docs_note": "సేవ పత్ర-అవసరాల జాబితా నుండి; స్థితులు ఈ సెషన్‌లో స్కాన్ చేసిన పత్రాలను మాత్రమే ప్రతిబింబిస్తాయి.",
        "doc_status": {
            "pending": "పెండింగ్‌లో",
            "uploaded": "అప్‌లోడ్ అయింది",
            "readable": "చదవగలిగింది",
            "needs_rescan": "మళ్లీ స్కాన్ చేయాలి",
            "optional": "ఐచ్ఛికం",
            "not_applicable": "వర్తించదు",
        },
        "doc_mandatory": "(తప్పనిసరి)",
        "doc_conditional": "(షరతులతో)",
        "decl_intro": "క్రింద ఉంచుకునే వినియోగదారు ఈ ప్రకటనలు చేస్తున్నారు:",
        "declarations": [
            "ఈ ఫారంలో ఇచ్చిన సమాచారం నా పరిజ్ఞానానికి వచ్చినంత వరకు సరైనదేనని ధృవీకరిస్తున్నాను.",
            "\u201cధృవీకరించబడింది\u201d లేదా \u201cసవరించబడింది\u201d అని గుర్తించబడిన అన్ని ఫీల్డ్లను నేను సమీక్షించి ఆమోదించాను.",
            "ఇది విద్యాపరమైన ప్రోటోటైప్ పత్రమని, ఏ బ్యాంకులోనూ దరఖాస్తు దాఖలు చేయబడలేదని, చేయలేనని అర్థం చేసుకున్నాను.",
        ],
        "conf_p1": "ఈ PDFలోని సమాచారం మొత్తం వినియోగదారు సమీక్షించి ధృవీకరించిన (లేదా స్వయంగా అందించిన) విలువల నుండి మాత్రమే తయారయింది.",
        "conf_p2": "\u201cఅందించలేదు\u201d అని గుర్తించబడిన ఫీల్డ్లు ప్రోటోటైప్ ఫారంలో ఖాళీగా ఉంచబడ్డాయి.",
        "conf_counts": "{total} ఫీల్డ్లలో {filled} ధృవీకరించిన సమాచారం కలిగి ఉన్నాయి; {missing} ఫీల్డ్(లు) అందించబడలేదు.",
        "lbl_signature": "వినియోగదారు సంతకం / గుర్తు:",
        "lbl_sign_date": "తేదీ:",
        "retention": "తయారయిన PDFలు ప్రోటోటైప్ తాత్కాలిక సెషన్ నిల్వలో మాత్రమే ఉంచబడతాయి; సెషన్ ముగిసినప్పుడు లేదా తొలగించబడినప్పుడు స్వయంచాలకంగా తొలగించబడతాయి.",
    },
    "hi": {
        "doc_title": "बैंकिंग सेवा आवेदन फॉर्म",
        "subtitle": "बहुभाषी AI ATM बैंकिंग सहायक — शैक्षिक प्रोटोटाइप",
        "banner_subtitle": "HDFC बैंक से संबद्ध नहीं / HDFC बैंक द्वारा जारी नहीं",
        "disclaimers": [
            "यह दस्तावेज़ HDFC बैंक से संबद्ध नहीं है अथवा उनके द्वारा जारी नहीं किया गया है।",
            "यह वास्तविक बैंकिंग लेन-देन के लिए वैध नहीं है।",
            "यह KYC सत्यापन के लिए वैध नहीं है।",
            "किसी बैंक में कोई आवेदन प्रस्तुत नहीं किया गया है।",
        ],
        "sec_meta": "आवेदन विवरण",
        "lbl_ref": "आवेदन संदर्भ संख्या",
        "lbl_form": "प्रोटोटाइप फॉर्म संख्या",
        "lbl_service": "बैंकिंग सेवा",
        "lbl_generated": "निर्माण तिथि (UTC)",
        "lbl_language": "दस्तावेज़ भाषा",
        "lbl_conf_status": "ग्राहक पुष्टि स्थिति",
        "conf_status_value": "रिकॉर्ड की गई — ग्राहक-समीक्षित जानकारी (विवरण नीचे)",
        "conf_status_none": "रिकॉर्ड नहीं हुई",
        "sec_applicant": "आवेदक की जानकारी",
        "sec_contact": "संपर्क जानकारी",
        "sec_address": "पते की जानकारी",
        "sec_account": "खाता जानकारी",
        "sec_service": "सेवा-विशिष्ट जानकारी",
        "sec_documents": "अपलोड किए गए दस्तावेज़ सूची",
        "sec_declarations": "ग्राहक घोषणाएँ",
        "sec_confirmation": "ग्राहक पुष्टि",
        "th_field": "फ़ील्ड",
        "th_value": "पुष्ट की गई जानकारी",
        "th_status": "ग्राहक समीक्षा",
        "st_confirmed": "ग्राहक-पुष्ट",
        "st_edited": "ग्राहक-संपादित",
        "st_missing": "नहीं दिया गया",
        "not_provided_marker": "— नहीं दिया गया —",
        "docs_caption": "दस्तावेज़",
        "docs_note": "सेवा के दस्तावेज़-आवश्यकता सूची से; स्थितियाँ केवल इसी सत्र में स्कैन किए गए दस्तावेज़ों को दर्शाती हैं।",
        "doc_status": {
            "pending": "लंबित",
            "uploaded": "अपलोड किया गया",
            "readable": "पढ़ने योग्य",
            "needs_rescan": "दोबारा स्कैन आवश्यक",
            "optional": "वैकल्पिक",
            "not_applicable": "लागू नहीं",
        },
        "doc_mandatory": "(आवश्यक)",
        "doc_conditional": "(शर्त के अधीन)",
        "decl_intro": "आगे बढ़ते हुए ग्राहक ये घोषणाएँ करता/करती है:",
        "declarations": [
            "इस फॉर्म में दी गई जानकारी अपने ज्ञान के अनुसार सही और सत्य है।",
            "\u201cग्राहक-पुष्ट\u201d अथवा \u201cग्राहक-संपादित\u201d रूप में चिन्हित प्रत्येक फ़ील्ड की समीक्षा करके मैंने उसे स्वीकृति दी है।",
            "मैं समझता/समझती हूँ कि यह शैक्षिक प्रोटोटाइप दस्तावेज़ है और किसी बैंक में कोई आवेदन प्रस्तुत नहीं किया जा सकता।",
        ],
        "conf_p1": "इस PDF की जानकारी केवल उन विलुवों से तैयार की गई है जिन्हें ग्राहक ने समीक्षा कर पुष्ट (अथवा स्वयं संपादित) की थी।",
        "conf_p2": "\u201cनहीं दिया गया\u201d चिन्हित फ़ील्ड प्रोटोटाइप फॉर्म में खाली छोड़े गए थे।",
        "conf_counts": "{total} फ़ील्ड में से {filled} में पुष्ट की गई जानकारी है; {missing} फ़ील्ड प्रदान नहीं किए गए।",
        "lbl_signature": "ग्राहक हस्ताक्षर / चिह्न:",
        "lbl_sign_date": "तिथि:",
        "retention": "तैयार की गई PDF केवल प्रोटोटाइप की अस्थायी सत्र संग्रहण में रखी जाती है और सत्र समाप्त होने या साफ़ होने पर स्वतः हटा दी जाती है।",
    },
}


# ---------------------------------------------------------------------------
# Field -> section grouping (only sections relevant to the service appear)
# ---------------------------------------------------------------------------

_SECTION_FIELDS: Dict[str, List[str]] = {
    "applicant": [
        "applicant_name", "fathers_name", "mothers_name", "date_of_birth",
        "gender", "nationality", "occupation", "employer_name",
        "monthly_income", "annual_income", "source_of_income",
        "pan_number", "aadhaar_number", "passport_number",
    ],
    "contact": ["mobile_number", "email"],
    "address": ["residential_address", "permanent_address", "pincode"],
    "account": ["bank_name", "account_holder_name", "account_number", "ifsc_code"],
    "service": [
        "card_requested", "loan_amount", "loan_purpose", "nominee_name",
        "nominee_relation", "business_name", "gstin", "cheque_number",
        "amount", "denomination_preference", "address_proof_type",
    ],
}
_SECTION_TITLE_KEY = {
    "applicant": "sec_applicant",
    "contact": "sec_contact",
    "address": "sec_address",
    "account": "sec_account",
    "service": "sec_service",
}


# ---------------------------------------------------------------------------
# HTML / CSS helpers
# ---------------------------------------------------------------------------

_CSS = """
@font-face { font-family: deva; src: url(NotoSansDevanagari-Regular.ttf); }
@font-face { font-family: devaB; src: url(NotoSansDevanagari-Bold.ttf); }
@font-face { font-family: telu; src: url(NotoSansTelugu-Regular.ttf); }
@font-face { font-family: teluB; src: url(NotoSansTelugu-Bold.ttf); }
@font-face { font-family: ns;  src: url(NotoSans-Regular.ttf); }
@font-face { font-family: nsB; src: url(NotoSans-Bold.ttf); }
html { font-family: ns, sans-serif; font-size: 8.5pt; line-height: 1.35; color: #1d242b; }
.deva { font-family: deva; }
.devaB { font-family: devaB; font-weight: bold; }
.telu { font-family: telu; }
.teluB { font-family: teluB; font-weight: bold; }
b { font-family: nsB, sans-serif; }
.sec { background-color: #eef3f6; border-left: 3pt solid #134a5c;
       padding: 3.5pt 7pt; margin: 7pt 0 3pt 0; color: #134a5c; font-size: 10pt; }
table { width: 100%; border-collapse: collapse; }
td, th { border: 0.4pt solid #b7c4cd; padding: 3pt 6pt; vertical-align: top; }
th { background-color: #134a5c; color: #ffffff; font-weight: bold; text-align: left; font-size: 8pt; }
.c1 { width: 37%; }  .c2 { width: 45%; }  .c3 { width: 18%; }
.doc1 { width: 78%; } .doc3 { width: 22%; }
.ok { color: #0d7a36; font-size: 7.5pt; }
.ed { color: #a56b00; font-size: 7.5pt; }
.na { color: #76828c; font-size: 7.5pt; font-style: italic; }
.miss { color: #93a1ab; font-style: italic; }
.banner { background-color: #fdf1e6; border: 1pt solid #cc7015; padding: 4pt 7pt; color: #7a3c00; font-size: 8pt; }
.bannertitle { background-color: #7a3c00; color: #ffffff; text-align: center; font-weight: bold;
               padding: 4.5pt 7pt; font-size: 10.5pt; font-family: nsB, sans-serif; }
.title { color: #134a5c; font-size: 15pt; font-family: nsB, sans-serif; }
.subtitle { color: #5b6a74; font-size: 8pt; }
.meta td { font-size: 8pt; }
.decl { margin: 2.5pt 0 0 14pt; }
.small { font-size: 7.2pt; color: #76828c; }
.sig { margin-top: 10pt; }
.footnote { color: #76828c; font-size: 7pt; margin-top: 5pt; }
"""


def _esc(text: Any) -> str:
    return _html.escape("" if text is None else str(text))


_SCRIPT_RUN = _re.compile(r"[\u0900-\u097F\u200C\u200D]+|[\u0C00-\u0C7F\u200C\u200D]+")


def _script_wrap_once(text: str) -> str:
    """Escape HTML text and wrap Devanagari/Telugu runs in font spans.

    The document base font (Noto Sans) covers Latin text; script spans cover
    Indic runs, mirroring the multilingual-mixed rendering verified earlier.
    """
    escaped = _esc(text)
    out: List[str] = []
    pos = 0
    for m in _SCRIPT_RUN.finditer(escaped):
        if m.start() > pos:
            out.append(escaped[pos:m.start()])
        chunk = m.group(0)
        if "\u0900" <= chunk[0] <= "\u097F":
            out.append(f"<span class='deva'>{chunk}</span>")
        else:
            out.append(f"<span class='telu'>{chunk}</span>")
        pos = m.end()
    out.append(escaped[pos:])
    return "".join(out)


def _bold_by_lang(text: Any, lang: str) -> str:
    s = _esc(text)
    if lang == "hi":
        return f"<span class='devaB'>{s}</span>"
    if lang == "te":
        return f"<span class='teluB'>{s}</span>"
    return f"<b>{s}</b>"


def _sec_heading(title: str, lang: str) -> str:
    return f"<p class='sec'>{_bold_by_lang(title, lang)}</p>"


def _status_cell(status: str, lang: str) -> str:
    t = PDF_STRINGS[lang]
    if status == "CUSTOMER_CONFIRMED":
        return f"<span class='ok'>{_script_wrap_once(t['st_confirmed'])}</span>"
    if status == "CUSTOMER_EDITED":
        return f"<span class='ed'>{_script_wrap_once(t['st_edited'])}</span>"
    if status == "MISSING":
        return f"<span class='na'>{_script_wrap_once(t['st_missing'])}</span>"
    return _script_wrap_once(status)


# ---------------------------------------------------------------------------
# Block builders
# ---------------------------------------------------------------------------

def _title_block(language: str) -> str:
    t = PDF_STRINGS[language]
    return (
        f"<p class='title'>{_bold_by_lang(t['doc_title'], language)}</p>"
        f"<p class='subtitle'>{_script_wrap_once(t['subtitle'])}</p>"
    )


def _banner_block(language: str) -> str:
    """Fixed prototype banner + the four compliance disclaimers."""
    t = PDF_STRINGS[language]
    lines = "".join(
        f"<p style='margin:1.5pt 0 0 0;'>{_script_wrap_once(d)}</p>"
        for d in t["disclaimers"]
    )
    return (
        f"<p class='bannertitle'>{_esc(PROTOTYPE_BANNER)}</p>"
        f"<p class='banner'>{_script_wrap_once(t['banner_subtitle'])}{lines}</p>"
    )


def _meta_block(application, completed: Dict[str, Any], language: str) -> str:
    t = PDF_STRINGS[language]
    generated_on = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows = [
        (t["lbl_ref"], application.reference_number),
        (t["lbl_form"], application.form_number),
        (t["lbl_service"], application.service_name),
        (t["lbl_generated"], generated_on),
        (t["lbl_language"], _LANG_NAME.get(language, language)),
        (
            t["lbl_conf_status"],
            t["conf_status_value"] if completed.get("pdf_ready") else t["conf_status_none"],
        ),
    ]
    table = "<table class='meta'>" + "".join(
        f"<tr><td class='c1'>{_script_wrap_once(k)}</td>"
        f"<td class='c2'>{_script_wrap_once(v)}</td><td class='c3'>&nbsp;</td></tr>"
        for k, v in rows
    ) + "</table>"
    return f"{_sec_heading(t['sec_meta'], language)}{table}"


def _field_rows(section_keys: List[str], fields_state: Dict[str, Any], lang: str) -> List[str]:
    t = PDF_STRINGS[lang]
    rows = []
    for fid in section_keys:
        rec = fields_state.get(fid) or {}
        definition = FORM_FIELD_TYPES.get(fid, {})
        label = (
            definition.get("label", {}).get(lang)
            or definition.get("label", {}).get("en")
            or fid
        )
        value = rec.get("value")
        status = rec.get("status", "MISSING")
        if value:
            value_cell = _script_wrap_once(value)
        else:
            value_cell = f"<span class='miss'>{_script_wrap_once(t['not_provided_marker'])}</span>"
        rows.append(
            f"<tr><td>{_script_wrap_once(label)}</td><td>{value_cell}</td>"
            f"<td>{_status_cell(status, lang)}</td></tr>"
        )
    return rows


def _table_header(lang: str) -> str:
    t = PDF_STRINGS[lang]
    return (
        f"<tr><th class='c1'>{t['th_field']}</th><th class='c2'>{t['th_value']}"
        f"</th><th class='c3'>{t['th_status']}</th></tr>"
    )


def _documents_rows(application, language: str) -> List[str]:
    """Reuses the Phase 3 document-requirement checklist engine."""
    t = PDF_STRINGS[language]
    checklist = get_application_checklist(
        service_id=application.service_id,
        service_name=application.service_name,
        form_number=application.form_number,
        application_id=application.reference_number,
    )
    rows = []
    for item in checklist.documents:
        doc_def = get_document_by_id(item.document_id)
        name = (
            (doc_def and (doc_def.name.get(language) or doc_def.name.get("en")))
            or item.name
        )
        suffix = ""
        if item.conditional:
            suffix = " " + t["doc_conditional"]
        elif item.mandatory:
            suffix = " " + t["doc_mandatory"]
        status = item.status.value if hasattr(item.status, "value") else str(item.status)
        rows.append(
            f"<tr><td class='doc1'>{_script_wrap_once(name + suffix)}</td>"
            f"<td class='doc3'>{_script_wrap_once(t['doc_status'].get(status, status))}</td></tr>"
        )
    return rows


def _documents_header(lang: str) -> str:
    t = PDF_STRINGS[lang]
    return f"<tr><th class='doc1'>{t['docs_caption']}</th><th class='doc3'>{t['th_status']}</th></tr>"


def _declarations_block(language: str) -> str:
    t = PDF_STRINGS[language]
    body = f"<p>{_script_wrap_once(t['decl_intro'])}</p>"
    items = "".join(
        f"<p class='decl'>{i + 1}. {_script_wrap_once(d)}</p>"
        for i, d in enumerate(t["declarations"])
    )
    return f"{_sec_heading(t['sec_declarations'], language)}{body}{items}"


def _confirmation_block(application, completed: Dict[str, Any], language: str) -> str:
    t = PDF_STRINGS[language]
    counts = completed.get("counts") or {}
    counts_line = t["conf_counts"].format(
        filled=completed.get("filled_fields", 0),
        total=completed.get("total_fields", 0),
        missing=counts.get("MISSING", 0),
    )
    parts = [
        f"<p>{_script_wrap_once(t['conf_p1'])}</p>",
        f"<p>{_script_wrap_once(counts_line)}</p>",
        f"<p class='small'>{_script_wrap_once(t['conf_p2'])}</p>",
        f"<p class='sig'>{_script_wrap_once(t['lbl_signature'])} ______________________"
        f" &nbsp;&nbsp; {_script_wrap_once(t['lbl_sign_date'])} ____________</p>",
        f"<p class='footnote'>{_script_wrap_once(t['retention'])}</p>",
    ]
    return f"{_sec_heading(t['sec_confirmation'], language)}{''.join(parts)}"


def _build_blocks(application, completed: Dict[str, Any], language: str) -> List[Dict[str, Any]]:
    """
    Flat list of unbreakable layout blocks. Form/document tables are chunked
    into <=_ROWS_PER_CHUNK row groups so rows never split across a page
    boundary. A continuation chunk placed at the top of a page automatically
    re-receives its table header; a section heading travels with its first
    rows so headings are never orphaned at a page bottom.
    """
    t = PDF_STRINGS[language]
    fields_state = _normalize_state(application.application_data)["fields"]
    service_fields = get_service_fields(application.service_id)

    def chunk_table(table_id: str, header: str, rows: List[str], lead: str) -> List[Dict[str, Any]]:
        blocks = []
        for i in range(0, len(rows), _ROWS_PER_CHUNK):
            body = lead if i == 0 else ""
            # only the first chunk carries the header; continuation chunks get
            # it re-injected by _render_document when they land at a page top.
            inner = header if i == 0 else ""
            body += f"<table>{inner}{''.join(rows[i:i + _ROWS_PER_CHUNK])}</table>"
            blocks.append({"html": body, "table_id": table_id, "chunk": i > 0})
        return blocks

    blocks: List[Dict[str, Any]] = [
        {"html": _title_block(language) + _banner_block(language)},
        {"html": _meta_block(application, completed, language)},
    ]

    for section in ("applicant", "contact", "address", "account", "service"):
        keys = [f for f in service_fields if f in _SECTION_FIELDS[section]]
        if not keys:
            continue
        heading = _sec_heading(t[_SECTION_TITLE_KEY[section]], language)
        blocks.extend(
            chunk_table(
                section,
                _table_header(language),
                _field_rows(keys, fields_state, language),
                heading,
            )
        )

    doc_rows = _documents_rows(application, language)
    if doc_rows:
        heading = _sec_heading(t["sec_documents"], language)
        doc_blocks = chunk_table("documents", _documents_header(language), doc_rows, heading)
        doc_blocks[-1]["html"] += f"<p class='footnote'>{_script_wrap_once(t['docs_note'])}</p>"
        blocks.extend(doc_blocks)

    blocks.append({"html": _declarations_block(language)})
    blocks.append({"html": _confirmation_block(application, completed, language)})
    return blocks


# ---------------------------------------------------------------------------
# Layout: measure blocks, paginate, place
# ---------------------------------------------------------------------------

def _measure(block_html: str, archive: pymupdf.Archive) -> float:
    """Height a block needs when laid out at BODY_W (same layout engine)."""
    story = pymupdf.Story(html=block_html, user_css=_CSS, archive=archive, em=8.5)
    _, filled = story.place(pymupdf.Rect(0, 0, BODY_W, PAGE_H))
    return max(filled.height if hasattr(filled, "height") else float(filled[3] - filled[1]), 1.0)


def _inject_header(block: Dict[str, Any], language: str) -> str:
    """Continuation chunk at a page top: repeat its table header row."""
    header = (
        _documents_header(language)
        if block.get("table_id") == "documents"
        else _table_header(language)
    )
    html_body = block["html"]
    marker = f"<table>{header}"
    if marker in html_body:
        return html_body
    return html_body.replace("<table>", f"<table>{header}", 1)


def _render_document(application, completed: Dict[str, Any], language: str) -> Tuple[pymupdf.Document, int]:
    font_path = _font_archive_path()
    archive = pymupdf.Archive(font_path)
    blocks = _build_blocks(application, completed, language)

    doc = pymupdf.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    cursor = TOP
    last_table_id: Optional[str] = None
    n_pages = 1

    for block in blocks:
        html_body = block["html"]
        # continuation chunk at top of a fresh page: re-add the header
        if block.get("chunk") and cursor == TOP and block.get("table_id") == last_table_id:
            html_body = _inject_header(block, language)
        needed = _measure(html_body, archive)

        if cursor + needed > BOTTOM:
            page = doc.new_page(width=PAGE_W, height=PAGE_H)
            cursor = TOP
            n_pages += 1
            if block.get("chunk") and block.get("table_id") == last_table_id:
                html_body = _inject_header(block, language)
                needed = _measure(html_body, archive)

        rect = pymupdf.Rect(SIDE, cursor, SIDE + BODY_W, min(cursor + needed + 2.0, BOTTOM + 4.0))
        spare, scale = page.insert_htmlbox(rect, html_body, css=_CSS, archive=archive)
        if scale is not None and scale < 0.97:
            # content overflowed the measured rect and was shrunk - retry on
            # a fresh page with a full-page rect so text renders unshrunk.
            page = doc.new_page(width=PAGE_W, height=PAGE_H)
            cursor = TOP
            n_pages += 1
            if block.get("chunk") and block.get("table_id") == last_table_id:
                html_body = _inject_header(block, language)
            rect = pymupdf.Rect(SIDE, cursor, SIDE + BODY_W, BOTTOM)
            page.insert_htmlbox(rect, html_body, css=_CSS, archive=archive)

        cursor += needed + 2.0
        last_table_id = block.get("table_id")
    return doc, n_pages


def _draw_furniture(doc: "pymupdf.Document", application, language: str, generated_on: str) -> None:
    """Original prototype identity: header band, accent stripe, footer."""
    banner_ascii = PROTOTYPE_BANNER.replace("\u2014", "-")
    generated_ascii = generated_on.replace("\u2014", "-")
    for pno in range(doc.page_count):
        page = doc[pno]
        # header band
        page.draw_rect(pymupdf.Rect(0, 0, PAGE_W, BAND_H), color=None, fill=_PRIMARY)
        page.draw_rect(pymupdf.Rect(0, BAND_H, PAGE_W, BAND_H + 2.5), color=None, fill=_ACCENT)
        page.insert_text(
            (SIDE, 19),
            "PROTOTYPE BANKING FORM",
            fontname="hebo", fontsize=11.5, color=(1, 1, 1),
        )
        page.insert_text(
            (SIDE, 33),
            f"{application.reference_number}  |  {application.service_name}",
            fontname="helv", fontsize=7.5, color=(0.85, 0.92, 0.97),
        )
        form_label = f"Prototype Form No. {application.form_number}"
        form_w = pymupdf.get_text_length(form_label, fontname="hebo", fontsize=8)
        page.insert_text(
            (PAGE_W - SIDE - form_w, 19),
            form_label, fontname="hebo", fontsize=8, color=(0.95, 0.86, 0.72),
        )
        page_no = f"Page {pno + 1} of {doc.page_count}"
        pn_w = pymupdf.get_text_length(page_no, fontname="helv", fontsize=7)
        page.insert_text(
            (PAGE_W - SIDE - pn_w, 33),
            page_no, fontname="helv", fontsize=7, color=(0.85, 0.92, 0.97),
        )
        # footer
        foot_y = PAGE_H - 24.0
        page.draw_line((SIDE, foot_y - 10), (PAGE_W - SIDE, foot_y - 10), color=(0.75, 0.80, 0.84), width=0.6)
        page.insert_text(
            (SIDE, foot_y),
            banner_ascii, fontname="helv", fontsize=6.3, color=_GRAY,
        )
        gen_w = pymupdf.get_text_length(generated_ascii, fontname="helv", fontsize=6.3)
        page.insert_text(
            (PAGE_W - SIDE - gen_w, foot_y),
            generated_ascii, fontname="helv", fontsize=6.3, color=_GRAY,
        )


# ---------------------------------------------------------------------------
# Service-level API (used by pdf_routes.py)
# ---------------------------------------------------------------------------

def generate_application_pdf(application, language: str = "en") -> Dict[str, Any]:
    """
    Generate (or regenerate) the application PDF from customer-confirmed data.
    Raises PdfGenerationError(409) if the customer-confirmation gate fails.
    """
    language = language if language in PDF_STRINGS else "en"
    completed = completion_status(application)
    if not completed.get("pdf_ready"):
        reason = completed.get("pdf_blocked_reason") or "unknown"
        raise PdfGenerationError(
            409,
            PDF_READY_BLOCK_MESSAGES.get(reason, PDF_READY_BLOCK_MESSAGES["unknown"]),
            reason=reason,
        )

    try:
        generated_on = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        doc, _ = _render_document(application, completed, language)
        _draw_furniture(doc, application, language, generated_on)
        try:
            doc.subset_fonts()  # embedded Noto fonts -> only used glyphs
        except Exception:
            pass  # subsetting is an optimization, never a blocker

        out_dir = PDF_ROOT / application.session_key
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{application.reference_number}.pdf"
        doc.save(str(path), garbage=3, deflate=True)
        file_size = path.stat().st_size
        page_count = doc.page_count
        doc.close()
    except PdfGenerationError:
        raise
    except Exception as exc:  # layout/font failures - no values in the message
        raise PdfGenerationError(500, f"PDF generation failed: {type(exc).__name__}")

    return {
        "application_id": application.reference_number,
        "service_id": application.service_id,
        "service_name": application.service_name,
        "form_number": application.form_number,
        "language": language,
        "status": "ready",
        "generated_at": generated_on,
        "file_name": path.name,
        "file_size": file_size,
        "page_count": page_count,
        "prototype_banner": PROTOTYPE_BANNER,
    }


def pdf_path(application) -> Path:
    return PDF_ROOT / application.session_key / f"{application.reference_number}.pdf"


def pdf_info(application) -> Optional[Dict[str, Any]]:
    """Metadata (never content) of the stored PDF, if one exists."""
    path = pdf_path(application)
    if not path.is_file():
        return None
    try:
        doc = pymupdf.open(str(path))
        pages = doc.page_count
        doc.close()
    except Exception:
        pages = None
    stat = path.stat()
    return {
        "file_name": path.name,
        "file_size": stat.st_size,
        "page_count": pages,
        "generated_at": datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M UTC"),
    }


def read_pdf_bytes(application) -> bytes:
    path = pdf_path(application)
    if not path.is_file():
        raise PdfGenerationError(404, "PDF has not been generated for this application yet.")
    return path.read_bytes()


def delete_pdf(application) -> bool:
    path = pdf_path(application)
    if path.is_file():
        path.unlink()
        return True
    return False


def purge_session(session_id: str) -> int:
    """Remove every generated PDF belonging to a session (all applications)."""
    folder = PDF_ROOT / session_id
    if not folder.is_dir():
        return 0
    count = len(list(folder.glob("*.pdf")))
    shutil.rmtree(folder, ignore_errors=True)
    return count


def purge_expired(max_age_hours: int = PDF_RETENTION_HOURS) -> int:
    """Delete generated PDFs older than the retention window (all sessions)."""
    if not PDF_ROOT.is_dir():
        return 0
    cutoff = _time.time() - max_age_hours * 3600
    removed = 0
    for folder in PDF_ROOT.iterdir():
        if not folder.is_dir():
            continue
        for pdf_file in folder.glob("*.pdf"):
            if pdf_file.stat().st_mtime < cutoff:
                pdf_file.unlink()
                removed += 1
        empty = True
        for item in folder.iterdir():
            if item.is_file():
                # keep the folder while any file is still fresh
                if item.stat().st_mtime < cutoff:
                    item.unlink()
                    removed += 1
                else:
                    empty = False
            elif item.is_dir():
                empty = False
        if empty:
            shutil.rmtree(folder, ignore_errors=True)
    return removed
