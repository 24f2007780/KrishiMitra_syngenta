# WhatsApp Web (`whatsapp_apps/`)

Unofficial **WhatsApp Web** automation for **demo/dev** using [Neonize](https://github.com/krypton-byte/neonize) (Whatsmeow). You scan a QR once; the session is saved locally.

**Not for production** — use Meta Cloud API or Twilio WhatsApp for real deployments.

## Setup

```bash
cd KrishiMitra_syngenta
cp .env.example .env
# Set TEST_PHONE_NUMBER=9876543210  (your phone for tests)

python -m venv .venv
source .venv/bin/activate
pip install neonize qrcode python-dotenv
```

## 1) Link your phone (first time only)

```bash
python -m whatsapp_apps.web.app login
```

1. A **QR** appears in the terminal (or a long pairing string).
2. On your phone: **WhatsApp → Linked devices → Link a device** → scan.
3. When you see `WhatsApp Web: connected.`, press **Ctrl+C**.
4. Session is saved under `whatsapp_apps/web/sessions/krishimitra.sqlite3` (do not commit).

## 2) Send a test message

Recipient must be a number you can message on WhatsApp (often need an existing chat or they must have your number).

```bash
# Dry run (no send)
python -m whatsapp_apps.web.app send --to 9876543210 --body "Hello from KrishiMitra" --dry-run

# Real send
python -m whatsapp_apps.web.app send --to 9876543210 --body "Hello from KrishiMitra"
```

Or interactive:

```bash
python -m whatsapp_apps.web.app
```

## Use from main app

```python
from whatsapp_apps.web.client import send_whatsapp

send_whatsapp("+919876543210", whatsapp_text_from_m11)
```

## Troubleshooting

| Issue | What to do |
|-------|------------|
| No QR / connect error | `pip install -U neonize`; Python 3.10+; retry `login` |
| Timeout waiting for connect | Run `login` first; scan QR before it expires (~60s) |
| Message not delivered | Number must include country code; open chat once manually on phone |
| Session invalid | Delete `whatsapp_apps/web/sessions/*.sqlite3` and `login` again |
| Account restricted | Unofficial clients can trigger limits — use a test number |

## Env vars

See root `.env.example`: `TEST_PHONE_NUMBER`, `WHATSAPP_SESSION_DIR`, `WHATSAPP_SESSION_NAME`.
