"""
Call Logging Service
Stores conversation logs and metadata for analytics.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime, date
import sqlite3
from pathlib import Path
import json


class CallLog(BaseModel):
    """Call log record."""
    log_id: Optional[int] = None
    session_id: str
    caller_phone: Optional[str] = None
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[int] = None
    intent: Optional[str] = None
    transcript: Optional[str] = None  # Full conversation as JSON
    summary: Optional[str] = None
    booking_created: bool = False
    booking_id: Optional[int] = None
    escalated: bool = False
    status: str = "completed"  # completed, failed, abandoned


class CallLogStore:
    """
    SQLite-based storage for call logs.
    """
    
    def __init__(self, db_path: str = "data/zylin.db"):
        """Initialize call log store."""
        self.db_path = db_path
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Create call_logs table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS call_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL UNIQUE,
                    caller_phone TEXT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_seconds INTEGER,
                    intent TEXT,
                    transcript TEXT,
                    summary TEXT,
                    booking_created INTEGER DEFAULT 0,
                    booking_id INTEGER,
                    escalated INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'completed'
                )
            """)
            conn.commit()
    
    def create_log(self, log: CallLog) -> CallLog:
        """Create a new call log."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO call_logs (
                    session_id, caller_phone, start_time, end_time,
                    duration_seconds, intent, transcript, summary,
                    booking_created, booking_id, escalated, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log.session_id,
                log.caller_phone,
                log.start_time,
                log.end_time,
                log.duration_seconds,
                log.intent,
                log.transcript,
                log.summary,
                1 if log.booking_created else 0,
                log.booking_id,
                1 if log.escalated else 0,
                log.status
            ))
            conn.commit()
            log.log_id = cursor.lastrowid
        
        return log
    
    def get_log(self, session_id: str) -> Optional[CallLog]:
        """Get log by session ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM call_logs WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return CallLog(**dict(row))
            return None
    
    def list_logs(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        intent: Optional[str] = None,
        limit: int = 100
    ) -> List[CallLog]:
        """List call logs with optional filters."""
        query = "SELECT * FROM call_logs WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND start_time >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND start_time <= ?"
            params.append(f"{end_date} 23:59:59")
        
        if intent:
            query += " AND intent = ?"
            params.append(intent)
        
        query += " ORDER BY start_time DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [CallLog(**dict(row)) for row in rows]
    
    def get_daily_stats(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for a specific date."""
        if not date_str:
            date_str = date.today().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total_calls,
                    SUM(CASE WHEN intent = 'faq' THEN 1 ELSE 0 END) as faq_count,
                    SUM(CASE WHEN intent = 'booking' THEN 1 ELSE 0 END) as booking_count,
                    SUM(CASE WHEN intent = 'urgent' THEN 1 ELSE 0 END) as urgent_count,
                    SUM(CASE WHEN booking_created = 1 THEN 1 ELSE 0 END) as bookings_created,
                    SUM(CASE WHEN escalated = 1 THEN 1 ELSE 0 END) as escalations,
                    AVG(duration_seconds) as avg_duration
                FROM call_logs
                WHERE DATE(start_time) = ?
            """, (date_str,))
            
            row = cursor.fetchone()
            
            return {
                "date": date_str,
                "total_calls": row[0] or 0,
                "faq_count": row[1] or 0,
                "booking_count": row[2] or 0,
                "urgent_count": row[3] or 0,
                "bookings_created": row[4] or 0,
                "escalations": row[5] or 0,
                "avg_duration_seconds": round(row[6], 1) if row[6] else 0
            }


# Helper to create log from session
def create_log_from_session(
    session: Dict[str, Any],
    booking_id: Optional[int] = None,
    summary: Optional[str] = None
) -> CallLog:
    """Create CallLog from conversation session data."""
    start_time = session.get("start_time")
    
    # Calculate duration if possible
    duration = None
    if start_time:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.now()
        duration = int((end_dt - start_dt).total_seconds())
    
    return CallLog(
        session_id=session["session_id"],
        caller_phone=session.get("caller_phone"),
        start_time=start_time or datetime.now().isoformat(),
        end_time=datetime.now().isoformat(),
        duration_seconds=duration,
        intent=session.get("intent"),
        transcript=json.dumps(session.get("conversation", [])),
        summary=summary,
        booking_created=booking_id is not None,
        booking_id=booking_id,
        escalated=session.get("intent") == "urgent",
        status="completed"
    )
