# ASR (Speech-to-Text) Service

## Overview

This service converts speech audio to text using OpenAI's Whisper model. It supports multiple audio formats and can process files, bytes, or URLs.

## Features

- ✅ Multiple audio formats: .wav, .mp3, .m4a, .webm, .ogg, .flac
- ✅ File, bytes, and URL input
- ✅ Multi-language support (auto-detection)
- ✅ Context prompts for domain-specific accuracy
- ✅ Detailed metadata (language, duration)

## Usage

### Basic Transcription

```python
from services.asr.transcribe import ASRService

asr = ASRService()

# Transcribe a file
result = await asr.transcribe_file("tests/audio/sample.wav")
print(result.text)  # "Hello, I need an appointment tomorrow at 3 PM"
```

### With Language Hint

```python
# Specify language for better accuracy (ISO-639-1 codes)
result = await asr.transcribe_file(
    "tests/audio/hindi.wav",
    language="hi"  # Hindi
)
```

### With Context Prompt

```python
# Provide context for domain-specific terms
result = await asr.transcribe_file(
    "tests/audio/medical.wav",
    prompt="Medical clinic call about booking appointments."
)
```

### Transcribe from URL

```python
# Transcribe audio from Twilio recording URL
result = await asr.transcribe_url(
    "https://api.twilio.com/recordings/RE123456.mp3"
)
```

### Transcribe from Bytes

```python
# Useful for uploaded files or streaming
audio_bytes = request.files['audio'].read()
result = await asr.transcribe_bytes(
    audio_bytes,
    filename="recording.wav"
)
```

### Quick Utility Function

```python
from services.asr.transcribe import transcribe

# Auto-detects file vs URL
text = await transcribe("tests/audio/sample.wav")
text = await transcribe("https://example.com/audio.mp3")
```

## Testing

### Interactive Testing

```bash
python services/asr/test_asr.py
```

Commands:
- `test all` - Transcribe all files in tests/audio/
- `test <filename>` - Transcribe specific file
- `test prompt` - Test with context prompt
- `quit` - Exit

### Test All Files

```bash
python services/asr/test_asr.py all
```

### Test Specific File

```bash
python services/asr/test_asr.py tests/audio/sample.wav
```

## Creating Test Audio Files

### Option 1: Record with System Audio

**Windows (PowerShell):**
```powershell
# Install ffmpeg first (via chocolatey)
choco install ffmpeg

# Record 10 seconds of audio
ffmpeg -f dshow -i audio="Microphone" -t 10 tests/audio/test1.wav
```

### Option 2: Generate Test Audio

```python
# generate_test_audio.py
from gtts import gTTS

texts = [
    "I need an appointment tomorrow at 3 PM",
    "What are your operating hours?",
    "This is an emergency, please help!"
]

for i, text in enumerate(texts, 1):
    tts = gTTS(text, lang='en')
    tts.save(f'tests/audio/test{i}.mp3')
```

### Option 3: Use Online Tools

1. Record on your phone
2. Transfer to `tests/audio/`
3. Or use: https://online-voice-recorder.com/

## Supported Languages

Whisper supports 100+ languages. Common ones:
- `en` - English
- `hi` - Hindi
- `es` - Spanish
- `fr` - French
- `de` - German
- `zh` - Chinese
- `ja` - Japanese

Leave `language=None` for auto-detection.

## Audio Quality Guidelines

### Optimal Quality
- Sample rate: 16kHz or higher
- Format: .wav (uncompressed) or .mp3 (high bitrate)
- Clear speech, minimal background noise
- Single speaker preferred

### Acceptable Quality
- Phone call quality (8kHz)
- Moderate background noise
- Multiple speakers (may have errors)

### Poor Quality
- Very noisy environments
- Heavily compressed audio
- Multiple overlapping speakers

## Performance

### Latency
- Small files (<1 min): ~2-5 seconds
- Medium files (1-5 min): ~5-15 seconds
- Large files (5-30 min): ~15-60 seconds

### Accuracy
- Clear English: 95-99%
- Accented English: 85-95%
- Noisy environments: 70-85%
- Non-English: 80-95% (varies by language)

## Cost

OpenAI Whisper API pricing:
- $0.006 per minute of audio
- Example: 100 calls/day × 2 min avg = $1.20/day

## Error Handling

```python
try:
    result = await asr.transcribe_file("audio.wav")
except FileNotFoundError:
    print("Audio file not found")
except Exception as e:
    print(f"Transcription failed: {e}")
```

## Integration with Zylin Brain

```python
from services.asr.transcribe import ASRService
from services.llm.brain import ZylinBrain

asr = ASRService()
brain = ZylinBrain()

# 1. Transcribe audio
transcription = await asr.transcribe_file("call.wav")

# 2. Process with LLM
response = await brain.process_message(transcription.text)

# 3. Handle intent
if response.intent == "booking":
    # Create booking
    pass
```

## Configuration

### Environment Variables

```env
OPENAI_API_KEY=sk-your-key-here  # Required
```

### Advanced Options

```python
asr = ASRService(
    api_key="custom-key",
    model="whisper-1"  # Only option for API currently
)
```

## Limitations

- Max file size: 25 MB (OpenAI API limit)
- Max duration: No strict limit, but longer = higher cost
- Formats: Must be common formats (no proprietary codecs)
- Real-time streaming: Not supported by API (use Media Streams for that)

## Future Improvements

1. **Local Whisper**: Self-host for lower cost, higher privacy
2. **Streaming**: Real-time transcription with WebSockets
3. **Diarization**: Identify different speakers
4. **Confidence Scores**: Per-word confidence metrics
5. **Punctuation Control**: Better formatting options
6. **Custom Vocabulary**: Train on business-specific terms

## Troubleshooting

### "File not found"
- Check file path is correct
- Ensure file exists in tests/audio/
- Use absolute paths or relative from project root

### "Invalid audio format"
- Convert to supported format: .wav, .mp3, .m4a
- Check file isn't corrupted
- Try re-encoding: `ffmpeg -i input.mp3 output.wav`

### "API key invalid"
- Check OPENAI_API_KEY in .env
- Ensure key starts with "sk-"
- Verify key is active in OpenAI dashboard

### "Transcription is inaccurate"
- Add language hint: `language="en"`
- Use context prompt for domain terms
- Check audio quality (noise, volume)
- Try pre-processing audio (noise reduction)

## Next Steps

After ASR is working:
1. ✅ Complete task 3 (ASR integration)
2. → Move to task 4: TTS integration
3. → Build conversation orchestrator
4. → Integrate with Twilio webhooks
