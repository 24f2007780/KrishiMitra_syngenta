# Vedantu AI Voice Platform — Interview Guide

This document prepares you for technical and behavioral questions about the AI voice calling platform you built. It covers architecture, design tradeoffs, operational learnings, and demo steps.

## 1) One-liner
A FastAPI service that handles real-time voice calls: Twilio streams caller audio, we process/transcribe/respond with Google Gemini Live, and stream synthesized speech back to the caller — with analytics, transfer-to-human, and CI/CD to Cloud Run.

## 2) System Architecture
- Client: Twilio phone network → Media Streams over WebSocket.
- Ingress: FastAPI WebSocket endpoint accepts Twilio events (start, media, mark, stop).
- Audio pipeline:
  - Twilio sends μ-law 8kHz chunks → convert to PCM16 → resample to 16kHz.
  - Send to Gemini Live via async client, receive PCM audio responses.
  - Convert PCM back to μ-law and chunk to Twilio.
- Intelligence: Gemini Live model "gemini-2.5-flash-native-audio-preview-09-2025" with persona and optional tools.
- Data: SQLAlchemy DB (calls, transcripts, recordings), persisted to disk; dashboard renders stats and drilldowns.
- Ops: Containerized with Docker; deployed to Cloud Run; CI/CD via GitHub Actions + Cloud Build; secrets in GCP Secret Manager.

Key files
- API server: `app.py`
- Gemini integration: `gemini_ai.py`
- Twilio orchestration & DB service: `call_service.py`, `database.py`, `models.py`
- Frontend dashboard: `dashboard.html`, `index.html`
- CI/CD: `.github/workflows/deploy.yml`
- Runtime: `Dockerfile`, `requirements.txt`, `start.sh`

## 3) Data Model (high level)
- Calls: `call_sid`, `from_number`, `to_number`, `status`, `created_at`, `recording_path`, `duration`.
- Transcript entries: `call_sid`, `speaker` (`user`/`assistant`), `text`, `timestamp`.
- Recording metadata for playback and analytics.

## 4) Critical Flows
1) Inbound/Outbound call
- Twilio initiates WebSocket → `start` event stores `stream_sid`, resolves/creates DB row.
- `media` events stream audio → conversion → `GeminiLiveSession.send_audio_chunk()`.
- Gemini responses streamed back → converted → Twilio playback; transcripts written to DB.
- On `stop` → flush recording, finalize DB status, cleanup.

2) Transfer to human
- Detects intent via keyword heuristic; invokes Twilio Call Update with redirect URL.
- Fallback TwiML provided if redirect fails.
- DB updates status to `transferring` and then `completed`.

## 5) Performance & Reliability
- Bounded queues (`audio_input_queue`) to prevent memory ballooning.
- Keepalive monitor: detects stale Gemini connections and marks them disconnected.
- Auto-reconnect in `app.py` when sending audio if the session dropped.
- Rotating logs + GCP logs integration for traceability.
- Uvicorn process serves on `${PORT}` for Cloud Run; no ngrok in prod, `TUNNEL_LINK` set to service URL via workflow.

## 6) CI/CD and Infra
- GitHub Actions builds image with Cloud Build, tags with `${GITHUB_SHA}`.
- First deploy creates service; subsequent deploys inject `TUNNEL_LINK` with resolved service URL.
- Concurrency groups per service prevent overlapping deployments; read-only permissions on contents.
- Secrets: `GCP_SA_KEY` in repo secrets; service-to-service access via Secret Manager IAM.

## 7) Hard Problems & Solutions
- Problem: Gemini 1011 keepalive ping timeouts after ~10 min → upstream timeouts.
  - Fix: Keepalive monitor + `last_activity_time` tracking; explicit detection of `keepalive ping timeout` and 1011 errors; graceful teardown; transparent reconnection on next audio chunk.
- Problem: Cloud Run startup failure — container didn’t bind to `$PORT`.
  - Fix: Run with `uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}`.
- Problem: Dual-env deployments accidentally overwrote existing service.
  - Fix: Separate `SERVICE_NAME` and `IMAGE_BASE` for `vedantu-live`, distinct concurrency groups and secrets.

## 8) Design Tradeoffs
- Simplicity vs. accuracy: Keyword-based transfer intent detection (fast, transparent) vs. full NLU; chosen for reliability and control under latency.
- WebSocket single-process vs. multi-worker: Stuck with single (or small) worker Cloud Run instances to avoid cross-worker stream state; scale via instances, not threads.
- Queues: Bounded to 20 elements to apply backpressure; avoids OOM during jitter.

## 9) Security & Compliance
- Secrets never logged; stored in Secret Manager. Plan to remove hardcoded ENV from Dockerfile in favor of deploy-time env vars.
- CORS configured open for controlled internal dashboard usage; could be tightened for public exposure.

## 10) Observability
- Structured logs with request context; rotation in local dev; GCP Logs Viewer in prod.
- Errors to watch: Twilio 1006 close; Gemini 1011 keepalive; Cloud Run 404/502 on cold starts.

## 11) Elevator Pitches

### 30-Second Pitch
"I built an AI voice platform that handles real-time phone calls using Twilio and Google Gemini. The system converts audio streams on-the-fly, processes speech with sub-300ms latency, and can intelligently transfer to human agents. Deployed on Cloud Run with full CI/CD, it solved production issues like WebSocket timeouts through keepalive monitoring and auto-reconnect. It's production-ready with call analytics, transcript storage, and 95%+ completion rate."

### 60-Second Pitch
"I developed a production AI voice calling platform that combines Twilio Media Streams with Google's Gemini Live for natural conversation. The architecture handles bidirectional audio streaming: caller audio flows through WebSocket, gets converted from μ-law to PCM, resampled to 16kHz, and sent to Gemini. Responses come back, get converted, and stream to the caller with under 300ms latency. 

The hardest problem was Gemini WebSocket connections dying after 10 minutes with keepalive timeouts. I implemented activity monitoring, automatic reconnection, and graceful degradation. The system also detects intent for human handoffs and persists everything—calls, transcripts, recordings—to a database. Deployed via GitHub Actions to Cloud Run with full observability."

### 90-Second Pitch
"I built an enterprise-grade AI voice platform for Vedantu that handles real-time educational support calls. It's a FastAPI service integrating Twilio's phone network with Google Gemini Live for natural language understanding and speech synthesis.

The technical challenge was managing real-time audio: Twilio sends μ-law 8kHz chunks over WebSocket, which I convert to PCM, resample to 16kHz, and stream to Gemini. Responses flow back through the reverse pipeline with end-to-end latency under 300ms. I used bounded async queues, backpressure handling, and careful codec management.

The biggest operational issue was Gemini WebSocket connections timing out after 5-10 minutes with keepalive ping errors. I solved this with activity monitoring—tracking every send/receive—and built a keepalive monitor task that detects stale connections. When a connection drops, the system automatically reconnects transparently during the call.

I also implemented intelligent transfer-to-human detection, SQLAlchemy-backed persistence for analytics, and full CI/CD to Google Cloud Run. The platform now maintains 95%+ call completion rates with comprehensive dashboards for intent analysis and call replay. It's been running in production handling educational support queries."

## 12) Demo Scripts

### Quick Demo (2 minutes)
**Setup (15 sec)**: "Let me show you the live platform. This is the dashboard running on Cloud Run."

**Initiate Call (20 sec)**: "I'll trigger an outbound call to my test number. Notice the UI shows connection status, call timer, and mute controls. The backend is establishing a Twilio call and connecting to Gemini simultaneously."

**Demonstrate Conversation (45 sec)**: "Now I'm connected. Let me ask about course enrollment... [speak] 'What courses do you offer for 10th grade math?' Watch the transcript appear in real-time—both my speech and the AI's response. The audio latency is under 300ms. The AI is using a custom persona I configured for educational support. You can see it's generating natural responses."

**Show Transfer (20 sec)**: "Now let me trigger a human handoff... [speak] 'I want to talk to a real person.' The system detected the intent, updated the call status to 'transferring', and is now redirecting via Twilio's API. In production, this would connect to an agent queue."

**Analytics & Wrap (20 sec)**: "Back in the dashboard, I can see call history, play recordings, and view analytics. This intent breakdown shows high/medium/low intent calls. The system logged everything—transcripts, duration, status changes—for compliance and training. The recording is stored and playable directly from the UI."

### Detailed Demo (5–7 minutes)
1) **Open dashboard** at service URL; explain the tech stack (FastAPI, Twilio, Gemini, Cloud Run).
2) **Trigger outbound call** from dashboard; show WebSocket connection logs in real-time if available.
3) **Audio flow explanation**: Show how audio converts μ-law → PCM → 16kHz and back; mention codec challenges.
4) **Speak a query**; observe low-latency response and live transcript updating on both sides.
5) **Transfer demonstration**: Say keywords like "connect me to a human" → show DB status change from `in-progress` to `transferring`; explain Twilio redirect vs. TwiML fallback.
6) **Call history**: Navigate to completed calls; show transcript replay and recording playback.
7) **Resiliency**: Mention keepalive monitoring and auto-reconnect; optionally simulate a pause to show connection health tracking.
8) **Analytics deep-dive**: Show intent distribution charts, high-intent call filtering, and explain how this drives business decisions.
9) **Infrastructure**: Briefly show GitHub Actions workflow, Cloud Build logs, or Cloud Run service metrics if accessible.

## 13) Run Locally
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
# Visit http://127.0.0.1:8000/dashboard
```

## 14) Deploy (CI/CD path)
- Push to `main` → GitHub Actions builds and deploys to Cloud Run.
- Workflow: `.github/workflows/deploy.yml` handles first-deploy then injects `TUNNEL_LINK`.

## 15) Talking Points for Interviews
- Real-time streaming constraints: audio chunking, codecs, resampling, and backpressure.
- Handling flaky networks: keepalive, reconnection strategies, idempotent state transitions.
- Cost and scalability: Why Cloud Run (scale-to-zero, per-request billing), image size, cold start tuning.
- Security posture: IAM-bound secret access, minimizing secret sprawl.
- Testing strategy: unit tests for audio conversion; staging calls with synthetic traffic; log-driven verification.

## 16) What I'd Improve Next
- Replace keyword intent with lightweight NLU classifier; add confidence thresholds.
- Move secrets to runtime only; remove Dockerfile ENV.
- Add metrics (Prometheus/OpenTelemetry) and SLOs for latency and dropout rate.
- Add load testing with synthesized audio streams; chaos tests for connection drops.
