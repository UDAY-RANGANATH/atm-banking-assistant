"""
Form Engine for Intelligent Application Form Autofill (Phase 5).

Reusable form configuration system:
  - FORM_FIELD_TYPES: canonical application form fields with multilingual
    labels (EN/TE/HI), input types, validation patterns and sensitive flags.
  - SERVICE_FORM_SCHEMAS: per-category base field sets + per-service
    overrides. All 59 services get a relevant form without 59 bespoke
    implementations.
  - FIELD_MAPPINGS: OCR extraction field keys per document type -> canonical
    form fields (e.g. PAN name -> Applicant Name, PAN identifier -> PAN
    Number, salary net -> Monthly Income, statement account holder ->
    Account Holder Name, IFSC -> IFSC Code).

Mapping rules:
  - A value is never invented: a form field is only populated from an actual
    extracted value of a scanned document.
  - Uncertain or unrelated values are never used: only fields registered in
    FIELD_MAPPINGS can populate form fields; low-confidence values are
    flagged LOW_CONFIDENCE and require customer review.
  - Extracted personal data (names, addresses, identifiers) is preserved
    untranslated and displayed exactly as printed (masked for identifiers).
"""

import re
from typing import Dict, Any, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Canonical form field types
# ---------------------------------------------------------------------------
# key: definition
#   label: {en, te, hi}
#   type: text | date | select | number | masked
#   sensitive: shown/stored masked at all times
#   pattern: optional validation regex (prototype-level validation)
#   options: for select fields
#   mandatory_default: included by default in category schemas

FORM_FIELD_TYPES: Dict[str, Dict[str, Any]] = {
    "applicant_name": {
        "label": {"en": "Applicant Name", "te": "దరఖాస్తుదారు పేరు", "hi": "आवेदक का नाम"},
        "type": "text",
        "sensitive": False,
        "pattern": r".{3,80}",
    },
    "fathers_name": {
        "label": {"en": "Father's Name", "te": "తండ్రి పేరు", "hi": "पिता का नाम"},
        "type": "text",
        "sensitive": False,
    },
    "mothers_name": {
        "label": {"en": "Mother's Name", "te": "తల్లి పేరు", "hi": "माता का नाम"},
        "type": "text",
        "sensitive": False,
    },
    "date_of_birth": {
        "label": {"en": "Date of Birth", "te": "జన్మ తేదీ", "hi": "जन्म तिथि"},
        "type": "date",
        "sensitive": False,
        "pattern": r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}",
    },
    "gender": {
        "label": {"en": "Gender", "te": "లింగం", "hi": "लिंग"},
        "type": "select",
        "options": ["male", "female", "other"],
        "sensitive": False,
    },
    "nationality": {
        "label": {"en": "Nationality", "te": "జాతీయత", "hi": "राष्ट्रीयता"},
        "type": "text",
        "sensitive": False,
    },
    "residential_address": {
        "label": {"en": "Residential Address", "te": "నివాస చిరునామా", "hi": "आवासीय पता"},
        "type": "text",
        "sensitive": False,
    },
    "permanent_address": {
        "label": {"en": "Permanent Address", "te": "శాశ్వత చిరునామా", "hi": "स्थायी पता"},
        "type": "text",
        "sensitive": False,
    },
    "pincode": {
        "label": {"en": "PIN Code", "te": "పిన్ కోడ్", "hi": "पिन कोड"},
        "type": "text",
        "pattern": r"\d{6}",
        "sensitive": False,
    },
    "mobile_number": {
        "label": {"en": "Mobile Number", "te": "మొబైల్ నంబర్", "hi": "मोबाइल नंबर"},
        "type": "text",
        "pattern": r"[6-9]\d{9}",
        "sensitive": False,
    },
    "email": {
        "label": {"en": "Email Address", "te": "ఇమెయిల్", "hi": "ईमेल पता"},
        "type": "text",
        "pattern": r"[^@\s]+@[^@\s]+\.[^@\s]+",
        "sensitive": False,
    },
    "occupation": {
        "label": {"en": "Occupation", "te": "వృత్తి", "hi": "व्यवसाय"},
        "type": "text",
        "sensitive": False,
    },
    "employer_name": {
        "label": {"en": "Employer Name", "te": "యజమాని పేరు", "hi": "नियोक्ता का नाम"},
        "type": "text",
        "sensitive": False,
    },
    "monthly_income": {
        "label": {"en": "Monthly Income", "te": "నెలవారీ ఆదాయం", "hi": "मासिक आय"},
        "type": "number",
        "sensitive": False,
    },
    "annual_income": {
        "label": {"en": "Annual Income", "te": "వార్షిక ఆదాయం", "hi": "वार्षिक आय"},
        "type": "number",
        "sensitive": False,
    },
    "source_of_income": {
        "label": {"en": "Source of Income", "te": "ఆదాయ మూలం", "hi": "आय का स्रोत"},
        "type": "select",
        "options": ["salary", "business", "agriculture", "pension", "other"],
        "sensitive": False,
    },
    "pan_number": {
        "label": {"en": "PAN Number", "te": "పాన్ నంబర్", "hi": "पैन नंबर"},
        "type": "masked",
        "pattern": r"[A-Z]{3}\d{4}[A-Z]|\w*XX\w*",
        "sensitive": True,
    },
    "aadhaar_number": {
        "label": {"en": "Aadhaar Number (masked)", "te": "ఆధార్ నంబర్ (మాస్క్డ్)", "hi": "आधार नंबर (मास्क)"},
        "type": "masked",
        "pattern": r"X{4} ?X{4} ?\d{4}",
        "sensitive": True,
    },
    "passport_number": {
        "label": {"en": "Passport Number", "te": "పాస్‌పోర్ట్ నంబర్", "hi": "पासपोर्ट नंबर"},
        "type": "masked",
        "sensitive": True,
    },
    "bank_name": {
        "label": {"en": "Bank Name", "te": "బ్యాంక్ పేరు", "hi": "बैंक का नाम"},
        "type": "text",
        "sensitive": False,
    },
    "account_holder_name": {
        "label": {"en": "Account Holder Name", "te": "ఖాతాదారు పేరు", "hi": "खाताधारक का नाम"},
        "type": "text",
        "sensitive": False,
    },
    "account_number": {
        "label": {"en": "Account Number (masked)", "te": "ఖాతా నంబర్ (మాస్క్డ్)", "hi": "खाता नंबर (मास्क)"},
        "type": "masked",
        "sensitive": True,
    },
    "ifsc_code": {
        "label": {"en": "IFSC Code", "te": "IFSC కోడ్", "hi": "IFSC कोड"},
        "type": "text",
        "pattern": r"[A-Z]{4}0[A-Z0-9]{6}",
        "sensitive": False,
    },
    "loan_amount": {
        "label": {"en": "Loan Amount Requested", "te": "కోరిన రుణ మొత్తం", "hi": "अनुरोधित ऋण राशि"},
        "type": "number",
        "sensitive": False,
    },
    "loan_purpose": {
        "label": {"en": "Purpose of Loan", "te": "రుణ ప్రయోజనం", "hi": "ऋण का उद्देश्य"},
        "type": "text",
        "sensitive": False,
    },
    "nominee_name": {
        "label": {"en": "Nominee Name", "te": "నామినీ పేరు", "hi": "नामांकित व्यक्ति का नाम"},
        "type": "text",
        "sensitive": False,
    },
    "nominee_relation": {
        "label": {"en": "Nominee Relationship", "te": "నామినీ సంబంధం", "hi": "नामित व्यक्ति संबंध"},
        "type": "select",
        "options": ["spouse", "son", "daughter", "father", "mother", "other"],
        "sensitive": False,
    },
    "card_requested": {
        "label": {"en": "Card Type Requested", "te": "కోరిన కార్డ్ రకం", "hi": "अनुरोधित कार्ड प्रकार"},
        "type": "select",
        "options": ["debit", "credit", "both"],
        "sensitive": False,
    },
    "business_name": {
        "label": {"en": "Business / Firm Name", "te": "వ్యాపార / సంస్థ పేరు", "hi": "व्यवसाय / फर्म का नाम"},
        "type": "text",
        "sensitive": False,
    },
    "gstin": {
        "label": {"en": "GSTIN", "te": "GSTIN", "hi": "GSTIN"},
        "type": "text",
        "pattern": r"\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9][A-Z0-9A-Z]{3}[A-Z0-9]",
        "sensitive": False,
    },
    "cheque_number": {
        "label": {"en": "Cheque Number", "te": "చెక్ నంబర్", "hi": "चेक नंबर"},
        "type": "text",
        "sensitive": False,
    },
    "amount": {
        "label": {"en": "Amount", "te": "మొత్తం", "hi": "राशि"},
        "type": "number",
        "sensitive": False,
    },
    "denomination_preference": {
        "label": {"en": "Cash Denomination Preference", "te": "నగదు విభజన ప్రాధాన్యత", "hi": "नकद मूल्यवर्ग प्राथमिकता"},
        "type": "text",
        "sensitive": False,
    },
    "address_proof_type": {
        "label": {"en": "Address Proof Type", "te": "చిరునామా సాక్ష్య రకం", "hi": "पता प्रमाण प्रकार"},
        "type": "select",
        "options": ["utility bill", "rent agreement", "bank statement", "aadhaar"],
        "sensitive": False,
    },
}

# ---------------------------------------------------------------------------
# Service form schemas
# ---------------------------------------------------------------------------
# Base schemas per service category + per-service overrides. Only field keys
# from FORM_FIELD_TYPES may appear. Every one of the 59 services gets a form
# without 59 separate implementations.

CATEGORY_BASE_SCHEMAS: Dict[str, List[str]] = {
    # Service-id prefixes observed across the 59 services:
    # acc, kyc, card, cheq, cash, dd, neft, rtgs, imps, loan, scheme, ins, inv
    "acc": [
        "applicant_name", "fathers_name", "date_of_birth", "gender",
        "residential_address", "pincode", "mobile_number", "email",
        "occupation", "annual_income", "source_of_income",
    ],
    "kyc": [
        "applicant_name", "date_of_birth", "gender",
        "residential_address", "pincode", "mobile_number", "email",
        "occupation", "annual_income", "source_of_income",
        "pan_number", "aadhaar_number",
    ],
    "card": [
        "applicant_name", "date_of_birth", "mobile_number", "residential_address",
        "pan_number", "occupation", "monthly_income", "card_requested",
    ],
    "cheq": [
        "account_holder_name", "account_number", "bank_name", "ifsc_code",
        "mobile_number", "date_of_birth",
    ],
    "cash": ["account_holder_name", "account_number", "amount"],
    "dd": ["applicant_name", "residential_address", "bank_name", "ifsc_code"],
    "neft": ["account_holder_name", "account_number", "ifsc_code", "bank_name"],
    "rtgs": ["account_holder_name", "account_number", "ifsc_code", "bank_name"],
    "imps": ["account_holder_name", "mobile_number", "ifsc_code"],
    "loan": [
        "applicant_name", "fathers_name", "date_of_birth", "residential_address",
        "mobile_number", "occupation", "employer_name", "monthly_income",
        "annual_income", "loan_amount", "loan_purpose", "nominee_name",
    ],
    "scheme": [
        "applicant_name", "date_of_birth", "gender", "residential_address",
        "annual_income", "mobile_number",
    ],
    "ins": [
        "applicant_name", "date_of_birth", "gender", "mobile_number", "email",
        "nominee_name", "nominee_relation", "annual_income",
    ],
    "inv": [
        "applicant_name", "date_of_birth", "mobile_number", "email", "pan_number",
        "annual_income", "bank_name", "account_number", "nominee_name",
    ],
}

# Per-service adjustments (field: None removes a base field; key adds it).
# Only FORM_FIELD_TYPES keys and preset strings for select fields are valid.
SERVICE_FORM_OVERRIDES: Dict[str, Dict[str, Optional[Any]]] = {
    # Pension accounts do not collect occupation / income source
    "acc-014": {"occupation": None, "source_of_income": None},
    # Card replacement / block services do not need income details
    # (ids are added in tests; unknown ids simply keep the base schema).
}

# Special handling: fields that services map from "amount" wording
# (cash/deposit/other one-off fields use 'amount' -> translate to a concrete
# canonical key at render time using the service's own label).


def get_service_fields(service_id: str) -> List[str]:
    """
    Resolve the ordered form field list for one of the 59 services.
    Unknown services fall back to the generic account schema minus nothing.
    """
    prefix = service_id.split("-")[0] if "-" in service_id else service_id
    base = list(CATEGORY_BASE_SCHEMAS.get(prefix, CATEGORY_BASE_SCHEMAS["acc"]))
    override = SERVICE_FORM_OVERRIDES.get(service_id, {})
    for key, val in override.items():
        if val is None:
            if key in base:
                base.remove(key)
        elif isinstance(val, str) and key in base:
            # e.g. preset an option value; keep field in the list
            continue
        else:
            base.append(key)
    # de-dup while preserving order
    seen = set()
    ordered: List[str] = []
    for k in base:
        if k not in seen and k in FORM_FIELD_TYPES:
            seen.add(k)
            ordered.append(k)
    return ordered


# ---------------------------------------------------------------------------
# OCR -> form field mappings
# ---------------------------------------------------------------------------
# A mapping rule describes how an extracted document field feeds a form field.
# source: doc type used by extraction.py schemas (or "<any>" fallback)
# Values are structured so a single registry drives API introspection too.

FIELD_MAPPINGS: List[Dict[str, Any]] = [
    # --- PAN documents -------------------------------------------------------
    {"doc_type": "PAN_LIKE", "doc_field": "full_name", "form_field": "applicant_name"},
    {"doc_type": "PAN_LIKE", "doc_field": "fathers_name", "form_field": "fathers_name"},
    {"doc_type": "PAN_LIKE", "doc_field": "date_of_birth", "form_field": "date_of_birth"},
    {"doc_type": "PAN_LIKE", "doc_field": "document_identifier", "form_field": "pan_number"},
    # --- Aadhaar-like documents (incl. address proof) ------------------------
    {"doc_type": "AADHAAR_LIKE", "doc_field": "full_name", "form_field": "applicant_name"},
    {"doc_type": "AADHAAR_LIKE", "doc_field": "date_of_birth", "form_field": "date_of_birth"},
    {"doc_type": "AADHAAR_LIKE", "doc_field": "gender", "form_field": "gender"},
    {"doc_type": "AADHAAR_LIKE", "doc_field": "address", "form_field": "residential_address"},
    {"doc_type": "AADHAAR_LIKE", "doc_field": "document_identifier", "form_field": "aadhaar_number"},
    # --- Salary slip ---------------------------------------------------------
    {"doc_type": "SALARY_SLIP", "doc_field": "employee_name", "form_field": "applicant_name"},
    {"doc_type": "SALARY_SLIP", "doc_field": "employer", "form_field": "employer_name"},
    {"doc_type": "SALARY_SLIP", "doc_field": "net_salary", "form_field": "monthly_income"},
    {"doc_type": "SALARY_SLIP", "doc_field": "basic_salary", "form_field": "monthly_income",
     "note": "fallback income source"},
    # --- Bank statement ------------------------------------------------------
    {"doc_type": "BANK_STATEMENT", "doc_field": "account_holder", "form_field": "account_holder_name"},
    {"doc_type": "BANK_STATEMENT", "doc_field": "account_holder", "form_field": "applicant_name"},
    {"doc_type": "BANK_STATEMENT", "doc_field": "account_number", "form_field": "account_number"},
    {"doc_type": "BANK_STATEMENT", "doc_field": "bank_name", "form_field": "bank_name"},
    {"doc_type": "BANK_STATEMENT", "doc_field": "ifsc", "form_field": "ifsc_code"},
    # --- Utility bill (address / name proof) ---------------------------------
    {"doc_type": "UTILITY_BILL", "doc_field": "consumer_name", "form_field": "applicant_name"},
    {"doc_type": "UTILITY_BILL", "doc_field": "address", "form_field": "residential_address"},
    # --- Rent agreement ------------------------------------------------------
    {"doc_type": "RENT_AGREEMENT", "doc_field": "tenant_name", "form_field": "applicant_name"},
    {"doc_type": "RENT_AGREEMENT", "doc_field": "address", "form_field": "residential_address"},
    # --- Income / employment certificates ------------------------------------
    {"doc_type": "INCOME_CERTIFICATE", "doc_field": "full_name", "form_field": "applicant_name"},
    {"doc_type": "INCOME_CERTIFICATE", "doc_field": "annual_income", "form_field": "annual_income"},
    {"doc_type": "EMPLOYMENT_CERTIFICATE", "doc_field": "employee_name", "form_field": "applicant_name"},
    {"doc_type": "EMPLOYMENT_CERTIFICATE", "doc_field": "employer", "form_field": "employer_name"},
    # --- ITR ------------------------------------------------------------------
    {"doc_type": "ITR", "doc_field": "full_name", "form_field": "applicant_name"},
    {"doc_type": "ITR", "doc_field": "total_income", "form_field": "annual_income"},
    {"doc_type": "ITR", "doc_field": "pan_identifier", "form_field": "pan_number"},
    # --- Birth certificate ----------------------------------------------------
    {"doc_type": "BIRTH_CERTIFICATE", "doc_field": "child_name", "form_field": "applicant_name"},
    {"doc_type": "BIRTH_CERTIFICATE", "doc_field": "date_of_birth", "form_field": "date_of_birth"},
    # --- Passports / voter ids / driving licences ------------------------------
    {"doc_type": "PASSPORT", "doc_field": "full_name", "form_field": "applicant_name"},
    {"doc_type": "PASSPORT", "doc_field": "date_of_birth", "form_field": "date_of_birth"},
    {"doc_type": "PASSPORT", "doc_field": "nationality", "form_field": "nationality"},
    {"doc_type": "PASSPORT", "doc_field": "document_identifier", "form_field": "passport_number"},
    {"doc_type": "VOTER_ID", "doc_field": "full_name", "form_field": "applicant_name"},
    {"doc_type": "VOTER_ID", "doc_field": "fathers_name", "form_field": "fathers_name"},
    {"doc_type": "VOTER_ID", "doc_field": "date_of_birth", "form_field": "date_of_birth"},
    {"doc_type": "DRIVING_LICENCE", "doc_field": "full_name", "form_field": "applicant_name"},
    {"doc_type": "DRIVING_LICENCE", "doc_field": "address", "form_field": "residential_address"},
    {"doc_type": "DRIVING_LICENCE", "doc_field": "date_of_birth", "form_field": "date_of_birth"},
    # --- Business documents ------------------------------------------------------
    {"doc_type": "GST_REGISTRATION", "doc_field": "business_name", "form_field": "business_name"},
    {"doc_type": "GST_REGISTRATION", "doc_field": "gstin", "form_field": "gstin"},
    {"doc_type": "BUSINESS_REGISTRATION", "doc_field": "business_name", "form_field": "business_name"},
    {"doc_type": "INCORPORATION_DOCUMENT", "doc_field": "company_name", "form_field": "business_name"},
    # --- Other name-bearing documents ---------------------------------------
    {"doc_type": "OTHER_ID", "doc_field": "full_name", "form_field": "applicant_name"},
    {"doc_type": "DECLARATION_FORM", "doc_field": "declarant_name", "form_field": "applicant_name"},
    {"doc_type": "INSURANCE_POLICY", "doc_field": "policyholder_name", "form_field": "applicant_name"},
    {"doc_type": "CLAIM_DOCUMENTS", "doc_field": "claimant_name", "form_field": "applicant_name"},
    {"doc_type": "POLICE_REPORT", "doc_field": "complainant_name", "form_field": "applicant_name"},
    {"doc_type": "MEDICAL_CERTIFICATE", "doc_field": "patient_name", "form_field": "applicant_name"},
    {"doc_type": "PROPERTY_DOCUMENT", "doc_field": "owner_name", "form_field": "applicant_name"},
    {"doc_type": "SALE_AGREEMENT", "doc_field": "buyer_name", "form_field": "applicant_name"},
    {"doc_type": "DEMAT_DOCUMENTS", "doc_field": "account_holder", "form_field": "account_holder_name"},
]

# Minimal trustworthy source for each mapping above is enforced by the caller:
# only confirmed/readable scan results with real values are considered.


def mappings_for_doc_type(doc_type: Optional[str]) -> List[Dict[str, Any]]:
    """All mapping rules relevant for a doc type ('<any>' matches every rule)."""
    if doc_type is None:
        return list(FIELD_MAPPINGS)
    return [m for m in FIELD_MAPPINGS if m["doc_type"] == doc_type or doc_type == "<any>"]


# ---------------------------------------------------------------------------
# Status model
# ---------------------------------------------------------------------------

FIELD_STATUSES = (
    "AUTO_FILLED",        # populated from a confident extraction
    "LOW_CONFIDENCE",     # populated but below threshold - requires review
    "CONFLICT",           # multiple documents disagree - requires review
    "MISSING",            # nothing to fill - customer may type a value
    "CUSTOMER_EDITED",    # customer typed/corrected before confirming
    "CUSTOMER_CONFIRMED", # customer explicitly approved the value
)

LOW_CONFIDENCE_THRESHOLD = 60.0


def status_from_confidence(confidence: Optional[float]) -> str:
    if confidence is None:
        return "LOW_CONFIDENCE"  # no reliable confidence - needs review
    return "LOW_CONFIDENCE" if confidence < LOW_CONFIDENCE_THRESHOLD else "AUTO_FILLED"


# ---------------------------------------------------------------------------
# Validation (prototype level)
# ---------------------------------------------------------------------------

_RE_CACHE: Dict[str, re.Pattern] = {}


def validate_field_value(form_field: str, value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a value against the field's pattern.
    Returns (ok, error_key). error keys are i18n keys on the frontend.
    Personal data itself is never echoed into error logs.
    """
    definition = FORM_FIELD_TYPES.get(form_field)
    if not definition:
        return False, "errors.unknownField"
    pattern = definition.get("pattern")
    if pattern and value:
        compiled = _RE_CACHE.setdefault(pattern, re.compile(pattern))
        if not compiled.fullmatch(value.strip()):
            return False, f"pattern.{form_field}"
    return True, None
