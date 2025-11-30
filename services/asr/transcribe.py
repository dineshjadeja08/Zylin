"""
ASR (Automatic Speech Recognition) Service
Converts audio (speech) to text using OpenAI Whisper API or local Whisper model.
Includes real-time streaming support via Deepgram.
"""

from typing import Optional, Literal, AsyncGenerator
from pathlib import Path
import os
from pydantic import BaseModel
from openai import AsyncOpenAI
import httpx
import asyncio

# Streaming ASR support
try:
    from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
    DEEPGRAM_AVAILABLE = True
except ImportError:
    DEEPGRAM_AVAILABLE = False
    print("⚠️  Deepgram SDK not available. Install with: pip install deepgram-sdk")


class TranscriptionResult(BaseModel):
    """Result of speech-to-text transcription."""
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None
    confidence: Optional[float] = None


class ASRService:
    """
    Automatic Speech Recognition service.
    Supports OpenAI Whisper API for high-quality transcription.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "whisper-1"
    ):
        """
        Initialize ASR service.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Whisper model to use (whisper-1 for API)
        """
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model
    
    async def transcribe_file(
        self,
        audio_file_path: str,
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe an audio file to text.
        
        Args:
            audio_file_path: Path to audio file (.wav, .mp3, .m4a, .webm, etc.)
            language: ISO-639-1 language code (e.g., 'en', 'hi') - optional, improves accuracy
            prompt: Optional text to guide the model's style or continue a previous segment
            
        Returns:
            TranscriptionResult with text and metadata
        """
        file_path = Path(audio_file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
        
        try:
            with open(file_path, "rb") as audio_file:
                # Call OpenAI Whisper API
                response = await self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language=language,
                    prompt=prompt,
                    response_format="verbose_json"  # Get detailed info
                )
            
            # Parse response
            return TranscriptionResult(
                text=response.text.strip(),
                language=response.language if hasattr(response, 'language') else language,
                duration=response.duration if hasattr(response, 'duration') else None,
                confidence=None  # Whisper API doesn't provide confidence scores
            )
            
        except Exception as e:
            print(f"❌ Error transcribing audio: {e}")
            raise
    
    async def transcribe_bytes(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio from bytes (useful for streaming or API uploads).
        
        Args:
            audio_bytes: Audio file as bytes
            filename: Filename to use (must have proper extension)
            language: ISO-639-1 language code
            prompt: Optional guidance text
            
        Returns:
            TranscriptionResult with text and metadata
        """
        try:
            # Create a file-like object from bytes
            from io import BytesIO
            audio_file = BytesIO(audio_bytes)
            audio_file.name = filename
            
            # Call OpenAI Whisper API
            response = await self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                language=language,
                prompt=prompt,
                response_format="verbose_json"
            )
            
            return TranscriptionResult(
                text=response.text.strip(),
                language=response.language if hasattr(response, 'language') else language,
                duration=response.duration if hasattr(response, 'duration') else None,
                confidence=None
            )
            
        except Exception as e:
            print(f"❌ Error transcribing audio bytes: {e}")
            raise
    
    async def transcribe_url(
        self,
        audio_url: str,
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio from a URL.
        
        Args:
            audio_url: URL to audio file
            language: ISO-639-1 language code
            prompt: Optional guidance text
            
        Returns:
            TranscriptionResult with text and metadata
        """
        try:
            # Download audio from URL
            async with httpx.AsyncClient() as client:
                response = await client.get(audio_url)
                response.raise_for_status()
                audio_bytes = response.content
            
            # Determine filename from URL
            filename = Path(audio_url).name or "audio.wav"
            
            # Transcribe
            return await self.transcribe_bytes(
                audio_bytes,
                filename=filename,
                language=language,
                prompt=prompt
            )
            
        except Exception as e:
            print(f"❌ Error downloading/transcribing audio from URL: {e}")
            raise


# Utility function for common use case
async def transcribe(
    audio_source: str,
    language: Optional[str] = None,
    prompt: Optional[str] = None
) -> str:
    """
    Quick transcription function that auto-detects source type.
    
    Args:
        audio_source: File path or URL
        language: Optional language code
        prompt: Optional guidance text
        
    Returns:
        Transcribed text string
    """
    asr = ASRService()
    
    # Detect if URL or file path
    if audio_source.startswith(("http://", "https://")):
        result = await asr.transcribe_url(audio_source, language, prompt)
    else:
        result = await asr.transcribe_file(audio_source, language, prompt)
    
    return result.text


class StreamingASRService:
    """
    Real-time streaming ASR using Deepgram.
    Processes audio chunks as they arrive and yields transcripts.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize streaming ASR service.
        
        Args:
            api_key: Deepgram API key (defaults to DEEPGRAM_API_KEY env var)
        """
        if not DEEPGRAM_AVAILABLE:
            raise ImportError(
                "Deepgram SDK not available. Install with: pip install deepgram-sdk"
            )
        
        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise ValueError("Deepgram API key required. Set DEEPGRAM_API_KEY env var.")
        
        self.client = DeepgramClient(self.api_key)
    
    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: str = "en",
        interim_results: bool = True
    ) -> AsyncGenerator[tuple[str, bool], None]:
        """
        Transcribe audio stream in real-time.
        
        Args:
            audio_stream: Async generator yielding audio chunks (PCM 16-bit, 8kHz)
            language: Language code (e.g., "en", "es", "hi")
            interim_results: Whether to return interim (partial) results
            
        Yields:
            Tuples of (transcript, is_final)
            - is_final=True means end of utterance
            - is_final=False means interim/partial result
        """
        # Create connection to Deepgram
        connection = self.client.listen.asynclive.v("1")
        
        # Storage for results
        transcripts = asyncio.Queue()
        
        # Event handlers
        async def on_message(self, result, **kwargs):
            sentence = result.channel.alternatives[0].transcript
            if len(sentence) > 0:
                is_final = result.is_final
                await transcripts.put((sentence, is_final))
        
        async def on_error(self, error, **kwargs):
            print(f"❌ Deepgram error: {error}")
        
        # Register event handlers
        connection.on(LiveTranscriptionEvents.Transcript, on_message)
        connection.on(LiveTranscriptionEvents.Error, on_error)
        
        # Configure options
        options = LiveOptions(
            language=language,
            model="nova-2",  # Latest Deepgram model
            punctuate=True,
            interim_results=interim_results,
            endpointing=300,  # 300ms of silence = end of utterance
            vad_events=True,  # Voice activity detection
            smart_format=True
        )
        
        try:
            # Start connection
            if not await connection.start(options):
                raise Exception("Failed to start Deepgram connection")
            
            # Send audio chunks
            async def send_audio():
                try:
                    async for chunk in audio_stream:
                        connection.send(chunk)
                        await asyncio.sleep(0.01)  # Small delay to avoid overwhelming
                    
                    # Signal end of stream
                    await connection.finish()
                except Exception as e:
                    print(f"❌ Error sending audio: {e}")
            
            # Start sending audio in background
            send_task = asyncio.create_task(send_audio())
            
            # Yield transcripts as they arrive
            while True:
                try:
                    # Wait for transcript with timeout
                    transcript, is_final = await asyncio.wait_for(
                        transcripts.get(),
                        timeout=5.0
                    )
                    yield (transcript, is_final)
                    
                    # If final, check if stream is done
                    if is_final and send_task.done():
                        # Wait a bit for any remaining transcripts
                        await asyncio.sleep(0.5)
                        if transcripts.empty():
                            break
                
                except asyncio.TimeoutError:
                    # No transcript for 5 seconds, check if done
                    if send_task.done():
                        break
        
        finally:
            # Clean up
            await connection.finish()
    
    async def transcribe_stream_simple(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: str = "en"
    ) -> AsyncGenerator[str, None]:
        """
        Simplified streaming transcription that only yields final results.
        
        Args:
            audio_stream: Async generator yielding audio chunks
            language: Language code
            
        Yields:
            Final transcripts (complete utterances)
        """
        async for transcript, is_final in self.transcribe_stream(
            audio_stream,
            language=language,
            interim_results=False
        ):
            if is_final:
                yield transcript


class MockStreamingASR:
    """
    Mock streaming ASR for testing without Deepgram API.
    Simulates real-time transcription with delays.
    """
    
    def __init__(self):
        """Initialize mock ASR."""
        pass
    
    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: str = "en",
        interim_results: bool = True
    ) -> AsyncGenerator[tuple[str, bool], None]:
        """
        Mock transcription that simulates real-time behavior.
        
        In a real scenario, this would analyze audio.
        For testing, we just yield mock transcripts.
        """
        # Consume audio stream
        audio_chunks = []
        async for chunk in audio_stream:
            audio_chunks.append(chunk)
            
            # Simulate processing delay
            await asyncio.sleep(0.02)  # 20ms per chunk
            
            # Every 50 chunks (~1 second), yield interim result
            if interim_results and len(audio_chunks) % 50 == 0:
                yield ("User is speaking...", False)
        
        # Simulate final transcription delay
        await asyncio.sleep(0.5)
        
        # Yield final result based on audio duration
        duration_seconds = len(audio_chunks) * 0.02
        
        if duration_seconds < 1:
            yield ("Hello", True)
        elif duration_seconds < 3:
            yield ("I need an appointment", True)
        else:
            yield ("I need an appointment tomorrow at 3 PM", True)
    
    async def transcribe_stream_simple(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: str = "en"
    ) -> AsyncGenerator[str, None]:
        """Simplified mock that only yields final results."""
        async for transcript, is_final in self.transcribe_stream(
            audio_stream,
            language=language,
            interim_results=False
        ):
            if is_final:
                yield transcript
