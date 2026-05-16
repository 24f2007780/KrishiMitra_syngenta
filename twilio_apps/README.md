# Twilio SMS & voice (`twilio_apps/`)

**Note:** Code lives in `twilio_apps/` (not `twilio/`) so Python can `import twilio` from the official SDK.

## Setup

```bash
cd KrishiMitra_syngenta
cp .env.example .env
# Edit .env with Twilio Console credentials + your TEST_PHONE_NUMBER

pip install twilio anthropic python-dotenv
# Voice CLI also needs: pip install pyngrok uvicorn python-multipart
```

**Twilio trial:** verify `TEST_PHONE_NUMBER` in the Twilio console before sending SMS or calls.

## SMS test

```bash
python -m twilio_apps.sms.app
# or
python -m twilio_apps.sms.app --to +919876543210 --body "KrishiMitra test" --dry-run
```

Import in main app:

```python
from twilio_apps.sms.client import send_sms
```

## Interactive voice call

Flow: outbound call → intro `<Say>` → `<Gather speech>` → Anthropic reply → `<Say>` → hangup.

```bash
python -m twilio_apps.call.app
```

Uses local webhook on port `8765` and **pyngrok** by default. Set `NGROK_AUTHTOKEN` in `.env`.

Without ngrok (you run tunnel yourself):

```bash
# Terminal 1: expose port 8765, put URL in PUBLIC_VOICE_BASE_URL
python -m uvicorn twilio_apps.call.webhook_server:app --host 0.0.0.0 --port 8765

# Terminal 2
python -m twilio_apps.call.app --no-ngrok
```

Import in main app:

```python
from twilio_apps.call.client import place_interactive_call
```

**Limitation:** This is turn-based (one question per call), not full duplex LiveKit-style conversation. Good for hackathon demo; upgrade to Media Streams or LiveKit later if needed.
