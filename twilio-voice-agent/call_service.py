"""
Service layer for call management
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from models import Call
import wave
import os


class CallService:
    """Service for managing call records"""
    
    RECORDINGS_DIR = "recordings"
    
    def __init__(self):
        os.makedirs(self.RECORDINGS_DIR, exist_ok=True)
    
    def create_call(
        self,
        db: Session,
        call_sid: str,
        direction: str,
        from_number: str,
        to_number: str,
        status: str = "queued"
    ) -> Call:
        """Create a new call record"""
        call = Call(
            call_sid=call_sid,
            direction=direction,
            from_number=from_number,
            to_number=to_number,
            status=status
        )
        db.add(call)
        db.commit()
        db.refresh(call)
        return call
    
    def get_call_by_sid(self, db: Session, call_sid: str) -> Optional[Call]:
        """Get call by Twilio call SID"""
        return db.query(Call).filter(Call.call_sid == call_sid).first()
    
    def get_call_by_stream_sid(self, db: Session, stream_sid: str) -> Optional[Call]:
        """Get call by stream SID"""
        return db.query(Call).filter(Call.stream_sid == stream_sid).first()
    
    def update_call_status(
        self,
        db: Session,
        call_sid: str,
        status: str,
        stream_sid: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Optional[Call]:
        """Update call status"""
        call = self.get_call_by_sid(db, call_sid)
        if call:
            call.status = status
            if stream_sid:
                call.stream_sid = stream_sid
            if error_message:
                call.error_message = error_message
            
            # Update timestamps
            if status == "in-progress" and not call.started_at:
                call.started_at = datetime.utcnow()
            elif status in ["completed", "failed", "no-answer"]:
                if not call.ended_at:
                    call.ended_at = datetime.utcnow()
                if call.started_at:
                    call.duration = (call.ended_at - call.started_at).total_seconds()
            
            db.commit()
            db.refresh(call)
        return call
    
    def set_recording_path(
        self,
        db: Session,
        call_sid: str,
        recording_path: str,
        duration: Optional[float] = None
    ) -> Optional[Call]:
        """Set recording file path for a call"""
        call = self.get_call_by_sid(db, call_sid)
        if call:
            call.recording_path = recording_path
            if duration:
                call.recording_duration = duration
            db.commit()
            db.refresh(call)
        return call
    
    def get_all_calls(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        direction: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Call]:
        """Get all calls with optional filters"""
        query = db.query(Call).order_by(Call.created_at.desc())
        
        if direction:
            query = query.filter(Call.direction == direction)
        if status:
            query = query.filter(Call.status == status)
        
        return query.offset(skip).limit(limit).all()
    
    def get_call_stats(self, db: Session) -> dict:
        """Get call statistics"""
        total_calls = db.query(Call).count()
        inbound_calls = db.query(Call).filter(Call.direction == "inbound").count()
        outbound_calls = db.query(Call).filter(Call.direction == "outbound").count()
        completed_calls = db.query(Call).filter(Call.status == "completed").count()
        
        return {
            "total_calls": total_calls,
            "inbound_calls": inbound_calls,
            "outbound_calls": outbound_calls,
            "completed_calls": completed_calls
        }
    
    def get_recording_path(self, call_sid: str) -> str:
        """Generate recording file path for a call"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{call_sid}_{timestamp}.wav"
        return os.path.join(self.RECORDINGS_DIR, filename)
    
    def add_transcript_entry(
        self,
        db: Session,
        call_sid: str,
        speaker: str,  # "user" or "assistant"
        text: str,
        timestamp: Optional[datetime] = None
    ) -> Optional[Call]:
        """Add a transcript entry to a call"""
        call = self.get_call_by_sid(db, call_sid)
        if call:
            if call.transcript is None:
                call.transcript = []
            
            entry = {
                "speaker": speaker,
                "text": text,
                "timestamp": (timestamp or datetime.utcnow()).isoformat()
            }
            
            # SQLAlchemy JSON needs to detect mutation
            transcript_copy = call.transcript.copy() if call.transcript else []
            transcript_copy.append(entry)
            call.transcript = transcript_copy
            
            db.commit()
            db.refresh(call)
        return call
    
    def calculate_intent_score(self, transcript_text: str) -> dict:
        """
        Calculate intent score based on transcript analysis
        Returns: {"score": 0-100, "category": "high"|"medium"|"low"}
        """
        if not transcript_text:
            return {"score": 0, "category": "low"}
        
        text_lower = transcript_text.lower()
        
        # High-Intent Keywords (60-100)
        high_intent_keywords = [
            'enrol', 'enroll', 'register', 'join', 'start', 'begin',
            'fee', 'fees', 'pricing', 'price', 'cost', 'payment', 'pay',
            'discount', 'offer', 'batch', 'when does', 'how do i',
            'one-to-one', '1-on-1', 'availability', 'schedule',
            'how much', 'how much does', 'what is the fee'
        ]
        
        # Medium-Intent Keywords (30-59)
        medium_intent_keywords = [
            'demo', 'free', 'trial', 'class', 'course structure',
            'subjects', 'covered', 'available', 'for class', 'for grade',
            'compare', 'difference', 'what subjects', 'what topics'
        ]
        
        # Low-Intent Keywords (0-29)
        low_intent_keywords = [
            'what is this', 'what do you offer', 'explain', 'solution',
            'doubt', 'chapter', 'how to', 'career', 'general'
        ]
        
        score = 0
        
        # Check for high-intent signals
        high_count = sum(1 for keyword in high_intent_keywords if keyword in text_lower)
        if high_count > 0:
            score = 60 + (high_count * 10)
        
        # Check for medium-intent signals
        medium_count = sum(1 for keyword in medium_intent_keywords if keyword in text_lower)
        if score < 30 and medium_count > 0:
            score = 30 + (medium_count * 8)
        
        # Cap at 100
        score = min(score, 100)
        
        # Determine category
        if score >= 60:
            category = "high"
        elif score >= 30:
            category = "medium"
        else:
            category = "low"
        
        return {"score": score, "category": category}
    
    def set_intent_score(
        self,
        db: Session,
        call_sid: str,
        intent_score: float,
        intent_category: str
    ) -> Optional[Call]:
        """Update intent score for a call"""
        call = self.get_call_by_sid(db, call_sid)
        if call:
            call.intent_score = intent_score
            call.intent_category = intent_category
            db.commit()
            db.refresh(call)
        return call
    
    def get_calls_by_intent(
        self,
        db: Session,
        intent_category: str,
        limit: int = 100
    ) -> list:
        """Get all calls filtered by intent category"""
        return db.query(Call).filter(
            Call.intent_category == intent_category
        ).order_by(Call.created_at.desc()).limit(limit).all()
    
    def get_intent_stats(self, db: Session) -> dict:
        """Get intent distribution statistics (legacy - enrollment only)"""
        total = db.query(Call).count()
        high = db.query(Call).filter(Call.intent_category == "high").count()
        medium = db.query(Call).filter(Call.intent_category == "medium").count()
        low = db.query(Call).filter(Call.intent_category == "low").count()
        
        return {
            "total": total,
            "high": high,
            "medium": medium,
            "low": low,
            "high_percentage": (high / total * 100) if total > 0 else 0,
            "medium_percentage": (medium / total * 100) if total > 0 else 0,
            "low_percentage": (low / total * 100) if total > 0 else 0
        }
    
    def get_intent_stats_by_type(self, db: Session, intent_type: str) -> dict:
        """Get intent distribution statistics for a specific intent type"""
        total = db.query(Call).filter(Call.intent_type == intent_type).count()
        high = db.query(Call).filter(Call.intent_type == intent_type, Call.intent_category == "high").count()
        medium = db.query(Call).filter(Call.intent_type == intent_type, Call.intent_category == "medium").count()
        low = db.query(Call).filter(Call.intent_type == intent_type, Call.intent_category == "low").count()
        
        return {
            "intent_type": intent_type,
            "total": total,
            "high": high,
            "medium": medium,
            "low": low,
            "high_percentage": (high / total * 100) if total > 0 else 0,
            "medium_percentage": (medium / total * 100) if total > 0 else 0,
            "low_percentage": (low / total * 100) if total > 0 else 0
        }
    
    def get_all_intent_breakdown(self, db: Session) -> dict:
        """Get statistics for all intent types"""
        return {
            "enrollment": self.get_intent_stats_by_type(db, "enrollment"),
            "academic_doubt": self.get_intent_stats_by_type(db, "academic_doubt"),
            "refund": self.get_intent_stats_by_type(db, "refund")
        }


# Singleton instance
call_service = CallService()
