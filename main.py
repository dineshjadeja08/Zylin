"""
FastAPI main application for Zylin.
Provides REST API endpoints for conversation management.
Includes WebSocket support for real-time streaming calls.
"""

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import os
import json
import asyncio
import uuid
from contextlib import asynccontextmanager

from services.llm.brain import ZylinBrain, ConversationResponse
from services.orchestrator.streaming_pipeline import StreamingPipeline
from services.utils.audio_codec import AudioCodec
from api.twilio_webhook import router as twilio_router

# App metadata
APP_TITLE = "Zylin AI Receptionist"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = """
Zylin is an AI-powered receptionist for small and medium businesses.
It handles phone calls, answers FAQs, books appointments, and escalates urgent matters.
"""


# Request/Response Models
class ConversationMessage(BaseModel):
    """Single message in a conversation."""
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ConversationRequest(BaseModel):
    """Request to process a conversation message."""
    message: str = Field(..., description="User's message", min_length=1)
    conversation_history: Optional[List[ConversationMessage]] = Field(
        default=None,
        description="Previous messages in the conversation"
    )
    caller_phone: Optional[str] = Field(
        default=None,
        description="Caller's phone number (for context)"
    )


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    service: str


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    print(f"🚀 Starting {APP_TITLE} v{APP_VERSION}")
    print(f"📝 Environment: {os.getenv('APP_ENV', 'development')}")
    
    # Initialize global brain instance
    app.state.brain = ZylinBrain()
    print("🧠 LLM Brain initialized")
    
    # Initialize streaming pipeline
    use_mock = os.getenv("USE_MOCK_STREAMING", "false").lower() == "true"
    app.state.streaming_pipeline = StreamingPipeline(use_mock_services=use_mock)
    print(f"🎙️  Streaming pipeline initialized (mock: {use_mock})")
    
    yield
    
    # Shutdown
    print("👋 Shutting down Zylin")


# Create FastAPI app
app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    lifespan=lifespan
)

# CORS middleware (adjust origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Twilio webhook router
app.include_router(twilio_router)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    print(f"❌ Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again."
        }
    )


# Routes
@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check."""
    return HealthResponse(
        status="healthy",
        version=APP_VERSION,
        service=APP_TITLE
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=APP_VERSION,
        service=APP_TITLE
    )


@app.post("/conversation", response_model=ConversationResponse)
async def process_conversation(request: ConversationRequest):
    """
    Process a conversation message and return structured response.
    
    This is the main endpoint for text-based interaction with Zylin.
    
    Args:
        request: ConversationRequest with message and optional history
        
    Returns:
        ConversationResponse with intent, message, and extracted data
    """
    try:
        brain: ZylinBrain = app.state.brain
        
        # Convert history to dict format
        history = None
        if request.conversation_history:
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]
        
        # Process message
        response = await brain.process_message(
            user_message=request.message,
            conversation_history=history
        )
        
        return response
        
    except Exception as e:
        print(f"❌ Error processing conversation: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process conversation"
        )


@app.post("/conversation/summary")
async def get_conversation_summary(
    conversation_history: List[ConversationMessage]
):
    """
    Generate a summary of a conversation.
    
    Useful for logging and analytics.
    """
    try:
        brain: ZylinBrain = app.state.brain
        
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in conversation_history
        ]
        
        summary = await brain.get_conversation_summary(history)
        
        return {"summary": summary}
        
    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate conversation summary"
        )


@app.get("/business")
async def get_business_info():
    """Get business context information."""
    brain: ZylinBrain = app.state.brain
    return brain.business_context.model_dump()


@app.websocket("/media-stream")
async def websocket_media_stream(websocket: WebSocket):
    """
    WebSocket endpoint for Twilio Media Streams.
    
    Handles real-time bidirectional audio streaming:
    - Receives audio chunks from Twilio
    - Processes through ASR → LLM → TTS pipeline
    - Sends audio response back to Twilio
    
    Message format from Twilio:
    {
        "event": "start|media|stop",
        "streamSid": "...",
        "media": {"payload": "base64-encoded-mulaw"},
        "customParameters": {...}
    }
    """
    await websocket.accept()
    print("\n🔌 WebSocket connection established")
    
    # Get streaming pipeline
    pipeline: StreamingPipeline = app.state.streaming_pipeline
    
    # Session state
    session_id = None
    stream_sid = None
    caller_phone = None
    audio_queue = asyncio.Queue()  # Queue for outgoing audio
    
    # Audio input buffer
    audio_input_queue = asyncio.Queue()
    
    try:
        # Task for sending audio back to Twilio
        async def send_audio_to_twilio():
            """Background task to send audio chunks to Twilio."""
            while True:
                try:
                    # Get audio message from queue
                    message = await audio_queue.get()
                    
                    if message is None:  # Shutdown signal
                        break
                    
                    # Add stream SID
                    message["streamSid"] = stream_sid
                    
                    # Send to Twilio
                    await websocket.send_json(message)
                    
                except Exception as e:
                    print(f"❌ Error sending audio: {e}")
                    break
        
        # Audio stream generator for ASR
        async def audio_stream_generator():
            """Generate audio stream from incoming chunks."""
            while True:
                chunk = await audio_input_queue.get()
                if chunk is None:  # End signal
                    break
                yield chunk
        
        # Start audio sender task
        sender_task = None
        pipeline_task = None
        
        # Main message loop
        while True:
            # Receive message from Twilio
            message_text = await websocket.receive_text()
            message = json.loads(message_text)
            
            event = message.get("event")
            
            if event == "start":
                # Stream started
                stream_sid = message["streamSid"]
                call_sid = message["start"].get("callSid")
                custom_params = message["start"].get("customParameters", {})
                caller_phone = custom_params.get("callerPhone")
                
                print(f"📞 Stream started: {stream_sid}")
                print(f"   Call SID: {call_sid}")
                print(f"   Caller: {caller_phone}")
                
                # Create session
                session_id = str(uuid.uuid4())
                pipeline.create_session(
                    session_id=session_id,
                    caller_phone=caller_phone,
                    stream_sid=stream_sid
                )
                
                # Start audio sender task
                sender_task = asyncio.create_task(send_audio_to_twilio())
                
                # Send greeting
                await pipeline.send_greeting(session_id, audio_queue)
                
                # Start pipeline processing task
                pipeline_task = asyncio.create_task(
                    pipeline.process_call_stream(
                        session_id,
                        audio_stream_generator(),
                        audio_queue
                    )
                )
            
            elif event == "media":
                # Audio chunk received
                if session_id is None:
                    continue  # Not ready yet
                
                # Decode μ-law audio
                payload = message["media"]["payload"]
                pcm_audio = AudioCodec.decode_mulaw_base64(payload)
                
                # Add to input queue for ASR
                await audio_input_queue.put(pcm_audio)
            
            elif event == "stop":
                # Stream stopped
                print(f"📞 Stream stopped: {stream_sid}")
                
                # Signal end of audio input
                await audio_input_queue.put(None)
                
                # Wait for pipeline to finish
                if pipeline_task:
                    try:
                        await asyncio.wait_for(pipeline_task, timeout=5.0)
                    except asyncio.TimeoutError:
                        print("⚠️  Pipeline task timeout")
                        pipeline_task.cancel()
                
                # Signal sender to stop
                await audio_queue.put(None)
                
                # Wait for sender to finish
                if sender_task:
                    try:
                        await asyncio.wait_for(sender_task, timeout=2.0)
                    except asyncio.TimeoutError:
                        print("⚠️  Sender task timeout")
                        sender_task.cancel()
                
                break
    
    except WebSocketDisconnect:
        print("🔌 WebSocket disconnected")
    
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if session_id and pipeline:
            try:
                pipeline.close_session(session_id)
            except:
                pass
        
        # Cancel tasks
        if sender_task and not sender_task.done():
            sender_task.cancel()
        if pipeline_task and not pipeline_task.done():
            pipeline_task.cancel()
        
        print("🔌 WebSocket connection closed")


if __name__ == "__main__":
    import uvicorn
    
    # Run server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
