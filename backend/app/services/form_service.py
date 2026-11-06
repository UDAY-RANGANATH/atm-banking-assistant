"""
Intelligent Application Form Autofill service (Phase 5).

Connects Phase 4 OCR extraction results (ScanStore) with the reusable form
configuration registry (form_engine.py) for all 59 banking services.

Design guarantees:
  - Nothing is ever invented: form fields are populated only from values
    actually extracted by OCR from a customer's scanned document.
  - Uncertain values are never silently used: values below the confidence
    threshold are flagged LOW_CONFIDENCE and require customer review.
  - Conflicts between documents are never auto-resolved: CONFLICT status
    with all candidate values is shown; the customer decides.
  - Customer decisions are never overwritten: a field the customer edited
    or explicitly confirmed keeps its status across autofill runs.
  - Extracted personal data is preserved exactly as OCR printed it
    (identifiers are already masked by the extraction layer).
  - Session ownership is enforced on every operation.
  - Nothing is ever silently submitted; confirmation is explicit.
"""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session as DBSession

from app.db.database import SessionLocal
from app.models import Application as ApplicationModel, Session as SessionModel
from app.services.form_engine import (
    FIELD_MAPPINGS,
    FORM_FIELD_TYPES,
    FIELD_STATUSES,
    LOW_CONFIDENCE_THRESHOLD,
    get_service_fields,
    status_from_confidence,
    validate_field_value,
)
from app.services.banking_services import get_service
from app.services.scanner import scan_store
from app.services.session import session_service

# Scan statuses whose extraction results may feed the autofill engine.
AUTOFILL_ELIGIBLE_STATUSES = {"readable", "confirmed"}
_UNSET = object()

_MAX_VALUE_LEN = 500


class FormApplicationError(Exception):
    """Domain error with an HTTP-ready status code."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _normalize_state(raw: Optional[str]) -> Dict[str, Any]:
    """Parse application_data JSON; tolerate legacy/absent payloads."""
    if not raw:
        return {"fields": {}, "autofill_runs": 0}
    try:
        state = json.loads(raw)
    except (ValueError, TypeError):
        return {"fields": {}, "autofill_runs": 0}
    if not isinstance(state, dict):
        return {"fields": {}, "autofill_runs": 0}
    state.setdefault("fields", {})
    state.setdefault("autofill_runs", 0)
    return state


def _persist(application: ApplicationModel, state: Dict[str, Any]) -> None:
    application.application_data = json.dumps(state, ensure_ascii=False)
    application.updated_at = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        row = (
            db.query(ApplicationModel)
            .filter(ApplicationModel.id == application.id)
            .first()
        )
        if row:
            row.application_data = application.application_data
            row.updated_at = application.updated_at
            db.commit()
            db.refresh(row)
            application.application_data = row.application_data
            application.updated_at = row.updated_at
    finally:
        db.close()


def new_reference_number() -> str:
    """Prototype reference number. Not an official acknowledgement."""
    return f"APP-{uuid.uuid4().hex[:8].upper()}"


# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------

def ensure_application(session_id: str, service_id: str) -> ApplicationModel:
    """
    Return the draft Application row for (session, service), creating it on
    first use. Enforces that both the session and the service exist.
    """
    sess = session_service.get_session(session_id)
    if not sess:
        raise FormApplicationError(404, "Session not found")
    svc = get_service(service_id)
    if not svc:
        raise FormApplicationError(404, "Service not found")

    db: DBSession = SessionLocal()
    try:
        row = (
            db.query(ApplicationModel)
            .filter(
                ApplicationModel.session_key == session_id,
                ApplicationModel.service_id == service_id,
            )
            .order_by(ApplicationModel.id.desc())
            .first()
        )
        if not row:
            internal = (
                db.query(SessionModel)
                .filter(SessionModel.session_id == session_id)
                .first()
            )
            if not internal:
                raise FormApplicationError(404, "Session not found")
            row = ApplicationModel(
                session_id=internal.id,
                session_key=session_id,
                service_id=service_id,
                service_name=svc.name,
                form_number=svc.formNumber,
                reference_number=new_reference_number(),
                status="draft",
                application_data=json.dumps({"fields": {}, "autofill_runs": 0}),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
        return row
    finally:
        db.close()


def get_application_for_session(
    application_ref: str, session_id: str
) -> ApplicationModel:
    """
    Load an application by reference number (or numeric id) and enforce that
    it belongs to the given session. Raises 404 / 403.
    """
    sess = session_service.get_session(session_id)
    if not sess:
        raise FormApplicationError(404, "Session not found")

    db: DBSession = SessionLocal()
    try:
        query = db.query(ApplicationModel).filter(
            ApplicationModel.reference_number == application_ref
        )
        row = query.first()
        if not row and application_ref.isdigit():
            row = (
                db.query(ApplicationModel)
                .filter(ApplicationModel.id == int(application_ref))
                .first()
            )
        if not row:
            raise FormApplicationError(404, "Application not found")
        if row.session_key != session_id:
            # Someone else's application - never leak its contents.
            raise FormApplicationError(403, "Application does not belong to this session")
        return row
    finally:
        db.close()


def purge_session_data(session_id: str) -> int:
    """Remove applications that belong to an expired/cleaned-up session."""
    db: DBSession = SessionLocal()
    try:
        rows = (
            db.query(ApplicationModel)
            .filter(ApplicationModel.session_key == session_id)
            .all()
        )
        count = len(rows)
        for row in rows:
            db.delete(row)
        db.commit()
        return count
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Autofill engine
# ---------------------------------------------------------------------------

def _harvest_scan_values(
    session_id: str, service_id: str
) -> List[Dict[str, Any]]:
    """
    Collect extraction candidates from all eligible scans of this session
    for this service: one entry per (mapping x scan x meaningful value).
    """
    candidates: List[Dict[str, Any]] = []
    for record in scan_store.for_session(session_id):
        if record.get("service_id") != service_id:
            continue  # each service only uses its own documents
        if record.get("status") not in AUTOFILL_ELIGIBLE_STATUSES:
            continue  # unreadable / awaiting-rescan scans are never used
        result = record.get("result") or {}
        doc_type = result.get("doc_type")
        fields = result.get("fields") or {}
        if not doc_type or not isinstance(fields, dict):
            continue
        for mapping in FIELD_MAPPINGS:
            if mapping["doc_type"] != doc_type:
                continue
            doc_field = mapping["doc_field"]
            entry = fields.get(doc_field)
            if not isinstance(entry, dict):
                continue
            value = entry.get("value")
            if value is None:
                continue
            value = str(value).strip()
            if not value:
                continue
            confidence = entry.get("confidence")
            candidates.append(
                {
                    "form_field": mapping["form_field"],
                    "value": value,
                    "confidence": confidence,
                    "scan_id": record["scan_id"],
                    "document_id": record.get("document_id"),
                    "doc_type": doc_type,
                    "doc_field": doc_field,
                    "doc_field_label": entry.get("label"),
                    "note": mapping.get("note"),
                }
            )
    return candidates


def _norm(value: str) -> str:
    """Normalized form for conflict comparison only (values are preserved
    exactly as extracted in the displayed/stored data)."""
    return re.sub(r"\s+", " ", value.strip().casefold())


def _merge_candidates(
    group: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Merge candidate values for one form field. Returns either an AUTO_FILLED/
    LOW_CONFIDENCE verdict (single distinct value) or a CONFLICT verdict with
    every distinct candidate preserved - never an automatic pick.
    """
    if not group:
        return {}
    distinct: Dict[str, Dict[str, Any]] = {}
    for cand in group:
        key = _norm(cand["value"])
        existing = distinct.get(key)
        if existing is None:
            distinct[key] = {
                "candidates": [cand],
                "best": cand,
            }
        else:
            distinct[key]["candidates"].append(cand)
            if (
                _conf(cand) is not None
                and (_conf(existing["best"]) is None or _conf(cand) > _conf(existing["best"]))
            ):
                existing["best"] = cand

    # one distinct value -> confident or low-confidence audit trail
    if len(distinct) == 1:
        entry = next(iter(distinct.values()))
        best = dict(entry["best"])
        best.pop("note", None)
        best["corroborated_by"] = [
            c["scan_id"] for c in entry["candidates"] if c["scan_id"] != best["scan_id"]
        ]
        return {
            "value": best["value"],
            "confidence": best.get("confidence"),
            "status": status_from_confidence(best.get("confidence")),
            "source": best,
        }

    # more than one distinct value -> CONFLICT; customer picks
    conflicts = []
    for entry in distinct.values():
        best = entry["best"]
        conflicts.append(
            {
                "value": best["value"],
                "confidence": best.get("confidence"),
                "scan_id": best["scan_id"],
                "document_id": best.get("document_id"),
                "doc_type": best["doc_type"],
                "doc_field_label": best.get("doc_field_label"),
            }
        )
    conflicts.sort(key=lambda c: (_conf(c) or 0.0), reverse=True)
    return {"value": None, "status": "CONFLICT", "conflicts": conflicts}


def _conf(entry: Dict[str, Any]) -> Optional[float]:
    c = entry.get("confidence")
    if isinstance(c, (int, float)):
        return float(c)
    return None


def run_autofill(application: ApplicationModel) -> Dict[str, Any]:
    """
    Populate the application's form fields from eligible scans, preserving
    every customer decision. Returns updated field state.
    """
    state = _normalize_state(application.application_data)
    existing_fields: Dict[str, Any] = state["fields"]
    service_fields = get_service_fields(application.service_id)

    harvested = _harvest_scan_values(application.session_key, application.service_id)
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for cand in harvested:
        if cand["form_field"] in service_fields:
            grouped.setdefault(cand["form_field"], []).append(cand)

    for field_id in service_fields:
        prior = existing_fields.get(field_id)
        # Customer decisions are never overwritten by future autofill runs.
        if prior and prior.get("status") in {"CUSTOMER_EDITED", "CUSTOMER_CONFIRMED"}:
            continue
        if prior and prior.get("customer_cleared"):
            # An explicit Clear Value is also a customer decision - the
            # cleared value must not silently come back on later runs.
            continue
        verdict = _merge_candidates(grouped.get(field_id, []))
        if not verdict:
            if not prior or prior.get("status") in {
                "AUTO_FILLED", "LOW_CONFIDENCE", "CONFLICT",
            }:
                existing_fields[field_id] = {
                    "value": None,
                    "status": "MISSING",
                    "confidence": None,
                    "source": None,
                }
            continue
        record = {
            "value": verdict["value"],
            "status": verdict["status"],
            "confidence": verdict.get("confidence"),
            "source": verdict.get("source"),
        }
        if verdict["status"] == "CONFLICT":
            record["conflicts"] = verdict["conflicts"]
        existing_fields[field_id] = record

    state["fields"] = existing_fields
    state["autofill_runs"] = int(state.get("autofill_runs", 0)) + 1
    state["last_autofill_at"] = datetime.now(timezone.utc).isoformat()
    _persist(application, state)
    return state


# ---------------------------------------------------------------------------
# Field operations
# ---------------------------------------------------------------------------

def _set_record(
    status: str,
    value: Optional[str] = None,
    confidence: Optional[float] = None,
    source: Optional[Dict[str, Any]] = None,
    conflicts: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    rec: Dict[str, Any] = {
        "value": value,
        "status": status,
        "confidence": confidence,
        "source": source,
    }
    if conflicts:
        rec["conflicts"] = conflicts
    return rec


def set_field(
    application: ApplicationModel,
    field_id: str,
    action: str,
    value: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Customer action on one field:
      edit   - customer typed/corrected a value          -> CUSTOMER_EDITED
      clear  - customer removed the value                -> MISSING
      confirm- customer approved the current value        -> CUSTOMER_CONFIRMED
      accept - alias of confirm (Accept Value action)
    """
    if field_id not in get_service_fields(application.service_id):
        raise FormApplicationError(404, f"Field {field_id} is not part of this application form")
    if action not in {"edit", "clear", "confirm", "accept"}:
        raise FormApplicationError(400, "Unknown field action")

    state = _normalize_state(application.application_data)
    fields: Dict[str, Any] = state["fields"]

    if action == "clear":
        fields[field_id] = _set_record("MISSING")
        fields[field_id]["customer_cleared"] = True
    elif action in {"confirm", "accept"}:
        prior = fields.get(field_id) or {}
        if prior.get("status") == "CONFLICT" and not prior.get("value"):
            raise FormApplicationError(
                409,
                "Resolve the conflicting value first (choose one candidate or edit the field)",
            )
        current = prior.get("value")
        if not current:
            raise FormApplicationError(
                400, "Confirm requires a value on the field"
            )
        fields[field_id] = _set_record(
            "CUSTOMER_CONFIRMED",
            value=current,
            confidence=prior.get("confidence"),
            source=prior.get("source"),
        )
    else:  # edit
        if value is None:
            raise FormApplicationError(400, "Field value is required for edit")
        value = str(value).strip()
        if not value:
            raise FormApplicationError(400, "Field value must not be blank")
        if len(value) > _MAX_VALUE_LEN:
            raise FormApplicationError(422, "Value is too long")
        # Manual entry of sensitive identifiers is never required - the
        # prototype never asks the customer to type full PAN/Aadhaar numbers.
        definition = FORM_FIELD_TYPES.get(field_id, {})
        if definition.get("sensitive") and prior_needs_mask(field_id, value):
            raise FormApplicationError(
                422,
                "Sensitive identifier: use the OCR-extracted (masked) value; "
                "the prototype never asks you to type full identifiers",
            )
        ok, error_key = validate_field_value(field_id, value)
        if not ok:
            raise FormValidationError(error_key)
        fields[field_id] = _set_record(
            "CUSTOMER_EDITED",
            value=value,
            confidence=None,
            source=None,
        )

    state["fields"] = fields
    _persist(application, state)
    return fields[field_id]


def prior_needs_mask(field_id: str, value: str) -> bool:
    """Manual-entry guard: reject unmasked PAN-style identifiers typed in."""
    if "XX" in value or "*" in value:
        return False
    return len(re.sub(r"[^A-Za-z0-9]", "", value)) >= 8


class FormValidationError(Exception):
    """Raised when a value fails prototype validation; carries i18n key."""

    def __init__(self, error_key: str):
        super().__init__(error_key)
        self.error_key = error_key


def confirm_fields(
    application: ApplicationModel, field_ids: List[str]
) -> Dict[str, Any]:
    """Explicitly approve one or more populated fields (Review + Accept)."""
    if not isinstance(field_ids, list) or not field_ids:
        raise FormApplicationError(400, "field_ids must be a non-empty list")
    valid = set(get_service_fields(application.service_id))
    unknown = [f for f in field_ids if f not in valid]
    if unknown:
        raise FormApplicationError(404, f"Unknown fields: {', '.join(unknown)}")

    state = _normalize_state(application.application_data)
    fields: Dict[str, Any] = state["fields"]
    confirmed: List[str] = []
    skipped: Dict[str, str] = {}
    conflicts: Dict[str, List[Dict[str, Any]]] = {}
    for fid in field_ids:
        prior = fields.get(fid) or {}
        if prior.get("status") == "CONFLICT" and not prior.get("value"):
            skipped[fid] = "conflict_unresolved"
            conflicts[fid] = prior.get("conflicts", [])
            continue
        if not prior.get("value"):
            skipped[fid] = "empty_value"
            continue
        if prior.get("status") == "CUSTOMER_CONFIRMED":
            skipped[fid] = "already_confirmed"
            continue
        fields[fid] = _set_record(
            "CUSTOMER_CONFIRMED",
            value=prior.get("value"),
            confidence=prior.get("confidence"),
            source=prior.get("source"),
        )
        confirmed.append(fid)
    state["fields"] = fields
    _persist(application, state)
    return {
        "confirmed": confirmed,
        "skipped": skipped,
        "conflicts": conflicts,
    }


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def build_form_view(
    application: ApplicationModel,
    state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Full form view used by GET /form and POST /autofill responses."""
    state = state or _normalize_state(application.application_data)
    fields_state: Dict[str, Any] = state["fields"]
    svc = get_service(application.service_id)
    field_views: List[Dict[str, Any]] = []
    for field_id in get_service_fields(application.service_id):
        definition = FORM_FIELD_TYPES.get(field_id, {})
        rec = fields_state.get(field_id, {})
        field_views.append(
            {
                "field_id": field_id,
                "label": definition.get("label", {"en": field_id, "te": "", "hi": ""}),
                "type": definition.get("type", "text"),
                "options": definition.get("options"),
                "pattern": definition.get("pattern"),
                "sensitive": bool(definition.get("sensitive", False)),
                "value": rec.get("value"),
                "status": rec.get("status", "MISSING"),
                "confidence": rec.get("confidence"),
                "source": rec.get("source"),
                "conflicts": rec.get("conflicts"),
            }
        )
    return {
        "application_id": application.reference_number,
        "service_id": application.service_id,
        "service_name": application.service_name,
        "form_number": application.form_number,
        "status": application.status,
        "language": None,
        "fields": field_views,
        "autofill_runs": state.get("autofill_runs", 0),
        "last_autofill_at": state.get("last_autofill_at"),
        "prototype_notice": (
            "Educational prototype. This form is not an official bank "
            "application; OCR autofill is not identity verification. Nothing "
            "is submitted without your explicit confirmation."
        ),
    }


def completion_status(application: ApplicationModel) -> Dict[str, Any]:
    state = _normalize_state(application.application_data)
    fields_state: Dict[str, Any] = state["fields"]
    counts = {s: 0 for s in FIELD_STATUSES}
    for fid in get_service_fields(application.service_id):
        counts[fields_state.get(fid, {}).get("status", "MISSING")] += 1
    total = len(get_service_fields(application.service_id))
    blocking = counts["LOW_CONFIDENCE"] + counts["CONFLICT"]
    filled = total - counts["MISSING"]
    confirmed_count = counts["CUSTOMER_CONFIRMED"] + counts["CUSTOMER_EDITED"]
    # Phase 6 gate: PDFs are generated from customer-confirmed data only.
    # A populated field that is still AUTO_FILLED has no recorded customer
    # confirmation, so generation is blocked until every populated field was
    # individually reviewed (confirmed or edited). MISSING fields may remain
    # (they are printed as "not provided"). At least one explicit customer
    # confirmation must be recorded.
    pdf_ready = (
        blocking == 0
        and counts["AUTO_FILLED"] == 0
        and confirmed_count >= 1
    )
    warnings: List[Dict[str, Any]] = []
    low_conf = []
    conflict_fields = []
    missing = []
    for fid in get_service_fields(application.service_id):
        rec = fields_state.get(fid, {})
        status = rec.get("status", "MISSING")
        if status == "LOW_CONFIDENCE":
            low_conf.append(fid)
        elif status == "CONFLICT":
            conflict_fields.append(fid)
        elif status == "MISSING":
            missing.append(fid)
    if conflict_fields:
        warnings.append(
            {
                "kind": "conflict",
                "fields": conflict_fields,
            }
        )
    if low_conf:
        warnings.append({"kind": "low_confidence", "fields": low_conf})
    if missing:
        warnings.append({"kind": "missing", "fields": missing})
    return {
        "application_id": application.reference_number,
        "service_id": application.service_id,
        "total_fields": total,
        "filled_fields": filled,
        "counts": counts,
        "warnings": warnings,
        "ready_to_continue": blocking == 0,
        "pdf_ready": pdf_ready,
        "pdf_blocked_reason": None if pdf_ready else _pdf_block_reason(counts),
        "note": (
            "Continue requires review of low-confidence and conflicting "
            "fields. Missing fields warn but can be completed manually."
        ),
    }


def _pdf_block_reason(counts: Dict[str, int]) -> str:
    """Stable (i18n-key style) reason why PDF generation is blocked."""
    if counts["LOW_CONFIDENCE"] or counts["CONFLICT"]:
        return "review_required"
    if counts["AUTO_FILLED"]:
        return "unconfirmed_fields"
    if counts["CUSTOMER_CONFIRMED"] + counts["CUSTOMER_EDITED"] < 1:
        return "no_confirmation"
    return "unknown"


def field_mappings_view(service_id: str) -> List[Dict[str, Any]]:
    """Introspection endpoint payload for one service's mappings."""
    get_service(service_id)  # 404 for unknown services
    fields = set(get_service_fields(service_id))
    return [m for m in FIELD_MAPPINGS if m["form_field"] in fields]
