# Run guide — create context & place a call

Short steps to run the KrishiMitra voice agent, save a farmer context JSON, and dial out via Twilio.

---

## Prerequisites

1. **Env** — parent repo or this folder:

   ```bash
   # KrishiMitra_syngenta/.env  (preferred)
   TWILIO_ACCOUNT_SID=...
   TWILIO_AUTH_TOKEN=...
   TWILIO_PHONE_NUMBER=+1...
   GEMINI_API_KEY=...
   ```

2. **Python deps** (once):

   ```bash
   cd twilio-voice-agent
   pip install -r requirements.txt
   ```

   On this machine you can use:

   ```bash
   export PYTHON=/storage/.venvs/vedantu-voice-agent/bin/python
   ```

3. **ngrok** on `PATH` (for Twilio webhooks). Trial Twilio accounts must have the destination number verified.

---

## Step 1 — Start the server (keep this terminal open)

```bash
cd twilio-voice-agent
export PYTHON_CMD=/storage/.venvs/vedantu-voice-agent/bin/python   # optional; or use your venv
./start.sh
```

Wait until you see:

- `Uvicorn running on http://127.0.0.1:8000`
- `ngrok: https://....ngrok-free.app`

**Do not close this terminal** while calling.

Quick check (second terminal):

```bash
curl http://127.0.0.1:8000/krishimitra/health
# → {"status":"ok", ... "tunnel_configured":true, "twilio_configured":true}
```

If `curl` fails with **Connection refused**, the server is not running — go back to Step 1.

---

## Step 2 — Create a farmer context file

Copy an example and edit it:

```bash
cd twilio-voice-agent/config
cp farmer_context.example.json farmer_<name>.json
```

Or copy a working regional example:

| File | Farmer | Language |
|------|--------|----------|
| `farmer_mayur.example.json` | Mayur, Gujarat | Gujarati |
| `farmer_rajnish.example.json` | Rajnish, Bihar | Bhojpuri |
| `farmer_context.example.json` | Template | Tamil |

### Required / important fields

| Field | Example | Notes |
|-------|---------|--------|
| `to_number` | `+919152155576` | E.164 only (no spaces) |
| `farmer_name` | `Mayur` | Used in intro & AI prompt |
| `preferred_language` | `Gujarati` | Drives Twilio `<Say>` locale (`gu-IN`, `hi-IN`, `ta-IN`, …) |
| `state` / `district` / `village` | `Gujarat`, `Anand`, `Boriavi` | Location context |
| `crop` or `crops` | `cotton` | Primary crop |
| `crop_stage` | `flowering` | Growth stage |
| `active_pest` | `whitefly` | Current threat |
| `why_now` | One sentence | **Why call today** (hackathon “context-first”) |
| `recommended_product` | `Amistar` | Advisory product |
| `retailer_name` | `Shree Krushi Udyog Kendra` | Where to buy / ask |
| `intro_script` | (optional) | Exact phone opening in farmer’s language. If omitted, Hindi intro is auto-built. |
| `example_message_en` | (optional) | Your notes only; not sent to Twilio |

**Phone number format:** `+91 91521 55576` → write as `+919152155576`.

**`intro_script` tips:** Write 2–4 short sentences in the farmer’s language (Gujarati script, Devanagari, etc.). Mention name, village, crop, pest, product, and “ask me anything.”

Minimal new farmer example:

```json
{
  "to_number": "+919876543210",
  "farmer_id": "GJ-099",
  "farmer_name": "Kiran",
  "preferred_language": "Gujarati",
  "state": "Gujarat",
  "district": "Rajkot",
  "village": "Gondal",
  "crops": ["groundnut"],
  "crop": "groundnut",
  "crop_stage": "pod formation",
  "pest_risk_level": "medium",
  "active_pest": "leaf miner",
  "why_now": "Dry spell followed by rain; leaf miner activity rising on groundnut.",
  "recommended_product": "Actara",
  "retailer_name": "Village Krishi Kendra",
  "urgency_score": 0.6
}
```

Save as `config/farmer_kiran.json`.

---

## Step 3 — Place the call

**New terminal** (server still running in the first):

```bash
cd twilio-voice-agent
/storage/.venvs/vedantu-voice-agent/bin/python scripts/krishimitra_call.py \
  --json config/farmer_mayur.example.json
```

Override phone without editing JSON:

```bash
/storage/.venvs/vedantu-voice-agent/bin/python scripts/krishimitra_call.py \
  --json config/farmer_mayur.example.json \
  --to +919152155576
```

Success looks like:

```text
POST http://127.0.0.1:8000/krishimitra/call
200 {"success":true,"call_sid":"CA...","context_id":"...","message":"Calling +91..."}
```

Answer the phone — Gujarati/Hindi/etc. intro, then live conversation with Gemini.

**Alternative (curl):**

```bash
curl -X POST http://127.0.0.1:8000/krishimitra/call \
  -H "Content-Type: application/json" \
  -d @config/farmer_mayur.example.json
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Connection refused` on port 8000 | Start `./start.sh` first; confirm with `curl .../health` |
| `TUNNEL_LINK not set` | Run `./start.sh` (starts ngrok) or set `TUNNEL_LINK` in `.env` to current ngrok https URL |
| Call rings but “application error” | ngrok URL changed — restart `./start.sh` and use the new URL |
| No AI audio after intro | Check `GEMINI_API_KEY`; see `logs/app.log` |
| Twilio won’t dial number | Trial account: verify destination in Twilio console |

Ngrok inspector: http://127.0.0.1:4040 — confirm requests to `/twilio/voice` and WebSocket `/ws/call`.

---

## One-page cheat sheet

```bash
# Terminal 1
cd twilio-voice-agent && ./start.sh

# Terminal 2
curl http://127.0.0.1:8000/krishimitra/health
cp config/farmer_context.example.json config/farmer_NEW.json
# edit farmer_NEW.json (to_number, name, language, crop, intro_script)
/storage/.venvs/vedantu-voice-agent/bin/python scripts/krishimitra_call.py --json config/farmer_NEW.json
```

More detail: `README_KRISHIMITRA.md`.

---

## SMS (same farmer JSON)

No server or ngrok needed for SMS — only Twilio env vars.

**From this folder (`twilio-voice-agent`):**

```bash
/storage/.venvs/vedantu-voice-agent/bin/python scripts/send_farmer_sms.py \
  --json config/farmer_mayur.example.json --preview

/storage/.venvs/vedantu-voice-agent/bin/python scripts/send_farmer_sms.py \
  --json config/farmer_mayur.example.json
```

**From repo root (`KrishiMitra_syngenta`):**

```bash
cd ..
/storage/.venvs/vedantu-voice-agent/bin/python -m sms_service.scripts.send_farmer_sms \
  --json twilio-voice-agent/config/farmer_mayur.example.json
```

SMS text priority: `sms_script` → `example_message_en` → `intro_script` → auto English.

---

## WhatsApp (same farmer JSON)

Uses **WhatsApp Web** (Neonize). Link your phone once, then send from context JSON.

**0. Install WhatsApp deps (once per venv):**

```bash
cd ~/Desktop/syngenta/KrishiMitra_syngenta
/storage/.venvs/vedantu-voice-agent/bin/pip install -r whatsapp_apps/requirements.txt
```

If you see `No module named 'neonize'` or a **Protobuf version** error, run the command above (neonize needs `protobuf>=7.34.1`).

**1. Login (once — scan QR):**

```bash
/storage/.venvs/vedantu-voice-agent/bin/python -m whatsapp_apps.web.app login
```

**2. From `twilio-voice-agent`:**

```bash
/storage/.venvs/vedantu-voice-agent/bin/python scripts/send_farmer_whatsapp.py \
  --json config/farmer_mayur.example.json --preview

/storage/.venvs/vedantu-voice-agent/bin/python scripts/send_farmer_whatsapp.py \
  --json config/farmer_mayur.example.json
```

**From repo root:**

```bash
python -m whatsapp_service.scripts.send_farmer_whatsapp \
  --json twilio-voice-agent/config/farmer_mayur.example.json
```

WhatsApp text priority: `whatsapp_script` → `sms_script` → `example_message_en` → `intro_script` → auto English.

Or: `python -m whatsapp_apps.web.app send --json twilio-voice-agent/config/farmer_mayur.example.json`
