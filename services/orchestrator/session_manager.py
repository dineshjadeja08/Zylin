"""
Conversation Orchestrator
Manages end-to-end conversation flow: ASR → LLM → TTS
"""

from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import BaseModel
from datetime import datetime
import uuid

from services.asr.transcribe import ASRService
from services.llm.brain import ZylinBrain, ConversationResponse
from services.tts.synthesize import TTSService, Voice


class ConversationSession(BaseModel):
    """A conversation session with a caller."""
    session_id: str
    caller_phone: Optional[str] = None
    start_time: datetime
    conversation_history: List[Dict[str, str]] = []
    intent: Optional[str] = None
    booking_data: Dict[str, Any] = {}
    completed: bool = False


class OrchestratorResult(BaseModel):
    """Result of orchestrating a conversation turn."""
    session_id: str
    user_text: str
    bot_text: str
    bot_audio_path: Optional[str] = None
    intent: str
    booking_complete: bool
    needs_escalation: bool
    extracted_data: Dict[str, Any]


class ConversationOrchestrator:
    """
    Orchestrates the full conversation pipeline:
    Audio → Text (ASR) → Brain (LLM) → Text → Audio (TTS)
    
    Manages session state, conversation history, and multi-turn flows.
    """
    
    def __init__(
        self,
        asr_service: Optional[ASRService] = None,
        brain: Optional[ZylinBrain] = None,
        tts_service: Optional[TTSService] = None,
        default_voice: Voice = "nova",
        generate_audio: bool = True
    ):
        """
        Initialize orchestrator.
        
        Args:
            asr_service: ASR service instance
            brain: LLM brain instance
            tts_service: TTS service instance
            default_voice: Default TTS voice
            generate_audio: Whether to generate TTS audio (disable for testing)
        """
        self.asr = asr_service or ASRService()
        self.brain = brain or ZylinBrain()
        self.tts = tts_service or TTSService(voice=default_voice)
        self.generate_audio = generate_audio
        
        # Active sessions
        self.sessions: Dict[str, ConversationSession] = {}
    
    def create_session(
        self,
        caller_phone: Optional[str] = None
    ) -> ConversationSession:
        """Create a new conversation session."""
        session_id = str(uuid.uuid4())
        
        session = ConversationSession(
            session_id=session_id,
            caller_phone=caller_phone,
            start_time=datetime.now(),
            conversation_history=[],
            booking_data={}
        )
        
        self.sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get an existing session."""
        return self.sessions.get(session_id)
    
    async def process_audio_turn(
        self,
        audio_file_path: str,
        session_id: str,
        output_audio_dir: str = "tests/tts"
    ) -> OrchestratorResult:
        """
        Process a complete conversation turn from audio input.
        
        Flow:
        1. Transcribe audio (ASR)
        2. Process with LLM brain
        3. Generate response audio (TTS)
        4. Update session state
        
        Args:
            audio_file_path: Path to caller's audio
            session_id: Session ID
            output_audio_dir: Where to save response audio
            
        Returns:
            OrchestratorResult with full turn data
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Step 1: Transcribe audio (ASR)
        print(f"🎤 Transcribing audio...")
        transcription = await self.asr.transcribe_file(audio_file_path)
        user_text = transcription.text
        print(f"📝 User said: {user_text}")
        
        # Step 2: Process with brain (LLM)
        response = await self.process_text_turn(user_text, session_id)
        
        # Step 3: Generate audio response (TTS)
        bot_audio_path = None
        if self.generate_audio:
            print(f"🔊 Generating audio response...")
            output_path = Path(output_audio_dir) / f"{session_id}_{len(session.conversation_history)}.mp3"
            tts_result = await self.tts.synthesize_to_file(
                response.bot_text,
                str(output_path)
            )
            bot_audio_path = tts_result.audio_file_path
            print(f"✅ Audio saved: {bot_audio_path}")
        
        return OrchestratorResult(
            session_id=session_id,
            user_text=user_text,
            bot_text=response.bot_text,
            bot_audio_path=bot_audio_path,
            intent=response.intent,
            booking_complete=response.booking_complete,
            needs_escalation=response.needs_escalation,
            extracted_data=response.extracted_data
        )
    
    async def process_text_turn(
        self,
        user_text: str,
        session_id: str
    ) -> OrchestratorResult:
        """
        Process a conversation turn from text input (skips ASR/TTS).
        
        Useful for testing or text-only channels.
        
        Args:
            user_text: User's message
            session_id: Session ID
            
        Returns:
            OrchestratorResult
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Process with LLM brain
        print(f"🧠 Processing with Zylin brain...")
        llm_response: ConversationResponse = await self.brain.process_message(
            user_text,
            session.conversation_history
        )
        
        bot_text = llm_response.message
        print(f"🤖 Zylin says: {bot_text}")
        
        # Update session
        session.conversation_history.append({"role": "user", "content": user_text})
        session.conversation_history.append({"role": "assistant", "content": bot_text})
        session.intent = llm_response.intent
        
        # Merge extracted data
        extracted = llm_response.extracted_data.model_dump(exclude_none=True)
        session.booking_data.update(extracted)
        
        # Check if conversation is complete
        if llm_response.booking_complete or llm_response.needs_escalation:
            session.completed = True
        
        return OrchestratorResult(
            session_id=session_id,
            user_text=user_text,
            bot_text=bot_text,
            bot_audio_path=None,
            intent=llm_response.intent,
            booking_complete=llm_response.booking_complete,
            needs_escalation=llm_response.needs_escalation,
            extracted_data=extracted
        )
    
    async def run_conversation(
        self,
        audio_files: List[str],
        caller_phone: Optional[str] = None,
        output_audio_dir: str = "tests/tts"
    ) -> ConversationSession:
        """
        Run a full multi-turn conversation from audio files.
        
        Args:
            audio_files: List of audio file paths (one per turn)
            caller_phone: Caller's phone number
            output_audio_dir: Where to save response audios
            
        Returns:
            Final conversation session
        """
        # Create session
        session = self.create_session(caller_phone)
        print(f"\n{'='*60}")
        print(f"🎬 Starting conversation session: {session.session_id}")
        print(f"{'='*60}\n")
        
        # Process each audio file as a turn
        for i, audio_file in enumerate(audio_files, 1):
            print(f"\n--- Turn {i} ---")
            
            result = await self.process_audio_turn(
                audio_file,
                session.session_id,
                output_audio_dir
            )
            
            print(f"📊 Intent: {result.intent}")
            if result.extracted_data:
                print(f"📝 Extracted: {result.extracted_data}")
            
            # Stop if conversation is complete
            if session.completed:
                print(f"\n✅ Conversation completed (intent: {session.intent})")
                break
        
        print(f"\n{'='*60}")
        print(f"🏁 Conversation session ended")
        print(f"{'='*60}\n")
        
        return session
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of a conversation session."""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        return {
            "session_id": session.session_id,
            "caller_phone": session.caller_phone,
            "start_time": session.start_time.isoformat(),
            "turn_count": len(session.conversation_history) // 2,
            "intent": session.intent,
            "booking_data": session.booking_data,
            "completed": session.completed,
            "conversation": session.conversation_history
        }
