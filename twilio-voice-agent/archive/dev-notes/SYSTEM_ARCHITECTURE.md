# System Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                    VEDANTU AI VOICE PLATFORM v2.0                          │
│                                                                             │
│  ┌──────────────────────┐            ┌──────────────────────────────────┐  │
│  │   index.html         │            │     dashboard.html               │  │
│  │                      │            │                                  │  │
│  │  Make AI Calls       │            │   Agent Call Handling            │  │
│  │                      │            │                                  │  │
│  │ Input: Phone number  │            │ Input: Click phone icon          │  │
│  │ Handler: Gemini AI   │            │ Handler: Agent's browser         │  │
│  │ WebSocket: /ws/call  │            │ WebSocket: /ws/agent-call        │  │
│  │                      │            │                                  │  │
│  │ /make-call ──────────┼────┐       │ /agent-call ──────────┐          │  │
│  └──────────────────────┘    │       └──────────────────────┼──────────┘  │
│                              │                              │              │
└──────────────────────────────┼──────────────────────────────┼──────────────┘
                               │                              │
                    ┌──────────▼──────────┐                  │
                    │                     │                  │
                    │   FastAPI Backend   │                  │
                    │   (app.py)          │                  │
                    │                     │                  │
                    └──────────┬──────────┘                  │
                               │                              │
               ┌───────────────┼───────────────┐              │
               │               │               │              │
        ┌──────▼──────┐  ┌─────▼────────┐  ┌──▼──────────────▼──────┐
        │ /twilio/    │  │ /twilio/     │  │ /twilio/agent-voice    │
        │ voice       │  │ continue     │  │                        │
        │ (Gemini)    │  │              │  │ (Agent webhook)        │
        └──────┬──────┘  └─────┬────────┘  └──┬───────────────┬─────┘
               │                │             │               │
        ┌──────▼──────┐  ┌─────▼────────┐  ┌──▼──┐        ┌──▼──────────────┐
        │ /ws/call    │  │ Media Stream │  │Call │        │ /ws/agent-call  │
        │ (Gemini)    │  │ Processing   │  │Log  │        │ (Agent Audio)   │
        └──────┬──────┘  └─────┬────────┘  └──┬──┘        └──┬──────────────┘
               │                │             │               │
               └────────────────┼─────────────┼───────────────┘
                                │             │
                    ┌───────────▼─────────────▼───────┐
                    │                                 │
                    │    SQLite Database              │
                    │    (calls.db)                   │
                    │                                 │
                    │  ├─ call_sid                    │
                    │  ├─ direction                   │
                    │  ├─ from_number                 │
                    │  ├─ to_number                   │
                    │  ├─ status                      │
                    │  ├─ duration                    │
                    │  ├─ intent_score                │
                    │  └─ transcript                  │
                    │                                 │
                    └─────────────────────────────────┘
```

---

## Call Flow: Gemini AI vs Agent

### Gemini AI Call Flow

```
                    Index.html
                        │
                        │ Input: +919147196925
                        ↓
                    /make-call (POST)
                        │
                        ↓
                Twilio Outbound Call
                from: +17654030113
                to:   +919147196925
                        │
                        ↓
                    Customer answers
                        │
                        ↓
            /twilio/voice (Webhook)
                        │
                        ↓
            TwiML → Redirect to /ws/call
                        │
                        ↓
            /ws/call (WebSocket)
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ↓               ↓               ↓
    Gemini AI      Audio Stream    Database
     API                            Update
     │
    (AI processes
     customer voice,
     generates response)
     │
        ↓
    TwiML Response
     │
    Say/Dial
     │
        ↓
  Customer hears
   AI response
```

### Agent Browser Call Flow

```
                   Dashboard.html
                        │
                        │ Click phone icon
                        ↓
                   Request Microphone
                   "Allow access?"
                        │
                        ↓
                   /agent-call (POST)
                        │
                        ↓
                Twilio Outbound Call
                from: +17654030113
                to:   +919147196925
                        │
                        ↓
                    Customer answers
                        │
                        ↓
            /twilio/agent-voice (Webhook)
                        │
                        ↓
        TwiML → Redirect to /ws/agent-call
                        │
                        ↓
            /ws/agent-call (WebSocket)
                        │
        ┌───────────────┼────────────────┐
        │               │                │
        ↓               ↓                ↓
    Agent's        Audio Stream    Database
    Browser                        Update
    (Mic/Speaker)  
    │              
   (Agent speaks/
    listens via
    browser)
    │
        ↓
    WebSocket sends
    agent's audio
     │
        ↓
  Customer hears
   agent's voice
```

---

## Technical Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          FRONTEND LAYER                              │
│                                                                      │
│  ┌─────────────────┐              ┌────────────────────────────┐   │
│  │  index.html     │              │ dashboard.html             │   │
│  │                 │              │                            │   │
│  │ • Phone input   │              │ • Call table               │   │
│  │ • Make call btn │              │ • Phone icons (📞)         │   │
│  │ • Status msg    │              │ • Call modal               │   │
│  │                 │              │ • Timer                    │   │
│  │                 │              │ • Mute button              │   │
│  └─────────────────┘              │ • Disconnect button        │   │
│                                    │ • Analytics                │   │
│                                    └────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ↓               ↓               ↓
                 HTTP            HTTP           WebSocket
                (GET/POST)      (GET/POST)      (Persistent)
                    │               │               │
└──────────────────────────────────────────────────────────────────────┘
│                          API LAYER (FastAPI)                         │
│                                                                      │
│  ┌─────────────────────┐  ┌───────────────┐  ┌──────────────────┐ │
│  │  RESTful Endpoints  │  │   Webhooks    │  │ WebSocket        │ │
│  │                     │  │               │  │ Handlers         │ │
│  │ GET  /              │  │ /twilio/voice │  │                  │ │
│  │ GET  /dashboard     │  │ /twilio/cont. │  │ /ws/call         │ │
│  │ POST /make-call     │  │ /twilio/agent │  │ /ws/agent-call   │ │
│  │ POST /agent-call    │  │               │  │                  │ │
│  │ GET  /api/v1/calls  │  │               │  │ Features:        │ │
│  │ POST /api/v1/...    │  │               │  │ • Real-time      │ │
│  │                     │  │               │  │ • Bidirectional  │ │
│  │ Error Handling      │  │ Status Updates│  │ • Audio stream   │ │
│  │ & Validation        │  │ & Logging     │  │ • Event handling │ │
│  └─────────────────────┘  └───────────────┘  └──────────────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ↓               ↓               ↓
              Database         Twilio API       Gemini API
              (SQLite)         (Voice)          (Audio)
                    │               │               │
┌──────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SERVICES                             │
│                                                                      │
│  ┌────────────────────┐ ┌──────────────────┐ ┌──────────────────┐  │
│  │  Database Layer    │ │  Twilio Voice    │ │  Gemini Live API │  │
│  │  (SQLite)          │ │  API             │ │                  │  │
│  │                    │ │                  │ │ • Audio input    │  │
│  │ • call records     │ │ • Initiate calls │ │ • AI processing  │  │
│  │ • call history     │ │ • Media streams  │ │ • Audio output   │  │
│  │ • transcripts      │ │ • Webhooks       │ │ • Real-time      │  │
│  │ • analytics        │ │ • Status updates │ │                  │  │
│  │                    │ │ • Phone numbers  │ │                  │  │
│  │ Connection:        │ │                  │ │ Connection:      │  │
│  │ from_=+17654030113 │ │ TUNNEL_LINK +    │ │ WebSocket via    │  │
│  │                    │ │ ngrok            │ │ /ws/call         │  │
│  └────────────────────┘ └──────────────────┘ └──────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     AGENT CALL FLOW                             │
└─────────────────────────────────────────────────────────────────┘

Dashboard (Browser)
    │
    │ Step 1: Click phone icon
    │ Event: initiateCallback('phone_number', event)
    ↓
Browser JavaScript
    │
    │ Step 2: Request microphone permission
    │ navigator.mediaDevices.getUserMedia({ audio: true })
    ↓
User System
    │
    │ Step 3: User clicks "Allow"
    │ window.agentAudioStream = stream
    ↓
Browser JavaScript
    │
    │ Step 4: POST /agent-call
    │ Body: { customer_phone: "+919147196925" }
    ↓
FastAPI Backend
    │
    │ Step 5: Create Twilio outbound call
    │ twilio_client.calls.create(
    │     to=customer_phone,
    │     from_=PHONE_NO,
    │     url=TUNNEL_LINK/twilio/agent-voice
    │ )
    ↓
Twilio Service
    │
    │ Step 6: Call customer phone
    │ from: +17654030113
    │ to:   +919147196925
    │ (Phone rings...)
    ↓
Customer
    │
    │ Step 7: Customer answers phone
    │
    ↓
Twilio Service
    │
    │ Step 8: Call webhook /twilio/agent-voice
    │ Send: CallSid, From, To
    ↓
FastAPI Webhook
    │
    │ Step 9: Return TwiML with WebSocket URL
    │ <Connect><Stream url="wss://.../ws/agent-call"/></Connect>
    ↓
Twilio Service
    │
    │ Step 10: Connect media stream to WebSocket
    │
    ↓
Browser JavaScript
    │
    │ Step 11: Open WebSocket connection
    │ new WebSocket('wss://.../ws/agent-call')
    ↓
FastAPI WebSocket Handler
    │
    │ Step 12: Accept connection
    │ await ws.accept()
    ↓
┌──────────────────────────────────────────────────────────────┐
│          BIDIRECTIONAL AUDIO STREAMING (REAL-TIME)           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Twilio → Websocket                                          │
│  Customer's voice → Mulaw encoded → base64 → JSON →          │
│  Browser receives → Decode mulaw → PCM → AudioContext →      │
│  Agent's speaker plays customer's voice                      │
│                                                              │
│  Agent's Browser → WebSocket                                 │
│  Microphone audio → AudioContext processor → PCM →           │
│  Encode mulaw → base64 → JSON → WebSocket →                  │
│  Twilio receives → Customer hears agent's voice              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
    │
    │ Steps 13-15: Real-time conversation
    │ Agent speaks/listens while timer counts
    │ Call information logged to database
    │
    ↓
Agent clicks disconnect button
    │
    │ Step 16: endCall()
    │ • Clear timer
    │ • Close WebSocket
    │ • Stop audio stream
    │ • Log completion
    │
    ↓
FastAPI WebSocket Handler
    │
    │ Step 17: Receive 'stop' event
    │ • Update database status="completed"
    │ • Clean up session
    │ • Calculate duration
    │
    ↓
Dashboard
    │
    │ Step 18: Modal closes
    │ Calls list refreshes
    │
    ↓
Call Completed ✓
```

---

## Component Interaction Matrix

```
┌──────────────────┬──────────┬────────────┬─────────────┬──────────┐
│ Component        │ Method   │ Endpoint   │ Data Flow   │ Handler  │
├──────────────────┼──────────┼────────────┼─────────────┼──────────┤
│ Dashboard        │ Click    │ JavaScript │ client-side │ function │
│ (index.html)     │ input    │ event      │ event       │ click    │
├──────────────────┼──────────┼────────────┼─────────────┼──────────┤
│ Microphone       │ Device   │ getUserMd. │ stream obj  │ browser  │
│ Permission       │ request  │ API        │ handle      │ prompt   │
├──────────────────┼──────────┼────────────┼─────────────┼──────────┤
│ HTTP Client      │ POST     │ /agent-call│ JSON        │ fetch()  │
│ (JavaScript)     │ request  │            │ body        │          │
├──────────────────┼──────────┼────────────┼─────────────┼──────────┤
│ FastAPI Endpoint │ Handle   │ /agent-call│ JSON data   │ async    │
│ (/agent-call)    │ request  │ POST       │ validation  │ function │
├──────────────────┼──────────┼────────────┼─────────────┼──────────┤
│ Twilio API       │ Create   │ REST API   │ call config │ API call │
│ (outbound call)  │ call     │ call       │ parameters  │          │
├──────────────────┼──────────┼────────────┼─────────────┼──────────┤
│ Twilio Webhook   │ POST     │ /twilio/   │ CallSid,    │ HTTP     │
│ (customer answers)│ callback │ agent-voice│ From, To    │ request  │
├──────────────────┼──────────┼────────────┼─────────────┼──────────┤
│ WebSocket        │ Connect  │ /ws/       │ stream info │ async    │
│ Handshake        │ upgrade  │ agent-call │ exchange    │ protocol │
├──────────────────┼──────────┼────────────┼─────────────┼──────────┤
│ Audio Context    │ Process  │ JavaScript │ PCM samples │ callback │
│ (Browser)        │ stream   │ Web API    │ per frame   │ function │
├──────────────────┼──────────┼────────────┼─────────────┼──────────┤
│ WebSocket        │ Send     │ /ws/       │ JSON media  │ client   │
│ (Agent to Twilio)│ message  │ agent-call │ payload     │ method   │
├──────────────────┼──────────┼────────────┼─────────────┼──────────┤
│ Database         │ INSERT   │ SQLAlchemy │ call record │ ORM      │
│ Logging          │ UPDATE   │ session    │ parameters  │ method   │
├──────────────────┼──────────┼────────────┼─────────────┼──────────┤
│ Call Status      │ State    │ WebSocket  │ text event  │ event    │
│ Updates          │ machine  │ message    │ data        │ handler  │
└──────────────────┴──────────┴────────────┴─────────────┴──────────┘
```

---

## Deployment Architecture

```
┌────────────────────────────────────────────────────────────────┐
│              DEPLOYMENT & NETWORKING                           │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Local Machine                                                 │
│  ┌──────────────────────────────────────┐                     │
│  │ Python App                           │                     │
│  │ (FastAPI + Uvicorn)                  │                     │
│  │                                      │                     │
│  │ localhost:8000 ◄────────────────────►│ Browser             │
│  │ • HTTP requests (GET/POST)           │ • Dashboard.html    │
│  │ • WebSocket upgrade (wss://)         │ • Call modal        │
│  │ • Serve static files (HTML/CSS/JS)   │ • Audio controls    │
│  │                                      │                     │
│  │ Database                             │                     │
│  │ • SQLite (calls.db)                  │                     │
│  │ • Local file storage                 │                     │
│  │                                      │                     │
│  │ Audio Processing                     │                     │
│  │ • WebSocket handlers                 │                     │
│  │ • Mulaw encoding/decoding            │                     │
│  │                                      │                     │
│  └──────────────────────────────────────┘                     │
│                 │                                              │
│           ngrok tunnel                                         │
│     (Public internet bridge)                                   │
│                 │                                              │
│  Example: https://abc123.ngrok.io                             │
│                 │                                              │
│         ┌───────┴─────────┐                                   │
│         │                 │                                   │
│         ↓                 ↓                                   │
│    ┌─────────────┐   ┌──────────────┐                        │
│    │ Twilio API  │   │ Gemini API   │                        │
│    │ (Voice)     │   │ (AI Audio)   │                        │
│    │             │   │              │                        │
│    │ • Create    │   │ • Process    │                        │
│    │   calls     │   │   audio      │                        │
│    │ • Webhooks  │   │ • Real-time  │                        │
│    │ • Media     │   │   response   │                        │
│    │   streams   │   │              │                        │
│    └─────────────┘   └──────────────┘                        │
│         │                                                     │
│    ┌────┴──────────────────────────┐                         │
│    │                               │                         │
│    ↓                               ↓                         │
│  ┌──────────────────┐      ┌──────────────────┐             │
│  │  Telecom        │      │ Cloud Services   │             │
│  │  Network        │      │                  │             │
│  │                 │      │ • Google Cloud   │             │
│  │ • Call routing  │      │ • Gemini LLM     │             │
│  │ • PSTN numbers  │      │ • Voice API      │             │
│  │ • Voip quality  │      │                  │             │
│  └─────────┬──────┘      └──────────────────┘             │
│            │                                              │
│            ↓                                              │
│  ┌──────────────────────────────┐                        │
│  │  Customer's Phone            │                        │
│  │  (Any telecom provider)      │                        │
│  │                              │                        │
│  │  Receives call from          │                        │
│  │  +17654030113                │                        │
│  │                              │                        │
│  │  Can be:                     │                        │
│  │  • Mobile phone              │                        │
│  │  • Landline                  │                        │
│  │  • VoIP phone                │                        │
│  │  • App (Twilio SDK)          │                        │
│  └──────────────────────────────┘                        │
│                                                           │
└────────────────────────────────────────────────────────────┘
```

---

## Configuration Flow

```
Environment Variables (`.env`)
│
├─ TWILIO_ACCOUNT_SID
├─ TWILIO_AUTH_TOKEN
├─ TWILIO_PHONE_NO = "+17654030113"
└─ GOOGLE_API_KEY
│
↓
app.py (FastAPI application)
│
├─ Initialize Twilio Client
│  └─ client = Client(account_sid, auth_token)
│
├─ Set PHONE_NO variable
│  └─ PHONE_NO = os.getenv("TWILIO_PHONE_NO")
│
├─ Set TUNNEL_LINK (ngrok URL)
│  └─ Required for webhooks/WebSocket
│
└─ Create FastAPI routes
   ├─ POST /agent-call
   ├─ POST /twilio/agent-voice
   └─ WebSocket /ws/agent-call
│
↓
Dashboard (browser)
│
├─ Set API_BASE
│  └─ API_BASE = "http://127.0.0.1:8000"
│
├─ Load call data
│  └─ GET /api/v1/calls
│
└─ Handle agent calls
   ├─ initiateCallback() → POST /agent-call
   ├─ connectAgentWebSocket() → WebSocket /ws/agent-call
   └─ sendAgentAudio() → Stream microphone audio
```

---

This architecture ensures:
- ✅ Real-time bidirectional communication
- ✅ Professional call handling experience
- ✅ Secure WebSocket connections
- ✅ Database persistence
- ✅ Scalable design
- ✅ Backward compatible with existing systems
