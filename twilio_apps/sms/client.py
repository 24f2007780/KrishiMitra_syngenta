"""Thin Twilio SMS wrapper for CLI and future orchestrator imports."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from twilio.rest import Client


def _client() -> Client:
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        raise RuntimeError("Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env")
    return Client(sid, token)


def send_sms(
    to: str,
    body: str,
    *,
    from_number: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Send an outbound SMS.

    ``to`` and ``from_number`` should be E.164 (e.g. +15551234567).
    """
    from_num = from_number or os.environ.get("TWILIO_PHONE_NUMBER") or os.environ.get("TWILIO_SMS_FROM")
    if not from_num:
        raise RuntimeError("Set TWILIO_PHONE_NUMBER (or TWILIO_SMS_FROM) in .env")

    if dry_run:
        return {
            "dry_run": True,
            "to": to,
            "from": from_num,
            "body": body,
            "sid": None,
            "status": "dry_run",
        }

    client = _client()
    msg = client.messages.create(to=to, from_=from_num, body=body)
    return {
        "dry_run": False,
        "to": to,
        "from": from_num,
        "body": body,
        "sid": msg.sid,
        "status": getattr(msg, "status", None),
    }
