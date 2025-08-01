"""Unit tests for data models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models import (
    Agent, AgentConfig, AgentStatus,
    CallRequest, CallResult, CallStatus, TwilioCallResult,
    UltravoxConfig, TwilioConfig, AppConfig, ErrorResponse
)


class TestAgentConfig:
    """Test cases for AgentConfig model."""
    
    def test_valid_agent_config(self):
        """Test valid agent configuration."""
        config = AgentConfig(
            name="Test Agent",
            prompt="You are a helpful assistant",
            voice="default",
            language="en",
            template_variables={"user_name": "John", "context": "support"}
        )
        
        assert config.name == "Test Agent"
        assert config.prompt == "You are a helpful assistant"
        assert config.voice == "default"
        assert config.language == "en"
        assert config.template_variables == {"user_name": "John", "context": "support"}
    
    def test_minimal_agent_config(self):
        """Test minimal valid agent configuration."""
        config = AgentConfig(
            name="Minimal Agent",
            prompt="Hello"
        )
        
        assert config.name == "Minimal Agent"
        assert config.prompt == "Hello"
        assert config.voice == "default"
        assert config.language == "en"
        assert config.template_variables == {}
    
    def test_invalid_name_empty(self):
        """Test validation error for empty name."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(name="", prompt="Hello")
        
        assert "String should have at least 1 character" in str(exc_info.value)
    
    def test_invalid_name_special_chars(self):
        """Test validation error for invalid characters in name."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(name="Test@Agent!", prompt="Hello")
        
        assert "can only contain letters, numbers, spaces, hyphens, and underscores" in str(exc_info.value)
    
    def test_name_whitespace_trimming(self):
        """Test name whitespace trimming."""
        config = AgentConfig(name="  Test Agent  ", prompt="Hello")
        assert config.name == "Test Agent"
    
    def test_invalid_language_format(self):
        """Test validation error for invalid language format."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(name="Test", prompt="Hello", language="invalid")
        
        assert 'Language must be in format "en" or "en-US"' in str(exc_info.value)
    
    def test_valid_language_formats(self):
        """Test valid language formats."""
        config1 = AgentConfig(name="Test", prompt="Hello", language="en")
        config2 = AgentConfig(name="Test", prompt="Hello", language="en-US")
        
        assert config1.language == "en"
        assert config2.language == "en-US"
    
    def test_invalid_template_variables_key(self):
        """Test validation error for invalid template variable key."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(
                name="Test",
                prompt="Hello",
                template_variables={"123invalid": "value"}
            )
        
        assert "must be a valid identifier" in str(exc_info.value)
    
    def test_invalid_template_variables_type(self):
        """Test validation error for non-string template variables."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(
                name="Test",
                prompt="Hello",
                template_variables={"key": 123}
            )
        
        assert "Input should be a valid string" in str(exc_info.value)


class TestAgent:
    """Test cases for Agent model."""
    
    def test_valid_agent(self):
        """Test valid agent model."""
        config = AgentConfig(name="Test Agent", prompt="Hello")
        agent = Agent(
            id="agent-123",
            config=config,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status=AgentStatus.ACTIVE
        )
        
        assert agent.id == "agent-123"
        assert agent.config.name == "Test Agent"
        assert agent.status == AgentStatus.ACTIVE
    
    def test_invalid_agent_id(self):
        """Test validation error for invalid agent ID."""
        config = AgentConfig(name="Test", prompt="Hello")
        
        with pytest.raises(ValidationError) as exc_info:
            Agent(
                id="invalid@id!",
                config=config,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status=AgentStatus.ACTIVE
            )
        
        assert "can only contain letters, numbers, hyphens, and underscores" in str(exc_info.value)


class TestCallRequest:
    """Test cases for CallRequest model."""
    
    def test_valid_call_request(self):
        """Test valid call request."""
        request = CallRequest(
            phone_number="+1234567890",
            template_context={"user_name": "John", "age": 25},
            agent_id="agent-123"
        )
        
        assert request.phone_number == "+1234567890"
        assert request.template_context == {"user_name": "John", "age": 25}
        assert request.agent_id == "agent-123"
    
    def test_phone_number_cleaning(self):
        """Test phone number cleaning and formatting."""
        request = CallRequest(
            phone_number="+1 (234) 567-8900",
            agent_id="agent-123"
        )
        
        assert request.phone_number == "+12345678900"
    
    def test_invalid_phone_number_format(self):
        """Test validation error for invalid phone number."""
        with pytest.raises(ValidationError) as exc_info:
            CallRequest(
                phone_number="1234567890",  # Missing +
                agent_id="agent-123"
            )
        
        assert "must be in international format" in str(exc_info.value)
    
    def test_invalid_phone_number_short(self):
        """Test validation error for too short phone number."""
        with pytest.raises(ValidationError) as exc_info:
            CallRequest(
                phone_number="+123",
                agent_id="agent-123"
            )
        
        assert "must be in international format" in str(exc_info.value)
    
    def test_invalid_template_context_key(self):
        """Test validation error for invalid template context key."""
        with pytest.raises(ValidationError) as exc_info:
            CallRequest(
                phone_number="+1234567890",
                template_context={"123invalid": "value"},
                agent_id="agent-123"
            )
        
        assert "must be a valid identifier" in str(exc_info.value)
    
    def test_invalid_template_context_value_type(self):
        """Test validation error for invalid template context value type."""
        with pytest.raises(ValidationError) as exc_info:
            CallRequest(
                phone_number="+1234567890",
                template_context={"key": {"nested": "object"}},
                agent_id="agent-123"
            )
        
        assert "must be a basic type" in str(exc_info.value)
    
    def test_valid_template_context_types(self):
        """Test valid template context value types."""
        request = CallRequest(
            phone_number="+1234567890",
            template_context={
                "string_val": "hello",
                "int_val": 42,
                "float_val": 3.14,
                "bool_val": True,
                "none_val": None
            },
            agent_id="agent-123"
        )
        
        assert request.template_context["string_val"] == "hello"
        assert request.template_context["int_val"] == 42
        assert request.template_context["float_val"] == 3.14
        assert request.template_context["bool_val"] is True
        assert request.template_context["none_val"] is None


class TestCallResult:
    """Test cases for CallResult model."""
    
    def test_valid_call_result(self):
        """Test valid call result."""
        result = CallResult(
            call_sid="CA" + "a" * 32,
            join_url="wss://example.com/join/123",
            status=CallStatus.INITIATED,
            created_at=datetime.now(),
            agent_id="agent-123",
            phone_number="+1234567890"
        )
        
        assert result.call_sid.startswith("CA")
        assert result.join_url.startswith("wss://")
        assert result.status == CallStatus.INITIATED
    
    def test_invalid_call_sid_format(self):
        """Test validation error for invalid call SID format."""
        with pytest.raises(ValidationError) as exc_info:
            CallResult(
                call_sid="invalid-sid",
                join_url="wss://example.com/join/123",
                status=CallStatus.INITIATED,
                created_at=datetime.now(),
                agent_id="agent-123",
                phone_number="+1234567890"
            )
        
        assert "must be a valid Twilio SID format" in str(exc_info.value)
    
    def test_invalid_join_url_format(self):
        """Test validation error for invalid join URL format."""
        with pytest.raises(ValidationError) as exc_info:
            CallResult(
                call_sid="CA" + "a" * 32,
                join_url="http://example.com",  # Not WebSocket
                status=CallStatus.INITIATED,
                created_at=datetime.now(),
                agent_id="agent-123",
                phone_number="+1234567890"
            )
        
        assert "must be a valid WebSocket URL" in str(exc_info.value)


class TestTwilioCallResult:
    """Test cases for TwilioCallResult model."""
    
    def test_valid_twilio_call_result(self):
        """Test valid Twilio call result."""
        result = TwilioCallResult(
            sid="CA" + "a" * 32,
            status="initiated",
            from_number="+1234567890",
            to_number="+1987654321"
        )
        
        assert result.sid.startswith("CA")
        assert result.status == "initiated"
        assert result.from_number == "+1234567890"
        assert result.to_number == "+1987654321"
    
    def test_invalid_phone_number_format(self):
        """Test validation error for invalid phone number format."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioCallResult(
                sid="CA" + "a" * 32,
                status="initiated",
                from_number="1234567890",  # Missing +
                to_number="+0987654321"
            )
        
        assert "must be in international format" in str(exc_info.value)


class TestUltravoxConfig:
    """Test cases for UltravoxConfig model."""
    
    def test_valid_ultravox_config(self):
        """Test valid Ultravox configuration."""
        config = UltravoxConfig(
            api_key="sk-1234567890abcdef1234567890abcdef",
            base_url="https://api.ultravox.ai"
        )
        
        assert config.api_key == "sk-1234567890abcdef1234567890abcdef"
        assert config.base_url == "https://api.ultravox.ai"
    
    def test_default_base_url(self):
        """Test default base URL."""
        config = UltravoxConfig(api_key="sk-1234567890abcdef1234567890abcdef")
        assert config.base_url == "https://api.ultravox.ai"
    
    def test_base_url_trailing_slash_removal(self):
        """Test base URL trailing slash removal."""
        config = UltravoxConfig(
            api_key="sk-1234567890abcdef1234567890abcdef",
            base_url="https://api.ultravox.ai/"
        )
        assert config.base_url == "https://api.ultravox.ai"
    
    def test_invalid_api_key_empty(self):
        """Test validation error for empty API key."""
        with pytest.raises(ValidationError) as exc_info:
            UltravoxConfig(api_key="")
        
        assert "cannot be empty" in str(exc_info.value)
    
    def test_invalid_api_key_too_short(self):
        """Test validation error for too short API key."""
        with pytest.raises(ValidationError) as exc_info:
            UltravoxConfig(api_key="short")
        
        assert "must be between 10 and 200 characters" in str(exc_info.value)
    
    def test_invalid_base_url_format(self):
        """Test validation error for invalid base URL format."""
        with pytest.raises(ValidationError) as exc_info:
            UltravoxConfig(
                api_key="sk-1234567890abcdef1234567890abcdef",
                base_url="not-a-url"
            )
        
        assert "must be a valid HTTP/HTTPS URL" in str(exc_info.value)


class TestTwilioConfig:
    """Test cases for TwilioConfig model."""
    
    def test_valid_twilio_config(self):
        """Test valid Twilio configuration."""
        config = TwilioConfig(
            account_sid="AC" + "a" * 32,
            auth_token="b" * 32,
            phone_number="+1234567890"
        )
        
        assert config.account_sid.startswith("AC")
        assert len(config.auth_token) == 32
        assert config.phone_number == "+1234567890"
    
    def test_invalid_account_sid_format(self):
        """Test validation error for invalid Account SID format."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioConfig(
                account_sid="invalid-sid",
                auth_token="b" * 32,
                phone_number="+1234567890"
            )
        
        assert "must be a valid Twilio Account SID format" in str(exc_info.value)
    
    def test_invalid_auth_token_format(self):
        """Test validation error for invalid auth token format."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioConfig(
                account_sid="AC" + "a" * 32,
                auth_token="invalid-token",
                phone_number="+1234567890"
            )
        
        assert "must be 32 hexadecimal characters" in str(exc_info.value)
    
    def test_phone_number_cleaning(self):
        """Test phone number cleaning."""
        config = TwilioConfig(
            account_sid="AC" + "a" * 32,
            auth_token="b" * 32,
            phone_number="+1 (234) 567-8900"
        )
        
        assert config.phone_number == "+12345678900"


class TestAppConfig:
    """Test cases for AppConfig model."""
    
    def test_valid_app_config(self):
        """Test valid application configuration."""
        ultravox_config = UltravoxConfig(api_key="sk-1234567890abcdef1234567890abcdef")
        twilio_config = TwilioConfig(
            account_sid="AC" + "a" * 32,
            auth_token="b" * 32,
            phone_number="+1234567890"
        )
        
        config = AppConfig(
            ultravox=ultravox_config,
            twilio=twilio_config,
            debug=True,
            log_level="DEBUG"
        )
        
        assert config.debug is True
        assert config.log_level == "DEBUG"
    
    def test_default_values(self):
        """Test default configuration values."""
        ultravox_config = UltravoxConfig(api_key="sk-1234567890abcdef1234567890abcdef")
        twilio_config = TwilioConfig(
            account_sid="AC" + "a" * 32,
            auth_token="b" * 32,
            phone_number="+1234567890"
        )
        
        config = AppConfig(ultravox=ultravox_config, twilio=twilio_config)
        
        assert config.debug is False
        assert config.log_level == "INFO"
    
    def test_invalid_log_level(self):
        """Test validation error for invalid log level."""
        ultravox_config = UltravoxConfig(api_key="sk-1234567890abcdef1234567890abcdef")
        twilio_config = TwilioConfig(
            account_sid="AC" + "a" * 32,
            auth_token="b" * 32,
            phone_number="+1234567890"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            AppConfig(
                ultravox=ultravox_config,
                twilio=twilio_config,
                log_level="INVALID"
            )
        
        assert "must be one of" in str(exc_info.value)


class TestErrorResponse:
    """Test cases for ErrorResponse model."""
    
    def test_valid_error_response(self):
        """Test valid error response."""
        error = ErrorResponse(
            error="VALIDATION_ERROR",
            message="Invalid input provided",
            details={"field": "phone_number", "issue": "invalid format"},
            timestamp="2023-01-01T00:00:00Z",
            request_id="req-123"
        )
        
        assert error.error == "VALIDATION_ERROR"
        assert error.message == "Invalid input provided"
        assert error.details == {"field": "phone_number", "issue": "invalid format"}
        assert error.timestamp == "2023-01-01T00:00:00Z"
        assert error.request_id == "req-123"
    
    def test_minimal_error_response(self):
        """Test minimal error response."""
        error = ErrorResponse(
            error="GENERIC_ERROR",
            message="Something went wrong",
            timestamp="2023-01-01T00:00:00Z"
        )
        
        assert error.error == "GENERIC_ERROR"
        assert error.message == "Something went wrong"
        assert error.details is None
        assert error.request_id is None
    
    def test_invalid_error_type_format(self):
        """Test validation error for invalid error type format."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorResponse(
                error="invalid-error-type",
                message="Test message",
                timestamp="2023-01-01T00:00:00Z"
            )
        
        assert "must be uppercase with underscores" in str(exc_info.value)