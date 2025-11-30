"""
Audio Codec Utilities for Twilio Media Streams
Handles μ-law encoding/decoding and audio format conversion.
"""

import audioop
import base64
from typing import Optional


class AudioCodec:
    """
    Utilities for audio encoding/decoding for Twilio Media Streams.
    
    Twilio uses:
    - Sample rate: 8000 Hz (8 kHz)
    - Encoding: μ-law (8-bit)
    - Format: base64-encoded
    - Chunk size: 20ms (160 bytes of μ-law = 320 bytes of PCM)
    """
    
    SAMPLE_RATE = 8000  # 8 kHz
    SAMPLE_WIDTH = 2    # 16-bit PCM (2 bytes per sample)
    CHUNK_SIZE_MS = 20  # 20ms chunks
    CHUNK_SIZE_BYTES = int(SAMPLE_RATE * CHUNK_SIZE_MS / 1000)  # 160 samples
    
    @staticmethod
    def decode_mulaw_base64(base64_data: str) -> bytes:
        """
        Decode base64 μ-law audio to 16-bit PCM.
        
        Args:
            base64_data: Base64-encoded μ-law audio from Twilio
            
        Returns:
            16-bit PCM audio bytes
        """
        # Decode base64
        mulaw_bytes = base64.b64decode(base64_data)
        
        # Convert μ-law to PCM (linear 16-bit)
        pcm_bytes = audioop.ulaw2lin(mulaw_bytes, 2)  # 2 = 16-bit samples
        
        return pcm_bytes
    
    @staticmethod
    def encode_pcm_to_mulaw_base64(pcm_bytes: bytes) -> str:
        """
        Encode 16-bit PCM audio to base64 μ-law for Twilio.
        
        Args:
            pcm_bytes: 16-bit PCM audio bytes
            
        Returns:
            Base64-encoded μ-law string
        """
        # Convert PCM to μ-law
        mulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)  # 2 = 16-bit samples
        
        # Encode to base64
        base64_data = base64.b64encode(mulaw_bytes).decode('utf-8')
        
        return base64_data
    
    @staticmethod
    def resample_audio(audio_bytes: bytes, 
                       from_rate: int, 
                       to_rate: int, 
                       sample_width: int = 2) -> bytes:
        """
        Resample audio from one rate to another.
        
        Args:
            audio_bytes: Input audio bytes
            from_rate: Source sample rate (e.g., 16000)
            to_rate: Target sample rate (e.g., 8000)
            sample_width: Bytes per sample (2 for 16-bit)
            
        Returns:
            Resampled audio bytes
        """
        if from_rate == to_rate:
            return audio_bytes
        
        # Use audioop to resample
        resampled, _ = audioop.ratecv(
            audio_bytes,
            sample_width,
            1,  # mono
            from_rate,
            to_rate,
            None
        )
        
        return resampled
    
    @staticmethod
    def convert_to_twilio_format(audio_bytes: bytes, 
                                 source_rate: int = 24000,
                                 source_width: int = 2) -> str:
        """
        Convert audio from any format to Twilio's required format.
        
        This is useful for TTS output which might be 24kHz PCM.
        
        Args:
            audio_bytes: Source audio (PCM)
            source_rate: Source sample rate
            source_width: Source sample width in bytes
            
        Returns:
            Base64-encoded μ-law string ready for Twilio
        """
        # Step 1: Resample to 8kHz if needed
        if source_rate != AudioCodec.SAMPLE_RATE:
            audio_bytes = AudioCodec.resample_audio(
                audio_bytes,
                source_rate,
                AudioCodec.SAMPLE_RATE,
                source_width
            )
        
        # Step 2: Convert to μ-law and base64
        return AudioCodec.encode_pcm_to_mulaw_base64(audio_bytes)
    
    @staticmethod
    def create_twilio_audio_message(base64_audio: str, stream_sid: str) -> dict:
        """
        Create a properly formatted Twilio Media message.
        
        Args:
            base64_audio: Base64-encoded μ-law audio
            stream_sid: Stream SID from Twilio
            
        Returns:
            Dictionary ready to be JSON-serialized and sent to Twilio
        """
        return {
            "event": "media",
            "streamSid": stream_sid,
            "media": {
                "payload": base64_audio
            }
        }
    
    @staticmethod
    def chunk_audio(audio_bytes: bytes, chunk_size_ms: int = 20) -> list[bytes]:
        """
        Split audio into chunks for streaming.
        
        Args:
            audio_bytes: Audio bytes to chunk
            chunk_size_ms: Chunk size in milliseconds
            
        Returns:
            List of audio chunks
        """
        # Calculate bytes per chunk
        samples_per_chunk = int(AudioCodec.SAMPLE_RATE * chunk_size_ms / 1000)
        bytes_per_chunk = samples_per_chunk * AudioCodec.SAMPLE_WIDTH
        
        # Split into chunks
        chunks = []
        for i in range(0, len(audio_bytes), bytes_per_chunk):
            chunk = audio_bytes[i:i + bytes_per_chunk]
            if len(chunk) == bytes_per_chunk:  # Only add complete chunks
                chunks.append(chunk)
        
        return chunks


class AudioBuffer:
    """
    Buffer for accumulating audio chunks until a complete utterance.
    """
    
    def __init__(self, max_duration_ms: int = 10000):
        """
        Initialize audio buffer.
        
        Args:
            max_duration_ms: Maximum buffer duration in milliseconds
        """
        self.buffer = bytearray()
        self.max_duration_ms = max_duration_ms
        self.max_bytes = int(
            AudioCodec.SAMPLE_RATE * 
            AudioCodec.SAMPLE_WIDTH * 
            max_duration_ms / 1000
        )
    
    def add_chunk(self, chunk: bytes) -> None:
        """Add audio chunk to buffer."""
        self.buffer.extend(chunk)
        
        # Prevent buffer overflow
        if len(self.buffer) > self.max_bytes:
            # Keep only the last max_bytes
            self.buffer = self.buffer[-self.max_bytes:]
    
    def get_audio(self) -> bytes:
        """Get buffered audio."""
        return bytes(self.buffer)
    
    def clear(self) -> None:
        """Clear the buffer."""
        self.buffer.clear()
    
    def duration_ms(self) -> float:
        """Get current buffer duration in milliseconds."""
        num_samples = len(self.buffer) / AudioCodec.SAMPLE_WIDTH
        return (num_samples / AudioCodec.SAMPLE_RATE) * 1000
    
    def has_audio(self) -> bool:
        """Check if buffer has any audio."""
        return len(self.buffer) > 0


# Example usage
if __name__ == "__main__":
    # Test encoding/decoding
    print("Testing audio codec utilities...\n")
    
    # Simulate receiving μ-law from Twilio
    print("1. Decoding μ-law from Twilio...")
    # Create some test μ-law data (silence)
    test_mulaw = b'\xff' * 160  # 160 bytes of μ-law silence
    test_base64 = base64.b64encode(test_mulaw).decode('utf-8')
    
    pcm = AudioCodec.decode_mulaw_base64(test_base64)
    print(f"   Decoded {len(test_mulaw)} μ-law bytes to {len(pcm)} PCM bytes")
    
    # Test encoding back
    print("\n2. Encoding PCM to μ-law for Twilio...")
    encoded = AudioCodec.encode_pcm_to_mulaw_base64(pcm)
    print(f"   Encoded {len(pcm)} PCM bytes to {len(encoded)} base64 chars")
    
    # Test resampling
    print("\n3. Resampling audio...")
    # Simulate 24kHz audio (from TTS)
    test_24khz = b'\x00\x00' * 2400  # 100ms of silence at 24kHz
    resampled = AudioCodec.resample_audio(test_24khz, 24000, 8000, 2)
    print(f"   Resampled {len(test_24khz)} bytes (24kHz) to {len(resampled)} bytes (8kHz)")
    
    # Test buffer
    print("\n4. Testing audio buffer...")
    buffer = AudioBuffer()
    chunk = b'\x00\x00' * 160  # 20ms of audio
    for i in range(5):
        buffer.add_chunk(chunk)
    print(f"   Buffer duration: {buffer.duration_ms():.1f}ms")
    print(f"   Buffer size: {len(buffer.get_audio())} bytes")
    
    print("\n✅ Audio codec utilities working correctly!")
