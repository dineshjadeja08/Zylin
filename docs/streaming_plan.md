# Real-Time Streaming Implementation Plan

## Overview

This document outlines the plan to upgrade Zylin from the current "record-then-process" approach to **real-time bi-directional audio streaming**. This enables natural, low-latency conversations similar to calling a human receptionist.

**Status:** Post-MVP Feature (Not Required for Initial Launch)

---

## Current Architecture (MVP)

```
Caller speaks
    ↓
Twilio records (up to 30 seconds)
    ↓
Recording POSTed to webhook
    ↓
Background processing:
  - Download recording
  - Transcribe (ASR)
  - Process (LLM)
  - Generate response (TTS)
  - Send via WhatsApp
```

**Limitations:**
- ❌ High latency (10-30 seconds)
- ❌ One-way interaction per turn
- ❌ No interruption handling
- ❌ Response via WhatsApp, not voice

---

## Target Architecture (Real-Time)

```
Caller speaks ─────┐
                   ↓
    ┌─────── Twilio Media Stream (WebSocket)
    │              ↓
    │        Zylin Server
    │              │
    │         ┌────┴────┐
    │         │         │
    │        ASR      TTS
    │         │         │
    │         └─── LLM ─┘
    │              ↓
    └──────── Audio Response
                   ↓
           Caller hears Zylin speaking
```

**Benefits:**
- ✅ Low latency (1-3 seconds)
- ✅ Two-way real-time conversation
- ✅ Can interrupt Zylin (like humans do)
- ✅ More natural experience
- ✅ Response delivered as voice call

---

## Technical Requirements

### 1. Twilio Media Streams

**What it is:** WebSocket connection that streams raw audio chunks in real-time.

**Setup:**
```xml
<Response>
    <Connect>
        <Stream url="wss://your-domain.com/media-stream">
            <Parameter name="sessionId" value="unique-session-123"/>
        </Stream>
    </Connect>
</Response>
```

**Audio Format:**
- Codec: µ-law (8-bit, 8kHz)
- Sample rate: 8000 Hz
- Encoding: base64
- Chunks: 20ms of audio per message

### 2. WebSocket Server

**FastAPI Implementation:**

```python
from fastapi import WebSocket, WebSocketDisconnect
import json
import base64

@app.websocket("/media-stream")
async def media_stream_handler(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            
            if data["event"] == "media":
                # Audio chunk in base64
                audio_chunk = base64.b64decode(data["media"]["payload"])
                
                # Process audio chunk
                await process_audio_chunk(audio_chunk)
            
            elif data["event"] == "start":
                # Call started
                session_id = data["start"]["customParameters"]["sessionId"]
                await init_session(session_id)
            
            elif data["event"] == "stop":
                # Call ended
                await cleanup_session()
                
    except WebSocketDisconnect:
        print("WebSocket disconnected")
```

### 3. Streaming ASR

**Options:**

#### Option A: Deepgram (Recommended for MVP)
- **Pros:** Built for streaming, low latency, good accuracy
- **Cons:** Additional service cost (~$0.0125/min)
- **Implementation:**

```python
from deepgram import Deepgram

dg = Deepgram(api_key)

async def transcribe_stream(audio_stream):
    async with dg.transcription.live({
        "punctuate": True,
        "interim_results": True
    }) as transcription:
        
        async for chunk in audio_stream:
            transcription.send(chunk)
        
        async for result in transcription:
            if result.is_final:
                yield result.channel.alternatives[0].transcript
```

#### Option B: OpenAI Whisper (Not Streaming)
- OpenAI Whisper API doesn't support streaming yet
- Would need to buffer 1-2 seconds before transcribing
- Higher latency but familiar tech stack

#### Option C: AssemblyAI
- Similar to Deepgram
- Real-time transcription API
- ~$0.015/min

### 4. Streaming LLM

**OpenAI Streaming:**

```python
async def stream_llm_response(transcript):
    response = await openai.ChatCompletion.acreate(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript}
        ],
        stream=True
    )
    
    async for chunk in response:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

### 5. Streaming TTS

**Options:**

#### Option A: ElevenLabs (Best Quality)
- Supports streaming
- Very natural voices
- ~$0.18/1000 chars (~$3.60 per 100 calls)

```python
from elevenlabs import generate, stream

audio_stream = generate(
    text=text_stream,
    voice="Bella",
    model="eleven_monolingual_v1",
    stream=True
)

stream(audio_stream)
```

#### Option B: OpenAI TTS (Not Streaming)
- High quality but batch only
- Need to buffer complete sentences
- Medium latency

#### Option C: Google Cloud TTS
- Supports streaming
- Good quality, many voices
- ~$4 per million characters

### 6. Audio Buffering Strategy

**Challenge:** Balance between latency and naturalness.

**Approach:**
```python
class AudioBuffer:
    def __init__(self):
        self.text_buffer = ""
        self.sentence_end_markers = [".", "!", "?"]
    
    async def process(self, text_chunk):
        self.text_buffer += text_chunk
        
        # Check for sentence end
        if any(marker in text_chunk for marker in self.sentence_end_markers):
            # Generate audio for complete sentence
            audio = await tts.synthesize(self.text_buffer)
            await send_to_twilio(audio)
            
            self.text_buffer = ""
```

---

## Implementation Phases

### Phase 1: WebSocket Infrastructure
**Goal:** Receive and send audio via WebSocket

**Tasks:**
1. Set up WebSocket endpoint in FastAPI
2. Handle Twilio Media Stream events (start, media, stop)
3. Decode incoming µ-law audio
4. Encode and send µ-law audio back to Twilio
5. Test with echo server (send back what you receive)

**Acceptance:**
- Can receive audio chunks from Twilio
- Can play audio back to caller
- Latency < 100ms for echo

### Phase 2: Streaming ASR Integration
**Goal:** Transcribe audio in real-time

**Tasks:**
1. Integrate Deepgram or AssemblyAI
2. Buffer incoming audio chunks
3. Send to ASR as stream
4. Handle interim vs final transcripts
5. Implement VAD (Voice Activity Detection) to detect when caller stops

**Acceptance:**
- Transcription appears within 500ms of speech
- Can detect end of utterance
- Accuracy ≥90% for clear speech

### Phase 3: Streaming LLM + TTS
**Goal:** Generate and speak responses in real-time

**Tasks:**
1. Stream LLM responses (token by token)
2. Buffer into sentences/phrases
3. Generate audio for each sentence
4. Send audio to Twilio WebSocket
5. Handle interruptions (caller speaks while Zylin is speaking)

**Acceptance:**
- First audio heard within 2 seconds of caller finishing
- Natural-sounding conversation flow
- Can handle interruptions gracefully

### Phase 4: State Management
**Goal:** Maintain conversation context

**Tasks:**
1. Session state storage (in-memory + Redis for scale)
2. Conversation history management
3. Intent tracking across turns
4. Booking data collection in real-time

**Acceptance:**
- Context preserved across turns
- Can complete multi-turn bookings
- State survives brief disconnections

### Phase 5: Production Optimization
**Goal:** Make it robust and scalable

**Tasks:**
1. Error handling and fallbacks
2. Audio quality monitoring
3. Latency tracking and alerts
4. Auto-scaling for concurrent calls
5. Cost optimization (buffer strategies, model selection)

**Acceptance:**
- 99% uptime
- Average latency < 2s
- Can handle 50+ concurrent calls

---

## Cost Analysis

### Current MVP (Record-then-Process):
- Twilio: $0.0085/min incoming
- OpenAI Whisper: $0.006/min
- OpenAI GPT-4: ~$0.01 per call
- OpenAI TTS: ~$0.005 per call
- **Total: ~$0.03 per 2-min call**

### Real-Time Streaming:
- Twilio Media Streams: $0.0085/min
- Deepgram: $0.0125/min
- OpenAI GPT-4: ~$0.01 per call
- ElevenLabs TTS: ~$0.036 per call
- **Total: ~$0.09 per 2-min call**

**3x increase, but better experience**

### Cost Savings Ideas:
1. Use GPT-3.5-turbo for non-critical intents (FAQ)
2. Cache common responses
3. Optimize token usage with shorter prompts
4. Use cheaper TTS for non-customer-facing audio

---

## Technical Challenges

### 1. Latency Management
**Problem:** Each component adds latency

**Solution:**
- Parallel processing where possible
- Streaming at every layer
- Predictive pre-generation (anticipate next response)

### 2. Audio Quality
**Problem:** 8kHz phone audio is lower quality

**Solution:**
- Train/fine-tune ASR on phone call data
- Use models optimized for telephony
- Implement noise suppression

### 3. Interruption Handling
**Problem:** User might interrupt Zylin mid-sentence

**Solution:**
- Continuous VAD monitoring
- Stop TTS immediately on interruption
- Resume context appropriately

### 4. State Synchronization
**Problem:** Need to track state across WebSocket connections

**Solution:**
- Use Redis for distributed state
- Implement state checkpointing
- Handle reconnections gracefully

### 5. Scale & Concurrency
**Problem:** WebSocket connections are stateful

**Solution:**
- Use load balancer with sticky sessions
- Horizontal scaling with connection pooling
- Implement connection limits per server

---

## Monitoring & Metrics

### Key Metrics:
1. **Latency Breakdown:**
   - ASR latency
   - LLM latency
   - TTS latency
   - End-to-end latency

2. **Quality Metrics:**
   - Transcription accuracy
   - Intent classification accuracy
   - Conversation completion rate

3. **Infrastructure:**
   - WebSocket connection duration
   - Disconnection rate
   - Audio packet loss

4. **Business Metrics:**
   - Booking completion rate (vs MVP)
   - Customer satisfaction (survey after call)
   - Escalation rate

### Monitoring Stack:
- Prometheus for metrics
- Grafana for dashboards
- Sentry for errors
- Custom dashboard for call quality

---

## Testing Strategy

### Unit Tests:
- WebSocket connection handling
- Audio encoding/decoding
- Buffer management
- State transitions

### Integration Tests:
- ASR → LLM → TTS pipeline
- Session state management
- Error recovery

### E2E Tests:
- Simulate complete calls
- Test interruption scenarios
- Verify booking flows
- Stress test concurrency

### User Acceptance Testing:
- Internal team makes test calls
- A/B test with real customers
- Compare to MVP metrics

---

## Migration Path (MVP → Streaming)

### Stage 1: Parallel Run (Week 1-2)
- Deploy streaming alongside MVP
- Route 10% of calls to streaming
- Compare metrics side-by-side

### Stage 2: Gradual Rollout (Week 3-4)
- If metrics look good, increase to 50%
- Monitor closely for issues
- Keep MVP as fallback

### Stage 3: Full Migration (Week 5-6)
- Route 100% to streaming
- Keep MVP code for emergencies
- Monitor for 2 weeks

### Stage 4: Cleanup (Week 7+)
- Remove MVP code path
- Optimize streaming performance
- Document learnings

---

## Alternative: Hybrid Approach

**Concept:** Use streaming for simple intents, record-then-process for complex ones.

### Routing Logic:
```python
if first_utterance_suggests_simple_faq():
    use_streaming()  # Fast response
else:
    use_recording()  # More processing time
```

**Pros:**
- Lower costs
- Best of both worlds

**Cons:**
- More complex code
- Inconsistent experience

---

## Timeline Estimate

### Minimal Viable Streaming (4-6 weeks):
- Week 1: WebSocket + echo server
- Week 2: Streaming ASR integration
- Week 3: Streaming LLM + TTS
- Week 4-5: Testing and refinement
- Week 6: Deployment and monitoring

### Production-Grade Streaming (8-12 weeks):
- Weeks 1-6: As above
- Weeks 7-8: State management and scale
- Weeks 9-10: Advanced features (interruption, fallbacks)
- Weeks 11-12: Performance tuning and optimization

---

## Decision: When to Implement?

### Implement Streaming If:
- ✅ MVP proves product-market fit
- ✅ Customers complain about latency
- ✅ Budget supports 3x cost increase
- ✅ Team has bandwidth for 6+ week project
- ✅ Competitive pressure (others offer real-time)

### Stick with MVP If:
- ❌ Still validating market fit
- ❌ Customers satisfied with current experience
- ❌ Need to conserve budget
- ❌ Higher priority features exist
- ❌ WhatsApp response is acceptable

---

## Recommended Next Steps

1. **Validate MVP First** (2-4 weeks)
   - Get 50+ real customer calls
   - Gather feedback on latency
   - Measure conversion rates

2. **Build Prototype** (1-2 weeks)
   - Simple WebSocket echo server
   - Test one conversation end-to-end
   - Measure actual latency

3. **Make Decision**
   - Review metrics and feedback
   - Calculate ROI (cost vs benefit)
   - Decide: build, defer, or hybrid

4. **If Go: Execute Plan**
   - Follow phase 1-5 above
   - Start with 10% rollout
   - Monitor and iterate

---

## References

- **Twilio Media Streams Docs:** https://www.twilio.com/docs/voice/twiml/stream
- **Deepgram Streaming API:** https://developers.deepgram.com/docs/streaming
- **ElevenLabs Streaming:** https://elevenlabs.io/docs/api-reference/streaming
- **OpenAI Streaming:** https://platform.openai.com/docs/api-reference/streaming

---

**Recommendation:** Ship MVP first, gather data, then decide on streaming based on actual customer needs and budget.

---

**Last Updated:** November 30, 2025
