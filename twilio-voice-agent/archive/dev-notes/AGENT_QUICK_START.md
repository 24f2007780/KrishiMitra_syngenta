# Agent Call Handling - Quick Start

## How to Handle Calls Through Dashboard

### Step 1: Access Dashboard
```
http://localhost:8000/dashboard
```

### Step 2: View Recent Calls
- Go to "Dashboard" tab
- Scroll down to "Recent Calls" table
- Find customer call you want to handle

### Step 3: Initiate Call
1. Click the **phone icon (📞)** on the customer row
2. Confirmation: "Call customer: [number]?"
3. Click **OK**

### Step 4: Allow Microphone
- Browser will ask: "Allow microphone access?"
- Click **Allow**

### Step 5: Call Modal Appears
- Shows **customer phone number**
- Shows **timer** (00:00)
- Shows **status** ("Initiating call...")
- Has **control buttons**: Mute (🔊), Disconnect (☎), Keypad (⌨)

### Step 6: Customer Answers
- You'll hear ringing or silence
- Timer starts counting
- Status changes to "Connected - Listening..."
- You hear customer's voice in your speaker

### Step 7: Talk with Customer
- **Speak into your microphone**
- **Hear customer through speaker**
- **Two-way conversation**

### Step 8: Control the Call

| Button | Action |
|--------|--------|
| 🔊 (Speaker) | Mute/Unmute your microphone |
| ☎ (Red) | Hang up and end call |
| ⌨ (Keypad) | Send touch tones (optional) |

### Step 9: End Call
1. Click **red disconnect button (☎)**
2. Modal closes
3. Call is logged as completed
4. Calls list refreshes

---

## What You'll See

### Call Modal

```
┌────────────────────────────────┐
│     CALLING                    │
│  +919147196925                 │
│                                │
│     04:32  (call duration)     │
│  Connected - Listening...      │
│                                │
│  [🔊] [  ☎  ] [⌨]             │
│        (Disconnect)            │
└────────────────────────────────┘
```

- **Purple gradient background**
- **Large phone number** (easy to see)
- **Running timer** (MM:SS format)
- **Status message**
- **Three control buttons**

---

## Keyboard Shortcuts (Optional)

| Key | Action |
|-----|--------|
| M | Toggle mute |
| D | Disconnect |
| K | Keypad |

---

## Example Conversation

```
Timer: 00:00
Status: "Initiating call..."

    → Phone rings (customer receives call)
    → Tim: "Hello?"
    → You: "Hi Tim, this is Sarah from Vedantu..."
    → Tim: "Oh great, thanks for calling back!"
    → You: "Of course! Let me help you with..."

Timer: 04:32
Status: "Connected - Listening..."

    → [conversation continues]
    → You: "Does that answer your question?"
    → Tim: "Yes, perfectly! Thank you so much."
    → You: "Great! If you need anything else, just let me know."
    → [Click red disconnect button]

Modal closes → Call logged → Calls list refreshes
```

---

## Troubleshooting

### "Allow microphone access?" doesn't appear
- Check browser security settings
- Try different browser (Chrome, Firefox, Safari, Edge)
- Refresh page and try again

### Can't hear customer
- Check system volume
- Check browser volume (not muted)
- Verify speakers work in browser settings
- Try testing audio in system settings

### Customer can't hear you
- Click speaker button to check if muted (should be 🔊 not 🔇)
- Check microphone is enabled in system settings
- Try saying something and check if customer hears
- Check microphone is not muted in browser

### Call doesn't start
- Check internet connection
- Verify server is running (backend logs)
- Check phone number format (should be E.164: +1234567890)
- Refresh dashboard page

### Modal closes unexpectedly
- WebSocket may have disconnected
- Check browser console for errors (F12)
- Refresh page and try again

---

## Best Practices

### Before Call
✓ Check customer info in dashboard  
✓ Review previous call notes  
✓ Ensure microphone works  
✓ Minimize background noise  
✓ Have information ready  

### During Call
✓ Speak clearly and professionally  
✓ Listen actively  
✓ Confirm customer information  
✓ Take notes if needed  
✓ Be patient and helpful  

### After Call
✓ Click disconnect cleanly  
✓ Review call timer (duration)  
✓ Check call was logged  
✓ Update any notes/records  
✓ Move to next customer  

---

## Call Flow at a Glance

```
Find customer
        ↓
Click phone icon
        ↓
Allow microphone
        ↓
Call modal opens
        ↓
Customer receives call
        ↓
Customer answers
        ↓
You hear customer voice
        ↓
Have conversation
        ↓
Click disconnect
        ↓
Call ends & logged
```

---

## Important Notes

- You do NOT need to enter your phone number
- You do NOT need to be called back
- You handle calls directly through your browser
- Call is recorded in database automatically
- Timer tracks call duration
- You can mute your mic anytime (button turns 🔇)

---

## Support

If you encounter issues:

1. **Check browser console** (F12 → Console)
2. **Refresh page** and try again
3. **Check backend logs** in terminal
4. **Verify internet connection**
5. **Test microphone** in system settings
6. **Contact IT support** if problem persists

---

## Phone Number Format

Always use **E.164 format**:

✓ Correct: `+919147196925`
✓ Correct: `+1 (206) 555-0100`
✗ Wrong: `9147196925`
✗ Wrong: `919147196925`
✗ Wrong: `+91-9147-196925`

The system will show the number in the modal, so you'll see it formatted clearly.

---

## Pro Tips

🎯 **Keep conversations natural** - It's real human interaction  
🎤 **Speak clearly** - Especially with international calls  
⏱️ **Watch the timer** - Know when calls are getting long  
🔇 **Use mute wisely** - Only when absolutely necessary  
✍️ **Take quick notes** - After each call, jot down key points  

---

## Quick Reference Card

```
DASHBOARD → FIND CUSTOMER → CLICK PHONE ICON
    ↓
ALLOW MICROPHONE → WAIT FOR CUSTOMER TO ANSWER
    ↓
SPEAK AND LISTEN → CONTROL WITH BUTTONS
    ↓
CLICK RED BUTTON TO DISCONNECT → CALL LOGGED
```

Good luck with your calls! 📞
