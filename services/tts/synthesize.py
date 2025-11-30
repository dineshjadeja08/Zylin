"""
TTS (Text-to-Speech) Service
Converts text to natural-sounding speech using OpenAI TTS API.
"""

from typing import Optional, Literal
from pathlib import Path
import os
from pydantic import BaseModel
from openai import AsyncOpenAI
import aiofiles


# Voice options for OpenAI TTS
Voice = Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
# Audio formats
AudioFormat = Literal["mp3", "opus", "aac", "flac"]


class TTSResult(BaseModel):
    """Result of text-to-speech synthesis."""
    audio_file_path: str
    text: str
    voice: str
    duration_estimate: Optional[float] = None


class TTSService:
    """
    Text-to-Speech service using OpenAI TTS API.
    Generates natural-sounding speech from text.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "tts-1",  # tts-1 or tts-1-hd for higher quality
        voice: Voice = "nova",  # Default voice
        speed: float = 1.0  # 0.25 to 4.0
    ):
        """
        Initialize TTS service.
        
        Args:
            api_key: OpenAI API key
            model: TTS model (tts-1 or tts-1-hd)
            voice: Default voice to use
            speed: Speech speed (0.25-4.0, default 1.0)
        """
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.default_voice = voice
        self.default_speed = speed
    
    async def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        voice: Optional[Voice] = None,
        speed: Optional[float] = None,
        format: AudioFormat = "mp3"
    ) -> TTSResult:
        """
        Convert text to speech and save to file.
        
        Args:
            text: Text to convert to speech
            output_path: Path where audio file will be saved
            voice: Voice to use (overrides default)
            speed: Speech speed (overrides default)
            format: Audio format
            
        Returns:
            TTSResult with file path and metadata
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Ensure output directory exists
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Use provided values or defaults
        selected_voice = voice or self.default_voice
        selected_speed = speed or self.default_speed
        
        try:
            # Call OpenAI TTS API
            response = await self.client.audio.speech.create(
                model=self.model,
                voice=selected_voice,
                input=text,
                speed=selected_speed,
                response_format=format
            )
            
            # Stream response to file
            async with aiofiles.open(output_path, 'wb') as f:
                async for chunk in response.iter_bytes():
                    await f.write(chunk)
            
            # Estimate duration (very rough: ~150 words per minute at 1.0 speed)
            word_count = len(text.split())
            duration_estimate = (word_count / 150) * 60 / selected_speed
            
            return TTSResult(
                audio_file_path=str(output_path),
                text=text,
                voice=selected_voice,
                duration_estimate=duration_estimate
            )
            
        except Exception as e:
            print(f"❌ Error synthesizing speech: {e}")
            raise
    
    async def synthesize_to_bytes(
        self,
        text: str,
        voice: Optional[Voice] = None,
        speed: Optional[float] = None,
        format: AudioFormat = "mp3"
    ) -> bytes:
        """
        Convert text to speech and return as bytes.
        
        Useful for streaming or API responses.
        
        Args:
            text: Text to convert
            voice: Voice to use
            speed: Speech speed
            format: Audio format
            
        Returns:
            Audio data as bytes
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        selected_voice = voice or self.default_voice
        selected_speed = speed or self.default_speed
        
        try:
            response = await self.client.audio.speech.create(
                model=self.model,
                voice=selected_voice,
                input=text,
                speed=selected_speed,
                response_format=format
            )
            
            # Collect all bytes
            audio_bytes = b""
            async for chunk in response.iter_bytes():
                audio_bytes += chunk
            
            return audio_bytes
            
        except Exception as e:
            print(f"❌ Error synthesizing speech: {e}")
            raise


# Utility function for quick synthesis
async def synthesize(
    text: str,
    output_path: str,
    voice: Voice = "nova",
    speed: float = 1.0
) -> str:
    """
    Quick TTS function for common use case.
    
    Args:
        text: Text to synthesize
        output_path: Where to save audio file
        voice: Voice to use
        speed: Speech speed
        
    Returns:
        Path to generated audio file
    """
    tts = TTSService(voice=voice, speed=speed)
    result = await tts.synthesize_to_file(text, output_path)
    return result.audio_file_path
