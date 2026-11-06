"""
Conversation Management (Phase 7).

Per-session conversation memory for the AI assistant:
- message history (bounded), so the customer's chat carries context
- last service referenced, for follow-up questions ("which documents?")
- session context (selected language is owned by session_service; this store
  only mirrors conversational state)

Everything is in-memory and wiped with the session: DELETE /api/session/{id}
and DELETE /api/ai/conversation/{session_id} purge the same store. No
message contents are written to disk or logs, so nothing sensitive is
retained beyond the active kiosk session.
"""

import threading
import time
from typing import Any, Dict, List, Optional


class ConversationStore:
    def __init__(self, max_messages: int = 40):
        self._lock = threading.Lock()
        self._store: Dict[str, Dict[str, Any]] = {}
        self._max_messages = max_messages

    # ------------------------------------------------------------------
    def ensure(self, session_id: str) -> Dict[str, Any]:
        with self._lock:
            conv = self._store.get(session_id)
            if conv is None:
                conv = {
                    "messages": [],
                    "last_service_id": None,
                    "last_intent": None,
                    "created_at": time.time(),
                    "updated_at": time.time(),
                }
                self._store[session_id] = conv
            return conv

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        max_messages: Optional[int] = None,
    ) -> None:
        cap = max_messages or self._max_messages
        with self._lock:
            conv = self._store.setdefault(
                session_id,
                {
                    "messages": [],
                    "last_service_id": None,
                    "last_intent": None,
                    "created_at": time.time(),
                    "updated_at": time.time(),
                },
            )
            conv["messages"].append({"role": role, "content": content})
            if len(conv["messages"]) > cap:
                conv["messages"] = conv["messages"][-cap:]
            conv["updated_at"] = time.time()

    def set_last_service(self, session_id: str, service_id: Optional[str]) -> None:
        with self._lock:
            conv = self._store.setdefault(
                session_id,
                {
                    "messages": [],
                    "last_service_id": None,
                    "last_intent": None,
                    "created_at": time.time(),
                    "updated_at": time.time(),
                },
            )
            conv["last_service_id"] = service_id
            conv["updated_at"] = time.time()

    def set_last_intent(self, session_id: str, intent: Optional[str]) -> None:
        with self._lock:
            conv = self._store.setdefault(
                session_id,
                {
                    "messages": [],
                    "last_service_id": None,
                    "last_intent": None,
                    "created_at": time.time(),
                    "updated_at": time.time(),
                },
            )
            conv["last_intent"] = intent
            conv["updated_at"] = time.time()

    # ------------------------------------------------------------------
    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        with self._lock:
            conv = self._store.get(session_id)
            if not conv:
                return []
            return [
                {"role": m["role"], "content": m["content"]}
                for m in conv["messages"]
            ]

    def get_last_service(self, session_id: str) -> Optional[str]:
        with self._lock:
            conv = self._store.get(session_id)
            return conv.get("last_service_id") if conv else None

    def context_summary(self, session_id: str) -> Dict[str, Any]:
        """Compact context for prompts: messages are length-trimmed and were
        already sanitised before being stored — no OCR data or identifiers."""
        with self._lock:
            conv = self._store.get(session_id)
            if not conv:
                return {"messages": [], "last_service_id": None}
            return {
                "messages": [
                    {"role": m["role"], "content": m["content"][:300]}
                    for m in conv["messages"][-12:]
                ],
                "last_service_id": conv.get("last_service_id"),
            }

    # ------------------------------------------------------------------
    def clear(self, session_id: str) -> bool:
        """Wipe one conversation; returns True when it existed."""
        with self._lock:
            return self._store.pop(session_id, None) is not None

    def purge_session(self, session_id: str) -> None:
        self.clear(session_id)

    def active_count(self) -> int:
        with self._lock:
            return len(self._store)


conversation_store = ConversationStore()
