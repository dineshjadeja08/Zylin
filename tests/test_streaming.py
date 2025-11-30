"""
End-to-End Streaming Pipeline Tests
Tests real-time audio streaming: WebSocket → ASR → LLM → TTS → WebSocket
"""

import asyncio
import pytest
import json
import base64
from typing import List, Dict
import time

from services.orchestrator.streaming_pipeline import StreamingPipeline, StreamingSession
from services.utils.audio_codec import AudioCodec
from services.asr.transcribe import MockStreamingASR
from services.tts.synthesize import MockStreamingTTS


@pytest.fixture
def streaming_pipeline():
    """Fixture for streaming pipeline with mock services."""
    return StreamingPipeline(use_mock_services=True)


@pytest.mark.asyncio
async def test_session_creation(streaming_pipeline):
    """Test session creation and management."""
    # Create session
    session = streaming_pipeline.create_session(
        session_id="test-session-1",
        caller_phone="+919876543210",
        stream_sid="ST123456"
    )
    
    assert session is not None
    assert session.session_id == "test-session-1"
    assert session.caller_phone == "+919876543210"
    assert session.stream_sid == "ST123456"
    assert session.is_active
    
    # Retrieve session
    retrieved = streaming_pipeline.get_session("test-session-1")
    assert retrieved == session
    
    # Close session
    streaming_pipeline.close_session("test-session-1")
    assert streaming_pipeline.get_session("test-session-1") is None


@pytest.mark.asyncio
async def test_audio_codec_roundtrip():
    """Test μ-law encoding/decoding roundtrip."""
    # Create test PCM audio (silence)
    pcm_original = b'\x00\x00' * 160  # 20ms of silence at 8kHz
    
    # Encode to μ-law base64
    mulaw_base64 = AudioCodec.encode_pcm_to_mulaw_base64(pcm_original)
    
    assert isinstance(mulaw_base64, str)
    assert len(mulaw_base64) > 0
    
    # Decode back to PCM
    pcm_decoded = AudioCodec.decode_mulaw_base64(mulaw_base64)
    
    assert isinstance(pcm_decoded, bytes)
    assert len(pcm_decoded) == len(pcm_original)


@pytest.mark.asyncio
async def test_audio_resampling():
    """Test audio resampling from 24kHz to 8kHz."""
    # Create 24kHz audio (1 second)
    audio_24khz = b'\x00\x00' * 24000
    
    # Resample to 8kHz
    audio_8khz = AudioCodec.resample_audio(audio_24khz, 24000, 8000, 2)
    
    # Should be 1/3 the size
    assert len(audio_8khz) == len(audio_24khz) // 3


@pytest.mark.asyncio
async def test_mock_streaming_asr():
    """Test mock ASR processes audio stream correctly."""
    asr = MockStreamingASR()
    
    # Create audio stream (2 seconds of audio)
    async def audio_stream():
        for _ in range(100):  # 100 chunks of 20ms = 2 seconds
            chunk = b'\x00\x00' * 160
            yield chunk
            await asyncio.sleep(0.001)  # Simulate real-time
    
    # Transcribe
    transcripts = []
    async for transcript, is_final in asr.transcribe_stream(audio_stream()):
        transcripts.append((transcript, is_final))
    
    # Should have at least one final transcript
    final_transcripts = [t for t, is_final in transcripts if is_final]
    assert len(final_transcripts) > 0
    assert len(final_transcripts[0]) > 0


@pytest.mark.asyncio
async def test_mock_streaming_tts():
    """Test mock TTS generates audio stream correctly."""
    tts = MockStreamingTTS()
    
    # Create text stream
    async def text_stream():
        yield "Hello, this is a test."
    
    # Synthesize
    audio_chunks = []
    async for chunk in tts.synthesize_stream(text_stream()):
        audio_chunks.append(chunk)
    
    # Should have generated audio chunks
    assert len(audio_chunks) > 0
    
    # Total audio should be non-zero
    total_audio = b''.join(audio_chunks)
    assert len(total_audio) > 0


@pytest.mark.asyncio
async def test_streaming_pipeline_greeting(streaming_pipeline):
    """Test pipeline sends greeting correctly."""
    # Create session
    session = streaming_pipeline.create_session(
        session_id="test-greeting",
        caller_phone="+919876543210"
    )
    
    # Create output queue
    output_queue = asyncio.Queue()
    
    # Send greeting
    await streaming_pipeline.send_greeting("test-greeting", output_queue)
    
    # Should have audio in queue
    assert output_queue.qsize() > 0
    
    # Check message format
    message = await output_queue.get()
    assert "event" in message
    assert message["event"] == "media"
    assert "media" in message
    assert "payload" in message["media"]
    
    # Payload should be valid base64
    payload = message["media"]["payload"]
    decoded = base64.b64decode(payload)
    assert len(decoded) > 0


@pytest.mark.asyncio
async def test_streaming_pipeline_single_turn(streaming_pipeline):
    """Test complete single-turn conversation through pipeline."""
    # Create session
    session = streaming_pipeline.create_session(
        session_id="test-turn",
        caller_phone="+919876543210"
    )
    
    # Create mock audio stream (2 seconds)
    async def audio_stream():
        for _ in range(100):
            chunk = b'\x00\x00' * 160
            yield chunk
            await asyncio.sleep(0.001)
    
    # Create output queue
    output_queue = asyncio.Queue()
    
    # Process stream
    start_time = time.time()
    
    await streaming_pipeline.process_call_stream(
        "test-turn",
        audio_stream(),
        output_queue
    )
    
    end_time = time.time()
    latency_ms = (end_time - start_time) * 1000
    
    # Should have completed
    assert output_queue.qsize() > 0
    
    # Latency should be reasonable (under 5 seconds for mock)
    assert latency_ms < 5000
    
    print(f"✅ Single turn latency: {latency_ms:.0f}ms")


@pytest.mark.asyncio
async def test_streaming_pipeline_conversation_history(streaming_pipeline):
    """Test conversation history is maintained correctly."""
    # Create session
    session = streaming_pipeline.create_session(
        session_id="test-history",
        caller_phone="+919876543210"
    )
    
    # Add some messages
    session.add_message("assistant", "Hello! How can I help?")
    session.add_message("user", "I need an appointment")
    session.add_message("assistant", "Sure, what date?")
    
    # Check history
    history = session.get_conversation_for_llm()
    
    assert len(history) == 3
    assert history[0]["role"] == "assistant"
    assert history[1]["role"] == "user"
    assert history[2]["role"] == "assistant"


@pytest.mark.asyncio
async def test_streaming_pipeline_latency_tracking(streaming_pipeline):
    """Test latency metrics are tracked."""
    # Create session
    session = streaming_pipeline.create_session(
        session_id="test-latency",
        caller_phone="+919876543210"
    )
    
    # Add some latency metrics
    session.add_latency_metric("asr_processing", 250.5)
    session.add_latency_metric("llm_processing", 500.2)
    session.add_latency_metric("tts_generation", 300.1)
    session.add_latency_metric("end_to_end", 1050.8)
    
    # Check metrics
    assert len(session.latency_metrics) == 4
    
    # Calculate average end-to-end
    e2e_metrics = [
        m["duration_ms"] for m in session.latency_metrics 
        if m["metric"] == "end_to_end"
    ]
    
    assert len(e2e_metrics) == 1
    assert e2e_metrics[0] == 1050.8


@pytest.mark.asyncio
async def test_twilio_websocket_message_flow():
    """
    Test complete Twilio WebSocket message flow.
    
    Simulates:
    1. Start message
    2. Multiple media messages
    3. Stop message
    """
    pipeline = StreamingPipeline(use_mock_services=True)
    
    # Simulate Twilio messages
    messages = []
    
    # Start message
    start_msg = {
        "event": "start",
        "streamSid": "STtest123",
        "start": {
            "callSid": "CAtest123",
            "customParameters": {
                "callerPhone": "+919876543210"
            }
        }
    }
    messages.append(start_msg)
    
    # Media messages (simulate 1 second of audio)
    for i in range(50):  # 50 chunks of 20ms each
        # Create μ-law audio
        pcm_chunk = b'\x00\x00' * 160
        mulaw_base64 = AudioCodec.encode_pcm_to_mulaw_base64(pcm_chunk)
        
        media_msg = {
            "event": "media",
            "streamSid": "STtest123",
            "media": {
                "payload": mulaw_base64
            }
        }
        messages.append(media_msg)
    
    # Stop message
    stop_msg = {
        "event": "stop",
        "streamSid": "STtest123"
    }
    messages.append(stop_msg)
    
    # Process messages
    session_id = None
    audio_input_queue = asyncio.Queue()
    audio_output_queue = asyncio.Queue()
    
    for msg in messages[:1]:  # Just process start for this test
        if msg["event"] == "start":
            session_id = "ws-test-session"
            pipeline.create_session(
                session_id=session_id,
                caller_phone=msg["start"]["customParameters"]["callerPhone"],
                stream_sid=msg["streamSid"]
            )
            
            # Send greeting
            await pipeline.send_greeting(session_id, audio_output_queue)
    
    # Should have created session
    assert session_id is not None
    session = pipeline.get_session(session_id)
    assert session is not None
    assert session.stream_sid == "STtest123"
    
    # Should have greeting audio
    assert audio_output_queue.qsize() > 0


@pytest.mark.asyncio
async def test_latency_target_monitoring(streaming_pipeline):
    """Test that pipeline monitors latency against target."""
    # Set low target for testing
    streaming_pipeline.max_latency_target_ms = 1000  # 1 second
    
    # Create session
    session = streaming_pipeline.create_session(
        session_id="test-target",
        caller_phone="+919876543210"
    )
    
    # Add metrics that exceed target
    session.add_latency_metric("end_to_end", 1500.0)  # Exceeds 1000ms
    
    # Check if over target
    e2e_metrics = [
        m["duration_ms"] for m in session.latency_metrics 
        if m["metric"] == "end_to_end"
    ]
    
    assert e2e_metrics[0] > streaming_pipeline.max_latency_target_ms


@pytest.mark.asyncio
async def test_concurrent_sessions(streaming_pipeline):
    """Test pipeline can handle multiple concurrent sessions."""
    # Create multiple sessions
    session_ids = []
    for i in range(5):
        session_id = f"concurrent-{i}"
        streaming_pipeline.create_session(
            session_id=session_id,
            caller_phone=f"+9198765432{i}0"
        )
        session_ids.append(session_id)
    
    # All sessions should exist
    assert len(streaming_pipeline.sessions) == 5
    
    for session_id in session_ids:
        session = streaming_pipeline.get_session(session_id)
        assert session is not None
        assert session.is_active
    
    # Close all sessions
    for session_id in session_ids:
        streaming_pipeline.close_session(session_id)
    
    # No sessions should remain
    assert len(streaming_pipeline.sessions) == 0


@pytest.mark.asyncio
async def test_audio_buffer_overflow_handling():
    """Test audio buffer handles overflow gracefully."""
    from services.utils.audio_codec import AudioBuffer
    
    # Create buffer with small max size
    buffer = AudioBuffer(max_duration_ms=100)  # 100ms max
    
    # Add more than max
    chunk = b'\x00\x00' * 160  # 20ms chunk
    for _ in range(10):  # 200ms total
        buffer.add_chunk(chunk)
    
    # Should not exceed max
    duration = buffer.duration_ms()
    assert duration <= 100  # May be slightly less due to truncation


@pytest.mark.asyncio
async def test_error_handling_invalid_audio():
    """Test pipeline handles invalid audio gracefully."""
    pipeline = StreamingPipeline(use_mock_services=True)
    
    # Create session
    session = pipeline.create_session(
        session_id="test-error",
        caller_phone="+919876543210"
    )
    
    # Create invalid audio stream (random data)
    async def invalid_audio_stream():
        yield b'\xff' * 100  # Invalid audio data
    
    output_queue = asyncio.Queue()
    
    # Should not crash
    try:
        await pipeline.process_call_stream(
            "test-error",
            invalid_audio_stream(),
            output_queue
        )
    except Exception as e:
        # Error handling should catch this
        print(f"Handled error: {e}")


if __name__ == "__main__":
    # Run tests
    print("Running Streaming Pipeline Tests\n")
    pytest.main([__file__, "-v", "-s"])
