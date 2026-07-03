"""In-memory TTL session store.

Holds completed `Analysis` results keyed by ``session_id`` so the API can re-fetch them
without re-running the pipeline. Entries expire after ``ttl_minutes``; expired entries are
purged lazily on access and can be purged eagerly via :meth:`purge`.

Privacy: only structured `Analysis` objects are stored — never raw uploaded bytes. This is a
stepping stone; Phase 7 replaces it with persistent SQLite storage.

The clock is injectable (``time_fn``) so expiry is testable without sleeping.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

from app.models.schemas import Analysis


@dataclass
class _Entry:
    analysis: Analysis
    expires_at: float


class SessionStore:
    def __init__(self, ttl_minutes: int = 60, time_fn: Callable[[], float] = time.monotonic):
        self._ttl_seconds: float = max(0, ttl_minutes) * 60
        self._time_fn = time_fn
        self._entries: dict[str, _Entry] = {}
        self._lock = threading.Lock()

    def put(self, analysis: Analysis) -> str:
        """Store an analysis and return its ``session_id``."""
        session_id = analysis.session_id
        expires_at = self._time_fn() + self._ttl_seconds
        with self._lock:
            self._entries[session_id] = _Entry(analysis=analysis, expires_at=expires_at)
        return session_id

    def get(self, session_id: str) -> Optional[Analysis]:
        """Return the stored analysis, or ``None`` if missing or expired.

        Expired entries are removed on access.
        """
        now = self._time_fn()
        with self._lock:
            entry = self._entries.get(session_id)
            if entry is None:
                return None
            if entry.expires_at <= now:
                del self._entries[session_id]
                return None
            return entry.analysis

    def purge(self) -> int:
        """Remove all expired entries. Returns the number removed."""
        now = self._time_fn()
        with self._lock:
            expired = [sid for sid, e in self._entries.items() if e.expires_at <= now]
            for sid in expired:
                del self._entries[sid]
        return len(expired)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)


_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """Return the process-wide session store (lazily created from settings)."""
    global _store
    if _store is None:
        from app.config import get_settings

        _store = SessionStore(ttl_minutes=get_settings().session_ttl_minutes)
    return _store
