"""
Streaming Pipeline for Real-Time Conversations
Orchestrates ASR → LLM → TTS flow for low-latency phone calls.
"""

import asyncio
from typing import Optional, AsyncGenerator, Dict
from datetime import datetime
import time
import os

from services.asr.transcribe import StreamingASRService, MockStreamingASR
from services.llm.brain import ZylinBrain, BusinessContext
from services.tts.synthesize import StreamingTTSService, MockStreamingTTS
from services.utils.audio_codec import AudioCodec, AudioBuffer
from services.bookings.store import BookingTool
from services.notifications.whatsapp import WhatsAppService
from services.logging.log_store import CallLogStore, CallLog


class StreamingSession:
    """
    Represents a single streaming conversation session.
    """
    
    def __init__(
        self,
        session_id: str,
        caller_phone: Optional[str] = None,
        stream_sid: Optional[str] = None
    ):
        """
        Initialize streaming session.
        
        Args:
            session_id: Unique session identifier
            caller_phone: Caller's phone number
            stream_sid: Twilio stream SID
        """
        self.session_id = session_id
        self.caller_phone = caller_phone
        self.stream_sid = stream_sid
        self.created_at = datetime.now()
        self.conversation_history = []  # List of {role, content, timestamp}
        self.audio_buffer = AudioBuffer(max_duration_ms=10000)  # 10 seconds max
        self.is_active = True
        self.latency_metrics = []  # Track latency for each turn
    
    def add_message(self, role: str, content: str) -> None:
        """Add message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now()
        })
    
    def get_conversation_for_llm(self) -> list[dict]:
        """Get conversation history formatted for LLM."""
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in self.conversation_history
        ]
    
    def add_latency_metric(self, metric_name: str, duration_ms: float) -> None:
        """Track latency for monitoring."""
        self.latency_metrics.append({
            "metric": metric_name,
            "duration_ms": duration_ms,
            "timestamp": datetime.now()
        })


class StreamingPipeline:
    """
    Real-time conversation pipeline.
    
    Handles the complete flow:
    1. Receive audio chunks from Twilio WebSocket
    2. Buffer and transcribe with streaming ASR
    3. Process with LLM brain
    4. Generate audio response with streaming TTS
    5. Send audio back to Twilio WebSocket
    """
    
    def __init__(
        self,
        use_mock_services: bool = False,
        max_latency_target_ms: float = 3000  # 3 second target
    ):
        """
        Initialize streaming pipeline.
        
        Args:
            use_mock_services: Use mock ASR/TTS for testing without API costs
            max_latency_target_ms: Target max latency (for monitoring)
        """
        self.use_mock_services = use_mock_services
        self.max_latency_target_ms = max_latency_target_ms
        
        # Initialize services
        if use_mock_services:
            self.asr = MockStreamingASR()
            self.tts = MockStreamingTTS()
        else:
            # Check for Deepgram key
            if os.getenv("DEEPGRAM_API_KEY"):
                self.asr = StreamingASRService()
            else:
                print("⚠️  No DEEPGRAM_API_KEY found, using mock ASR")
                self.asr = MockStreamingASR()
            
            self.tts = StreamingTTSService()
        
        self.brain = ZylinBrain()
        self.booking_tool = BookingTool()
        self.whatsapp_service = WhatsAppService()
        self.log_store = CallLogStore()
        
        # Active sessions
        self.sessions: Dict[str, StreamingSession] = {}
    
    def create_session(
        self,
        session_id: str,
        caller_phone: Optional[str] = None,
        stream_sid: Optional[str] = None
    ) -> StreamingSession:
        """Create new streaming session."""
        session = StreamingSession(session_id, caller_phone, stream_sid)
        self.sessions[session_id] = session
        print(f"📞 Created streaming session: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[StreamingSession]:
        """Get existing session."""
        return self.sessions.get(session_id)
    
    def close_session(self, session_id: str) -> None:
        """Close and clean up session."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.is_active = False
            
            # Log the call
            self._log_call(session)
            
            del self.sessions[session_id]
            print(f"📞 Closed streaming session: {session_id}")
    
    async def process_call_stream(
        self,
        session_id: str,
        audio_input_stream: AsyncGenerator[bytes, None],
        audio_output_queue: asyncio.Queue
    ) -> None:
        """
        Process complete call stream.
        
        This is the main pipeline that runs for the duration of the call.
        
        Args:
            session_id: Session identifier
            audio_input_stream: Incoming audio chunks (PCM from Twilio)
            audio_output_queue: Queue to send outgoing audio chunks
        """
        session = self.get_session(session_id)
        if not session:
            print(f"❌ Session not found: {session_id}")
            return
        
        try:
            print(f"\n🎙️  Starting streaming pipeline for session {session_id}")
            
            # Process audio turns until call ends
            async for transcript, is_final in self.asr.transcribe_stream(
                audio_input_stream,
                language="en",
                interim_results=False  # Only final results
            ):
                if not is_final:
                    continue  # Skip interim results
                
                print(f"\n📝 User said: {transcript}")
                
                # Process this utterance
                await self._process_utterance(
                    session,
                    transcript,
                    audio_output_queue
                )
        
        except Exception as e:
            print(f"❌ Error in streaming pipeline: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Clean up
            self.close_session(session_id)
    
    async def _process_utterance(
        self,
        session: StreamingSession,
        transcript: str,
        audio_output_queue: asyncio.Queue
    ) -> None:
        """
        Process a single user utterance through the pipeline.
        
        Flow: Transcript → LLM → TTS → Audio Output
        """
        start_time = time.time()
        
        # Add user message to history
        session.add_message("user", transcript)
        
        # Step 1: Process with LLM (with timing)
        llm_start = time.time()
        
        conversation_history = session.get_conversation_for_llm()
        response = await self.brain.process_message(transcript, conversation_history)
        
        llm_duration = (time.time() - llm_start) * 1000
        session.add_latency_metric("llm_processing", llm_duration)
        
        print(f"🧠 LLM response ({llm_duration:.0f}ms): {response.reply[:80]}...")
        print(f"📊 Intent: {response.intent}, Booking: {response.booking_complete}, Urgent: {response.needs_escalation}")
        
        # Add assistant message to history
        session.add_message("assistant", response.reply)
        
        # Step 2: Handle actions (bookings, escalations)
        await self._handle_actions(session, response)
        
        # Step 3: Generate and stream audio response
        tts_start = time.time()
        
        # Create text stream from LLM response (simulate streaming)
        async def text_stream():
            yield response.reply
        
        # Generate audio chunks
        audio_chunks_sent = 0
        async for audio_chunk in self.tts.synthesize_stream_for_twilio(text_stream()):
            # Convert to μ-law and enqueue
            mulaw_base64 = AudioCodec.encode_pcm_to_mulaw_base64(audio_chunk)
            await audio_output_queue.put({
                "event": "media",
                "media": {
                    "payload": mulaw_base64
                }
            })
            audio_chunks_sent += 1
        
        tts_duration = (time.time() - tts_start) * 1000
        session.add_latency_metric("tts_generation", tts_duration)
        
        # Total latency
        total_duration = (time.time() - start_time) * 1000
        session.add_latency_metric("end_to_end", total_duration)
        
        print(f"🔊 Audio sent ({audio_chunks_sent} chunks, TTS: {tts_duration:.0f}ms)")
        print(f"⏱️  Total latency: {total_duration:.0f}ms (target: {self.max_latency_target_ms}ms)")
        
        # Warn if over latency target
        if total_duration > self.max_latency_target_ms:
            print(f"⚠️  Latency exceeded target by {total_duration - self.max_latency_target_ms:.0f}ms")
    
    async def _handle_actions(self, session: StreamingSession, response) -> None:
        """
        Handle bookings, escalations, and other actions.
        """
        # Handle booking
        if response.intent == "booking" and response.booking_complete:
            print("📅 Creating booking...")
            try:
                booking = self.booking_tool.create_booking_from_conversation(
                    response.extracted_data,
                    session.session_id
                )
                
                # Send WhatsApp confirmation
                if session.caller_phone:
                    self.whatsapp_service.send_booking_confirmation(
                        customer_name=booking.customer_name,
                        customer_phone=booking.customer_phone,
                        appointment_date=booking.appointment_date,
                        appointment_time=booking.appointment_time,
                        business_name=os.getenv("BUSINESS_NAME", "Our Business")
                    )
            except Exception as e:
                print(f"❌ Error creating booking: {e}")
        
        # Handle urgent escalation
        elif response.intent == "urgent" and response.needs_escalation:
            print("🚨 Escalating to owner...")
            try:
                self.whatsapp_service.send_urgent_alert(
                    owner_phone=os.getenv("OWNER_PHONE", "+919876543210"),
                    caller_phone=session.caller_phone or "Unknown",
                    issue_summary=response.extracted_data.get("issue_summary", "Urgent issue"),
                    business_name=os.getenv("BUSINESS_NAME", "Our Business")
                )
            except Exception as e:
                print(f"❌ Error sending alert: {e}")
    
    def _log_call(self, session: StreamingSession) -> None:
        """
        Log completed call to database.
        """
        try:
            # Calculate average latency
            if session.latency_metrics:
                avg_latency = sum(
                    m["duration_ms"] for m in session.latency_metrics 
                    if m["metric"] == "end_to_end"
                ) / len([m for m in session.latency_metrics if m["metric"] == "end_to_end"])
            else:
                avg_latency = 0
            
            # Determine intent from last message
            intent = "other"
            if len(session.conversation_history) > 0:
                # Simplistic: look for keywords
                last_user_msg = next(
                    (m["content"] for m in reversed(session.conversation_history) if m["role"] == "user"),
                    ""
                )
                if "appointment" in last_user_msg.lower() or "book" in last_user_msg.lower():
                    intent = "booking"
                elif "urgent" in last_user_msg.lower() or "emergency" in last_user_msg.lower():
                    intent = "urgent"
                elif "hours" in last_user_msg.lower() or "location" in last_user_msg.lower():
                    intent = "faq"
            
            log = CallLog(
                session_id=session.session_id,
                caller_phone=session.caller_phone,
                timestamp=session.created_at.isoformat(),
                intent=intent,
                transcript=session.conversation_history,
                summary=f"Streaming call, {len(session.conversation_history)} messages, avg latency {avg_latency:.0f}ms"
            )
            
            self.log_store.create_log(log)
            print(f"📝 Call logged: {session.session_id}")
        
        except Exception as e:
            print(f"❌ Error logging call: {e}")
    
    async def send_greeting(
        self,
        session_id: str,
        audio_output_queue: asyncio.Queue
    ) -> None:
        """
        Send initial greeting to caller.
        
        This is called when the call first connects.
        """
        session = self.get_session(session_id)
        if not session:
            return
        
        greeting = "Hello! I'm Zylin, your AI receptionist. How can I help you today?"
        
        # Add to conversation history
        session.add_message("assistant", greeting)
        
        # Generate audio
        async def text_stream():
            yield greeting
        
        print(f"👋 Sending greeting: {greeting}")
        
        async for audio_chunk in self.tts.synthesize_stream_for_twilio(text_stream()):
            mulaw_base64 = AudioCodec.encode_pcm_to_mulaw_base64(audio_chunk)
            await audio_output_queue.put({
                "event": "media",
                "media": {
                    "payload": mulaw_base64
                }
            })
        
        print("✅ Greeting sent")


# Example usage for testing
if __name__ == "__main__":
    async def test_pipeline():
        """Test the streaming pipeline with mock data."""
        print("Testing Streaming Pipeline\n")
        
        # Create pipeline with mock services
        pipeline = StreamingPipeline(use_mock_services=True)
        
        # Create session
        session = pipeline.create_session(
            session_id="test-123",
            caller_phone="+919876543210"
        )
        
        # Create mock audio stream (silence)
        async def mock_audio_stream():
            # Simulate 2 seconds of audio
            for _ in range(100):  # 100 chunks of 20ms each
                chunk = b'\x00\x00' * 160  # 20ms of silence at 8kHz
                yield chunk
                await asyncio.sleep(0.02)
        
        # Create output queue
        output_queue = asyncio.Queue()
        
        # Process the stream
        await pipeline.process_call_stream(
            "test-123",
            mock_audio_stream(),
            output_queue
        )
        
        # Check output
        print(f"\n📊 Output queue size: {output_queue.qsize()}")
        
        print("\n✅ Pipeline test complete!")
    
    # Run test
    asyncio.run(test_pipeline())
