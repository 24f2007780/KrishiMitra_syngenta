# Twilio SMS

## Goal

Outbound SMS: given **to number**, **message body**, and optional **metadata** (grower_id, delivery_id), send via Twilio and return a message SID for logging.

## Layout (you add files)

Suggested files when you implement:

- `app.py` — interactive CLI: prompts for number, message, optional grower_id; calls Twilio; prints SID.
- `client.py` (optional) — thin wrapper used by both CLI and main app.
- `tests/` — pytest with mocked Twilio client, or a `test_send_dry_run.py` that never calls the API.

## Environment

Document in root `.env.example`:

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_SMS_FROM` (your Twilio SMS-capable number)

## How to test (manual)

1. Set env vars; use Twilio trial rules (verified destination numbers) if on trial.
2. Run your future `app.py`; send one short test string to your own phone.
3. Confirm delivery in Twilio console and optionally via status callback URL later.

## Integration with main app

- Same function the CLI calls becomes what M16 (or a delivery worker) invokes after M10 produces `sms_text`.
- Keep **length** (160 chars) enforced upstream in M10, not in Twilio layer.

## Empty placeholder

This folder is ready for your code. Add `app.py` when you start.
