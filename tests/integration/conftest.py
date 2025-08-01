"""
Configuration and fixtures for integration tests.
"""

import os
import pytest
from typing import Optional
from app.services.config_service import ConfigService
from app.services.http_client_service import HTTPClientService
from app.services.agent_service import AgentService
from app.services.call_service import CallService
from app.models.config import UltravoxConfig, TwilioConfig


@pytest.fixture(scope="session")
def integration_config():
    """
    Integration test configuration.
    
    Loads configuration from environment variables with test prefixes.
    """
    return {
        "ultravox_api_key": os.getenv("TEST_ULTRAVOX_API_KEY"),
        "ultravox_base_url": os.getenv("TEST_ULTRAVOX_BASE_URL", "https://api.ultravox.ai"),
        "twilio_account_sid": os.getenv("TEST_TWILIO_ACCOUNT_SID"),
        "twilio_auth_token": os.getenv("TEST_TWILIO_AUTH_TOKEN"),
        "twilio_phone_number": os.getenv("TEST_TWILIO_PHONE_NUMBER"),
        "test_phone_number": os.getenv("TEST_PHONE_NUMBER", "+15551234567"),  # Safe test number
    }


@pytest.fixture
def skip_if_no_credentials(integration_config):
    """
    Skip test if required credentials are not available.
    """
    def _skip_if_missing(*required_keys):
        missing = [key for key in required_keys if not integration_config.get(key)]
        if missing:
            pytest.skip(f"Missing required credentials: {', '.join(missing)}")
    
    return _skip_if_missing


@pytest.fixture
def ultravox_config(integration_config, skip_if_no_credentials):
    """
    Ultravox configuration for integration tests.
    """
    skip_if_no_credentials("ultravox_api_key")
    
    return UltravoxConfig(
        api_key=integration_config["ultravox_api_key"],
        base_url=integration_config["ultravox_base_url"]
    )


@pytest.fixture
def twilio_config(integration_config, skip_if_no_credentials):
    """
    Twilio configuration for integration tests.
    """
    skip_if_no_credentials("twilio_account_sid", "twilio_auth_token", "twilio_phone_number")
    
    return TwilioConfig(
        account_sid=integration_config["twilio_account_sid"],
        auth_token=integration_config["twilio_auth_token"],
        phone_number=integration_config["twilio_phone_number"]
    )


@pytest.fixture
def integration_config_service(ultravox_config, twilio_config):
    """
    Configuration service with real credentials for integration tests.
    """
    config_service = ConfigService()
    
    # Override the config methods to return test configurations
    config_service.get_ultravox_config = lambda: ultravox_config
    config_service.get_twilio_config = lambda: twilio_config
    
    return config_service


@pytest.fixture
def http_client():
    """
    HTTP client service for integration tests.
    """
    return HTTPClientService()


@pytest.fixture
def agent_service(integration_config_service, http_client):
    """
    Agent service with real dependencies for integration tests.
    """
    return AgentService(http_client, integration_config_service)


@pytest.fixture
def call_service(integration_config_service, http_client):
    """
    Call service with real dependencies for integration tests.
    """
    return CallService(integration_config_service, http_client)


@pytest.fixture
def test_agent_config():
    """
    Test agent configuration for integration tests.
    """
    from app.models.agent import AgentConfig
    
    return AgentConfig(
        name="Integration Test Agent",
        prompt="You are a helpful test assistant. Keep responses brief and confirm you received the template variables.",
        voice="default",
        language="en",
        template_variables={
            "test_var": "This is a test variable",
            "user_name": "Integration Test User"
        }
    )


@pytest.fixture
def cleanup_agents():
    """
    Fixture to track and cleanup test agents.
    """
    created_agents = []
    
    def add_agent(agent_id: str):
        created_agents.append(agent_id)
    
    yield add_agent
    
    # Cleanup after test
    if created_agents:
        # Note: In a real implementation, you might want to clean up test agents
        # For now, we'll just log them
        print(f"Test agents created (manual cleanup may be needed): {created_agents}")


@pytest.fixture
def test_call_request():
    """
    Test call request for integration tests.
    """
    from app.models.call import CallRequest
    
    return CallRequest(
        phone_number="+15551234567",  # Safe test number that won't actually be called
        template_context={
            "user_name": "Integration Test User",
            "test_scenario": "integration_test",
            "timestamp": "2024-01-01T00:00:00Z"
        },
        agent_id=""  # Will be set by individual tests
    )


# Markers for different types of integration tests
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "ultravox: mark test as requiring Ultravox API credentials"
    )
    config.addinivalue_line(
        "markers", "twilio: mark test as requiring Twilio API credentials"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )