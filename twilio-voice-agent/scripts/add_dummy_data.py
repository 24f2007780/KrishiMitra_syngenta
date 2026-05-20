#!/usr/bin/env python3
"""
Dummy data generator for call analytics POC
Generates realistic call records for testing the dashboard

Run from repo root: python scripts/add_dummy_data.py
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from datetime import datetime, timedelta
import random
import json
from database import get_db, init_db
from models import Call

# Sample realistic transcripts by intent type
ENROLLMENT_TRANSCRIPTS = [
    [
        {"speaker": "user", "text": "Hi, I'm interested in enrolling for your engineering courses"},
        {"speaker": "assistant", "text": "Great! We have comprehensive engineering programs. What's your background?"},
        {"speaker": "user", "text": "I'm a fresher looking to prepare for placements"},
        {"speaker": "assistant", "text": "Perfect! We have a placement-focused program. Would you like more details?"},
    ],
    [
        {"speaker": "user", "text": "Do you have courses for JEE preparation?"},
        {"speaker": "assistant", "text": "Yes, we specialize in JEE Main and Advanced. When are you planning to take the exam?"},
        {"speaker": "user", "text": "Next year, I'm in class 11"},
        {"speaker": "assistant", "text": "We have year-long programs for class 11 students. Would you like to know the fees?"},
    ],
    [
        {"speaker": "user", "text": "I want to improve my mathematical skills"},
        {"speaker": "assistant", "text": "We have tailored math programs. What level are you at?"},
        {"speaker": "user", "text": "High school level, I struggle with calculus"},
        {"speaker": "assistant", "text": "Calculus is our specialty. Let me transfer you to our enrollment specialist"},
    ],
]

ACADEMIC_DOUBT_TRANSCRIPTS = [
    [
        {"speaker": "user", "text": "Can you help me understand derivatives?"},
        {"speaker": "assistant", "text": "Of course! Derivatives measure the rate of change. Let me explain with an example."},
        {"speaker": "user", "text": "How do I solve chain rule problems?"},
        {"speaker": "assistant", "text": "The chain rule is when you have a function inside another function..."},
    ],
    [
        {"speaker": "user", "text": "I'm stuck on quadratic equations"},
        {"speaker": "assistant", "text": "Let's break it down. What specific part is confusing?"},
        {"speaker": "user", "text": "The discriminant formula"},
        {"speaker": "assistant", "text": "The discriminant tells us the nature of roots. The formula is b² - 4ac..."},
    ],
    [
        {"speaker": "user", "text": "I need help with physics - Newton's laws"},
        {"speaker": "assistant", "text": "Newton's laws are fundamental. Which law are you struggling with?"},
        {"speaker": "user", "text": "The third law - action and reaction"},
        {"speaker": "assistant", "text": "Every action has an equal and opposite reaction..."},
    ],
    [
        {"speaker": "user", "text": "How do I balance chemical equations?"},
        {"speaker": "assistant", "text": "Let's identify the number of atoms on each side first..."},
        {"speaker": "user", "text": "This is confusing with multiple coefficients"},
        {"speaker": "assistant", "text": "Let me show you a systematic approach..."},
    ],
]

REFUND_TRANSCRIPTS = [
    [
        {"speaker": "user", "text": "I want to get my money back. This course is terrible"},
        {"speaker": "assistant", "text": "I'm sorry to hear that. Can you tell me what's the issue?"},
        {"speaker": "user", "text": "The teaching quality is poor. I'm not learning anything"},
        {"speaker": "assistant", "text": "Let me connect you with our refund team to discuss this"},
    ],
    [
        {"speaker": "user", "text": "I want a refund immediately"},
        {"speaker": "assistant", "text": "Of course, I can help with that. How many days have you been using the course?"},
        {"speaker": "user", "text": "3 days, and I don't like the content"},
        {"speaker": "assistant", "text": "We have a 7-day money-back guarantee. Let me process your refund"},
    ],
    [
        {"speaker": "user", "text": "This course doesn't match the description"},
        {"speaker": "assistant", "text": "I apologize for the mismatch. Can you elaborate?"},
        {"speaker": "user", "text": "It says advanced but the content is basic"},
        {"speaker": "assistant", "text": "Let me escalate this to our refund manager immediately"},
    ],
    [
        {"speaker": "user", "text": "I'm unhappy with my purchase. I want a refund"},
        {"speaker": "assistant", "text": "I understand your frustration. When did you purchase?"},
        {"speaker": "user", "text": "5 days ago"},
        {"speaker": "assistant", "text": "You're within the refund window. Let me initiate the process"},
    ],
]


def generate_phone_numbers(count: int) -> list:
    """Generate realistic Indian phone numbers in E.164 format"""
    numbers = []
    for _ in range(count):
        # Indian mobile numbers: +91 followed by 10 digits
        phone = f"+91{random.randint(6000000000, 9999999999)}"
        numbers.append(phone)
    return numbers


def generate_dummy_calls() -> list:
    """Generate realistic dummy call records"""
    calls = []
    
    # Define intent types and their characteristics
    intent_config = {
        "enrollment": {
            "high_pct": 0.40,
            "medium_pct": 0.45,
            "low_pct": 0.15,
            "avg_duration": 450,  # 7.5 minutes
            "transcripts": ENROLLMENT_TRANSCRIPTS,
            "icon": "📚"
        },
        "academic_doubt": {
            "high_pct": 0.25,
            "medium_pct": 0.50,
            "low_pct": 0.25,
            "avg_duration": 300,  # 5 minutes
            "transcripts": ACADEMIC_DOUBT_TRANSCRIPTS,
            "icon": "❓"
        },
        "refund": {
            "high_pct": 0.55,
            "medium_pct": 0.30,
            "low_pct": 0.15,
            "avg_duration": 240,  # 4 minutes
            "transcripts": REFUND_TRANSCRIPTS,
            "icon": "💸"
        }
    }
    
    # Generate 35 calls total (split across intent types)
    calls_per_type = 12
    
    for intent_type, config in intent_config.items():
        phone_numbers = generate_phone_numbers(calls_per_type + 5)
        
        for i in range(calls_per_type):
            # Randomly determine intent category based on distribution
            rand = random.random()
            if rand < config["high_pct"]:
                category = "high"
                score = random.randint(80, 100)
            elif rand < config["high_pct"] + config["medium_pct"]:
                category = "medium"
                score = random.randint(50, 79)
            else:
                category = "low"
                score = random.randint(0, 49)
            
            # Generate random timestamps (last 7 days)
            days_ago = random.randint(0, 6)
            hours_ago = random.randint(0, 23)
            created_at = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago, minutes=random.randint(0, 59))
            
            # Duration based on intent type + randomness
            duration = config["avg_duration"] + random.randint(-120, 120)
            
            # Select random transcript
            transcript = random.choice(config["transcripts"])
            
            call = Call(
                call_sid=f"CA{''.join(random.choices('0123456789abcdef', k=30))}",
                stream_sid=f"MZ{''.join(random.choices('0123456789abcdef', k=30))}",
                direction="inbound",
                from_number=phone_numbers[i],
                to_number="+17654030113",
                status="completed",
                created_at=created_at,
                started_at=created_at + timedelta(seconds=2),
                ended_at=created_at + timedelta(seconds=duration),
                duration=duration,
                recording_path=f"recordings/call_{intent_type}_{i}.wav",
                recording_duration=duration,
                transcript=transcript,
                intent_score=score,
                intent_category=category,
                intent_type=intent_type,
                intent_breakdown={
                    "enrollment": random.randint(0, 100) if intent_type == "enrollment" else random.randint(0, 40),
                    "academic_doubt": random.randint(0, 100) if intent_type == "academic_doubt" else random.randint(0, 40),
                    "refund": random.randint(0, 100) if intent_type == "refund" else random.randint(0, 40),
                },
                caller_name=f"User_{intent_type}_{i}",
                notes=f"{config['icon']} {intent_type.replace('_', ' ').title()} - {category.upper()} Intent"
            )
            calls.append(call)
    
    return calls


def main():
    """Main entry point"""
    print("🔄 Initializing database...")
    init_db()
    
    print("📝 Generating dummy call data...")
    calls = generate_dummy_calls()
    
    print(f"💾 Adding {len(calls)} dummy records to database...")
    with get_db() as db:
        for call in calls:
            db.add(call)
        db.commit()
    
    print("✅ Dummy data added successfully!")
    print()
    print("📊 Data Summary:")
    print("=" * 50)
    
    with get_db() as db:
        from call_service import CallService
        cs = CallService()
        
        for intent_type in ["enrollment", "academic_doubt", "refund"]:
            stats = cs.get_intent_stats_by_type(db, intent_type)
            print(f"\n{intent_type.upper()}:")
            print(f"  Total: {stats['total']}")
            print(f"  High: {stats['high']} ({stats['high_percentage']:.1f}%)")
            print(f"  Medium: {stats['medium']} ({stats['medium_percentage']:.1f}%)")
            print(f"  Low: {stats['low']} ({stats['low_percentage']:.1f}%)")
    
    print("\n" + "=" * 50)
    print("💡 To remove this data later, delete data/calls.db and restart")


if __name__ == "__main__":
    main()
