"""
Integration tests for FastAPI endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Fixture providing test client."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_conversation_endpoint(client):
    """Test conversation processing endpoint."""
    request_data = {
        "message": "What are your hours?",
        "conversation_history": None
    }
    
    response = client.post("/conversation", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "intent" in data
    assert "message" in data
    assert "extracted_data" in data


def test_conversation_with_history(client):
    """Test conversation with history."""
    request_data = {
        "message": "And do you do blood tests?",
        "conversation_history": [
            {"role": "user", "content": "What are your hours?"},
            {"role": "assistant", "content": "We're open 9 AM to 6 PM."}
        ]
    }
    
    response = client.post("/conversation", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "faq"


def test_business_info_endpoint(client):
    """Test business info endpoint."""
    response = client.get("/business")
    
    assert response.status_code == 200
    data = response.json()
    assert "business_name" in data
    assert "services" in data


def test_conversation_summary_endpoint(client):
    """Test conversation summary endpoint."""
    request_data = [
        {"role": "user", "content": "What are your hours?"},
        {"role": "assistant", "content": "We're open 9 AM to 6 PM."}
    ]
    
    response = client.post("/conversation/summary", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data


def test_invalid_conversation_request(client):
    """Test invalid request handling."""
    request_data = {
        "message": ""  # Empty message should fail validation
    }
    
    response = client.post("/conversation", json=request_data)
    
    assert response.status_code == 422  # Validation error
