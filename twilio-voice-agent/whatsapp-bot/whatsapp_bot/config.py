"""Paths and environment for the WhatsApp bot."""

from __future__ import annotations

import os
from pathlib import Path

WHATSAPP_BOT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = WHATSAPP_BOT_ROOT.parent
KNOWLEDGE_DIR = WHATSAPP_BOT_ROOT / "knowledge"
PERSONA_FILE = REPO_ROOT / "config" / "persona.txt"
CHROME_PROFILE_DIR = WHATSAPP_BOT_ROOT / ".chrome_profile"
QR_OUTPUT = WHATSAPP_BOT_ROOT / "qr.png"


def load_dotenv_layers() -> None:
    from dotenv import load_dotenv

    # Never override variables already set in the process env (e.g. export WHATSAPP_HEADLESS=false).
    load_dotenv(REPO_ROOT / ".env", override=False)
    load_dotenv(WHATSAPP_BOT_ROOT / ".env", override=False)


def verbose_logs() -> bool:
    return os.getenv("WHATSAPP_VERBOSE", "").lower() in ("1", "true", "yes")


def load_persona(fallback: str) -> str:
    try:
        return PERSONA_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return fallback


def allowed_chat_titles() -> set[str] | None:
    raw = os.getenv("WHATSAPP_ALLOWED_CHATS", "").strip()
    if not raw:
        return None
    return {s.strip() for s in raw.split(",") if s.strip()}


def headless() -> bool:
    return os.getenv("WHATSAPP_HEADLESS", "false").lower() in ("1", "true", "yes")


def chrome_extra_args() -> list[str]:
    raw = os.getenv("WHATSAPP_CHROME_ARGS", "").strip()
    if not raw:
        return []
    return [a for a in raw.split() if a]


def gemini_api_key() -> str:
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set (repo .env or whatsapp-bot/.env).")
    return key


def llm_model() -> str:
    return os.getenv("LLM_MODEL", "gemini-2.5-flash").strip()
