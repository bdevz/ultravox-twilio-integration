"""
Integration tests for request validation middleware and model validation.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import create_app
from app.models.agent import Agent, AgentConfig, AgentStatus
from app.models.call import CallRequest, CallResult, CallStatus
from app.api.routes import get_agent_service_dependency, get_call_service_dependency


@pytest.fixture
def app():
    """Create FastAPI app."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_services(app):
    """Mock both agent and call services."""
    mock_agent_service = AsyncMock()
    mock_call_service = AsyncMock()
    
    # Mock successful responses
    sample_agent = Agent(
        id="agent_123",
        config=AgentConfig(
            name="Test Agent",
            prompt="You are a helpful assistant"
        ),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        status=AgentStatus.ACTIVE
    )
    
    sample_call_result = CallResult(
        call_sid="CA" + "a" * 32,
        join_url="wss://example.com/join",
        status=CallStatus.INITIATED,
        created_at=datetime.now(timezone.utc),
        agent_id="agent_123",
        phone_number="+1234567890"
    )
    
    mock_agent_service.create_agent.return_value = sample_agent
    mock_agent_service.get_agent.return_value = sample_agent
    mock_agent_service.list_agents.return_value = [sample_agent]
    mock_agent_service.update_agent.return_value = sample_agent
    mock_call_service.initiate_call.return_value = sample_call_result
    
    # Override dependencies
    app.dependency_overrides[get_agent_service_dependency] = lambda: mock_agent_service
    app.dependency_overrides[get_call_service_dependency] = lambda: mock_call_service
    
    yield mock_agent_service, mock_call_service
    
    # Clean up
    app.dependency_overrides.clear()


class TestRequestValidationMiddleware:
    """Test request validation middleware functionality."""
    
    def test_content_length_validation_success(self, client, mock_services):
        """Test successful request with valid content length."""
        response = client.post(
            "/api/v1/agents",
            json={
                "name": "Test Agent",
                "prompt": "You are a helpful assistant"
            }
        )
        assert response.status_code == 201
    
    def test_content_length_validation_failure(self, client, mock_services):
        """Test request rejection for oversized content."""
        # Create a large payload
        large_prompt = "x" * (1024 * 1024 + 1)  # Larger than 1MB
        
        response = client.post(
            "/api/v1/agents",
            json={
                "name": "Test Agent",
                "prompt": large_prompt
            }
        )
        assert response.status_code == 413
        data = response.json()
        assert data["detail"]["error"] == "payload_too_large"
    
    def test_content_type_validation_success(self, client, mock_services):
        """Test successful request with correct content type."""
        response = client.post(
            "/api/v1/agents",
            json={
                "name": "Test Agent",
                "prompt": "You are a helpful assistant"
            },
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 201
    
    def test_content_type_validation_failure(self, client, mock_services):
        """Test request rejection for invalid content type."""
        response = client.post(
            "/api/v1/agents",
            data="name=Test&prompt=Hello",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 415
        data = response.json()
        assert data["detail"]["error"] == "unsupported_media_type"
    
    def test_json_structure_validation_call_success(self, client, mock_services):
        """Test successful call request with valid JSON structure."""
        response = client.post(
            "/api/v1/calls/agent_123",
            json={
                "phone_number": "+1234567890",
                "agent_id": "agent_123",
                "template_context": {"name": "John"}
            }
        )
        assert response.status_code == 201
    
    def test_json_structure_validation_call_missing_fields(self, client, mock_services):
        """Test call request rejection for missing required fields."""
        response = client.post(
            "/api/v1/calls/agent_123",
            json={
                "template_context": {"name": "John"}
                # Missing phone_number and agent_id
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "missing_required_fields"
        assert "phone_number" in data["detail"]["missing_fields"]
        assert "agent_id" in data["detail"]["missing_fields"]
    
    def test_json_structure_validation_agent_success(self, client, mock_services):
        """Test successful agent request with valid JSON structure."""
        response = client.post(
            "/api/v1/agents",
            json={
                "name": "Test Agent",
                "prompt": "You are a helpful assistant",
                "template_variables": {"greeting": "Hello"}
            }
        )
        assert response.status_code == 201
    
    def test_json_structure_validation_agent_missing_fields(self, client, mock_services):
        """Test agent request rejection for missing required fields."""
        response = client.post(
            "/api/v1/agents",
            json={
                "template_variables": {"greeting": "Hello"}
                # Missing name and prompt
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "missing_required_fields"
        assert "name" in data["detail"]["missing_fields"]
        assert "prompt" in data["detail"]["missing_fields"]
    
    def test_invalid_json_payload(self, client, mock_services):
        """Test request rejection for invalid JSON."""
        response = client.post(
            "/api/v1/agents",
            data='{"name": "Test", "prompt": invalid_json}',
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "invalid_json"
    
    def test_template_context_validation_invalid_type(self, client, mock_services):
        """Test call request rejection for invalid template_context type."""
        response = client.post(
            "/api/v1/calls/agent_123",
            json={
                "phone_number": "+1234567890",
                "agent_id": "agent_123",
                "template_context": "not_an_object"  # Should be dict
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "invalid_template_context"
    
    def test_template_variables_validation_invalid_type(self, client, mock_services):
        """Test agent request rejection for invalid template_variables type."""
        response = client.post(
            "/api/v1/agents",
            json={
                "name": "Test Agent",
                "prompt": "You are a helpful assistant",
                "template_variables": "not_an_object"  # Should be dict
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "invalid_template_variables"


class TestPhoneNumberValidation:
    """Test comprehensive phone number validation."""
    
    def test_valid_phone_numbers(self, client, mock_services):
        """Test various valid phone number formats."""
        valid_numbers = [
            "+1234567890",      # US format
            "+12345678901",     # US with extension
            "+441234567890",    # UK format
            "+33123456789",     # France format
            "+4912345678901",   # Germany format
            "+8112345678901",   # Japan format
            "+8612345678901",   # China format
            "+911234567890",    # India format
        ]
        
        for phone_number in valid_numbers:
            response = client.post(
                "/api/v1/calls/agent_123",
                json={
                    "phone_number": phone_number,
                    "agent_id": "agent_123",
                    "template_context": {}
                }
            )
            assert response.status_code == 201, f"Failed for phone number: {phone_number}"
    
    def test_invalid_phone_numbers(self, client, mock_services):
        """Test various invalid phone number formats."""
        invalid_numbers = [
            "",                 # Empty
            "1234567890",       # Missing +
            "+",                # Just +
            "+1",               # Too short
            "+123456",          # Too short
            "+12345678901234567890",  # Too long
            "+0123456789",      # Starts with 0 after +
            "abc123456789",     # Contains letters
            "+1-234-567-890",   # Contains invalid characters after cleaning
            "+1 234 567 890",   # Spaces (should be cleaned but let's test)
        ]
        
        for phone_number in invalid_numbers:
            response = client.post(
                "/api/v1/calls/agent_123",
                json={
                    "phone_number": phone_number,
                    "agent_id": "agent_123",
                    "template_context": {}
                }
            )
            assert response.status_code == 422, f"Should have failed for phone number: {phone_number}"
    
    def test_phone_number_cleaning(self, client, mock_services):
        """Test phone number cleaning and normalization."""
        # These should be cleaned and accepted
        numbers_to_clean = [
            "+1 (234) 567-8901",    # US format with formatting
            "+1.234.567.8901",      # Dots
            "+1-234-567-8901",      # Hyphens
            "+44 20 1234 5678",     # UK with spaces
        ]
        
        for phone_number in numbers_to_clean:
            response = client.post(
                "/api/v1/calls/agent_123",
                json={
                    "phone_number": phone_number,
                    "agent_id": "agent_123",
                    "template_context": {}
                }
            )
            assert response.status_code == 201, f"Failed for phone number: {phone_number}"
    
    def test_country_specific_validation(self, client, mock_services):
        """Test country-specific phone number validation."""
        # Test US numbers (must be exactly 10 digits after +1)
        invalid_us_numbers = [
            "+1234567890",      # 9 digits
            "+123456789012",    # 11 digits
        ]
        
        for phone_number in invalid_us_numbers:
            response = client.post(
                "/api/v1/calls/agent_123",
                json={
                    "phone_number": phone_number,
                    "agent_id": "agent_123",
                    "template_context": {}
                }
            )
            assert response.status_code == 422, f"Should have failed for US number: {phone_number}"


class TestTemplateContextValidation:
    """Test comprehensive template context validation."""
    
    def test_valid_template_contexts(self, client, mock_services):
        """Test various valid template context formats."""
        valid_contexts = [
            {},                                     # Empty
            {"name": "John"},                      # Simple string
            {"age": 25},                           # Integer
            {"price": 19.99},                      # Float
            {"active": True},                      # Boolean
            {"optional": None},                    # None
            {"data": [1, 2, 3]},                  # List
            {"nested": {"key": "value"}},         # Nested dict
            {"_private": "value"},                # Underscore key
            {"key123": "value"},                  # Alphanumeric key
        ]
        
        for context in valid_contexts:
            response = client.post(
                "/api/v1/calls/agent_123",
                json={
                    "phone_number": "+1234567890",
                    "agent_id": "agent_123",
                    "template_context": context
                }
            )
            assert response.status_code == 201, f"Failed for context: {context}"
    
    def test_invalid_template_context_keys(self, client, mock_services):
        """Test invalid template context keys."""
        invalid_contexts = [
            {"123key": "value"},           # Starts with number
            {"key-name": "value"},         # Contains hyphen
            {"key name": "value"},         # Contains space
            {"key.name": "value"},         # Contains dot
            {"": "value"},                 # Empty key
            {"agent_id": "value"},         # Reserved key
            {"system": "value"},           # Reserved key
            {"x" * 101: "value"},          # Key too long
        ]
        
        for context in invalid_contexts:
            response = client.post(
                "/api/v1/calls/agent_123",
                json={
                    "phone_number": "+1234567890",
                    "agent_id": "agent_123",
                    "template_context": context
                }
            )
            assert response.status_code == 422, f"Should have failed for context: {context}"
    
    def test_invalid_template_context_values(self, client, mock_services):
        """Test invalid template context values."""
        invalid_contexts = [
            {"key": "x" * 1001},           # String too long
            {"key": 2**32},                # Integer too large
            {"key": -2**32},               # Integer too small
            {"key": 1e11},                 # Float too large
            {"key": "<script>alert('xss')</script>"},  # Potentially dangerous content
            {"key": "javascript:alert(1)"},           # Dangerous protocol
        ]
        
        for context in invalid_contexts:
            response = client.post(
                "/api/v1/calls/agent_123",
                json={
                    "phone_number": "+1234567890",
                    "agent_id": "agent_123",
                    "template_context": context
                }
            )
            assert response.status_code == 422, f"Should have failed for context: {context}"
    
    def test_template_context_size_limits(self, client, mock_services):
        """Test template context size limitations."""
        # Test maximum number of variables
        large_context = {f"key{i}": f"value{i}" for i in range(51)}  # 51 keys (over limit)
        
        response = client.post(
            "/api/v1/calls/agent_123",
            json={
                "phone_number": "+1234567890",
                "agent_id": "agent_123",
                "template_context": large_context
            }
        )
        assert response.status_code == 422
    
    def test_template_context_nested_size_limits(self, client, mock_services):
        """Test nested template context size limitations."""
        # Create a large nested structure
        large_nested = {"data": ["x" * 100] * 50}  # Large serialized size
        
        response = client.post(
            "/api/v1/calls/agent_123",
            json={
                "phone_number": "+1234567890",
                "agent_id": "agent_123",
                "template_context": large_nested
            }
        )
        assert response.status_code == 422


class TestAgentValidation:
    """Test agent-specific validation scenarios."""
    
    def test_valid_agent_configurations(self, client, mock_services):
        """Test various valid agent configurations."""
        valid_configs = [
            {
                "name": "Simple Agent",
                "prompt": "You are helpful"
            },
            {
                "name": "Complex Agent",
                "prompt": "You are a helpful assistant",
                "voice": "custom",
                "language": "en-US",
                "template_variables": {"greeting": "Hello"}
            },
            {
                "name": "Agent_123",
                "prompt": "x" * 100,  # Long prompt
                "template_variables": {}
            }
        ]
        
        for config in valid_configs:
            response = client.post("/api/v1/agents", json=config)
            assert response.status_code == 201, f"Failed for config: {config}"
    
    def test_invalid_agent_names(self, client, mock_services):
        """Test invalid agent names."""
        invalid_configs = [
            {"name": "", "prompt": "Hello"},                    # Empty name
            {"name": "x" * 101, "prompt": "Hello"},            # Name too long
            {"name": "Agent@123", "prompt": "Hello"},          # Invalid characters
            {"name": "Agent<script>", "prompt": "Hello"},      # Dangerous content
        ]
        
        for config in invalid_configs:
            response = client.post("/api/v1/agents", json=config)
            assert response.status_code == 422, f"Should have failed for config: {config}"
    
    def test_invalid_agent_prompts(self, client, mock_services):
        """Test invalid agent prompts."""
        invalid_configs = [
            {"name": "Agent", "prompt": ""},                   # Empty prompt
            {"name": "Agent", "prompt": "x" * 10001},         # Prompt too long
        ]
        
        for config in invalid_configs:
            response = client.post("/api/v1/agents", json=config)
            assert response.status_code == 422, f"Should have failed for config: {config}"
    
    def test_invalid_language_codes(self, client, mock_services):
        """Test invalid language codes."""
        invalid_configs = [
            {"name": "Agent", "prompt": "Hello", "language": "english"},     # Invalid format
            {"name": "Agent", "prompt": "Hello", "language": "en-us"},       # Wrong case
            {"name": "Agent", "prompt": "Hello", "language": "en-USA"},      # Too long
            {"name": "Agent", "prompt": "Hello", "language": "123"},         # Numbers
        ]
        
        for config in invalid_configs:
            response = client.post("/api/v1/agents", json=config)
            assert response.status_code == 422, f"Should have failed for config: {config}"


class TestEndToEndValidation:
    """Test end-to-end validation scenarios."""
    
    def test_complete_call_flow_validation(self, client, mock_services):
        """Test complete call flow with all validation steps."""
        # 1. Create agent with validation
        agent_response = client.post(
            "/api/v1/agents",
            json={
                "name": "Test Agent",
                "prompt": "You are a helpful assistant",
                "template_variables": {"greeting": "Hello {name}"}
            }
        )
        assert agent_response.status_code == 201
        
        # 2. Initiate call with validation
        call_response = client.post(
            "/api/v1/calls/agent_123",
            json={
                "phone_number": "+1 (555) 123-4567",  # Will be cleaned
                "agent_id": "agent_123",
                "template_context": {
                    "name": "John Doe",
                    "account_type": "premium",
                    "balance": 1500.50
                }
            }
        )
        assert call_response.status_code == 201
    
    def test_validation_error_response_format(self, client, mock_services):
        """Test that validation errors return consistent response format."""
        response = client.post(
            "/api/v1/calls/agent_123",
            json={
                "phone_number": "invalid",
                "agent_id": "agent_123"
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        
        # Check response structure
        assert "detail" in data
        assert isinstance(data["detail"], list)
        
        # Check error details
        error = data["detail"][0]
        assert "type" in error
        assert "msg" in error
        assert "loc" in error
    
    def test_middleware_correlation_id_preservation(self, client, mock_services):
        """Test that correlation ID is preserved through validation."""
        correlation_id = "test-correlation-123"
        
        response = client.post(
            "/api/v1/agents",
            json={"name": "Test", "prompt": "Hello"},
            headers={"X-Correlation-ID": correlation_id}
        )
        
        assert response.status_code == 201
        assert response.headers.get("X-Correlation-ID") == correlation_id