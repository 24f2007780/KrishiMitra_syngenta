#!/usr/bin/env python3
"""
Send KrishiMitra WhatsApp from farmer context JSON.

Run from twilio-voice-agent:

    python scripts/send_farmer_whatsapp.py --json config/farmer_mayur.example.json --preview
    python scripts/send_farmer_whatsapp.py --json config/farmer_mayur.example.json

First-time login (scan QR once):

    cd .. && python -m whatsapp_apps.web.app login
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from whatsapp_service.scripts.send_farmer_whatsapp import main  # noqa: E402

if __name__ == "__main__":
    main()
