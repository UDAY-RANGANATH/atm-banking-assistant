"""
Banking Knowledge Retrieval (Phase 7).

Deterministic knowledge layer built on top of the REAL project data:
- app.services.banking_services  -> 59 services, 4 categories
- app.services.document_engine   -> 39 documents, service document mappings
- app.services.form_service      -> live application progress information

Everything the assistant says about banking facts comes from these catalogues
except the banking-terminology glossary, which contains only neutral,
definition-style explanations (no fees, rates, or invented policy).

The module never invents availability, eligibility, fees, interest rates or
policy. When information is not in the catalogue it returns an explicit
"information unavailable" template.

Multilingual answer templates exist for en / te / hi. Banking terms, service
names and numeric values (form numbers, minutes) are preserved verbatim in
every language. Names, addresses and account numbers are never translated.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from app.services.banking_services import BankingService, SERVICES
from app.services.document_engine import (
    get_service_mappings,
    get_document_by_id,
)

SUPPORTED_LANGUAGES = ("en", "te", "hi")

# ---------------------------------------------------------------------------
# Language detection (script based)
# ---------------------------------------------------------------------------

def detect_language(text: str, fallback: str = "en") -> str:
    """Detect the dominant script language of a user message.

    Mixed-language input (one Indic script + English words) maps to the Indic
    script; pure Latin text keeps the customer's selected language so
    transliterated Hindi/Telugu still behaves as their chosen language.
    """
    if not text:
        return fallback if fallback in SUPPORTED_LANGUAGES else "en"
    counts = {"te": 0, "hi": 0}
    for ch in text:
        code = ord(ch)
        if 0x0C00 <= code <= 0x0C7F:  # Telugu block
            counts["te"] += 1
        elif 0x0900 <= code <= 0x097F:  # Devanagari block
            counts["hi"] += 1
    best = max(counts, key=lambda k: counts[k])
    if counts[best] > 0:
        return best
    return fallback if fallback in SUPPORTED_LANGUAGES else "en"


# ---------------------------------------------------------------------------
# Intent keywords (en / te / hi)
# ---------------------------------------------------------------------------

def _kw(*phrase_groups: str) -> List[str]:
    """Split comma-separated phrase lists into clean phrase keywords."""
    out: List[str] = []
    for group in phrase_groups:
        for phrase in group.split(","):
            p = phrase.strip().lower()
            if p:
                out.append(p)
    return out

IntentKeywords = Dict[str, Dict[str, List[str]]]

INTENT_KEYWORDS: IntentKeywords = {
    "greeting": {
        "en": _kw("hello, hi, hey, namaste, good morning, good afternoon, good evening, thanks, thank you"),
        "te": _kw("నమస్కారం, హలో, వందనం, ధన్యవాదాలు, థాంక్స్"),
        "hi": _kw("नमस्ते, नमस्कार, हैलो, प्रणाम, सुप्रभात, धन्यवाद, शुक्रिया"),
    },
    "list_services": {
        "en": _kw("what services, which services, list of services, show services, all services, available services, services do you offer, what can i do, what all services"),
        "te": _kw("సేవలు, ఏ సేవలు, సేవలు ఎన్ని, సేవలు చూపించు, జాబితా, అందుబాటులో ఉన్న సేవలు, ఏమి చేయవచ్చు"),
        "hi": _kw("सेवाएं, कौन सी सेवाएं, क्या सेवाएं, सूची, सभी सेवाएं, उपलब्ध सेवाएं, क्या कर सकता"),
    },
    "documents": {
        "en": _kw("which documents, what documents, document requirement, documents required, documents do i need, papers required, documents needed"),
        "te": _kw("డాక్యుమెంట్, డాక్యుమెంట్లు, పత్రాలు, కాగితాలు, డాక్యుమెంట్లు కావాలి, పత్రాలు కావాలి"),
        "hi": _kw("दस्तावेज़, दस्तावेज, कागजात, प्रमाण पत्र, दस्तावेज़ चाहिए, कागजात चाहिए"),
    },
    "eligibility": {
        "en": _kw("eligibility, eligible, who can apply, who is eligible, criteria, qualify"),
        "te": _kw("అర్హత, అర్హులు, అర్హుడు, ఎవరు అర్హులు"),
        "hi": _kw("पात्रता, पात्र, योग्यता, कौन पात्र"),
    },
    "procedure": {
        "en": _kw("how to apply, application procedure, how do i apply, steps to apply, what is the process, procedure"),
        "te": _kw("ఎలా దరఖాస్తు, దరఖాస్తు విధానం, ప్రక్రియ, విధానం, దరఖాస్తు చేయడానికి"),
        "hi": _kw("कैसे आवेदन, आवेदन प्रक्रिया, प्रक्रिया, आवेदन कैसे करें, तरीका"),
    },
    "time": {
        "en": _kw("how long, how much time, estimated time, duration, time taken"),
        "te": _kw("ఎంత సమయం, సమయం పడుతుంది, అంచనా సమయం"),
        "hi": _kw("कितना समय, कितने समय, अवधि, समय लगेगा"),
    },
    "progress": {
        "en": _kw("application status, status of my application, my application progress, progress of my application, application reference"),
        "te": _kw("దరఖాస్తు స్థితి, స్టేటస్, దరఖాస్తు ప్రోగ్రెస్, దరఖాస్తు రిఫరెన్స్"),
        "hi": _kw("आवेदन स्थिति, आवेदन की स्थिति, आवेदन प्रगति, आवेदन रेफरेंस"),
    },
    "pdf": {
        "en": _kw("download pdf, download my application, application pdf, generate pdf, how to download, get pdf copy, pdf download"),
        "te": _kw("pdf డౌన్‌లోడ్, డౌన్‌లోడ్, దరఖాస్తు pdf, ప్రింట్ అవుట్"),
        "hi": _kw("pdf डाउनलोड, डाउनलोड, आवेदन pdf, प्रिंट, कॉपी"),
    },
    "autofill": {
        "en": _kw("fill the form, can you fill, autofill, pre-fill, fill it for me, fill my form, fill for me"),
        "te": _kw("ఫారం నింపు, నింపండి, నింపివ్వు, ఆటోఫిల్, ఫారం భర్తీ"),
        "hi": _kw("फॉर्म भरो, भर दो, भर देंगे, फॉर्म भर दें, ऑटोफिल"),
    },
    "scan_rejection": {
        "en": _kw("rejected, rejection, why rejected, scan failed, rescan, not accepted, scan quality"),
        "te": _kw("తిరస్కరించారు, రిజెక్ట్, తిరిగి స్కాన్, స్కాన్ సరిగా"),
        "hi": _kw("रिजेक्ट, अस्वीकृत, फिर स्कैन, स्कैन नहीं, स्कैन क्वालिटी"),
    },
    "unavailable_fees": {
        "en": _kw("interest rate, fees, charges, how much money, minimum balance, exchange rate, emi calculation"),
        "te": _kw("వడ్డీ రేటు, ఛార్జీలు, రేటు, ఎంత డబ్బు, కనీస నిధి"),
        "hi": _kw("ब्याज दर, शुल्क, चार्ज, कितना पैसा, न्यूनतम राशि"),
    },
}

# ---------------------------------------------------------------------------
# Service matching over the real catalogue
# ---------------------------------------------------------------------------

_STOP_TOKENS = {
    "a", "an", "the", "i", "want", "to", "open", "apply", "for", "of", "in",
    "my", "me", "is", "are", "what", "which", "how", "do", "does", "need",
    "can", "you", "please", "tell", "about", "with", "and", "or", "get",
    "have", "help", "some", "information", "info", "know", "like", "would",
    "that", "give", "explain", "enrol", "register", "make", "new", "any",
}

def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"[^a-z0-9\s\u0c00-\u0c7f\u0900-\u097f]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

_FORM_NUMBER_RE = re.compile(r"\b([A-Z]{2,6})\s?-?\s?(\d{3})\b", re.IGNORECASE)

# alias -> service id, derived from real catalogue names (no invented services)
_SERVICE_ALIASES: Dict[str, str] = {
    "savings account": "acc-001",
    "savings": "acc-001",
    "current account": "acc-002",
    "demat account": "inv-001",
    "credit card": "card-002",
    "debit card": "card-001",
    "personal loan": "loan-003",
    "home loan": "loan-001",
    "fixed deposit": "acc-010",
    "recurring deposit": "acc-009",
}


def match_form_number(text: str) -> Optional[BankingService]:
    """Match a prototype form number like ACC-001 / CARD-004 in the text.

    The catalogue contains a few duplicated prototype form numbers
    (pre-existing Phase 2 data artifact); ties are broken deterministically
    by the lowest service id so identical questions always give identical
    answers. The reply names the exact service it resolved.
    """
    m = _FORM_NUMBER_RE.search(text)
    if not m:
        return None
    form = f"{m.group(1).upper()}-{m.group(2)}"
    return form_number_lookup(form)


def form_number_lookup(form: str) -> Optional[BankingService]:
    matches = sorted(
        (svc for svc in SERVICES.values() if svc.formNumber == form),
        key=lambda s: s.id,
    )
    return matches[0] if matches else None


_INDEX_READY = False
_SERVICE_TOKEN_INDEX: List[Tuple[BankingService, Dict[str, float]]] = []


def _build_index() -> None:
    global _INDEX_READY
    if _INDEX_READY:
        return
    for svc in SERVICES.values():
        tokens: Dict[str, float] = {}
        for tok in _normalise(svc.name).split():
            if tok and tok not in tokens:
                tokens[tok] = 2.0
        _SERVICE_TOKEN_INDEX.append((svc, tokens))
    _INDEX_READY = True


def find_service(text: str) -> Optional[BankingService]:
    """Find the service the customer most likely mentions.

    Priority: exact prototype form number > VERBATIM catalogue service name >
    curated alias phrase > token overlap against the REAL service names.
    """
    form_svc = match_form_number(text)
    if form_svc:
        return form_svc

    lowered = _normalise(text)

    # A verbatim catalogue service name mentioned in the question always wins
    # over generic aliases like "credit card" (a substring of several names).
    for svc in SERVICES.values():
        normalized_name = _normalise(svc.name)
        if normalized_name and normalized_name in lowered:
            return svc

    for phrase, service_id in _SERVICE_ALIASES.items():
        if phrase in lowered and service_id in SERVICES:
            return SERVICES[service_id]

    _build_index()
    query_tokens = [
        t for t in lowered.split()
        if t not in _STOP_TOKENS and len(t) > 2
    ]
    if not query_tokens:
        return None
    best: Optional[Tuple[float, float, BankingService]] = None
    for svc, tokens in _SERVICE_TOKEN_INDEX:
        score = 0.0
        overlap = 0
        for qt in query_tokens:
            if qt in tokens:
                score += tokens[qt]
                overlap += 1
        if overlap == 0:
            continue
        coverage = overlap / len(query_tokens)
        cand = (score, coverage, svc)
        if best is None or (score, coverage) > (best[0], best[1]):
            best = cand
    # Require a decisive match: at least 2 catalogue tokens hitting the query.
    if best and best[0] >= 2.0:
        return best[2]
    return None


# ---------------------------------------------------------------------------
# Banking terminology glossary (neutral definitions only)
# ---------------------------------------------------------------------------

GLOSSARY: Dict[str, Dict[str, Any]] = {
    "kyc": {
        "aliases": ["kyc", "know your customer", "know.your.customer"],
        "answer": {
            "en": "KYC (Know Your Customer) is the process of verifying a customer's identity using prescribed identity and address proof documents. In this prototype, KYC documents are scanned and their details pre-filled into the application form.",
            "te": "KYC (Know Your Customer) అంటే గుర్తింపు మరియు చిరునామా ఆధారపత్రాల ద్వారా గ్రాహకుని గుర్తింపును ధృవీకరించే ప్రక్రియ. ఈ ప్రోటోటైప్‌లో KYC పత్రాలు స్కాన్ చేసి, వాటి వివరాలు దరఖాస్తు ఫారంలో ప్రీ-ఫిల్ అవుతాయి.",
            "hi": "KYC (Know Your Customer) निर्धारित पहचान और पते के दस्तावेज़ों से ग्राहक की पहचान सत्यापित करने की प्रक्रिया है। इस प्रोटोटाइप में KYC दस्तावेज़ स्कैन होकर उनकी जानकारी आवेदन फ़ॉर्म में भरी जाती है।",
        },
    },
    "pan": {
        "aliases": ["pan", "pan.card", "permanent account number"],
        "answer": {
            "en": "A PAN (Permanent Account Number) card is a 10-character income-tax identity document. In this prototype, details such as full name and date of birth are read from it during document scanning.",
            "te": "PAN (Permanent Account Number) కార్డు అనేది 10 అక్షరాల పన్ను గుర్తింపు పత్రం. ఈ ప్రోటోటైప్‌లో పూర్తి పేరు, జన్మ తేదీ వంటి వివరాలు స్కానింగ్ ద్వారా చదవబడతాయి.",
            "hi": "PAN (Permanent Account Number) कार्ड 10 वर्णों का आय-कर पहचान दस्तावेज़ है। इस प्रोटोटाइप में पूरा नाम और जन्म तिथि जैसे विवरण स्कैन के दौरान पढ़े जाते हैं।",
        },
    },
    "aadhaar": {
        "aliases": ["aadhaar", "aadhar", "uidai", "aadhaar.card"],
        "answer": {
            "en": "An Aadhaar card is a government-issued identity document with the holder's demographic details. In this prototype it is used as an identity and address proof for service applications.",
            "te": "ఆధార్ కార్డు అనేది ప్రభుత్వం జారీ చేసిన గుర్తింపు పత్రం. ఈ ప్రోటోటైప్‌లో ఇది దరఖాస్తులకు గుర్తింపు మరియు చిరునామా రుజువుగా వాడబడుతుంది.",
            "hi": "आधार कार्ड सरकार द्वारा जारी पहचान दस्तावेज़ है। इस प्रोटोटाइप में यह आवेदनों के लिए पहचान और पते के प्रमाण के रूप में उपयोग होता है।",
        },
    },
    "ifsc": {
        "aliases": ["ifsc", "ifsc.code"],
        "answer": {
            "en": "An IFSC code is an 11-character code that identifies a specific bank branch in electronic payment systems.",
            "te": "IFSC కోడ్ అనేది ఎలక్ట్రానిక్ చెల్లింపుల్లో ఒక నిర్దిష్ట బ్యాంక్ బ్రాంచ్‌ను గుర్తించే 11-అక్షరాల కోడ్.",
            "hi": "IFSC कोड 11 वर्णों का कोड है जो इलेक्ट्रॉनिक भुगतान प्रणालियों में एक विशेष बैंक शाखा की पहचान करता है।",
        },
    },
    "emi": {
        "aliases": ["emi", "equated monthly installment", "equated monthly instalment"],
        "answer": {
            "en": "An EMI (Equated Monthly Instalment) is a fixed payment amount a borrower makes each month towards repaying a loan.",
            "te": "EMI (Equated Monthly Instalment) అనేది రుణం చెల్లించడానికి రుణగ్రహీత ప్రతి నెల చేసే నిర్దిష్ట మొత్తం.",
            "hi": "EMI (Equated Monthly Instalment) ऋण चुकाने के लिए उधारकर्ता हर महीने चुकाने वाली निश्चित किस्त है।",
        },
    },
    "nominee": {
        "aliases": ["nominee", "nomination"],
        "answer": {
            "en": "A nominee is the person recorded on an account or investment to receive its proceeds when the holder passes away.",
            "te": "నామినీ అంటే ఖాతాదారు మరణించినప్పుడు ఆ ఖాతా లేదా పెట్టుబడి ఫలాలను పొందేందుకు నమోదు చేయబడిన వ్యక్తి.",
            "hi": "नामांकित व्यक्ति (nominee) वह होता है जिसे खाता या निवेश की राशि खाताधारक के निधन के बाद मिलती है।",
        },
    },
    "demat": {
        "aliases": ["demat", "demat.account", "depository"],
        "answer": {
            "en": "A demat account holds securities such as shares and bonds in electronic form.",
            "te": "డీమ్యాట్ ఖాతా అనేది షేర్లు, బాండ్ల వంటి సెక్యూరిటీలను ఎలక్ట్రానిక్ రూపంలో నిల్వ చేస్తుంది.",
            "hi": "डीमैट खाता शेयर और बॉन्ड जैसी प्रतिभूतियों को इलेक्ट्रॉनिक रूप में रखता है।",
        },
    },
    "sip": {
        "aliases": ["sip", "systematic investment plan"],
        "answer": {
            "en": "A SIP (Systematic Investment Plan) is a way of investing a fixed amount at regular intervals into a mutual fund scheme.",
            "te": "SIP (Systematic Investment Plan) అనేది మ్యూచువల్ ఫండ్ పథకంలో క్రమం తప్పకుండా నిర్దిష్ట మొత్తం పెట్టుబడి చేసే పద్ధతి.",
            "hi": "SIP (Systematic Investment Plan) म्यूचुअल फंड योजना में निश्चित राशि का नियमित अंतराल पर निवेश करने का तरीका है।",
        },
    },
    "credit score": {
        "aliases": ["credit score", "cibil", "credit rating"],
        "answer": {
            "en": "A credit score is a numerical indicator of a borrower's credit history used by lenders when assessing loan applications.",
            "te": "క్రెడిట్ స్కోర్ అనేది రుణగ్రహీత చెల్లింపు చరిత్రను తెలిపే సంఖ్యాత్మక సూచిక; రుణ దరఖాస్తుల మూల్యాంకనంలో వాడుతారు.",
            "hi": "क्रेडिट स्कोर उधारकर्ता के भुगतान इतिहास का संख्यात्मक सूचक है जिसका उपयोग ऋण आवेदनों के मूल्यांकन में होता है।",
        },
    },
    "recurring deposit": {
        "aliases": ["recurring deposit", " r.d.", " rd "],
        "answer": {
            "en": "A recurring deposit (RD) is a savings scheme where a fixed amount is deposited every month for a chosen period.",
            "te": "రికరింగ్ డిపాజిట్ (RD) అంటే నిర్ణీత కాలం పాటు ప్రతి నెల నిర్దిష్ట మొత్తం జమ చేసే పొదుపు పథకం.",
            "hi": "आवर्ती जमा (RD) एक बचत योजना है जिसमें निर्धारित अवधि तक हर महीने निश्चित राशि जमा की जाती है।",
        },
    },
    "fixed deposit": {
        "aliases": ["fixed deposit", " f.d."],
        "answer": {
            "en": "A fixed deposit (FD) is a one-time deposit held for a fixed period; its closure procedure is one of the services in this prototype's catalogue.",
            "te": "ఫిక్స్‌డ్ డిపాజిట్ (FD) అంటే ఒకసారి జమ చేసి నిర్ణీత కాలం పాటు నిలిపే ఖాతా; దీని ముగింపు విధానం ఈ ప్రోటోటైప్ సేవల్లో ఒకటి.",
            "hi": "सावधि जमा (FD) एक बार की गई जमा है जो निर्धारित अवधि तक रखी जाती है; इसकी समापन प्रक्रिया इस प्रोटोटाइप के सेवा सूची में है।",
        },
    },
}

# ---------------------------------------------------------------------------
# Language templates for answers
# ---------------------------------------------------------------------------

TEMPLATES: Dict[str, Dict[str, str]] = {
    "greeting": {
        "en": "Hello! I am the ATM banking assistant. I can explain the services available here, their eligibility and document requirements, and how to apply. Ask me anything — for example: {example}",
        "te": "నమస్కారం! నేను ఏటీఎం బ్యాంకింగ్ సహాయకుడను. ఇక్కడ అందుబాటులో ఉన్న సేవలు, వాటి అర్హతలు, డాక్యుమెంట్లు, దరఖాస్తు విధానం గురించి చెప్పగలను. ఏదైనా అడగండి — ఉదా: {example}",
        "hi": "नमस्ते! मैं ATM बैंकिंग सहायक हूँ। मैं यहाँ उपलब्ध सेवाओं, उनकी पात्रता, दस्तावेज़ों और आवेदन की प्रक्रिया के बारे में बता सकता हूँ। कुछ भी पूछिए — जैसे: {example}",
    },
    "fallback": {
        "en": "Sorry, I did not understand that. I can explain the services available on this ATM, their eligibility and document requirements, application steps, and how to generate your application PDF. Please try again in different words.",
        "te": "క్షమించండి, అర్థం కాలేదు. ఈ ఏటీఎంలో అందుబాటులో ఉన్న సేవలు, వాటి అర్హతలు, డాక్యుమెంట్లు, దరఖాస్తు విధానం, దరఖాస్తు PDF గురించి చెప్పగలను. దయచేసి వేరే మాటల్లో ప్రయత్నించండి.",
        "hi": "क्षमा करें, समझ नहीं आया। मैं इस ATM पर उपलब्ध सेवाओं, उनकी पात्रता, दस्तावेज़ों, आवेदन के चरणों और आवेदन PDF बनाने के बारे में बता सकता हूँ। कृपया दूसरे शब्दों में पूछें।",
    },
    "list_categories": {
        "en": "There are 4 categories with 59 services on this ATM:\n{list}\nTell me the service you want and I will explain it.",
        "te": "ఈ ఏటీఎంలో 4 విభాగాల్లో 59 సేవలు ఉన్నాయి:\n{list}\nమీకు కావాల్సిన సేవ చెప్పండి, నేను వివరిస్తాను.",
        "hi": "इस ATM पर 4 श्रेणियों में 59 सेवाएं हैं:\n{list}\nअपनी इच्छित सेवा बताइए, मैं आगे समझाऊँगा।",
    },
    "list_services": {
        "en": "Services under {category}:\n{list}\nWhich one would you like to know about?",
        "te": "{category} విభాగంలోని సేవలు:\n{list}\nదేని గురించి తెలుసుకోవాలి?",
        "hi": "{category} श्रेणी की सेवाएं:\n{list}\nकिस सेवा के बारे में जानना चाहेंगे?",
    },
    "service_intro": {
        "en": "{name} (prototype form {form})\n{description}\nEligibility: {eligibility}\nEstimated time: {time}\nYou can ask me \"what documents do I need?\" for the document list.",
        "te": "{name} (ప్రోటోటైప్ ఫారం {form})\n{description}\nఅర్హత: {eligibility}\nఅంచనా సమయం: {time}\n\"నాకు ఏ డాక్యుమెంట్లు కావాలి?\" అని అడిగితే డాక్యుమెంట్ జాబితా చూపిస్తాను.",
        "hi": "{name} (प्रोटोटाइप फ़ॉर्म {form})\n{description}\nपात्रता: {eligibility}\nअनुमानित समय: {time}\n\"मुझे कौन से दस्तावेज़ चाहिए?\" पूछें तो सूची दिखा सकता हूँ।",
    },
    "eligibility": {
        "en": "Eligibility for {name}: {eligibility}\n(This is from the service catalogue; this prototype does not decide eligibility.)",
        "te": "{name}కి అర్హత: {eligibility}\n(ఇది సేవ జాబితా నుండి; ఈ ప్రోటోటైప్ అర్హతను నిర్ణయించదు.)",
        "hi": "{name} की पात्रता: {eligibility}\n(यह सेवा सूची से है; यह प्रोटोटाइप पात्रता तय नहीं करता।)",
    },
    "documents": {
        "en": "Documents needed for {name} (from the actual checklist):\n{list}\n{note}",
        "te": "{name}కి కావలసిన డాక్యుమెంట్లు (అసలు చెక్‌లిస్ట్ నుండి):\n{list}\n{note}",
        "hi": "{name} के लिए आवश्यक दस्तावेज़ (वास्तविक चेकलिस्ट से):\n{list}\n{note}",
    },
    "procedure": {
        "en": "How to apply for {name}:\n1. Select the service on this ATM — its document checklist opens.\n2. Scan your documents.\n3. Review the pre-filled form and confirm the details.\n4. Generate the application PDF.\nPrototype form number: {form}. Please confirm every detail yourself; the assistant cannot submit anything for you.",
        "te": "{name}కి దరఖాస్తు విధానం:\n1. ఈ ఏటీఎంలో సేవను ఎంచుకోండి — చెక్‌లిస్ట్ తెరుచుకుంటుంది.\n2. మీ డాక్యుమెంట్లు స్కాన్ చేయండి.\n3. ప్రీ-ఫిల్ ఫారం చూసి, వివరాలు ధృవీకరించండి.\n4. దరఖాస్తు PDF జనరేట్ చేయండి.\nప్రోటోటైప్ ఫారం నంబర్: {form}. అన్ని వివరాలు మీరే ధృవీకరించండి; సహాయకుడు మీ తరపున ఏమీ సమర్పించడు.",
        "hi": "{name} के लिए आवेदन कैसे करें:\n1. इस ATM पर सेवा चुनें — उसकी दस्तावेज़ चेकलिस्ट खुलती है।\n2. अपने दस्तावेज़ स्कैन करें।\n3. पहले से भरे फ़ॉर्म की समीक्षा कर विवरण कन्फ़र्म करें।\n4. आवेदन PDF बनाएँ।\nप्रोटोटाइप फ़ॉर्म नंबर: {form}. कृपया हर विवरण स्वयं कन्फ़र्म करें; सहायक आपकी ओर से कुछ भी सबमिट नहीं करता।",
    },
    "time": {
        "en": "Estimated time for {name}: {time}. (An estimate from the service catalogue.)",
        "te": "{name}కి అంచనా సమయం: {time}. (సేవ జాబితా నుండి అంచనా.)",
        "hi": "{name} का अनुमानित समय: {time}. (सेवा सूची से।)",
    },
    "progress_found": {
        "en": "Your application {ref} for {name}:\n- Fields filled: {completed}/{total}\n- Mandatory pending: {pending}\n- Fields confirmed: {confirmed}\nPlease continue on the application screens — the assistant cannot confirm or submit it for you.",
        "te": "మీ దరఖాస్తు {ref} ({name}):\n- భర్తీ అయిన ఫీల్డ్‌లు: {completed}/{total}\n- తప్పనిసరి మిగిలినవి: {pending}\n- ధృవీకరించిన ఫీల్డ్‌లు: {confirmed}\nదరఖాస్తు స్క్రీన్‌ల్లో కొనసాగించండి — సహాయకుడు మీ తరపున ధృవీకరించడు లేదా సమర్పించడు.",
        "hi": "आपका आवेदन {ref} ({name}):\n- भरे गए फ़ील्ड: {completed}/{total}\n- आवश्यक बाकी: {pending}\n- कन्फ़र्म किए फ़ील्ड: {confirmed}\nकृपया आवेदन स्क्रीन पर जारी रखें — सहायक आपकी ओर से कन्फ़र्म या सबमिट नहीं करता।",
    },
    "progress_none": {
        "en": "I don't see an application for you yet. Choose a service on this ATM and start it from its service card — then your application reference will show up here.",
        "te": "మీ దరఖాస్తు సమాచారం కనపడడం లేదు. ఈ ఏటీఎంలో ఒక సేవను ఎంచుకుని, సేవ కార్డు నుండి దరఖాస్తు ప్రారంభించండి — అప్పుడు రిఫరెన్స్ ఇక్కడ కనిపిస్తుంది.",
        "hi": "मुझे आपका आवेदन नहीं दिख रहा। इस ATM पर एक सेवा चुनकर उसके सेवा कार्ड से आवेदन शुरू करें — फिर आपका रेफ़रेंस यहाँ दिखेगा।",
    },
    "pdf": {
        "en": "To download your application PDF:\n1. On the application form screen, complete and confirm all mandatory fields.\n2. Choose \"Generate PDF\"; the download then appears on the same screen.\nThe prototype generates a demonstration document — it is NOT a submission to the bank.",
        "te": "మీ దరఖాస్తు PDF డౌన్‌లోడ్ ఎలా:\n1. దరఖాస్తు ఫారం స్క్రీన్‌లో తప్పనిసరి ఫీల్డ్‌లన్నీ పూర్తి చేసి ధృవీకరించండి.\n2. \"Generate PDF\" ఎంచుకోండి; డౌన్‌లోడ్ అదే స్క్రీన్‌లో కనిపిస్తుంది.\nప్రోటోటైప్ తయారుచేసేది ప్రదర్శన పత్రం — ఇది బ్యాంకుకు సమర్పణ కాదు.",
        "hi": "आपका आवेदन PDF डाउनलोड कैसे करें:\n1. आवेदन फ़ॉर्म स्क्रीन पर सभी आवश्यक फ़ील्ड पूरे कर कन्फ़र्म करें।\n2. \"Generate PDF\" चुनें; डाउनलोड उसी स्क्रीन पर मिलेगा।\nप्रोटोटाइप एक प्रदर्शन दस्तावेज़ बनाता है — यह बैंक में सबमिशन नहीं है।",
    },
    "autofill": {
        "en": "I cannot fill the form for you. After you scan documents, the prototype's autofill reads scanned values into the application form. Open the application form screen and use the autofill button there — every field stays under your control and you must confirm each one.",
        "te": "ఫారం నేను నింపలేను. డాక్యుమెంట్లు స్కాన్ చేసిన తర్వాత, ప్రోటోటైప్ ఆటోఫిల్ స్కాన్ విలువలను దరఖాస్తు ఫారంలోకి చదువుతుంది. దరఖాస్తు ఫారం స్క్రీన్ తెరిచి అక్కడి ఆటోఫిల్ బటన్ వాడండి — ప్రతి ఫీల్డ్ మీ నియంత్రణలోనే ఉంటుంది, మీరే ధృవీకరించాలి.",
        "hi": "मैं फ़ॉर्म आपके लिए नहीं भर सकता। दस्तावेज़ स्कैन होने के बाद प्रोटोटाइप का ऑटोफिल स्कैन की गई जानकारी आवेदन फ़ॉर्म में पढ़ता है। आवेदन फ़ॉर्म स्क्रीन खोलें और वहाँ का ऑटोफिल बटन उपयोग करें — हर फ़ील्ड का नियंत्रण आपके पास रहता है और आपको कन्फ़र्म करना होता है।",
    },
    "scan_rejection": {
        "en": "A scan is usually rejected when the image is unclear or a mandatory document is missing. Please check:\n1. Good light, flat surface, all corners visible.\n2. The document matches the checklist item you selected.\n3. The checklist status screen — rejected items show a reason and a rescan option.\nOn the kiosk screen you can rescan or correct extracted values yourself; the assistant cannot accept or verify documents.",
        "te": "స్కాన్ సాధారణంగా చిత్రం స్పష్టంగా లేకపోవడం లేదా తప్పనిసరి డాక్యుమెంట్ అందకపోవడంతో తిరస్కరించబడుతుంది. చూడండి:\n1. మంచి వెలుతురు, సమతలం, నాలుగు మూలలు కనిపించేలా.\n2. మీరు ఎంచుకున్న చెక్‌లిస్ట్ అంశానికి సరిపోయే డాక్యుమెంట్.\n3. చెక్‌లిస్ట్ స్టాటస్ స్క్రీన్ — తిరస్కరించిన వాటికి కారణం, రీస్కాన్ ఎంపిక కనిపిస్తాయి.\nకొస్క్ స్క్రీన్‌లో మీరే రీస్కాన్ చేయవచ్చు లేదా సరిదిద్దవచ్చు; సహాయకుడు డాక్యుమెంట్లను అంగీకరించడు.",
        "hi": "स्कैन सामान्यतः तब रिजेक्ट होता है जब तस्वीर स्पष्ट न हो या आवश्यक दस्तावेज़ गायब हो। कृपया देखें:\n1. अच्छी रोशनी, समतल सतह, चारों कोने दिखें।\n2. चुने गए चेकलिस्ट आइटम से दस्तावेज़ मेल खाता हो।\n3. चेकलिस्ट स्थिति स्क्रीन — रिजेक्ट आइटम का कारण और रीस्कैन विकल्प दिखता है।\nक्योस्क स्क्रीन पर आप स्वयं रीस्कैन या सुधार कर सकते हैं; सहायक दस्तावेज़ स्वीकार नहीं करता।",
    },
    "unavailable": {
        "en": "I can only answer using the service catalogue available on this ATM. Details such as fees, interest rates, charges or decisions are not available in this prototype, so I prefer not to guess. Please ask me about the lists of services, documents, procedures, or your application progress.",
        "te": "నేను ఈ ఏటీఎంలో అందుబాటులో ఉన్న సేవ జాబితా ఆధారంగా మాత్రమే చెప్తాను. ఛార్జీలు, వడ్డీ రేట్లు, రేట్లు లేదా నిర్ణయాల వివరాలు ఈ ప్రోటోటైప్‌లో లేవు, కాబట్టి ఊహించడం మానడానికి ఇష్టపడతాను. సేవలు, డాక్యుమెంట్లు, విధానం లేదా మీ దరఖాస్తు ప్రగతి గురించి అడగండి.",
        "hi": "मैं केवल इस ATM पर उपलब्ध सेवा सूची के आधार पर उत्तर देता हूँ। शुल्क, ब्याज दरें, चार्ज या निर्णयों की जानकारी इस प्रोटोटाइप में उपलब्ध नहीं है, इसलिए अनुमान नहीं लगाता। कृपया सेवाओं, दस्तावेज़ों, प्रक्रिया या आपकी आवेदन प्रगति के बारे में पूछें।",
    },
    "language_switched": {
        "en": "I will reply in {langname} from now on. (You can also change the language anytime using the language button on the screen.)",
        "te": "ఇకపై నేను {langname} లో స్పందిస్తాను. (స్క్రీన్‌లోని భాష బటన్‌తో భాష ఎప్పుడైనా మార్చుకోవచ్చు.)",
        "hi": "अब मैं {langname} में उत्तर दूँगा। (स्क्रीन के भाषा बटन से भी आप कभी भी भाषा बदल सकते हैं।)",
    },
    "safety_refusal": {
        "en": "This is an educational banking prototype, not a real ATM. I cannot process real transactions, access real accounts, or ask for PINs, OTPs or passwords — and I never will. To continue an application, please use the service and application screens; I'm happy to answer questions about them.",
        "te": "ఇది విద్యాపరమైన బ్యాంకింగ్ ప్రోటోటైప్, నిజమైన ATM కాదు. నిజమైన లావాదేవీలు, స్వీయ ఖాతాల యాక్సెస్, PIN/OTP/పాస్‌వర్డ్‌లను అడగడం — ఏవీ నేను చేయలేను, చేస్తాను కూడా. దరఖాస్తు కొనసాగించడానికి సేవ/దరఖాస్తు స్క్రీన్‌లను వాడండి; వాటి గురించి అడగండి, నేను సంతోషంగా చెప్తాను.",
        "hi": "यह एक शैक्षिक बैंकिंग प्रोटोटाइप है, वास्तविक ATM नहीं। मैं वास्तविक लेन-देन, खातों तक पहुँच, या PIN/OTP/पासवर्ड मांगने में सक्षम नहीं हूँ — और कभी नहीं रहूँगा। आवेदन जारी रखने के लिए कृपया सेवा/आवेदन स्क्रीन का उपयोग करें; उनके बारे में प्रश्नों के उत्तर देने में मुझे खुशी होगी।",
    },
}

LANG_NAMES = {"en": "English", "te": "Telugu (తెలుగు)", "hi": "Hindi (हिंदी)"}

CATEGORY_TITLES: Dict[str, Dict[str, str]] = {
    "account": {"en": "Account Services & Maintenance", "te": "ఖాతా సేవలు", "hi": "खाता सेवाएं"},
    "cards": {"en": "Cards & Cheque Services", "te": "కార్డులు & చెక్కు సేవలు", "hi": "कार्ड व चेक सेवाएं"},
    "loans": {"en": "Loans & Credit Facilities", "te": "రుణాలు & క్రెడిట్ సౌకర్యాలు", "hi": "ऋण व क्रेडिट सेवाएं"},
    "investments": {"en": "Investments, Insurance & Wealth Management", "te": "పెట్టుబడులు, ఇన్సూరెన్స్ & వెల్త్ మేనేజ్‌మెంట్", "hi": "निवेश, बीमा व संपत्ति प्रबंधन"},
}

SUGGESTIONS: Dict[str, List[str]] = {
    "en": [
        "What services are available on this ATM?",
        "I want to open a savings account.",
        "Which documents do I need?",
        "How do I download my application PDF?",
        "What is KYC?",
        "What is the status of my application?",
    ],
    "te": [
        "ఈ ఏటీఎంలో ఏ సేవలు అందుబాటులో ఉన్నాయి?",
        "నాకు సేవింగ్స్ ఖాతా కావాలి.",
        "నాకు ఏ డాక్యుమెంట్లు కావాలి?",
        "దరఖాస్తు PDF డౌన్‌లోడ్ ఎలా చేయాలి?",
        "KYC అంటే ఏమిటి?",
        "నా దరఖాస్తు స్థితి ఏమిటి?",
    ],
    "hi": [
        "इस ATM पर कौन सी सेवाएं उपलब्ध हैं?",
        "मुझे सेविंग्स खाता खोलना है।",
        "मुझे कौन से दस्तावेज़ चाहिए?",
        "आवेदन PDF डाउनलोड कैसे करें?",
        "KYC क्या है?",
        "मेरे आवेदन की स्थिति क्या है?",
    ],
}

CONDITIONAL_WORD = {"en": "conditional", "te": "షరతుతో కావాలి", "hi": "शर्त के साथ"}
OPTIONAL_WORD = {"en": "optional", "te": "ఐచ్ఛికం", "hi": "वैकल्पिक"}
MANDATORY_WORD = {"en": "mandatory", "te": "తప్పనిసరి", "hi": "आवश्यक"}


# ---------------------------------------------------------------------------
# Intent matching
# ---------------------------------------------------------------------------

def _kw_matches(kw: str, text_norm: str) -> bool:
    """Keyword containment with word boundaries for Latin-script keywords.

    Bare short words like "hi" must not match inside "which" — substring
    matching hijacked unrelated questions (e.g. greetings) in Phase 8 E2E
    probing. Indic-script keywords keep plain containment (script tokens are
    not split by \\w boundary rules reliably across the three languages).
    """
    if any(
        ("\u0900" <= ch <= "\u097F") or ("\u0C00" <= ch <= "\u0C7F") for ch in kw
    ):
        return kw in text_norm
    return re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", text_norm) is not None


def match_intent(text_norm: str, lang: str) -> str:
    """Best-effort intent detection from multilingual keyword groups."""
    for intent, groups in INTENT_KEYWORDS.items():
        for probe in (lang, "en"):
            for kw in groups.get(probe, []):
                if _kw_matches(kw, text_norm):
                    return intent
    return ""


# ---------------------------------------------------------------------------
# Answer construction
# ---------------------------------------------------------------------------

def _document_lines(svc: BankingService, lang: str) -> List[Dict[str, str]]:
    """Document lines resolved from the REAL service document mappings,
    with translated document names when a translation exists."""
    lines: List[Dict[str, str]] = []
    for mapping in get_service_mappings(svc.id):
        doc = get_document_by_id(mapping.document_id)
        if not doc:
            continue
        label = doc.name.get(lang) or doc.name.get("en", doc.id)
        if mapping.conditional:
            kind = CONDITIONAL_WORD.get(lang, "conditional")
        elif mapping.mandatory:
            kind = MANDATORY_WORD.get(lang, "mandatory")
        else:
            kind = OPTIONAL_WORD.get(lang, "optional")
        lines.append({"label": label, "kind": kind})
    return lines


def format_document_list(svc: BankingService, lang: str) -> str:
    """Deterministic list: mandatory first, then conditional, then optional."""
    ordered = _document_lines(svc, lang)
    rank_map = {
        MANDATORY_WORD.get(lang): 0,
        CONDITIONAL_WORD.get(lang): 1,
        OPTIONAL_WORD.get(lang): 2,
    }
    ordered.sort(key=lambda d: rank_map.get(d["kind"], 3))
    return "\n".join(f"- {d['label']} ({d['kind']})" for d in ordered)


def format_services_list(lang: str, category: Optional[str] = None) -> List[str]:
    lines: List[str] = []
    for svc in sorted(SERVICES.values(), key=lambda s: (s.category, s.id)):
        if category and svc.category != category:
            continue
        lines.append(f"- {svc.name} ({svc.formNumber})")
    return lines


def format_categories_list(lang: str) -> str:
    counts: Dict[str, int] = {}
    for svc in SERVICES.values():
        counts[svc.category] = counts.get(svc.category, 0) + 1
    lines = []
    for key in ("account", "cards", "loans", "investments"):
        label = CATEGORY_TITLES[key][lang]
        n = counts.get(key, 0)
        lines.append(f"- {label} ({n})")
    return "\n".join(lines)


def glossary_answer(text_norm: str, lang: str) -> Optional[str]:
    for entry in GLOSSARY.values():
        for alias in entry["aliases"]:
            if alias in text_norm and len(alias) > 2:
                return entry["answer"].get(lang) or entry["answer"]["en"]
    return None


def definition_cue(text_norm: str) -> bool:
    """True when the customer is asking for the definition of a term
    (e.g. 'what is KYC?'), rather than about a specific service."""
    cues = (
        "what is ", "what are ", "meaning of", "mean by",
        "అంటే ఏమిటి", "అంటే", "అర్థం",
        "क्या है", "का मतलब", "मतलब", "इसका मतलब",
    )
    return any(c in text_norm for c in cues)


def language_switch_request(text_norm: str) -> Optional[str]:
    """Detect an explicit mid-session request to change the reply language."""
    cues = {
        "te": ["reply in telugu", "respond in telugu", "speak in telugu", "tell in telugu",
               "telugu lo cheppu", "telugu lo cheppandi", "తెలుగులో"],
        "hi": ["reply in hindi", "respond in hindi", "speak in hindi", "tell in hindi",
               "hindi me reply", "hindi mein reply", "हिंदी में"],
        "en": ["reply in english", "respond in english", "speak in english", "tell in english",
               "in english please"],
    }
    for lang in SUPPORTED_LANGUAGES:
        for cue in cues[lang]:
            if cue in text_norm:
                return lang
    return None
