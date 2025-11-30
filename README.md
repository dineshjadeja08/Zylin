# Zylin AI Receptionist 🤖

**Intelligent phone assistant for small and medium businesses**

Zylin is an AI-powered receptionist that handles incoming phone calls with **real-time audio streaming**, answers FAQs, books appointments, and escalates urgent matters to business owners. Built with FastAPI, OpenAI GPT-4, Deepgram, and Twilio.

---

## 🎯 Features

### ✅ Core Features (Complete)
- **Real-Time Streaming** - Low-latency bi-directional audio (<3s response time)
- **LLM Brain** - GPT-4 powered intent classification & natural conversation
- **FAQ Handling** - Answers questions about hours, services, pricing
- **Appointment Booking** - Collects customer details and schedules appointments
- **Urgent Escalation** - Detects emergencies and complaints, alerts owner
- **ASR Integration** - Deepgram streaming + OpenAI Whisper (batch)
- **TTS Integration** - OpenAI TTS with 6 voice options
- **Twilio Integration** - WebSocket streaming + legacy recording modes
- **WhatsApp Notifications** - Booking confirmations and urgent alerts
- **Call Logging** - Complete transcripts, analytics, and metrics

### 🎉 NEW: Real-Time Streaming
- **WebSocket-based** audio streaming via Twilio Media Streams
- **Sub-3-second latency** for natural conversations
- **Interruption handling** - Caller can interrupt Zylin
- **Latency tracking** - Monitor performance metrics per call
- **Mock mode** - Test without API costs

See [`docs/STREAMING_COMPLETE.md`](docs/STREAMING_COMPLETE.md) for details.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key
- (Optional) Twilio account for phone integration

### Installation

```powershell
# Clone the repository
git clone https://github.com/dineshjadeja08/Zylin.git
cd Zylin

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
Copy-Item .env.example .env
# Edit .env and add your API keys:
# - OPENAI_API_KEY (required)
# - DEEPGRAM_API_KEY (optional, for real-time ASR)
# - TWILIO_* credentials (optional, for phone calls)
```

### Run the API Server

#### Option 1: Mock Mode (No API Costs)

```powershell
# Use mock streaming services for testing
$env:USE_MOCK_STREAMING = "true"
python main.py

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

#### Option 2: Production Mode (Real-Time Streaming)

```powershell
# Requires OPENAI_API_KEY and DEEPGRAM_API_KEY in .env
python main.py

# WebSocket endpoint: ws://localhost:8000/media-stream
# For Twilio: wss://your-domain.com/media-stream
```

### Test the System

```powershell
# 1. Test LLM Brain
python services/llm/test_harness.py

# 2. Test Streaming Pipeline
python -m pytest tests/test_streaming.py -v

# 3. Run Full Demo
python tests/demo.py

# 4. Test All Components
python -m pytest tests/ -v
```

---

## 📡 API Endpoints

### REST API

#### Health Check
```http
GET /health
GET /
```

#### Process Conversation (Text)
```http
POST /conversation
Content-Type: application/json

{
  "message": "I need an appointment tomorrow at 3 PM",
  "conversation_history": [
    {"role": "user", "content": "Previous message"},
    {"role": "assistant", "content": "Previous response"}
  ]
}
```

**Response:**
```json
{
  "intent": "booking",
  "message": "Great! May I have your name please?",
  "extracted_data": {
    "date": "2025-12-01",
    "time": "15:00"
  },
  "booking_complete": false,
  "needs_escalation": false
}
```

#### Twilio Webhooks
```http
POST /api/twilio/voice          # Incoming calls (streaming)
POST /api/twilio/voice-legacy   # Incoming calls (recording)
POST /api/twilio/recording/{id} # Recording received
POST /api/twilio/status         # Call status updates
```

### WebSocket API

#### Real-Time Audio Streaming
```
ws://localhost:8000/media-stream
wss://your-domain.com/media-stream  (production)
```

Handles Twilio Media Streams for bidirectional audio.

**Message Format:**
```json
// Start
{"event": "start", "streamSid": "STxxx", "start": {...}}

// Audio chunk (incoming)
{"event": "media", "media": {"payload": "base64-mulaw"}}

// Audio chunk (outgoing)
{"event": "media", "streamSid": "STxxx", "media": {"payload": "base64-mulaw"}}

// Stop
{"event": "stop", "streamSid": "STxxx"}
```

### Other Endpoints
```http
GET /business                    # Business context
POST /conversation/summary       # Generate summary
[
  {"role": "user", "content": "Message 1"},
  {"role": "assistant", "content": "Response 1"}
]
```

---

## 🧪 Testing

### Run Unit Tests
```powershell
pytest tests/test_brain.py -v
```

### Run API Tests
```powershell
pytest tests/test_api.py -v
```

### Run All Tests
```powershell
pytest -v
```

---

## 🏗️ Project Structure

```
Zylin/
├── main.py                         # FastAPI app + WebSocket endpoint
├── requirements.txt                # Python dependencies
├── .env.example                   # Environment variables template
├── .gitignore                     # Git ignore rules
│
├── api/
│   └── twilio_webhook.py          # Twilio webhook handlers
│
├── docs/
│   ├── brain.md                   # LLM brain design
│   ├── streaming_plan.md          # Streaming architecture (original plan)
│   └── STREAMING_COMPLETE.md      # Streaming implementation guide
│
├── infra/
│   └── twilio-config.md           # Twilio setup guide
│
├── services/
│   ├── llm/
│   │   ├── brain.py               # GPT-4 conversation engine
│   │   └── test_harness.py        # Interactive testing
│   │
│   ├── asr/
│   │   ├── transcribe.py          # Whisper + Deepgram streaming ASR
│   │   └── test_asr.py            # ASR tests
│   │
│   ├── tts/
│   │   ├── synthesize.py          # OpenAI TTS + streaming
│   │   └── test_tts.py            # TTS tests
│   │
│   ├── orchestrator/
│   │   ├── session_manager.py     # Multi-turn conversation manager
│   │   └── streaming_pipeline.py  # Real-time streaming orchestrator
│   │
│   ├── bookings/
│   │   └── store.py               # SQLite booking storage
│   │
│   ├── notifications/
│   │   └── whatsapp.py            # Twilio WhatsApp messaging
│   │
│   ├── logging/
│   │   └── log_store.py           # Call logging & analytics
│   │
│   └── utils/
│       └── audio_codec.py         # μ-law encoding/decoding
│
├── scripts/
│   └── daily_report.py            # Analytics reports
│
└── tests/
    ├── conftest.py                # Pytest configuration
    ├── test_brain.py              # LLM tests
    ├── test_api.py                # API tests
    ├── test_e2e.py                # End-to-end tests
    ├── test_streaming.py          # Streaming pipeline tests
    └── demo.py                    # Full system demo
```

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file with:

```env
# OpenAI Configuration (Required)
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4-turbo-preview

# Deepgram Configuration (Optional - for real-time ASR)
DEEPGRAM_API_KEY=your-deepgram-key

# Streaming Configuration
USE_MOCK_STREAMING=false           # true for testing without API costs
PUBLIC_URL=https://your-domain.com # Your public URL for webhooks

# Twilio Configuration (Optional - for phone integration)
TWILIO_ACCOUNT_SID=ACxxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WHATSAPP_NUMBER=+14155238886

# Business Information
BUSINESS_NAME=Your Business Name
BUSINESS_PHONE=+911234567890
BUSINESS_ADDRESS=Your business address
OWNER_PHONE=+919876543210

# Application Settings
APP_ENV=development
LOG_LEVEL=INFO
```

### Business Context

Update business-specific information in `services/llm/brain.py`:
- Operating hours
- Services offered
- Pricing information
- Contact details

---

## 📊 Intent Classification

Zylin classifies conversations into 4 intents:

### 1. FAQ Intent
- Questions about hours, location, services, pricing
- Example: *"What time do you close?"*

### 2. Booking Intent
- Appointment scheduling requests
- Collects: name, phone, date, time
- Example: *"I need an appointment tomorrow at 3 PM"*

### 3. Urgent Intent
- Emergencies, complaints, escalations
- Triggers owner notification
- Example: *"This is an emergency!"*

### 4. Other Intent
- Unclear or off-topic conversations
- Asks for clarification

---

## 🛣️ Roadmap

### ✅ Phase 1: Text-Only LLM Brain (COMPLETED)
- System prompt design
- Intent classification
- Data extraction
- Test harness

### 🚧 Phase 2: Audio Processing (IN PROGRESS)
- ASR integration (Whisper/OpenAI)
- TTS integration (ElevenLabs/OpenAI)
- Audio file testing

### 📋 Phase 3: Conversation Orchestration (PLANNED)
- Session management
- Multi-turn conversations
- Context handling

### 📋 Phase 4: Telephony Integration (PLANNED)
- Twilio webhook endpoints
- Call recording processing
- Phone number management

### 📋 Phase 5: Business Actions (PLANNED)
- Booking database (SQLite)
- WhatsApp notifications (Twilio)
- Call logging & analytics

### 📋 Phase 6: Production Ready (PLANNED)
- Error handling & retries
- Rate limiting
- Authentication
- Deployment (Docker)

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🆘 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact: [your-email@example.com]

---

## 📚 Documentation

- [PRD (Product Requirements Document)](prd.md)
- [Brain Design](docs/brain.md)
- [Test Cases](tests/test_llm_brain.md)
- [LLM Service README](services/llm/README.md)

---

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Powered by [OpenAI GPT-4](https://openai.com/)
- Phone integration via [Twilio](https://www.twilio.com/)

---

**Made with ❤️ for small businesses**
