# Zylin LLM Service

## Overview

This service implements the core "brain" of Zylin - an LLM-powered conversational agent that:
- Classifies caller intent (FAQ, booking, urgent, other)
- Extracts structured data from natural language
- Maintains conversation context
- Generates appropriate responses

## Architecture

### Core Components

1. **ZylinBrain** (`brain.py`)
   - Main LLM interface
   - System prompt management
   - Intent classification
   - Data extraction
   - Response generation

2. **Test Harness** (`test_harness.py`)
   - Interactive testing mode
   - Automated test suite
   - Performance metrics

### Response Structure

```python
class ConversationResponse:
    intent: "faq" | "booking" | "urgent" | "other"
    message: str  # Natural language response
    extracted_data: ExtractedData
    booking_complete: bool
    needs_escalation: bool

class ExtractedData:
    name: str | None
    phone: str | None
    date: str | None  # YYYY-MM-DD
    time: str | None  # HH:MM 24-hour
    notes: str | None
    issue_summary: str | None
```

## Usage

### Interactive Testing

```bash
python services/llm/test_harness.py
```

This launches an interactive chat where you can:
- Type messages as a caller
- See intent classification and data extraction in real-time
- Test conversation flows
- Type `reset` to start over
- Type `history` to see conversation
- Type `quit` to exit

### Automated Testing

```bash
python services/llm/test_harness.py test
```

Runs the full test suite from `tests/test_llm_brain.md` and reports:
- Test pass/fail for each case
- Overall accuracy percentage
- Failed test details

**Success Criteria:** ≥90% accuracy (18/20 tests passing)

### Using in Code

```python
from services.llm.brain import ZylinBrain

# Initialize
brain = ZylinBrain()

# Process a message
response = await brain.process_message(
    "I need an appointment tomorrow at 3 PM",
    conversation_history=[...]  # optional
)

# Check results
print(response.intent)  # "booking"
print(response.message)  # Natural response
print(response.extracted_data.date)  # "2025-12-01"
print(response.booking_complete)  # False (missing name/phone)
```

## Configuration

### Environment Variables

Required:
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_MODEL`: Model to use (default: `gpt-4-turbo-preview`)

Business context (optional, has defaults):
- `BUSINESS_NAME`
- `BUSINESS_PHONE`
- `BUSINESS_ADDRESS`
- `OWNER_PHONE`

### Business Context

Business information is injected into the system prompt. Update `DEFAULT_BUSINESS_CONTEXT` in `brain.py` or pass custom `BusinessContext` when initializing.

```python
from services.llm.brain import ZylinBrain, BusinessContext

custom_context = BusinessContext(
    business_name="My Clinic",
    business_type="healthcare",
    phone="+911234567890",
    address="123 Street, City",
    hours={...},
    services=[...],
    pricing={...},
    owner_phone="+919876543210"
)

brain = ZylinBrain(business_context=custom_context)
```

## Intent Classification

### FAQ Intent
Triggered by: questions about hours, location, services, pricing
- No data extraction needed
- Responds with business information
- Asks if anything else needed

### Booking Intent
Triggered by: appointment requests, scheduling language
- Extracts: name, phone, date, time
- Asks follow-up questions for missing data
- Sets `booking_complete=True` when all 4 fields collected

### Urgent Intent
Triggered by: emergency keywords, complaint language, angry tone
- Extracts: issue_summary
- Sets `needs_escalation=True`
- Promises owner callback

### Other Intent
Triggered by: unclear requests, off-topic conversation
- Asks for clarification
- Offers alternatives

## Date/Time Parsing

The brain converts natural language dates to structured format:
- "tomorrow" → YYYY-MM-DD (next day)
- "next Tuesday" → YYYY-MM-DD (upcoming Tuesday)
- "3 PM" → "15:00" (24-hour format)
- "four thirty" → "16:30"

## Phone Number Handling

Indian phone numbers are automatically prefixed with +91 if missing:
- "9876543210" → "+919876543210"
- "+919876543210" → "+919876543210" (unchanged)

## Error Handling

If the LLM fails or returns invalid JSON:
- Returns fallback response with `other` intent
- Logs error for debugging
- Asks user to try again

## Testing Strategy

### Phase 1: Manual Review
- Review system prompt for clarity
- Check example dialogues make sense
- Validate business context format

### Phase 2: Interactive Testing
- Test various phrasings
- Check tone and professionalism
- Verify natural conversation flow
- Test edge cases (interruptions, corrections)

### Phase 3: Automated Testing
- Run full test suite
- Check ≥90% accuracy
- Analyze failure patterns
- Iterate on prompt

## Performance Tuning

### Temperature
Currently: `0.4`
- Lower (0.2-0.3): More consistent, less creative
- Higher (0.5-0.7): More natural, less predictable

### Max Tokens
Currently: `500`
- Sufficient for brief responses
- Increase if responses get cut off

### Model Selection
- `gpt-4-turbo-preview`: Best quality, higher cost
- `gpt-3.5-turbo`: Faster, lower cost, slightly less accurate
- `gpt-4`: Good balance (currently used)

## Limitations & Future Improvements

### Current Limitations
- No memory across sessions (stateless)
- Limited context window (conversation history may get trimmed)
- No calendar integration (can't check conflicts)
- English and Hindi only (no multilingual support yet)
- No voice tone detection (relies on transcript only)

### Planned Improvements
1. Add conversation memory/session storage
2. Integrate with calendar for conflict detection
3. Support more languages
4. Add sentiment analysis for better urgent detection
5. Fine-tune on domain-specific conversations
6. Add custom function calling for complex actions

## Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check raw LLM responses by adding print statements in `brain.py`:
```python
print(f"Raw LLM response: {response_text}")
```

## API Costs

Approximate cost per call (GPT-4 Turbo):
- Average conversation: 500-1000 tokens
- Cost: ~$0.01-0.02 per conversation
- 100 calls/day = ~$1-2/day

Consider using GPT-3.5 Turbo for production to reduce costs by 10x.

## Security Notes

- API keys should be in `.env` (never committed)
- Conversation logs may contain PII (mask phone numbers)
- Consider GDPR compliance for EU customers
- Implement rate limiting to prevent abuse

## Next Steps

After LLM brain is validated:
1. ✅ Complete task 1 (this service)
2. → Move to task 2: Wrap in FastAPI endpoints
3. → Add ASR integration
4. → Add TTS integration
5. → Build conversation orchestrator
