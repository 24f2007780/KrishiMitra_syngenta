"""In-memory call context keyed by session_id (replace with Redis for production)."""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

_lock = threading.Lock()
_STORE: Dict[str, Dict[str, Any]] = {}


def set_session(session_id: str, data: Dict[str, Any]) -> None:
    with _lock:
        _STORE[session_id] = data


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        return _STORE.get(session_id)


def pop_session(session_id: str) -> None:
    with _lock:
        _STORE.pop(session_id, None)
