"""
Run the WhatsApp Web bot (RedShot + Selenium).

Limitations vs whatsapp-web.js / Baileys:
  RedShot only reacts to chats that appear under WhatsApp's *Unread* filter (sidebar
  badge). If the conversation is open or already marked read, no event fires — so
  you won't get replies. For event-driven "every message" behaviour in Python,
  consider Playwright-based whatsplay or the official Cloud API (e.g. pywa).

Usage:
  cd whatsapp-bot && pip install -r requirements.txt
  WHATSAPP_HEADLESS=false python -m whatsapp_bot   # false = visible window (not headless)

After you see "WhatsApp Web session active", send a *new* 1:1 message from another
phone so the chat shows an unread count; keep that chat closed on the desktop.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from whatsapp_bot.redshot_patch import ensure_redshot_message_py_fixed

if not ensure_redshot_message_py_fixed():
    logging.getLogger("whatsapp_bot").warning("redshot not found on path; patch skipped.")

from redshot import Client
from redshot.auth import LocalProfileAuth
from redshot.object import Message, SearchResult
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options

from whatsapp_bot.config import (
    CHROME_PROFILE_DIR,
    KNOWLEDGE_DIR,
    QR_OUTPUT,
    allowed_chat_titles,
    chrome_extra_args,
    headless,
    load_dotenv_layers,
    load_persona,
    verbose_logs,
)
from whatsapp_bot.gemini_service import from_env
from whatsapp_bot.rag_index import RagIndex

logger = logging.getLogger("whatsapp_bot")

_HB_AT = 0.0

DEFAULT_PERSONA = (
    "You are a helpful and friendly AI customer support agent (dcVoice). "
    "Be warm, patient, and professional. "
    "Always reply in the same language as the user's most recent message."
)


def _fingerprint(msg: Message) -> str:
    u = (msg.info.user or "").strip()
    t = (msg.text or "").strip()
    tm = msg.info.time or ""
    return f"{u}|{tm}|{t}"


class WhatsAppClient(Client):
    """RedShot Client with optional extra Chrome flags (servers, sandbox)."""

    def __init__(
        self,
        auth=None,
        poll_freq=0.25,
        unread_messages_sleep=0.5,
        headless=True,
        extra_chrome_args: list[str] | None = None,
    ):
        self._extra_chrome_args = extra_chrome_args or []
        super().__init__(
            auth=auth,
            poll_freq=poll_freq,
            unread_messages_sleep=unread_messages_sleep,
            headless=headless,
        )

    def _init_driver(self):
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        for arg in self._extra_chrome_args:
            options.add_argument(arg)
        self.auth.add_arguments(options)
        return Chrome(options=options)


def _vlog(msg: str, *args) -> None:
    if verbose_logs():
        logger.info(msg, *args)


def main() -> None:
    load_dotenv_layers()
    CHROME_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    hl = headless()
    raw_hl = os.getenv("WHATSAPP_HEADLESS", "(unset)")
    logger.info(
        "WHATSAPP_HEADLESS=%r → %s Chrome window (set false for first-time QR login).",
        raw_hl,
        "hidden" if hl else "visible",
    )

    persona = load_persona(DEFAULT_PERSONA)
    try:
        llm = from_env(persona)
    except RuntimeError as e:
        logger.error("%s", e)
        sys.exit(1)

    rag = RagIndex(KNOWLEDGE_DIR)
    if not rag.is_ready:
        logger.warning("RAG index empty; bot will rely on persona only.")

    allow = allowed_chat_titles()
    last_handled: dict[str, str] = {}

    auth = LocalProfileAuth(str(CHROME_PROFILE_DIR), profile="selenium")
    client = WhatsAppClient(
        auth=auth,
        headless=hl,
        poll_freq=0.35,
        unread_messages_sleep=0.6,
        extra_chrome_args=chrome_extra_args(),
    )

    def shutdown(*_args):
        logger.info("Stopping…")
        try:
            client.stop()
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    @client.event("on_start")
    def _on_start():
        logger.info("Browser starting (headless=%s)", hl)

    @client.event("on_auth")
    def _on_auth():
        logger.info("WhatsApp Web: waiting for QR or linked-device flow…")

    @client.event("on_loading")
    def _on_loading(loading_chats: bool):
        logger.info("WhatsApp Web: loading (chats UI=%s)…", loading_chats)

    @client.event("on_qr")
    def _on_qr(qr_binary: bytes):
        QR_OUTPUT.write_bytes(qr_binary)
        logger.info("Scan QR code image: %s", QR_OUTPUT.resolve())

    @client.event("on_qr_change")
    def _on_qr_change(qr_binary: bytes):
        QR_OUTPUT.write_bytes(qr_binary)
        logger.info("QR refreshed: %s", QR_OUTPUT.resolve())

    @client.event("on_logged_in")
    def _on_logged_in():
        logger.info("WhatsApp Web session active.")
        logger.info(
            "Reminder: this bot only handles 1:1 chats that show an *unread* badge. "
            "Leave the chat closed here, send from your phone, then wait a few seconds."
        )

    @client.event("on_tick")
    def _on_tick():
        global _HB_AT
        if not verbose_logs():
            return
        now = time.monotonic()
        if now - _HB_AT < 90.0:
            return
        _HB_AT = now
        logger.info(
            "Verbose heartbeat: still polling (unread filter). "
            "No reply usually means login incomplete, allowlist, or chat already read/open."
        )

    @client.event("on_unread_chat")
    def _on_unread_chat(chat: SearchResult):
        # RedShot sets `group` for group rows (see parse_search_result); 1:1 chats omit it.
        if chat.has_group():
            _vlog(
                "Skip group chat (personal only): title=%r group=%r",
                chat.title,
                chat.group,
            )
            return

        title = (chat.title or "").strip()
        if not title:
            return
        if allow is not None and title not in allow:
            logger.warning(
                "Skip chat %r — not in WHATSAPP_ALLOWED_CHATS (allowlist is on).",
                title,
            )
            return

        logger.info("Unread 1:1 chat: %r — fetching messages…", title)

        try:
            messages = client.get_recent_messages(title, sleep=1.0)
        except Exception:
            logger.exception("get_recent_messages failed for %r", title)
            return

        if not messages:
            logger.warning("No messages parsed for %r (WhatsApp UI may have changed).", title)
            return

        last_incoming = None
        for m in reversed(messages):
            user = (m.info.user or "").strip().lower()
            if user and user != "you":
                last_incoming = m
                break

        if last_incoming is None:
            logger.info(
                "Skip %r: no message from others in loaded pane (only outgoing/'You' or empty sender).",
                title,
            )
            return

        fp = _fingerprint(last_incoming)
        if last_handled.get(title) == fp:
            _vlog("Skip %r: already handled this message fingerprint.", title)
            return

        query = (last_incoming.text or "").strip()
        if len(query) < 2:
            _vlog("Skip %r: incoming text too short.", title)
            return

        ctx = rag.retrieve(query, top_k=4) if rag.is_ready else ""
        try:
            reply = llm.reply(query, ctx)
        except Exception:
            logger.exception("Gemini failed for chat %r", title)
            reply = (
                "I'm having trouble replying right now. Please try again shortly "
                "or ask for a human agent."
            )

        try:
            client.send_message(title, reply)
            last_handled[title] = fp
            logger.info("Replied to %r", title)
        except Exception:
            logger.exception("send_message failed for %r", title)

    logger.info(
        "Bot loop running: 1:1 only, groups ignored; RedShot = *unread* sidebar only "
        "(not like whatsapp-web.js). Ctrl+C to stop. Set WHATSAPP_VERBOSE=true for heartbeats."
    )
    client.run()


if __name__ == "__main__":
    main()
