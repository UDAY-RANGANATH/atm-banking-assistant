"""
AI Assistant API routes (Phase 7).

Endpoints:
- POST /api/ai/chat                       -> rich chat response + actions + suggestions
- GET  /api/ai/health                     -> provider/model status (no secrets)
- POST /api/ai/health/probe?              -> optional: live provider ping (bounded; never on the critical path)
- GET  /api/ai/suggestions                -> language-aware suggested questions
- DELETE /api/ai/conversation/{session}   -> clear one conversation (ownership enforced)

The legacy POST /api/chat in routes.py is unchanged in contract: it now
delegates to the same engine so Phase 1 tests keep passing.

Privacy: no document images or OCR payloads pass through these routes; bodies
are sanitised in the engine before any external call. Message contents are
never logged. DELETE requires the caller to prove it owns the conversation by
sending the same session id as X-Session-Id (the kiosk client always has its
own session id); mismatches are rejected with 403.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from app.services.ai import ai_service
from app.services.ai_conversation import conversation_store
from app.services.ai_knowledge import SUGGESTIONS, SUPPORTED_LANGUAGES
from app.services.session import session_service

router = APIRouter(prefix="/ai")


class AIChatRequest(BaseModel):
    session_id: str
    message: str
    language: Optional[str] = None


class AIChatAction(BaseModel):
    type: str
    service_id: Optional[str] = None
    label: Optional[str] = None


class AIChatResponse(BaseModel):
    response: str
    source: str
    session_id: str
    language: str
    actions: List[AIChatAction]
    suggestions: List[str]


class AIHealthResponse(BaseModel):
    provider: str
    configured: bool
    model: str
    active_source: str
    rate_limited: bool
    last_error: Optional[str] = None
    last_ok_at: Optional[float] = None
    language_detection: str
    knowledge_source: str
    conversation_sessions: int


class AISuggestionsResponse(BaseModel):
    language: str
    suggestions: List[str]


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(req: AIChatRequest):
    try:
        result = await ai_service.answer(
            req.session_id, req.message, req.language
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")
    return AIChatResponse(**result)


# ---------------------------------------------------------------------------
# Health (no network call by default; probe=1 performs a bounded ping)
# ---------------------------------------------------------------------------

@router.get("/health", response_model=AIHealthResponse)
async def ai_health(probe: Optional[str] = None):
    status = ai_service.status()
    response = AIHealthResponse(
        provider=status["provider"],
        configured=status["configured"],
        model=status["model"],
        active_source=status["active_source"],
        rate_limited=status.get("rate_limited", False),
        last_error=status.get("last_error"),
        last_ok_at=status.get("last_ok_at"),
        language_detection="en/te/hi script-based",
        knowledge_source="banking_services + document_engine catalogues",
        conversation_sessions=status["conversation_sessions"],
    )
    if probe in ("1", "true"):
        # Explicit opt-in only: a live round-trip must never slow the UI path.
        ok = await ai_service.provider.health_ping()
        response.last_error = None if ok else (ai_service.provider._last_error or "provider_unreachable")
        response.last_ok_at = ai_service.provider._last_ok_at if ok else response.last_ok_at
    return response


# ---------------------------------------------------------------------------
# Suggestions
# ---------------------------------------------------------------------------

@router.get("/suggestions", response_model=AISuggestionsResponse)
async def ai_suggestions(session_id: Optional[str] = None,
                         language: Optional[str] = None):
    lang = language or "en"
    if session_id:
        session = session_service.get_session(session_id)
        if session and session.get("language") in SUPPORTED_LANGUAGES:
            lang = session["language"]
    if lang not in SUGGESTIONS:
        lang = "en"
    return AISuggestionsResponse(language=lang, suggestions=SUGGESTIONS[lang])


# ---------------------------------------------------------------------------
# Conversation cleanup (ownership enforced)
# ---------------------------------------------------------------------------

@router.delete("/conversation/{session_id}")
async def delete_conversation(
    session_id: str,
    x_session_id: Optional[str] = Header(default=None),
):
    if not x_session_id or x_session_id != session_id:
        raise HTTPException(
            status_code=403,
            detail="Conversation cleanup requires the owning session id in X-Session-Id",
        )
    existed = conversation_store.clear(session_id)
    return {"status": "cleared", "session_id": session_id, "existed": existed}
