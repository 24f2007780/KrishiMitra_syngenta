"""Call context for Twilio voice: memory + JSON files so CLI and uvicorn share state."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

_lock = threading.Lock()
_STORE: Dict[str, Dict[str, Any]] = {}


def _session_dir() -> Path:
    raw = os.environ.get("VOICE_SESSION_DIR", "").strip()
    if raw:
        p = Path(raw).expanduser().resolve()
    else:
        p = Path(__file__).resolve().parent / "sessions"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _path(session_id: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")
    if not safe or safe != session_id:
        raise ValueError("Invalid session_id")
    return _session_dir() / f"{safe}.json"


def set_session(session_id: str, data: Dict[str, Any]) -> None:
    """Persist so a separate uvicorn process (manual ngrok) can read the same session."""
    with _lock:
        _STORE[session_id] = data
    path = _path(session_id)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        if session_id in _STORE:
            return dict(_STORE[session_id])
    path = _path(session_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if isinstance(data, dict):
        with _lock:
            _STORE[session_id] = data
        return dict(data)
    return None


def pop_session(session_id: str) -> None:
    with _lock:
        _STORE.pop(session_id, None)
    try:
        _path(session_id).unlink(missing_ok=True)
    except ValueError:
        pass
