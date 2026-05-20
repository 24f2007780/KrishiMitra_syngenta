# Gemini AI Voice Integration

## What This Does

Your Twilio phone system now has **AI-powered voice conversations** using Google's Gemini Live API! When someone answers a call, they can talk to Gemini AI in real-time.

## How It Works

```
Caller → Twilio Phone → WebSocket → Gemini AI → Real-time Voice Response
```

1. **Call is made** via your web interface or API
2. **Caller presses a key** to connect (as configured in your TwiML)
3. **Twilio streams audio** via WebSocket to your server
4. **Your server** converts audio format and sends to Gemini Live API
5. **Gemini responds** with natural voice in real-time
6. **Response is streamed back** to the caller

## Audio Processing Pipeline

### Incoming (Caller → Gemini):
- Twilio sends: **μ-law, 8kHz**
- Convert to: **PCM 16-bit**
- Resample to: **16kHz** (Gemini's input format)
- Send to Gemini Live API

### Outgoing (Gemini → Caller):
- Gemini sends: **PCM 24kHz**
- Resample to: **8kHz**
- Convert to: **μ-law**
- Send back to Twilio → Caller hears it

## Files Created

1. **`gemini_ai.py`** - Gemini Live API integration module
   - `GeminiLiveSession` class for managing conversations
   - Audio format conversion utilities
   - Async audio streaming

2. **`app.py`** - Updated WebSocket handler
   - Connects Twilio audio stream to Gemini
   - Handles bidirectional audio flow
   - Session management

## Configuration

Make sure your `.env` file has:
```env
GEMINI_API_KEY=AIzaSy...  # Your Gemini API key
```

## Customization

### Change Gemini's Personality

Edit in `app.py` at the WebSocket handler:

```python
gemini_session = GeminiLiveSession(
    api_key=GEMINI_API_KEY,
    system_instruction="Your custom instructions here..."
)
```

Examples:
- **Customer Support**: "You are a helpful customer support agent. Be professional and solve issues efficiently."
- **Sales Bot**: "You are an enthusiastic sales representative. Be persuasive but respectful."
- **Appointment Scheduler**: "You are an appointment scheduling assistant. Collect name, date, and time preferences."

### Adjust Response Style

In `gemini_ai.py`, modify the config:

```python
self.config = {
    "response_modalities": ["AUDIO"],  # or ["TEXT", "AUDIO"]
    "system_instruction": "...",
    # Add more config options
}
```

## Testing

### 1. Start the server:
```bash
source venv/bin/activate
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 2. Make sure ngrok is running:
```bash
ngrok http 8000
```
Update the ngrok URL in `app.py` if it changed.

### 3. Make a call:
```bash
curl -X POST http://localhost:8000/api/v1/callback \
  -H "Content-Type: application/json" \
  -d '{"to_number": "+919943193399"}'
```

### 4. When you answer:
- Listen for: "Press any key to connect to support"
- Press any key on your phone
- Start talking to Gemini AI!

## What You Can Ask Gemini

Try these:
- "What's the weather like?"
- "Tell me a joke"
- "Help me with [your product/service]"
- "Schedule an appointment"
- "What are your business hours?"

## Monitoring

Watch the server logs to see:
- `🎧 Media stream connected` - Call connected
- `🔌 Connecting to Gemini Live API...` - Connecting to AI
- `✅ Connected to Gemini Live API` - Ready!
- `📥 Sent X bytes to Gemini` - Audio being sent
- `🎵 Received audio from Gemini` - AI is responding
- `📤 Sent X bytes to Twilio` - Response going to caller

## Troubleshooting

### "No module named 'google'"
```bash
pip install google-genai
```

### "Unsupported WebSocket"
```bash
pip install 'uvicorn[standard]' websockets
```

### No audio from Gemini
- Check Gemini API key is valid
- Check logs for connection errors
- Verify audio format conversions

### Caller can't hear responses
- Verify ngrok URL in `app.py` matches your current ngrok session
- Check WebSocket connection in logs
- Ensure phone has good connection

## Next Steps

1. **Add function calling** - Let Gemini check databases, APIs, etc.
2. **Implement conversation memory** - Track user across calls
3. **Add speech recognition** - Get transcripts
4. **Integrate with your CRM** - Save call data
5. **Add analytics** - Track conversation metrics

## Cost Considerations

- **Gemini Live API**: Check [pricing](https://ai.google.dev/pricing)
- **Twilio**: Per-minute calling charges
- Use trial accounts for testing

## Security Notes

- Never commit `.env` file
- Rotate API keys regularly
- Use ephemeral tokens in production (see Gemini docs)
- Validate all inputs

---

**Ready to talk to AI!** 🎙️🤖
