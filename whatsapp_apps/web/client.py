"""
WhatsApp Web client (Neonize / Whatsmeow).

Session is stored under whatsapp_apps/web/sessions/ — scan QR once, then reuse.
"""

from __future__ import annotations

import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SESSION_DIR = _ROOT / "whatsapp_apps" / "web" / "sessions"

SESSION_DIR = Path(os.environ.get("WHATSAPP_SESSION_DIR", str(_DEFAULT_SESSION_DIR)))
SESSION_NAME = os.environ.get("WHATSAPP_SESSION_NAME", "krishimitra")

_client = None
_connect_thread: Optional[threading.Thread] = None
_connected = threading.Event()
_lock = threading.Lock()


def normalize_phone(to: str, default_country_code: str = "91") -> str:
    """Digits only, E.164 without + (e.g. 919876543210)."""
    s = re.sub(r"\D", "", to or "")
    if not s:
        raise ValueError("Empty phone number")
    if s.startswith("0") and len(s) == 11:
        s = default_country_code + s[1:]
    if len(s) == 10 and default_country_code:
        s = default_country_code + s
    return s


def session_db_path() -> Path:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    return SESSION_DIR / f"{SESSION_NAME}.sqlite3"


def _print_qr_payload(data: Any) -> None:
    text = data if isinstance(data, str) else str(data)
    try:
        import qrcode

        qr = qrcode.QRCode(border=1)
        qr.add_data(text)
        qr.print_ascii(invert=True)
    except Exception:
        print("Pairing payload (open WhatsApp → Linked devices → Link a device):")
        print(text)
        print("\nTip: pip install qrcode  →  ASCII QR in this terminal")


def _qr_codes_from_event(ev: Any) -> List[str]:
    codes = getattr(ev, "Codes", None) or getattr(ev, "codes", None)
    if codes:
        return [str(c) for c in codes]
    one = getattr(ev, "Code", None) or getattr(ev, "code", None)
    return [str(one)] if one else []


def _ensure_client():
    global _client
    if _client is not None:
        return _client

    from neonize.client import NewClient
    from neonize.events import ConnectedEv, QREv

    db = str(session_db_path())
    _client = NewClient(db)

    @_client.event(ConnectedEv)
    def on_connected(c, _ev):  # noqa: ARG001
        _connected.set()
        print("WhatsApp Web: connected.")

    @_client.event(QREv)
    def on_qr(_c, ev):  # noqa: ARG001
        print("\n--- Scan QR (phone: WhatsApp → Linked devices → Link a device) ---\n")
        for code in _qr_codes_from_event(ev):
            _print_qr_payload(code)
        print()

    return _client


def connect(timeout: float = 180) -> None:
    """Start background connection; block until ConnectedEv or timeout."""
    global _connect_thread

    with _lock:
        _connected.clear()
        client = _ensure_client()

        if _connect_thread is None or not _connect_thread.is_alive():

            def _run():
                try:
                    client.connect()
                except Exception as exc:
                    print(f"WhatsApp connect error: {exc}")

            _connect_thread = threading.Thread(target=_run, daemon=True)
            _connect_thread.start()

    if not _connected.wait(timeout):
        raise TimeoutError(
            f"WhatsApp not connected within {timeout}s. "
            "Run: python -m whatsapp_apps.web.app login — scan QR, then retry send."
        )


def send_whatsapp(
    to: str,
    body: str,
    *,
    dry_run: bool = False,
    connect_timeout: float = 180,
) -> Dict[str, Any]:
    """
    Send a text message to ``to`` (E.164 or 10-digit Indian mobile).

    Reuses saved session when possible; otherwise shows QR in the terminal.
    """
    normalized = normalize_phone(to)
    if dry_run:
        return {
            "dry_run": True,
            "to": normalized,
            "body": body,
            "status": "dry_run",
            "session": str(session_db_path()),
        }

    connect(timeout=connect_timeout)
    from neonize.utils import build_jid

    client = _ensure_client()
    jid = build_jid(normalized)
    try:
        client.send_message(jid, text=body)
    except TypeError:
        client.send_message(jid, body)

    return {
        "dry_run": False,
        "to": normalized,
        "body": body,
        "status": "sent",
        "session": str(session_db_path()),
    }


def run_login_loop() -> None:
    """Connect and keep process alive (first-time QR or session refresh)."""
    from neonize.events import event

    connect(timeout=300)
    print("Session file:", session_db_path())
    print("Press Ctrl+C to exit (session stays saved).")
    try:
        event.wait()
    except KeyboardInterrupt:
        print("\nStopped.")
