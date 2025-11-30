"""
WhatsApp Notifications Service
Sends notifications via Twilio WhatsApp API.
"""

from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import os
from twilio.rest import Client


class WhatsAppMessage(BaseModel):
    """WhatsApp message to send."""
    to_phone: str  # Must include country code
    message: str
    from_phone: Optional[str] = None


class WhatsAppService:
    """
    WhatsApp notification service using Twilio.
    """
    
    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
        dry_run: bool = False
    ):
        """
        Initialize WhatsApp service.
        
        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            from_number: Twilio WhatsApp number (format: whatsapp:+14155238886)
            dry_run: If True, only log messages instead of sending
        """
        self.dry_run = dry_run or (os.getenv("APP_ENV") == "test")
        
        if not self.dry_run:
            self.client = Client(
                account_sid or os.getenv("TWILIO_ACCOUNT_SID"),
                auth_token or os.getenv("TWILIO_AUTH_TOKEN")
            )
            
            # Format WhatsApp number
            from_num = from_number or os.getenv("TWILIO_WHATSAPP_NUMBER")
            if from_num and not from_num.startswith("whatsapp:"):
                from_num = f"whatsapp:{from_num}"
            
            self.from_number = from_num
        else:
            self.client = None
            self.from_number = "whatsapp:+1234567890"
    
    def send_message(
        self,
        to_phone: str,
        message: str
    ) -> dict:
        """
        Send WhatsApp message.
        
        Args:
            to_phone: Recipient phone (format: +919876543210)
            message: Message text
            
        Returns:
            Result dict with status and details
        """
        # Format recipient number
        if not to_phone.startswith("whatsapp:"):
            to_phone = f"whatsapp:{to_phone}"
        
        if self.dry_run:
            # Log only in dry-run mode
            print(f"\n{'='*60}")
            print(f"📱 [DRY RUN] WhatsApp Message")
            print(f"{'='*60}")
            print(f"From: {self.from_number}")
            print(f"To: {to_phone}")
            print(f"Message:\n{message}")
            print(f"{'='*60}\n")
            
            return {
                "status": "dry_run",
                "to": to_phone,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            # Send via Twilio
            result = self.client.messages.create(
                from_=self.from_number,
                to=to_phone,
                body=message
            )
            
            print(f"✅ WhatsApp sent to {to_phone}: SID={result.sid}")
            
            return {
                "status": "sent",
                "sid": result.sid,
                "to": to_phone,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Failed to send WhatsApp to {to_phone}: {e}")
            
            return {
                "status": "failed",
                "to": to_phone,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def send_booking_confirmation(
        self,
        customer_name: str,
        customer_phone: str,
        appointment_date: str,
        appointment_time: str,
        business_name: str
    ) -> dict:
        """Send booking confirmation message."""
        message = f"""Hi {customer_name}! 👋

Your appointment is confirmed:
📅 Date: {appointment_date}
⏰ Time: {appointment_time}

Thank you for choosing {business_name}!

If you need to reschedule, please call us.
"""
        
        return self.send_message(customer_phone, message)
    
    def send_urgent_alert(
        self,
        owner_phone: str,
        caller_phone: str,
        issue_summary: str,
        business_name: str
    ) -> dict:
        """Send urgent issue alert to owner."""
        message = f"""🚨 URGENT: New escalation from Zylin

Caller: {caller_phone}
Issue: {issue_summary}

Please follow up immediately.

- {business_name} via Zylin AI
"""
        
        return self.send_message(owner_phone, message)


# Message templates
class MessageTemplates:
    """Pre-defined message templates."""
    
    @staticmethod
    def booking_confirmation(
        customer_name: str,
        date: str,
        time: str,
        business_name: str
    ) -> str:
        return f"""Hi {customer_name}! 👋

Your appointment is confirmed:
📅 {date}
⏰ {time}

See you then!
- {business_name}"""
    
    @staticmethod
    def booking_reminder(
        customer_name: str,
        date: str,
        time: str,
        business_name: str
    ) -> str:
        return f"""Hi {customer_name},

Reminder: Your appointment is tomorrow!
📅 {date}
⏰ {time}

Looking forward to seeing you.
- {business_name}"""
    
    @staticmethod
    def urgent_alert(
        caller_phone: str,
        issue: str
    ) -> str:
        return f"""🚨 URGENT

Caller: {caller_phone}
Issue: {issue}

Please follow up ASAP."""
