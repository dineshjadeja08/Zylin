"""
Twilio Webhook Endpoints
Handle incoming calls and recordings from Twilio.
"""

from fastapi import APIRouter, Request, Form, HTTPException, BackgroundTasks
from fastapi.responses import Response
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import httpx
import os

from services.orchestrator.session_manager import ConversationOrchestrator
from services.bookings.store import BookingTool
from services.notifications.whatsapp import WhatsAppService
from services.logging.log_store import CallLogStore, create_log_from_session

# Create router
router = APIRouter(prefix="/api/twilio", tags=["Twilio Webhooks"])

# Initialize services
orchestrator = ConversationOrchestrator()
booking_tool = BookingTool()
whatsapp_service = WhatsAppService()
log_store = CallLogStore()


class CallStatus(BaseModel):
    """Call status information from Twilio."""
    CallSid: str
    From: str
    To: str
    CallStatus: str
    RecordingUrl: Optional[str] = None


@router.post("/voice")
async def handle_incoming_call(
    CallSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    CallStatus: str = Form(...)
):
    """
    Handle incoming voice call from Twilio.
    
    This is the webhook URL you configure in Twilio:
    https://your-domain.com/api/twilio/voice
    
    TwiML response tells Twilio what to do with the call.
    """
    print(f"\n📞 Incoming call from {From} (SID: {CallSid})")
    
    # Create session for this call
    session = orchestrator.create_session(caller_phone=From)
    
    # Store session ID in a way we can retrieve it later
    # For MVP, we'll use CallSid as session mapping
    session_mapping[CallSid] = session.session_id
    
    # TwiML response to record the caller
    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">
        Hello! I'm Zylin, your AI receptionist. How can I help you today?
    </Say>
    <Record 
        action="/api/twilio/recording/{CallSid}"
        maxLength="30"
        playBeep="true"
        timeout="5"
        transcribe="false"
    />
    <Say voice="Polly.Joanna">
        I didn't receive a response. Please call back if you need assistance.
    </Say>
    <Hangup/>
</Response>"""
    
    return Response(content=twiml_response, media_type="application/xml")


# Session mapping (in production, use Redis or database)
session_mapping = {}


@router.post("/recording/{call_sid}")
async def handle_recording(
    call_sid: str,
    background_tasks: BackgroundTasks,
    RecordingUrl: str = Form(...),
    RecordingSid: str = Form(...),
    RecordingDuration: int = Form(...)
):
    """
    Handle recorded audio from caller.
    
    This webhook is called when Twilio finishes recording.
    We process the audio and generate a response.
    """
    print(f"\n🎤 Recording received for call {call_sid}")
    print(f"   URL: {RecordingUrl}")
    print(f"   Duration: {RecordingDuration}s")
    
    # Get session ID
    session_id = session_mapping.get(call_sid)
    if not session_id:
        print(f"❌ Session not found for call {call_sid}")
        return Response(content="<Response><Hangup/></Response>", media_type="application/xml")
    
    # Process recording in background
    background_tasks.add_task(
        process_recording_and_respond,
        recording_url=RecordingUrl,
        session_id=session_id,
        call_sid=call_sid
    )
    
    # Immediate TwiML response (tell caller we're processing)
    twiml_response = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">
        Thank you. Let me help you with that.
    </Say>
    <Pause length="2"/>
    <Hangup/>
</Response>"""
    
    return Response(content=twiml_response, media_type="application/xml")


async def process_recording_and_respond(
    recording_url: str,
    session_id: str,
    call_sid: str
):
    """
    Background task to process recording and send response via WhatsApp.
    
    Flow:
    1. Download recording from Twilio
    2. Transcribe with ASR
    3. Process with LLM brain
    4. Take action (booking, escalation, etc.)
    5. Send response via WhatsApp
    6. Log the call
    """
    try:
        print(f"\n🔄 Processing recording for session {session_id}")
        
        # Get session
        session = orchestrator.get_session(session_id)
        if not session:
            print(f"❌ Session {session_id} not found")
            return
        
        # Step 1: Download recording
        print("📥 Downloading recording...")
        audio_data = await download_twilio_recording(recording_url)
        
        # Step 2: Transcribe
        print("🎤 Transcribing audio...")
        from services.asr.transcribe import ASRService
        asr = ASRService()
        transcription = await asr.transcribe_bytes(
            audio_data,
            filename="recording.wav"
        )
        user_text = transcription.text
        print(f"📝 User said: {user_text}")
        
        # Step 3: Process with brain
        print("🧠 Processing with Zylin brain...")
        result = await orchestrator.process_text_turn(user_text, session_id)
        
        print(f"📊 Intent: {result.intent}")
        print(f"🤖 Response: {result.bot_text}")
        
        # Step 4: Take actions based on intent
        booking_id = None
        
        if result.intent == "booking" and result.booking_complete:
            print("📅 Creating booking...")
            booking = booking_tool.create_booking_from_conversation(
                result.extracted_data,
                session_id
            )
            booking_id = booking.booking_id
            
            # Send WhatsApp confirmation
            whatsapp_service.send_booking_confirmation(
                customer_name=booking.customer_name,
                customer_phone=booking.customer_phone,
                appointment_date=booking.appointment_date,
                appointment_time=booking.appointment_time,
                business_name=os.getenv("BUSINESS_NAME", "Our Business")
            )
            
        elif result.intent == "urgent" and result.needs_escalation:
            print("🚨 Escalating to owner...")
            whatsapp_service.send_urgent_alert(
                owner_phone=os.getenv("OWNER_PHONE", "+919876543210"),
                caller_phone=session.caller_phone or "Unknown",
                issue_summary=result.extracted_data.get("issue_summary", "Urgent issue"),
                business_name=os.getenv("BUSINESS_NAME", "Our Business")
            )
        
        # Step 5: Send response via WhatsApp (for all intents)
        print("📱 Sending WhatsApp response...")
        if session.caller_phone:
            whatsapp_service.send_message(
                to_phone=session.caller_phone,
                message=result.bot_text
            )
        
        # Step 6: Log the call
        print("📝 Logging call...")
        session_data = orchestrator.get_session_summary(session_id)
        log = create_log_from_session(
            session_data,
            booking_id=booking_id,
            summary=f"{result.intent} - {user_text[:50]}"
        )
        log_store.create_log(log)
        
        print(f"✅ Call processing complete for {call_sid}")
        
    except Exception as e:
        print(f"❌ Error processing recording: {e}")
        import traceback
        traceback.print_exc()
        
        # Send error notification to owner
        try:
            whatsapp_service.send_message(
                to_phone=os.getenv("OWNER_PHONE", "+919876543210"),
                message=f"⚠️ Error processing call {call_sid}: {str(e)}"
            )
        except:
            pass


async def download_twilio_recording(recording_url: str) -> bytes:
    """Download recording from Twilio."""
    # Twilio recordings need authentication
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    # Add .wav to get WAV format
    if not recording_url.endswith(".wav"):
        recording_url += ".wav"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            recording_url,
            auth=(account_sid, auth_token)
        )
        response.raise_for_status()
        return response.content


@router.post("/status")
async def handle_call_status(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    From: str = Form(...),
    To: str = Form(...)
):
    """
    Handle call status updates from Twilio.
    
    Useful for tracking call completion, duration, etc.
    """
    print(f"📊 Call status update: {CallSid} - {CallStatus}")
    
    # Log status changes
    # In production, update call logs with final status
    
    return Response(content="OK")


@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoint."""
    return {
        "status": "healthy",
        "service": "Twilio Webhooks",
        "endpoints": [
            "/api/twilio/voice",
            "/api/twilio/recording/{call_sid}",
            "/api/twilio/status"
        ]
    }
