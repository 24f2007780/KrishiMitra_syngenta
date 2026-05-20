# Twilio Call API Documentation

## Base URL
- Local: `http://localhost:8000`
- Ngrok: `https://9f77ea856b0f.ngrok-free.app`

---

## Endpoints

### 1. Web Interface
**GET /** 
- Returns the HTML interface for making calls
- Access in browser: `http://localhost:8000`

---

### 2. Make Call (Web UI Endpoint)
**POST /make-call**

Initiates a call to a phone number (used by web interface).

**Request Body:**
```json
{
  "to_number": "+1234567890"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "call_sid": "CA123...",
  "status": "queued",
  "message": "Call initiated to +1234567890"
}
```

**Error Response (400/403/422):**
```json
{
  "success": false,
  "error": "The number +919471961925 is not verified. Please verify it in your Twilio console first.",
  "error_code": "TWILIO_ERROR"
}
```

---

### 3. Request Callback (RESTful API)
**POST /api/v1/callback**

RESTful API endpoint to request a callback. This will call the provided phone number.

**Request Body:**
```json
{
  "to_number": "+919943193399"
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "call_sid": "CA0bde33b9e33eba5ac9905c9950a4d557",
  "status": "queued",
  "to_number": "+919943193399",
  "from_number": "+17654030113",
  "message": "Callback request accepted and processing"
}
```

**Error Responses:**

**403 Forbidden (Unverified Number):**
```json
{
  "success": false,
  "error": "The number +919471961925 is not verified. Trial accounts can only call verified numbers.",
  "error_code": "CALLBACK_FAILED",
  "to_number": "+919471961925"
}
```

**422 Unprocessable Entity (Invalid Format):**
```json
{
  "success": false,
  "error": "Invalid phone number format. Use E.164 format (e.g., +1234567890).",
  "error_code": "CALLBACK_FAILED",
  "to_number": "1234567890"
}
```

---

### 4. List Calls
**GET /api/v1/calls**

Get a list of all calls with optional filters.

**Query Parameters:**
- `skip` (optional): Number of records to skip for pagination (default: 0)
- `limit` (optional): Maximum number of records to return (default: 100)
- `direction` (optional): Filter by direction (`inbound` or `outbound`)
- `status` (optional): Filter by status (`queued`, `ringing`, `in-progress`, `completed`, `failed`)

**Example:**
```bash
GET /api/v1/calls?direction=inbound&limit=10
```

**Success Response (200):**
```json
{
  "success": true,
  "count": 2,
  "calls": [
    {
      "id": 1,
      "call_sid": "CA0bde33b9e33eba5ac9905c9950a4d557",
      "stream_sid": "MZ1f7cb6ada1b61368fd2e13545231986d",
      "direction": "outbound",
      "from_number": "+17654030113",
      "to_number": "+919943193399",
      "status": "completed",
      "created_at": "2026-01-06T07:43:57.702000",
      "started_at": "2026-01-06T07:44:19.930000",
      "ended_at": "2026-01-06T07:45:30.123000",
      "duration": 70.193,
      "recording_path": "recordings/CA0bde33b9e33eba5ac9905c9950a4d557_20260106_074430.wav",
      "recording_duration": 70.15,
      "caller_name": null,
      "notes": null,
      "error_message": null
    }
  ]
}
```

---

### 5. Get Call Details
**GET /api/v1/calls/{call_sid}**

Get detailed information about a specific call.

**Success Response (200):**
```json
{
  "success": true,
  "call": {
    "id": 1,
    "call_sid": "CA0bde33b9e33eba5ac9905c9950a4d557",
    "stream_sid": "MZ1f7cb6ada1b61368fd2e13545231986d",
    "direction": "outbound",
    "from_number": "+17654030113",
    "to_number": "+919943193399",
    "status": "completed",
    "created_at": "2026-01-06T07:43:57.702000",
    "started_at": "2026-01-06T07:44:19.930000",
    "ended_at": "2026-01-06T07:45:30.123000",
    "duration": 70.193,
    "recording_path": "recordings/CA0bde33b9e33eba5ac9905c9950a4d557_20260106_074430.wav",
    "recording_duration": 70.15,
    "caller_name": null,
    "notes": null,
    "error_message": null
  }
}
```

**Error Response (404):**
```json
{
  "success": false,
  "error": "Call not found"
}
```

---

### 6. Get Call Statistics
**GET /api/v1/calls/stats**

Get overall call statistics.

**Success Response (200):**
```json
{
  "success": true,
  "stats": {
    "total_calls": 45,
    "inbound_calls": 23,
    "outbound_calls": 22,
    "completed_calls": 40
  }
}
```

---

### 7. Download Call Recording
**GET /api/v1/recordings/{call_sid}**

Download the audio recording of a call.

**Success Response (200):**
- Returns WAV audio file
- Content-Type: `audio/wav`
- Filename: `{call_sid}.wav`

**Error Response (404):**
```json
{
  "success": false,
  "error": "Recording not found"
}
```

or

```json
{
  "success": false,
  "error": "Recording file not found on disk"
}
```

---

## Usage Examples

### cURL
```bash
# Request callback
curl -X POST http://localhost:8000/api/v1/callback \
  -H "Content-Type: application/json" \
  -d '{"to_number": "+919943193399"}'

# List all calls
curl http://localhost:8000/api/v1/calls

# List inbound calls only
curl "http://localhost:8000/api/v1/calls?direction=inbound&limit=20"

# Get specific call details
curl http://localhost:8000/api/v1/calls/CA0bde33b9e33eba5ac9905c9950a4d557

# Get call statistics
curl http://localhost:8000/api/v1/calls/stats

# Download call recording
curl http://localhost:8000/api/v1/recordings/CA0bde33b9e33eba5ac9905c9950a4d557 \
  --output recording.wav
```

### Python
```python
import requests

# Request callback
response = requests.post(
    "http://localhost:8000/api/v1/callback",
    json={"to_number": "+919943193399"}
)
print(response.json())

# List all calls
calls = requests.get("http://localhost:8000/api/v1/calls")
print(calls.json())

# List completed outbound calls
calls = requests.get(
    "http://localhost:8000/api/v1/calls",
    params={"direction": "outbound", "status": "completed", "limit": 10}
)
print(calls.json())

# Get specific call
call = requests.get("http://localhost:8000/api/v1/calls/CA0bde...")
print(call.json())

# Get statistics
stats = requests.get("http://localhost:8000/api/v1/calls/stats")
print(stats.json())

# Download recording
recording = requests.get("http://localhost:8000/api/v1/recordings/CA0bde...")
with open("recording.wav", "wb") as f:
    f.write(recording.content)
```

### JavaScript/Fetch
```javascript
// Request callback
fetch('http://localhost:8000/api/v1/callback', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    to_number: '+919943193399'
  })
})
.then(response => response.json())
.then(data => console.log(data));

// List all calls
fetch('http://localhost:8000/api/v1/calls')
  .then(response => response.json())
  .then(data => console.log(data));

// List inbound calls with filters
fetch('http://localhost:8000/api/v1/calls?direction=inbound&limit=20')
  .then(response => response.json())
  .then(data => console.log(data));

// Get specific call
fetch('http://localhost:8000/api/v1/calls/CA0bde33b9e33eba5ac9905c9950a4d557')
  .then(response => response.json())
  .then(data => console.log(data));

// Get statistics
fetch('http://localhost:8000/api/v1/calls/stats')
  .then(response => response.json())
  .then(data => console.log(data));

// Download recording
fetch('http://localhost:8000/api/v1/recordings/CA0bde33b9e33eba5ac9905c9950a4d557')
  .then(response => response.blob())
  .then(blob => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'recording.wav';
    a.click();
  });
```

---

## Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `TWILIO_ERROR` | 400 | General Twilio API error |
| `CALLBACK_FAILED` | 400/403/422 | Callback request failed |

---

## Common Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| "The number X is not verified" | Trial account limitation | Verify the number in Twilio console |
| "Invalid phone number format" | Wrong format | Use E.164 format: +[country][number] |
| "Invalid Twilio phone number configuration" | Server config issue | Check .env file settings |
| "This phone number cannot receive calls" | Number doesn't support voice | Use a different number |

---

## Phone Number Format (E.164)

Always use E.164 format for phone numbers:
- ✅ `+919943193399` (India)
- ✅ `+17654030113` (USA)
- ✅ `+442071234567` (UK)
- ❌ `9943193399` (Missing country code)
- ❌ `+91 99431 93399` (Has spaces)

---

## Rate Limits

Twilio trial accounts have limitations:
- Can only call verified numbers
- Limited free credits
- No SMS to unverified numbers

Upgrade to a paid account to remove these restrictions.

---

## Database & Recordings

### Database
The application uses SQLite with SQLAlchemy ORM to store call records.

**Location:** `data/calls.db`

**Schema:**
- `id`: Auto-incrementing primary key
- `call_sid`: Twilio call SID (unique, indexed)
- `stream_sid`: Twilio media stream SID
- `direction`: `inbound` or `outbound`
- `from_number`: Caller phone number
- `to_number`: Recipient phone number
- `status`: `queued`, `ringing`, `in-progress`, `completed`, `failed`, `no-answer`
- `created_at`: Timestamp when call was created
- `started_at`: Timestamp when call actually connected
- `ended_at`: Timestamp when call ended
- `duration`: Call duration in seconds
- `recording_path`: Path to the WAV recording file
- `recording_duration`: Recording duration in seconds
- `caller_name`: Optional caller name
- `notes`: Optional notes
- `error_message`: Error message if call failed

### Call Recordings
All calls are automatically recorded and saved as WAV files.

**Location:** `recordings/`

**Format:**
- File format: WAV (PCM)
- Sample rate: 8000 Hz
- Channels: Mono
- Bit depth: 16-bit
- Naming: `{call_sid}_{timestamp}.wav`

**Features:**
- Automatic recording on call start
- Records full bidirectional audio (caller + AI)
- Metadata stored in database
- Downloadable via API

---

## Call Status Flow

```
outbound: queued → in-progress → completed/failed
inbound:  ringing → in-progress → completed/failed/no-answer
```

---

## Directory Structure

```
11labs/
├── app.py                  # Main FastAPI application
├── models.py              # SQLAlchemy models
├── database.py            # Database setup and session management
├── call_service.py        # Business logic for call management
├── audio_recorder.py      # Audio recording utility
├── gemini_ai.py          # Gemini Live API integration
├── persona.txt           # AI agent persona/instructions
├── index.html            # Web UI
├── .env                  # Environment variables
├── data/
│   └── calls.db          # SQLite database
├── recordings/           # Call recordings (WAV files)
└── logs/
    └── app.log          # Application logs
```
