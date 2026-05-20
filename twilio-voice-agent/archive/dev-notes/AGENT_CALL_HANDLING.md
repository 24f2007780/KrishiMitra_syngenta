# Agent Call Handling System - Browser-Based Audio

## Overview

This system allows human agents to handle calls directly through the dashboard using their **browser microphone and speaker**. This is similar to how Gemini AI handles calls, but with a real human agent instead.

## How It Works

### Before (Gemini AI Handling)
```
index.html:
1. Put customer number: +919147196925
2. Click "Make Call"
3. Twilio calls +919147196925
4. Gemini AI handles conversation via Media Stream
5. Audio streamed through WebSocket
```

### After (Agent Browser-Based Handling)
```
dashboard.html:
1. Find customer call in table
2. Click phone icon (no need to input agent phone)
3. Agent's browser requests microphone permission
4. Twilio calls +919147196925
5. Agent handles conversation through browser mic/speaker
6. Audio streamed to agent's speaker, agent's mic sent to customer
```

---

## Architecture

### Three Main Components

#### 1. **Call Initiation Endpoint** (`/agent-call`)
- **Method**: POST
- **Body**: `{ "customer_phone": "+919147196925" }`
- **Returns**: `{ call_sid, status, message }`
- **Process**:
  - Creates outbound call from Twilio (+17654030113) to customer
  - Points to `/twilio/agent-voice` for handling
  - Logs call to database with status="in-progress"

#### 2. **Twilio Webhook** (`/twilio/agent-voice`)
- **Method**: POST (from Twilio)
- **Receives**: CallSid, From, To
- **Responds**: TwiML that connects to WebSocket
- **Process**:
  - Customer answers → Twilio calls webhook
  - Webhook returns TwiML pointing to `/ws/agent-call`
  - Customer's audio streams to WebSocket

#### 3. **Agent WebSocket Handler** (`/ws/agent-call`)
- **Protocol**: WebSocket
- **Bidirectional Audio**:
  - **Incoming**: Customer audio → Agent's browser speaker
  - **Outgoing**: Agent's microphone → Customer
- **Process**:
  - Accepts WebSocket connection from agent's browser
  - Receives Twilio media events (customer audio)
  - Receives agent audio from browser
  - Routes audio bidirectionally

---

## Browser-Side Implementation

### 1. Request Microphone Permission

```javascript
const stream = await navigator.mediaDevices.getUserMedia({ 
    audio: true 
});
window.agentAudioStream = stream;
```

### 2. Initiate Call

```javascript
const response = await fetch('/agent-call', {
    method: 'POST',
    body: JSON.stringify({
        customer_phone: "+919147196925"
    })
});
```

### 3. Connect WebSocket

```javascript
const wsUrl = 'wss://...../ws/agent-call';
window.agentWebSocket = new WebSocket(wsUrl);
```

### 4. Send Agent's Mic Audio

```javascript
const audioContext = new AudioContext();
const source = audioContext.createMediaStreamSource(window.agentAudioStream);
const processor = audioContext.createScriptProcessor(4096, 1, 1);

processor.onaudioprocess = (event) => {
    const audioData = event.inputBuffer.getChannelData(0);
    // Convert to mulaw and send via WebSocket
    window.agentWebSocket.send(JSON.stringify({
        event: 'media',
        media: { payload: btoa(...) }
    }));
};
```

### 5. Receive Customer's Audio

```javascript
window.agentWebSocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.event === 'media') {
        // Customer audio
        const audioData = atob(data.media.payload);
        // Decode mulaw and play to agent's speaker
        playAudioToSpeaker(audioData);
    }
};
```

---

## Step-by-Step Flow

```
┌─────────────────────────────────────────────────────┐
│ Agent sees customer call in dashboard               │
│ Clicks phone icon on customer row                   │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│ Browser asks: "Allow microphone access?"            │
│ Agent clicks: Allow                                 │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│ Dashboard shows call modal:                         │
│ - Phone number                                      │
│ - Timer (00:00)                                     │
│ - Status: "Initiating call..."                      │
│ - Mute, Disconnect, Keypad buttons                  │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│ POST /agent-call with customer phone                │
│ ↓                                                   │
│ Backend creates Twilio call                         │
│ from +17654030113 to customer phone                 │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│ Customer's phone rings                              │
│ Modal status: "Waiting for customer to answer..."   │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│ Customer answers phone                              │
│ ↓                                                   │
│ Twilio calls /twilio/agent-voice webhook            │
│ ↓                                                   │
│ Webhook returns TwiML pointing to /ws/agent-call    │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│ Agent's browser connects WebSocket                  │
│ ↓                                                   │
│ Dashboard initiates audio streaming                 │
│ ↓                                                   │
│ Agent's mic audio → sent to customer                │
│ Customer's audio → played in agent's speaker        │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│ Modal status: "Connected - Listening..."            │
│ Timer starts counting                               │
│ Agent and customer can now talk                     │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│ Agent controls call:                                │
│ - Can mute mic (🔊 → 🔇)                            │
│ - Can disconnect (red ☎ button)                     │
│ - Can press keypad (⌨) for DTMF                     │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│ Agent clicks disconnect button                      │
│ ↓                                                   │
│ WebSocket closes                                    │
│ Audio stream stops                                  │
│ Call logged as "completed"                          │
│ Modal closes                                        │
└─────────────────────────────────────────────────────┘
```

---

## API Endpoints

### 1. POST `/agent-call`
**Initiate call for agent handling**

Request:
```json
{
    "customer_phone": "+919147196925"
}
```

Response:
```json
{
    "success": true,
    "call_sid": "CA1234567890abcdef",
    "status": "queued",
    "customer_phone": "+919147196925",
    "twilio_number": "+17654030113",
    "message": "Call initiated to +919147196925. Connect agent browser session."
}
```

### 2. POST `/twilio/agent-voice`
**Webhook from Twilio (automatic)**

Receives:
- CallSid
- From (customer number)
- To (Twilio number)

Returns: TwiML with WebSocket redirect

### 3. WebSocket `/ws/agent-call`
**Bidirectional audio stream**

Messages from Twilio:
```json
{
    "event": "start",
    "start": {
        "streamSid": "MZ123...",
        "callSid": "CA123..."
    }
}
```

```json
{
    "event": "media",
    "media": {
        "payload": "base64encodedmulawaudio"
    }
}
```

Messages from Agent:
```json
{
    "event": "media",
    "media": {
        "payload": "base64encodedagentaudio"
    }
}
```

---

## Call Modal Features

### Display Information
- **Phone Number**: Shows customer phone in large text (32px)
- **Timer**: Real-time call duration (MM:SS format)
- **Status**: Current state ("Initiating call...", "Connected...", etc.)

### Control Buttons

| Button | Icon | Function |
|--------|------|----------|
| Mute | 🔊/🔇 | Toggle microphone on/off |
| Disconnect | ☎ (Red) | End call and close modal |
| Keypad | ⌨ | Send DTMF digits (future) |

### Styling
- Beautiful purple gradient background
- Professional layout
- Hover effects on buttons
- Real-time timer updates
- Responsive design

---

## Database Logging

Each call is logged to `calls.db` with:

```
Call Record:
├── call_sid: "CA1234567890abcdef"
├── direction: "outbound"
├── from_number: "+17654030113"
├── to_number: "+919147196925"
├── status: "in-progress" → "completed"
├── duration: (calculated on close)
├── created_at: timestamp
├── intent_score: (analyzed from transcript)
├── intent_category: "high/medium/low"
└── transcript: (stored as JSON)
```

---

## Browser Permissions Required

1. **Microphone**: Required for agent to be heard
   - User is prompted with: "Allow microphone access?"
   - Must click "Allow" to proceed

2. **Audio Context**: For audio processing
   - Automatically created when needed
   - Used for mixing agent mic audio with Twilio audio

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Allow microphone access" | Browser mic not permitted | Click "Allow" in browser prompt |
| "Connection error: ..." | WebSocket failed | Check TUNNEL_LINK configuration |
| "Phone number not verified" | Twilio trial account | Verify number in Twilio console |
| "Invalid phone number" | Wrong format | Use E.164 format: +1234567890 |

### Error Flow
```
Error Occurs
    ↓
Timer stops
    ↓
WebSocket closes
    ↓
Audio stream stops
    ↓
Modal closes
    ↓
Alert shown to agent
    ↓
Calls list refreshes
```

---

## Configuration

### Key Variables

**app.py:**
```python
PHONE_NO = os.getenv("TWILIO_PHONE_NO")  # Your Twilio number
TUNNEL_LINK = "https://abc123.ngrok.io"  # Public URL
```

**dashboard.html:**
```javascript
const API_BASE = "http://127.0.0.1:8000"  // Backend URL
```

### Ngrok Setup
```bash
ngrok http 8000
# Gives you: https://abc123.ngrok.io
# Update TUNNEL_LINK in app.py
```

---

## Testing

### Manual Test Steps

1. **Start server**
   ```bash
   python app.py
   ```

2. **Open dashboard**
   ```
   http://localhost:8000/dashboard
   ```

3. **Make a test call** (or wait for inbound)
   - You should see call in "Recent Calls" table
   - Click phone icon on any outbound call to customer

4. **Allow microphone**
   - Browser will ask for permission
   - Click "Allow"

5. **Call modal appears**
   - Shows customer number
   - Timer starts at 00:00
   - Status shows "Initiating call..."

6. **Customer receives call**
   - Call comes from +17654030113
   - Can answer normally

7. **Agent hears customer**
   - Audio plays in agent's speaker
   - Agent can speak through mic
   - Customer hears agent

8. **End call**
   - Agent clicks red disconnect button
   - Call logs as completed
   - Modal closes
   - Calls list refreshes

---

## Comparison: Gemini vs Agent Handling

| Feature | Gemini AI | Agent Browser |
|---------|-----------|---------------|
| Entry point | index.html | dashboard.html |
| Audio source | Gemini AI API | Browser microphone |
| Backend URL | `/twilio/voice` | `/twilio/agent-voice` |
| WebSocket | `/ws/call` | `/ws/agent-call` |
| Agent input | Put phone, click button | Click phone icon |
| Conversation | AI-driven | Human-driven |
| Call control | Gemini controls | Agent controls |
| Mute option | No | Yes (🔊/🔇) |
| Recording | Saved to file | Call metadata |
| Intent analysis | Automatic | Post-call (optional) |

---

## Future Enhancements

1. **Call Transfer**: Agent can transfer to another agent
2. **Call Recording**: Automatic recording with download
3. **Call Notes**: Agent can add notes during call
4. **Screen Sharing**: Agent can share screen with customer
5. **Chat**: Parallel text chat alongside voice
6. **Call Queue**: Show waiting customers in order
7. **Callback Requests**: Customer can request callback
8. **Call Analytics**: Track agent performance

---

## Troubleshooting

### Microphone not working
- Check browser permissions (Settings → Privacy → Microphone)
- Try different browser (Chrome, Firefox, Edge)
- Test microphone in system settings

### No audio from customer
- Check Twilio account status
- Verify phone numbers are correct
- Check ngrok tunnel is active
- Review WebSocket connection in browser console

### Call doesn't initiate
- Check backend server is running
- Verify API_BASE URL is correct
- Check browser console for errors
- Review server logs: `tail -f logs/app.log`

### WebSocket connection fails
- Check TUNNEL_LINK in app.py matches ngrok URL
- Check WSS (secure WebSocket) URL is correct
- Try clearing browser cache and reloading

---

## File Changes Summary

### Backend (`app.py`)
- Added `AgentCallRequest` model
- Added `/agent-call` endpoint (initiate call)
- Added `/twilio/agent-voice` endpoint (webhook)
- Added `/ws/agent-call` WebSocket handler
- Added `agent_call_sessions` dictionary
- Imported `datetime` for session tracking

### Frontend (`dashboard.html`)
- Updated `initiateCallback()` function → `initiateAgentCall()`
- Added `connectAgentWebSocket()` for WebSocket setup
- Added `sendAgentAudio()` for mic audio streaming
- Updated `endCall()` to close WebSocket and audio
- Added `toggleMute()` function
- Updated mute button onclick to call `toggleMute()`
- Removed agent phone input (no longer needed)
- Removed "Agent Phone" field from filters

---

## Summary

The **Agent Browser-Based Call Handling System** allows human agents to:

1. ✓ View customer calls in dashboard
2. ✓ Click phone icon to initiate call
3. ✓ Use browser microphone and speaker
4. ✓ Control call (mute, disconnect)
5. ✓ Handle real conversations with customers
6. ✓ All through dashboard interface

This replaces the previous "callback with agent phone" system with a more seamless, browser-native experience.
