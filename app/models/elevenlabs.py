"""
ElevenLabs-specific models for voice synthesis integration.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Any, List, Literal
from pydantic import BaseModel, Field, field_validator
import re


class VoiceCategory(str, Enum):
    """Voice category enumeration."""
    PREMADE = "premade"
    CLONED = "cloned"
    GENERATED = "generated"
    PROFESSIONAL = "professional"


class AudioFormat(str, Enum):
    """Supported audio formats for ElevenLabs."""
    MP3_44100_128 = "mp3_44100_128"
    MP3_22050_32 = "mp3_22050_32"
    PCM_16000 = "pcm_16000"
    PCM_22050 = "pcm_22050"
    PCM_24000 = "pcm_24000"
    PCM_44100 = "pcm_44100"


class VoiceSettings(BaseModel):
    """Voice synthesis settings for ElevenLabs."""
    stability: float = Field(
        default=0.75, 
        ge=0.0, 
        le=1.0, 
        description="Voice stability (0.0 to 1.0)"
    )
    similarity_boost: float = Field(
        default=0.75, 
        ge=0.0, 
        le=1.0, 
        description="Similarity boost (0.0 to 1.0)"
    )
    style: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0, 
        description="Style exaggeration (0.0 to 1.0)"
    )
    use_speaker_boost: bool = Field(
        default=False, 
        description="Enable speaker boost for better clarity"
    )

    def to_elevenlabs_dict(self) -> Dict[str, Any]:
        """Convert to ElevenLabs API format."""
        return {
            "stability": self.stability,
            "similarity_boost": self.similarity_boost,
            "style": self.style,
            "use_speaker_boost": self.use_speaker_boost
        }


class Voice(BaseModel):
    """ElevenLabs voice model."""
    voice_id: str = Field(..., description="Unique voice identifier")
    name: str = Field(..., description="Voice name")
    category: VoiceCategory = Field(..., description="Voice category")
    description: Optional[str] = Field(None, description="Voice description")
    preview_url: Optional[str] = Field(None, description="Preview audio URL")
    settings: Optional[VoiceSettings] = Field(None, description="Default voice settings")
    labels: Optional[Dict[str, str]] = Field(default_factory=dict, description="Voice labels/metadata")
    available_for_tiers: Optional[List[str]] = Field(default_factory=list, description="Available subscription tiers")

    @field_validator('voice_id')
    @classmethod
    def validate_voice_id(cls, v):
        """Validate voice ID format."""
        if not v or not isinstance(v, str):
            raise ValueError('Voice ID must be a non-empty string')
        return v.strip()

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate voice name."""
        if not v or not isinstance(v, str):
            raise ValueError('Voice name must be a non-empty string')
        return v.strip()


class ElevenLabsCallRequest(BaseModel):
    """Request model for ElevenLabs voice synthesis calls."""
    phone_number: str = Field(
        ..., 
        description="Phone number in international format",
        pattern=r'^\+[1-9]\d{1,14}$'
    )
    text: str = Field(
        ..., 
        min_length=1, 
        max_length=5000, 
        description="Text to synthesize (max 5000 characters)"
    )
    voice_id: str = Field(..., description="ElevenLabs voice ID")
    voice_settings: Optional[VoiceSettings] = Field(
        None, 
        description="Voice synthesis settings"
    )
    audio_format: AudioFormat = Field(
        default=AudioFormat.MP3_44100_128,
        description="Audio format for synthesis"
    )
    template_context: Optional[Dict[str, str]] = Field(
        default_factory=dict, 
        description="Template variables for text substitution"
    )

    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        """Validate and clean text for synthesis."""
        if not v or not isinstance(v, str):
            raise ValueError('Text must be a non-empty string')
        
        # Clean up text
        text = v.strip()
        
        # Check length
        if len(text) > 5000:
            raise ValueError(f'Text length {len(text)} exceeds maximum of 5000 characters')
        
        # Basic content validation
        if not text:
            raise ValueError('Text cannot be empty after cleaning')
            
        return text

    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        """Validate phone number format."""
        if not v or not isinstance(v, str):
            raise ValueError('Phone number must be a non-empty string')
        
        phone = v.strip()
        if not re.match(r'^\+[1-9]\d{1,14}$', phone):
            raise ValueError('Phone number must be in international format (+1234567890)')
        
        return phone


class UnifiedCallRequest(BaseModel):
    """Unified request model supporting both Ultravox and ElevenLabs calls."""
    call_type: Literal["ultravox", "elevenlabs"] = Field(
        ..., 
        description="Type of call to create"
    )
    phone_number: str = Field(
        ..., 
        description="Phone number in international format",
        pattern=r'^\+[1-9]\d{1,14}$'
    )
    
    # Ultravox-specific fields
    agent_id: Optional[str] = Field(None, description="Ultravox agent ID (required for ultravox calls)")
    
    # ElevenLabs-specific fields
    text: Optional[str] = Field(None, description="Text to synthesize (required for elevenlabs calls)")
    voice_id: Optional[str] = Field(None, description="ElevenLabs voice ID (required for elevenlabs calls)")
    voice_settings: Optional[VoiceSettings] = Field(None, description="Voice synthesis settings")
    audio_format: Optional[AudioFormat] = Field(AudioFormat.MP3_44100_128, description="Audio format")
    
    # Common fields
    template_context: Optional[Dict[str, str]] = Field(
        default_factory=dict, 
        description="Template variables"
    )

    @field_validator('agent_id')
    @classmethod
    def validate_agent_id(cls, v, info):
        """Validate agent_id is provided for Ultravox calls."""
        if info.data.get('call_type') == 'ultravox' and not v:
            raise ValueError('agent_id is required for ultravox calls')
        return v

    @field_validator('text')
    @classmethod
    def validate_text_for_elevenlabs(cls, v, info):
        """Validate text is provided for ElevenLabs calls."""
        if info.data.get('call_type') == 'elevenlabs':
            if not v:
                raise ValueError('text is required for elevenlabs calls')
            if len(v.strip()) > 5000:
                raise ValueError('text exceeds maximum length of 5000 characters')
        return v

    @field_validator('voice_id')
    @classmethod
    def validate_voice_id_for_elevenlabs(cls, v, info):
        """Validate voice_id is provided for ElevenLabs calls."""
        if info.data.get('call_type') == 'elevenlabs' and not v:
            raise ValueError('voice_id is required for elevenlabs calls')
        return v


class AudioData(BaseModel):
    """Model for audio data from ElevenLabs synthesis."""
    content: bytes = Field(..., description="Audio content as bytes")
    format: AudioFormat = Field(..., description="Audio format")
    content_type: str = Field(..., description="MIME content type")
    size_bytes: int = Field(..., description="Audio size in bytes")
    duration_seconds: Optional[float] = Field(None, description="Audio duration in seconds")
    
    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_response(
        cls, 
        content: bytes, 
        audio_format: AudioFormat = AudioFormat.MP3_44100_128
    ) -> 'AudioData':
        """Create AudioData from API response."""
        content_type_map = {
            AudioFormat.MP3_44100_128: "audio/mpeg",
            AudioFormat.MP3_22050_32: "audio/mpeg",
            AudioFormat.PCM_16000: "audio/wav",
            AudioFormat.PCM_22050: "audio/wav",
            AudioFormat.PCM_24000: "audio/wav",
            AudioFormat.PCM_44100: "audio/wav",
        }
        
        return cls(
            content=content,
            format=audio_format,
            content_type=content_type_map.get(audio_format, "audio/mpeg"),
            size_bytes=len(content)
        )


class QuotaInfo(BaseModel):
    """ElevenLabs quota information."""
    character_count: int = Field(..., description="Characters used")
    character_limit: int = Field(..., description="Character limit")
    can_extend_character_limit: bool = Field(..., description="Can extend limit")
    allowed_to_extend_character_limit: bool = Field(..., description="Allowed to extend")
    next_character_count_reset_unix: int = Field(..., description="Next reset timestamp")
    voice_limit: int = Field(..., description="Voice limit")
    voice_count: int = Field(..., description="Voices used")
    can_extend_voice_limit: bool = Field(..., description="Can extend voice limit")
    can_use_instant_voice_cloning: bool = Field(..., description="Can use instant cloning")
    can_use_professional_voice_cloning: bool = Field(..., description="Can use professional cloning")
    currency: Optional[str] = Field(None, description="Currency")
    status: str = Field(..., description="Subscription status")

    @property
    def character_usage_percentage(self) -> float:
        """Calculate character usage percentage."""
        if self.character_limit == 0:
            return 0.0
        return (self.character_count / self.character_limit) * 100

    @property
    def characters_remaining(self) -> int:
        """Calculate remaining characters."""
        return max(0, self.character_limit - self.character_count)

    @property
    def is_quota_exceeded(self) -> bool:
        """Check if quota is exceeded."""
        return self.character_count >= self.character_limit


# ============================================================================
# ElevenLabs Conversational AI Models
# ============================================================================

class ConversationStatus(str, Enum):
    """ElevenLabs conversation status enumeration."""
    CREATED = "created"
    ACTIVE = "active"
    ENDED = "ended"
    ERROR = "error"


class ElevenLabsAgentStatus(str, Enum):
    """ElevenLabs agent status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CREATING = "creating"
    ERROR = "error"


class TurnDetectionConfig(BaseModel):
    """Configuration for conversation turn detection."""
    type: str = Field(default="server_vad", description="Turn detection type")
    threshold: Optional[float] = Field(default=0.5, ge=0.0, le=1.0, description="Detection threshold")
    prefix_padding_ms: Optional[int] = Field(default=300, ge=0, description="Prefix padding in milliseconds")
    silence_duration_ms: Optional[int] = Field(default=1000, ge=0, description="Silence duration in milliseconds")

    def to_elevenlabs_dict(self) -> Dict[str, Any]:
        """Convert to ElevenLabs API format."""
        config = {"type": self.type}
        if self.threshold is not None:
            config["threshold"] = self.threshold
        if self.prefix_padding_ms is not None:
            config["prefix_padding_ms"] = self.prefix_padding_ms
        if self.silence_duration_ms is not None:
            config["silence_duration_ms"] = self.silence_duration_ms
        return config


class ElevenLabsConversationConfig(BaseModel):
    """Configuration for ElevenLabs conversations."""
    turn_detection: Optional[TurnDetectionConfig] = Field(
        default_factory=TurnDetectionConfig, 
        description="Turn detection configuration"
    )
    agent_tools: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, 
        description="Agent tools configuration"
    )
    language: str = Field(default="en", description="Conversation language")
    max_duration_seconds: int = Field(
        default=1800, 
        ge=60, 
        le=3600, 
        description="Maximum conversation duration (60-3600 seconds)"
    )
    webhook_url: Optional[str] = Field(None, description="Webhook URL for conversation events")

    @field_validator('language')
    @classmethod
    def validate_language(cls, v):
        """Validate language code format."""
        if v and not re.match(r'^[a-z]{2}(-[A-Z]{2})?$', v):
            raise ValueError('Language must be in format "en" or "en-US"')
        return v

    @field_validator('webhook_url')
    @classmethod
    def validate_webhook_url(cls, v):
        """Validate webhook URL format."""
        if v and not re.match(r'^https?://[^\s]+$', v):
            raise ValueError('Webhook URL must be a valid HTTP/HTTPS URL')
        return v

    def to_elevenlabs_dict(self) -> Dict[str, Any]:
        """Convert to ElevenLabs API format."""
        config = {
            "language": self.language,
            "max_duration_seconds": self.max_duration_seconds
        }
        
        if self.turn_detection:
            config["turn_detection"] = self.turn_detection.to_elevenlabs_dict()
        
        if self.agent_tools:
            config["agent_tools"] = self.agent_tools
            
        if self.webhook_url:
            config["webhook_url"] = self.webhook_url
            
        return config


class ElevenLabsAgentConfig(BaseModel):
    """Configuration for an ElevenLabs conversational agent."""
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=100, 
        description="Agent name"
    )
    system_prompt: str = Field(
        ..., 
        min_length=1, 
        max_length=10000, 
        description="System prompt for the agent"
    )
    voice_id: str = Field(..., description="ElevenLabs voice ID")
    conversation_config: ElevenLabsConversationConfig = Field(
        default_factory=ElevenLabsConversationConfig,
        description="Conversation configuration"
    )
    template_variables: Optional[Dict[str, str]] = Field(
        default_factory=dict, 
        description="Template variables for prompt substitution"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate agent name contains only allowed characters."""
        if not re.match(r'^[a-zA-Z0-9\s\-_\.]+$', v):
            raise ValueError('Agent name can only contain letters, numbers, spaces, hyphens, underscores, and periods')
        return v.strip()

    @field_validator('system_prompt')
    @classmethod
    def validate_system_prompt(cls, v):
        """Validate and clean system prompt."""
        if not v or not isinstance(v, str):
            raise ValueError('System prompt must be a non-empty string')
        
        prompt = v.strip()
        if len(prompt) > 10000:
            raise ValueError(f'System prompt length {len(prompt)} exceeds maximum of 10000 characters')
        
        if not prompt:
            raise ValueError('System prompt cannot be empty after cleaning')
            
        return prompt

    @field_validator('voice_id')
    @classmethod
    def validate_voice_id(cls, v):
        """Validate voice ID format."""
        if not v or not isinstance(v, str):
            raise ValueError('Voice ID must be a non-empty string')
        return v.strip()

    @field_validator('template_variables')
    @classmethod
    def validate_template_variables(cls, v):
        """Validate template variables."""
        if v:
            for key, value in v.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise ValueError('Template variables must be string key-value pairs')
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                    raise ValueError(f'Template variable key "{key}" must be a valid identifier')
        return v

    def to_elevenlabs_dict(self) -> Dict[str, Any]:
        """Convert to ElevenLabs API format."""
        return {
            "name": self.name,
            "system_prompt": self.system_prompt,
            "voice_id": self.voice_id,
            "conversation_config": self.conversation_config.to_elevenlabs_dict()
        }


class ElevenLabsAgent(BaseModel):
    """ElevenLabs conversational agent model."""
    id: str = Field(..., description="Unique agent identifier")
    config: ElevenLabsAgentConfig = Field(..., description="Agent configuration")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    status: ElevenLabsAgentStatus = Field(..., description="Agent status")

    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        """Validate agent ID format."""
        if not re.match(r'^[a-zA-Z0-9\-_]+$', v):
            raise ValueError('Agent ID can only contain letters, numbers, hyphens, and underscores')
        return v

    @property
    def agent_type(self) -> str:
        """Return agent type for unified handling."""
        return "elevenlabs"

    @property
    def voice_info(self) -> Dict[str, str]:
        """Return voice information for API responses."""
        return {
            "voice_id": self.config.voice_id,
            "voice_name": "Unknown"  # Will be populated by service layer
        }


class ElevenLabsConversation(BaseModel):
    """ElevenLabs conversation model."""
    id: str = Field(..., description="Unique conversation identifier")
    agent_id: str = Field(..., description="Agent ID for this conversation")
    status: ConversationStatus = Field(..., description="Conversation status")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    ended_at: Optional[datetime] = Field(None, description="End timestamp")
    phone_number: Optional[str] = Field(None, description="Phone number if phone conversation")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        """Validate conversation ID format."""
        if not v or not isinstance(v, str):
            raise ValueError('Conversation ID must be a non-empty string')
        return v.strip()

    @field_validator('agent_id')
    @classmethod
    def validate_agent_id(cls, v):
        """Validate agent ID format."""
        if not re.match(r'^[a-zA-Z0-9\-_]+$', v):
            raise ValueError('Agent ID can only contain letters, numbers, hyphens, and underscores')
        return v

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate conversation duration in seconds."""
        if self.started_at and self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return None

    @property
    def is_active(self) -> bool:
        """Check if conversation is currently active."""
        return self.status == ConversationStatus.ACTIVE


class ElevenLabsConversationalCallRequest(BaseModel):
    """Request model for ElevenLabs conversational AI calls."""
    phone_number: str = Field(
        ..., 
        description="Phone number in international format",
        pattern=r'^\+[1-9]\d{1,14}$'
    )
    agent_id: str = Field(..., description="ElevenLabs agent ID")
    template_context: Optional[Dict[str, str]] = Field(
        default_factory=dict, 
        description="Template variables for prompt substitution"
    )

    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        """Validate phone number format."""
        if not v or not isinstance(v, str):
            raise ValueError('Phone number must be a non-empty string')
        
        phone = v.strip()
        if not re.match(r'^\+[1-9]\d{1,14}$', phone):
            raise ValueError('Phone number must be in international format (+1234567890)')
        
        return phone

    @field_validator('agent_id')
    @classmethod
    def validate_agent_id(cls, v):
        """Validate agent ID format."""
        if not re.match(r'^[a-zA-Z0-9\-_]+$', v):
            raise ValueError('Agent ID can only contain letters, numbers, hyphens, and underscores')
        return v


class ElevenLabsCallResult(BaseModel):
    """Result model for ElevenLabs conversational calls."""
    call_sid: str = Field(..., description="Twilio call SID")
    conversation_id: str = Field(..., description="ElevenLabs conversation ID")
    agent_id: str = Field(..., description="Agent ID used for the call")
    voice_id: str = Field(..., description="Voice ID used for the call")
    status: str = Field(..., description="Call status")
    created_at: datetime = Field(..., description="Call creation timestamp")
    phone_number: str = Field(..., description="Phone number called")

    @field_validator('call_sid')
    @classmethod
    def validate_call_sid(cls, v):
        """Validate Twilio call SID format."""
        if not re.match(r'^CA[a-f0-9]{32}$', v):
            raise ValueError('Call SID must be a valid Twilio SID format')
        return v

    @property
    def call_type(self) -> str:
        """Return call type for unified handling."""
        return "elevenlabs_conversational"


# ============================================================================
# Unified Models for Multi-Platform Support
# ============================================================================

class UnifiedAgent(BaseModel):
    """Unified agent model supporting both Ultravox and ElevenLabs agents."""
    id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Agent name")
    agent_type: Literal["ultravox", "elevenlabs"] = Field(..., description="Agent platform type")
    config: Dict[str, Any] = Field(..., description="Platform-specific configuration")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    status: str = Field(..., description="Agent status")
    voice_info: Optional[Dict[str, str]] = Field(None, description="Voice information (for ElevenLabs)")

    @classmethod
    def from_ultravox_agent(cls, agent) -> 'UnifiedAgent':
        """Convert Ultravox agent to unified format."""
        return cls(
            id=agent.id,
            name=agent.config.name,
            agent_type="ultravox",
            config={
                "name": agent.config.name,
                "prompt": agent.config.prompt,
                "voice": agent.config.voice,
                "language": agent.config.language,
                "template_variables": agent.config.template_variables
            },
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            status=agent.status,
            voice_info=None
        )

    @classmethod
    def from_elevenlabs_agent(cls, agent: ElevenLabsAgent, voice_name: Optional[str] = None) -> 'UnifiedAgent':
        """Convert ElevenLabs agent to unified format."""
        return cls(
            id=agent.id,
            name=agent.config.name,
            agent_type="elevenlabs",
            config={
                "name": agent.config.name,
                "system_prompt": agent.config.system_prompt,
                "voice_id": agent.config.voice_id,
                "conversation_config": agent.config.conversation_config.model_dump(),
                "template_variables": agent.config.template_variables
            },
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            status=agent.status,
            voice_info={
                "voice_id": agent.config.voice_id,
                "voice_name": voice_name or "Unknown"
            }
        )


class UnifiedCallRequest(BaseModel):
    """Enhanced unified request model supporting conversational AI calls."""
    call_type: Literal["ultravox", "elevenlabs"] = Field(
        ..., 
        description="Type of call to create"
    )
    phone_number: str = Field(
        ..., 
        description="Phone number in international format",
        pattern=r'^\+[1-9]\d{1,14}$'
    )
    agent_id: str = Field(..., description="Agent ID for the call")
    template_context: Optional[Dict[str, str]] = Field(
        default_factory=dict, 
        description="Template variables"
    )

    @field_validator('agent_id')
    @classmethod
    def validate_agent_id(cls, v):
        """Validate agent_id is provided."""
        if not v:
            raise ValueError('agent_id is required for all call types')
        return v

    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        """Validate phone number format."""
        if not v or not isinstance(v, str):
            raise ValueError('Phone number must be a non-empty string')
        
        phone = v.strip()
        if not re.match(r'^\+[1-9]\d{1,14}$', phone):
            raise ValueError('Phone number must be in international format (+1234567890)')
        
        return phone


class ElevenLabsConfig(BaseModel):
    """ElevenLabs service configuration."""
    api_key: str = Field(..., description="ElevenLabs API key")
    base_url: str = Field(
        default="https://api.elevenlabs.io", 
        description="ElevenLabs API base URL"
    )
    default_voice_id: str = Field(
        default="21m00Tcm4TlvDq8ikWAM", 
        description="Default voice ID (Rachel)"
    )
    default_voice_settings: VoiceSettings = Field(
        default_factory=VoiceSettings, 
        description="Default voice settings"
    )
    max_text_length: int = Field(
        default=5000, 
        description="Maximum text length for synthesis"
    )
    audio_format: AudioFormat = Field(
        default=AudioFormat.MP3_44100_128, 
        description="Default audio format"
    )
    request_timeout: float = Field(
        default=30.0, 
        description="Request timeout in seconds"
    )
    enable_preview: bool = Field(
        default=True, 
        description="Enable voice preview functionality"
    )
    # New conversational AI specific settings
    enable_conversational_ai: bool = Field(
        default=True,
        description="Enable conversational AI features"
    )
    default_conversation_config: ElevenLabsConversationConfig = Field(
        default_factory=ElevenLabsConversationConfig,
        description="Default conversation configuration"
    )

    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v):
        """Validate API key format."""
        if not v or not isinstance(v, str):
            raise ValueError('API key must be a non-empty string')
        return v.strip()

    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v):
        """Validate base URL format."""
        if not v or not isinstance(v, str):
            raise ValueError('Base URL must be a non-empty string')
        
        url = v.strip().rstrip('/')
        if not url.startswith(('http://', 'https://')):
            raise ValueError('Base URL must start with http:// or https://')
        
        return url