# Frontend Integration Guide

Quick guide for integrating the Call Tracking API into your frontend application.

## Base URL
```
http://127.0.0.1:8000
```

---

## 1. List All Calls

**Endpoint:** `GET /api/v1/calls`

**Query Parameters:**
- `skip` (optional): Pagination offset (default: 0)
- `limit` (optional): Max records to return (default: 100)
- `direction` (optional): Filter by `inbound` or `outbound`
- `status` (optional): Filter by `queued`, `in-progress`, `completed`, `failed`

**Example Request:**
```javascript
// Fetch all calls
const response = await fetch('http://127.0.0.1:8000/api/v1/calls?limit=50');
const data = await response.json();

console.log(data);
// {
//   "success": true,
//   "count": 15,
//   "calls": [...]
// }
```

**Response Structure:**
```json
{
  "success": true,
  "count": 2,
  "calls": [
    {
      "id": 1,
      "call_sid": "CA42fbeba029c213db9828aa28caf4330d",
      "stream_sid": "MZ4493d9196e7f067e5021bf2cfd45dcfd",
      "direction": "outbound",
      "from_number": "+1234567890",
      "to_number": "+0987654321",
      "status": "completed",
      "created_at": "2026-01-06T16:07:00.599000",
      "started_at": "2026-01-06T16:07:01.000000",
      "ended_at": "2026-01-06T16:08:30.500000",
      "duration": 89.5,
      "recording_path": "recordings/CA42fbeba029c213db9828aa28caf4330d_20260106_103700.wav",
      "recording_duration": 89.5,
      "transcript": [],
      "caller_name": null,
      "notes": null,
      "error_message": null
    }
  ]
}
```

---

## 2. Get Call Details

**Endpoint:** `GET /api/v1/calls/{call_sid}`

**Example Request:**
```javascript
const callSid = 'CA42fbeba029c213db9828aa28caf4330d';
const response = await fetch(`http://127.0.0.1:8000/api/v1/calls/${callSid}`);
const data = await response.json();

console.log(data.call);
```

**Response Structure:**
```json
{
  "success": true,
  "call": {
    "id": 1,
    "call_sid": "CA42fbeba029c213db9828aa28caf4330d",
    "stream_sid": "MZ4493d9196e7f067e5021bf2cfd45dcfd",
    "direction": "outbound",
    "from_number": "+1234567890",
    "to_number": "+0987654321",
    "status": "completed",
    "created_at": "2026-01-06T16:07:00.599000",
    "started_at": "2026-01-06T16:07:01.000000",
    "ended_at": "2026-01-06T16:08:30.500000",
    "duration": 89.5,
    "recording_path": "recordings/CA42fbeba029c213db9828aa28caf4330d_20260106_103700.wav",
    "recording_duration": 89.5,
    "transcript": [
      {
        "speaker": "user",
        "text": "Hello, I need help with my math homework",
        "timestamp": "2026-01-06T16:07:05.123456"
      },
      {
        "speaker": "assistant",
        "text": "Hi! I'd be happy to help you with your math homework. What topic are you working on?",
        "timestamp": "2026-01-06T16:07:07.456789"
      }
    ],
    "caller_name": null,
    "notes": null,
    "error_message": null
  }
}
```

---

## 3. Get Recording Information

**Endpoint:** `GET /api/v1/recordings/{call_sid}`

Returns the same data as `/api/v1/calls/{call_sid}` (includes recording path and transcript).

**Example Request:**
```javascript
const callSid = 'CA42fbeba029c213db9828aa28caf4330d';
const response = await fetch(`http://127.0.0.1:8000/api/v1/recordings/${callSid}`);
const data = await response.json();

const recordingPath = data.call.recording_path;
const transcript = data.call.transcript;
```

---

## 4. Download Audio File

**Endpoint:** `GET /api/v1/recordings/{call_sid}/download`

Downloads the actual WAV audio file.

**Example Request:**
```javascript
const callSid = 'CA42fbeba029c213db9828aa28caf4330d';
const downloadUrl = `http://127.0.0.1:8000/api/v1/recordings/${callSid}/download`;

// Option 1: Direct download link
window.open(downloadUrl, '_blank');

// Option 2: Play in HTML5 audio player
const audio = document.getElementById('audio-player');
audio.src = downloadUrl;
audio.play();
```

---

## 5. Get Call Statistics

**Endpoint:** `GET /api/v1/calls/stats`

**Example Request:**
```javascript
const response = await fetch('http://127.0.0.1:8000/api/v1/calls/stats');
const data = await response.json();

console.log(data.stats);
// {
//   "total_calls": 50,
//   "inbound_calls": 30,
//   "outbound_calls": 20,
//   "completed_calls": 45
// }
```

---

## Complete React Example

```jsx
import React, { useState, useEffect } from 'react';

const CallsList = () => {
  const [calls, setCalls] = useState([]);
  const [selectedCall, setSelectedCall] = useState(null);
  const [loading, setLoading] = useState(true);

  const API_BASE = 'http://127.0.0.1:8000';

  // Fetch all calls on mount
  useEffect(() => {
    fetchCalls();
  }, []);

  const fetchCalls = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/calls?limit=100`);
      const data = await response.json();
      if (data.success) {
        setCalls(data.calls);
      }
    } catch (error) {
      console.error('Error fetching calls:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCallDetails = async (callSid) => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/calls/${callSid}`);
      const data = await response.json();
      if (data.success) {
        setSelectedCall(data.call);
      }
    } catch (error) {
      console.error('Error fetching call details:', error);
    }
  };

  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) return <div>Loading calls...</div>;

  return (
    <div style={{ display: 'flex', gap: '20px' }}>
      {/* Calls List */}
      <div style={{ flex: 1 }}>
        <h2>Calls</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {calls.map((call) => (
            <div
              key={call.call_sid}
              onClick={() => fetchCallDetails(call.call_sid)}
              style={{
                padding: '15px',
                border: '1px solid #ddd',
                borderRadius: '8px',
                cursor: 'pointer',
                backgroundColor: selectedCall?.call_sid === call.call_sid ? '#e3f2fd' : 'white'
              }}
            >
              <div style={{ fontWeight: 'bold' }}>
                {call.direction === 'inbound' ? '📞 Inbound' : '📱 Outbound'}
              </div>
              <div style={{ fontSize: '12px', color: '#666' }}>
                {call.from_number} → {call.to_number}
              </div>
              <div style={{ fontSize: '12px', marginTop: '5px' }}>
                Status: <span style={{ color: call.status === 'completed' ? 'green' : 'orange' }}>
                  {call.status}
                </span>
              </div>
              <div style={{ fontSize: '12px' }}>
                Duration: {formatDuration(call.duration)}
              </div>
              <div style={{ fontSize: '11px', color: '#999' }}>
                {new Date(call.created_at).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Call Details Panel */}
      {selectedCall && (
        <div style={{ flex: 1, padding: '20px', border: '1px solid #ddd', borderRadius: '8px' }}>
          <h2>Call Details</h2>
          
          {/* Call Info */}
          <div style={{ marginBottom: '20px' }}>
            <p><strong>Call SID:</strong> {selectedCall.call_sid}</p>
            <p><strong>Direction:</strong> {selectedCall.direction}</p>
            <p><strong>Status:</strong> {selectedCall.status}</p>
            <p><strong>Duration:</strong> {formatDuration(selectedCall.duration)}</p>
          </div>

          {/* Audio Player */}
          {selectedCall.recording_path && (
            <div style={{ marginBottom: '20px' }}>
              <h3>Recording</h3>
              <audio controls style={{ width: '100%' }}>
                <source 
                  src={`${API_BASE}/api/v1/recordings/${selectedCall.call_sid}/download`}
                  type="audio/wav"
                />
              </audio>
              <a 
                href={`${API_BASE}/api/v1/recordings/${selectedCall.call_sid}/download`}
                download
                style={{ fontSize: '12px' }}
              >
                Download Recording
              </a>
            </div>
          )}

          {/* Transcript */}
          <div>
            <h3>Transcript</h3>
            {selectedCall.transcript && selectedCall.transcript.length > 0 ? (
              <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                {selectedCall.transcript.map((entry, index) => (
                  <div
                    key={index}
                    style={{
                      padding: '10px',
                      marginBottom: '10px',
                      backgroundColor: entry.speaker === 'user' ? '#f5f5f5' : '#e3f2fd',
                      borderRadius: '8px'
                    }}
                  >
                    <div style={{ fontWeight: 'bold', fontSize: '12px', marginBottom: '5px' }}>
                      {entry.speaker === 'user' ? '👤 User' : '🤖 Assistant'}
                      <span style={{ marginLeft: '10px', color: '#999', fontWeight: 'normal' }}>
                        {new Date(entry.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div>{entry.text}</div>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: '#999' }}>No transcript available</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CallsList;
```

---

## Data Structure Reference

### Call Object
```typescript
interface Call {
  id: number;
  call_sid: string;              // Twilio Call SID (unique identifier)
  stream_sid: string | null;     // Twilio Stream SID
  direction: 'inbound' | 'outbound';
  from_number: string;           // Caller's phone number
  to_number: string;             // Recipient's phone number
  status: 'queued' | 'ringing' | 'in-progress' | 'completed' | 'failed' | 'no-answer';
  created_at: string;            // ISO 8601 timestamp
  started_at: string | null;     // When call actually connected
  ended_at: string | null;       // When call ended
  duration: number | null;       // Duration in seconds
  recording_path: string | null; // Path to WAV file
  recording_duration: number | null;
  transcript: TranscriptEntry[]; // Conversation transcript
  caller_name: string | null;
  notes: string | null;
  error_message: string | null;
}

interface TranscriptEntry {
  speaker: 'user' | 'assistant';
  text: string;
  timestamp: string;             // ISO 8601 timestamp
}
```

---

## CORS Configuration

If your frontend is on a different domain, you may need to enable CORS. The backend already has CORS enabled for all origins (`*`), so you should be able to make requests from any frontend.

---

## Error Handling

All endpoints return a consistent error format:

```json
{
  "success": false,
  "error": "Error message here"
}
```

Always check the `success` field before accessing data:

```javascript
const response = await fetch(url);
const data = await response.json();

if (!data.success) {
  console.error('API Error:', data.error);
  return;
}

// Safe to use data
console.log(data.calls);
```

---

## Need Help?

- Check API logs: The server logs all requests and errors
- Test endpoints: Use Postman or curl to verify endpoints work
- Check CORS: If requests fail from browser, check browser console for CORS errors
