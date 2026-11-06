"""
Scanner Service (Phase 4)

Manages document scans: temporary file storage, scan records,
status transitions, checklist association and cleanup.

- Temporary images live in backend/temp_scans/{session_id}/ and are deleted
  on scan completion, session cleanup, or via the periodic purge helper.
- Raw OCR text is never stored; only the masked structured result is.
- Customer confirmation / OCR readability ≠ official KYC verification.
"""

import json
import shutil
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

from app.models import DocumentScan
from app.db.database import SessionLocal, init_db
from app.services.banking_services import get_service
from app.services.document_engine import (
    DOCUMENT_CATALOGUE,
    SERVICE_DOCUMENT_MAPPINGS,
    get_service_mappings,
    DocumentRequirementStatus,
    update_checklist_status,
)

TEMP_ROOT = Path(__file__).resolve().parents[1] / "temp_scans"
TEMP_RETENTION_HOURS = 6

# ---------------------------------------------------------------------------
# Scan status model
# ---------------------------------------------------------------------------

# Checklist-visible statuses (valid transitions)
VALID_TRANSITIONS: Dict[str, set] = {
    "uploaded": {"ocr_processing", "needs_rescan"},
    "ocr_processing": {"readable", "needs_rescan", "confirmation_pending"},
    "confirmation_pending": {"confirmed", "needs_rescan", "ocr_processing"},
    "readable": {"confirmed", "needs_rescan"},
    "confirmed": {"needs_rescan", "ocr_processing"},
    "needs_rescan": {"uploaded", "ocr_processing", "confirmation_pending", "readable"},
}


class TransitionError(Exception):
    pass


# ---------------------------------------------------------------------------
# Scan records
# ---------------------------------------------------------------------------

class ScanStore:
    """
    In-memory registry of live scan sessions + DB persistence of scan
    metadata (no raw OCR text, no image paths beyond temp file names).
    """

    def __init__(self):
        self._scans: Dict[str, Dict[str, Any]] = {}

    # -- creation ----------------------------------------------------------

    def create(
        self,
        session_id: str,
        service_id: str,
        document_id: str,
        source: str,
        original_bytes: bytes,
        original_ext: str,
    ) -> Dict[str, Any]:
        scan_id = f"scan_{uuid.uuid4().hex[:20]}"
        folder = TEMP_ROOT / session_id
        folder.mkdir(parents=True, exist_ok=True)
        original_path = folder / f"orig_{scan_id}{original_ext}"
        # Secure naming: server-generated uuid names, no user input in path
        with original_path.open("wb") as fh:
            fh.write(original_bytes)

        record: Dict[str, Any] = {
            "scan_id": scan_id,
            "session_id": session_id,
            "service_id": service_id,
            "document_id": document_id,
            "source": source,          # "camera" | "upload"
            "status": "uploaded",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "original_path": str(original_path),
            "processed_path": None,
            "quality": None,
            "result": None,
            "ocr_available": "true",
            "confirmed_by_customer": False,
            "history": [{"status": "uploaded", "at": record_time()}],
        }
        self._scans[scan_id] = record
        self._db_upsert(record)
        return record

    # -- lookups -----------------------------------------------------------

    def get(self, scan_id: str) -> Optional[Dict[str, Any]]:
        return self._scans.get(scan_id)

    def for_session(self, session_id: str) -> List[Dict[str, Any]]:
        return [r for r in self._scans.values() if r["session_id"] == session_id]

    # -- transitions -------------------------------------------------------

    def transition(self, scan_id: str, new_status: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        record = self._scans.get(scan_id)
        if not record:
            raise TransitionError("Scan not found")
        current = record["status"]
        if new_status not in VALID_TRANSITIONS.get(current, set()):
            raise TransitionError(
                f"Invalid status transition: {current} -> {new_status}"
            )
        record["status"] = new_status
        record["history"].append({"status": new_status, "at": record_time()})
        if extra:
            record.update(extra)
        self._db_upsert(record)
        return record

    def force_status(self, scan_id: str, new_status: str) -> Dict[str, Any]:
        record = self._scans.get(scan_id)
        if not record:
            raise TransitionError("Scan not found")
        record["status"] = new_status
        record["history"].append({"status": new_status, "at": record_time()})
        self._db_upsert(record)
        return record

    # -- persistence (metadata only) ---------------------------------------

    def _db_upsert(self, record: Dict[str, Any]) -> None:
        db = SessionLocal()
        try:
            row = (
                db.query(DocumentScan)
                .filter(DocumentScan.scan_id == record["scan_id"])
                .first()
            )
            if not row:
                # Persist only masked extraction + classification, never raw OCR
                masked_result = self._masked_result_for_db(record)
                row = DocumentScan(
                    scan_id=record["scan_id"],
                    session_id=record["session_id"],
                    service_id=record["service_id"],
                    document_id=record["document_id"],
                    status=record["status"],
                )
                db.add(row)
            row.status = record["status"]
            if record.get("quality"):
                row.quality_status = record["quality"].get("status")
            if record.get("result"):
                row.classification = record["result"].get("classification", {}).get("detected_type")
                row.classification_match = record["result"].get("classification", {}).get("match")
                row.extraction = json.dumps(
                    {
                        "fields": record["result"].get("fields", {}),
                        "extraction_status": record["result"].get("extraction_status"),
                    }
                )
                row.ocr_available = "true" if record["result"].get("ocr_available") else "false"
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    @staticmethod
    def _masked_result_for_db(record: Dict[str, Any]) -> Dict[str, Any]:
        """Only masked fields are persisted; raw OCR text is dropped."""
        result = record.get("result") or {}
        return {
            "fields": result.get("fields", {}),
            "extraction_status": result.get("extraction_status"),
        }

    # -- cleanup -----------------------------------------------------------

    def delete(self, scan_id: str) -> bool:
        record = self._scans.pop(scan_id, None)
        if not record:
            return False
        _remove_files(record)
        return True

    def purge_session(self, session_id: str) -> int:
        """Remove all scans + temp files for a session."""
        scans = [r for r in list(self._scans.values()) if r["session_id"] == session_id]
        for r in scans:
            self._scans.pop(r["scan_id"], None)
            _remove_files(r)
        folder = TEMP_ROOT / session_id
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
        return len(scans)

    def purge_expired(self, max_age_hours: int = TEMP_RETENTION_HOURS) -> int:
        """Delete scans whose temp files are older than the retention window."""
        cutoff = time.time() - max_age_hours * 3600
        removed = 0
        for r in list(self._scans.values()):
            p = Path(r["original_path"])
            if p.exists() and p.stat().st_mtime < cutoff:
                self._scans.pop(r["scan_id"], None)
                _remove_files(r)
                removed += 1
        # Also drop orphaned temp folders from crashed runs
        if TEMP_ROOT.exists():
            for folder in TEMP_ROOT.iterdir():
                if folder.is_dir() and folder.stat().st_mtime < cutoff and not any(
                    r for r in self._scans.values() if r["session_id"] == folder.name
                ):
                    shutil.rmtree(folder, ignore_errors=True)
        return removed

    def cleanup_stale_folders(self) -> int:
        """Remove empty temp folders. Called on demand."""
        count = 0
        if TEMP_ROOT.exists():
            for folder in TEMP_ROOT.iterdir():
                if folder.is_dir() and not any(folder.iterdir()):
                    shutil.rmtree(folder, ignore_errors=True)
                    count += 1
        return count


def record_time() -> str:
    return datetime.now(timezone.utc).isoformat()


def _remove_files(record: Dict[str, Any]) -> None:
    for key in ("original_path", "processed_path"):
        p = record.get(key)
        if p:
            try:
                Path(p).unlink(missing_ok=True)
            except Exception:
                pass


scan_store = ScanStore()


# ---------------------------------------------------------------------------
# Application / checklist association validation
# ---------------------------------------------------------------------------

def validate_application_document(
    session_id: str,
    service_id: Optional[str],
    document_id: str,
) -> Dict[str, Any]:
    """
    Never trust client IDs blindly: document_id must exist in the catalogue,
    and the service must actually map to that document.

    Returns {"document_id", "service_id", "document", "mapping"}.
    Raises ValueError on invalid associations.
    """
    doc = DOCUMENT_CATALOGUE.get(document_id)
    if not doc:
        raise ValueError(f"Unknown document_id: {document_id}")

    mappings = [
        m for m in SERVICE_DOCUMENT_MAPPINGS if m.document_id == document_id
    ]

    if service_id:
        service = get_service(service_id)
        if not service:
            raise ValueError(f"Unknown service_id: {service_id}")
        svc_mapping = next(
            (m for m in mappings if m.service_id == service_id), None
        )
        if not svc_mapping:
            raise ValueError(
                f"Document {document_id} is not part of service {service_id}"
            )
        mapping = svc_mapping
    elif mappings:
        mapping = mappings[0]
        service_id = mapping.service_id
    else:
        raise ValueError(
            f"Document {document_id} is not mapped to any service for standalone uploads"
        )

    return {
        "document_id": document_id,
        "service_id": service_id,
        "document_name": doc.name.get("en", document_id),
        "mandatory": mapping.mandatory,
        "conditional": mapping.conditional,
    }


def sync_checklist_status(
    session_id: str,
    scan: Dict[str, Any],
) -> None:
    """
    Update Phase 3 checklist status using only the valid status transitions.

    Mapping scan status -> checklist status:
      uploaded/ocr_processing -> UPLOADED
      readable / confirmed    -> READABLE   (still only readability, not KYC)
      needs_rescan            -> NEEDS_RESCAN

    Mandatory documents are never set to NOT_APPLICABLE by this workflow.
    """
    scan_status = scan["status"]
    if scan_status in {"uploaded", "ocr_processing"}:
        checklist_status = DocumentRequirementStatus.UPLOADED
    elif scan_status in {"readable", "confirmed", "confirmation_pending"}:
        checklist_status = DocumentRequirementStatus.READABLE
    elif scan_status == "needs_rescan":
        checklist_status = DocumentRequirementStatus.NEEDS_RESCAN
    else:
        return

    # Guard: mandatory document must not be silently marked N/A
    if checklist_status == DocumentRequirementStatus.NOT_APPLICABLE:
        return

    update_checklist_status(
        application_id=session_id,
        document_id=scan["document_id"],
        status=checklist_status,
    )
