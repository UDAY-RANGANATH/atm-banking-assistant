"""
Scanner API routes (Phase 4)

Endpoints:
  POST /api/scanner/upload                  - upload image from device
  POST /api/scanner/capture                 - submit camera capture
  POST /api/scanner/process/{scan_id}       - run preprocessing + OCR pipeline
  GET  /api/scanner/result/{scan_id}        - fetch scan result
  POST /api/scanner/confirm/{scan_id}       - customer confirms extraction
  POST /api/scanner/rescan/{scan_id}        - request rescan
  GET  /api/scanner/status/{session_id}     - scan statuses for a session
  GET  /api/scanner/image/{scan_id}         - processed/original preview image
  DELETE /api/scanner/{scan_id}             - delete scan + temp files
  POST /api/scanner/cleanup/{session_id}    - purge session temp files
  GET  /api/scanner/engine/status           - OCR engine availability & languages
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import cv2
import numpy as np
import json
import urllib.parse

from app.services.image_processing import (
    load_image, encode_jpeg, preprocess, assess_quality, quality_summary,
    ALLOWED_EXTENSIONS, MAX_FILE_BYTES,
)
from app.services.ocr_engine import get_ocr_service, UnsupportedLanguageError, AVAILABLE, AVAILABLE_LANGUAGES
from app.services.extraction import DOC_TYPE_BY_DOCUMENT_ID, process_scan_result
from app.services.scanner import (
    scan_store, TransitionError, validate_application_document,
    sync_checklist_status, TEMP_ROOT, record_time,
)
from app.services.session import session_service
from app.services.banking_services import get_service
from app.services.document_engine import get_service_mappings, get_checklist_for_service, get_application_checklist

router = APIRouter()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ProcessResponse(BaseModel):
    scan_id: str
    status: str
    quality: Dict[str, Any]
    result: Dict[str, Any]


class ConfirmRequest(BaseModel):
    corrections: Optional[Dict[str, str]] = None  # field -> corrected value (customer edit)


class ScanSummary(BaseModel):
    scan_id: str
    document_id: str
    service_id: str
    status: str
    quality_status: Optional[str] = None
    classification_match: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/webp", "image/bmp",
}


def _ext_for(content_type: str, filename: str) -> str:
    ct = (content_type or "").lower().split(";")[0].strip()
    if ct in {"image/jpeg", "image/jpg"}:
        return ".jpg"
    if ct == "image/png":
        return ".png"
    if ct == "image/webp":
        return ".webp"
    if ct == "image/bmp":
        return ".bmp"
    name = (filename or "").lower()
    for ext in ALLOWED_EXTENSIONS:
        if name.endswith(ext):
            return ext
    raise HTTPException(status_code=415, detail="Unsupported file type. Use JPEG, PNG, WEBP or BMP.")


def _validate_session(session_id: str) -> None:
    if session_id and not session_service.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")


def _fetch_scan(scan_id: str):
    record = scan_store.get(scan_id)
    if not record:
        raise HTTPException(status_code=404, detail="Scan not found")
    return record


def _run_pipeline(record: Dict[str, Any], languages: List[str]) -> Dict[str, Any]:
    """Preprocess -> quality -> OCR -> classify -> extract. No fabricated output.

    OCR runs on two preprocessing variants (enhanced grayscale and
    adaptively-thresholded) and the best-confidence result is kept.
    """
    original = load_image(record["original_path"])
    if original is None:
        raise HTTPException(status_code=422, detail="Could not read the stored image file.")

    processed, pre_info = preprocess(original, apply_threshold=False)
    processed_for_quality, _ = preprocess(original, apply_threshold=True)
    processed_path = record["original_path"].rsplit(".", 1)[0] + "_processed.jpg"
    data = encode_jpeg(processed)
    with open(processed_path, "wb") as fh:
        fh.write(data)

    quality = quality_summary(assess_quality(processed_for_quality, pre_info))

    ocr_service = get_ocr_service()
    ocr_result = None
    ocr_error = None
    if ocr_service is None:
        ocr_error = (
            "No OCR engine is installed. Please contact the kiosk operator; "
            "the scanned image has been saved and can be uploaded again once OCR is available."
        )
    else:
        try:
            # Best-of-two: enhanced grayscale vs adaptive threshold.
            attempt_a = ocr_service.run(processed, languages)
            attempt_b = None
            try:
                attempt_b = ocr_service.run(processed_for_quality, languages)
            except (RuntimeError, UnsupportedLanguageError):
                pass
            if attempt_b and attempt_b["confidence"] > attempt_a["confidence"]:
                # persist the better-quality image too
                better_path = record["original_path"].rsplit(".", 1)[0] + "_processed.jpg"
                with open(better_path, "wb") as fh:
                    fh.write(encode_jpeg(processed_for_quality))
                processed_path = better_path
                ocr_result = attempt_b
            else:
                ocr_result = attempt_a
        except UnsupportedLanguageError as exc:
            ocr_error = str(exc)
        except RuntimeError as exc:
            ocr_error = str(exc)

    record["processed_path"] = processed_path

    document_id = record["document_id"]
    if ocr_result is not None:
        result = process_scan_result(ocr_result, document_id)
    else:
        result = process_scan_result(None, document_id)
        if ocr_error:
            result["message"] = ocr_error

    result["preprocess"] = pre_info
    result["ocr_available"] = ocr_result is not None and result.get("ocr_available", True)

    record["quality"] = quality
    record["processed_path"] = processed_path
    record["ocr_available"] = "true" if result.get("ocr_available") else "false"
    record["result"] = result

    # Decide scan status from quality + result
    ocr_fields_empty = (
        result.get("extraction_status") in {"EMPTY_OCR", "OCR_UNAVAILABLE"}
        or (result.get("fields") and all(
            v.get("value") is None for v in result["fields"].values() if isinstance(v, dict)
        ))
    )
    if quality["status"] == "POOR" and ocr_fields_empty:
        new_status = "needs_rescan"
    elif not result.get("ocr_available") or result.get("extraction_status") == "EMPTY_OCR":
        new_status = "confirmation_pending"
    else:
        new_status = "confirmation_pending"

    try:
        scan_store.transition(record["scan_id"], new_status, extra={})
    except TransitionError:
        scan_store.force_status(record["scan_id"], new_status)
        record["status"] = new_status

    sync_checklist_status(record["session_id"], record)
    return {"record": record, "quality": quality, "result": result}


def _public_view(record: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize a scan record for the frontend (paths stripped)."""
    return {
        "scan_id": record["scan_id"],
        "session_id": record["session_id"],
        "service_id": record["service_id"],
        "document_id": record["document_id"],
        "source": record["source"],
        "status": record["status"],
        "created_at": record["created_at"],
        "quality": record.get("quality"),
        "result": record.get("result"),
        "confirmed_by_customer": record.get("confirmed_by_customer", False),
        "history": record.get("history"),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/scanner/upload", response_model=ProcessResponse)
async def scanner_upload(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    service_id: str = Form(...),
    document_id: str = Form(...),
    languages: Optional[str] = Form(None),  # comma-separated, optional
):
    """Upload a document image from device storage. Runs the full pipeline."""
    return await _ingest("upload", file, session_id, service_id, document_id, languages)


@router.post("/scanner/capture", response_model=ProcessResponse)
async def scanner_capture(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    service_id: str = Form(...),
    document_id: str = Form(...),
    languages: Optional[str] = Form(None),
):
    """Submit a camera capture. Runs the full pipeline."""
    return await _ingest("camera", file, session_id, service_id, document_id, languages)


async def _ingest(source, file, session_id, service_id, document_id, languages):
    # Validate session / service / document relationships server-side
    _validate_session(session_id)
    try:
        validate_application_document(session_id, service_id, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")

    ext = _ext_for(file.content_type or "", file.filename or "")

    record = scan_store.create(
        session_id=session_id,
        service_id=service_id,
        document_id=document_id,
        source=source,
        original_bytes=data,
        original_ext=ext,
    )
    try:
        lm = [l.strip() for l in (languages or "").split(",") if l.strip()]
        if not lm:
            lm = ["eng", "hin", "tel"]
        pipe = _run_pipeline(record, lm)
    except HTTPException:
        scan_store.delete(record["scan_id"])
        raise
    except Exception as exc:
        scan_store.delete(record["scan_id"])
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}")

    return ProcessResponse(
        scan_id=record["scan_id"],
        status=record["status"],
        quality=pipe["quality"],
        result=pipe["result"],
    )


@router.post("/scanner/process/{scan_id}", response_model=ProcessResponse)
async def scanner_process(scan_id: str, languages: Optional[str] = None):
    """Re-run the processing pipeline for an existing scan."""
    record = _fetch_scan(scan_id)
    lm = [l.strip() for l in (languages or "").split(",") if l.strip()] or ["eng", "hin", "tel"]
    pipe = _run_pipeline(record, lm)
    return ProcessResponse(
        scan_id=record["scan_id"],
        status=record["status"],
        quality=pipe["quality"],
        result=pipe["result"],
    )


@router.get("/scanner/result/{scan_id}")
async def scanner_result(scan_id: str):
    record = _fetch_scan(scan_id)
    return _public_view(record)


@router.post("/scanner/confirm/{scan_id}")
async def scanner_confirm(scan_id: str, req: ConfirmRequest):
    """
    Customer confirms (or corrects) extracted information.

    Optional corrections are recorded as customer-set values and marked with
    source 'customer' so downstream phases can distinguish OCR vs edits.
    """
    record = _fetch_scan(scan_id)
    if record["status"] != "confirmation_pending" and record["status"] != "readable":
        raise HTTPException(
            status_code=409,
            detail=f"Scan is not awaiting confirmation (status: {record['status']}).",
        )

    if req.corrections:
        corrections = {}
        result = record.get("result") or {}
        for field, value in req.corrections.items():
            if field in result.get("fields", {}) and isinstance(value, str):
                rec = dict(result["fields"][field])
                rec["value"] = value
                rec["confidence"] = None
                rec["source_line"] = None
                rec["source"] = "customer"
                result["fields"][field] = rec
                corrections[field] = value
        record["result"] = result

    record["confirmed_by_customer"] = True
    try:
        scan_store.transition(scan_id, "confirmed")
    except TransitionError:
        scan_store.force_status(scan_id, "confirmed")
    sync_checklist_status(record["session_id"], record)
    scan_store._db_upsert(record)
    return _public_view(record)


@router.post("/scanner/rescan/{scan_id}")
async def scanner_rescan(scan_id: str):
    """Mark a scan as needing rescan (checklist item needs_rescan)."""
    record = _fetch_scan(scan_id)
    try:
        scan_store.transition(scan_id, "needs_rescan")
    except TransitionError:
        scan_store.force_status(scan_id, "needs_rescan")
    record["confirmed_by_customer"] = False
    sync_checklist_status(record["session_id"], record)
    scan_store._db_upsert(record)
    return _public_view(record)


@router.get("/scanner/status/{session_id}")
async def scanner_status(session_id: str):
    """Scan summaries + checklist state for a session (application)."""
    _validate_session(session_id)
    scans = scan_store.for_session(session_id)
    summaries = [_public_view(r) for r in scans]

    # Group per service + checklist progress
    services: Dict[str, Dict[str, Any]] = {}
    for s in summaries:
        services.setdefault(s["service_id"], []).append(s)

    service_state: Dict[str, Any] = {}
    for svc_id in services:
        svc = get_service(svc_id)
        checklist = get_application_checklist(
            svc_id,
            svc.name if svc else svc_id,
            svc.formNumber if svc else "",
            application_id=session_id,  # application id == session id
        )
        status_by_doc: Dict[str, Any] = {}
        for s in services[svc_id]:
            prev = status_by_doc.get(s["document_id"])
            status_by_doc[s["document_id"]] = {
                "scan_id": s["scan_id"],
                "status": s["status"],
                "quality_status": (s.get("quality") or {}).get("status"),
                "match": (s.get("result") or {}).get("classification", {}).get("match"),
                "latest": prev is None,
            }
        service_state[svc_id] = {
            "scans": services[svc_id],
            "checklist": checklist.model_dump(),
            "scan_status_by_document": status_by_doc,
        }

    return {"session_id": session_id, "services": service_state}


@router.get("/scanner/image/{scan_id}")
async def scanner_image(scan_id: str, variant: str = "processed"):
    """Return preview image bytes (processed by default, original on request)."""
    record = _fetch_scan(scan_id)
    path = record.get("processed_path") if variant == "processed" else record.get("original_path")
    if not path or not __import__("pathlib").Path(path).exists():
        raise HTTPException(status_code=404, detail="Image not available")
    with open(path, "rb") as fh:
        data = fh.read()
    return Response(content=data, media_type="image/jpeg")


@router.delete("/scanner/{scan_id}")
async def scanner_delete(scan_id: str):
    if not scan_store.delete(scan_id):
        raise HTTPException(status_code=404, detail="Scan not found")
    return {"status": "deleted", "scan_id": scan_id}


@router.post("/scanner/cleanup/{session_id}")
async def scanner_cleanup(session_id: str):
    removed = scan_store.purge_session(session_id)
    return {"status": "cleaned", "session_id": session_id, "scans_removed": removed}


@router.post("/scanner/purge-expired")
async def scanner_purge_expired():
    removed = scan_store.purge_expired()
    return {"status": "purged", "scans_removed": removed}


@router.get("/scanner/engine/status")
async def scanner_engine_status():
    return {
        "ocr_available": AVAILABLE,
        "engine": "tesseract" if AVAILABLE else None,
        "languages_available": AVAILABLE_LANGUAGES,
        "languages_requested": ["eng", "hin", "tel"],
        "supported": {
            "eng": "eng" in AVAILABLE_LANGUAGES,
            "hin": "hin" in AVAILABLE_LANGUAGES,
            "tel": "tel" in AVAILABLE_LANGUAGES,
        },
    }
