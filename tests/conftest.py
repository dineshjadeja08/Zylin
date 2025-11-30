"""
Pytest configuration and fixtures for Zylin tests.
"""

import pytest
import os
from dotenv import load_dotenv

# Load test environment variables
load_dotenv()

# Set test environment
os.environ["APP_ENV"] = "test"
os.environ["LOG_LEVEL"] = "DEBUG"


@pytest.fixture
def test_business_context():
    """Fixture providing test business context."""
    from services.llm.brain import BusinessContext
    
    return BusinessContext(
        business_name="Test Clinic",
        business_type="healthcare",
        phone="+911234567890",
        address="123 Test Street, Test City, TS 123456",
        hours={
            "monday": "9:00 AM - 6:00 PM",
            "tuesday": "9:00 AM - 6:00 PM",
            "wednesday": "9:00 AM - 6:00 PM",
            "thursday": "9:00 AM - 6:00 PM",
            "friday": "9:00 AM - 6:00 PM",
            "saturday": "10:00 AM - 2:00 PM",
            "sunday": "Closed",
        },
        services=["General consultation", "Blood tests", "X-ray"],
        pricing={
            "consultation": "₹500",
            "blood_test": "₹800-2000",
            "xray": "₹1200"
        },
        owner_phone="+919876543210"
    )


@pytest.fixture
async def zylin_brain(test_business_context):
    """Fixture providing ZylinBrain instance."""
    from services.llm.brain import ZylinBrain
    
    brain = ZylinBrain(business_context=test_business_context)
    return brain


@pytest.fixture
def sample_conversation_history():
    """Fixture providing sample conversation history."""
    return [
        {"role": "user", "content": "What are your hours?"},
        {"role": "assistant", "content": "We're open Monday to Friday 9 AM to 6 PM, and Saturday 10 AM to 2 PM."}
    ]
