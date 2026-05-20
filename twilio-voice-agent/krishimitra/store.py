"""In-memory farmer call context (keyed by context_id for Twilio webhooks)."""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

_lock = threading.Lock()
_STORE: Dict[str, Dict[str, Any]] = {}


def put(context_id: str, data: Dict[str, Any]) -> None:
    with _lock:
        _STORE[context_id] = dict(data)


def get(context_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        item = _STORE.get(context_id)
        return dict(item) if item else None


def pop(context_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        item = _STORE.pop(context_id, None)
        return dict(item) if item else None
