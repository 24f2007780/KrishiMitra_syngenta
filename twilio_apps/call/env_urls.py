"""Resolve public HTTPS base for Twilio voice webhooks (ngrok or deployed host)."""

from __future__ import annotations

import os


def voice_public_base_url() -> str:
    """
    Origin Twilio must use for /voice/* callbacks.
    Set one of these in .env (same value, no trailing slash):
    PUBLIC_VOICE_BASE_URL, NGROK_PUBLIC_URL, or NGROK_VOICE_BASE_URL.
    """
    for key in (
        "PUBLIC_VOICE_BASE_URL",
        "NGROK_PUBLIC_URL",
        "NGROK_VOICE_BASE_URL",
    ):
        v = (os.environ.get(key) or "").strip().rstrip("/")
        if v:
            return v
    return ""
