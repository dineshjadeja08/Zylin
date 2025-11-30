# Zylin AI Receptionist 🤖

**Intelligent phone assistant for small and medium businesses**

Zylin is an AI-powered receptionist that handles incoming phone calls, answers FAQs, books appointments, and escalates urgent matters to business owners. Built with FastAPI, OpenAI GPT-4, and Twilio.

---

## 🎯 Features (MVP)

- ✅ **Text-Only LLM Brain** - Intent classification & natural conversation
- ✅ **FAQ Handling** - Answers questions about hours, services, pricing
- ✅ **Appointment Booking** - Collects customer details and schedules appointments
- ✅ **Urgent Escalation** - Detects emergencies and complaints, alerts owner
- 🚧 **ASR Integration** - Speech-to-text (coming soon)
- 🚧 **TTS Integration** - Text-to-speech (coming soon)
- 🚧 **Twilio Phone Integration** - Real phone call handling (coming soon)
- 🚧 **WhatsApp Notifications** - Confirmations and alerts (coming soon)

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
# Edit .env and add your OPENAI_API_KEY
```

### Run the API Server

```powershell
# Start FastAPI server
python main.py

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Test the LLM Brain

```powershell
# Interactive testing
python services/llm/test_harness.py

# Automated test suite
python services/llm/test_harness.py test
```

---

## 📡 API Endpoints

### Health Check
```http
GET /health
```

### Process Conversation
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

### Get Business Info
```http
GET /business
```

### Generate Conversation Summary
```http
POST /conversation/summary
Content-Type: application/json

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
├── main.py                    # FastAPI application
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
│
├── docs/
│   └── brain.md              # LLM brain design documentation
│
├── services/
│   ├── llm/
│   │   ├── brain.py          # Core LLM brain logic
│   │   ├── test_harness.py   # Interactive testing tool
│   │   └── README.md         # LLM service documentation
│   │
│   ├── asr/                  # Speech-to-text (coming soon)
│   ├── tts/                  # Text-to-speech (coming soon)
│   ├── orchestrator/         # Conversation orchestrator (coming soon)
│   ├── bookings/             # Booking management (coming soon)
│   └── notifications/        # WhatsApp notifications (coming soon)
│
└── tests/
    ├── conftest.py           # Pytest configuration
    ├── test_brain.py         # LLM brain unit tests
    ├── test_api.py           # API integration tests
    └── test_llm_brain.md     # Test cases documentation
```

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file with:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4-turbo-preview

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
