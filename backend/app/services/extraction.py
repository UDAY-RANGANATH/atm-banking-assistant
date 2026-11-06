"""
Document Classification & Structured Information Extraction (Phase 4)

- Classification matches OCR text against per-document-type keyword sets,
  with the selected checklist document acting as the primary context.
- Extraction uses per-type field schemas and regular expressions over OCR
  lines. Missing fields are returned as null - values are NEVER invented.
- Field confidence comes from real Tesseract word confidences of the line
  that matched; no artificial confidence values are computed.
- Sensitive identifiers (Aadhaar, PAN) are masked before leaving this module.

This is OCR-based document recognition, NOT document authentication.
The system never claims to verify whether an Aadhaar/PAN/certificate is
genuine - it only reads text from an image.
"""

import re
from typing import Dict, Any, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Document type definitions
# ---------------------------------------------------------------------------

# doc engine id -> canonical doc type used for classification/extraction
DOC_TYPE_BY_DOCUMENT_ID: Dict[str, str] = {
    "doc-aadhaar": "AADHAAR_LIKE",
    "doc-aadhaar-address": "AADHAAR_LIKE",
    "doc-pan": "PAN_LIKE",
    "doc-passport": "PASSPORT",
    "doc-voter-id": "VOTER_ID",
    "doc-driving-licence": "DRIVING_LICENCE",
    "doc-other-id": "OTHER_ID",
    "doc-utility-bill": "UTILITY_BILL",
    "doc-bank-statement": "BANK_STATEMENT",
    "doc-rent-agreement": "RENT_AGREEMENT",
    "doc-form60": "DECLARATION_FORM",
    "doc-salary-slips": "SALARY_SLIP",
    "doc-income-certificate": "INCOME_CERTIFICATE",
    "doc-itr": "ITR",
    "doc-employment-certificate": "EMPLOYMENT_CERTIFICATE",
    "doc-10th-marksheet": "MARKSHEET",
    "doc-12th-marksheet": "MARKSHEET",
    "doc-graduation-certificate": "EDUCATIONAL_CERTIFICATE",
    "doc-admission-letter": "ADMISSION_LETTER",
    "doc-fee-structure": "FEE_STRUCTURE",
    "doc-birth-certificate": "BIRTH_CERTIFICATE",
    "doc-photograph": "PHOTOGRAPH",
    "doc-signature": "SIGNATURE",
    "doc-property-documents": "PROPERTY_DOCUMENT",
    "doc-sale-agreement": "SALE_AGREEMENT",
    "doc-property-valuation": "VALUATION_REPORT",
    "doc-gold-documents": "GOLD_DOCUMENT",
    "doc-vehicle-quotation": "VEHICLE_QUOTATION",
    "doc-business-registration": "BUSINESS_REGISTRATION",
    "doc-gst-registration": "GST_REGISTRATION",
    "doc-business-financials": "BUSINESS_FINANCIALS",
    "doc-partnership-deed": "PARTNERSHIP_DEED",
    "doc-company-incorporation": "INCORPORATION_DOCUMENT",
    "doc-insurance-policy": "INSURANCE_POLICY",
    "doc-claim-documents": "CLAIM_DOCUMENTS",
    "doc-police-report": "POLICE_REPORT",
    "doc-medical-certificate": "MEDICAL_CERTIFICATE",
    "doc-demat-documents": "DEMAT_DOCUMENTS",
    "doc-other-declaration": "DECLARATION_FORM",
}

# Classification keyword sets per doc type (OCR-text evidence)
CLASSIFICATION_KEYWORDS: Dict[str, List[str]] = {
    "AADHAAR_LIKE": ["aadhaar", "aadhar", "आधार", "uidai", "unique identification"],
    "PAN_LIKE": ["permanent account number", "income tax department", "पैन", "pan card", "govt. of india"],
    "PASSPORT": ["passport", "republic of india", "travel document"],
    "VOTER_ID": ["election commission", "epic", "voter"],
    "DRIVING_LICENCE": ["driving licence", "driving license", "dl no", "transport department"],
    "OTHER_ID": [],
    "UTILITY_BILL": ["electricity bill", "water bill", "gas bill", "telephone bill", "amount due", "bill no"],
    "BANK_STATEMENT": ["statement of account", "account statement", "transaction", "balance", "ifsc"],
    "RENT_AGREEMENT": ["rent agreement", "leave and license", "landlord", "tenant"],
    "DECLARATION_FORM": ["declaration", "declare", "form 60", "form no. 60", "self declaration"],
    "SALARY_SLIP": ["salary slip", "pay slip", "payroll", "gross salary", "net salary", "earnings", "deductions"],
    "INCOME_CERTIFICATE": ["income certificate", "annual income"],
    "ITR": ["income tax return", "assessment year", "acknowledgement", "itr"],
    "EMPLOYMENT_CERTIFICATE": ["employment certificate", "to whomsoever it may concern", "designation", "employee"],
    "MARKSHEET": ["marksheet", "mark sheet", "secondary school", "higher secondary", "10th", "12th", "board", "marks obtained"],
    "EDUCATIONAL_CERTIFICATE": ["bachelor", "degree", "b.tech", "b.sc", "b.com", "b.a.", "university", "graduation"],
    "ADMISSION_LETTER": ["admission", "offer of admission", "enroll", "seat allotted"],
    "FEE_STRUCTURE": ["fee structure", "tuition fee", "semester fee", "fees payable"],
    "BIRTH_CERTIFICATE": ["birth certificate", "date of birth", "municipal"],
    "PHOTOGRAPH": [],
    "SIGNATURE": [],
    "PROPERTY_DOCUMENT": ["title deed", "sale deed", "property", "khata", "registration of documents"],
    "SALE_AGREEMENT": ["sale agreement", "agreement to sell", "seller", "purchaser"],
    "VALUATION_REPORT": ["valuation", "market value", "valuer", "valuation report"],
    "GOLD_DOCUMENT": ["gold", "karat", "carat", "purity", "ornaments", "hallmark"],
    "VEHICLE_QUOTATION": ["quotation", "ex-showroom", "on-road price", "vehicle", "chassis"],
    "BUSINESS_REGISTRATION": ["business registration", "trade licence", "/msme/", "udyam", "provisional registration"],
    "GST_REGISTRATION": ["gst", "goods and services tax", "gstin"],
    "BUSINESS_FINANCIALS": ["profit", "loss statement", "balance sheet", "turnover", "audit"],
    "PARTNERSHIP_DEED": ["partnership deed", "partners", "profit sharing"],
    "INCORPORATION_DOCUMENT": ["certificate of incorporation", "registrar of companies", "cin", "company"],
    "INSURANCE_POLICY": ["policy", "insurance", "policy number", "sum assured", "premium"],
    "CLAIM_DOCUMENTS": ["claim", "claimant", "incident", "claim number"],
    "POLICE_REPORT": ["police", "fir", "station", "complainant"],
    "MEDICAL_CERTIFICATE": ["medical certificate", "diagnosis", "doctor", "hospital"],
    "DEMAT_DOCUMENTS": ["demat", "depository", "dp id", "client id"],
}

NOT_DOCUMENT_TYPES = {"PHOTOGRAPH", "SIGNATURE", "OTHER_ID"}


def classify_document(
    ocr_text: str,
    expected_document_id: str,
) -> Dict[str, Any]:
    """
    Classify a scanned document.

    The selected checklist document is the primary context: it defines the
    expected type. OCR keyword evidence corroborates or contradicts it.

    Returns:
      {
        "expected_type": str,
        "detected_type": str | None,
        "match": "MATCH" | "MISMATCH" | "UNKNOWN",
        "evidence": [matched keywords],
      }
    """
    text = (ocr_text or "").lower()
    evidence: Dict[str, int] = {}

    for dtype, keywords in CLASSIFICATION_KEYWORDS.items():
        if not keywords:
            continue
        score = 0
        matched = []
        for kw in keywords:
            if kw.lower() in text:
                score += 2
                matched.append(kw)
        if score:
            evidence[dtype] = score
            evidence[f"{dtype}::kw"] = score

    expected_type = DOC_TYPE_BY_DOCUMENT_ID.get(expected_document_id, "UNKNOWN")

    if expected_type in NOT_DOCUMENT_TYPES or expected_type == "UNKNOWN":
        # Nothing sensible to classify; trust the checklist selection
        return {
            "expected_type": expected_type,
            "detected_type": expected_type if expected_type != "UNKNOWN" else None,
            "match": "MATCH",
            "evidence": [],
        }

    detected: Optional[str] = None
    best = 0
    for dtype in evidence:
        if "::kw" in dtype:
            continue
        if evidence[dtype] > best:
            best = evidence[dtype]
            detected = dtype

    # Collect matched keywords of the detected type
    kw_list: List[str] = []
    if detected:
        kw_key = f"{detected}::kw"
        # Re-run keyword match purely for the report (cheap, deterministic)
        for kw in CLASSIFICATION_KEYWORDS.get(detected, []):
            if kw.lower() in text:
                kw_list.append(kw)

    if detected is None:
        match = "UNKNOWN"
        detected = None
    elif detected == expected_type or (detected, expected_type) in [
        ("AADHAAR_LIKE", "AADHAAR_LIKE"),
    ]:
        match = "MATCH"
    else:
        # Related pairs that are legitimately the same physical document
        related = {
            ("AADHAAR_LIKE", "DRIVING_LICENCE"): False,  # explicit, keep strict
            ("MARKSHEET", "EDUCATIONAL_CERTIFICATE"): True,
            ("EDUCATIONAL_CERTIFICATE", "MARKSHEET"): True,
            ("DECLARATION_FORM", "FORM60"): True,
        }
        match = "MATCH" if related.get((detected, expected_type)) else "MISMATCH"

    return {
        "expected_type": expected_type,
        "detected_type": detected,
        "match": match,
        "evidence": kw_list,
    }


# ---------------------------------------------------------------------------
# Extraction schemas / regexes
# ---------------------------------------------------------------------------

RE_DATE = re.compile(r"\b(\d{1,2}[\/\-. ]\d{1,2}[\/\-. ]\d{2,4}|\d{4}[\/\-.]\d{1,2}[\/\-.]\d{1,2})\b")
RE_AADHAAR = re.compile(r"\b(\d{4}\s?\d{4}\s?\d{4})\b")
RE_PAN = re.compile(r"\b([A-Z]{5}\d{4}[A-Z])\b")
RE_GSTIN = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9][A-Z0-9A-Z]{3}[A-Z0-9]\b)")
RE_PASSPORT = re.compile(r"\b([A-Z]\d{7})\b")
RE_CIN = re.compile(r"\b([LU]\d{5}[A-Z]{2}\d{4}[A-Z]{2}\d{6})\b")
RE_VOTER = re.compile(r"\b([A-Z]{3}\d{7})\b")
RE_DL = re.compile(r"\b([A-Z]{2}[- ]?\d{2}[- ]?\d{11,13})\b")
RE_AMOUNT = re.compile(r"(?:Rs\.?|INR|₹)\s*([0-9,]+(?:\.[0-9]{1,2})?)|([0-9][0-9,]{2,}(?:\.[0-9]{1,2})?)")
RE_YEAR = re.compile(r"\b(19\d{2}|20[0-2]\d)\b")
RE_IFSC = re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b")

FIELD_LABELS = {
    "full_name": ("name", "नाम", "పేరు"),
    "date_of_birth": ("dob", "date of birth", "d.o.b", "जन्म तिथि", "जन्मदिनांक", "పుట్టిన తేదీ"),
    "fathers_name": ("father", "s/o", "d/o", "पिता", "తండ్రి"),
    "address": ("address", "पता", "చిరునామా"),
    "gender": ("gender", "male", "female", "लिंग"),
    "employee_name": ("employee name", "employee", "name"),
    "employer": ("employer", "company", "firm"),
    "basic_salary": ("basic", "basic salary"),
    "gross_salary": ("gross", "gross salary"),
    "net_salary": ("net", "net salary", "net pay"),
    "pay_period": ("pay period", "month", "salary month"),
    "student_name": ("name",),
    "institution": ("school", "college", "university", "institution", "board"),
    "qualification": ("class", "std", "course", "degree", "examination"),
    "year_of_completion": ("year of passing", "passing", "year"),
    "marks_or_grade": ("marks", "percentage", "grade", "total"),
    "business_name": ("business name", "firm name", "trading as"),
    "company_name": ("company name",),
    "account_holder": ("account holder", "holder name"),
    "account_number": ("account number", "a/c"),
    "bank_name": ("bank",),
    "ifsc": ("ifsc",),
    "tenant_name": ("tenant",),
    "landlord_name": ("landlord",),
    "owner_name": ("owner",),
    "buyer_name": ("buyer", "purchaser"),
    "seller_name": ("seller", "vendor"),
    "declarant_name": ("declarant", "name of declarant"),
    "policyholder_name": ("policy holder", "policyholder", "holder name", "insured"),
    "policy_number": ("policy no", "policy number", "policy number"),
    "claimant_name": ("claimant",),
    "complainant_name": ("complainant",),
    "patient_name": ("patient", "patient name"),
    "doctor_name": ("doctor", "dr.", "physician"),
    "child_name": ("name of child", "child name"),
    "parents_names": ("parents", "mother", "father"),
    "dp_id": ("dp id",),
    "client_id": ("client id",),
    "person_type": (),
    "consumer_name": ("consumer name", "consumer no", "consumer"),
    "registration_number": ("registration no", "registration number", "reg no", "udyam"),
    "gstin": ("gstin",),
    "policy_number": ("policy no", "policy number"),
    "vehicle_model": ("vehicle", "model", "make", "make/model"),
    "dealer_name": ("dealer",),
    "document_type": ("deed", "sale deed", "title deed", "khata", "document type"),
    "police_station": ("police station", "station"),
    "fir_number": ("fir no", "fir number", "fir"),
    "hospital_name": ("hospital", "clinic", "medical centre", "medical center"),
    "issuing_authority": ("issuing authority", "issued by", "authority"),
    "assessment_year": ("assessment year", "ay"),
}

# Fields whose extracted value is a numeric amount
AMOUNT_FIELDS = [
    "amount_due", "basic_salary", "gross_salary", "net_salary",
    "annual_income", "total_income", "total_fees", "sale_price",
    "property_value", "vehicle_price", "coverage_amount",
    "claim_amount", "annual_turnover", "net_profit",
]

# Field schema per doc type (illustrative schemas from the spec, extended
# to all supported types). Values: human field names.
EXTRACTION_SCHEMAS: Dict[str, Dict[str, str]] = {
    "AADHAAR_LIKE": {
        "full_name": "Full Name",
        "date_of_birth": "Date of Birth",
        "gender": "Gender",
        "address": "Address",
        "document_identifier": "Aadhaar Number (masked)",
    },
    "PAN_LIKE": {
        "full_name": "Full Name",
        "fathers_name": "Father's Name",
        "date_of_birth": "Date of Birth",
        "document_identifier": "PAN Identifier (masked)",
    },
    "PASSPORT": {
        "full_name": "Full Name",
        "date_of_birth": "Date of Birth",
        "nationality": "Nationality",
        "document_identifier": "Passport Number (masked)",
    },
    "VOTER_ID": {
        "full_name": "Full Name",
        "date_of_birth": "Date of Birth",
        "fathers_name": "Father's Name",
        "document_identifier": "Voter ID Number (masked)",
    },
    "DRIVING_LICENCE": {
        "full_name": "Full Name",
        "date_of_birth": "Date of Birth",
        "address": "Address",
        "document_identifier": "Licence Number",
    },
    "OTHER_ID": {
        "full_name": "Full Name",
        "document_identifier": "Document Number",
    },
    "UTILITY_BILL": {
        "consumer_name": "Consumer Name",
        "address": "Service Address",
        "bill_date": "Bill Date",
        "amount_due": "Amount Due",
    },
    "BANK_STATEMENT": {
        "account_holder": "Account Holder",
        "account_number": "Account Number (masked)",
        "bank_name": "Bank Name",
        "ifsc": "IFSC Code",
        "statement_period": "Statement Period",
    },
    "RENT_AGREEMENT": {
        "tenant_name": "Tenant Name",
        "landlord_name": "Landlord Name",
        "address": "Premises Address",
        "agreement_date": "Agreement Date",
    },
    "DECLARATION_FORM": {
        "declarant_name": "Declarant Name",
        "declaration_date": "Declaration Date",
    },
    "SALARY_SLIP": {
        "employee_name": "Employee Name",
        "employer": "Employer",
        "pay_period": "Pay Period",
        "basic_salary": "Basic Salary",
        "gross_salary": "Gross Salary",
        "net_salary": "Net Salary",
    },
    "INCOME_CERTIFICATE": {
        "full_name": "Applicant Name",
        "annual_income": "Annual Income",
        "issuing_authority": "Issuing Authority",
        "certificate_date": "Certificate Date",
    },
    "ITR": {
        "full_name": "Assessee Name",
        "assessment_year": "Assessment Year",
        "total_income": "Total Income",
        "pan_identifier": "PAN (masked)",
    },
    "EMPLOYMENT_CERTIFICATE": {
        "employee_name": "Employee Name",
        "employer": "Employer",
        "designation": "Designation",
        "joining_date": "Date of Joining",
    },
    "MARKSHEET": {
        "student_name": "Student Name",
        "institution": "Board / School",
        "qualification": "Examination / Class",
        "year_of_completion": "Year of Passing",
        "marks_or_grade": "Marks or Grade",
    },
    "EDUCATIONAL_CERTIFICATE": {
        "student_name": "Student Name",
        "institution": "University / College",
        "qualification": "Degree",
        "year_of_completion": "Year of Completion",
    },
    "ADMISSION_LETTER": {
        "student_name": "Student Name",
        "institution": "Institution",
        "course_name": "Course",
        "admission_date": "Admission Date",
    },
    "FEE_STRUCTURE": {
        "course_name": "Course",
        "institution": "Institution",
        "total_fees": "Total Fees",
        "payment_schedule": "Payment Schedule",
    },
    "BIRTH_CERTIFICATE": {
        "child_name": "Child Name",
        "date_of_birth": "Date of Birth",
        "place_of_birth": "Place of Birth",
        "parents_names": "Parents' Names",
    },
    "PROPERTY_DOCUMENT": {
        "owner_name": "Owner Name",
        "property_address": "Property Address",
        "document_type": "Document Type",
        "registration_date": "Registration Date",
    },
    "SALE_AGREEMENT": {
        "buyer_name": "Buyer Name",
        "seller_name": "Seller Name",
        "property_address": "Property Address",
        "sale_price": "Sale Price",
    },
    "VALUATION_REPORT": {
        "property_address": "Property Address",
        "property_value": "Market Value",
        "valued_by": "Valuer",
        "valuation_date": "Valuation Date",
    },
    "GOLD_DOCUMENT": {
        "gold_weight": "Gold Weight",
        "gold_purity": "Gold Purity",
        "purchase_date": "Purchase Date",
    },
    "VEHICLE_QUOTATION": {
        "vehicle_model": "Vehicle Model",
        "dealer_name": "Dealer Name",
        "vehicle_price": "Quoted Price",
        "quotation_date": "Quotation Date",
    },
    "BUSINESS_REGISTRATION": {
        "business_name": "Business Name",
        "registration_number": "Registration Number",
        "registration_date": "Registration Date",
    },
    "GST_REGISTRATION": {
        "business_name": "Business Name",
        "gstin": "GSTIN",
        "registration_date": "Registration Date",
    },
    "BUSINESS_FINANCIALS": {
        "business_name": "Business Name",
        "annual_turnover": "Annual Turnover",
        "net_profit": "Net Profit",
        "financial_year": "Financial Year",
    },
    "PARTNERSHIP_DEED": {
        "business_name": "Firm Name",
        "partner_names": "Partners",
        "profit_sharing_ratio": "Profit Sharing Ratio",
    },
    "INCORPORATION_DOCUMENT": {
        "company_name": "Company Name",
        "cin": "CIN",
        "incorporation_date": "Incorporation Date",
    },
    "INSURANCE_POLICY": {
        "policyholder_name": "Policyholder Name",
        "policy_number": "Policy Number",
        "policy_type": "Policy Type",
        "coverage_amount": "Coverage / Sum Assured",
    },
    "CLAIM_DOCUMENTS": {
        "claimant_name": "Claimant Name",
        "claim_number": "Claim Number",
        "claim_amount": "Claim Amount",
        "incident_date": "Incident Date",
    },
    "POLICE_REPORT": {
        "complainant_name": "Complainant Name",
        "fir_number": "FIR Number",
        "police_station": "Police Station",
        "incident_date": "Incident Date",
    },
    "MEDICAL_CERTIFICATE": {
        "patient_name": "Patient Name",
        "doctor_name": "Doctor Name",
        "hospital_name": "Hospital / Clinic",
        "treatment_date": "Treatment Date",
    },
    "DEMAT_DOCUMENTS": {
        "account_holder": "Account Holder",
        "dp_id": "DP ID",
        "client_id": "Client ID",
        "depository_name": "Depository",
    },
    "PHOTOGRAPH": {},
    "SIGNATURE": {},
}


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _label_value(line_text: str, labels: Tuple[str, ...]):
    """Extract the value after a label like 'Name : ...' (None if absent)."""
    lw = line_text.lower()
    for lbl in labels:
        idx = lw.find(lbl.lower())
        if idx != -1:
            after = line_text[idx + len(lbl):]
            after = re.sub(r"^[\s:.\-–—|]+", "", after)
            after = after.strip()
            if after:
                return after
    return None


def _try_schema_label(line_text: str, field: str):
    return _label_value(line_text, FIELD_LABELS.get(field, ()))


def _confidence_of_line(lines: List[Dict[str, Any]], matched_text: str) -> Optional[float]:
    for line in lines:
        if line["text"].strip() == matched_text.strip() or matched_text in line["text"]:
            return line["confidence"]
    return None


def extract_fields(
    doc_type: str,
    ocr_lines: List[Dict[str, Any]],
    full_text: str,
) -> Dict[str, Dict[str, Any]]:
    """
    Run the extraction schema for a doc type.

    Returns {field: {"label": str, "value": str|None, "confidence": float|None,
                     "source_line": str|None}}
    Missing fields are null - never invented.
    """
    schema = EXTRACTION_SCHEMAS.get(doc_type, {})
    out: Dict[str, Dict[str, Any]] = {
        f: {"label": lbl, "value": None, "confidence": None, "source_line": None}
        for f, lbl in schema.items()
    }

    lines = [l["text"] for l in ocr_lines]

    def set_field(field: str, value, line_text: str, conf=None):
        if field not in out:
            return
        if out[field]["value"] is None and value:
            out[field]["value"] = str(value)
            out[field]["source_line"] = line_text
            out[field]["confidence"] = conf

    lines = [raw["text"] for raw in ocr_lines]
    confs = {raw["text"]: raw["confidence"] for raw in ocr_lines}

    # --- Label pattern matching (Name:, DOB:, etc.) ---
    # The label and the value may be on the same line ('Name : X') or on the
    # following line(s) when the document uses stacked labels.
    for i, raw in enumerate(ocr_lines):
        line_text = raw["text"]
        conf = raw["confidence"]
        if i == 0:
            continue  # the first line is usually the document title - skip it
        for field, labels in FIELD_LABELS.items():
            if field not in out:
                continue
            if out[field]["value"] is not None:
                continue
            lw = line_text.lower()
            matched_label = next(
                (lbl for lbl in labels if lbl.lower() in lw), None
            )
            if matched_label is None:
                continue
            v = _label_value(line_text, (matched_label,))
            if v:
                # Trim runaway values (labels at end of line swallow next line)
                if len(v) > 80:
                    v = None
                else:
                    # For amount fields keep just the numeric part
                    if field in AMOUNT_FIELDS:
                        am = RE_AMOUNT.search(v)
                        if am:
                            v = am.group(1) or am.group(2)
                    # For identifier fields keep the clean identifier
                    elif field in ("document_identifier", "pan_identifier", "gstin", "cin", "account_number"):
                        v = re.sub(r"\s+", "", v) if "account_number" not in field else v
                    set_field(field, v, line_text, conf)
            if out[field]["value"] is None:
                # stacked-label documents: value usually on the next line
                for j in (i + 1, i + 2):
                    if j < len(lines):
                        nxt = lines[j].strip()
                        if nxt and len(nxt) <= 80 and ":" not in nxt:
                            # value line must not itself be a label line
                            if not any(
                                lbl.lower() in nxt.lower() for lbl in FIELD_LABELS.get(field, ())
                            ):
                                set_field(field, nxt, nxt, confs.get(nxt))
                                break
            # only the first matching label per line can claim this line: fall
            # through so later fields can still match their own labels

        # --- Per-line pattern matching (identifiers, dates, amounts, ...) ---
        line_text = raw["text"]
        conf = raw["confidence"]

        # --- Document identifiers by regex over the whole line ---
        if "document_identifier" in out and out["document_identifier"]["value"] is None:
            m = None
            if doc_type == "AADHAAR_LIKE":
                m = RE_AADHAAR.search(line_text)
            elif doc_type == "PAN_LIKE":
                m = RE_PAN.search(line_text)
            elif doc_type == "PASSPORT":
                m = RE_PASSPORT.search(line_text)
            elif doc_type == "VOTER_ID":
                m = RE_VOTER.search(line_text)
            elif doc_type == "DRIVING_LICENCE":
                m = RE_DL.search(line_text)
            if m:
                set_field("document_identifier", m.group(1).replace(" ", ""), line_text, conf)

        if "pan_identifier" in out and out["pan_identifier"]["value"] is None:
            m = RE_PAN.search(line_text)
            if m:
                set_field("pan_identifier", m.group(1), line_text, conf)

        if "ifsc" in out and out["ifsc"]["value"] is None:
            m = RE_IFSC.search(line_text)
            if m:
                set_field("ifsc", m.group(1).upper(), line_text, conf)

        if "gstin" in out and out["gstin"]["value"] is None:
            m = RE_GSTIN.search(line_text)
            if m:
                set_field("gstin", m.group(1), line_text, conf)

        if "cin" in out and out["cin"]["value"] is None:
            m = RE_CIN.search(line_text)
            if m:
                set_field("cin", m.group(1), line_text, conf)

        # --- Dates ---
        date_fields = [
            "date_of_birth", "bill_date", "agreement_date", "declaration_date",
            "certificate_date", "admission_date", "registration_date",
            "valuation_date", "purchase_date", "quotation_date",
            "incident_date", "treatment_date", "joining_date", "issue_date",
        ]
        for field in date_fields:
            if field not in out:
                continue
            if out[field]["value"] is not None:
                continue
            m = RE_DATE.search(line_text)
            if m:
                set_field(field, m.group(1), line_text, conf)

        # --- Amounts (label context required to avoid grabbing random numbers) ---
        amount_fields = AMOUNT_FIELDS
        for field in amount_fields:
            if field not in out:
                continue
            if out[field]["value"] is not None:
                continue
            labels = FIELD_LABELS.get(field, ())
            lw = line_text.lower()
            label_on_line = next((lbl for lbl in labels if lbl.lower() in lw), None)
            if label_on_line is None:
                continue
            after = _label_value(line_text, (label_on_line,))
            m = RE_AMOUNT.search(after) if after else None
            if m:
                val = m.group(1) or m.group(2)
                set_field(field, val, line_text, conf)

        # --- Other specific patterns ---
        if "assessment_year" in out and out["assessment_year"]["value"] is None and full_text:
            m = re.search(r"assessment\s+year[^0-9]{0,12}(\d{4}[-\s/–]\d{2,4})", full_text, re.I)
            if m:
                src = next((l["text"] for l in ocr_lines if "assessment" in l["text"].lower()), "")
                set_field("assessment_year", m.group(1), src, None)
        if "year_of_completion" in out and out["year_of_completion"]["value"] is None:
            m = RE_YEAR.search(line_text)
            if m:
                set_field("year_of_completion", m.group(1), line_text, conf)
        if "financial_year" in out and out["financial_year"]["value"] is None:
            m = re.search(r"\b(\d{4}[-\s/–]\d{2,4})\b", line_text)
            if m:
                set_field("financial_year", m.group(1), line_text, conf)
        if "gold_purity" in out and out["gold_purity"]["value"] is None:
            m = re.search(r"\b(24\d{0,2}|22\d{0,2}|21\d{0,2}|18\d{0,2})\s*K(?:arat)?\b", line_text, re.I)
            if not m:
                m = re.search(r"\b(\d{2})\s*(?:k|kt|karat|carat|purity)\b", line_text, re.I)
            if m:
                set_field("gold_purity", m.group(1) + "K", line_text, conf)
        if "gold_weight" in out and out["gold_weight"]["value"] is None:
            m = re.search(r"\b(\d+(?:\.\d+)?)\s*(g|gram|grams|gm)\b", line_text, re.I)
            if m:
                set_field("gold_weight", m.group(1) + " g", line_text, conf)
        if "dp_id" in out and out["dp_id"]["value"] is None:
            m = re.search(r"\bDP\s*ID[:\s]*([A-Z0-9]+)", line_text, re.I)
            if m:
                set_field("dp_id", m.group(1), line_text, conf)
        if "client_id" in out and out["client_id"]["value"] is None:
            m = re.search(r"\bClient\s*ID[:\s]*([A-Z0-9]+)", line_text, re.I)
            if m:
                set_field("client_id", m.group(1), line_text, conf)
        if "policy_number" in out and out["policy_number"]["value"] is None:
            m = re.search(r"policy\s*(?:no|number)[.\s:]*([A-Z0-9/-]+)", line_text, re.I)
            if m:
                set_field("policy_number", m.group(1), line_text, conf)
        if "fir_number" in out and out["fir_number"]["value"] is None:
            m = re.search(r"\bFIR\s*(?:no|number)[.\s:]*([A-Z0-9/-]+)", line_text, re.I)
            if m:
                set_field("fir_number", m.group(1), line_text, conf)

    # Names: fall back to the line right after a name-label line, only for the
    # FIRST name-like schema field. Prefer null over a wrong guess.
    HEADER_WORDS = (
        "tax", "department", "government", "govt", "authority", "certificate",
        "board", "corporation", "ministry", "commission", "bank", "declaration",
        "statement", "synthetic", "test", "prototype", "republic", "unique",
        "identification", "income", "education", "insurance", "company pvt",
    )
    primary_name_field = next((f for f in out if f.endswith("name")), None)
    if primary_name_field and out[primary_name_field]["value"] is None:
        name_labels = FIELD_LABELS.get(primary_name_field, ())
        for idx, line in enumerate(lines[:-1]):
            if any(lbl.lower() in line.lower() for lbl in name_labels):
                nxt = lines[idx + 1].strip()
                if (
                    nxt
                    and 5 <= len(nxt) <= 60
                    and ":" not in nxt
                    and not RE_DATE.search(nxt)
                    and not any(w in nxt.lower() for w in HEADER_WORDS)
                ):
                    set_field(primary_name_field, nxt, nxt, None)
                    break

    return out


def mask_sensitive(doc_type: str, fields: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Mask sensitive identifiers in the returned (displayed/stored) data."""
    masked = {k: dict(v) for k, v in fields.items()}

    def mask_doc_id(value: Optional[str], kind: str) -> Optional[str]:
        if not value:
            return value
        if kind == "AADHAAR_LIKE":
            digits = re.sub(r"\D", "", value)
            if len(digits) >= 4:
                return "*!*!* " * 0 + "XXXX XXXX " + digits[-4:]
            return "XXXX XXXX XXXX"
        if kind == "PAN_LIKE":
            return value[:5] + "XX" + value[7:] if len(value) == 10 else "XXXXXXXX" + value[-2:]
        if kind == "PASSPORT":
            return value[:1] + "XXXXXXX"[-len(value) + 1:] if len(value) == 8 else "X" * len(value)
        if kind in {"VOTER_ID"}:
            return value[:2] + "X" * max(len(value) - 2, 0)
        if kind in {"OTHER_ID", "DRIVING_LICENCE"}:
            return value if kind == "DRIVING_LICENCE" else value[:2] + "X" * max(len(value) - 2, 0)
        return value

    if doc_type in {"AADHAAR_LIKE", "PAN_LIKE", "PASSPORT", "VOTER_ID", "DRIVING_LICENCE", "OTHER_ID"}:
        f = "document_identifier"
        if masked.get(f, {}).get("value"):
            masked[f]["value"] = mask_doc_id(masked[f]["value"], doc_type)
    if doc_type == "ITR":
        f = "pan_identifier"
        if masked.get(f, {}).get("value"):
            v = masked[f]["value"]
            masked[f]["value"] = (v[:5] + "X" + v[-2:]) if len(v) == 10 else v
    # account numbers
    for f in ("account_number",):
        if masked.get(f, {}).get("value"):
            v = re.sub(r"\D", "", str(masked[f]["value"]))
            if len(v) >= 4:
                masked[f]["value"] = "XXXX XXXX " + v[-4:]
    return masked


def process_scan_result(
    ocr_result: Optional[Dict[str, Any]],
    expected_document_id: str,
) -> Dict[str, Any]:
    """
    Full pipeline from OCR output to classification + extraction + masking.
    Returns a per-scan result dict (no raw OCR text beyond lines metadata).
    """
    if ocr_result is None:
        return {
            "ocr_available": False,
            "extraction_status": "OCR_UNAVAILABLE",
            "classification": {
                "expected_type": DOC_TYPE_BY_DOCUMENT_ID.get(expected_document_id, "UNKNOWN"),
                "detected_type": None,
                "match": "UNKNOWN",
                "evidence": [],
            },
            "fields": {},
            "languages_used": [],
            "message": "OCR engine is not available on this machine. "
                       "Document saved for review; text extraction could not be performed.",
        }

    full_text = ocr_result["text"]
    lines = ocr_result["lines"]
    classification = classify_document(full_text, expected_document_id)

    detected_type = classification["detected_type"]
    doc_type = detected_type if detected_type in EXTRACTION_SCHEMAS else \
        DOC_TYPE_BY_DOCUMENT_ID.get(expected_document_id, "OTHER_ID")

    fields = extract_fields(doc_type, lines, full_text)
    fields = mask_sensitive(doc_type, fields)

    filled = sum(1 for v in fields.values() if v["value"] is not None)
    if not full_text.strip():
        extraction_status = "EMPTY_OCR"
    elif filled == 0:
        extraction_status = "PARTIAL"
    else:
        extraction_status = "SUCCESS"

    return {
        "ocr_available": True,
        "engine": ocr_result["engine"],
        "languages_used": ocr_result["languages_used"],
        "ocr_confidence": ocr_result["confidence"],
        "extraction_status": extraction_status,
        "classification": classification,
        "doc_type": doc_type,
        "fields": fields,
    }
