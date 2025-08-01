"""
Tests for the main FastAPI application.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    app = create_app()
    return TestClient(app)

def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/api/v1/health")
    # Health check might return 503 if configuration is missing in test environment
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    assert data["service"] == "ultravox-twilio-integration"

def test_app_creation():
    """Test that the app can be created successfully."""
    app = create_app()
    assert app is not None
    assert app.title == "Ultravox-Twilio Integration Service"