#!/usr/bin/env python3
"""
Place an outbound Twilio call that:
1) Speaks a short personalised intro (from prompts / context).
2) Listens with <Gather speech>.
3) Replies with a short LLM answer (Anthropic) or a template if no API key.

Requires public URL for webhooks. By default starts local FastAPI + pyngrok.

Run from repo root:

    python -m twilio_apps.call.app

Env: see repo .env.example (Twilio, VOICE_WEBHOOK_PORT, NGROK_PUBLIC_URL / PUBLIC_VOICE_BASE_URL, …).
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")

# Ensure project root on path for `python twilio_apps/call/app.py` style runs
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _prompt(msg: str, default: str | None = None) -> str:
    hint = f" [{default}]" if default else ""
    s = input(f"{msg}{hint}: ").strip()
    if not s and default is not None:
        return default
    return s


def main() -> None:
    parser = argparse.ArgumentParser(description="Outbound interactive Twilio voice test")
    parser.add_argument("--to", help="Callee E.164")
    parser.add_argument("--dry-run", action="store_true", help="Print plan only; no call / no tunnel")
    parser.add_argument(
        "--no-ngrok",
        action="store_true",
        help="Use PUBLIC_VOICE_BASE_URL or NGROK_PUBLIC_URL from .env (run ngrok yourself to VOICE_WEBHOOK_PORT)",
    )
    args, _ = parser.parse_known_args()

    from twilio.rest import Client

    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_num = os.environ.get("TWILIO_PHONE_NUMBER") or os.environ.get("TWILIO_VOICE_FROM")
    if not sid or not token or not from_num:
        print("Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER in .env", file=sys.stderr)
        sys.exit(1)

    if args.to:
        to = args.to
    else:
        print("KrishiMitra outbound voice test\n")
        to = _prompt("Callee E.164", os.environ.get("TEST_PHONE_NUMBER", ""))
    if not to:
        print("Need --to or TEST_PHONE_NUMBER default.", file=sys.stderr)
        sys.exit(1)

    farmer_name = _prompt("Farmer name", "Rajan Kumar") if not args.to else (os.environ.get("CALL_FARMER_NAME") or "Farmer")
    crop = _prompt("Primary crop", "rice") if not args.to else (os.environ.get("CALL_CROP") or "rice")
    district = _prompt("District", "Thanjavur") if not args.to else (os.environ.get("CALL_DISTRICT") or "")
    why = _prompt("Why-now (one line)", "High humidity; fungal risk on flowering rice.") if not args.to else (
        os.environ.get("CALL_WHY_NOW") or ""
    )
    speech_lang = _prompt("Speech language code for Twilio (BCP-47)", "en-IN") if not args.to else (
        os.environ.get("CALL_SPEECH_LANGUAGE") or "en-IN"
    )
    retailer = _prompt("Retailer name", "Suresh Agro Stores") if not args.to else (os.environ.get("CALL_RETAILER") or "")

    session_id = str(uuid.uuid4())
    intro = (
        f"Namaskaram {farmer_name}. This is KrishiMitra advisory. "
        f"You grow {crop} in {district}. {why} "
        f"If you need product support, ask {retailer}. "
        "Now please ask your question after the tone."
    )

    context = {
        "farmer_name": farmer_name,
        "crop": crop,
        "district": district,
        "why_now": why,
        "retailer_name": retailer,
        "speech_language": speech_lang,
        "intro_script": intro,
    }

    from twilio_apps.call import session_store
    from twilio_apps.call.env_urls import voice_public_base_url

    session_store.set_session(session_id, context)

    port = int(os.environ.get("VOICE_WEBHOOK_PORT", "8765"))
    public_base = voice_public_base_url()

    base_for_url = public_base or "https://example.com"
    start_url = f"{base_for_url.rstrip('/')}/voice/start/{session_id}"
    if args.dry_run:
        print("Dry run — would dial (start local webhook + set PUBLIC_VOICE_BASE_URL for a real run):")
        print("  to:", to)
        print("  from:", from_num)
        print("  url:", start_url)
        return

    if args.no_ngrok:
        if not public_base:
            print(
                "With --no-ngrok set PUBLIC_VOICE_BASE_URL, NGROK_PUBLIC_URL, or NGROK_VOICE_BASE_URL "
                f"to your ngrok HTTPS URL (tunnel must forward to this machine port {port}).",
                file=sys.stderr,
            )
            sys.exit(1)
        os.environ.setdefault("PUBLIC_VOICE_BASE_URL", public_base)
        print(
            f"Using existing webhook on port {port} (not starting another server). "
            "Ensure uvicorn is already running, e.g.:\n"
            f"  python -m uvicorn twilio_apps.call.webhook_server:app --host 0.0.0.0 --port {port}\n",
        )
    else:
        import uvicorn
        from twilio_apps.call.webhook_server import app as voice_app

        def _run_server():
            uvicorn.run(voice_app, host="0.0.0.0", port=port, log_level="warning")

        threading.Thread(target=_run_server, daemon=True).start()
        time.sleep(1.2)
        try:
            from pyngrok import conf, ngrok

            ngrok_token = os.environ.get("NGROK_AUTHTOKEN")
            if ngrok_token:
                conf.get_default().auth_token = ngrok_token
            tunnel = ngrok.connect(port, "http")
            public_base = tunnel.public_url.rstrip("/")
            os.environ["PUBLIC_VOICE_BASE_URL"] = public_base
            print(f"Public voice URL: {public_base}\n")
        except ImportError:
            print(
                "Install pyngrok or run with --no-ngrok and set NGROK_PUBLIC_URL or PUBLIC_VOICE_BASE_URL.",
                file=sys.stderr,
            )
            sys.exit(1)

    if not public_base:
        print("Could not determine public base URL (ngrok failed or env missing).", file=sys.stderr)
        sys.exit(1)

    start_url = f"{public_base.rstrip('/')}/voice/start/{session_id}"

    client = Client(sid, token)
    call = client.calls.create(to=to, from_=from_num, url=start_url, method="GET")
    print("Call initiated:", call.sid)
    print("Answer the phone; speak after the prompt. Ctrl+C exits this script (ngrok may stop).")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("Exiting.")
        if not args.no_ngrok:
            try:
                from pyngrok import ngrok

                ngrok.kill()
            except Exception:
                pass


if __name__ == "__main__":
    main()
