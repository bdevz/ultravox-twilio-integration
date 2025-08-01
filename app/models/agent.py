"""Agent models for Ultravox integration."""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


class AgentStatus(str, Enum):
    """Agent status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CREATING = "creating"
    ERROR = "error"


class AgentConfig(BaseModel):
    """Configuration for an Ultravox agent."""
    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    prompt: str = Field(..., min_length=1, max_length=10000, description="Agent prompt")
    voice: Optional[str] = Field(default="default", description="Voice configuration")
    language: Optional[str] = Field(default="en", description="Language code")
    template_variables: Optional[Dict[str, str]] = Field(default_factory=dict, description="Template variables")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate agent name contains only allowed characters."""
        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', v):
            raise ValueError('Agent name can only contain letters, numbers, spaces, hyphens, and underscores')
        return v.strip()
    
    @field_validator('language')
    @classmethod
    def validate_language(cls, v):
        """Validate language code format."""
        if v and not re.match(r'^[a-z]{2}(-[A-Z]{2})?$', v):
            raise ValueError('Language must be in format "en" or "en-US"')
        return v
    
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


class Agent(BaseModel):
    """Ultravox agent model."""
    id: str = Field(..., description="Unique agent identifier")
    config: AgentConfig = Field(..., description="Agent configuration")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    status: AgentStatus = Field(..., description="Agent status")
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        """Validate agent ID format."""
        if not re.match(r'^[a-zA-Z0-9\-_]+$', v):
            raise ValueError('Agent ID can only contain letters, numbers, hyphens, and underscores')
        return v
    
    model_config = ConfigDict(use_enum_values=True)