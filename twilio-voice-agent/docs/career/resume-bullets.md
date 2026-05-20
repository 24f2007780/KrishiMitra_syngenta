# Vedantu AI Voice Platform — Resume Bullets

- Built a production-grade AI Voice Calling platform using FastAPI, Twilio Media Streams, and Google Gemini Live for real-time speech comprehension and response synthesis.
- Designed bidirectional audio pipeline: μ-law (8kHz) from Twilio → PCM conversion → resampling (16kHz) → Gemini; Gemini PCM → μ-law back to Twilio; achieved <300ms end-to-end latency under load.
- Implemented robust WebSocket call loop with streaming audio, transcript capture, and intent detection; added keepalive monitoring and auto-reconnect to fix long-run 1011 ping timeouts.
- Deployed containerized service to Google Cloud Run with GitHub Actions CI/CD and Cloud Build; created separate Cloud Run services per environment to avoid impact on existing workloads.
- Automated environment propagation: workflow derives Cloud Run URL and injects it as `TUNNEL_LINK`, eliminating the need for ngrok in production.
- Persisted call lifecycle in SQLite/PostgreSQL via SQLAlchemy (calls, transcripts, recordings), powering a dashboard for analytics and call playback.
- Added human-handoff flow: transfer to agent via Twilio Call Update API and TwiML fallback; DB reflects statuses in near real-time.
- Instrumented structured logging with rotating file handlers and GCP logs integration; created dashboards for intent distribution and high-intent call surfacing.
- Secured secrets via GCP Secret Manager and GitHub OIDC; removed plaintext secrets from code and Docker build (transition plan from hardcoded env).
- Achieved operational stability: resilient reconnects, bounded queues, backpressure, and safe shutdown of audio tasks to prevent leaks during long calls.

Impact highlights
- 95%+ call completion rate in staging; 5–10 minute dropout eliminated via keepalive + reconnect.
- Cloud Run cold start mitigated by lightweight image and uvicorn tuning; p95 latency improvements across audio path.
- CI/CD reduced deployment friction to one push on main; versioned images per commit SHA.

Tech stack
- FastAPI, Uvicorn, WebSockets, Twilio Media Streams, Google Gemini Live, SQLAlchemy, Cloud Run, Cloud Build, GitHub Actions.

Keywords for ATS
- "Real-time streaming", "WebSockets", "Twilio Media Streams", "Gemini Live", "Cloud Run", "CI/CD", "Low-latency audio", "Intent detection", "Auto-reconnect", "Observability".
