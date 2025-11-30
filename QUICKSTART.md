# Zylin Quick Start Guide

## 🚀 Getting Started (5 Minutes)

### 1. Install Dependencies

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install packages
pip install -r requirements.txt
```

### 2. Set Up Environment

```powershell
# Copy example env file
Copy-Item .env.example .env

# Edit .env and add your OpenAI API key
notepad .env
```

Minimum required:
```env
OPENAI_API_KEY=sk-your-key-here
```

### 3. Test the LLM Brain

```powershell
# Interactive chat mode
python services/llm/test_harness.py

# Try these messages:
# - "What are your hours?"
# - "I need an appointment tomorrow at 3 PM"
# - "This is an emergency!"

# Run automated tests
python services/llm/test_harness.py test
```

### 4. Start the API Server

```powershell
# Start FastAPI server
python main.py

# Visit http://localhost:8000/docs for API documentation
```

### 5. Test API with Sample Request

```powershell
# Test conversation endpoint
curl -X POST "http://localhost:8000/conversation" `
  -H "Content-Type: application/json" `
  -d '{"message": "What are your hours?"}'
```

---

## 🧪 Testing Individual Services

### Test ASR (Speech-to-Text)

```powershell
# Place audio files in tests/audio/
# Then run:
python services/asr/test_asr.py all
```

### Test TTS (Text-to-Speech)

```powershell
# Generate audio for all test phrases
python services/tts/test_tts.py phrases

# Test all voices
python services/tts/test_tts.py voices
```

### View Daily Report

```powershell
# Today's stats
python scripts/daily_report.py

# Yesterday's stats
python scripts/daily_report.py --yesterday
```

---

## 📁 Project Overview

```
Zylin/
├── main.py                 # FastAPI app (run this!)
├── services/
│   ├── llm/               # LLM brain
│   ├── asr/               # Speech-to-text
│   ├── tts/               # Text-to-speech
│   ├── orchestrator/      # Conversation flow
│   ├── bookings/          # Appointment storage
│   ├── notifications/     # WhatsApp alerts
│   └── logging/           # Call logs
├── tests/                 # Test files & audio
└── data/                  # SQLite database
```

---

## 🎯 Common Tasks

### Add Test Audio File

1. Record audio (phone call simulation)
2. Save as `.wav` or `.mp3` in `tests/audio/`
3. Run: `python services/asr/test_asr.py all`

### Change Business Information

Edit `services/llm/brain.py`:
- Update `DEFAULT_BUSINESS_CONTEXT`
- Or set environment variables in `.env`

### Check Database

```powershell
# View bookings
sqlite3 data/zylin.db "SELECT * FROM bookings;"

# View call logs
sqlite3 data/zylin.db "SELECT * FROM call_logs;"
```

### Enable WhatsApp (Optional)

Add to `.env`:
```env
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
TWILIO_WHATSAPP_NUMBER=+14155238886
```

---

## ⚡ Next Steps

1. ✅ Test LLM brain with various queries
2. ✅ Add test audio files and verify ASR
3. ✅ Listen to generated TTS audio
4. 🚧 Integrate Twilio webhooks (see docs)
5. 🚧 Deploy to production

---

## 🆘 Troubleshooting

### "Module not found" errors
```powershell
pip install -r requirements.txt
```

### "OpenAI API key not set"
```powershell
# Check .env file exists and has:
OPENAI_API_KEY=sk-...
```

### "Permission denied" on scripts
```powershell
# Run from project root:
python services/llm/test_harness.py
# NOT: cd services/llm && python test_harness.py
```

### Database locked
```powershell
# Close any SQLite browser/viewer
# Or delete and recreate:
Remove-Item data/zylin.db
python main.py  # Will recreate DB
```

---

## 📚 Full Documentation

- [README.md](README.md) - Full project documentation
- [prd.md](prd.md) - Product requirements
- [docs/brain.md](docs/brain.md) - LLM brain design
- Service READMEs in each `services/*/README.md`

---

**Ready to build? Start with step 1! 🚀**
