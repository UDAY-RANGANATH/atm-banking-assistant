"""
Intelligent Application Form Autofill API (Phase 5).

Endpoints (all enforce session ownership):
  POST /api/applications/init                      create/reuse draft application
  GET  /api/applications/{id}/form                 form + populated fields
  POST /api/applications/{id}/autofill             run OCR->form autofill
  GET  /api/applications/{id}/field-mappings       introspect mapping registry
  PATCH /api/applications/{id}/fields/{field_id}   edit | clear | confirm | accept
  POST /api/applications/{id}/fields/confirm       confirm one/many fields
  POST /api/applications/{id}/save                 save progress
  GET  /api/applications/{id}/completion-status    readiness + warnings

Security & compliance notes:
  - Only masked/structured values ever leave the OCR layer; these endpoints
    never return unmasked identifiers.
  - Nothing here submits an application: "save" only persists draft state,
    and the frontend must require explicit customer confirmation.
  - No personal data is written to logs.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.form_service import (
    FormApplicationError,
    FormValidationError,
    _normalize_state,
    _persist,
    build_form_view,
    completion_status,
    confirm_fields,
    ensure_application,
    field_mappings_view,
    get_application_for_session,
    run_autofill,
    set_field,
)

router = APIRouter(prefix="/applications")


class InitApplicationRequest(BaseModel):
    session_id: str = Field(min_length=8)
    service_id: str = Field(min_length=4)


class FieldActionRequest(BaseModel):
    session_id: str
    action: str
    value: Optional[str] = None
    language: Optional[str] = None


class ConfirmFieldsRequest(BaseModel):
    session_id: str
    field_ids: List[str]


def _http_error(exc: FormApplicationError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


def _session_id(session_id: str) -> str:
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    return session_id


# ---------------------------------------------------------------------------
# Init + form views
# ---------------------------------------------------------------------------

@router.post("/init")
async def init_application(req: InitApplicationRequest):
    """Create (or reuse) the draft application for this session + service."""
    try:
        app_row = ensure_application(req.session_id, req.service_id)
    except FormApplicationError as exc:
        raise _http_error(exc)
    return build_form_view(app_row)


@router.get("/{application_id}/form")
async def get_application_form(
    application_id: str, session_id: str, language: Optional[str] = None
):
    try:
        app_row = get_application_for_session(application_id, _session_id(session_id))
    except FormApplicationError as exc:
        raise _http_error(exc)
    view = build_form_view(app_row)
    view["language"] = language
    return view


# ---------------------------------------------------------------------------
# Autofill
# ---------------------------------------------------------------------------

@router.post("/{application_id}/autofill")
async def autofill_application(
    application_id: str, session_id: str, language: Optional[str] = None
):
    try:
        app_row = get_application_for_session(application_id, _session_id(session_id))
        state = run_autofill(app_row)
    except FormApplicationError as exc:
        raise _http_error(exc)
    view = build_form_view(app_row, state)
    view["language"] = language
    return view


@router.get("/{application_id}/field-mappings")
async def get_field_mappings(application_id: str, session_id: str):
    try:
        app_row = get_application_for_session(application_id, _session_id(session_id))
    except FormApplicationError as exc:
        raise _http_error(exc)
    return {
        "application_id": application_id,
        "mappings": field_mappings_view(app_row.service_id),
    }


# ---------------------------------------------------------------------------
# Field operations
# ---------------------------------------------------------------------------

@router.patch("/{application_id}/fields/{field_id}")
async def patch_field(
    application_id: str, field_id: str, req: FieldActionRequest
):
    try:
        app_row = get_application_for_session(application_id, req.session_id)
        record = set_field(app_row, field_id, req.action, req.value)
    except FormValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.error_key)
    except FormApplicationError as exc:
        raise _http_error(exc)
    return {
        "application_id": application_id,
        "field_id": field_id,
        "record": record,
    }


@router.post("/{application_id}/fields/confirm")
async def confirm_application_fields(
    application_id: str, req: ConfirmFieldsRequest
):
    try:
        app_row = get_application_for_session(application_id, req.session_id)
        result = confirm_fields(app_row, req.field_ids)
    except FormApplicationError as exc:
        raise _http_error(exc)
    return {"application_id": application_id, **result}


# ---------------------------------------------------------------------------
# Save + completion
# ---------------------------------------------------------------------------

@router.post("/{application_id}/save")
async def save_application(application_id: str, session_id: str):
    try:
        app_row = get_application_for_session(application_id, _session_id(session_id))
    except FormApplicationError as exc:
        raise _http_error(exc)
    # Draft state is persisted on every mutation; save is an explicit
    # checkpoint acknowledgement (still NOT a submission).
    state = _normalize_state(app_row.application_data)
    saved_at = datetime.now(timezone.utc).isoformat()
    state["saved_at"] = saved_at
    _persist(app_row, state)
    return {
        "application_id": application_id,
        "status": "saved",
        "saved_at": saved_at,
        "note": "Draft saved. Nothing has been submitted.",
    }


@router.get("/{application_id}/completion-status")
async def get_completion_status(application_id: str, session_id: str):
    try:
        app_row = get_application_for_session(application_id, _session_id(session_id))
    except FormApplicationError as exc:
        raise _http_error(exc)
    return completion_status(app_row)
