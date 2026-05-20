"""
Database models for call tracking and user management
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User account with role-based access"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=True)
    phone = Column(String(20), nullable=True)
    role = Column(String(20), nullable=False, default="cse")  # 'admin' or 'cse'
    password_hash = Column(String(255), nullable=False)  # format: salt:hash
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_public_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "username": self.username,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Call(Base):
    """Call record model"""
    __tablename__ = "calls"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    call_sid = Column(String(50), unique=True, nullable=False, index=True)
    stream_sid = Column(String(50), nullable=True)
    direction = Column(String(10), nullable=False)  # inbound or outbound
    from_number = Column(String(20), nullable=False)
    to_number = Column(String(20), nullable=False)
    status = Column(String(20), default="queued")  # queued, ringing, in-progress, completed, failed, no-answer
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)  # When call actually connected
    ended_at = Column(DateTime, nullable=True)
    duration = Column(Float, nullable=True)  # Duration in seconds
    
    # Recording
    recording_path = Column(String(255), nullable=True)
    recording_duration = Column(Float, nullable=True)
    
    # Transcript - JSON array of {"speaker": "user"|"assistant", "text": "...", "timestamp": "..."}
    transcript = Column(JSON, nullable=True, default=list)
    
    # Intent Analysis
    intent_score = Column(Float, nullable=True, default=0)  # 0-100 score for enrollment intent (legacy)
    intent_category = Column(String(20), nullable=True)  # high, medium, low
    intent_type = Column(String(50), default="enrollment")  # enrollment, academic_doubt, refund
    intent_breakdown = Column(JSON, nullable=True, default={})  # {"enrollment": 75, "academic_doubt": 45, "refund": 20}
    
    # Metadata
    caller_name = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "call_sid": self.call_sid,
            "stream_sid": self.stream_sid,
            "direction": self.direction,
            "from_number": self.from_number,
            "to_number": self.to_number,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration": self.duration,
            "recording_path": self.recording_path,
            "recording_duration": self.recording_duration,
            "transcript": self.transcript or [],
            "intent_score": self.intent_score or 0,
            "intent_category": self.intent_category or "low",
            "intent_type": self.intent_type or "enrollment",
            "intent_breakdown": self.intent_breakdown or {},
            "caller_name": self.caller_name,
            "notes": self.notes,
            "error_message": self.error_message
        }
