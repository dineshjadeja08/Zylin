"""
Bookings Service
Manages appointment bookings with SQLite storage.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import sqlite3
from pathlib import Path
import json


class Booking(BaseModel):
    """Appointment booking model."""
    booking_id: Optional[int] = None
    customer_name: str
    customer_phone: str
    appointment_date: str  # YYYY-MM-DD
    appointment_time: str  # HH:MM
    notes: Optional[str] = None
    status: str = "confirmed"  # confirmed, cancelled, completed
    created_at: Optional[str] = None
    session_id: Optional[str] = None


class BookingStore:
    """
    SQLite-based storage for bookings.
    Simple CRUD operations for MVP.
    """
    
    def __init__(self, db_path: str = "data/zylin.db"):
        """Initialize booking store."""
        self.db_path = db_path
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Create bookings table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT NOT NULL,
                    customer_phone TEXT NOT NULL,
                    appointment_date TEXT NOT NULL,
                    appointment_time TEXT NOT NULL,
                    notes TEXT,
                    status TEXT DEFAULT 'confirmed',
                    created_at TEXT NOT NULL,
                    session_id TEXT
                )
            """)
            conn.commit()
    
    def create_booking(self, booking: Booking) -> Booking:
        """
        Create a new booking.
        
        Args:
            booking: Booking data (booking_id will be auto-assigned)
            
        Returns:
            Booking with assigned booking_id
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO bookings (
                    customer_name, customer_phone, appointment_date,
                    appointment_time, notes, status, created_at, session_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                booking.customer_name,
                booking.customer_phone,
                booking.appointment_date,
                booking.appointment_time,
                booking.notes,
                booking.status,
                datetime.now().isoformat(),
                booking.session_id
            ))
            conn.commit()
            booking.booking_id = cursor.lastrowid
            booking.created_at = datetime.now().isoformat()
        
        return booking
    
    def get_booking(self, booking_id: int) -> Optional[Booking]:
        """Get a booking by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM bookings WHERE booking_id = ?",
                (booking_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return Booking(**dict(row))
            return None
    
    def list_bookings(
        self,
        status: Optional[str] = None,
        date: Optional[str] = None,
        limit: int = 100
    ) -> List[Booking]:
        """
        List bookings with optional filters.
        
        Args:
            status: Filter by status
            date: Filter by appointment date (YYYY-MM-DD)
            limit: Maximum number of results
            
        Returns:
            List of bookings
        """
        query = "SELECT * FROM bookings WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if date:
            query += " AND appointment_date = ?"
            params.append(date)
        
        query += " ORDER BY appointment_date, appointment_time LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [Booking(**dict(row)) for row in rows]
    
    def update_booking_status(
        self,
        booking_id: int,
        status: str
    ) -> Optional[Booking]:
        """Update booking status."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE bookings SET status = ? WHERE booking_id = ?",
                (status, booking_id)
            )
            conn.commit()
        
        return self.get_booking(booking_id)
    
    def delete_booking(self, booking_id: int) -> bool:
        """Delete a booking."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM bookings WHERE booking_id = ?",
                (booking_id,)
            )
            conn.commit()
            return cursor.rowcount > 0


# Booking tool for LLM
class BookingTool:
    """
    Tool that LLM orchestrator can call to create bookings.
    Acts as bridge between conversation and database.
    """
    
    def __init__(self, store: Optional[BookingStore] = None):
        """Initialize booking tool."""
        self.store = store or BookingStore()
    
    def can_create_booking(self, booking_data: dict) -> tuple[bool, Optional[str]]:
        """
        Check if booking has all required fields.
        
        Returns:
            (is_valid, error_message)
        """
        required = ["name", "phone", "date", "time"]
        missing = [f for f in required if not booking_data.get(f)]
        
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
        
        return True, None
    
    def create_booking_from_conversation(
        self,
        booking_data: dict,
        session_id: Optional[str] = None
    ) -> Booking:
        """
        Create booking from conversation extracted data.
        
        Args:
            booking_data: Dict with name, phone, date, time, notes
            session_id: Conversation session ID
            
        Returns:
            Created booking
        """
        booking = Booking(
            customer_name=booking_data["name"],
            customer_phone=booking_data["phone"],
            appointment_date=booking_data["date"],
            appointment_time=booking_data["time"],
            notes=booking_data.get("notes"),
            session_id=session_id
        )
        
        return self.store.create_booking(booking)
