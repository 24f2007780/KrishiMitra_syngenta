# Intent Analysis System - Complete Guide

## Overview

The **Intent Analysis System** has been fully implemented to analyze student enrollment intent from voice calls. It evaluates whether a caller is likely to enroll in Vedantu courses based on conversation content.

## Features Implemented

### 1. **Intent Scoring Algorithm**
- **High Intent (60-100 points)**: Explicit enrollment/fee questions
  - Keywords: enrol, enroll, register, join, start, fee, fees, pricing, price, cost, payment, discount, offer, batch, when does, how do i, 1-on-1, availability, how much
  
- **Medium Intent (30-59 points)**: Demo/evaluation questions
  - Keywords: demo, free, trial, class, course structure, subjects, covered, available, for class, for grade, compare, difference
  
- **Low Intent (0-29 points)**: Informational/exploratory
  - Keywords: what is vedantu, explain, ncert, solution, doubt, chapter, how to, career, general

### 2. **Database Schema**
Added two new columns to the `calls` table:
```
- intent_score (FLOAT): Score 0-100 representing enrollment likelihood
- intent_category (VARCHAR): One of "high", "medium", or "low"
```

### 3. **Backend API Endpoints**

#### `/api/v1/intent/stats` (GET)
Returns overall intent distribution statistics:
```json
{
  "success": true,
  "intent_stats": {
    "total": 10,
    "high": 3,
    "medium": 0,
    "low": 0,
    "high_percentage": 30.0,
    "medium_percentage": 0.0,
    "low_percentage": 0.0
  }
}
```

#### `/api/v1/calls/by-intent/{category}` (GET)
Returns calls filtered by intent category (high/medium/low):
```json
{
  "success": true,
  "category": "high",
  "count": 3,
  "calls": [...]
}
```

#### `/api/v1/calls/{call_sid}/analyze-intent` (POST)
Analyzes transcript and updates intent score for a specific call:
```json
{
  "success": true,
  "call_sid": "CA...",
  "intent_score": 80,
  "intent_category": "high"
}
```

### 4. **Dashboard Analytics**

The Analytics section (`/dashboard` → Analytics tab) now displays:

#### Intent Distribution Chart
- Doughnut chart showing High/Medium/Low intent breakdown
- Color coded: Red (High), Orange (Medium), Blue (Low)

#### Intent Statistics Cards
- High Intent: Count and percentage
- Medium Intent: Count and percentage  
- Low Intent: Count and percentage

#### Categorized Call Lists
- **High Intent Calls**: Lists 5 most recent high-intent calls with scores
- **Medium Intent Calls**: Lists 5 most recent medium-intent calls
- **Low Intent Calls**: Lists 5 most recent low-intent calls

Each call shows:
- Phone numbers (from → to)
- Creation timestamp
- Intent score (0-100)
- Call duration

### 5. **Service Layer Methods**

#### `calculate_intent_score(transcript_text)`
Analyzes text and returns:
```python
{
    "score": 0-100,
    "category": "high" | "medium" | "low"
}
```

#### `set_intent_score(db, call_sid, score, category)`
Updates a call record with intent analysis results

#### `get_calls_by_intent(db, category, limit)`
Retrieves calls filtered by intent category

#### `get_intent_stats(db)`
Returns distribution statistics with percentages

## Usage

### Access the Dashboard
1. Start the server: `python -m uvicorn app:app --host 127.0.0.1 --port 8000`
2. Open browser: `http://127.0.0.1:8000/dashboard`
3. Click **Analytics** in the sidebar
4. View intent distribution and categorized calls

### Analyze a Call
```bash
curl -X POST http://127.0.0.1:8000/api/v1/calls/{call_sid}/analyze-intent
```

### Get Intent Statistics
```bash
curl http://127.0.0.1:8000/api/v1/intent/stats
```

### Filter by Intent Category
```bash
curl http://127.0.0.1:8000/api/v1/calls/by-intent/high?limit=10
```

## Current Data

- **Total Calls**: 10
- **High Intent Calls**: 3 (30%)
- **Medium Intent Calls**: 0 (0%)
- **Low Intent Calls**: 0 (0%)
- **Unanalyzed Calls**: 7

## Files Modified

### `models.py`
- Added `intent_score` (Float, nullable, default=0)
- Added `intent_category` (String, nullable)
- Updated `to_dict()` to include new fields

### `call_service.py`
- Added `calculate_intent_score(text)` - Keyword-based scoring
- Added `set_intent_score(db, call_sid, score, category)` - Update scores
- Added `get_calls_by_intent(db, category, limit)` - Filter by intent
- Added `get_intent_stats(db)` - Statistics calculation

### `app.py`
- Added `/api/v1/intent/stats` endpoint
- Added `/api/v1/calls/by-intent/{category}` endpoint
- Added `/api/v1/calls/{call_sid}/analyze-intent` endpoint

### `dashboard.html`
- New analytics section with intent visualization
- Intent distribution doughnut chart (Chart.js)
- Intent statistics cards
- Categorized call lists with filtering
- New JavaScript functions:
  - `loadIntentStats()` - Load intent data
  - `loadIntentCalls(category)` - Load calls by category
  - `updateIntentChart(stats)` - Render chart

## Database Migrations

The following SQL was executed to add intent columns:
```sql
ALTER TABLE calls ADD COLUMN intent_score FLOAT DEFAULT 0;
ALTER TABLE calls ADD COLUMN intent_category VARCHAR(20);
```

## Performance Notes

- Intent analysis uses keyword matching (very fast, O(n) where n = word count)
- Dashboard charts render in real-time using Chart.js
- Intent data is auto-loaded when Analytics tab is selected
- All API endpoints return paginated results (default limit=50)

## Future Enhancements

- [ ] Machine learning-based intent detection (NLP)
- [ ] Sentiment analysis integration
- [ ] Real-time intent analysis during calls
- [ ] Intent trend charts (over time)
- [ ] Automatic follow-up suggestions based on intent
- [ ] Export intent analysis reports

## Testing

Run the verification script:
```bash
python -c "
import sys; sys.path.insert(0, '.')
from database import get_db
from call_service import call_service
with get_db() as db:
    print('High Intent:', call_service.get_intent_stats(db)['high'])
"
```

## Support

For issues or questions about intent analysis:
1. Check that database columns exist: `SELECT intent_score, intent_category FROM calls LIMIT 1`
2. Verify API endpoints are responding: `curl http://127.0.0.1:8000/api/v1/intent/stats`
3. Review call transcripts for proper keyword matching
