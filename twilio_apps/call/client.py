"""Programmatic outbound call (same as CLI, for orchestrator / workers)."""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, Optional

from twilio.rest import Client

from twilio_apps.call import session_store
from twilio_apps.call.env_urls import voice_public_base_url


def place_interactive_call(
    to: str,
    context: Dict[str, Any],
    *,
    public_voice_base_url: Optional[str] = None,
    from_number: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
  Store ``context`` on disk, then dial ``to`` with TwiML URL
  ``{base}/voice/start/{session_id}`` (``GET`` by default from ``calls.create``).

  Webhook server must already be running and reachable at ``public_voice_base_url``.
  """
    base = (public_voice_base_url or voice_public_base_url()).rstrip("/")
    if not base and not dry_run:
        raise RuntimeError("Set PUBLIC_VOICE_BASE_URL / NGROK_PUBLIC_URL or pass public_voice_base_url")

    from_num = from_number or os.environ.get("TWILIO_PHONE_NUMBER") or os.environ.get("TWILIO_VOICE_FROM")
    if not from_num:
        raise RuntimeError("Set TWILIO_PHONE_NUMBER in .env")

    session_id = str(uuid.uuid4())
    session_store.set_session(session_id, context)
    start_url = f"{base}/voice/start/{session_id}"

    if dry_run:
        return {"dry_run": True, "to": to, "from": from_num, "url": start_url, "session_id": session_id}

    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        raise RuntimeError("Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")

    call = Client(sid, token).calls.create(to=to, from_=from_num, url=start_url, method="GET")
    return {
        "dry_run": False,
        "to": to,
        "from": from_num,
        "url": start_url,
        "session_id": session_id,
        "call_sid": call.sid,
    }
