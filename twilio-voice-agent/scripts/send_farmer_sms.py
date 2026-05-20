#!/usr/bin/env python3
"""
Send KrishiMitra SMS from farmer context JSON.

Run from twilio-voice-agent (recommended):

    python scripts/send_farmer_sms.py --json config/farmer_mayur.example.json
    python scripts/send_farmer_sms.py --json config/farmer_mayur.example.json --preview
    python scripts/send_farmer_sms.py --json config/farmer_mayur.example.json --dry-run

Or from repo root (KrishiMitra_syngenta):

    python -m sms_service.scripts.send_farmer_sms --json twilio-voice-agent/config/farmer_mayur.example.json
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from sms_service.scripts.send_farmer_sms import main  # noqa: E402

if __name__ == "__main__":
    main()
