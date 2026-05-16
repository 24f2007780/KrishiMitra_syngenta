# Twilio voice — interactive, personalised calls

## Goal

Place an **outbound call** where the system **listens to the farmer** and **replies in a personalised way**, using context from KrishiMitra (crop, risk, language, retailer, etc.). This is **not** “play a fixed script and hang up.”

## What you are building (conceptually)

1. **Outbound dial** — Twilio calls the farmer’s number.
2. **Bidirectional audio** — farmer speaks; your stack turns speech into text, runs an LLM with **farmer context**, turns reply into speech.
3. **Personalisation** — the “system prompt” or agent config is filled from the **context** you pass at dial time (and optionally short memory for this call only).

## Architecture options (choose one before coding)

| Option | When to use |
|--------|-------------|
| **Twilio Media Streams + your WebSocket server** | You want everything in your repo; comfortable with streaming audio, STT, LLM, TTS latency. |
| **LiveKit Agents + Twilio SIP / trunk** | You want a proper agent runtime, tools, and easier multi-step conversation. |
| **Third-party voice agent API** | Fastest path to “it talks back” for a demo; you pass context as JSON + phone number. |

Document your choice at the top of this README when decided.

## Layout (you add files)

Suggested files when you implement:

- `app.py` — interactive CLI: prompts for **callee number**, **context** (paste JSON or path to file), optional language; starts outbound call with TwiML or API that points to your **voice URL** or stream.
- `webhook/` or `server.py` — HTTP server Twilio hits for TwiML, `<Connect><Stream>`, or `<Gather>` depending on design.
- `agent/` — prompt templates, “build system message from FarmerContext”, max duration, safety rules.
- `tests/` — mock Twilio request signatures; unit tests for “context → prompt string” without placing real calls.

## Interactive CLI inputs (`app.py` behaviour you should aim for)

Ask the operator for:

1. **Phone number** (E.164, e.g. +91…)
2. **Context** — structured fields your agent needs: farmer name, crop, district, pest risk, why-now summary, recommended product, language, retailer name, etc. (can be multiline paste or path to `context.json`)
3. **Optional:** `dry_run` — print TwiML URL and payload without dialing
4. **Optional:** max call duration seconds

## Testing safely

- Use **your** phone as callee during development.
- **Trial accounts:** only verified numbers; upgrade or verify test numbers as needed.
- Add **dry_run** mode that logs what would be sent.
- For Media Streams / WebSocket: test locally with **ngrok** (or similar) so Twilio can reach your dev machine.

## Integration with main app / Redis

- **Synchronous:** orchestrator POSTs “start call” to a small FastAPI service that wraps the same logic as `app.py`.
- **Async:** enqueue `{ phone, context_ref or serialized context, delivery_id }`; worker runs the dial and updates delivery status via your existing M15-style API.
- **Context size:** keep prompts bounded; pass **IDs** to DB if context is huge, and let the voice worker fetch context.

## Compliance and UX (short)

- Brief **disclosure** at start of call (“This is an automated advisory call from …”) — align with team and hackathon rules.
- **Barge-in** and latency matter for “natural” feel; note in design doc if you accept higher latency for demo.

## Empty placeholder

This folder is ready for your code. Start with `README` updates + architecture choice, then `app.py` + minimal webhook.
