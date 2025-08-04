"""
Tests for ElevenLabs Conversational AI models.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from app.models.elevenlabs import (
    # Conversational AI models
    ElevenLabsAgentConfig,
    ElevenLabsAgent,
    ElevenLabsAgentStatus,
    ElevenLabsConversation,
    ConversationStatus,
    ElevenLabsConversationalCallRequest,
    ElevenLabsCallResult,
    ElevenLabsConversationConfig,
    TurnDetectionConfig,
    UnifiedAgent,
    UnifiedCallRequest,
    # Existing models
    VoiceSettings
)


class TestTurnDetectionConfig:
    """Test TurnDetectionConfig model."""
    
    def test_valid_turn_detection_config(self):
        """Test creating valid turn detection config."""
        config = TurnDetectionConfig(
            type="server_vad",
            threshold=0.7,
            prefix_padding_ms=500,
            silence_duration_ms=1500
        )
        
        assert config.type == "server_vad"
        assert config.threshold == 0.7
        assert config.prefix_padding_ms == 500
        assert config.silence_duration_ms == 1500
    
    def test_default_turn_detection_config(self):
        """Test default turn detection config values."""
        config = TurnDetectionConfig()
        
        assert config.type == "server_vad"
        assert config.threshold == 0.5
        assert config.prefix_padding_ms == 300
        assert config.silence_duration_ms == 1000
    
    def test_turn_detection_config_to_elevenlabs_dict(self):
        """Test conversion to ElevenLabs API format."""
        config = TurnDetectionConfig(
            type="server_vad",
            threshold=0.8,
            prefix_padding_ms=400,
            silence_duration_ms=1200
        )
        
        result = config.to_elevenlabs_dict()
        expected = {
            "type": "server_vad",
            "threshold": 0.8,
            "prefix_padding_ms": 400,
            "silence_duration_ms": 1200
        }
        
        assert result == expected
    
    def test_invalid_threshold_values(self):
        """Test validation of threshold values."""
        with pytest.raises(ValidationError):
            TurnDetectionConfig(threshold=-0.1)
        
        with pytest.raises(ValidationError):
            TurnDetectionConfig(threshold=1.1)


class TestElevenLabsConversationConfig:
    """Test ElevenLabsConversationConfig model."""
    
    def test_valid_conversation_config(self):
        """Test creating valid conversation config."""
        turn_detection = TurnDetectionConfig(threshold=0.6)
        config = ElevenLabsConversationConfig(
            turn_detection=turn_detection,
            language="en-US",
            max_duration_seconds=2400,
            webhook_url="https://example.com/webhook"
        )
        
        assert config.turn_detection == turn_detection
        assert config.language == "en-US"
        assert config.max_duration_seconds == 2400
        assert config.webhook_url == "https://example.com/webhook"
    
    def test_default_conversation_config(self):
        """Test default conversation config values."""
        config = ElevenLabsConversationConfig()
        
        assert config.language == "en"
        assert config.max_duration_seconds == 1800
        assert config.agent_tools == []
        assert config.webhook_url is None
    
    def test_invalid_language_format(self):
        """Test validation of language format."""
        with pytest.raises(ValidationError):
            ElevenLabsConversationConfig(language="invalid")
        
        with pytest.raises(ValidationError):
            ElevenLabsConversationConfig(language="en-us")  # Should be uppercase
    
    def test_invalid_duration_range(self):
        """Test validation of duration range."""
        with pytest.raises(ValidationError):
            ElevenLabsConversationConfig(max_duration_seconds=30)  # Too short
        
        with pytest.raises(ValidationError):
            ElevenLabsConversationConfig(max_duration_seconds=4000)  # Too long
    
    def test_invalid_webhook_url(self):
        """Test validation of webhook URL."""
        with pytest.raises(ValidationError):
            ElevenLabsConversationConfig(webhook_url="invalid-url")
        
        with pytest.raises(ValidationError):
            ElevenLabsConversationConfig(webhook_url="ftp://example.com")
    
    def test_conversation_config_to_elevenlabs_dict(self):
        """Test conversion to ElevenLabs API format."""
        turn_detection = TurnDetectionConfig(threshold=0.7)
        config = ElevenLabsConversationConfig(
            turn_detection=turn_detection,
            language="en-US",
            max_duration_seconds=2400,
            agent_tools=[{"type": "function", "name": "test"}],
            webhook_url="https://example.com/webhook"
        )
        
        result = config.to_elevenlabs_dict()
        
        assert result["language"] == "en-US"
        assert result["max_duration_seconds"] == 2400
        assert result["agent_tools"] == [{"type": "function", "name": "test"}]
        assert result["webhook_url"] == "https://example.com/webhook"
        assert "turn_detection" in result


class TestElevenLabsAgentConfig:
    """Test ElevenLabsAgentConfig model."""
    
    def test_valid_agent_config(self):
        """Test creating valid agent config."""
        config = ElevenLabsAgentConfig(
            name="Test Agent",
            system_prompt="You are a helpful assistant.",
            voice_id="21m00Tcm4TlvDq8ikWAM",
            template_variables={"user_name": "John", "company": "Acme Corp"}
        )
        
        assert config.name == "Test Agent"
        assert config.system_prompt == "You are a helpful assistant."
        assert config.voice_id == "21m00Tcm4TlvDq8ikWAM"
        assert config.template_variables == {"user_name": "John", "company": "Acme Corp"}
    
    def test_agent_config_with_defaults(self):
        """Test agent config with default values."""
        config = ElevenLabsAgentConfig(
            name="Simple Agent",
            system_prompt="Hello world",
            voice_id="test_voice_id"
        )
        
        assert config.template_variables == {}
        assert isinstance(config.conversation_config, ElevenLabsConversationConfig)
    
    def test_invalid_agent_name(self):
        """Test validation of agent name."""
        with pytest.raises(ValidationError):
            ElevenLabsAgentConfig(
                name="",  # Empty name
                system_prompt="Test",
                voice_id="test_voice"
            )
        
        with pytest.raises(ValidationError):
            ElevenLabsAgentConfig(
                name="Agent@#$%",  # Invalid characters
                system_prompt="Test",
                voice_id="test_voice"
            )
    
    def test_invalid_system_prompt(self):
        """Test validation of system prompt."""
        with pytest.raises(ValidationError):
            ElevenLabsAgentConfig(
                name="Test Agent",
                system_prompt="",  # Empty prompt
                voice_id="test_voice"
            )
        
        with pytest.raises(ValidationError):
            ElevenLabsAgentConfig(
                name="Test Agent",
                system_prompt="x" * 10001,  # Too long
                voice_id="test_voice"
            )
    
    def test_invalid_template_variables(self):
        """Test validation of template variables."""
        with pytest.raises(ValidationError):
            ElevenLabsAgentConfig(
                name="Test Agent",
                system_prompt="Test",
                voice_id="test_voice",
                template_variables={"123invalid": "value"}  # Invalid key
            )
        
        with pytest.raises(ValidationError):
            ElevenLabsAgentConfig(
                name="Test Agent",
                system_prompt="Test",
                voice_id="test_voice",
                template_variables={"key": 123}  # Non-string value
            )
    
    def test_agent_config_to_elevenlabs_dict(self):
        """Test conversion to ElevenLabs API format."""
        config = ElevenLabsAgentConfig(
            name="Test Agent",
            system_prompt="You are helpful.",
            voice_id="test_voice_id"
        )
        
        result = config.to_elevenlabs_dict()
        
        assert result["name"] == "Test Agent"
        assert result["system_prompt"] == "You are helpful."
        assert result["voice_id"] == "test_voice_id"
        assert "conversation_config" in result


class TestElevenLabsAgent:
    """Test ElevenLabsAgent model."""
    
    def test_valid_agent(self):
        """Test creating valid ElevenLabs agent."""
        config = ElevenLabsAgentConfig(
            name="Test Agent",
            system_prompt="You are helpful.",
            voice_id="test_voice_id"
        )
        
        agent = ElevenLabsAgent(
            id="agent_123",
            config=config,
            created_at=datetime.now(timezone.utc),
            status=ElevenLabsAgentStatus.ACTIVE
        )
        
        assert agent.id == "agent_123"
        assert agent.config == config
        assert agent.status == ElevenLabsAgentStatus.ACTIVE
        assert agent.agent_type == "elevenlabs"
    
    def test_invalid_agent_id(self):
        """Test validation of agent ID."""
        config = ElevenLabsAgentConfig(
            name="Test Agent",
            system_prompt="Test",
            voice_id="test_voice"
        )
        
        with pytest.raises(ValidationError):
            ElevenLabsAgent(
                id="agent@123",  # Invalid characters
                config=config,
                created_at=datetime.now(timezone.utc),
                status=ElevenLabsAgentStatus.ACTIVE
            )
    
    def test_agent_voice_info_property(self):
        """Test voice_info property."""
        config = ElevenLabsAgentConfig(
            name="Test Agent",
            system_prompt="Test",
            voice_id="test_voice_123"
        )
        
        agent = ElevenLabsAgent(
            id="agent_123",
            config=config,
            created_at=datetime.now(timezone.utc),
            status=ElevenLabsAgentStatus.ACTIVE
        )
        
        voice_info = agent.voice_info
        assert voice_info["voice_id"] == "test_voice_123"
        assert voice_info["voice_name"] == "Unknown"


class TestElevenLabsConversation:
    """Test ElevenLabsConversation model."""
    
    def test_valid_conversation(self):
        """Test creating valid conversation."""
        conversation = ElevenLabsConversation(
            id="conv_123",
            agent_id="agent_456",
            status=ConversationStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            phone_number="+1234567890"
        )
        
        assert conversation.id == "conv_123"
        assert conversation.agent_id == "agent_456"
        assert conversation.status == ConversationStatus.ACTIVE
        assert conversation.phone_number == "+1234567890"
        assert conversation.is_active is True
    
    def test_conversation_duration_calculation(self):
        """Test duration calculation."""
        now = datetime.now(timezone.utc)
        started = now.replace(second=0)
        ended = now.replace(second=30)
        
        conversation = ElevenLabsConversation(
            id="conv_123",
            agent_id="agent_456",
            status=ConversationStatus.ENDED,
            created_at=started,
            started_at=started,
            ended_at=ended
        )
        
        assert conversation.duration_seconds == 30.0
    
    def test_invalid_agent_id_format(self):
        """Test validation of agent ID format."""
        with pytest.raises(ValidationError):
            ElevenLabsConversation(
                id="conv_123",
                agent_id="agent@456",  # Invalid characters
                status=ConversationStatus.ACTIVE,
                created_at=datetime.now(timezone.utc)
            )


class TestElevenLabsConversationalCallRequest:
    """Test ElevenLabsConversationalCallRequest model."""
    
    def test_valid_call_request(self):
        """Test creating valid call request."""
        request = ElevenLabsConversationalCallRequest(
            phone_number="+1234567890",
            agent_id="agent_123",
            template_context={"user_name": "John"}
        )
        
        assert request.phone_number == "+1234567890"
        assert request.agent_id == "agent_123"
        assert request.template_context == {"user_name": "John"}
    
    def test_invalid_phone_number(self):
        """Test validation of phone number."""
        with pytest.raises(ValidationError):
            ElevenLabsConversationalCallRequest(
                phone_number="1234567890",  # Missing +
                agent_id="agent_123"
            )
        
        with pytest.raises(ValidationError):
            ElevenLabsConversationalCallRequest(
                phone_number="+0123456789",  # Starts with 0
                agent_id="agent_123"
            )
    
    def test_invalid_agent_id(self):
        """Test validation of agent ID."""
        with pytest.raises(ValidationError):
            ElevenLabsConversationalCallRequest(
                phone_number="+1234567890",
                agent_id="agent@123"  # Invalid characters
            )


class TestElevenLabsCallResult:
    """Test ElevenLabsCallResult model."""
    
    def test_valid_call_result(self):
        """Test creating valid call result."""
        result = ElevenLabsCallResult(
            call_sid="CA" + "a" * 32,
            conversation_id="conv_123",
            agent_id="agent_456",
            voice_id="voice_789",
            status="initiated",
            created_at=datetime.now(timezone.utc),
            phone_number="+1234567890"
        )
        
        assert result.call_type == "elevenlabs_conversational"
        assert result.conversation_id == "conv_123"
        assert result.agent_id == "agent_456"
        assert result.voice_id == "voice_789"
    
    def test_invalid_call_sid(self):
        """Test validation of call SID."""
        with pytest.raises(ValidationError):
            ElevenLabsCallResult(
                call_sid="invalid_sid",
                conversation_id="conv_123",
                agent_id="agent_456",
                voice_id="voice_789",
                status="initiated",
                created_at=datetime.now(timezone.utc),
                phone_number="+1234567890"
            )


class TestUnifiedAgent:
    """Test UnifiedAgent model."""
    
    def test_from_elevenlabs_agent(self):
        """Test creating unified agent from ElevenLabs agent."""
        config = ElevenLabsAgentConfig(
            name="Test Agent",
            system_prompt="You are helpful.",
            voice_id="test_voice_id"
        )
        
        elevenlabs_agent = ElevenLabsAgent(
            id="agent_123",
            config=config,
            created_at=datetime.now(timezone.utc),
            status=ElevenLabsAgentStatus.ACTIVE
        )
        
        unified = UnifiedAgent.from_elevenlabs_agent(elevenlabs_agent, "Rachel")
        
        assert unified.id == "agent_123"
        assert unified.name == "Test Agent"
        assert unified.agent_type == "elevenlabs"
        assert unified.voice_info["voice_id"] == "test_voice_id"
        assert unified.voice_info["voice_name"] == "Rachel"
        assert "system_prompt" in unified.config
        assert "voice_id" in unified.config


class TestUnifiedCallRequest:
    """Test UnifiedCallRequest model."""
    
    def test_valid_elevenlabs_call_request(self):
        """Test creating valid ElevenLabs call request."""
        request = UnifiedCallRequest(
            call_type="elevenlabs",
            phone_number="+1234567890",
            agent_id="agent_123",
            template_context={"user_name": "John"}
        )
        
        assert request.call_type == "elevenlabs"
        assert request.phone_number == "+1234567890"
        assert request.agent_id == "agent_123"
        assert request.template_context == {"user_name": "John"}
    
    def test_valid_ultravox_call_request(self):
        """Test creating valid Ultravox call request."""
        request = UnifiedCallRequest(
            call_type="ultravox",
            phone_number="+1234567890",
            agent_id="agent_456"
        )
        
        assert request.call_type == "ultravox"
        assert request.agent_id == "agent_456"
    
    def test_missing_agent_id(self):
        """Test validation when agent_id is missing."""
        with pytest.raises(ValidationError):
            UnifiedCallRequest(
                call_type="elevenlabs",
                phone_number="+1234567890",
                agent_id=""  # Empty agent_id
            )
    
    def test_invalid_phone_number_format(self):
        """Test validation of phone number format."""
        with pytest.raises(ValidationError):
            UnifiedCallRequest(
                call_type="elevenlabs",
                phone_number="1234567890",  # Missing +
                agent_id="agent_123"
            )


if __name__ == "__main__":
    pytest.main([__file__])