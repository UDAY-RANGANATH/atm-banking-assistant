"""
Document Requirement Engine - Centralized Document Configuration

This module defines:
1. Reusable document definitions (organized by categories A-H)
2. Service-to-document mappings (which documents each service requires)
3. Conditional rules (when a document becomes mandatory/optional/not applicable)
4. Multilingual document names, descriptions, and purposes

IMPORTANT: These are PROTOTYPE document requirements for educational purposes.
They are based on general banking practices and RBI/UIDAI guidance references,
but are not official HDFC Bank requirements. Prototype assumptions are clearly
marked where official requirements cannot be established.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from enum import Enum


class DocumentCategory(str, Enum):
    IDENTITY = "A"
    ADDRESS = "B"
    FINANCIAL = "C"
    EDUCATIONAL = "D"
    PHOTO_SIGNATURE = "E"
    PROPERTY_ASSET = "F"
    BUSINESS = "G"
    INSURANCE_INVESTMENT = "H"


class DocumentRequirementStatus(str, Enum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    READABLE = "readable"
    NEEDS_RESCAN = "needs_rescan"
    OPTIONAL = "optional"
    NOT_APPLICABLE = "not_applicable"


class DocumentDefinition(BaseModel):
    """Reusable document definition - defines what a document is, globally."""

    id: str
    category: str  # A-H
    name: Dict[str, str]  # {en, te, hi}
    description: Dict[str, str]
    purpose: Dict[str, str]  # Why this document is needed generally
    extracted_fields: List[str]
    alternatives: List[str] = []  # Alternative document IDs
    validation_requirements: List[str] = []
    is_sensitive: bool = False  # Whether it contains highly sensitive data (e.g., Aadhaar number)


class ServiceDocumentMapping(BaseModel):
    """Maps a specific document to a specific service with service-specific classification."""

    service_id: str
    document_id: str
    mandatory: bool  # True = must be provided
    conditional: bool = False  # True = only under certain conditions
    conditional_reason: Optional[str] = None  # Why this is conditional
    service_specific_purpose: Optional[Dict[str, str]] = None  # Override general purpose
    alternatives: List[str] = []  # Service-specific alternative document IDs
    notes: Optional[str] = None


class DocumentChecklistItem(BaseModel):
    """A document requirement for a specific service, resolved and ready for UI."""

    document_id: str
    name: str
    category: str
    description: str
    purpose: str
    mandatory: bool
    conditional: bool
    conditional_reason: Optional[str]
    extracted_fields: List[str]
    alternatives: List[str]
    status: DocumentRequirementStatus = DocumentRequirementStatus.PENDING
    scanned_at: Optional[str] = None
    ocr_confidence: Optional[float] = None


class DocumentChecklist(BaseModel):
    """Complete document checklist for a service."""

    service_id: str
    service_name: str
    form_number: str
    documents: List[DocumentChecklistItem]
    total_required: int
    total_optional: int
    total_conditional: int


class ChecklistUpdate(BaseModel):
    """Request to update a document's status in a checklist."""

    application_id: str
    document_id: str
    status: DocumentRequirementStatus
    scanned_at: Optional[str] = None
    ocr_confidence: Optional[float] = None


class ChecklistProgress(BaseModel):
    """Progress summary for a checklist."""

    application_id: str
    service_id: str
    total_documents: int
    completed: int
    pending: int
    optional: int
    not_applicable: int
    needs_rescan: int
    percentage: float
    all_mandatory_complete: bool


# ============================================================================
# DOCUMENT CATALOGUE - Reusable Document Definitions
# ============================================================================

DOCUMENT_CATALOGUE: Dict[str, DocumentDefinition] = {

    # ------------------------------------------------------------------
    # CATEGORY A: Identity Proof
    # ------------------------------------------------------------------
    "doc-aadhaar": DocumentDefinition(
        id="doc-aadhaar",
        category="A",
        name={
            "en": "Aadhaar Card",
            "te": "ఆధార్ కార్డు",
            "hi": "आधार कार्ड",
        },
        description={
            "en": "Government-issued identity card with biometric and demographic details.",
            "te": "భారतीय సరકારీrodyAM ఇంటర్నేషనల్ గుర్తిణీకార్డు.",
            "hi": "सरकार द्वारा जारी पहचान पत्र जिसमें बायोमीट्रिक और जनसांख्यिकीय विवरण होते हैं।",
        },
        purpose={
            "en": "Establishes the customer's identity and, where applicable, residential address.",
            "te": " గనుబ Abschnitt కోసం.",
            "hi": "ग्राहक की पहचान और, जहां लागू हो, आवासीय पता स्थापित करता है।",
        },
        extracted_fields=["full_name", "date_of_birth", "address", "gender"],
        alternatives=["doc-passport", "doc-voter-id", "doc-driving-licence"],
        validation_requirements=["Valid Aadhaar number format", "Name matches application"],
        is_sensitive=True,
    ),
    "doc-passport": DocumentDefinition(
        id="doc-passport",
        category="A",
        name={
            "en": "Passport",
            "te": "పాస్పోర్ట్",
            "hi": "पासपोर्ट",
        },
        description={
            "en": "Official travel document issued by the government certifying identity and nationality.",
            "te": "ప్రయాణాధికార పత్రం.",
            "hi": "सरकार द्वारा जारी आधिकारिक यात्रा दस्तावेज जो पहचान और राष्ट्रीयता प्रमाणित करता है।",
        },
        purpose={
            "en": "Proof of identity and nationality; accepted alternative to Aadhaar.",
            "te": "న హాలు",
            "hi": "पहचान और राष्ट्रीयता का प्रमाण; आधार का स्वीकृत विकल्प।",
        },
        extracted_fields=["full_name", "nationality", "passport_number", "date_of_birth"],
        alternatives=["doc-aadhaar", "doc-voter-id"],
        validation_requirements=["Valid passport number", "Not expired"],
        is_sensitive=False,
    ),
    "doc-voter-id": DocumentDefinition(
        id="doc-voter-id",
        category="A",
        name={
            "en": "Voter ID Card",
            "te": "వోటర్ আইడీ",
            "hi": "वोटर आईडी कार्ड",
        },
        description={
            "en": "Election Commission of India issued identity card for voters.",
            "te": "ఎన్నికల కమిషన్ జారీ గుర్త బృందం.",
            "hi": "भारत के निर्वाचन आयोग द्वारा जारी मतदाता पहचान पत्र।",
        },
        purpose={
            "en": "Accepted identity proof for Indian citizens.",
            "te": "వ zająకుండా",
            "hi": "भारतीय नागरिकों के लिए स्वीकृत पहचान प्रमाण।",
        },
        extracted_fields=["full_name", "voter_id_number", "date_of_birth"],
        alternatives=["doc-aadhaar", "doc-passport"],
        validation_requirements=["Valid Voter ID number"],
        is_sensitive=False,
    ),
    "doc-driving-licence": DocumentDefinition(
        id="doc-driving-licence",
        category="A",
        name={
            "en": "Driving Licence",
            "te": "డ్రైవింగ్ లైసెన్స్",
            "hi": "ड्राइविंग लाइसेंस",
        },
        description={
            "en": "Government-issued permit to drive motor vehicles, also serves as identity proof.",
            "te": "వాహనాలు నడపడానికి అనుమతి పత్రం.",
            "hi": "मोटर वाहन चलाने के लिए सरकार द्वारा जारी अनुमति पत्र, पहचान प्रमाण के रूप में भी काम करता है।",
        },
        purpose={
            "en": "Accepted identity and age proof.",
            "te": "హarrollo",
            "hi": "स्वीकृत पहचान और आयु प्रमाण।",
        },
        extracted_fields=["full_name", "licence_number", "date_of_birth", "address"],
        alternatives=["doc-aadhaar", "doc-passport"],
        validation_requirements=["Valid licence number", "Not expired"],
        is_sensitive=False,
    ),
    "doc-other-id": DocumentDefinition(
        id="doc-other-id",
        category="A",
        name={
            "en": "Other Officially Accepted Identity Document",
            "te": "ఇతర atteint గుర్త>",
            "hi": "अन्य आधिकारिक रूप से स्वीकृत पहचान दस्तावेज",
        },
        description={
            "en": "Any other government-approved identity document not listed above.",
            "te": "మర共和国",
            "hi": "ऊपर सूचीबद्ध किए गए अलावा कोई भी अन्य सरकार द्वारा अनुमोदित पहचान दस्तावेज।",
        },
        purpose={
            "en": "Identity proof when standard documents are not available.",
            "te": "ఎ何が",
            "hi": "मानक दस्तावेज उपलब्ध न होने पर पहचान प्रमाण।",
        },
        extracted_fields=["full_name", "document_number"],
        alternatives=[],
        validation_requirements=["Government-issued", "Valid and not expired"],
        is_sensitive=False,
    ),

    # ------------------------------------------------------------------
    # CATEGORY B: Address Proof
    # ------------------------------------------------------------------
    "doc-utility-bill": DocumentDefinition(
        id="doc-utility-bill",
        category="B",
        name={
            "en": "Utility Bill",
            "te": "వమచే Rússia",
            "hi": "यूटिलिटी बिल",
        },
        description={
            "en": "Recent electricity, water, gas, or telephone bill in the customer's name.",
            "te": " కాంతరిన్",
            "hi": "ग्राहक के नाम पर हाल का बिजली, पानी, गैस या टेलीफोन बिल।",
        },
        purpose={
            "en": "Verifies the customer's current residential address.",
            "te": "డ scientia",
            "hi": "ग्राहक के वर्तमान आवासीय पते का सत्यापन करता है।",
        },
        extracted_fields=["address", "customer_name", "bill_date"],
        alternatives=["doc-bank-statement", "doc-rent-agreement"],
        validation_requirements=["Not older than 3 months", "In customer's name"],
        is_sensitive=False,
    ),
    "doc-bank-statement": DocumentDefinition(
        id="doc-bank-statement",
        category="B",
        name={
            "en": "Bank Statement",
            "te": "బ్యాంక్ స్టేట్‌మెంట్",
            "hi": "बैंक स्टेटमेंट",
        },
        description={
            "en": "Recent bank statement showing transactions and address.",
            "te": " Bank-స్టేట్‌మెంట్",
            "hi": "लेन-देन और पता दिखाने वाला हाल का बैंक स्टेटमेंट।",
        },
        purpose={
            "en": "Proof of address and financial history.",
            "te": " డیزంబర్",
            "hi": "पते और वित्तीय इतिहास का प्रमाण।",
        },
        extracted_fields=["address", "account_number", "bank_name"],
        alternatives=["doc-utility-bill", "doc-rent-agreement"],
        validation_requirements=["Not older than 3 months", "Bank stamp/seal"],
        is_sensitive=False,
    ),
    "doc-rent-agreement": DocumentDefinition(
        id="doc-rent-agreement",
        category="B",
        name={
            "en": "Rent Agreement",
            "te": "అద్ద cominciò",
            "hi": "किरायेनामा",
        },
        description={
            "en": "Registered rent agreement showing the customer's residential address.",
            "te": "ఇ syncs",
            "hi": "ग्राहक के आवासीय पते वाला पंजीकृत किरायेनामा।",
        },
        purpose={
            "en": "Proof of residential address for tenants.",
            "te": "ന 선언",
            "hi": "भाड़े पर रहने वालों के लिए आवासीय पते का प्रमाण।",
        },
        extracted_fields=["address", "landlord_name", "tenant_name", "agreement_date"],
        alternatives=["doc-utility-bill", "doc-bank-statement"],
        validation_requirements=["Registered and stamped", "Not expired"],
        is_sensitive=False,
    ),
    "doc-aadhaar-address": DocumentDefinition(
        id="doc-aadhaar-address",
        category="B",
        name={
            "en": "Aadhaar Card (as Address Proof)",
            "te": "ఆధార్ కార్డు (చిరునామా నిరూపణకಾಗಿ)",
            "hi": "आधार कार्ड (पता प्रमाण के रूप में)",
        },
        description={
            "en": "Aadhaar card used specifically as residential address proof.",
            "te": "おお田",
            "hi": "आवासीय पता प्रमाण के रूप में आधार कार्ड का उपयोग।",
        },
        purpose={
            "en": "Establishes residential address when Aadhaar is accepted for address verification.",
            "te": "డata",
            "hi": "आवासीय पता स्थापित करता है जब पता सत्यापन के लिए आधार स्वीकार किया जाता है।",
        },
        extracted_fields=["address"],
        alternatives=["doc-utility-bill", "doc-bank-statement"],
        validation_requirements=["Valid Aadhaar number", "Address clearly visible"],
        is_sensitive=True,
    ),

    # ------------------------------------------------------------------
    # CATEGORY C: Financial Documents
    # ------------------------------------------------------------------
    "doc-pan": DocumentDefinition(
        id="doc-pan",
        category="C",
        name={
            "en": "PAN Card",
            "te": "పాన్ కార్డ్",
            "hi": "पैन कार्ड",
        },
        description={
            "en": "Permanent Account Number card issued by the Income Tax Department.",
            "te": "పన్ను kbkb",
            "hi": "आयकर विभाग द्वारा जारी स्थायी खाता संख्या कार्ड।",
        },
        purpose={
            "en": "Used for tax identification and applicable financial compliance requirements.",
            "te": "زب cake",
            "hi": "कर पहचान और लागू वित्तीय अनुपालन आवश्यकताओं के लिए उपयोग किया जाता है।",
        },
        extracted_fields=["full_name", "pan_number", "date_of_birth"],
        alternatives=["doc-form60"],
        validation_requirements=["Valid PAN format", "Name matches application"],
        is_sensitive=False,
    ),
    "doc-form60": DocumentDefinition(
        id="doc-form60",
        category="C",
        name={
            "en": "Form 60 (PAN Alternative Declaration)",
            "te": "ఫారమ్ 60 (పాన్ ప్రత్యామ్నాయ గोषणాపత్రం)",
            "hi": "फॉर्म 60 (पैन वैकल्पिक घोषणा)",
        },
        description={
            "en": "Declaration form for individuals who do not have a PAN card.",
            "te": "పాన్ కార్డ్ లేకుండా వ్యక్తులకు గोषणాపత్రం.",
            "hi": "जिन व्यक्तियों के पास पैन कार्ड नहीं है, उनके लिए घोषणा पत्र।",
        },
        purpose={
            "en": "Accepted alternative to PAN for tax compliance when PAN is not available.",
            "te": "తో",
            "hi": "पैन उपलब्ध न होने पर कर अनुपालन के लिए पैन का स्वीकृत विकल्प।",
        },
        extracted_fields=["full_name", "address", "declaration_date"],
        alternatives=["doc-pan"],
        validation_requirements=["Signed declaration", "Reason for not having PAN"],
        is_sensitive=False,
    ),
    "doc-salary-slips": DocumentDefinition(
        id="doc-salary-slips",
        category="C",
        name={
            "en": "Salary Slips",
            "te": "వేతన రசీదులు",
            "hi": "वेतन पर्चियां",
        },
        description={
            "en": "Recent salary slips showing monthly income and employer details.",
            "te": "తెల్ల విధానం",
            "hi": "मासिक आय और नियोक्ता विवरण दिखाने वाले हाल के वेतन पर्चियां।",
        },
        purpose={
            "en": "Proof of regular income for loan and credit applications.",
            "te": " సిర Usuario",
            "hi": "ऋण और क्रेडिट आवेदनों के लिए नियमित आय का प्रमाण।",
        },
        extracted_fields=["monthly_income", "employer_name", "employee_name"],
        alternatives=["doc-income-certificate", "doc-itr"],
        validation_requirements=["Recent (last 3 months)", "Employer stamp"],
        is_sensitive=False,
    ),
    "doc-income-certificate": DocumentDefinition(
        id="doc-income-certificate",
        category="C",
        name={
            "en": "Income Certificate",
            "te": "ఆదాయ సర్టిఫికెట్",
            "hi": "आय प्रमाणपत्र",
        },
        description={
            "en": "Government-issued certificate certifying annual income.",
            "te": " Austin-వ Tex-మెట్ను",
            "hi": "वार्षिक आय प्रमाणित करने वाला सरकार द्वारा जारी प्रमाणपत्र।",
        },
        purpose={
            "en": "Proof of income for economically weaker sections and loan eligibility.",
            "te": "ి alarmset",
            "hi": "आर्थिक रूप से कमजोर वर्गों और ऋण पात्रता के लिए आय का प्रमाण।",
        },
        extracted_fields=["annual_income", "certificate_number", "issuing_authority"],
        alternatives=["doc-salary-slips", "doc-itr"],
        validation_requirements=["Government-issued", "Valid and current"],
        is_sensitive=False,
    ),
    "doc-itr": DocumentDefinition(
        id="doc-itr",
        category="C",
        name={
            "en": "Income Tax Return (ITR)",
            "te": "ఆదాయపన్ను రిటర్న్",
            "hi": "आयकर रिटर्न",
        },
        description={
            "en": "Filed income tax return showing declared income.",
            "te": " 펀드-సంగీతం",
            "hi": "घोषित आय दिखाने वाला दाखिल किया गया आयकर रिटर्न।",
        },
        purpose={
            "en": "Proof of income for self-employed individuals and loan applications.",
            "te": " సమсније",
            "hi": "स्व-नियोजित व्यक्तियों और ऋण आवेदनों के लिए आय का प्रमाण।",
        },
        extracted_fields=["annual_income", "assessment_year", "pan_number"],
        alternatives=["doc-salary-slips", "doc-income-certificate"],
        validation_requirements=["Filed with tax department", "Acknowledgment number"],
        is_sensitive=False,
    ),
    "doc-employment-certificate": DocumentDefinition(
        id="doc-employment-certificate",
        category="C",
        name={
            "en": "Employment Certificate",
            "te": "నియోజిక సర్టిఫికెట్",
            "hi": "रोजगार प्रमाणपत्र",
        },
        description={
            "en": "Certificate from employer confirming employment and position.",
            "te": " నియు Mainstream",
            "hi": "नियोक्ता द्वारा रोजगार और पद की पुष्टि करने वाला प्रमाणपत्र।",
        },
        purpose={
            "en": "Proof of employment for salary-based loans and overdraft facilities.",
            "te": "Lemonade",
            "hi": "वेतन-आधारित ऋण और ओवरड्राफ्ट सुविधाओं के लिए रोजगार का प्रमाण।",
        },
        extracted_fields=["employer_name", "position", "employment_date", "salary"],
        alternatives=["doc-salary-slips"],
        validation_requirements=["Employer letterhead", "Signed by authorized signatory"],
        is_sensitive=False,
    ),

    # ------------------------------------------------------------------
    # CATEGORY D: Educational Documents
    # ------------------------------------------------------------------
    "doc-10th-marksheet": DocumentDefinition(
        id="doc-10th-marksheet",
        category="D",
        name={
            "en": "10th Class Marksheet",
            "te": "10వ తరగతి మార్క్‌శీట్",
            "hi": "10वीं कक्षा मार्कशीट",
        },
        description={
            "en": "Secondary school examination marksheet showing date of birth and educational qualification.",
            "te": "సeban-વેસ્ટ-మెట్ను",
            "hi": "जन्म तिथि और शैक्षिक योग्यता दिखाने वाली माध्यमिक विद्यालय परीक्षा मार्कशीट।",
        },
        purpose={
            "en": "Age proof and educational qualification evidence.",
            "te": "诚然",
            "hi": "आयु प्रमाण और शैक्षिक योग्यता प्रमाण।",
        },
        extracted_fields=["full_name", "date_of_birth", "school_name", "year_of_passing"],
        alternatives=["doc-birth-certificate"],
        validation_requirements=["Board/University name", "Year of passing"],
        is_sensitive=False,
    ),
    "doc-12th-marksheet": DocumentDefinition(
        id="doc-12th-marksheet",
        category="D",
        name={
            "en": "12th Class Marksheet",
            "te": "12వ తరగతి మార్క్‌శీట్",
            "hi": "12वीं कक्षा मार्कशीट",
        },
        description={
            "en": "Higher secondary examination marksheet showing educational qualification.",
            "te": "న teleforce-మెట్ను",
            "hi": "शैक्षिक योग्यता दिखाने वाली उच्चतर माध्यमिक परीक्षा मार्कशीट।",
        },
        purpose={
            "en": "Educational qualification evidence for education loans.",
            "te": "న tx-వేదాంతం",
            "hi": "शिक्षा ऋणों के लिए शैक्षिक योग्यता प्रमाण।",
        },
        extracted_fields=["full_name", "school_name", "year_of_passing", "stream"],
        alternatives=["doc-graduation-certificate"],
        validation_requirements=["Board/University name", "Year of passing"],
        is_sensitive=False,
    ),
    "doc-graduation-certificate": DocumentDefinition(
        id="doc-graduation-certificate",
        category="D",
        name={
            "en": "Graduation Certificate",
            "te": "గ్రాడ్యుయేషన్ సర్టిఫికెట్",
            "hi": "स्नातक प्रमाणपत्र",
        },
        description={
            "en": "Degree certificate from a recognized university or college.",
            "te": "పేజ pbkb-సంగీతం",
            "hi": "मान्यता प्राप्त विश्वविद्यालय या कॉलेज से डिग्री प्रमाणपत्र।",
        },
        purpose={
            "en": "Higher educational qualification proof.",
            "te": "స tx-వేదాంతం",
            "hi": "उच्च शैक्षिक योग्यता प्रमाण।",
        },
        extracted_fields=["full_name", "degree", "university", "year_of_completion"],
        alternatives=["doc-12th-marksheet"],
        validation_requirements=["University name", "Degree name", "Year of completion"],
        is_sensitive=False,
    ),
    "doc-admission-letter": DocumentDefinition(
        id="doc-admission-letter",
        category="D",
        name={
            "en": "Admission Letter",
            "te": "ప్రవೇಶ pattern/",
            "hi": "प्रवेश पत्र",
        },
        description={
            "en": "Official admission letter from a recognized educational institution.",
            "te": "’université-సంగీతం",
            "hi": "मान्यता प्राप्त शैक्षणिक संस्थान से आधिकारिक प्रवेश पत्र।",
        },
        purpose={
            "en": "Proof of admission into an educational institution for education loans.",
            "te": "స్టార్-సంగీతం",
            "hi": "शिक्षा ऋणों के लिए शैक्षणिक संस्थान में प्रवेश का प्रमाण।",
        },
        extracted_fields=["institution_name", "course_name", "admission_date", "course_duration"],
        alternatives=[],
        validation_requirements=["Institution letterhead", "Signed by authorized authority"],
        is_sensitive=False,
    ),
    "doc-fee-structure": DocumentDefinition(
        id="doc-fee-structure",
        category="D",
        name={
            "en": "Educational Fee Structure",
            "te": "విద్యా ఫీ بنية/",
            "hi": "शैक्षिक शुल्क संरचना",
        },
        description={
            "en": "Document showing the fee structure of the educational course.",
            "te": "వ specific-సంగీతం",
            "hi": "शैक्षिक पाठ्यक्रम की शुल्क संरचना दिखाने वाला दस्तावेज।",
        },
        purpose={
            "en": "Estimates educational expenses for loan amount calculation.",
            "te": " ప్లేట్-సంగీతం",
            "hi": "ऋण राशि गणना के लिए शैक्षिक व्यय का अनुमान।",
        },
        extracted_fields=["total_fees", "course_name", "institution_name", "payment_schedule"],
        alternatives=[],
        validation_requirements=["Institution letterhead", "Breakdown of fees"],
        is_sensitive=False,
    ),

    # ------------------------------------------------------------------
    # CATEGORY E: Photographs and Signatures
    # ------------------------------------------------------------------
    "doc-photograph": DocumentDefinition(
        id="doc-photograph",
        category="E",
        name={
            "en": "Passport-size Photograph",
            "te": "పాస్పోర్ట్ పరిమాణం ఫోటో",
            "hi": "पासपोर्ट आकार फोटोग्राफ",
        },
        description={
            "en": "Recent passport-size color photograph of the customer.",
            "te": "పేజీ-ఫోటో",
            "hi": "ग्राहक की हाल की पासपोर्ट आकार की रंगीन फोटो।",
        },
        purpose={
            "en": "Used for customer identification and account records.",
            "te": "క",
            "hi": "ग्राहक पहचान और खाता रिकॉर्ड के लिए उपयोग किया जाता है।",
        },
        extracted_fields=[],
        alternatives=[],
        validation_requirements=["Recent (last 6 months)", "White background", "Clear face"],
        is_sensitive=False,
    ),
    "doc-signature": DocumentDefinition(
        id="doc-signature",
        category="E",
        name={
            "en": "Signature Specimen",
            "te": "సైన్ నమూనా",
            "hi": "हस्ताक्षर नमूना",
        },
        description={
            "en": "Customer's specimen signature for account records and verification.",
            "te": "క칭-సంగీతం",
            "hi": "खाता रिकॉर्ड और सत्यापन के लिए ग्राहक का हस्ताक्षर नमूना।",
        },
        purpose={
            "en": "Verifies customer's signature for cheques and account operations.",
            "te": "స tx-సంగీతం",
            "hi": "चेक और खाता संचालन के लिए ग्राहक के हस्ताक्षर का सत्यापन करता है।",
        },
        extracted_fields=[],
        alternatives=[],
        validation_requirements=["Clear signature", "On white paper", "Matches ID"],
        is_sensitive=False,
    ),

    # ------------------------------------------------------------------
    # CATEGORY F: Property and Asset Documents
    # ------------------------------------------------------------------
    "doc-property-documents": DocumentDefinition(
        id="doc-property-documents",
        category="F",
        name={
            "en": "Property Documents",
            "te": "అస్తి పత్రాలు",
            "hi": "संपत्ति दस्तावेज",
        },
        description={
            "en": "Title deed, sale deed, or ownership documents for the property.",
            "te": " tx-సంగీతం",
            "hi": "संपत्ति के लिए शीर्षक विलेख, विक्रय विलेख या स्वामित्व दस्तावेज।",
        },
        purpose={
            "en": "Proof of property ownership for home loans and mortgage-related services.",
            "te": "tx",
            "hi": "गृह ऋण और बंधक संबंधित सेवाओं के लिए संपत्ति स्वामित्व का प्रमाण।",
        },
        extracted_fields=["property_address", "owner_name", "survey_number", "area"],
        alternatives=["doc-sale-agreement"],
        validation_requirements=["Registered document", "Clear title"],
        is_sensitive=False,
    ),
    "doc-sale-agreement": DocumentDefinition(
        id="doc-sale-agreement",
        category="F",
        name={
            "en": "Sale Agreement",
            "te": "విక్రయ($(window))",
            "hi": "विक्रय समझौता",
        },
        description={
            "en": "Agreement between buyer and seller for property purchase.",
            "te": "tx-సంగీతం",
            "hi": "संपत्ति खरीद के लिए खरीदार और विक्रेता के बीच समझौता।",
        },
        purpose={
            "en": "Evidence of property transaction and agreed price.",
            "te": "tx-సంగీతం",
            "hi": "संपत्ति लेन-देन और तय की गई कीमत का प्रमाण।",
        },
        extracted_fields=["buyer_name", "seller_name", "property_address", "sale_price"],
        alternatives=["doc-property-documents"],
        validation_requirements=["Signed by both parties", "Stamp duty paid"],
        is_sensitive=False,
    ),
    "doc-property-valuation": DocumentDefinition(
        id="doc-property-valuation",
        category="F",
        name={
            "en": "Property Valuation Report",
            "te": "అస్తి విలువ నివేదిక",
            "hi": "संपत्ति मूल्यांकन रिपोर्ट",
        },
        description={
            "en": "Professional valuation report assessing the market value of the property.",
            "te": "tx-సంగీతం",
            "hi": "संपत्ति के बाजार मूल्य का आकलन करने वाला व्यावसायिक मूल्यांकन रिपोर्ट।",
        },
        purpose={
            "en": "Determines loan eligibility and amount for property-backed loans.",
            "te": "tx-సంగీతం",
            "hi": "संपत्ति-आधारित ऋणों के लिए ऋण पात्रता और राशि निर्धारित करता है।",
        },
        extracted_fields=["property_value", "valued_by", "valuation_date"],
        alternatives=[],
        validation_requirements=["Certified valuer", "Date of valuation"],
        is_sensitive=False,
    ),
    "doc-gold-documents": DocumentDefinition(
        id="doc-gold-documents",
        category="F",
        name={
            "en": "Gold-related Documents",
            "te": "బంగారు పత్రాలు",
            "hi": "सोने से संबंधित दस्तावेज",
        },
        description={
            "en": "Purchase invoice, purity certificate, or ownership proof for gold ornaments.",
            "te": "tx-సంగీతం",
            "hi": "सोने के आभूषणों के लिए खरीद चालान, शुद्धता प्रमाणपत्र या स्वामित्व प्रमाण।",
        },
        purpose={
            "en": "Proof of gold ownership and purity for gold loan applications.",
            "te": "tx-సంగీతం",
            "hi": "सोना ऋण आवेदनों के लिए सोने के स्वामित्व और शुद्धता का प्रमाण।",
        },
        extracted_fields=["gold_weight", "gold_purity", "purchase_date"],
        alternatives=[],
        validation_requirements=["Purity hallmark", "Purchase invoice"],
        is_sensitive=False,
    ),
    "doc-vehicle-quotation": DocumentDefinition(
        id="doc-vehicle-quotation",
        category="F",
        name={
            "en": "Vehicle Quotation",
            "te": "వాహన cotización/",
            "hi": "वाहन उद्धरण",
        },
        description={
            "en": "Price quotation from vehicle dealer for the vehicle to be purchased.",
            "te": "tx-సంగీతం",
            "hi": "खरीदे जाने वाले वाहन के लिए वाहन डीलर से मूल्य उद्धरण।",
        },
        purpose={
            "en": "Estimates vehicle cost for vehicle loan applications.",
            "te": "tx-సంగీతం",
            "hi": "वाहन ऋण आवेदनों के लिए वाहन लागत का अनुमान।",
        },
        extracted_fields=["vehicle_model", "vehicle_price", "dealer_name"],
        alternatives=[],
        validation_requirements=["Dealer letterhead", "Vehicle details"],
        is_sensitive=False,
    ),

    # ------------------------------------------------------------------
    # CATEGORY G: Business Documents
    # ------------------------------------------------------------------
    "doc-business-registration": DocumentDefinition(
        id="doc-business-registration",
        category="G",
        name={
            "en": "Business Registration Certificate",
            "te": "వ్యాపార నమోదు సర్టిఫికెట్",
            "hi": "व्यवसाय पंजीकरण प्रमाणपत्र",
        },
        description={
            "en": "Certificate proving the business is legally registered.",
            "te": " tx-సంగీతం",
            "hi": "व्यवसाय के कानूनी रूप से पंजीकृत होने का प्रमाण।",
        },
        purpose={
            "en": "Proof of business existence for business loans and current accounts.",
            "te": "tx-సంగీతం",
            "hi": "व्यवसाय ऋण और चालू खातों के लिए व्यवसाय अस्तित्व का प्रमाण।",
        },
        extracted_fields=["business_name", "registration_number", "registration_date"],
        alternatives=["doc-gst-registration", "doc-company-incorporation"],
        validation_requirements=["Government-issued", "Valid and current"],
        is_sensitive=False,
    ),
    "doc-gst-registration": DocumentDefinition(
        id="doc-gst-registration",
        category="G",
        name={
            "en": "GST Registration",
            "te": "జీఎஸ్టీ enregistre/",
            "hi": "जीएसटी पंजीकरण",
        },
        description={
            "en": "Goods and Services Tax registration certificate.",
            "te": " tx-సంగీతం",
            "hi": "वस्तु और सेवा कर पंजीकरण प्रमाणपत्र।",
        },
        purpose={
            "en": "Tax registration proof for business banking services.",
            "te": "tx-సంగీతం",
            "hi": "व्यवसाय बैंकिंग सेवाओं के लिए कर पंजीकरण प्रमाण।",
        },
        extracted_fields=["gstin", "business_name", "registration_date"],
        alternatives=["doc-business-registration"],
        validation_requirements=["Valid GSTIN", "Not cancelled"],
        is_sensitive=False,
    ),
    "doc-business-financials": DocumentDefinition(
        id="doc-business-financials",
        category="G",
        name={
            "en": "Business Financial Statements",
            "te": "వ్యాపార ఆర్థిక ప్ర నివేధికలు/",
            "hi": "व्यवसाय वित्तीय विवरण",
        },
        description={
            "en": "Profit and loss statement, balance sheet, and cash flow statement.",
            "te": "tx-సంగీతం",
            "hi": "लाभ-हानि विवरण, तुलन पत्र और नकद प्रवाह विवरण।",
        },
        purpose={
            "en": "Proof of business financial health for loan applications.",
            "te": "tx-సంగీతం",
            "hi": "ऋण आवेदनों के लिए व्यवसाय वित्तीय स्वास्थ्य का प्रमाण।",
        },
        extracted_fields=["annual_turnover", "net_profit", "financial_year"],
        alternatives=["doc-itr", "doc-bank-statement"],
        validation_requirements=["Chartered accountant certificate", "Audited"],
        is_sensitive=False,
    ),
    "doc-partnership-deed": DocumentDefinition(
        id="doc-partnership-deed",
        category="G",
        name={
            "en": "Partnership Deed",
            "te": "భాగідారీ lente/",
            "hi": "भागीदारी विलेख",
        },
        description={
            "en": "Legal document defining the partnership terms between partners.",
            "te": "tx-సంగీతం",
            "hi": "भागीदारों के बीच भागीदारी शर्तों को परिभाषित करने वाला कानूनी दस्तावेज।",
        },
        purpose={
            "en": "Proof of partnership structure for partnership firm accounts.",
            "te": "tx-సంగీతం",
            "hi": "भागीदारी फर्म खातों के लिए भागीदारी संरचना का प्रमाण।",
        },
        extracted_fields=["partner_names", "partnership_type", "profit_sharing_ratio"],
        alternatives=["doc-company-incorporation"],
        validation_requirements=["Registered deed", "Signed by all partners"],
        is_sensitive=False,
    ),
    "doc-company-incorporation": DocumentDefinition(
        id="doc-company-incorporation",
        category="G",
        name={
            "en": "Company Incorporation Document",
            "te": "కంపెనీ రిజిస్ట్రేషన్/",
            "hi": "कंपनी निगमन दस्तावेज",
        },
        description={
            "en": "Certificate of incorporation from Registrar of Companies.",
            "te": "tx-సంగీతం",
            "hi": "कंपनी रजिस्ट्रार से निगमन प्रमाणपत्र।",
        },
        purpose={
            "en": "Proof of company existence for corporate accounts and business loans.",
            "te": "tx-సంగీతం",
            "hi": "कॉर्पोरेट खातों और व्यवसाय ऋणों के लिए कंपनी अस्तित्व का प्रमाण।",
        },
        extracted_fields=["company_name", "cin", "incorporation_date"],
        alternatives=["doc-business-registration"],
        validation_requirements=["ROC registration", "Not dissolved"],
        is_sensitive=False,
    ),

    # ------------------------------------------------------------------
    # CATEGORY H: Insurance and Investment Documents
    # ------------------------------------------------------------------
    "doc-insurance-policy": DocumentDefinition(
        id="doc-insurance-policy",
        category="H",
        name={
            "en": "Insurance Policy Document",
            "te": "బీమా పಾಲिसీ పత్రం/",
            "hi": "बीमा पॉलिसी दस्तावेज",
        },
        description={
            "en": "Insurance policy showing coverage details and policy number.",
            "te": "tx-సంగీతం",
            "hi": "कवरेज विवरण और पॉलिसी नंबर दिखाने वाला बीमा पॉलिसी दस्तावेज।",
        },
        purpose={
            "en": "Proof of insurance coverage for insurance-related services.",
            "te": "tx-సంగీతం",
            "hi": "बीमा संबंधित सेवाओं के लिए बीमा कवरेज का प्रमाण।",
        },
        extracted_fields=["policy_number", "policy_type", "coverage_amount"],
        alternatives=[],
        validation_requirements=["Valid policy number", "Insurance company name"],
        is_sensitive=False,
    ),
    "doc-claim-documents": DocumentDefinition(
        id="doc-claim-documents",
        category="H",
        name={
            "en": "Claim-related Supporting Documents",
            "te": "క్లెయిమ్ సహాయక పత్రాలు/",
            "hi": "दावे से संबंधित सहायक दस्तावेज",
        },
        description={
            "en": "Documents supporting an insurance claim (bills, reports, certificates).",
            "te": "tx-సంగీతం",
            "hi": "बीमा दावे का समर्थन करने वाले दस्तावेज (बिल, रिपोर्ट, प्रमाणपत्र)।",
        },
        purpose={
            "en": "Evidence required to process an insurance claim.",
            "te": "tx-సంగీతం",
            "hi": "बीमा दावे को संसाधित करने के लिए आवश्यक प्रमाण।",
        },
        extracted_fields=["claim_type", "claim_amount", "incident_date"],
        alternatives=["doc-police-report", "doc-medical-certificate"],
        validation_requirements=["Related to insured event", "Dated documents"],
        is_sensitive=False,
    ),
    "doc-police-report": DocumentDefinition(
        id="doc-police-report",
        category="H",
        name={
            "en": "Police Report",
            "te": "ప offenbar/",
            "hi": "पुलिस रिपोर्ट",
        },
        description={
            "en": "Official police report for theft, loss, or accident claims.",
            "te": "tx-సంగీతం",
            "hi": "चोरी, हानि या दुर्घटना दावों के लिए आधिकारिक पुलिस रिपोर्ट।",
        },
        purpose={
            "en": "Official record of an incident for insurance claim processing.",
            "te": "tx-సంగీతం",
            "hi": "बीमा दावा संसाधन के लिए एक घटना का आधिकारिक रिकॉर्ड।",
        },
        extracted_fields=["fir_number", "incident_date", "police_station"],
        alternatives=["doc-medical-certificate"],
        validation_requirements=["FIR number", "Police station seal"],
        is_sensitive=False,
    ),
    "doc-medical-certificate": DocumentDefinition(
        id="doc-medical-certificate",
        category="H",
        name={
            "en": "Medical Certificate",
            "te": "వైద్య దస్తావేజ్/",
            "hi": "चिकित्सा प्रमाणपत्र",
        },
        description={
            "en": "Medical practitioner's certificate for health insurance claims.",
            "te": "tx-సంగీతం",
            "hi": "स्वास्थ्य बीमा दावों के लिए चिकित्सा व्यवसायी का प्रमाणपत्र।",
        },
        purpose={
            "en": "Medical evidence for health and life insurance claims.",
            "te": "tx-సంగీతం",
            "hi": "स्वास्थ्य और जीवन बीमा दावों के लिए चिकित्सा प्रमाण।",
        },
        extracted_fields=["diagnosis", "doctor_name", "hospital_name", "treatment_date"],
        alternatives=["doc-police-report"],
        validation_requirements=["Registered medical practitioner", "Hospital/clinic stamp"],
        is_sensitive=False,
    ),
    "doc-demat-documents": DocumentDefinition(
        id="doc-demat-documents",
        category="H",
        name={
            "en": "Demat-related Documentation",
            "te": "డేమాట్ పత్రాలు/",
            "hi": "डीमैट से संबंधित दस्तावेज",
        },
        description={
            "en": "Demat account details and related documentation for investment services.",
            "te": "tx-సంగీతం",
            "hi": "निवेश सेवाओं के लिए डीमैट खाता विवरण और संबंधित दस्तावेज।",
        },
        purpose={
            "en": "Proof of demat account for investment and trading applications.",
            "te": "tx-సంగీతం",
            "hi": "निवेश और ट्रेडिंग आवेदनों के लिए डीमैट खाते का प्रमाण।",
        },
        extracted_fields=["dp_id", "client_id", "depository_name"],
        alternatives=[],
        validation_requirements=["Valid DP ID", "Client ID"],
        is_sensitive=False,
    ),
    "doc-other-declaration": DocumentDefinition(
        id="doc-other-declaration",
        category="H",
        name={
            "en": "Other Service-specific Declaration",
            "te": "ఇతర సేవ-నిర్దిష్ట నిరూపణ/",
            "hi": "अन्य सेवा-विशिष्ट घोषणा",
        },
        description={
            "en": "Any additional declaration or supporting document required for a specific service.",
            "te": "tx-సంగీతం",
            "hi": "किसी विशिष्ट सेवा के लिए आवश्यक कोई अतिरिक्त घोषणा या सहायक दस्तावेज।",
        },
        purpose={
            "en": "Satisfies particular service eligibility or KYC requirements.",
            "te": "tx-సంగీతం",
            "hi": "विशेष सेवा पात्रता या केवाईसी आवश्यकताओं को पूरा करता है।",
        },
        extracted_fields=["declaration_type", "declaration_date"],
        alternatives=[],
        validation_requirements=["Signed declaration", "Service-specific format"],
        is_sensitive=False,
    ),

    # Additional supporting documents
    "doc-birth-certificate": DocumentDefinition(
        id="doc-birth-certificate",
        category="D",
        name={
            "en": "Birth Certificate",
            "te": "జన్మ ధృవీకరణ పత్రం/",
            "hi": "जन्म प्रमाणपत्र",
        },
        description={
            "en": "Official birth certificate showing date of birth and place of birth.",
            "te": "tx-సంగీతం",
            "hi": "जन्म तिथि और जन्म स्थान दिखाने वाला आधिकारिक जन्म प्रमाणपत्र।",
        },
        purpose={
            "en": "Age proof for minor accounts and age-related eligibility.",
            "te": "tx-సంగీతం",
            "hi": "नाबालिग खातों और आयु से संबंधित पात्रता के लिए आयु प्रमाण।",
        },
        extracted_fields=["full_name", "date_of_birth", "place_of_birth", "parents_names"],
        alternatives=["doc-10th-marksheet"],
        validation_requirements=["Government-issued", "Official seal"],
        is_sensitive=False,
    ),
}

# ============================================================================
# SERVICE-TO-DOCUMENT MAPPINGS
# ============================================================================

# Each mapping specifies which documents a service requires and their classification.
SERVICE_DOCUMENT_MAPPINGS: List[ServiceDocumentMapping] = [

    # =======================================================================
    # CATEGORY A: ACCOUNT SERVICES & MAINTENANCE
    # =======================================================================

    # acc-001: Savings Account Opening
    ServiceDocumentMapping(service_id="acc-001", document_id="doc-aadhaar", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Establishes customer identity and residential address.",
                                                     "te": "పేజీ-సంగీతం",
                                                     "hi": "ग्राहक की पहचान और आवासीय पता स्थापित करता है।"},
                           alternatives=["doc-passport", "doc-voter-id", "doc-driving-licence"]),
    ServiceDocumentMapping(service_id="acc-001", document_id="doc-pan", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Tax identification for account opening.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "खाता खोलने के लिए कर पहचान।"},
                           alternatives=["doc-form60"]),
    ServiceDocumentMapping(service_id="acc-001", document_id="doc-photograph", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Customer identification for account records.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "खाता रिकॉर्ड के लिए ग्राहक पहचान।"}),
    ServiceDocumentMapping(service_id="acc-001", document_id="doc-aadhaar-address", mandatory=False, conditional=True,
                           conditional_reason="Required if Aadhaar does not adequately establish residential address.",
                           service_specific_purpose={"en": "Additional address proof when needed.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "जब आवश्यक हो तो अतिरिक्त पता प्रमाण।"},
                           alternatives=["doc-utility-bill", "doc-bank-statement", "doc-rent-agreement"]),

    # acc-002: Current Account Opening
    ServiceDocumentMapping(service_id="acc-002", document_id="doc-aadhaar", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Identity and address proof for business applicant.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "व्यवसाय आवेदक के लिए पहचान और पता प्रमाण।"}),
    ServiceDocumentMapping(service_id="acc-002", document_id="doc-pan", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Tax identification for business account.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "व्यवसाय खाते के लिए कर पहचान।"}),
    ServiceDocumentMapping(service_id="acc-002", document_id="doc-business-registration", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Proof of business existence.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "व्यवसाय अस्तित्व का प्रमाण।"}),
    ServiceDocumentMapping(service_id="acc-002", document_id="doc-photograph", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Account records photograph.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "खाता रिकॉर्ड फोटो।"}),

    # acc-003: Address Change
    # acc-003: Address Change
    ServiceDocumentMapping(service_id="acc-003", document_id="doc-aadhaar-address", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "New residential address proof.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "नया आवासीय पता प्रमाण।"},
                           alternatives=["doc-utility-bill", "doc-bank-statement", "doc-rent-agreement"]),
    ServiceDocumentMapping(service_id="acc-003", document_id="doc-aadhaar", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Identity verification for address change.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "पता बदलने के लिए पहचान सत्यापन।"}),

    # acc-004: Mobile Number Update
    ServiceDocumentMapping(service_id="acc-004", document_id="doc-aadhaar", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Identity verification for mobile number change.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "मोबाइल नंबर बदलने के लिए पहचान सत्यापन।"}),

    # acc-005: Email Update
    ServiceDocumentMapping(service_id="acc-005", document_id="doc-aadhaar", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Identity verification for email change.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "ईमेल बदलने के लिए पहचान सत्यापन।"}),

    # acc-006: Signature Update
    ServiceDocumentMapping(service_id="acc-006", document_id="doc-signature", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "New signature specimen for account records.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "खाता रिकॉर्ड के लिए नया हस्ताक्षर नमूना।"}),
    ServiceDocumentMapping(service_id="acc-006", document_id="doc-aadhaar", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Identity verification for signature update.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "हस्ताक्षर अपडेट के लिए पहचान सत्यापन।"}),

    # acc-007: Non-resident Declaration
    ServiceDocumentMapping(service_id="acc-007", document_id="doc-passport", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Identity and nationality proof for NRI status.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "NRI स्थिति के लिए पहचान और राष्ट्रीयता प्रमाण।"}),
    ServiceDocumentMapping(service_id="acc-007", document_id="doc-other-id", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Overseas address proof.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "विदेशी पता प्रमाण।"}),
    ServiceDocumentMapping(service_id="acc-007", document_id="doc-other-declaration", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Non-resident status declaration.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "गैर-निवासी स्थिति घोषणा।"}),

    # acc-008: Legal Entity Information Update
    ServiceDocumentMapping(service_id="acc-008", document_id="doc-business-registration", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Legal entity registration proof.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "कानूनी इकाई पंजीकरण प्रमाण।"}),
    ServiceDocumentMapping(service_id="acc-008", document_id="doc-pan", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Entity tax identification.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "इकाई कर पहचान।"}),
    ServiceDocumentMapping(service_id="acc-008", document_id="doc-aadhaar", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Authorized signatory identity proof.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "अधिकृत हस्ताक्षरकर्ता पहचान प्रमाण।"}),

    # kyc-001: KYC Update
    ServiceDocumentMapping(service_id="kyc-001", document_id="doc-aadhaar", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Identity and address proof for KYC refresh.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "केवाईसी ताज़ा करने के लिए पहचान और पता प्रमाण।"}),
    ServiceDocumentMapping(service_id="kyc-001", document_id="doc-pan", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Tax identification for KYC compliance.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "केवाईसी अनुपालन के लिए कर पहचान।"}),

    # acc-009: Recurring Deposit Opening
    ServiceDocumentMapping(service_id="acc-009", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="acc-009", document_id="doc-pan", mandatory=True, conditional=False,
                           alternatives=["doc-form60"]),
    ServiceDocumentMapping(service_id="acc-009", document_id="doc-photograph", mandatory=True, conditional=False),

    # acc-010: Fixed Deposit Opening
    ServiceDocumentMapping(service_id="acc-010", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="acc-010", document_id="doc-pan", mandatory=True, conditional=False,
                           alternatives=["doc-form60"]),
    ServiceDocumentMapping(service_id="acc-010", document_id="doc-photograph", mandatory=True, conditional=False),

    # acc-011: Joint Account Holder Addition/Deletion
    ServiceDocumentMapping(service_id="acc-011", document_id="doc-aadhaar", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Identity proof for new joint account holder.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "नए संयुक्त खाता धारक के लिए पहचान प्रमाण।"}),
    ServiceDocumentMapping(service_id="acc-011", document_id="doc-pan", mandatory=True, conditional=False,
                           alternatives=["doc-form60"]),
    ServiceDocumentMapping(service_id="acc-011", document_id="doc-photograph", mandatory=True, conditional=False),

    # acc-012: Minor-to-Major Conversion
    ServiceDocumentMapping(service_id="acc-012", document_id="doc-10th-marksheet", mandatory=True, conditional=True,
                           conditional_reason="Required as age proof for conversion from minor to major.",
                           service_specific_purpose={"en": "Age proof for minor-to-major conversion.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "नाबालिग से वयस्क में रूपांतरण के लिए आयु प्रमाण।"}),
    ServiceDocumentMapping(service_id="acc-012", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="acc-012", document_id="doc-pan", mandatory=True, conditional=False,
                           alternatives=["doc-form60"]),
    ServiceDocumentMapping(service_id="acc-012", document_id="doc-photograph", mandatory=True, conditional=False),

    # acc-013: Branch Transfer
    ServiceDocumentMapping(service_id="acc-013", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="acc-013", document_id="doc-other-declaration", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Branch transfer request declaration.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "शाखा स्थानांतरण अनुरोध घोषणा।"}),

    # acc-014: Dormant Account Activation
    ServiceDocumentMapping(service_id="acc-014", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="acc-014", document_id="doc-other-declaration", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Dormant account activation declaration.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "सुप्त खाता सक्रियकरण घोषणा।"}),

    # acc-015: Frozen Account Activation Request
    ServiceDocumentMapping(service_id="acc-015", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="acc-015", document_id="doc-other-declaration", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Frozen account activation request declaration.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "फ्रीज किए गए खाते के सक्रियकरण अनुरोध की घोषणा।"}),

    # acc-016: Savings Account Closure
    ServiceDocumentMapping(service_id="acc-016", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="acc-016", document_id="doc-other-declaration", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Account closure request declaration.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "खाता बंद करने के अनुरोध की घोषणा।"}),

    # acc-017: Current Account Closure
    ServiceDocumentMapping(service_id="acc-017", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="acc-017", document_id="doc-business-registration", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Business registration for closure verification.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "बंद करने के सत्यापन के लिए व्यवसाय पंजीकरण।"}),
    ServiceDocumentMapping(service_id="acc-017", document_id="doc-other-declaration", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Account closure request declaration.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "खाता बंद करने के अनुरोध की घोषणा।"}),

    # acc-018: Fixed Deposit Closure
    ServiceDocumentMapping(service_id="acc-018", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="acc-018", document_id="doc-other-declaration", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Fixed deposit closure request declaration.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "सावधि जमा बंद करने के अनुरोध की घोषणा।"}),

    # acc-019: Recurring Deposit Closure
    ServiceDocumentMapping(service_id="acc-019", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="acc-019", document_id="doc-other-declaration", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Recurring deposit closure request declaration.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "आवर्ती जमा बंद करने के अनुरोध की घोषणा।"}),

    # =======================================================================
    # CATEGORY B: CARDS & CHEQUE SERVICES
    # =======================================================================

    # card-001: New Debit Card Application
    ServiceDocumentMapping(service_id="card-001", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="card-001", document_id="doc-pan", mandatory=True, conditional=False,
                           alternatives=["doc-form60"]),

    # card-002: New Credit Card Application
    ServiceDocumentMapping(service_id="card-002", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="card-002", document_id="doc-pan", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="card-002", document_id="doc-salary-slips", mandatory=True, conditional=False,
                           alternatives=["doc-itr", "doc-income-certificate"]),

    # card-003: Card Replacement
    ServiceDocumentMapping(service_id="card-003", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="card-003", document_id="doc-other-id", mandatory=False, conditional=False,
                           service_specific_purpose={"en": "Old card (if available) for replacement reference.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "प्रतिस्थापन संदर्भ के लिए पुराना कार्ड (यदि उपलब्ध हो।"}),

    # card-004: PIN Generation Request
    ServiceDocumentMapping(service_id="card-004", document_id="doc-aadhaar", mandatory=True, conditional=False),

    # card-005: Lost Card Blocking / Hotlisting
    ServiceDocumentMapping(service_id="card-005", document_id="doc-aadhaar", mandatory=True, conditional=False),

    # card-006: Credit Limit Enhancement Request
    ServiceDocumentMapping(service_id="card-006", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="card-006", document_id="doc-pan", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="card-006", document_id="doc-salary-slips", mandatory=True, conditional=False,
                           alternatives=["doc-itr", "doc-bank-statement"]),

    # cheq-001: Cheque Book Request
    ServiceDocumentMapping(service_id="cheq-001", document_id="doc-aadhaar", mandatory=True, conditional=False),

    # cheq-002: Stop-payment Instruction
    ServiceDocumentMapping(service_id="cheq-002", document_id="doc-aadhaar", mandatory=True, conditional=False),

    # cheq-003: Cheque Deposit Slip
    ServiceDocumentMapping(service_id="cheq-003", document_id="doc-aadhaar", mandatory=True, conditional=False),

    # cash-001: Cash Deposit Slip
    ServiceDocumentMapping(service_id="cash-001", document_id="doc-aadhaar", mandatory=True, conditional=False),

    # cash-002: Cash Withdrawal Slip
    ServiceDocumentMapping(service_id="cash-002", document_id="doc-aadhaar", mandatory=True, conditional=False),

    # dd-001: Demand Draft Application
    ServiceDocumentMapping(service_id="dd-001", document_id="doc-aadhaar", mandatory=True, conditional=False),

    # neft-001: NEFT Application
    ServiceDocumentMapping(service_id="neft-001", document_id="doc-aadhaar", mandatory=True, conditional=False),

    # rtgs-001: RTGS Application
    ServiceDocumentMapping(service_id="rtgs-001", document_id="doc-aadhaar", mandatory=True, conditional=False),

    # imps-001: IMPS Application
    ServiceDocumentMapping(service_id="imps-001", document_id="doc-aadhaar", mandatory=True, conditional=False),

    # =======================================================================
    # CATEGORY C: LOANS & CREDIT FACILITIES
    # =======================================================================

    # loan-001: Home Loan Application
    ServiceDocumentMapping(service_id="loan-001", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-001", document_id="doc-pan", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-001", document_id="doc-salary-slips", mandatory=True, conditional=True,
                           conditional_reason="Required for salaried applicants.",
                           alternatives=["doc-itr", "doc-income-certificate"]),
    ServiceDocumentMapping(service_id="loan-001", document_id="doc-property-documents", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-001", document_id="doc-property-valuation", mandatory=False, conditional=True,
                           conditional_reason="Required where property valuation is applicable."),

    # loan-002: Vehicle Loan Application
    ServiceDocumentMapping(service_id="loan-002", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-002", document_id="doc-pan", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-002", document_id="doc-vehicle-quotation", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-002", document_id="doc-salary-slips", mandatory=True, conditional=True,
                           conditional_reason="Required for income verification.",
                           alternatives=["doc-itr", "doc-income-certificate"]),

    # loan-003: Personal Loan Application
    ServiceDocumentMapping(service_id="loan-003", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-003", document_id="doc-pan", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-003", document_id="doc-salary-slips", mandatory=True, conditional=False,
                           alternatives=["doc-itr", "doc-income-certificate"]),

    # loan-004: Gold Loan Application
    ServiceDocumentMapping(service_id="loan-004", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-004", document_id="doc-gold-documents", mandatory=True, conditional=False),

    # loan-005: Education Loan Application
    ServiceDocumentMapping(service_id="loan-005", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-005", document_id="doc-pan", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-005", document_id="doc-admission-letter", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-005", document_id="doc-10th-marksheet", mandatory=True, conditional=True,
                           conditional_reason="Required as educational history evidence.",
                           alternatives=["doc-12th-marksheet"]),
    ServiceDocumentMapping(service_id="loan-005", document_id="doc-fee-structure", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-005", document_id="doc-salary-slips", mandatory=True, conditional=True,
                           conditional_reason="Required for applicant/parent/guardian income verification.",
                           alternatives=["doc-itr", "doc-income-certificate"]),

    # loan-006: Overdraft Against Salary
    ServiceDocumentMapping(service_id="loan-006", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-006", document_id="doc-pan", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-006", document_id="doc-salary-slips", mandatory=True, conditional=False),

    # loan-007: Overdraft Against Fixed Deposit
    ServiceDocumentMapping(service_id="loan-007", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-007", document_id="doc-pan", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-007", document_id="doc-bank-statement", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Fixed deposit receipt details.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "सावधि जमा रसीद विवरण।"}),

    # loan-008: MSME Loan Application
    ServiceDocumentMapping(service_id="loan-008", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-008", document_id="doc-pan", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-008", document_id="doc-business-registration", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-008", document_id="doc-business-financials", mandatory=True, conditional=False),

    # loan-009: Working Capital Loan Application
    ServiceDocumentMapping(service_id="loan-009", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-009", document_id="doc-pan", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-009", document_id="doc-business-registration", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-009", document_id="doc-bank-statement", mandatory=True, conditional=False),

    # loan-010: Agricultural Credit
    ServiceDocumentMapping(service_id="loan-010", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-010", document_id="doc-other-id", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Land records for agricultural credit.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "कृषि ऋण के लिए भूमि रिकॉर्ड।"}),
    ServiceDocumentMapping(service_id="loan-010", document_id="doc-other-declaration", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Crop details declaration.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "फसल विवरण घोषणा।"}),

    # loan-011: Kisan Credit Card Application
    ServiceDocumentMapping(service_id="loan-011", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="loan-011", document_id="doc-other-id", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Land records for Kisan Credit Card.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "किसान क्रेडिट कार्ड के लिए भूमि रिकॉर्ड।"}),
    ServiceDocumentMapping(service_id="loan-011", document_id="doc-other-declaration", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Crop details declaration.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "फसल विवरण घोषणा।"}),

    # scheme-001: Capital Gains Account Scheme
    ServiceDocumentMapping(service_id="scheme-001", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="scheme-001", document_id="doc-pan", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="scheme-001", document_id="doc-property-documents", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Sale deed documents for capital gains.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "पूंजीगत लाभ के लिए बिक्री विलेख दस्तावेज।"}),

    # scheme-002: PMJDY
    ServiceDocumentMapping(service_id="scheme-002", document_id="doc-aadhaar", mandatory=True, conditional=False,
                           alternatives=["doc-voter-id", "doc-other-id"]),

    # scheme-003: Government Social Security Scheme
    ServiceDocumentMapping(service_id="scheme-003", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="scheme-003", document_id="doc-bank-statement", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Bank account details for premium debit.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "प्रीमियम डेबिट के लिए बैंक खाता विवरण।"}),

    # =======================================================================
    # CATEGORY D: INVESTMENTS, INSURANCE & WEALTH MANAGEMENT
    # =======================================================================

    # ins-001: Life Insurance Application
    ServiceDocumentMapping(service_id="ins-001", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="ins-001", document_id="doc-pan", mandatory=True, conditional=False),

    # ins-002: Health Insurance Application
    ServiceDocumentMapping(service_id="ins-002", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="ins-002", document_id="doc-pan", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="ins-002", document_id="doc-medical-certificate", mandatory=True, conditional=False),

    # ins-003: Vehicle Insurance Application
    ServiceDocumentMapping(service_id="ins-003", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="ins-003", document_id="doc-other-id", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Vehicle registration certificate (RC).",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "वाहन पंजीकरण प्रमाणपत्र (आरसी)।"}),
    ServiceDocumentMapping(service_id="ins-003", document_id="doc-driving-licence", mandatory=True, conditional=False),

    # ins-004: Home Insurance Application
    ServiceDocumentMapping(service_id="ins-004", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="ins-004", document_id="doc-property-documents", mandatory=True, conditional=False,
                           alternatives=["doc-rent-agreement"]),

    # ins-005: Travel Insurance Application
    ServiceDocumentMapping(service_id="ins-005", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="ins-005", document_id="doc-passport", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="ins-005", document_id="doc-other-declaration", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Travel itinerary.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "यात्रा कार्यक्रम।"}),

    # ins-006: Insurance Claim Application
    ServiceDocumentMapping(service_id="ins-006", document_id="doc-insurance-policy", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="ins-006", document_id="doc-claim-documents", mandatory=True, conditional=False),

    # inv-001: Demat Account Opening
    ServiceDocumentMapping(service_id="inv-001", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="inv-001", document_id="doc-pan", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="inv-001", document_id="doc-bank-statement", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Bank details for fund settlement.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "निधि निपटान के लिए बैंक विवरण।"}),
    ServiceDocumentMapping(service_id="inv-001", document_id="doc-photograph", mandatory=True, conditional=False),

    # inv-002: Mutual Fund Investment Application
    ServiceDocumentMapping(service_id="inv-002", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="inv-002", document_id="doc-pan", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="inv-002", document_id="doc-bank-statement", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Bank details for dividend payouts.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "लाभांश भुगतान के लिए बैंक विवरण।"}),

    # inv-003: IPO Application
    ServiceDocumentMapping(service_id="inv-003", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="inv-003", document_id="doc-pan", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="inv-003", document_id="doc-demat-documents", mandatory=True, conditional=False),

    # inv-004: Bond Subscription Application
    ServiceDocumentMapping(service_id="inv-004", document_id="doc-aadhaar", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="inv-004", document_id="doc-pan", mandatory=True, conditional=False),
    ServiceDocumentMapping(service_id="inv-004", document_id="doc-bank-statement", mandatory=True, conditional=False,
                           service_specific_purpose={"en": "Bank details for interest payouts.",
                                                     "te": "tx-సంగీతం",
                                                     "hi": "ब्याज भुगतान के लिए बैंक विवरण।"}),

]


def get_document_catalogue() -> List[DocumentDefinition]:
    """Return all document definitions."""
    return list(DOCUMENT_CATALOGUE.values())


def get_document_by_id(document_id: str) -> Optional[DocumentDefinition]:
    """Return a single document definition by ID."""
    return DOCUMENT_CATALOGUE.get(document_id)


def get_documents_by_category(category: str) -> List[DocumentDefinition]:
    """Return documents filtered by category (A-H)."""
    return [d for d in DOCUMENT_CATALOGUE.values() if d.category == category]


def get_service_mappings(service_id: str) -> List[ServiceDocumentMapping]:
    """Return all document mappings for a service."""
    return [m for m in SERVICE_DOCUMENT_MAPPINGS if m.service_id == service_id]


def get_checklist_for_service(service_id: str, service_name: str, form_number: str) -> DocumentChecklist:
    """Build a resolved document checklist for a service."""
    mappings = get_service_mappings(service_id)
    documents: List[DocumentChecklistItem] = []

    for mapping in mappings:
        doc_def = get_document_by_id(mapping.document_id)
        if not doc_def:
            continue

        # Resolve name, description, purpose in English (default)
        name = doc_def.name.get("en", mapping.document_id)
        description = doc_def.description.get("en", "")
        purpose = mapping.service_specific_purpose.get("en", doc_def.purpose.get("en", "")) if mapping.service_specific_purpose else doc_def.purpose.get("en", "")

        # Determine status based on mandatory/conditional
        if mapping.mandatory:
            status = DocumentRequirementStatus.PENDING
        elif mapping.conditional:
            status = DocumentRequirementStatus.PENDING
        else:
            status = DocumentRequirementStatus.OPTIONAL

        documents.append(DocumentChecklistItem(
            document_id=doc_def.id,
            name=name,
            category=doc_def.category,
            description=description,
            purpose=purpose,
            mandatory=mapping.mandatory,
            conditional=mapping.conditional,
            conditional_reason=mapping.conditional_reason,
            extracted_fields=doc_def.extracted_fields,
            alternatives=mapping.alternatives or doc_def.alternatives,
            status=status,
        ))

    total_required = sum(1 for d in documents if d.mandatory and not d.conditional)
    total_optional = sum(1 for d in documents if not d.mandatory and not d.conditional)
    total_conditional = sum(1 for d in documents if d.conditional)

    return DocumentChecklist(
        service_id=service_id,
        service_name=service_name,
        form_number=form_number,
        documents=documents,
        total_required=total_required,
        total_optional=total_optional,
        total_conditional=total_conditional,
    )


def get_document_translations(document_id: str, language: str) -> Optional[Dict[str, str]]:
    """Return translated name, description, purpose for a document."""
    doc = get_document_by_id(document_id)
    if not doc:
        return None
    return {
        "name": doc.name.get(language, doc.name.get("en", "")),
        "description": doc.description.get(language, doc.description.get("en", "")),
        "purpose": doc.purpose.get(language, doc.purpose.get("en", "")),
    }


# In-memory storage for checklist status (per application)
# In production, this would be persisted to a database
_checklist_storage: Dict[str, Dict[str, DocumentRequirementStatus]] = {}


def update_checklist_status(application_id: str, document_id: str, status: DocumentRequirementStatus) -> None:
    """Update a document's status in an application's checklist."""
    if application_id not in _checklist_storage:
        _checklist_storage[application_id] = {}
    _checklist_storage[application_id][document_id] = status


def get_application_checklist(
    service_id: str,
    service_name: str,
    form_number: str,
    application_id: str,
) -> DocumentChecklist:
    """
    Checklist for a service with per-application status overlay applied.

    Application ids are application/session-scoped: the base checklist is
    resolved from the catalogue, then any stored per-application statuses
    (uploaded/readable/needs_rescan/...) override the base value.
    """
    checklist = get_checklist_for_service(service_id, service_name, form_number)
    stored = _checklist_storage.get(application_id, {})
    if stored:
        for item in checklist.documents:
            if item.document_id in stored:
                item.status = stored[item.document_id]
    return checklist


def get_checklist_progress(application_id: str, service_id: str) -> Optional[ChecklistProgress]:
    """Calculate progress for an application's document checklist."""
    # Get the checklist for the service
    # We need service info - this is simplified; in production we'd look up the service
    mappings = get_service_mappings(service_id)
    if not mappings:
        return None

    app_status = _checklist_storage.get(application_id, {})

    total = len(mappings)
    completed = 0
    pending = 0
    optional_count = 0
    not_applicable = 0
    needs_rescan = 0

    for mapping in mappings:
        status = app_status.get(mapping.document_id, DocumentRequirementStatus.PENDING)
        if status == DocumentRequirementStatus.UPLOADED or status == DocumentRequirementStatus.READABLE:
            completed += 1
        elif status == DocumentRequirementStatus.PENDING:
            pending += 1
        elif status == DocumentRequirementStatus.OPTIONAL:
            optional_count += 1
        elif status == DocumentRequirementStatus.NOT_APPLICABLE:
            not_applicable += 1
        elif status == DocumentRequirementStatus.NEEDS_RESCAN:
            needs_rescan += 1

    percentage = (completed / total * 100) if total > 0 else 0.0

    # Count mandatory documents
    mandatory_docs = [m for m in mappings if m.mandatory]
    mandatory_complete = all(
        app_status.get(m.document_id, DocumentRequirementStatus.PENDING)
        in [DocumentRequirementStatus.UPLOADED, DocumentRequirementStatus.READABLE]
        for m in mandatory_docs
    ) if mandatory_docs else True

    return ChecklistProgress(
        application_id=application_id,
        service_id=service_id,
        total_documents=total,
        completed=completed,
        pending=pending,
        optional=optional_count,
        not_applicable=not_applicable,
        needs_rescan=needs_rescan,
        percentage=round(percentage, 1),
        all_mandatory_complete=mandatory_complete,
    )
