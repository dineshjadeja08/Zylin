"""
ASR (Automatic Speech Recognition) Service
Converts audio (speech) to text using OpenAI Whisper API or local Whisper model.
"""

from typing import Optional, Literal
from pathlib import Path
import os
from pydantic import BaseModel
from openai import AsyncOpenAI
import httpx


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
