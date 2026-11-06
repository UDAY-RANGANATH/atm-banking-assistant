"""
Application PDF Generation and Document Export API (Phase 6).

Endpoints (all enforce session ownership):
    POST   /api/applications/{id}/generate-pdf   generate (or regenerate)
    GET    /api/applications/{id}/pdf            download/preview bytes
    GET    /api/applications/{id}/pdf/status     status + completion info
    DELETE /api/applications/{id}/pdf            remove the generated file

Security & compliance notes:
    - Generation is gated: a PDF is only produced from fields the customer
      individually reviewed (customer-confirmed or customer-edited);
      the gate re-checks form_service.completion_status at generation time.
    - No public PDF URL is created: files live under the controlled
      backend/generated_pdfs/{session_key}/ location (no static mount),
      are served only after an ownership check, and are purged when the
      session expires or is deleted.
    - Bytes are streamed from memory; nothing sensitive is logged.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.services.form_service import (
    FormApplicationError,
    completion_status,
    get_application_for_session,
)
from app.services.pdf_engine import (
    PdfGenerationError,
    delete_pdf,
    generate_application_pdf,
    pdf_info,
    read_pdf_bytes,
)

router = APIRouter(prefix="/applications")


class GeneratePdfRequest(BaseModel):
    session_id: str = Field(min_length=8)
    language: Optional[str] = None


def _owned_application(application_id: str, session_id: str):
    try:
        return get_application_for_session(application_id, session_id)
    except FormApplicationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


def _pdf_http_error(exc: PdfGenerationError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/{application_id}/generate-pdf")
async def generate_pdf(application_id: str, req: GeneratePdfRequest):
    """Generate the application PDF from customer-confirmed data."""
    app_row = _owned_application(application_id, req.session_id)
    try:
        meta = generate_application_pdf(app_row, language=req.language or "en")
    except PdfGenerationError as exc:
        raise _pdf_http_error(exc)
    return meta


@router.get("/{application_id}/pdf/status")
async def get_pdf_status(application_id: str, session_id: str):
    """Generation status + completion/readiness info (no file bytes)."""
    app_row = _owned_application(application_id, session_id)
    completed = completion_status(app_row)
    info = pdf_info(app_row)
    return {
        "application_id": app_row.reference_number,
        "service_id": app_row.service_id,
        "service_name": app_row.service_name,
        "form_number": app_row.form_number,
        "pdf_exists": info is not None,
        "pdf": info,
        "completion": completed,
    }


@router.get("/{application_id}/pdf")
async def download_pdf(application_id: str, session_id: str):
    """Return the stored PDF bytes (inline; no-cache; no public URL)."""
    app_row = _owned_application(application_id, session_id)
    try:
        data = read_pdf_bytes(app_row)
    except PdfGenerationError as exc:
        raise _pdf_http_error(exc)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{app_row.reference_number}.pdf"',
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@router.delete("/{application_id}/pdf")
async def delete_application_pdf(application_id: str, session_id: str):
    """Delete the generated PDF file for this application."""
    app_row = _owned_application(application_id, session_id)
    deleted = delete_pdf(app_row)
    return {
        "application_id": app_row.reference_number,
        "status": "deleted" if deleted else "not_found",
    }
