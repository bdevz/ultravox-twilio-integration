"""
Configuration management for the application.
"""

from pydantic import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    
    # Application settings
    app_name: str = "Ultravox-Twilio Integration Service"
    debug: bool = False
    
    # Ultravox API settings
    ultravox_api_key: Optional[str] = None
    ultravox_base_url: str = "https://api.ultravox.ai"
    
    # Twilio settings
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def get_settings() -> Settings:
    """
    Get application settings.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()