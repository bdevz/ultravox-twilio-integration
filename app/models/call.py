"""Call models for Twilio integration."""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


class CallStatus(str, Enum):
    """Call status enumeration."""
    INITIATED = "initiated"
    RINGING = "ringing"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BUSY = "busy"
    NO_ANSWER = "no-answer"
    CANCELED = "canceled"


class CallRequest(BaseModel):
    """Request model for initiating a call."""
    phone_number: str = Field(..., description="Phone number to call")
    template_context: Dict[str, Any] = Field(default_factory=dict, description="Template context variables")
    agent_id: str = Field(..., description="Agent ID to use for the call")
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        """Validate phone number format with comprehensive checks."""
        if not v or not isinstance(v, str):
            raise ValueError('Phone number must be a non-empty string')
        
        # Remove all whitespace and common separators
        cleaned = re.sub(r'[\s\-\(\)\.]', '', v)
        
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', cleaned)
        
        # Must start with +
        if not cleaned.startswith('+'):
            raise ValueError('Phone number must start with + for international format')
        
        # Check for valid international format
        # Country code (1-3 digits) + national number (4-15 digits)
        if not re.match(r'^\+[1-9]\d{0,3}\d{4,15}$', cleaned):
            raise ValueError('Phone number must be in valid international format (+[country code][number], 7-18 digits total)')
        
        # Check total length (including +)
        if len(cleaned) < 8 or len(cleaned) > 18:
            raise ValueError('Phone number must be between 8-18 characters including country code')
        
        # Validate common country codes and their expected lengths
        country_patterns = {
            r'^\+1\d{10}$': 'North America (US/Canada) numbers must have exactly 10 digits after +1',
            r'^\+44\d{10,11}$': 'UK numbers must have 10-11 digits after +44',
            r'^\+33\d{9,10}$': 'France numbers must have 9-10 digits after +33',
            r'^\+49\d{10,12}$': 'Germany numbers must have 10-12 digits after +49',
            r'^\+81\d{10,11}$': 'Japan numbers must have 10-11 digits after +81',
            r'^\+86\d{11}$': 'China numbers must have exactly 11 digits after +86',
            r'^\+91\d{10}$': 'India numbers must have exactly 10 digits after +91',
        }
        
        # Check against known patterns for better error messages
        for pattern, error_msg in country_patterns.items():
            if cleaned.startswith(pattern.split('\\d')[0].replace('^\\+', '+')):
                if not re.match(pattern, cleaned):
                    raise ValueError(error_msg)
                break
        
        return cleaned
    
    @field_validator('agent_id')
    @classmethod
    def validate_agent_id(cls, v):
        """Validate agent ID format."""
        if not re.match(r'^[a-zA-Z0-9\-_]+$', v):
            raise ValueError('Agent ID can only contain letters, numbers, hyphens, and underscores')
        return v
    
    @field_validator('template_context')
    @classmethod
    def validate_template_context(cls, v):
        """Validate template context variables with comprehensive checks."""
        if not v:
            return v or {}
        
        if not isinstance(v, dict):
            raise ValueError('Template context must be a dictionary/object')
        
        # Check maximum number of context variables
        if len(v) > 50:
            raise ValueError('Template context cannot have more than 50 variables')
        
        reserved_keys = {'agent_id', 'call_id', 'timestamp', 'system', 'internal'}
        
        for key, value in v.items():
            # Validate key type and format
            if not isinstance(key, str):
                raise ValueError('Template context keys must be strings')
            
            # Check key length
            if len(key) > 100:
                raise ValueError(f'Template context key "{key}" is too long (max 100 characters)')
            
            # Check for reserved keys
            if key.lower() in reserved_keys:
                raise ValueError(f'Template context key "{key}" is reserved and cannot be used')
            
            # Validate key format (must be valid identifier)
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                raise ValueError(f'Template context key "{key}" must be a valid identifier (letters, numbers, underscore, starting with letter or underscore)')
            
            # Validate value types and content
            if value is None:
                continue
            elif isinstance(value, str):
                if len(value) > 1000:
                    raise ValueError(f'Template context string value for "{key}" is too long (max 1000 characters)')
                # Check for potentially dangerous content
                if any(dangerous in value.lower() for dangerous in ['<script', 'javascript:', 'data:', 'vbscript:']):
                    raise ValueError(f'Template context value for "{key}" contains potentially unsafe content')
            elif isinstance(value, (int, float)):
                # Check for reasonable numeric ranges
                if isinstance(value, int) and (value < -2**31 or value > 2**31 - 1):
                    raise ValueError(f'Template context integer value for "{key}" is out of range')
                elif isinstance(value, float) and (abs(value) > 1e10):
                    raise ValueError(f'Template context float value for "{key}" is out of range')
            elif isinstance(value, bool):
                pass  # Boolean values are always valid
            elif isinstance(value, (list, dict)):
                # Allow simple nested structures but validate them
                try:
                    import json
                    json_str = json.dumps(value)
                    if len(json_str) > 2000:
                        raise ValueError(f'Template context nested value for "{key}" is too large when serialized')
                except (TypeError, ValueError):
                    raise ValueError(f'Template context value for "{key}" contains non-serializable data')
            else:
                raise ValueError(f'Template context value for "{key}" must be a basic type (str, int, float, bool, None, list, dict)')
        
        return v


class CallResult(BaseModel):
    """Result model for call operations."""
    call_sid: str = Field(..., description="Twilio call SID")
    join_url: str = Field(..., description="Ultravox join URL")
    status: CallStatus = Field(..., description="Call status")
    created_at: datetime = Field(..., description="Call creation timestamp")
    agent_id: str = Field(..., description="Agent ID used for the call")
    phone_number: str = Field(..., description="Phone number called")
    
    @field_validator('call_sid')
    @classmethod
    def validate_call_sid(cls, v):
        """Validate Twilio call SID format."""
        if not re.match(r'^CA[a-f0-9]{32}$', v):
            raise ValueError('Call SID must be a valid Twilio SID format')
        return v
    
    @field_validator('join_url')
    @classmethod
    def validate_join_url(cls, v):
        """Validate join URL format."""
        if not re.match(r'^wss?://[^\s]+$', v):
            raise ValueError('Join URL must be a valid WebSocket URL')
        return v
    
    model_config = ConfigDict(use_enum_values=True)


class TwilioCallResult(BaseModel):
    """Result model for Twilio call operations."""
    sid: str = Field(..., description="Twilio call SID")
    status: str = Field(..., description="Twilio call status")
    from_number: str = Field(..., description="From phone number")
    to_number: str = Field(..., description="To phone number")
    created_at: Optional[datetime] = Field(None, description="Call creation timestamp")
    
    @field_validator('sid')
    @classmethod
    def validate_sid(cls, v):
        """Validate Twilio SID format."""
        if not re.match(r'^CA[a-f0-9]{32}$', v):
            raise ValueError('SID must be a valid Twilio SID format')
        return v
    
    @field_validator('from_number', 'to_number')
    @classmethod
    def validate_phone_numbers(cls, v):
        """Validate phone number format."""
        if not re.match(r'^\+[1-9]\d{6,14}$', v):
            raise ValueError('Phone number must be in international format')
        return v