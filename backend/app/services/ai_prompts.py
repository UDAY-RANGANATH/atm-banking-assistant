"""
Prompt Management (Phase 7).

Builds the system prompt and message list for the configured LLM provider.

The prompt bakes in the banking guardrails (§7), the multilingual contract
(§4) and the privacy contract (§10):
- never request PIN / CVV / OTP / passwords,
- never claim real account access, real transactions, official document
  verification or a real submission to HDFC Bank,
- never invent fees, interest rates, eligibility or policy beyond the supplied
  catalogue extracts,
- reply in the customer's selected language,
- never translate names, addresses, account numbers or extracted personal
  information.

Only compact, already-sanitised context is embedded in prompts: the current
service metadata and conversational history — never document images, raw OCR
data, or personal identifier values.
"""

from typing import Any, Dict, List, Optional

from app.services.banking_services import BankingService
from app.services.document_engine import get_service_mappings

GUARDRAILS_LANGUAGE_ONLY = (
    "Reply ONLY in {language_name}, keeping the reply short, clear and suitable "
    "for a bank ATM kiosk screen. Follow these strict rules:\n"
    "1. You assist an EDUCATIONAL ATM banking PROTOTYPE, not a real bank.\n"
    "2. Never claim real account access, real transactions, real submission of an "
    "application to a bank, or official verification of documents.\n"
    "3. Never ask for PIN, CVV, OTP or passwords; warn users who try to share them.\n"
    "4. Refuse real banking transactions and explain the prototype cannot perform them.\n"
    "5. Use ONLY the banking facts in the context; never invent availability, "
    "eligibility, fees, interest rates or policy; say when information is unavailable.\n"
    "6. Never translate names, addresses, account numbers or extracted personal "
    "information; keep banking terms and numbers unchanged.\n"
    "7. Guide users to the relevant screens instead of claiming to modify fields, "
    "confirm documents, approve applications or generate PDFs yourself."
)

SERVICE_TOPICS = {
    "en": "You explain available services, eligibility, document requirements, the "
          "application procedure, prototype form numbers, application progress and "
          "common banking terms.",
    "te": "అందుబాటులో ఉన్న సేవలు, అర్హత, అవసరమైన డాక్యుమెంట్లు, దరఖాస్తు విధానం, ప్రోటోటైప్ ఫారం నంబర్లు, దరఖాస్తు స్థితి మరియు బ్యాంకింగ్ పదాలను వివరించడం మీ పని.",
    "hi": "आप उपलब्ध सेवाएं, पात्रता, आवश्यक दस्तावेज़, आवेदन प्रक्रिया, प्रोटोटाइप फ़ॉर्म नंबर, आवेदन की स्थिति और सामान्य बैंकिंग शब्द समझाते हैं।",
}


def build_system_prompt(language: str) -> str:
    lang = language if language in ("en", "te", "hi") else "en"
    language_name = {"en": "English", "te": "Telugu (తెలుగు)", "hi": "Hindi (हिंदी)"}[lang]
    rules = (
        GUARDRAILS_LANGUAGE_ONLY.replace("{language_name}", language_name)
        + "\n"
        + SERVICE_TOPICS.get(lang, SERVICE_TOPICS["en"])
    )
    return rules


def describe_service_for_prompt(svc: Optional[BankingService], language: str) -> str:
    """Compact service fact sheet for the prompt (catalogue data only)."""
    if svc is None:
        return ""
    doc_lines = []
    for mapping in get_service_mappings(svc.id):
        role = "mandatory" if mapping.mandatory and not mapping.conditional else (
            "conditional" if mapping.conditional else "optional"
        )
        doc_lines.append(f"{mapping.document_id} ({role})")
    return (
        f"SERVICE: id={svc.id}; name={svc.name}; prototype_form_number={svc.formNumber}; "
        f"category={svc.category}; description={svc.description}; "
        f"eligibility={svc.eligibility}; estimated_time={svc.estimatedTime}; "
        f"documents={'; '.join(doc_lines)}"
    )


def build_messages(
    sanitized_message: str,
    language: str,
    service: Optional[BankingService],
    history: List[Dict[str, str]],
    extra_context: str = "",
) -> List[Dict[str, str]]:
    """Full provider message list: system rules + compact context + history."""
    lang = language if language in ("en", "te", "hi") else "en"
    language_name = {"en": "English", "te": "Telugu (తెలుగు)", "hi": "Hindi (हिंदी)"}[lang]
    context_parts = [
        f"Customer selected language: {language_name}. Reply in {language_name}.",
        describe_service_for_prompt(service, lang),
    ]
    if extra_context:
        context_parts.append(extra_context)
    context = "\n".join(p for p in context_parts if p)
    messages = [{"role": "system", "content": build_system_prompt(lang) + "\n\nCONTEXT:\n" + context}]
    # Bounded history (already sanitised when stored)
    messages.extend(history[-12:])
    messages.append({"role": "user", "content": sanitized_message})
    return messages
