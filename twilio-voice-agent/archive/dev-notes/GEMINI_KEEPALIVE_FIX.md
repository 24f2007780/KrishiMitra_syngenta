# Gemini Live API Keepalive Timeout Fix

## Problem
After 5-10 minutes of deployment, the Gemini WebSocket connection was timing out with:
```
Error receiving from Gemini: sent 1011 (internal error) keepalive ping timeout; no close frame received
```

This caused `upstream request timeout` errors and service unavailability.

## Root Cause
- Long-running WebSocket connections to Gemini API have keepalive/ping-pong timeout issues
- When no data is actively being sent/received for extended periods, the connection becomes stale
- The error code 1011 indicates an internal server error on Gemini's side

## Solution Implemented

### 1. **Keepalive Monitoring** (gemini_ai.py)
- Added `_keepalive_monitor()` task that tracks connection health
- Monitors `last_activity_time` to detect stale connections
- Marks connection as dead if no activity for 60+ seconds (2x timeout)
- Prevents hanging connections from accumulating

### 2. **Activity Tracking**
- Updated every audio send/receive operation to record `last_activity_time`
- Helps identify when connection becomes genuinely inactive

### 3. **Better Error Detection**
- Enhanced error handling to specifically catch:
  - "keepalive ping timeout" errors
  - 1011 internal error codes
  - Stale connection states
- Graceful degradation when connection fails

### 4. **Automatic Reconnection** (app.py)
- Added reconnection logic in the WebSocket handler
- When sending audio and connection is lost, automatically attempt reconnect
- Reconnection happens transparently during the call
- Falls back gracefully if reconnection fails

### 5. **Connection Timeout Protection**
- Added timeout wrapper for initial connection (60s)
- Prevents indefinite connection hangs
- Faster failure detection and recovery

## Files Modified

### `gemini_ai.py`
- Added constants: `KEEPALIVE_TIMEOUT = 30s`, `CONNECTION_TIMEOUT = 60s`
- Added fields: `keepalive_task`, `last_activity_time`, reconnection counters
- Enhanced `connect()` with timeout wrapper
- Enhanced `_send_audio()` with activity tracking and error detection
- Enhanced `_receive_responses()` with keepalive error detection
- Added new `_keepalive_monitor()` coroutine
- Updated `disconnect()` to cancel keepalive task

### `app.py`
- Added connection status check in media event handler
- Added automatic reconnection attempt on send failure
- Better error logging for connection issues

## Benefits
✅ Connection stays alive even during low-activity periods
✅ Automatic recovery from temporary connection drops
✅ Detects and recovers from Gemini API internal errors
✅ No manual intervention required during calls
✅ Better error visibility for debugging

## Testing Recommendations
1. Deploy and monitor logs for "keepalive" errors (should not appear)
2. Test long calls (15+ minutes) to verify stability
3. Monitor Cloud Run logs for connection patterns
4. Check that audio flows continuously without interruption

## Future Improvements
- Add metrics/alerts for connection drops
- Implement exponential backoff for reconnection attempts
- Add connection quality monitoring
- Consider connection pooling if needed
