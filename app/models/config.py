"""Configuration models for external services."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class UltravoxConfig(BaseModel):
    """Configuration for Ultravox API."""
    api_key: str = Field(..., description="Ultravox API key")
    base_url: str = Field(default="https://api.ultravox.ai", description="Ultravox API base URL")
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v):
        """Validate API key format."""
        if not v or len(v.strip()) == 0:
            raise ValueError('API key cannot be empty')
        
        # Basic validation - should be a non-empty string with reasonable length
        if len(v) < 10 or len(v) > 200:
            raise ValueError('API key must be between 10 and 200 characters')
        
        # Check for common patterns that might indicate invalid keys
        if v.startswith('sk-') and len(v) < 20:
            raise ValueError('API key appears to be invalid format')
        
        return v.strip()
    
    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v):
        """Validate base URL format."""
        if not re.match(r'^https?://[^\s/$.?#].[^\s]*$', v):
            raise ValueError('Base URL must be a valid HTTP/HTTPS URL')
        
        # Remove trailing slash for consistency
        return v.rstrip('/')


class TwilioConfig(BaseModel):
    """Configuration for Twilio API."""
    account_sid: str = Field(..., description="Twilio Account SID")
    auth_token: str = Field(..., description="Twilio Auth Token")
    phone_number: str = Field(..., description="Twilio phone number for outbound calls")
    
    @field_validator('account_sid')
    @classmethod
    def validate_account_sid(cls, v):
        """Validate Twilio Account SID format."""
        if not re.match(r'^AC[a-f0-9]{32}$', v):
            raise ValueError('Account SID must be a valid Twilio Account SID format (AC followed by 32 hex characters)')
        return v
    
    @field_validator('auth_token')
    @classmethod
    def validate_auth_token(cls, v):
        """Validate Twilio Auth Token format."""
        if not v or len(v.strip()) == 0:
            raise ValueError('Auth token cannot be empty')
        
        # Twilio auth tokens are typically 32 characters of hex
        if not re.match(r'^[a-f0-9]{32}$', v):
            raise ValueError('Auth token must be 32 hexadecimal characters')
        
        return v
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        """Validate Twilio phone number format."""
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', v)
        
        # Check for valid international format (minimum 7 digits after country code)
        if not re.match(r'^\+[1-9]\d{6,14}$', cleaned):
            raise ValueError('Phone number must be in international format (e.g., +1234567890)')
        
        return cleaned


class AppConfig(BaseModel):
    """Main application configuration."""
    ultravox: UltravoxConfig = Field(..., description="Ultravox configuration")
    twilio: TwilioConfig = Field(..., description="Twilio configuration")
    debug: bool = Field(default=False, description="Debug mode flag")
    log_level: str = Field(default="INFO", description="Logging level")
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {", ".join(valid_levels)}')
        return v.upper()


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")
    timestamp: str = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    
    @field_validator('error')
    @classmethod
    def validate_error_type(cls, v):
        """Validate error type format."""
        if not re.match(r'^[A-Z_]+$', v):
            raise ValueError('Error type must be uppercase with underscores')
        return v