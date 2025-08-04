"""
ElevenLabs-specific exception classes for the voice synthesis integration.
"""

from typing import Optional, Dict, Any
from app.exceptions.base import ExternalServiceError, ValidationError


class ElevenLabsAPIError(ExternalServiceError):
    """Base exception for ElevenLabs API errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None, 
        quota_exceeded: bool = False,
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None
    ):
        self.quota_exceeded = quota_exceeded
        super().__init__(
            message=message, 
            service_name="elevenlabs",
            details=details, 
            status_code=status_code or 502
        )
        # Override the error_code after super() call
        if error_code:
            self.error_code = error_code


class VoiceNotFoundError(ElevenLabsAPIError):
    """Exception raised when a requested voice is not found."""
    
    def __init__(self, voice_id: str, details: Optional[Dict[str, Any]] = None):
        message = f"Voice with ID '{voice_id}' not found"
        super().__init__(
            message=message,
            error_code="voice_not_found",
            details=details or {"voice_id": voice_id},
            status_code=404
        )


class TextTooLongError(ValidationError):
    """Exception raised when text exceeds maximum length for synthesis."""
    
    def __init__(self, text_length: int, max_length: int, details: Optional[Dict[str, Any]] = None):
        message = f"Text length {text_length} exceeds maximum allowed length of {max_length} characters"
        super().__init__(
            message=message,
            details=details or {
                "text_length": text_length,
                "max_length": max_length,
                "field": "text"
            }
        )


class QuotaExceededError(ElevenLabsAPIError):
    """Exception raised when ElevenLabs API quota is exceeded."""
    
    def __init__(self, quota_type: str = "character", details: Optional[Dict[str, Any]] = None):
        message = f"ElevenLabs {quota_type} quota exceeded"
        super().__init__(
            message=message,
            error_code="quota_exceeded",
            quota_exceeded=True,
            details=details or {"quota_type": quota_type},
            status_code=429
        )


class VoiceGenerationError(ElevenLabsAPIError):
    """Exception raised when voice synthesis fails."""
    
    def __init__(self, message: str, voice_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if voice_id:
            error_details["voice_id"] = voice_id
            
        super().__init__(
            message=f"Voice generation failed: {message}",
            error_code="voice_generation_failed",
            details=error_details,
            status_code=500
        )


class ElevenLabsConfigurationError(Exception):
    """Exception raised when ElevenLabs configuration is invalid or missing."""
    
    def __init__(self, message: str, missing_config: Optional[str] = None):
        self.missing_config = missing_config
        super().__init__(message)


class AudioProcessingError(ElevenLabsAPIError):
    """Exception raised when audio processing fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Audio processing failed: {message}",
            error_code="audio_processing_failed",
            details=details,
            status_code=500
        )


# ============================================================================
# ElevenLabs Conversational AI Exceptions
# ============================================================================

class ElevenLabsAgentError(ElevenLabsAPIError):
    """Base exception for ElevenLabs agent-related errors."""
    
    def __init__(
        self, 
        message: str, 
        agent_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None
    ):
        error_details = details or {}
        if agent_id:
            error_details["agent_id"] = agent_id
            
        super().__init__(
            message=message,
            error_code="agent_error",
            details=error_details,
            status_code=status_code or 500
        )


class ElevenLabsAgentNotFoundError(ElevenLabsAgentError):
    """Exception raised when a requested agent is not found."""
    
    def __init__(self, agent_id: str, details: Optional[Dict[str, Any]] = None):
        message = f"Agent with ID '{agent_id}' not found"
        super().__init__(
            message=message,
            agent_id=agent_id,
            details=details,
            status_code=404
        )
        self.error_code = "agent_not_found"


class ElevenLabsAgentValidationError(ValidationError):
    """Exception raised when agent configuration validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if field:
            error_details["field"] = field
            
        super().__init__(
            message=f"Agent validation failed: {message}",
            details=error_details
        )


class ElevenLabsAgentCreationError(ElevenLabsAgentError):
    """Exception raised when agent creation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Agent creation failed: {message}",
            details=details,
            status_code=500
        )
        self.error_code = "agent_creation_failed"


class ConversationError(ElevenLabsAPIError):
    """Base exception for conversation-related errors."""
    
    def __init__(
        self, 
        message: str, 
        conversation_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None
    ):
        error_details = details or {}
        if conversation_id:
            error_details["conversation_id"] = conversation_id
            
        super().__init__(
            message=message,
            error_code="conversation_error",
            details=error_details,
            status_code=status_code or 500
        )


class ConversationNotFoundError(ConversationError):
    """Exception raised when a requested conversation is not found."""
    
    def __init__(self, conversation_id: str, details: Optional[Dict[str, Any]] = None):
        message = f"Conversation with ID '{conversation_id}' not found"
        super().__init__(
            message=message,
            conversation_id=conversation_id,
            details=details,
            status_code=404
        )
        self.error_code = "conversation_not_found"


class ConversationCreationError(ConversationError):
    """Exception raised when conversation creation fails."""
    
    def __init__(self, message: str, agent_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if agent_id:
            error_details["agent_id"] = agent_id
            
        super().__init__(
            message=f"Conversation creation failed: {message}",
            details=error_details,
            status_code=500
        )
        self.error_code = "conversation_creation_failed"


class PhoneCallInitiationError(ConversationError):
    """Exception raised when phone call initiation fails."""
    
    def __init__(
        self, 
        message: str, 
        conversation_id: Optional[str] = None,
        phone_number: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if phone_number:
            error_details["phone_number"] = phone_number
            
        super().__init__(
            message=f"Phone call initiation failed: {message}",
            conversation_id=conversation_id,
            details=error_details,
            status_code=500
        )
        self.error_code = "phone_call_initiation_failed"