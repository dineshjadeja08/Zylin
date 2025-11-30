"""
Unit tests for Zylin LLM brain service.
"""

import pytest
from services.llm.brain import ZylinBrain, ConversationResponse, ExtractedData


@pytest.mark.asyncio
async def test_brain_initialization(zylin_brain):
    """Test that brain initializes correctly."""
    assert zylin_brain is not None
    assert zylin_brain.business_context.business_name == "Test Clinic"
    assert zylin_brain.system_prompt is not None


@pytest.mark.asyncio
async def test_faq_intent_classification(zylin_brain):
    """Test FAQ intent classification."""
    response = await zylin_brain.process_message("What are your hours?")
    
    assert response.intent == "faq"
    assert response.message is not None
    assert len(response.message) > 0
    assert not response.booking_complete
    assert not response.needs_escalation


@pytest.mark.asyncio
async def test_booking_intent_classification(zylin_brain):
    """Test booking intent classification."""
    response = await zylin_brain.process_message("I need an appointment")
    
    assert response.intent == "booking"
    assert response.message is not None
    assert not response.booking_complete  # Should be false without full details


@pytest.mark.asyncio
async def test_booking_data_extraction(zylin_brain):
    """Test extraction of booking data."""
    message = "I'd like to book for tomorrow at 3 PM. My name is John Doe and number is +919876543210."
    response = await zylin_brain.process_message(message)
    
    assert response.intent == "booking"
    assert response.extracted_data.name == "John Doe"
    assert response.extracted_data.phone == "+919876543210"
    assert response.extracted_data.time == "15:00"
    assert response.extracted_data.date is not None  # Should have extracted date


@pytest.mark.asyncio
async def test_urgent_intent_classification(zylin_brain):
    """Test urgent intent classification."""
    response = await zylin_brain.process_message("This is an emergency!")
    
    assert response.intent == "urgent"
    assert response.needs_escalation
    assert response.extracted_data.issue_summary is not None


@pytest.mark.asyncio
async def test_phone_number_formatting(zylin_brain):
    """Test that phone numbers are formatted with +91 prefix."""
    message = "Book appointment for tomorrow 2 PM. Name is Raj, phone 9876543210."
    response = await zylin_brain.process_message(message)
    
    assert response.extracted_data.phone == "+919876543210"


@pytest.mark.asyncio
async def test_conversation_with_history(zylin_brain, sample_conversation_history):
    """Test that conversation history is maintained."""
    response = await zylin_brain.process_message(
        "And do you do blood tests?",
        conversation_history=sample_conversation_history
    )
    
    assert response.intent == "faq"
    assert response.message is not None


@pytest.mark.asyncio
async def test_error_handling(zylin_brain):
    """Test error handling with invalid input."""
    # This should not crash
    response = await zylin_brain.process_message("")
    
    assert response is not None
    assert response.intent in ["faq", "booking", "urgent", "other"]


@pytest.mark.asyncio
async def test_conversation_summary(zylin_brain, sample_conversation_history):
    """Test conversation summary generation."""
    summary = await zylin_brain.get_conversation_summary(sample_conversation_history)
    
    assert summary is not None
    assert len(summary) > 0
    assert isinstance(summary, str)
