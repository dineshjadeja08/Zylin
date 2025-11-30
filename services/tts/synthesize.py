"""
TTS (Text-to-Speech) Service
Converts text to natural-sounding speech using OpenAI TTS API.
Includes real-time streaming support for low-latency responses.
"""

from typing import Optional, Literal, AsyncGenerator
from pathlib import Path
import os
import asyncio
import io
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


class StreamingTTSService:
    """
    Streaming TTS for real-time audio generation.
    Converts text chunks to audio and yields them for immediate playback.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        voice: Voice = "nova",
        speed: float = 1.1  # Slightly faster for phone calls
    ):
        """
        Initialize streaming TTS service.
        
        Args:
            api_key: OpenAI API key
            voice: Voice to use
            speed: Speech speed (1.0-1.3 recommended for calls)
        """
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.voice = voice
        self.speed = speed
    
    async def synthesize_stream(
        self,
        text_stream: AsyncGenerator[str, None],
        output_format: str = "pcm"
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream TTS audio as text arrives.
        
        This implementation buffers text into sentences and generates
        audio for each complete sentence for natural pacing.
        
        Args:
            text_stream: Async generator yielding text chunks from LLM
            output_format: "pcm" for raw PCM audio, "mp3" for compressed
            
        Yields:
            Audio bytes (PCM 16-bit, 24kHz or MP3)
        """
        sentence_buffer = ""
        sentence_endings = [".", "!", "?", "\n"]
        
        async for text_chunk in text_stream:
            sentence_buffer += text_chunk
            
            # Check if we have a complete sentence
            has_ending = any(ending in text_chunk for ending in sentence_endings)
            
            if has_ending or len(sentence_buffer) > 200:  # Max buffer size
                # Generate audio for this sentence
                sentence = sentence_buffer.strip()
                
                if sentence:
                    # Synthesize this sentence
                    response = await self.client.audio.speech.create(
                        model="tts-1",  # Use faster model for streaming
                        voice=self.voice,
                        input=sentence,
                        speed=self.speed,
                        response_format=output_format
                    )
                    
                    # Stream audio bytes
                    async for audio_chunk in response.iter_bytes(chunk_size=4096):
                        yield audio_chunk
                
                # Clear buffer
                sentence_buffer = ""
        
        # Handle any remaining text
        if sentence_buffer.strip():
            response = await self.client.audio.speech.create(
                model="tts-1",
                voice=self.voice,
                input=sentence_buffer.strip(),
                speed=self.speed,
                response_format=output_format
            )
            
            async for audio_chunk in response.iter_bytes(chunk_size=4096):
                yield audio_chunk
    
    async def synthesize_stream_for_twilio(
        self,
        text_stream: AsyncGenerator[str, None]
    ) -> AsyncGenerator[bytes, None]:
        """
        Generate audio stream in Twilio-compatible format.
        
        This wraps synthesize_stream and converts output to 8kHz PCM
        ready for μ-law encoding.
        
        Args:
            text_stream: Text chunks from LLM
            
        Yields:
            PCM audio bytes (16-bit, 8kHz mono) ready for μ-law conversion
        """
        from services.utils.audio_codec import AudioCodec
        
        # Generate audio at 24kHz (OpenAI TTS default)
        async for audio_chunk in self.synthesize_stream(text_stream, output_format="pcm"):
            # Resample from 24kHz to 8kHz for Twilio
            # Note: OpenAI TTS outputs 24kHz 16-bit mono PCM
            resampled = AudioCodec.resample_audio(
                audio_chunk,
                from_rate=24000,
                to_rate=8000,
                sample_width=2
            )
            
            yield resampled
    
    async def synthesize_sentence(
        self,
        text: str,
        output_format: str = "pcm"
    ) -> bytes:
        """
        Synthesize a single sentence/phrase quickly.
        
        Args:
            text: Text to synthesize
            output_format: Audio format
            
        Returns:
            Complete audio bytes
        """
        response = await self.client.audio.speech.create(
            model="tts-1",
            voice=self.voice,
            input=text,
            speed=self.speed,
            response_format=output_format
        )
        
        audio_bytes = b""
        async for chunk in response.iter_bytes():
            audio_bytes += chunk
        
        return audio_bytes


class MockStreamingTTS:
    """
    Mock streaming TTS for testing without OpenAI API.
    Generates silence with appropriate delays.
    """
    
    def __init__(self, voice: Voice = "nova", speed: float = 1.0):
        """Initialize mock TTS."""
        self.voice = voice
        self.speed = speed
    
    async def synthesize_stream(
        self,
        text_stream: AsyncGenerator[str, None],
        output_format: str = "pcm"
    ) -> AsyncGenerator[bytes, None]:
        """
        Mock synthesis that generates silence.
        
        Simulates realistic timing for testing.
        """
        total_text = ""
        
        async for text_chunk in text_stream:
            total_text += text_chunk
        
        # Simulate processing time (100 chars/sec)
        processing_time = len(total_text) / 100.0
        await asyncio.sleep(processing_time)
        
        # Generate silence (16-bit PCM, 8kHz)
        # Approximate: 1 second of audio = 16000 bytes
        duration_seconds = len(total_text) * 0.05  # ~20 chars per second of speech
        audio_bytes = b'\x00\x00' * int(8000 * duration_seconds)
        
        # Yield in chunks (20ms each)
        chunk_size = 320  # 20ms at 8kHz 16-bit
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i + chunk_size]
            yield chunk
            await asyncio.sleep(0.02)  # Simulate real-time
    
    async def synthesize_stream_for_twilio(
        self,
        text_stream: AsyncGenerator[str, None]
    ) -> AsyncGenerator[bytes, None]:
        """Mock Twilio-compatible stream."""
        async for chunk in self.synthesize_stream(text_stream, output_format="pcm"):
            yield chunk
    
    async def synthesize_sentence(
        self,
        text: str,
        output_format: str = "pcm"
    ) -> bytes:
        """Mock single sentence synthesis."""
        # Convert to async generator
        async def text_gen():
            yield text
        
        audio_bytes = b""
        async for chunk in self.synthesize_stream(text_gen(), output_format):
            audio_bytes += chunk
        
        return audio_bytes
