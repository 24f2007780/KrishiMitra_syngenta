#!/usr/bin/env python3
"""
WhatsApp Web CLI (Neonize).

First time — link your phone (QR):

    python -m whatsapp_apps.web.app login

Send a test message:

    python -m whatsapp_apps.web.app send --to 9876543210 --body "KrishiMitra test"
    python -m whatsapp_apps.web.app send --to +919876543210 --body "Hello" --dry-run

Interactive:

    python -m whatsapp_apps.web.app
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from whatsapp_apps.web.client import run_login_loop, send_whatsapp  # noqa: E402


def _prompt(msg: str, default: str | None = None) -> str:
    hint = f" [{default}]" if default else ""
    s = input(f"{msg}{hint}: ").strip()
    if not s and default is not None:
        return default
    return s


def cmd_login(_args: argparse.Namespace) -> None:
    run_login_loop()


def cmd_send(args: argparse.Namespace) -> None:
    to = args.to or os.environ.get("TEST_WHATSAPP_NUMBER") or os.environ.get("TEST_PHONE_NUMBER", "")
    body = args.body or "KrishiMitra WhatsApp test."
    if not to:
        print("Need --to or TEST_PHONE_NUMBER in .env", file=sys.stderr)
        sys.exit(1)
    try:
        out = send_whatsapp(to, body, dry_run=args.dry_run)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(out)


def cmd_interactive() -> None:
    print("KrishiMitra — WhatsApp Web test\n")
    print("If this is your first time, run: python -m whatsapp_apps.web.app login\n")
    default_to = os.environ.get("TEST_WHATSAPP_NUMBER") or os.environ.get("TEST_PHONE_NUMBER", "")
    to = _prompt("To number (10-digit or +91...)", default_to)
    body = _prompt("Message", "KrishiMitra advisory test from WhatsApp Web.")
    dry = _prompt("Dry run only? (y/n)", "n").lower().startswith("y")
    try:
        print(send_whatsapp(to, body, dry_run=dry))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="WhatsApp Web (Neonize) for KrishiMitra")
    sub = parser.add_subparsers(dest="command")

    p_login = sub.add_parser("login", help="Show QR / connect and save session")
    p_login.set_defaults(func=cmd_login)

    p_send = sub.add_parser("send", help="Send one message")
    p_send.add_argument("--to", help="Recipient phone")
    p_send.add_argument("--body", default="KrishiMitra test")
    p_send.add_argument("--dry-run", action="store_true")
    p_send.set_defaults(func=cmd_send)

    args = parser.parse_args()
    if args.command == "login":
        cmd_login(args)
    elif args.command == "send":
        cmd_send(args)
    else:
        cmd_interactive()


if __name__ == "__main__":
    main()
