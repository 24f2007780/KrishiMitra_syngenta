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

Uses local webhook on port **`8765`** (override with `VOICE_WEBHOOK_PORT` in `.env`) and **pyngrok** by default. Set `NGROK_AUTHTOKEN` in `.env`.

Without ngrok (you run the tunnel yourself — e.g. `ngrok http 8765`):

```bash
# Terminal 1: webhook on 8765 (or your VOICE_WEBHOOK_PORT)
python -m uvicorn twilio_apps.call.webhook_server:app --host 0.0.0.0 --port 8765

# Terminal 2: set PUBLIC_VOICE_BASE_URL / NGROK_PUBLIC_URL / NGROK_VOICE_BASE_URL in .env to the ngrok https URL (no trailing slash), then:
python -m twilio_apps.call.app --no-ngrok
```

With `--no-ngrok`, the script **does not** bind port 8765 again — keep your existing uvicorn + ngrok running.

Import in main app:

```python
from twilio_apps.call.client import place_interactive_call
```

**Limitation:** This is turn-based (one question per call), not full duplex LiveKit-style conversation. Good for hackathon demo; upgrade to Media Streams or LiveKit later if needed.

## Voice: “We’re sorry, an application error occurred”

Twilio plays that when the webhook URL returns **non‑TwiML** (often HTML) or **HTTP error** (4xx/5xx).

### Most common fix (this repo)

1. **HTTP method:** Twilio defaults to **POST** for your TwiML `url`. The handler must accept POST (and we set `method="GET"` on `calls.create` as well).

2. **Session in the URL path:** For POST, **query strings are not always preserved** the way you expect. Use **`/voice/start/{session_id}`** (not `?session_id=`). The app now uses path-based URLs and writes session JSON to `twilio_apps/call/sessions/` so a separate uvicorn process can read it.

3. **Valid TwiML on errors:** Unhandled exceptions now return **HTTP 200 + spoken error** so Twilio does not receive FastAPI’s HTML error page.

4. **Smoke test (no session file):** After ngrok + uvicorn are up:

   ```bash
   curl -sS -X POST "https://YOUR-NGROK.ngrok-free.app/voice/twilio-ping"
   ```

   You should see **XML** starting with `<?xml` and `<Response>`. If you see **HTML** (ngrok warning page), Twilio will keep failing until you fix the tunnel ([ERR_NGROK_6024](https://ngrok.com/docs/errors/err_ngrok_6024)) — e.g. **Cloudflare Tunnel** or **paid ngrok**.

Restart **uvicorn** after pulling, then run the call script again.

### If it still fails

1. **Test the tunnel from your laptop** (replace with your ngrok URL):

   ```bash
   curl -sS "https://YOUR-SUBDOMAIN.ngrok-free.app/health"
   ```

   You want JSON `{"status":"ok",...}`. If you get HTML (browser warning page), **Twilio will fail** — ngrok free sometimes blocks non-browser clients ([ERR_NGROK_6024](https://ngrok.com/docs/errors/err_ngrok_6024); Twilio cannot send `ngrok-skip-browser-warning`).

2. **Try the same URL with the ngrok skip header** (Twilio cannot send this header; this only checks if the warning page is the issue):

   ```bash
   curl -sS -H "ngrok-skip-browser-warning: true" "https://YOUR-SUBDOMAIN.ngrok-free.app/health"
   ```

   If this works **without** the header it fails, use a **paid ngrok reserved domain**, **Cloudflare Tunnel** (`cloudflared tunnel --url http://localhost:8765`), or run **`python -m twilio_apps.call.app`** without `--no-ngrok` so **pyngrok** opens the tunnel in-process.

3. **`.env` URL** — use **HTTPS**, **no trailing slash**:

   `https://ca3f-....ngrok-free.app`  
   Set **one** of: `PUBLIC_VOICE_BASE_URL`, `NGROK_PUBLIC_URL`, or `NGROK_VOICE_BASE_URL`.

4. **Manual ngrok + separate uvicorn** — the CLI writes the call session to **`twilio_apps/call/sessions/*.json`**, so the webhook process can read it. Order: start **uvicorn** → start **ngrok** → run **`python -m twilio_apps.call.app --no-ngrok --to +91...`**.

5. **Twilio Debugger** — Console → **Monitor → Logs → Errors** shows the exact HTTP status and URL Twilio requested.
