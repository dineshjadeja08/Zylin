"""
FastAPI main application for Zylin.
Provides REST API endpoints for conversation management.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import os
from contextlib import asynccontextmanager

from services.llm.brain import ZylinBrain, ConversationResponse
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
