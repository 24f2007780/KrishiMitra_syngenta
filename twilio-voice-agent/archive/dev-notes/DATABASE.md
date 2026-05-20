# Database Setup

## Overview
This application uses **SQLite** with **SQLAlchemy ORM** for call tracking and management.

## Features
✅ No migrations required - schema auto-creates on first run  
✅ Simple SQLite file-based database  
✅ ORM-based (no raw SQL)  
✅ Automatic call logging and status tracking  
✅ Call recordings with metadata storage  

## Database Location
```
data/calls.db
```

## Automatic Initialization
The database is automatically created when the app starts:
```python
# In app.py
init_db()  # Creates tables if they don't exist
```

## Schema

### `calls` Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| call_sid | VARCHAR(50) | Twilio call SID (unique, indexed) |
| stream_sid | VARCHAR(50) | Media stream SID |
| direction | VARCHAR(10) | `inbound` or `outbound` |
| from_number | VARCHAR(20) | Caller's phone number |
| to_number | VARCHAR(20) | Recipient's phone number |
| status | VARCHAR(20) | Call status |
| created_at | DATETIME | When call was initiated |
| started_at | DATETIME | When call connected |
| ended_at | DATETIME | When call ended |
| duration | FLOAT | Call duration (seconds) |
| recording_path | VARCHAR(255) | Path to WAV file |
| recording_duration | FLOAT | Recording duration (seconds) |
| caller_name | VARCHAR(100) | Optional caller name |
| notes | TEXT | Optional notes |
| error_message | TEXT | Error if call failed |

## Usage Examples

### Query Calls
```python
from database import get_db
from call_service import call_service

# Get all calls
with get_db() as db:
    calls = call_service.get_all_calls(db)
    for call in calls:
        print(call.to_dict())

# Get specific call
with get_db() as db:
    call = call_service.get_call_by_sid(db, "CA123...")
    if call:
        print(f"Duration: {call.duration}s")
        print(f"Recording: {call.recording_path}")

# Get statistics
with get_db() as db:
    stats = call_service.get_call_stats(db)
    print(stats)
```

### Direct SQLAlchemy Query
```python
from database import get_db
from models import Call
from datetime import datetime, timedelta

with get_db() as db:
    # Get recent completed calls
    recent_calls = db.query(Call)\
        .filter(Call.status == "completed")\
        .filter(Call.created_at >= datetime.utcnow() - timedelta(days=7))\
        .order_by(Call.created_at.desc())\
        .limit(10)\
        .all()
    
    for call in recent_calls:
        print(f"{call.call_sid}: {call.from_number} → {call.to_number}")
```

## Backup

### Manual Backup
```bash
cp data/calls.db data/calls_backup_$(date +%Y%m%d).db
```

### Automated Backup Script
```bash
#!/bin/bash
# backup_db.sh
BACKUP_DIR="backups"
mkdir -p $BACKUP_DIR
cp data/calls.db "$BACKUP_DIR/calls_$(date +%Y%m%d_%H%M%S).db"
echo "Backup created"
```

## Reset Database
```bash
# Delete database file
rm data/calls.db

# Restart app - it will auto-create fresh database
uvicorn app:app --reload
```

## Viewing Database

### Using SQLite CLI
```bash
sqlite3 data/calls.db

# View schema
.schema calls

# Query calls
SELECT call_sid, direction, status, duration 
FROM calls 
ORDER BY created_at DESC 
LIMIT 10;

# Statistics
SELECT 
    direction,
    status,
    COUNT(*) as count,
    AVG(duration) as avg_duration
FROM calls
GROUP BY direction, status;
```

### Using DB Browser for SQLite
Download: https://sqlitebrowser.org/

1. Open `data/calls.db`
2. Browse Data tab
3. Select `calls` table

## No Migrations Needed
Unlike complex ORMs with migrations (Alembic, etc.), this setup:
- Auto-creates tables on startup
- No migration files
- Simple and maintainable
- Perfect for small to medium applications

If you need to change the schema:
1. Update `models.py`
2. Delete `data/calls.db`
3. Restart app (fresh DB with new schema)
