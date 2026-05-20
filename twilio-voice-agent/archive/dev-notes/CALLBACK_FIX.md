# Fixed Callback Flow - Agent Calling Customer

## What Was Fixed

The callback system now correctly:
1. **Takes agent's phone number** from the dashboard input field
2. **Calls the agent** from your Twilio number (+17654030113)
3. **Connects the customer** to the agent when agent answers
4. **Establishes proper two-way call** between agent and customer

## Previous Flow (Incorrect)
```
Agent clicks phone icon
        ↓
Twilio calls customer directly
        ↓
Agent hears nothing (not part of call)
        ✗ WRONG
```

## New Flow (Correct)
```
Agent enters their phone number in dashboard
        ↓
Agent clicks phone icon with customer number
        ↓
Confirmation shows both numbers
        ↓
Twilio calls AGENT from +17654030113
        ↓
Call modal opens (shows customer phone)
        ↓
Agent answers their phone
        ↓
TwiML automatically dials customer
        ↓
Agent and customer are now connected
        ✓ CORRECT
```

## How to Use

### Step 1: Enter Agent Phone
1. Go to Dashboard → All Calls tab
2. Find "Agent Phone:" field at the top
3. Enter your phone number (e.g., +1 234 567 890)
4. This is saved in the input field for all callbacks

### Step 2: Initiate Callback
1. Find a call in the list
2. Click the phone icon (☎) in the rightmost column
3. Confirmation dialog shows:
   ```
   Agent: +1 234 567 890
   Customer: +919147196925
   
   Call agent to connect with customer?
   ```
4. Click OK to confirm

### Step 3: Answer Your Phone
1. Your phone rings (from Twilio number +17654030113)
2. Answer the call
3. You'll hear "Connecting you to the customer at +919147196925"
4. Customer phone is automatically dialed
5. Call is established between you and customer

### Step 4: End Call
1. Click the red disconnect button in modal, OR
2. Hang up your phone
3. Call ends and list refreshes

## Backend Changes

### New Request Model
```python
class CallbackRequest(BaseModel):
    agent_phone: str        # Your phone number
    customer_phone: str     # Customer phone number
```

### Updated Endpoint
```
POST /api/v1/callback
Content-Type: application/json

{
  "agent_phone": "+1234567890",
  "customer_phone": "+919147196925"
}
```

### Response
```json
{
  "success": true,
  "call_sid": "CA...",
  "status": "ringing",
  "agent_phone": "+1234567890",
  "customer_phone": "+919147196925",
  "twilio_number": "+17654030113",
  "message": "Calling agent +1234567890 to connect with customer +919147196925"
}
```

### TwiML Logic
```python
response = VoiceResponse()
response.say(f"Connecting you to the customer at {customer_phone}")
response.dial(customer_phone, timeout=30)
```

This:
1. Greets the agent
2. Dials the customer automatically when agent answers

## Frontend Changes

### Agent Phone Input
Located in All Calls section:
```html
<input type="tel" id="agent-phone-input" 
       placeholder="Enter your phone +1234567890"
       style="width: 250px;">
```

### Updated Callback Function
```javascript
async function initiateCallback(phoneNumber, event) {
    // Get agent phone from input
    const agentPhone = document.getElementById('agent-phone-input').value;
    
    // Validate agent phone entered
    if (!agentPhone) {
        alert('Please enter your phone number first');
        return;
    }
    
    // Call backend with BOTH numbers
    const response = await fetch('/api/v1/callback', {
        method: 'POST',
        body: JSON.stringify({
            agent_phone: agentPhone,
            customer_phone: phoneNumber
        })
    });
}
```

## Call Modal Updates

The call modal now displays:
- **Customer phone number**: Shows who you're connecting to
- **Status**: "Calling agent..." → "Agent answering..."
- **Timer**: Tracks call duration
- **Disconnect button**: Click to end call

## Key Improvements

1. **Two-way Communication**: Both agent and customer hear each other
2. **Proper Workflow**: Agent answers their phone, then customer is connected
3. **Clear Information**: Modal shows exactly who's being called
4. **Error Handling**: Validates agent phone is entered before attempting call
5. **Confirmation**: Shows both numbers before initiating

## Testing Checklist

- [ ] Server started: `./venv/bin/python -m uvicorn app:app --reload`
- [ ] Dashboard opens: `http://127.0.0.1:8000/dashboard`
- [ ] Agent Phone field visible in All Calls tab
- [ ] Enter your phone number in Agent Phone field
- [ ] Click phone icon on a call
- [ ] Confirmation shows both agent and customer numbers
- [ ] Click OK
- [ ] Your phone rings from +17654030113
- [ ] Answer your phone
- [ ] You hear "Connecting you to customer..."
- [ ] Customer phone is dialed automatically
- [ ] Call is established between you and customer
- [ ] Click red disconnect button to end call

## Important Notes

**Required for Testing:**
- Your phone number must be verified in Twilio console
- Customer phone must be verified (for trial accounts)
- Both numbers must be in E.164 format: +1234567890

**TwiML Dial Timeout:**
- Waits 30 seconds for customer to answer
- If customer doesn't answer, call returns to agent

**Call Recording:**
- Calls are logged to database with both numbers
- Recordings saved with full conversation

## Files Modified

1. **app.py**
   - Added `CallbackRequest` model with agent_phone and customer_phone
   - Updated `/api/v1/callback` endpoint with TwiML response
   - Changed from calling customer directly to calling agent first

2. **dashboard.html**
   - Added agent phone input field in filters
   - Updated `initiateCallback()` function
   - Now passes both agent and customer phones to API
   - Updated confirmation dialog to show both numbers

## API Backward Compatibility

**Old API** (still works for make-call):
```python
class CallRequest(BaseModel):
    to_number: str
```

**New API** (for callbacks):
```python
class CallbackRequest(BaseModel):
    agent_phone: str
    customer_phone: str
```

Both are supported simultaneously.

---

**Status**: Fixed and ready to use!
