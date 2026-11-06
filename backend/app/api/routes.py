from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.services.session import session_service
from app.services.scanner import scan_store
from app.services.ai import ai_service
from app.services.ai_conversation import conversation_store
from app.services.banking_services import (
    get_all_services,
    get_services_by_category,
    get_service,
    get_categories,
    BankingService,
)
from app.services.document_engine import (
    DocumentDefinition,
    ServiceDocumentMapping,
    DocumentChecklist,
    ChecklistUpdate,
    ChecklistProgress,
    DocumentRequirementStatus,
    get_document_catalogue,
    get_document_by_id,
    get_service_mappings,
    get_checklist_for_service,
    get_application_checklist,
    update_checklist_status,
    get_checklist_progress,
    DOCUMENT_CATALOGUE,
    SERVICE_DOCUMENT_MAPPINGS,
)


router = APIRouter()


class LanguageSelectRequest(BaseModel):
    session_id: str
    language: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    source: str
    session_id: str


class SessionResponse(BaseModel):
    session_id: str
    language: str
    current_step: str


# ---------------------------------------------------------------------------
# Service Catalogue Request/Response Models
# ---------------------------------------------------------------------------

class DocumentRequirementResponse(BaseModel):
    name: str
    mandatory: bool
    conditional: bool
    purpose: str
    extractedFields: List[str]
    alternatives: List[str]


class BankingServiceResponse(BaseModel):
    id: str
    category: str
    name: str
    formNumber: str
    isPrototype: bool
    description: str
    helpText: str
    fullExplanation: str
    eligibility: str
    documents: List[DocumentRequirementResponse]
    estimatedTime: str


class CategoryResponse(BaseModel):
    key: str
    label: str


# ---------------------------------------------------------------------------
# Health & Session Endpoints (Phase 1 - preserved)
# ---------------------------------------------------------------------------

@router.get("/health")
async def health():
    return {"status": "ok", "service": "AI Banking Assistant"}


@router.post("/session", response_model=SessionResponse)
async def create_session(language: str = "en"):
    session_id = session_service.create_session(language=language)
    return SessionResponse(
        session_id=session_id,
        language=language,
        current_step="language_selection",
    )


@router.post("/session/language", response_model=SessionResponse)
async def set_language(req: LanguageSelectRequest):
    success = session_service.set_language(req.session_id, req.language)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    sess = session_service.get_session(req.session_id)
    return SessionResponse(
        session_id=req.session_id,
        language=sess["language"],
        current_step=sess["current_step"],
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    sess = session_service.get_session(req.session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    # Phase 7: the legacy Phase 1 contract now delegates to the full
    # multilingual engine; the response shape stays {response, source, session_id}.
    result = await ai_service.generate_response(
        message=req.message,
        language=sess["language"],
        context={"session_id": req.session_id},
    )
    return ChatResponse(
        response=result["response"],
        source=result.get("source", "mock"),
        session_id=req.session_id,
    )


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    sess = session_service.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(
        session_id=session_id,
        language=sess["language"],
        current_step=sess["current_step"],
    )


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    session_service.cleanup_session(session_id)
    # Expire/cleanup: remove scans (incl. temp files), applications and
    # generated PDFs that belonged to this session (Phases 4 + 5 + 6),
    # and the AI conversation history (Phase 7).
    scan_store.purge_session(session_id)
    conversation_store.purge_session(session_id)
    from app.services.form_service import purge_session_data
    purge_session_data(session_id)
    from app.services import pdf_engine
    pdf_engine.purge_session(session_id)
    pdf_engine.purge_expired()
    return {"status": "cleaned"}


# ---------------------------------------------------------------------------
# Service Catalogue Endpoints (Phase 2)
# ---------------------------------------------------------------------------

@router.get("/services/categories", response_model=List[CategoryResponse])
async def get_service_categories():
    """Return all service categories."""
    return get_categories()


@router.get("/services", response_model=List[BankingServiceResponse])
async def list_services(category: Optional[str] = None):
    """Return all services, optionally filtered by category."""
    if category:
        services = get_services_by_category(category)
    else:
        services = get_all_services()
    return services


@router.get("/services/{service_id}", response_model=BankingServiceResponse)
async def get_service_details(service_id: str):
    """Return detailed information for a single service."""
    svc = get_service(service_id)
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")
    return svc


# ---------------------------------------------------------------------------
# Application Start Endpoint (Phase 2)
# ---------------------------------------------------------------------------

class StartApplicationRequest(BaseModel):
    session_id: str
    service_id: str


class StartApplicationResponse(BaseModel):
    session_id: str
    service_id: str
    service_name: str
    form_number: str
    current_step: str


@router.post("/application/start", response_model=StartApplicationResponse)
async def start_application(req: StartApplicationRequest):
    """Start an application for a given service and update session context."""
    sess = session_service.get_session(req.session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    svc = get_service(req.service_id)
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    # Update session with selected service
    session_service.update_session(
        req.session_id,
        {
            "selected_service": req.service_id,
            "current_step": "service_selected",
        },
    )

    return StartApplicationResponse(
        session_id=req.session_id,
        service_id=req.service_id,
        service_name=svc.name,
        form_number=svc.formNumber,
        current_step="service_selected",
    )


# ---------------------------------------------------------------------------
# Document Requirement Engine Endpoints (Phase 3)
# ---------------------------------------------------------------------------

@router.get("/documents/catalogue", response_model=List[DocumentDefinition])
async def get_documents_catalogue():
    """Return all document definitions in the catalogue."""
    return get_document_catalogue()


@router.get("/documents/service/{service_id}", response_model=List[ServiceDocumentMapping])
async def get_documents_for_service(service_id: str):
    """Return all document mappings for a specific service."""
    mappings = get_service_mappings(service_id)
    if not mappings:
        # Check if service exists
        svc = get_service(service_id)
        if not svc:
            raise HTTPException(status_code=404, detail="Service not found")
    return mappings


@router.get("/documents/{document_id}", response_model=DocumentDefinition)
async def get_document_detail(document_id: str):
    """Return a single document definition by ID."""
    doc = get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/documents/service/{service_id}/checklist", response_model=DocumentChecklist)
async def get_service_checklist(service_id: str, application_id: Optional[str] = None):
    """Return the resolved document checklist for a service.

    When application_id is given, per-application statuses (set e.g. by the
    scanner workflow) override the base statuses.
    """
    svc = get_service(service_id)
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")
    if application_id:
        return get_application_checklist(
            service_id=service_id,
            service_name=svc.name,
            form_number=svc.formNumber,
            application_id=application_id,
        )
    return get_checklist_for_service(
        service_id=service_id,
        service_name=svc.name,
        form_number=svc.formNumber,
    )


@router.post("/documents/checklist/{application_id}/update")
async def update_checklist_item(application_id: str, update: ChecklistUpdate):
    """Update a document's status in an application's checklist."""
    update_checklist_status(
        application_id=application_id,
        document_id=update.document_id,
        status=update.status,
    )
    return {"status": "updated", "application_id": application_id, "document_id": update.document_id}


@router.get("/documents/checklist/{application_id}/progress", response_model=ChecklistProgress)
async def get_checklist_progress_endpoint(application_id: str, service_id: str):
    """Return progress summary for an application's document checklist."""
    progress = get_checklist_progress(application_id=application_id, service_id=service_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Checklist not found")
    return progress
