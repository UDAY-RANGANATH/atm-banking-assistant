"""
AI Assistant Engine (Phase 7).

Single orchestrator behind every chat route (POST /api/chat keeps the Phase 1
`{response, source, session_id}` contract; POST /api/ai/chat returns the
rich Phase 7 response).

Flow per message:
1. sanitise the user input (privacy §10; PAN/Aadhaar/OTP/PIN/CVV values masked),
2. classify against the safety guardrails (real transactions / shared secrets),
3. handle explicit mid-session language-switch requests,
4. detect message script language (mixed-language tolerant),
5. retrieve knowledge from the REAL service/document catalogues,
6. when a provider is configured, consult the LLM under guardrails (bounded
   timeout, limited retries, rate-limit cooldown) and validate the reply,
7. otherwise emit the deterministic catalogue-grounded answer.

The ATM never depends on the external AI provider: unconfigured, slow,
rate-limited, erroring or unsafe provider behaviour all fall back to the
deterministic engine. Conversation history and context live in
ai_conversation.conversation_store and are purged together with the kiosk
session; nothing is logged with customer text.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session as DBSession

from app.core.config import get_settings
from app.db.database import SessionLocal
from app.models import Application as ApplicationModel
from app.services.ai_provider import AIProviderError, LLMProvider
from app.services.ai_prompts import build_messages
from app.services.ai_conversation import conversation_store
from app.services.ai_safety import (
    REFUSAL_FOR_SECRET,
    REFUSAL_FOR_TRANSACTION,
    evaluate_input,
    sanitize_user_input,
    validate_provider_reply,
)
from app.services.ai_knowledge import (
    LANG_NAMES,
    SUGGESTIONS,
    SUPPORTED_LANGUAGES,
    TEMPLATES,
    detect_language,
    find_service,
    format_categories_list,
    format_document_list,
    glossary_answer,
    definition_cue,
    match_form_number,
    language_switch_request,
    match_intent,
)
from app.services.banking_services import SERVICES, BankingService
from app.services.session import session_service
from app.services import form_service

# Answer provenance values surfaced in the API
SOURCE_ENGINE = "assistant"     # deterministic catalogue-grounded answer
SOURCE_PROVIDER = "provider"    # validated reply from the configured LLM
SOURCE_FALLBACK = "fallback"    # provider failed/unsafe -> deterministic
SOURCE_SAFETY = "safety"        # guardrail refusal (no provider consulted)

_NO_SERVICE_PROMPT = {
    "en": ("Please name the service first — for example \"savings account\", "
           "\"home loan\" or \"debit card\" — then I can explain its documents, "
           "eligibility or procedure."),
    "te": ("ముందస్తుగా సేవ పేరు చెప్పండి — ఉదా: \"సేవింగ్స్ ఖాతా\", \"హోమ్ లోన్\", \"డెబిట్ కార్డ్\" — "
           "అప్పుడు దాని డాక్యుమెంట్లు, అర్హత లేదా విధానం వివరిస్తాను."),
    "hi": ("कृपया पहले सेवा बताएं — जैसे \"सेविंग्स खाता\", \"होम लोन\", \"डेबिट कार्ड\" — "
           "फिर मैं उसके दस्तावेज़, पात्रता या प्रक्रिया समझा सकता हूँ।"),
}

_ASPECT_INTENTS = ("documents", "eligibility", "procedure", "time")


class AIAssistantEngine:
    """Facade used by the API layer (also aliased as the historical AIService)."""

    def __init__(self):
        self.settings = get_settings()
        self.provider = LLMProvider(
            provider=self.settings.AI_PROVIDER,
            api_key=self.settings.AI_API_KEY,
            base_url=self.settings.AI_BASE_URL,
            model=self.settings.AI_MODEL,
            timeout=self.settings.AI_TIMEOUT_SECONDS,
            max_retries=self.settings.AI_MAX_RETRIES,
            rate_limit_cooldown=self.settings.AI_RATE_LIMIT_COOLDOWN,
        )
        self.history_store = conversation_store
        self._last_provider_latency_s: Optional[float] = None
        # Injection seam for automated tests / deployments.
        self._injected_provider: Optional[Any] = None

    # ------------------------------------------------------------------
    # Configuration / health
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        return self.provider.is_configured() or self._injected_provider is not None

    def set_provider_for_testing(self, provider: Optional[Any]) -> None:
        self._injected_provider = provider

    def status(self) -> Dict[str, Any]:
        info = self.provider.status()
        info["conversation_sessions"] = self.history_store.active_count()
        info["active_source"] = (
            "provider" if self.is_configured() else "assistant"
        )
        return info

    # ------------------------------------------------------------------
    # Main entry point (Phase 7 response shape)
    # ------------------------------------------------------------------

    async def answer(
        self,
        session_id: str,
        message: str,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        session = session_service.get_session(session_id)
        if session is None:
            raise KeyError("session_not_found")

        selected = language or session.get("language") or "en"
        selected = selected if selected in SUPPORTED_LANGUAGES else "en"

        # Sanitised copy — this is what both the local engine and the provider
        # ever see; identifiers are masked and secrets never become context.
        sanitized = sanitize_user_input(
            message, max_length=self.settings.AI_MAX_MESSAGE_LENGTH
        )
        lowered = sanitized.lower()

        # -- Safety: real transactions / shared secrets ---------------------
        safety_class = evaluate_input(message)
        if safety_class in ("real_transaction", "secret_sharing"):
            text = (
                REFUSAL_FOR_TRANSACTION[selected]
                if safety_class == "real_transaction"
                else REFUSAL_FOR_SECRET[selected]
            )
            self.history_store.add_message(session_id, "user", sanitized)
            self.history_store.add_message(session_id, "assistant", text)
            self.history_store.set_last_intent(session_id, "safety")
            return self._response(text, SOURCE_SAFETY, session_id, selected, [])

        # -- Explicit mid-session language switch ---------------------------
        switch = language_switch_request(lowered)
        if switch and switch != selected:
            session_service.set_language(session_id, switch)
            self.history_store.add_message(session_id, "user", sanitized)
            text = TEMPLATES["language_switched"][switch].format(
                langname=LANG_NAMES[switch]
            )
            self.history_store.add_message(session_id, "assistant", text)
            self.history_store.set_last_intent(session_id, "language")
            return self._response(text, SOURCE_ENGINE, session_id, switch, [])

        # -- Knowledge retrieval --------------------------------------------
        service = find_service(lowered)
        if service:
            self.history_store.set_last_service(session_id, service.id)
        else:
            service = self._service_from_history(session_id)
        intent = match_intent(lowered, selected)
        self.history_store.set_last_intent(session_id, intent or None)

        deterministic_text, actions = self._deterministic_answer(
            lowered, selected, intent, service, session_id,
            mentioned_form=match_form_number(lowered) is not None,
        )

        # -- Provider round-trip (only when configured) ----------------------
        if self.is_configured():
            provider_text = await self._consult_provider(
                session_id, sanitized, selected, service
            )
            if provider_text is not None:
                self.history_store.add_message(session_id, "user", sanitized)
                self.history_store.add_message(session_id, "assistant", provider_text)
                return self._response(
                    provider_text, SOURCE_PROVIDER, session_id, selected, actions
                )

        # -- Deterministic answer (also the failure-path fallback) -----------
        self.history_store.add_message(session_id, "user", sanitized)
        self.history_store.add_message(session_id, "assistant", deterministic_text)
        return self._response(deterministic_text, SOURCE_ENGINE, session_id, selected, actions)

    # ------------------------------------------------------------------
    # Legacy Phase 1 contract: {response, source, session_id}
    # ------------------------------------------------------------------

    async def generate_response(
        self,
        message: str,
        language: str = "en",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        session_id = (context or {}).get("session_id") if context else None
        if session_id and session_service.get_session(session_id):
            result = await self.answer(session_id, message, language)
            return {
                "response": result["response"],
                "source": result["source"],
                "session_id": session_id,
            }
        # No usable session context (library/testing use): deterministic.
        offline = await self.answer_offline(message, language)
        return {
            "response": offline["response"],
            "source": offline["source"],
            "session_id": session_id or "",
        }

    async def answer_offline(self, message: str, language: str = "en") -> Dict[str, Any]:
        """Deterministic engine without a kiosk session."""
        selected = language if language in SUPPORTED_LANGUAGES else "en"
        lowered = sanitize_user_input(message, max_length=300).lower()
        service = find_service(lowered)
        intent = match_intent(lowered, selected)
        text, _actions = self._deterministic_answer(
            lowered, selected, intent, service, None,
            mentioned_form=match_form_number(lowered) is not None,
        )
        return {"response": text, "source": SOURCE_ENGINE}

    # ------------------------------------------------------------------
    # Deterministic catalogue-grounded engine
    # ------------------------------------------------------------------

    def _deterministic_answer(
        self,
        lowered: str,
        language: str,
        intent: str,
        service: Optional[BankingService],
        session_id: Optional[str],
        mentioned_form: bool = False,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Every answer is grounded in SERVICES / document mappings. `language`
        is the customer's SELECTED language — the assistant always replies in
        the selected language, tolerating other-language input."""

        def templ(key: str) -> str:
            return TEMPLATES[key][language]

        actions: List[Dict[str, Any]] = self._service_nav(service)

        if intent == "greeting":
            return templ("greeting").format(example=SUGGESTIONS[language][1]), actions

        if intent == "list_services":
            categories = format_categories_list(language)
            return templ("list_categories").format(list=categories), []

        if intent in _ASPECT_INTENTS and service is None:
            return _NO_SERVICE_PROMPT[language], []

        if intent == "documents" and service is not None:
            listing = format_document_list(service, language)
            note = {
                "en": "(Grounded in the real document checklist; mandatory items first.)",
                "te": "(అసలు డాక్యుమెంట్ చెక్‌లిస్ట్ ఆధారంగా; తప్పనిసరి అవే మొదట.)",
                "hi": "(वास्तविक दस्तावेज़ चेकलिस्ट पर आधारित; आवश्यक पहले।)",
            }[language]
            return (
                TEMPLATES["documents"][language].format(
                    name=service.name, list=listing, note=note
                ),
                actions,
            )

        if intent == "eligibility" and service is not None:
            return (
                TEMPLATES["eligibility"][language].format(
                    name=service.name, eligibility=service.eligibility
                ),
                actions,
            )

        if intent == "procedure" and service is not None:
            return (
                TEMPLATES["procedure"][language].format(
                    name=service.name, form=service.formNumber
                ),
                actions,
            )

        if intent == "time" and service is not None:
            return (
                TEMPLATES["time"][language].format(
                    name=service.name, time=service.estimatedTime
                ),
                actions,
            )

        if intent == "progress":
            return self._progress_answer(session_id, language), []

        if intent == "pdf":
            return templ("pdf"), []

        if intent == "autofill":
            return templ("autofill"), []

        if intent == "scan_rejection":
            return templ("scan_rejection"), []

        if intent == "unavailable_fees":
            return templ("unavailable"), []

        gloss = glossary_answer(lowered, language)
        if gloss and (
            service is None or (definition_cue(lowered) and not mentioned_form)
        ):
            return gloss, []

        if service is not None:
            return (
                TEMPLATES["service_intro"][language].format(
                    name=service.name,
                    form=service.formNumber,
                    description=service.description,
                    eligibility=service.eligibility,
                    time=service.estimatedTime,
                ),
                actions,
            )

        return templ("fallback"), []

    # ------------------------------------------------------------------
    # Application progress grounded in the Phase 5 application store
    # ------------------------------------------------------------------

    def progress_for_session(self, session_id: str, language: str) -> str:
        return self._progress_answer(session_id, language)

    def _progress_answer(self, session_id: Optional[str], language: str) -> str:
        if not session_id:
            return TEMPLATES["progress_none"][language]
        application = self._latest_application(session_id)
        if application is None:
            return TEMPLATES["progress_none"][language]
        status = form_service.completion_status(application)
        svc = SERVICES.get(application.service_id)
        counts = status["counts"]
        pending = counts.get("MISSING", 0) + counts.get("LOW_CONFIDENCE", 0) + counts.get("CONFLICT", 0)
        confirmed = counts.get("CUSTOMER_CONFIRMED", 0) + counts.get("CUSTOMER_EDITED", 0)
        return TEMPLATES["progress_found"][language].format(
            ref=application.reference_number,
            name=svc.name if svc else application.service_id,
            completed=status["filled_fields"],
            total=status["total_fields"],
            pending=pending,
            confirmed=confirmed,
        )

    @staticmethod
    def _latest_application(session_id: str) -> Optional[ApplicationModel]:
        db: DBSession = SessionLocal()
        try:
            return (
                db.query(ApplicationModel)
                .filter(ApplicationModel.session_key == session_id)
                .order_by(ApplicationModel.id.desc())
                .first()
            )
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Provider consultation
    # ------------------------------------------------------------------

    async def _consult_provider(
        self,
        session_id: str,
        sanitized_message: str,
        language: str,
        service: Optional[BankingService],
    ) -> Optional[str]:
        """Return the validated reply text, or None when the provider failed,
        timed out, was rate-limited or produced a guardrail-violating reply."""
        history = self.history_store.get_history(session_id)[-12:]
        extra = ""
        application = self._latest_application(session_id)
        if application is not None:
            # Reference number and service only — no customer identifiers.
            extra = (
                f"ACTIVE_APPLICATION: reference={application.reference_number}; "
                f"service_id={application.service_id}; "
                f"status={application.status}"
            )
        messages = build_messages(sanitized_message, language, service, history, extra)
        start = time.monotonic()
        try:
            if self._injected_provider is not None:
                reply = await self._call_injected(messages)
            else:
                reply = await self.provider.complete(messages)
        except AIProviderError:
            self._last_provider_latency_s = time.monotonic() - start
            return None
        except Exception:
            self._last_provider_latency_s = time.monotonic() - start
            return None
        rejection = validate_provider_reply(reply)
        if rejection is not None:
            return None
        return reply

    async def _call_injected(self, messages: List[Dict[str, str]]) -> str:
        provider = self._injected_provider
        # Accept either an object exposing .complete() or a bare async callable
        if hasattr(provider, "complete"):
            result = await provider.complete(messages)
        else:
            result = await provider(messages)
        if not isinstance(result, str) or not result.strip():
            raise AIProviderError("provider_empty_response")
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _service_from_history(self, session_id: str) -> Optional[BankingService]:
        last = self.history_store.get_last_service(session_id)
        if last:
            return SERVICES.get(last)
        return None

    def _service_nav(self, service: Optional[BankingService]) -> List[Dict[str, Any]]:
        """The assistant only OFFERS navigation; the customer taps the button —
        it never silently modifies workflow state."""
        if service is None:
            return []
        return [
            {
                "type": "navigate_service",
                "service_id": service.id,
                "label": service.name,
            }
        ]

    def _response(
        self,
        text: str,
        source: str,
        session_id: str,
        language: str,
        actions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "response": text,
            "source": source,
            "session_id": session_id,
            "language": language,
            "actions": actions,
            "suggestions": SUGGESTIONS[language],
        }


ai_service = AIAssistantEngine()

# Backwards-compatible alias for existing imports of AIService
AIService = AIAssistantEngine
