# Integrations (Twilio, WhatsApp)

This area holds **delivery** and **real-time channel** code that is **separate** from core KrishiMitra services (`farmer_service`, `context_service`, etc.).

## Layout

| Path | Role |
|------|------|
| `twilio_apps/` | SMS + interactive voice call; see `twilio_apps/README.md`. |
| `whatsapp_apps/` | WhatsApp Web (Neonize); see `whatsapp_apps/README.md`. |
| `whatsapp/` | Pointer to `whatsapp_apps/`. |

## Principles

1. **Content vs delivery** — M10/M11/M12 produce text; these folders **send** it (or start a voice session).
2. **CLI first** — each channel has an `app.py` (or similar) you can run with dummy prompts before wiring FastAPI or Redis.
3. **One import surface** — later, expose `send_sms`, `send_whatsapp`, `start_voice_call` (names up to you) so the orchestrator or workers do not depend on CLI internals.

## Environment

Keep all secrets in project-root `.env` (gitignored). Add `.env.example` at repo root listing Twilio and WhatsApp-related keys when you create them.

## Redis / workers

Workers should call the **same functions** the CLI uses, with payloads: `to`, `body` or `context`, `delivery_id`, `farmer_id`.
