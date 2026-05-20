# KrishiMitra — Twilio voice agent

This folder is the **working** voice stack: **Twilio Media Streams** + **Gemini Live** (real two-way speech).  
It replaces the older `twilio_apps/call` Gather + TwiML approach that was failing with ngrok.

## Why this works

| Old (`twilio_apps/call`) | This folder |
|--------------------------|-------------|
| Twilio fetches one TwiML URL per step | WebSocket audio stream |
| Breaks on ngrok HTML / POST issues | Same pattern as your other project |
| One-shot `<Gather>` | Continuous conversation |

## Setup

1. Copy env (or use parent `KrishiMitra_syngenta/.env`):

   ```bash
   cd twilio-voice-agent
   cp .env.example .env
   # GEMINI_API_KEY, TWILIO_*, TUNNEL_LINK or NGROK_PUBLIC_URL
   ```

2. Install:

   ```bash
   python -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Start server + ngrok:

   ```bash
   ./start.sh
   # or: PORT=8000 START_NGROK=1 ./start.sh
   ```

   Copy the printed `TUNNEL_LINK` into `.env` if needed.

## Place a KrishiMitra call

```bash
curl -X POST http://127.0.0.1:8000/krishimitra/call \
  -H "Content-Type: application/json" \
  -d @config/farmer_context.example.json
```

Or use the CLI:

```bash
python scripts/krishimitra_call.py --to +919471961925
```

Answer the phone — you should hear the KrishiMitra intro, then talk to the AI in your language.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/krishimitra/call` | Outbound call with farmer JSON body |
| GET | `/krishimitra/health` | Config check |
| POST | `/twilio/voice` | Twilio webhook (used internally) |
| WS | `/ws/call` | Media stream (Twilio ↔ Gemini) |

## Persona & context

- Base persona: `config/persona.txt`
- Example payload: `config/farmer_context.example.json`
- Context is injected into Gemini **system instruction** per call.

## Env vars (main)

| Variable | Purpose |
|----------|---------|
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_PHONE_NUMBER` | Twilio |
| `GEMINI_API_KEY` | Google Gemini (voice AI) |
| `TUNNEL_LINK` or `NGROK_PUBLIC_URL` | Public https URL (no trailing slash) |
| `VOICE_ENGINE` | `gemini_live` (default) or `pipeline` |
| `LIVE_API` | `1` to use Live API model |

Parent repo `.env` is loaded automatically.

## Troubleshooting

- **No audio / app error:** open `http://127.0.0.1:4040` (ngrok inspector) and confirm Twilio hits `/twilio/voice` and `/ws/call` with 200.
- **Gemini errors:** check `GEMINI_API_KEY` and `logs/app.log`.
- **Trial Twilio:** destination number must be verified.
