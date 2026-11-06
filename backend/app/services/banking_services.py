"""
Banking Service Catalogue - Configurable Data Module

All banking services are defined here as configurable data.
Each service has:
- Unique prototype form number (ACC-xxx, KYC-xxx, CARD-xxx, LOAN-xxx, INV-xxx)
- Description, help text, eligibility, documents, estimated time
- Document requirements with mandatory/optional/conditional classifications

IMPORTANT: These are PROTOTYPE form identifiers, NOT official HDFC Bank form numbers.
Generated applications are demonstration documents only.
"""

from typing import List, Dict, Any
from pydantic import BaseModel


class DocumentRequirement(BaseModel):
    name: str
    mandatory: bool  # True = mandatory, False = optional
    conditional: bool = False  # True = only required under certain conditions
    purpose: str
    extractedFields: List[str]
    alternatives: List[str] = []


class BankingService(BaseModel):
    id: str
    category: str  # account, cards, loans, investments
    name: str
    formNumber: str
    isPrototype: bool = True
    description: str
    helpText: str  # Short help summary
    fullExplanation: str  # Detailed help explanation (7-part)
    eligibility: str
    documents: List[DocumentRequirement]
    estimatedTime: str


# ---------------------------------------------------------------------------
# SERVICE CATALOGUE
# ---------------------------------------------------------------------------

SERVICES: Dict[str, BankingService] = {

    # =======================================================================
    # CATEGORY A: ACCOUNT SERVICES & MAINTENANCE
    # =======================================================================

    "acc-001": BankingService(
        id="acc-001",
        category="account",
        name="Savings Account Opening",
        formNumber="ACC-001",
        description="Open a new savings account with debit card and digital banking access.",
        helpText=(
            "A savings account lets you deposit money safely, withdraw when needed, "
            "and earn interest on eligible deposits. You can also receive payments, "
            "use debit cards and access digital banking facilities."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "A savings account is a basic bank account where you can deposit money, "
            "withdraw it when needed, and earn interest on eligible deposits.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To keep money safe, receive payments (salary, transfers), pay bills, "
            "and access ATM and digital banking services.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Resident individuals aged 18 and above. Minors can open an account with a guardian.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Secure deposits, interest earnings, debit card access, digital banking, "
            "and easy withdrawals.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card (identity & address), PAN Card (tax ID), and a passport-size photograph.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select this service, scan your documents, review the pre-filled form, "
            "confirm details, and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The application is processed by the bank. You will receive account details "
            "and a debit card once approved."
        ),
        eligibility="Resident individuals aged 18 and above. Minors can open with a guardian.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                conditional=False,
                purpose="Establishes the customer's identity and residential address.",
                extractedFields=["full_name", "date_of_birth", "address", "gender"],
                alternatives=["Passport", "Voter ID", "Driving License"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                conditional=False,
                purpose="Used for tax identification and applicable financial compliance requirements.",
                extractedFields=["full_name", "pan_number", "date_of_birth"],
                alternatives=["Form 60 (if PAN not available)"],
            ),
            DocumentRequirement(
                name="Passport-size Photograph",
                mandatory=True,
                conditional=False,
                purpose="Used for customer identification and account records.",
                extractedFields=[],
            ),
            DocumentRequirement(
                name="Address Proof",
                mandatory=False,
                conditional=True,
                purpose="Required if the identity document does not adequately establish the residential address.",
                extractedFields=["address"],
                alternatives=["Utility bill", "Bank statement", "Rent agreement"],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    "acc-002": BankingService(
        id="acc-002",
        category="account",
        name="Current Account Opening",
        formNumber="ACC-002",
        description="Open a current account for business transactions.",
        helpText=(
            "A current account is for businesses and professionals who need frequent "
            "transactions and do not earn interest on balances."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "A current account is a bank account designed for businesses, firms, and "
            "professionals who make frequent deposits and withdrawals.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "For daily business transactions, receiving payments from clients, and "
            "managing business cash flow.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Business owners, firms, companies, and professionals.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Unlimited transactions, overdraft facility (where applicable), and "
            "business banking features.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, Business Registration certificate, and photograph.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select this service, scan your documents, review the pre-filled form, "
            "confirm details, and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank verifies business documents and activates the current account."
        ),
        eligibility="Business owners, firms, companies, and professionals.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Establishes the applicant's identity and address.",
                extractedFields=["full_name", "date_of_birth", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification for the business applicant.",
                extractedFields=["full_name", "pan_number"],
                alternatives=["Form 60"],
            ),
            DocumentRequirement(
                name="Business Registration",
                mandatory=True,
                purpose="Proof of business existence and legal entity type.",
                extractedFields=["business_name", "registration_number"],
                alternatives=["GST certificate", "Shop establishment license"],
            ),
            DocumentRequirement(
                name="Passport-size Photograph",
                mandatory=True,
                purpose="For account records and identification.",
                extractedFields=[],
            ),
        ],
        estimatedTime="15-20 min",
    ),

    "kyc-001": BankingService(
        id="kyc-001",
        category="account",
        name="KYC Update",
        formNumber="KYC-001",
        description="Update your KYC details including address, email, or mobile number.",
        helpText=(
            "Keep your KYC details current to continue using banking services "
            "without interruption."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "KYC (Know Your Customer) update lets you refresh your identity, address, "
            "email, or mobile number on file with the bank.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When you move, change contact details, or the bank requires periodic KYC refresh.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing account holders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Uninterrupted banking services, compliance with RBI regulations, "
            "and updated contact details.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card and PAN Card.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select KYC Update, scan your documents, confirm the updated details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank updates your KYC records and confirms the changes."
        ),
        eligibility="Existing account holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity and address proof for KYC update.",
                extractedFields=["full_name", "date_of_birth", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification for KYC compliance.",
                extractedFields=["full_name", "pan_number"],
                alternatives=["Form 60"],
            ),
        ],
        estimatedTime="5-10 min",
    ),

    "acc-003": BankingService(
        id="acc-003",
        category="account",
        name="Address Change",
        formNumber="ACC-003",
        description="Update your residential address on your bank account records.",
        helpText=(
            "Change your registered residential address with the bank using valid "
            "address proof."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "An address change request updates your residential address on your bank "
            "account records.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When you move to a new home and need bank statements and communications "
            "sent to the new address.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing account holders with valid address proof.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Ensures bank correspondence reaches you and keeps records current.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card or alternative address proof.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Address Change, scan your address proof, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank updates your address in their records."
        ),
        eligibility="Existing account holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="New residential address proof.",
                extractedFields=["full_name", "address"],
                alternatives=["Passport", "Utility bill", "Rent agreement"],
            ),
        ],
        estimatedTime="5-10 min",
    ),

    "acc-004": BankingService(
        id="acc-004",
        category="account",
        name="Mobile Number Update",
        formNumber="ACC-004",
        description="Update your registered mobile number on your bank account.",
        helpText=(
            "Change the mobile number linked to your account for alerts and OTPs."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Mobile number update changes the phone number linked to your bank account "
            "for SMS alerts and notifications.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When you change your phone number and want to continue receiving "
            "transaction alerts.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing account holders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Continued receipt of SMS alerts and secure communication.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Identity proof (Aadhaar Card).<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Mobile Number Update, scan your ID, confirm the new number, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank updates your mobile number and sends a confirmation."
        ),
        eligibility="Existing account holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for mobile number change.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
        ],
        estimatedTime="5 min",
    ),

    "acc-005": BankingService(
        id="acc-005",
        category="account",
        name="Email Update",
        formNumber="ACC-005",
        description="Update your registered email address on your bank account.",
        helpText=(
            "Change the email address linked to your account for statements and alerts."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Email update changes the email address on your bank account for "
            "statements and digital communications.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When you change your email provider or personal email address.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing account holders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Receive e-statements and digital alerts at your current email.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Identity proof (Aadhaar Card).<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Email Update, scan your ID, confirm the new email, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank updates your email address in their records."
        ),
        eligibility="Existing account holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for email change.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
        ],
        estimatedTime="5 min",
    ),

    "acc-006": BankingService(
        id="acc-006",
        category="account",
        name="Signature Update",
        formNumber="ACC-006",
        description="Update your specimen signature on your bank account records.",
        helpText=(
            "Change your signature on file with the bank."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Signature update lets you change your specimen signature on your bank "
            "account records.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When your signature has changed and cheques or documents need to match.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing account holders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Ensures signed documents match your current signature.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Identity proof (Aadhaar Card).<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Signature Update, scan your ID, provide new signature specimen, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank updates your specimen signature."
        ),
        eligibility="Existing account holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for signature update.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
        ],
        estimatedTime="10 min",
    ),

    "acc-007": BankingService(
        id="acc-007",
        category="account",
        name="Non-resident Declaration",
        formNumber="ACC-007",
        description="File a non-resident declaration for NRI/NRO/NRE accounts.",
        helpText=(
            "Declare non-resident status for NRI, NRO, or NRE account types."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "A non-resident declaration formally states your non-resident status "
            "for NRI/NRO/NRE banking.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To open or operate NRI, NRO, or NRE accounts as a non-resident Indian.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Non-resident Indians and persons of Indian origin.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Enables NRI/NRO/NRE account operations and repatriation benefits.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Passport, visa, and overseas address proof.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Non-resident Declaration, scan your documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank processes the declaration for NRI account services."
        ),
        eligibility="Non-resident Indians and persons of Indian origin.",
        documents=[
            DocumentRequirement(
                name="Passport",
                mandatory=True,
                purpose="Identity and nationality proof for non-resident status.",
                extractedFields=["full_name", "nationality", "passport_number"],
            ),
            DocumentRequirement(
                name="Visa",
                mandatory=True,
                purpose="Proof of residence status abroad.",
                extractedFields=["visa_type", "validity"],
            ),
            DocumentRequirement(
                name="Overseas Address Proof",
                mandatory=True,
                purpose="Proof of current overseas residential address.",
                extractedFields=["address"],
                alternatives=["Utility bill", "Bank statement"],
            ),
        ],
        estimatedTime="15-20 min",
    ),

    "acc-008": BankingService(
        id="acc-008",
        category="account",
        name="Legal Entity Information Update",
        formNumber="ACC-008",
        description="Update legal entity information for business accounts.",
        helpText=(
            "Update legal entity details such as directors, partners, or business structure."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Legal entity information update changes business entity details on "
            "company or firm accounts.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When there are changes in directors, partners, or business structure.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Business account holders (companies, firms, LLPs).<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Keeps business registration details current with the bank.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Business registration, PAN, and authorized signatory documents.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Legal Entity Information Update, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank updates the legal entity information on the business account."
        ),
        eligibility="Business account holders (companies, firms, LLPs).",
        documents=[
            DocumentRequirement(
                name="Business Registration Certificate",
                mandatory=True,
                purpose="Proof of legal entity and registration details.",
                extractedFields=["business_name", "registration_number"],
                alternatives=["GST certificate"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification for the business entity.",
                extractedFields=["pan_number"],
                alternatives=["Form 60"],
            ),
            DocumentRequirement(
                name="Authorized Signatory ID",
                mandatory=True,
                purpose="Identity of the person authorized to operate the account.",
                extractedFields=["full_name"],
                alternatives=["Aadhaar Card", "Passport"],
            ),
        ],
        estimatedTime="15-20 min",
    ),

    # =======================================================================
    # CATEGORY B: CARDS & CHEQUE SERVICES
    # =======================================================================

    "card-001": BankingService(
        id="card-001",
        category="cards",
        name="New Debit Card Application",
        formNumber="CARD-001",
        description="Apply for a new debit card linked to your account.",
        helpText=(
            "A debit card lets you withdraw cash and make payments directly "
            "from your account."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for a new debit card linked to your savings or current account.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To withdraw cash from ATMs and make card payments at merchants.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing savings or current account holders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "ATM access, card payments, and online shopping.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card and PAN Card.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select New Debit Card Application, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank issues and mails the debit card to your registered address."
        ),
        eligibility="Existing savings or current account holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for card issuance.",
                extractedFields=["full_name", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification for card application.",
                extractedFields=["full_name", "pan_number"],
                alternatives=["Form 60"],
            ),
        ],
        estimatedTime="5-10 min",
    ),

    "card-002": BankingService(
        id="card-002",
        category="cards",
        name="New Credit Card Application",
        formNumber="CARD-004",
        description="Apply for a new credit card.",
        helpText=(
            "Apply for a credit card based on your income and credit profile."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for a new credit card based on your income and credit history.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "For credit-based purchases, EMI options, and building credit history.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Salaried or self-employed individuals meeting income criteria.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Credit purchases, reward points, EMI conversion, and emergency funds.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, and income proof.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select New Credit Card Application, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank assesses creditworthiness and issues the card if approved."
        ),
        eligibility="Salaried or self-employed individuals meeting income criteria.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity and address verification.",
                extractedFields=["full_name", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification for credit assessment.",
                extractedFields=["full_name", "pan_number"],
                alternatives=["Form 60"],
            ),
            DocumentRequirement(
                name="Income Proof",
                mandatory=True,
                purpose="Salary slips or bank statements to assess repayment capacity.",
                extractedFields=["monthly_income", "employer_name"],
                alternatives=["ITR", "Form 16"],
            ),
        ],
        estimatedTime="15-20 min",
    ),

    "card-003": BankingService(
        id="card-003",
        category="cards",
        name="Card Replacement",
        formNumber="CARD-003",
        description="Request a replacement for a damaged or expired debit/credit card.",
        helpText=(
            "Get a new card issued when your existing card is damaged, expired, "
            "or worn out."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Request a replacement card when your existing debit or credit card is "
            "damaged, expired, or worn out.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To continue using card services when the current card no longer works.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing cardholders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Uninterrupted card access and cash withdrawal.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card and the old card (if available).<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Card Replacement, scan your ID, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank deactivates the old card and issues a replacement."
        ),
        eligibility="Existing cardholders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for card replacement.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="Old Card (if available)",
                mandatory=False,
                purpose="The damaged or expired card to be replaced.",
                extractedFields=[],
            ),
        ],
        estimatedTime="5 min",
    ),

    "card-004": BankingService(
        id="card-004",
        category="cards",
        name="PIN Generation Request",
        formNumber="CARD-005",
        description="Request PIN generation for your debit or credit card.",
        helpText=(
            "Generate a new PIN for your card through a secure process."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Request PIN generation for a new or existing debit/credit card.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When you forget your PIN or need a new one for a new card.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing cardholders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Secure access to ATM and card services.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card for identity verification.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select PIN Generation, scan your ID, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank generates a new PIN and sends it securely."
        ),
        eligibility="Existing cardholders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for PIN generation.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
        ],
        estimatedTime="5 min",
    ),

    "card-005": BankingService(
        id="card-005",
        category="cards",
        name="Lost Card Blocking / Hotlisting",
        formNumber="CARD-002",
        description="Block or hotlist a lost or stolen card.",
        helpText=(
            "Immediately block a lost or stolen card to prevent unauthorized use."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Lost card blocking (hotlisting) immediately stops a lost or stolen "
            "debit/credit card from being used.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To prevent unauthorized transactions when a card is lost or stolen.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing cardholders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Immediate fraud protection and peace of mind.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card for identity verification.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Lost Card Blocking, scan your ID, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank blocks the card immediately and issues a replacement if requested."
        ),
        eligibility="Existing cardholders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for card blocking.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
        ],
        estimatedTime="3-5 min",
    ),

    "card-006": BankingService(
        id="card-006",
        category="cards",
        name="Credit Limit Enhancement Request",
        formNumber="CARD-006",
        description="Request an increase in your credit card limit.",
        helpText=(
            "Apply to increase your existing credit card spending limit."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Request an increase to the spending limit on your existing credit card.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When you need more purchasing power or higher credit availability.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing credit cardholders with good repayment history.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Higher spending capacity and better credit utilization ratio.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, and income proof.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Credit Limit Enhancement, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank reviews income and repayment history, then approves or declines."
        ),
        eligibility="Existing credit cardholders with good repayment history.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification.",
                extractedFields=["pan_number"],
                alternatives=["Form 60"],
            ),
            DocumentRequirement(
                name="Income Proof",
                mandatory=True,
                purpose="To assess enhanced repayment capacity.",
                extractedFields=["monthly_income"],
                alternatives=["ITR", "Bank statements"],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    # =======================================================================
    # CATEGORY B2: Cheque Services
    # =======================================================================

    "cheq-001": BankingService(
        id="cheq-001",
        category="cards",
        name="Cheque Book Request",
        formNumber="CHQ-001",
        description="Request a new cheque book for your account.",
        helpText=(
            "Apply for a cheque book to issue cheques for payments."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Request a new cheque book linked to your savings or current account.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To issue cheques for payments, rent, or business transactions.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing savings or current account holders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Ability to issue cheques for payments and record-keeping.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card and account details.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Cheque Book Request, scan your ID, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank issues and mails a cheque book to your address."
        ),
        eligibility="Existing savings or current account holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for cheque book issuance.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
        ],
        estimatedTime="5 min",
    ),

    "cheq-002": BankingService(
        id="cheq-002",
        category="cards",
        name="Stop-payment Instruction",
        formNumber="CHQ-002",
        description="Issue a stop-payment instruction for a cheque.",
        helpText=(
            "Ask the bank to stop payment on a specific cheque."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Issue a stop-payment instruction to prevent a specific cheque from "
            "being encashed.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When a cheque is lost, stolen, or issued in error.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing account holders who have issued cheques.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Prevents unauthorized encashment of a specific cheque.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card and cheque details (number, amount).<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Stop-payment Instruction, scan your ID, provide cheque details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank places a stop-payment flag on the specified cheque."
        ),
        eligibility="Existing account holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for stop-payment request.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
        ],
        estimatedTime="5 min",
    ),

    "cheq-003": BankingService(
        id="cheq-003",
        category="cards",
        name="Cheque Deposit Slip",
        formNumber="CHQ-003",
        description="Generate a cheque deposit slip for depositing cheques.",
        helpText=(
            "Create a deposit slip to deposit cheques into your account."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Generate a cheque deposit slip to deposit cheques into your account.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When depositing cheques received from others into your account.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing account holders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Proper recording of cheque deposits and faster clearing.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card and the cheque(s) to deposit.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Cheque Deposit Slip, scan your ID, provide deposit details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank processes the cheque deposit and credits your account."
        ),
        eligibility="Existing account holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for cheque deposit.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
        ],
        estimatedTime="5 min",
    ),

    # =======================================================================
    # CATEGORY B3: Cash and Fund Transactions
    # =======================================================================

    "cash-001": BankingService(
        id="cash-001",
        category="cards",
        name="Cash Deposit Slip",
        formNumber="CSD-001",
        description="Generate a cash deposit slip for depositing cash.",
        helpText=(
            "Create a deposit slip to deposit cash into your account."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Generate a cash deposit slip to deposit cash into your bank account.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To deposit physical cash into your savings or current account.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing account holders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Secure cash deposit and immediate account credit.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card for identity verification.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Cash Deposit Slip, scan your ID, provide deposit amount, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank accepts the cash and credits your account."
        ),
        eligibility="Existing account holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for cash deposit.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
        ],
        estimatedTime="5 min",
    ),

    "cash-002": BankingService(
        id="cash-002",
        category="cards",
        name="Cash Withdrawal Slip",
        formNumber="CSW-001",
        description="Generate a cash withdrawal slip for withdrawing cash.",
        helpText=(
            "Create a withdrawal slip to withdraw cash from your account."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Generate a cash withdrawal slip to withdraw cash from your bank account.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To withdraw cash over the counter when an ATM is not available.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing account holders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Cash withdrawal without needing a card or ATM.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card and passbook (if available).<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Cash Withdrawal Slip, scan your ID, provide withdrawal amount, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank verifies your identity and dispenses the cash."
        ),
        eligibility="Existing account holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for cash withdrawal.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
        ],
        estimatedTime="5 min",
    ),

    "dd-001": BankingService(
        id="dd-001",
        category="cards",
        name="Demand Draft Application",
        formNumber="DD-001",
        description="Apply for a Demand Draft for secure fund transfer.",
        helpText=(
            "Request a Demand Draft to transfer funds securely to another party."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for a Demand Draft (DD), a prepaid negotiable instrument for "
            "secure fund transfers.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "For secure payments where the receiver needs guaranteed funds.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing account holders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Secure, guaranteed fund transfer accepted widely.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card and beneficiary details.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Demand Draft Application, scan your ID, provide DD details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank issues the Demand Draft upon payment of the amount plus charges."
        ),
        eligibility="Existing account holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for DD application.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    "neft-001": BankingService(
        id="neft-001",
        category="cards",
        name="NEFT Application",
        formNumber="NEFT-001",
        description="Apply for NEFT fund transfer.",
        helpText=(
            "Request National Electronic Funds Transfer (NEFT) to another bank account."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for NEFT (National Electronic Funds Transfer) to send money "
            "to another bank account.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To transfer funds electronically to another person's bank account.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing account holders with net banking or branch access.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Secure electronic fund transfer across banks in India.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card and beneficiary account details.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select NEFT Application, scan your ID, provide transfer details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank processes the NEFT transfer in batches as per RBI timings."
        ),
        eligibility="Existing account holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for NEFT transfer.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
        ],
        estimatedTime="5-10 min",
    ),

    "rtgs-001": BankingService(
        id="rtgs-001",
        category="cards",
        name="RTGS Application",
        formNumber="RTGS-001",
        description="Apply for RTGS (real-time gross settlement) fund transfer.",
        helpText=(
            "Request RTGS for high-value, real-time fund transfers."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for RTGS (Real-Time Gross Settlement) for high-value, "
            "real-time fund transfers.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "For urgent, high-value transfers that need immediate settlement.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing account holders (minimum transfer amount applies).<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Real-time, irreversible, secure high-value transfers.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card and beneficiary account details.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select RTGS Application, scan your ID, provide transfer details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank processes the RTGS transfer in real time."
        ),
        eligibility="Existing account holders (minimum transfer amount applies).",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for RTGS transfer.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
        ],
        estimatedTime="5-10 min",
    ),

    "imps-001": BankingService(
        id="imps-001",
        category="cards",
        name="IMPS Application",
        formNumber="IMPS-001",
        description="Apply for IMPS (Immediate Payment Service) fund transfer.",
        helpText=(
            "Request IMPS for instant, 24x7 fund transfers."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for IMPS (Immediate Payment Service) for instant, 24x7 "
            "fund transfers using mobile or internet banking.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "For instant money transfers any time, including weekends and holidays.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing account holders with mobile/internet banking.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Instant transfers available 24x7, including holidays.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card and beneficiary mobile number/MMID.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select IMPS Application, scan your ID, provide transfer details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank processes the IMPS transfer instantly."
        ),
        eligibility="Existing account holders with mobile/internet banking.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for IMPS transfer.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
        ],
        estimatedTime="5 min",
    ),

    # =======================================================================
    # CATEGORY C: LOANS & CREDIT FACILITIES
    # =======================================================================

    "loan-001": BankingService(
        id="loan-001",
        category="loans",
        name="Home Loan Application",
        formNumber="LOAN-001",
        description="Apply for a home loan to purchase or construct a house.",
        helpText=(
            "A home loan helps you buy or build a home with flexible repayment options."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for a home loan to purchase or construct a residential house.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To finance the purchase or construction of a home.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Salaried or self-employed individuals meeting income criteria.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Home ownership, tax benefits, and long repayment tenure.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, income proof, and property documents.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Home Loan Application, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank verifies documents, assesses eligibility, and sanctions the loan."
        ),
        eligibility="Salaried or self-employed individuals meeting income criteria.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity and address verification.",
                extractedFields=["full_name", "date_of_birth", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification for loan application.",
                extractedFields=["full_name", "pan_number"],
                alternatives=["Form 60"],
            ),
            DocumentRequirement(
                name="Income Proof",
                mandatory=True,
                purpose="Salary slips or bank statements to assess repayment capacity.",
                extractedFields=["monthly_income", "employer_name"],
                alternatives=["ITR", "Form 16"],
            ),
            DocumentRequirement(
                name="Property Documents",
                mandatory=True,
                purpose="Title and ownership documents for the property.",
                extractedFields=["property_address", "owner_name"],
            ),
        ],
        estimatedTime="20-30 min",
    ),

    "loan-002": BankingService(
        id="loan-002",
        category="loans",
        name="Vehicle Loan Application",
        formNumber="LOAN-003",
        description="Apply for a loan to purchase a vehicle.",
        helpText=(
            "A vehicle loan helps you buy a car or two-wheeler."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for a loan to purchase a new or used vehicle (car or two-wheeler).<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To finance the purchase of a personal or commercial vehicle.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Salaried or self-employed individuals meeting income criteria.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Vehicle ownership with flexible EMI repayment.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, vehicle quotation, and income proof.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Vehicle Loan Application, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank verifies documents and vehicle details, then sanctions the loan."
        ),
        eligibility="Salaried or self-employed individuals meeting income criteria.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity and address verification.",
                extractedFields=["full_name", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification for loan application.",
                extractedFields=["full_name", "pan_number"],
                alternatives=["Form 60"],
            ),
            DocumentRequirement(
                name="Vehicle Quotation",
                mandatory=True,
                purpose="Price quote from the vehicle dealer.",
                extractedFields=["vehicle_model", "price"],
            ),
            DocumentRequirement(
                name="Income Proof",
                mandatory=True,
                purpose="To assess repayment capacity.",
                extractedFields=["monthly_income"],
                alternatives=["ITR", "Bank statements"],
            ),
        ],
        estimatedTime="15-25 min",
    ),

    "loan-003": BankingService(
        id="loan-003",
        category="loans",
        name="Personal Loan Application",
        formNumber="LOAN-004",
        description="Apply for a personal loan for personal expenses.",
        helpText=(
            "An unsecured loan for personal expenses like medical, travel, or emergencies."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for an unsecured personal loan for personal expenses.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "For medical emergencies, travel, wedding, or other personal expenses.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Salaried or self-employed individuals meeting income criteria.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "No collateral required, quick disbursal, flexible use.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, and income proof.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Personal Loan Application, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank assesses creditworthiness and disburses the loan if approved."
        ),
        eligibility="Salaried or self-employed individuals meeting income criteria.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity and address verification.",
                extractedFields=["full_name", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification for loan application.",
                extractedFields=["full_name", "pan_number"],
                alternatives=["Form 60"],
            ),
            DocumentRequirement(
                name="Income Proof",
                mandatory=True,
                purpose="To assess repayment capacity.",
                extractedFields=["monthly_income"],
                alternatives=["ITR", "Bank statements"],
            ),
        ],
        estimatedTime="15-20 min",
    ),

    "loan-004": BankingService(
        id="loan-004",
        category="loans",
        name="Gold Loan Application",
        formNumber="LOAN-005",
        description="Apply for a gold loan against gold ornaments.",
        helpText=(
            "A secured loan where gold ornaments are pledged as collateral."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for a secured gold loan by pledging gold ornaments as collateral.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "For quick, short-term funds without selling your gold.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Individuals owning gold ornaments.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Quick disbursal, minimal documentation, no credit score requirement.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Applicable identity documents and gold-related assessment requirements.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Gold Loan Application, scan your ID, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank assesses the gold value and disburses the loan."
        ),
        eligibility="Individuals owning gold ornaments.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for gold loan.",
                extractedFields=["full_name", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="Gold Ownership Proof",
                mandatory=True,
                purpose="Proof that the gold belongs to the applicant.",
                extractedFields=["gold_weight", "gold_purity"],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    "loan-005": BankingService(
        id="loan-005",
        category="loans",
        name="Education Loan Application",
        formNumber="LOAN-002",
        description="Apply for an education loan for higher studies.",
        helpText=(
            "Fund higher education expenses including tuition, books, and living costs."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for an education loan to fund higher education expenses.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To pay for college tuition, books, hostel, and other education costs.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Students with admission to a recognized institution.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Funds education, moratorium period, tax benefits on interest.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, admission letter, and academic records.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Education Loan Application, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank verifies admission and academic records, then sanctions the loan."
        ),
        eligibility="Students with admission to a recognized institution.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity and address verification.",
                extractedFields=["full_name", "date_of_birth", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification for loan application.",
                extractedFields=["full_name", "pan_number"],
                alternatives=["Form 60"],
            ),
            DocumentRequirement(
                name="Admission Letter",
                mandatory=True,
                purpose="Proof of admission to a recognized educational institution.",
                extractedFields=["institution_name", "course_name"],
            ),
            DocumentRequirement(
                name="Academic Records",
                mandatory=True,
                purpose="Previous educational certificates and mark sheets.",
                extractedFields=["qualification", "year_of_completion"],
            ),
        ],
        estimatedTime="15-25 min",
    ),

    "loan-006": BankingService(
        id="loan-006",
        category="loans",
        name="Overdraft Against Salary",
        formNumber="LOAN-006",
        description="Overdraft facility against your salary account.",
        helpText=(
            "Withdraw more than your account balance up to a salary-based limit."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Overdraft facility allowing you to withdraw more than your salary "
            "account balance up to a pre-approved limit.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "For short-term cash flow needs between salary credits.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Salaried individuals with a salary account.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Immediate access to extra funds, interest only on used amount.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, and salary slips.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Overdraft Against Salary, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank verifies salary and sets the overdraft limit."
        ),
        eligibility="Salaried individuals with a salary account.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification.",
                extractedFields=["pan_number"],
                alternatives=["Form 60"],
            ),
            DocumentRequirement(
                name="Salary Slips",
                mandatory=True,
                purpose="To assess overdraft limit based on salary.",
                extractedFields=["monthly_salary", "employer_name"],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    "loan-007": BankingService(
        id="loan-007",
        category="loans",
        name="Overdraft Against Fixed Deposit",
        formNumber="LOAN-007",
        description="Overdraft facility against your fixed deposit.",
        helpText=(
            "Withdraw funds against your fixed deposit without breaking it."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Overdraft facility against your existing fixed deposit receipt.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "For emergency funds without breaking or closing your fixed deposit.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Fixed deposit holders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Funds without breaking FD, interest only on used amount.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, and fixed deposit receipt.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Overdraft Against FD, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank marks a lien on the FD and sets the overdraft limit."
        ),
        eligibility="Fixed deposit holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification.",
                extractedFields=["pan_number"],
                alternatives=["Form 60"],
            ),
            DocumentRequirement(
                name="Fixed Deposit Receipt",
                mandatory=True,
                purpose="Proof of the fixed deposit to be lien-marked.",
                extractedFields=["fd_number", "fd_amount"],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    # C2: Business and Agricultural Loans
    "loan-008": BankingService(
        id="loan-008",
        category="loans",
        name="MSME Loan Application",
        formNumber="LOAN-008",
        description="Apply for a Micro, Small & Medium Enterprise loan.",
        helpText=(
            "A loan for small businesses to fund working capital or expansion."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for an MSME (Micro, Small & Medium Enterprise) loan to fund "
            "business operations or expansion.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "For working capital, machinery purchase, or business growth.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Registered MSMEs and small business owners.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Business growth support, government scheme benefits.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, business registration, and financial statements.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select MSME Loan Application, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank assesses business viability and sanctions the loan."
        ),
        eligibility="Registered MSMEs and small business owners.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification of business owner.",
                extractedFields=["full_name", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification for business.",
                extractedFields=["pan_number"],
                alternatives=["Form 60"],
            ),
            DocumentRequirement(
                name="Business Registration",
                mandatory=True,
                purpose="Proof of MSME registration.",
                extractedFields=["business_name", "registration_number"],
                alternatives=["Udyam registration"],
            ),
            DocumentRequirement(
                name="Financial Statements",
                mandatory=True,
                purpose="To assess business repayment capacity.",
                extractedFields=["annual_turnover", "net_profit"],
                alternatives=["ITR", "Bank statements"],
            ),
        ],
        estimatedTime="20-30 min",
    ),

    "loan-009": BankingService(
        id="loan-009",
        category="loans",
        name="Working Capital Loan Application",
        formNumber="LOAN-009",
        description="Apply for a working capital loan for business operations.",
        helpText=(
            "A loan to fund daily business operations and cash flow needs."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for a working capital loan to fund daily business operations.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "For inventory purchases, payroll, and daily cash flow needs.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing businesses with operational history.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Smooth business operations, cash flow management.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, business registration, and bank statements.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Working Capital Loan, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank assesses turnover and sanctions the working capital loan."
        ),
        eligibility="Existing businesses with operational history.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification.",
                extractedFields=["pan_number"],
                alternatives=["Form 60"],
            ),
            DocumentRequirement(
                name="Business Registration",
                mandatory=True,
                purpose="Proof of business existence.",
                extractedFields=["business_name"],
            ),
            DocumentRequirement(
                name="Bank Statements",
                mandatory=True,
                purpose="To assess cash flow and repayment capacity.",
                extractedFields=["monthly_turnover"],
            ),
        ],
        estimatedTime="15-25 min",
    ),

    "loan-010": BankingService(
        id="loan-010",
        category="loans",
        name="Agricultural Credit",
        formNumber="LOAN-010",
        description="Apply for agricultural credit for farming activities.",
        helpText=(
            "Credit for farmers to fund crops, equipment, and agricultural expenses."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for agricultural credit to fund farming activities and expenses.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "For seeds, fertilizers, equipment, and crop-related expenses.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Farmers and agricultural landowners.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Seasonal funding, subsidized interest rates (where applicable).<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, land records, and crop details.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Agricultural Credit, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank verifies land records and sanctions agricultural credit."
        ),
        eligibility="Farmers and agricultural landowners.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification of farmer.",
                extractedFields=["full_name", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="Land Records",
                mandatory=True,
                purpose="Proof of agricultural land ownership.",
                extractedFields=["land_area", "survey_number"],
            ),
            DocumentRequirement(
                name="Crop Details",
                mandatory=True,
                purpose="Information about the crop to be cultivated.",
                extractedFields=["crop_type", "expected_yield"],
            ),
        ],
        estimatedTime="15-20 min",
    ),

    "loan-011": BankingService(
        id="loan-011",
        category="loans",
        name="Kisan Credit Card Application",
        formNumber="LOAN-011",
        description="Apply for a Kisan Credit Card for farmers.",
        helpText=(
            "A credit card for farmers to meet agricultural and allied credit needs."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for a Kisan Credit Card (KCC) to meet agricultural and allied "
            "credit needs.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "For timely credit for crop cultivation and allied activities.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Farmers, sharecroppers, and tenant farmers.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Flexible credit, insurance coverage, subsidized interest.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, land records, and crop details.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Kisan Credit Card Application, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank issues a Kisan Credit Card with a credit limit."
        ),
        eligibility="Farmers, sharecroppers, and tenant farmers.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification of farmer.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="Land Records",
                mandatory=True,
                purpose="Proof of agricultural land.",
                extractedFields=["land_area"],
            ),
            DocumentRequirement(
                name="Crop Details",
                mandatory=True,
                purpose="Details of crops cultivated.",
                extractedFields=["crop_type"],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    # C3: Specialized Schemes
    "scheme-001": BankingService(
        id="scheme-001",
        category="loans",
        name="Capital Gains Account Scheme",
        formNumber="SCHEME-001",
        description="Apply for the Capital Gains Account Scheme.",
        helpText=(
            "Deposit capital gains to claim tax exemptions under this scheme."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for the Capital Gains Account Scheme to deposit capital gains "
            "and claim tax exemptions.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To avail tax benefits on capital gains from property or asset sales.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Taxpayers with capital gains.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Tax exemption on reinvested capital gains.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, and sale deed documents.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Capital Gains Account Scheme, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank opens a capital gains account for the deposit."
        ),
        eligibility="Taxpayers with capital gains.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification.",
                extractedFields=["pan_number"],
                alternatives=["Form 60"],
            ),
            DocumentRequirement(
                name="Sale Deed Documents",
                mandatory=True,
                purpose="Proof of capital gains from asset sale.",
                extractedFields=["property_details", "sale_amount"],
            ),
        ],
        estimatedTime="15-20 min",
    ),

    "scheme-002": BankingService(
        id="scheme-002",
        category="loans",
        name="Pradhan Mantri Jan Dhan Yojana (PMJDY)",
        formNumber="SCHEME-002",
        description="Apply for a PMJDY basic savings bank account.",
        helpText=(
            "A financial inclusion scheme for zero-balance bank accounts."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for a Pradhan Mantri Jan Dhan Yojana (PMJDY) basic savings "
            "bank account.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To access basic banking services without minimum balance requirements.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Indian citizens aged 18 and above without a bank account.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Zero balance, RuPay debit card, overdraft facility, insurance.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card or alternative identity proof.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select PMJDY, scan your ID, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank opens a PMJDY account with a RuPay debit card."
        ),
        eligibility="Indian citizens aged 18 and above without a bank account.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity and address proof for PMJDY account.",
                extractedFields=["full_name", "address"],
                alternatives=["Voter ID", "NREGA job card"],
            ),
        ],
        estimatedTime="10 min",
    ),

    "scheme-003": BankingService(
        id="scheme-003",
        category="loans",
        name="Government Social Security Scheme Application",
        formNumber="SCHEME-003",
        description="Apply for government-backed social security schemes.",
        helpText=(
            "Apply for schemes like PMSBY, PMJJBY, and Atal Pension Yojana."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for government-backed social security schemes such as PMSBY, "
            "PMJJBY, and Atal Pension Yojana.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "For life insurance, accident coverage, and pension benefits.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Bank account holders within specified age groups.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Insurance coverage, pension, and financial security.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, bank account details, and age proof.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Social Security Scheme, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank enrolls you in the chosen social security scheme."
        ),
        eligibility="Bank account holders within specified age groups.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity and age verification.",
                extractedFields=["full_name", "date_of_birth"],
                alternatives=["Voter ID", "Birth certificate"],
            ),
            DocumentRequirement(
                name="Bank Account Details",
                mandatory=True,
                purpose="Account where premiums will be debited.",
                extractedFields=["account_number"],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    # =======================================================================
    # CATEGORY D: INVESTMENTS, INSURANCE & WEALTH MANAGEMENT
    # =======================================================================

    # D1: Insurance
    "ins-001": BankingService(
        id="ins-001",
        category="investments",
        name="Life Insurance Application",
        formNumber="INS-001",
        description="Apply for a life insurance policy.",
        helpText=(
            "Life insurance provides financial protection to your family."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for a life insurance policy to protect your family financially.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To provide financial security to dependents in case of unfortunate events.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Individuals meeting age and health criteria.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Life cover, tax benefits, financial protection.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, and age proof.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Life Insurance Application, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The insurance provider assesses risk and issues the policy."
        ),
        eligibility="Individuals meeting age and health criteria.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity and age verification.",
                extractedFields=["full_name", "date_of_birth", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification.",
                extractedFields=["pan_number"],
                alternatives=["Form 60"],
            ),
        ],
        estimatedTime="15-20 min",
    ),

    "ins-002": BankingService(
        id="ins-002",
        category="investments",
        name="Health Insurance Application",
        formNumber="INS-002",
        description="Apply for a health insurance policy.",
        helpText=(
            "Health insurance covers medical and hospitalization expenses."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for a health insurance policy to cover medical expenses.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To cover hospitalization, surgery, and medical treatment costs.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Individuals and families meeting age criteria.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Medical expense coverage, cashless hospitalization, tax benefits.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, and medical reports.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Health Insurance Application, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The insurer assesses health risk and issues the policy."
        ),
        eligibility="Individuals and families meeting age criteria.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification.",
                extractedFields=["full_name", "date_of_birth"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification.",
                extractedFields=["pan_number"],
                alternatives=["Form 60"],
            ),
            DocumentRequirement(
                name="Medical Reports",
                mandatory=True,
                purpose="Health status for risk assessment.",
                extractedFields=[],
            ),
        ],
        estimatedTime="15-25 min",
    ),

    "ins-003": BankingService(
        id="ins-003",
        category="investments",
        name="Vehicle Insurance Application",
        formNumber="INS-003",
        description="Apply for vehicle insurance for your car or two-wheeler.",
        helpText=(
            "Vehicle insurance covers damage and third-party liability."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for vehicle insurance for your car or two-wheeler.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "Mandatory third-party cover and protection for your vehicle.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Vehicle owners.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Accident cover, third-party liability, theft protection.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, vehicle registration (RC), and driving license.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Vehicle Insurance Application, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The insurer issues the vehicle insurance policy."
        ),
        eligibility="Vehicle owners.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification of vehicle owner.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="Vehicle Registration Certificate (RC)",
                mandatory=True,
                purpose="Proof of vehicle ownership and details.",
                extractedFields=["vehicle_number", "chassis_number"],
            ),
            DocumentRequirement(
                name="Driving License",
                mandatory=True,
                purpose="Proof of eligibility to drive the vehicle.",
                extractedFields=["license_number"],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    "ins-004": BankingService(
        id="ins-004",
        category="investments",
        name="Home Insurance Application",
        formNumber="INS-004",
        description="Apply for home insurance for your property.",
        helpText=(
            "Home insurance covers your house and contents against damage."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for home insurance to protect your house and its contents.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To protect against fire, theft, and natural disasters.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Homeowners and tenants.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Property damage cover, contents cover, liability protection.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, property documents, and address proof.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Home Insurance Application, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The insurer assesses property value and issues the policy."
        ),
        eligibility="Homeowners and tenants.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification.",
                extractedFields=["full_name", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="Property Documents",
                mandatory=True,
                purpose="Proof of property ownership or tenancy.",
                extractedFields=["property_address"],
                alternatives=["Rent agreement", "Sale deed"],
            ),
        ],
        estimatedTime="15-20 min",
    ),

    "ins-005": BankingService(
        id="ins-005",
        category="investments",
        name="Travel Insurance Application",
        formNumber="INS-005",
        description="Apply for travel insurance for domestic or international trips.",
        helpText=(
            "Travel insurance covers medical and trip-related emergencies abroad."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for travel insurance for domestic or international trips.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To cover medical emergencies, trip cancellation, and lost baggage.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Individuals planning to travel.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Medical cover, trip cancellation, baggage loss protection.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, passport, and travel itinerary.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Travel Insurance Application, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The insurer issues the travel insurance policy."
        ),
        eligibility="Individuals planning to travel.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="Passport",
                mandatory=True,
                purpose="Proof of identity for international travel.",
                extractedFields=["passport_number", "nationality"],
            ),
            DocumentRequirement(
                name="Travel Itinerary",
                mandatory=True,
                purpose="Details of the planned trip.",
                extractedFields=["destination", "travel_dates"],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    "ins-006": BankingService(
        id="ins-006",
        category="investments",
        name="Insurance Claim Application",
        formNumber="INS-006",
        description="File an insurance claim for a covered event.",
        helpText=(
            "Submit a claim to receive insurance benefits for a covered event."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "File an insurance claim to receive benefits for a covered event.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To receive compensation for an insured loss or event.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Policyholders with an active insurance policy.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Financial compensation for covered losses.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Policy details and supporting claim documents.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Insurance Claim Application, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The insurer assesses the claim and settles it if valid."
        ),
        eligibility="Policyholders with an active insurance policy.",
        documents=[
            DocumentRequirement(
                name="Policy Details",
                mandatory=True,
                purpose="Insurance policy number and coverage details.",
                extractedFields=["policy_number", "policy_type"],
            ),
            DocumentRequirement(
                name="Supporting Claim Documents",
                mandatory=True,
                purpose="Proof of the insured event or loss.",
                extractedFields=[],
                alternatives=["Police report", "Medical certificate", "Repair bill"],
            ),
        ],
        estimatedTime="15-25 min",
    ),

    # D2: Investment Services
    "inv-001": BankingService(
        id="inv-001",
        category="investments",
        name="Demat Account Opening",
        formNumber="INV-001",
        description="Open a demat account to hold securities electronically.",
        helpText=(
            "A demat account lets you hold shares and other securities in electronic form."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Open a demat (dematerialized) account to hold shares and securities electronically.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To trade in stocks, mutual funds, and other securities.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Resident individuals aged 18 and above.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Paperless trading, secure holding, easy transfer of securities.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, bank details, and photograph.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Demat Account Opening, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The depository participant opens your demat account."
        ),
        eligibility="Resident individuals aged 18 and above.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity and address verification.",
                extractedFields=["full_name", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Mandatory for demat account (SEBI requirement).",
                extractedFields=["pan_number"],
                alternatives=[],
            ),
            DocumentRequirement(
                name="Bank Details",
                mandatory=True,
                purpose="Linked bank account for fund settlement.",
                extractedFields=["account_number", "ifsc_code"],
            ),
            DocumentRequirement(
                name="Passport-size Photograph",
                mandatory=True,
                purpose="For account records.",
                extractedFields=[],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    "inv-002": BankingService(
        id="inv-002",
        category="investments",
        name="Mutual Fund Investment Application",
        formNumber="INV-002",
        description="Apply to invest in mutual funds.",
        helpText=(
            "Invest in mutual funds for wealth creation."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply to invest in mutual funds for wealth creation.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "For diversified investment and long-term wealth creation.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Individuals meeting KYC requirements.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Diversification, professional management, liquidity.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, and bank details.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Mutual Fund Investment, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The mutual fund house processes your investment."
        ),
        eligibility="Individuals meeting KYC requirements.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity and address verification.",
                extractedFields=["full_name", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification for investment.",
                extractedFields=["pan_number"],
                alternatives=["Form 60"],
            ),
            DocumentRequirement(
                name="Bank Details",
                mandatory=True,
                purpose="For dividend payouts and redemption proceeds.",
                extractedFields=["account_number"],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    "inv-003": BankingService(
        id="inv-003",
        category="investments",
        name="IPO Application",
        formNumber="INV-003",
        description="Apply for shares in an Initial Public Offering (IPO).",
        helpText=(
            "Apply to buy shares when a company lists on the stock exchange."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply for shares in an Initial Public Offering (IPO) when a company lists.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To invest in a company at its public listing stage.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Individuals with a demat account and PAN.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Potential listing gains, early investment opportunity.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, and demat account details.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select IPO Application, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "Shares are allotted based on the IPO subscription and allotment process."
        ),
        eligibility="Individuals with a demat account and PAN.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Mandatory for IPO application.",
                extractedFields=["pan_number"],
                alternatives=[],
            ),
            DocumentRequirement(
                name="Demat Account Details",
                mandatory=True,
                purpose="Account where allotted shares will be credited.",
                extractedFields=["dp_id", "client_id"],
            ),
        ],
        estimatedTime="10 min",
    ),

    "inv-004": BankingService(
        id="inv-004",
        category="investments",
        name="Bond Subscription Application",
        formNumber="INV-004",
        description="Apply to subscribe to government or corporate bonds.",
        helpText=(
            "Invest in bonds for fixed income and capital preservation."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Apply to subscribe to government or corporate bonds for fixed income.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "For stable, fixed-income investment with capital preservation.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Individuals meeting KYC requirements.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Fixed interest, lower risk, regular income.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, and bank details.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Bond Subscription, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "Bonds are allotted and interest is paid periodically."
        ),
        eligibility="Individuals meeting KYC requirements.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification.",
                extractedFields=["pan_number"],
                alternatives=["Form 60"],
            ),
            DocumentRequirement(
                name="Bank Details",
                mandatory=True,
                purpose="For interest payouts and redemption.",
                extractedFields=["account_number"],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    # =======================================================================
    # Additional Account Services (to reach 59 total services)
    # =======================================================================

    "acc-009": BankingService(
        id="acc-009",
        category="account",
        name="Recurring Deposit (RD) Opening",
        formNumber="ACC-003",
        description="Open a recurring deposit account for regular monthly savings.",
        helpText=(
            "An RD lets you deposit a fixed amount every month and earn interest."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Open a recurring deposit account to save a fixed amount monthly.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "For disciplined monthly savings with guaranteed returns.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Resident individuals aged 18 and above.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Regular savings habit, guaranteed returns, loan against RD.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, photograph.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select RD Opening, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank opens the RD account and sets up monthly debit."
        ),
        eligibility="Resident individuals aged 18 and above.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity and address verification.",
                extractedFields=["full_name", "date_of_birth", "address"],
                alternatives=["Passport", "Voter ID", "Driving License"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification for RD account.",
                extractedFields=["full_name", "pan_number", "date_of_birth"],
                alternatives=["Form 60 (if PAN not available)"],
            ),
            DocumentRequirement(
                name="Passport-size Photograph",
                mandatory=True,
                purpose="Used for customer identification and account records.",
                extractedFields=[],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    "acc-010": BankingService(
        id="acc-010",
        category="account",
        name="Fixed Deposit (FD) Opening",
        formNumber="ACC-004",
        description="Open a fixed deposit account for lump-sum savings.",
        helpText=(
            "An FD lets you deposit a lump sum and earn higher interest."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Open a fixed deposit account to deposit a lump sum for a fixed tenure.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "To earn higher interest on idle funds with capital safety.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Resident individuals aged 18 and above.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Higher interest than savings, flexible tenures, loan against FD.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, photograph.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select FD Opening, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank opens the FD account and issues a receipt."
        ),
        eligibility="Resident individuals aged 18 and above.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity and address verification.",
                extractedFields=["full_name", "date_of_birth", "address"],
                alternatives=["Passport", "Voter ID", "Driving License"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification for FD account.",
                extractedFields=["full_name", "pan_number", "date_of_birth"],
                alternatives=["Form 60 (if PAN not available)"],
            ),
            DocumentRequirement(
                name="Passport-size Photograph",
                mandatory=True,
                purpose="Used for customer identification and account records.",
                extractedFields=[],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    "acc-011": BankingService(
        id="acc-011",
        category="account",
        name="Joint Account Holder Addition/Deletion",
        formNumber="ACC-005",
        description="Add or remove joint account holders from an existing account.",
        helpText=(
            "Modify the holders of a joint bank account."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Add or delete joint account holders from an existing bank account.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When family members need joint access or a holder needs to be removed.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing joint account holders and new applicants.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Shared account access, updated account records.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, PAN Card, photograph for each holder.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Joint Account Modification, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank updates the account holder list."
        ),
        eligibility="Existing joint account holders and new applicants.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity proof for new joint account holder.",
                extractedFields=["full_name", "date_of_birth", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification for joint holder.",
                extractedFields=["full_name", "pan_number"],
                alternatives=["Form 60"],
            ),
            DocumentRequirement(
                name="Passport-size Photograph",
                mandatory=True,
                purpose="For account records of the joint holder.",
                extractedFields=[],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    "acc-012": BankingService(
        id="acc-012",
        category="account",
        name="Minor-to-Major Conversion",
        formNumber="ACC-006",
        description="Convert a minor account to a major account upon turning 18.",
        helpText=(
            "Convert a minor's bank account to a regular adult account."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Convert a minor bank account to a regular account when the holder turns 18.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When a minor account holder reaches adulthood and needs full account access.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Former minor account holders who have turned 18.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Full account control, removal of guardian restrictions.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Age proof (10th marksheet/birth certificate), Aadhaar Card, PAN Card.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Minor-to-Major Conversion, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank converts the account and removes guardian restrictions."
        ),
        eligibility="Former minor account holders who have turned 18.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity and address verification.",
                extractedFields=["full_name", "date_of_birth", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="PAN Card",
                mandatory=True,
                purpose="Tax identification for adult account.",
                extractedFields=["full_name", "pan_number", "date_of_birth"],
                alternatives=["Form 60"],
            ),
            DocumentRequirement(
                name="10th Class Marksheet",
                mandatory=True,
                conditional=True,
                conditional_reason="Required as age proof for conversion from minor to major.",
                purpose="Age proof showing date of birth.",
                extractedFields=["full_name", "date_of_birth"],
                alternatives=["Birth Certificate"],
            ),
            DocumentRequirement(
                name="Passport-size Photograph",
                mandatory=True,
                purpose="Updated photograph for adult account records.",
                extractedFields=[],
            ),
        ],
        estimatedTime="15-20 min",
    ),

    "acc-013": BankingService(
        id="acc-013",
        category="account",
        name="Branch Transfer",
        formNumber="ACC-007",
        description="Transfer your bank account from one branch to another.",
        helpText=(
            "Move your account to a different branch of the same bank."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Transfer your existing bank account from one branch to another.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When you relocate to a different city or area.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Existing account holders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Continued banking services at a convenient branch.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, branch transfer declaration.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Branch Transfer, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank transfers your account records to the new branch."
        ),
        eligibility="Existing account holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for branch transfer.",
                extractedFields=["full_name", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="Other Service-specific Declaration",
                mandatory=True,
                purpose="Branch transfer request declaration.",
                extractedFields=["declaration_type", "declaration_date"],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    "acc-014": BankingService(
        id="acc-014",
        category="account",
        name="Dormant Account Activation",
        formNumber="ACC-008",
        description="Activate a dormant (inactive) bank account.",
        helpText=(
            "Reactivate an account that has had no transactions for a long period."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Reactivate a dormant bank account that has had no transactions.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When you want to use an old account that has become inactive.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Owners of dormant accounts.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Regain access to funds and banking services.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, activation declaration.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Dormant Account Activation, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank verifies identity and reactivates the account."
        ),
        eligibility="Owners of dormant accounts.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for account activation.",
                extractedFields=["full_name", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="Other Service-specific Declaration",
                mandatory=True,
                purpose="Dormant account activation declaration.",
                extractedFields=["declaration_type", "declaration_date"],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    "acc-015": BankingService(
        id="acc-015",
        category="account",
        name="Frozen Account Activation Request",
        formNumber="ACC-009",
        description="Request activation of a frozen bank account.",
        helpText=(
            "Apply to unfreeze a bank account that has been frozen by the bank."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Request activation of a bank account that has been frozen.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When your account has been frozen due to regulatory or legal reasons.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Owners of frozen accounts.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Regain access to frozen funds and services.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, activation request declaration.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Frozen Account Activation, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank reviews the request and may unfreeze the account."
        ),
        eligibility="Owners of frozen accounts.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for frozen account activation.",
                extractedFields=["full_name", "address"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="Other Service-specific Declaration",
                mandatory=True,
                purpose="Frozen account activation request declaration.",
                extractedFields=["declaration_type", "declaration_date"],
            ),
        ],
        estimatedTime="15-20 min",
    ),

    "acc-016": BankingService(
        id="acc-016",
        category="account",
        name="Savings Account Closure",
        formNumber="ACC-010",
        description="Close a savings bank account.",
        helpText=(
            "Permanently close your savings account."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Close a savings bank account permanently.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When you no longer need the account or want to consolidate accounts.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Savings account holders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "No more account maintenance fees, simplified banking.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, account closure declaration.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Savings Account Closure, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank closes the account and returns remaining balance."
        ),
        eligibility="Savings account holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for account closure.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="Other Service-specific Declaration",
                mandatory=True,
                purpose="Account closure request declaration.",
                extractedFields=["declaration_type", "declaration_date"],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    "acc-017": BankingService(
        id="acc-017",
        category="account",
        name="Current Account Closure",
        formNumber="ACC-011",
        description="Close a current bank account.",
        helpText=(
            "Permanently close your current account."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Close a current bank account permanently.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When you close your business or no longer need the current account.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Current account holders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "No more account maintenance fees, business closure documentation.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, Business Registration, closure declaration.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Current Account Closure, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank closes the account and returns remaining balance."
        ),
        eligibility="Current account holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for account closure.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="Business Registration",
                mandatory=True,
                purpose="Business registration for closure verification.",
                extractedFields=["business_name", "registration_number"],
                alternatives=["GST certificate", "Shop establishment license"],
            ),
            DocumentRequirement(
                name="Other Service-specific Declaration",
                mandatory=True,
                purpose="Account closure request declaration.",
                extractedFields=["declaration_type", "declaration_date"],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    "acc-018": BankingService(
        id="acc-018",
        category="account",
        name="Fixed Deposit Closure",
        formNumber="ACC-012",
        description="Close a fixed deposit account before or at maturity.",
        helpText=(
            "Close your FD and withdraw the maturity amount."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Close a fixed deposit account before maturity or at maturity.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When you need the funds or want to reinvest elsewhere.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Fixed deposit holders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Access to deposited funds, closure documentation.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, closure declaration.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Fixed Deposit Closure, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank closes the FD and pays the maturity/premature amount."
        ),
        eligibility="Fixed deposit holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for FD closure.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="Other Service-specific Declaration",
                mandatory=True,
                purpose="Fixed deposit closure request declaration.",
                extractedFields=["declaration_type", "declaration_date"],
            ),
        ],
        estimatedTime="10-15 min",
    ),

    "acc-019": BankingService(
        id="acc-019",
        category="account",
        name="Recurring Deposit Closure",
        formNumber="ACC-013",
        description="Close a recurring deposit account.",
        helpText=(
            "Close your RD and withdraw the accumulated amount."
        ),
        fullExplanation=(
            "<b>1. What is this service?</b><br>"
            "Close a recurring deposit account before or at maturity.<br><br>"
            "<b>2. Why would someone need it?</b><br>"
            "When you need the accumulated funds or want to stop monthly deposits.<br><br>"
            "<b>3. Who is eligible?</b><br>"
            "Recurring deposit holders.<br><br>"
            "<b>4. What are its benefits?</b><br>"
            "Access to accumulated savings, closure documentation.<br><br>"
            "<b>5. What documents are needed?</b><br>"
            "Aadhaar Card, closure declaration.<br><br>"
            "<b>6. What is the application procedure?</b><br>"
            "Select Recurring Deposit Closure, scan documents, confirm details, "
            "and generate the application PDF.<br><br>"
            "<b>7. What happens after submitting?</b><br>"
            "The bank closes the RD and pays the accumulated amount."
        ),
        eligibility="Recurring deposit holders.",
        documents=[
            DocumentRequirement(
                name="Aadhaar Card",
                mandatory=True,
                purpose="Identity verification for RD closure.",
                extractedFields=["full_name"],
                alternatives=["Passport", "Voter ID"],
            ),
            DocumentRequirement(
                name="Other Service-specific Declaration",
                mandatory=True,
                purpose="Recurring deposit closure request declaration.",
                extractedFields=["declaration_type", "declaration_date"],
            ),
        ],
        estimatedTime="10-15 min",
    ),
}


def get_all_services() -> List[BankingService]:
    """Return all services sorted by category and ID."""
    return sorted(SERVICES.values(), key=lambda s: (s.category, s.id))


def get_services_by_category(category: str) -> List[BankingService]:
    """Return services filtered by category."""
    return sorted(
        [s for s in SERVICES.values() if s.category == category],
        key=lambda s: s.id,
    )


def get_service(service_id: str) -> BankingService | None:
    """Return a single service by ID, or None if not found."""
    return SERVICES.get(service_id)


def get_categories() -> List[Dict[str, str]]:
    """Return the list of service categories."""
    return [
        {
            "key": "account",
            "label": "Account Services & Maintenance",
        },
        {
            "key": "cards",
            "label": "Cards & Cheque Services",
        },
        {
            "key": "loans",
            "label": "Loans & Credit Facilities",
        },
        {
            "key": "investments",
            "label": "Investments, Insurance & Wealth Management",
        },
    ]
