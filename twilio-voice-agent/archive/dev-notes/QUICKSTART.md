# Quick Start Guide - Vedantu AI Voice Assistant with Intent Analysis

## Get Started in 2 Minutes

### Prerequisites
- Python 3.12+
- Virtual environment (already set up)
- Twilio account
- Google Gemini API key

### Step 1: Configure Environment
```bash
cd /home/ra/Downloads/11labs

# Edit .env with your credentials
nano .env

# Required environment variables:
# TWILIO_ACCOUNT_SID=your_account_sid
# TWILIO_AUTH_TOKEN=your_auth_token
# TWILIO_PHONE_NO=your_phone_number
# GEMINI_API_KEY=your_gemini_key
# TUNNEL_LINK=your_ngrok_url (e.g., https://xyz.ngrok-free.app)
```

### Step 2: Start the Server
```bash
# Terminal 1: Start FastAPI server
./venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000

# Terminal 2: Start ngrok tunnel (optional, for local testing)
ngrok http 8000

# Terminal 3: Monitor logs
tail -f logs/app.log
```

### Step 3: Access the Dashboard
Open your browser and navigate to:
```
http://127.0.0.1:8000/dashboard
```

## View Intent Analysis

1. **Click "Analytics"** in the left sidebar
2. **See intent distribution** with doughnut chart
3. **View intent statistics**:
   - High Intent (enrollment/fees questions)
   - Medium Intent (demo/trial questions)
   - Low Intent (informational questions)
4. **Explore calls by category** with scores

## 🎯 Test Intent Analysis

### Via API
```bash
# Get intent statistics
curl http://127.0.0.1:8000/api/v1/intent/stats

# Get high intent calls
curl http://127.0.0.1:8000/api/v1/calls/by-intent/high?limit=10

# Analyze a specific call
curl -X POST http://127.0.0.1:8000/api/v1/calls/CA123.../analyze-intent
```

### Via Python
```python
import sys
sys.path.insert(0, '/home/ra/Downloads/11labs')

from database import get_db
from call_service import call_service

with get_db() as db:
    # Get intent stats
    stats = call_service.get_intent_stats(db)
    print(f"High Intent Calls: {stats['high']} ({stats['high_percentage']}%)")
    
    # Get high intent calls
    calls = call_service.get_calls_by_intent(db, "high", limit=5)
    for call in calls:
        print(f"- {call.call_sid}: {call.intent_score} score")
```

## 📱 Make a Test Call

### Outbound Call (Initiate from Dashboard)
1. Go to Dashboard → All Calls
2. Enter phone number
3. Click "Initiate Call"
4. Wait for connection to Gemini AI
5. Speak naturally
6. Call will record and analyze intent

### Inbound Call
1. Configure Twilio webhook to point to your server
2. Call your Twilio number
3. System will accept and connect to AI

## 📈 Current Data

- **Total Calls**: 10
- **High Intent**: 3 calls (30%)
- **Medium Intent**: 0 calls (0%)
- **Low Intent**: 0 calls (0%)
- **Unanalyzed**: 7 calls (70%)

## 🔍 Understand Intent Scores

| Score | Category | Examples |
|-------|----------|----------|
| 60-100 | 🔥 High | "I want to enroll", "What are the fees?", "How much does it cost?" |
| 30-59 | ⚡ Medium | "Can I try a demo?", "What courses do you offer?", "Free trial?" |
| 0-29 | ❄️ Low | "What is Vedantu?", "Explain NCERT", "How to solve this?" |

## 📊 Dashboard Sections

### Dashboard (Home)
- Call statistics overview
- Recent calls list
- Status indicators

### All Calls
- Browse all calls
- Filter by direction (inbound/outbound)
- Filter by status (completed/failed/etc)
- View call details & transcripts

### Analytics (Intent Analysis)
- Intent distribution chart
- Intent statistics cards
- High intent calls list
- Medium intent calls list
- Low intent calls list

### Recordings
- View saved audio files
- Download WAV recordings
- View call transcripts

### Settings
- Configure preferences
- System settings (placeholder)

## 🛠️ Troubleshooting

### Stats showing 0?
```bash
# Check database
sqlite3 data/calls.db
> SELECT COUNT(*) FROM calls;
> SELECT COUNT(*) FROM calls WHERE status='completed';
```

### Intent not calculating?
```bash
# Run analysis on all calls
python3 -c "
import sys; sys.path.insert(0, '.')
from database import get_db
from call_service import call_service
with get_db() as db:
    calls = call_service.get_all_calls(db)
    for call in calls:
        if call.transcript:
            result = call_service.calculate_intent_score(str(call.transcript))
            call_service.set_intent_score(db, call.call_sid, result['score'], result['category'])
"
```

### No calls in database?
```bash
# Make sure Twilio webhook is configured correctly
# Verify TUNNEL_LINK in .env points to your ngrok URL
# Check logs for errors: tail -f logs/app.log
```

## 📚 Documentation Files

- **INTENT_ANALYSIS_GUIDE.md** - Detailed intent analysis documentation
- **SYSTEM_STATUS.md** - Complete system overview and features
- **API_DOCS.md** - API endpoint reference (if exists)
- **DATABASE.md** - Database schema documentation (if exists)

## 🎓 Learning Resources

### Intent Analysis Algorithm
The system uses keyword matching:
1. Count occurrences of keywords in transcript
2. Assign base score based on keyword category
3. Calculate final score (0-100)
4. Categorize as high/medium/low

### Example Calculation
```
Input: "I want to enroll and ask about fees"
- "enroll" keyword → 15 points (high-intent)
- "fees" keyword → 15 points (high-intent)
- "ask" keyword → 5 points (medium-intent)
Total Score: 35 points (would be adjusted to account for frequency)
Category: High (high-intent keywords present)
```

## 🔄 Workflow Example

1. **Call Initiated**
   - User calls or you initiate outbound
   - System creates call record
   - Connects to Gemini AI

2. **Conversation**
   - Real-time bidirectional audio
   - Transcript captured
   - Recording saved (both sides)

3. **Call Ends**
   - Duration calculated
   - Status updated to "completed"
   - Recording finalized

4. **Analysis**
   - Transcript analyzed for intent
   - Intent score calculated (0-100)
   - Intent category assigned (high/medium/low)
   - Dashboard updates automatically

5. **Follow-up**
   - High intent: Potential leads
   - Medium intent: Nurture campaigns
   - Low intent: Information seekers

## 🚨 Important Notes

- **Recordings**: Stored in `recordings/` directory (WAV format)
- **Database**: SQLite in `data/calls.db`
- **Logs**: Rotating files in `logs/` directory (5MB max each)
- **Transcripts**: Stored as JSON in database
- **API Rate Limiting**: Not configured (add for production)

## 📞 Support

For issues, check:
1. Logs: `tail -f logs/app.log`
2. Database: `sqlite3 data/calls.db ".tables"`
3. API Health: `curl http://127.0.0.1:8000/api/v1/calls/stats`

---

**Ready to test?** Navigate to `http://127.0.0.1:8000/dashboard` now! 🎉
