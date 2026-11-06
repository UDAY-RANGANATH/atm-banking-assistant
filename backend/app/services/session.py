from typing import Optional, Dict, Any
from app.db.database import SessionLocal
from app.models import Session as SessionModel
import uuid


class SessionService:
    """Service for managing user sessions."""

    def __init__(self):
        self._memory: Dict[str, Dict[str, Any]] = {}

    def create_session(self, language: str = "en") -> str:
        session_id = str(uuid.uuid4())
        db = SessionLocal()
        try:
            db_session = SessionModel(
                session_id=session_id,
                language=language,
                current_step="language_selection",
            )
            db.add(db_session)
            db.commit()
            db.refresh(db_session)
        finally:
            db.close()

        self._memory[session_id] = {
            "language": language,
            "current_step": "language_selection",
            "selected_service": None,
            "documents_scanned": {},
            "confirmed_info": {},
        }
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        # Check memory first
        if session_id in self._memory:
            return self._memory[session_id]

        # Fall back to DB
        db = SessionLocal()
        try:
            db_session = (
                db.query(SessionModel)
                .filter(SessionModel.session_id == session_id)
                .first()
            )
            if db_session:
                return {
                    "language": db_session.language,
                    "current_step": db_session.current_step,
                    "selected_service": None,
                    "documents_scanned": {},
                    "confirmed_info": {},
                }
        finally:
            db.close()
        return None

    def update_session(
        self, session_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            db_session = (
                db.query(SessionModel)
                .filter(SessionModel.session_id == session_id)
                .first()
            )
            if db_session:
                for key, value in updates.items():
                    if hasattr(db_session, key):
                        setattr(db_session, key, value)
                db.commit()
                db.refresh(db_session)

        finally:
            db.close()

        if session_id in self._memory:
            self._memory[session_id].update(updates)
            return self._memory[session_id]
        return None

    def set_language(self, session_id: str, language: str) -> bool:
        result = self.update_session(
            session_id, {"language": language, "current_step": "welcome"}
        )
        return result is not None

    def cleanup_session(self, session_id: str) -> bool:
        self._memory.pop(session_id, None)
        db = SessionLocal()
        try:
            db_session = (
                db.query(SessionModel)
                .filter(SessionModel.session_id == session_id)
                .first()
            )
            if db_session:
                db.delete(db_session)
                db.commit()
        finally:
            db.close()
        return True


session_service = SessionService()
