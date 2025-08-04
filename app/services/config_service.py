"""
Configuration service for loading and validating environment variables.
"""

import os
import logging
from typing import Optional, Dict, Any
from pydantic import ValidationError
from app.models.config import UltravoxConfig, TwilioConfig, AppConfig
from app.models.elevenlabs import ElevenLabsConfig


logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ConfigService:
    """Service for loading and validating application configuration."""
    
    def __init__(self):
        self._config: Optional[AppConfig] = None
        self._ultravox_config: Optional[UltravoxConfig] = None
        self._twilio_config: Optional[TwilioConfig] = None
        self._elevenlabs_config: Optional[ElevenLabsConfig] = None
    
    def load_configuration(self) -> AppConfig:
        """
        Load and validate complete application configuration.
        
        Returns:
            AppConfig: Validated application configuration
            
        Raises:
            ConfigurationError: If configuration is invalid or missing
        """
        try:
            ultravox_config = self.get_ultravox_config()
            twilio_config = self.get_twilio_config()
            
            # ElevenLabs config is optional
            elevenlabs_config = None
            try:
                elevenlabs_config = self.get_elevenlabs_config()
            except ConfigurationError as e:
                logger.info(f"ElevenLabs configuration not available: {e.message}")
            
            # Load application-level settings
            debug = self._get_env_bool("DEBUG", default=False)
            log_level = os.getenv("LOG_LEVEL", "INFO")
            
            self._config = AppConfig(
                ultravox=ultravox_config,
                twilio=twilio_config,
                debug=debug,
                log_level=log_level
            )
            
            logger.info("Configuration loaded successfully")
            return self._config
            
        except ValidationError as e:
            error_details = self._format_validation_errors(e)
            raise ConfigurationError(
                "Configuration validation failed",
                details=error_details
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration: {str(e)}"
            )
    
    def get_ultravox_config(self) -> UltravoxConfig:
        """
        Load and validate Ultravox configuration.
        
        Returns:
            UltravoxConfig: Validated Ultravox configuration
            
        Raises:
            ConfigurationError: If Ultravox configuration is invalid
        """
        if self._ultravox_config is not None:
            return self._ultravox_config
        
        try:
            api_key = self._get_required_env("ULTRAVOX_API_KEY")
            base_url = os.getenv("ULTRAVOX_BASE_URL", "https://api.ultravox.ai")
            
            self._ultravox_config = UltravoxConfig(
                api_key=api_key,
                base_url=base_url
            )
            
            logger.debug("Ultravox configuration loaded")
            return self._ultravox_config
            
        except ValidationError as e:
            error_details = self._format_validation_errors(e)
            raise ConfigurationError(
                "Invalid Ultravox configuration",
                details=error_details
            )
    
    def get_twilio_config(self) -> TwilioConfig:
        """
        Load and validate Twilio configuration.
        
        Returns:
            TwilioConfig: Validated Twilio configuration
            
        Raises:
            ConfigurationError: If Twilio configuration is invalid
        """
        if self._twilio_config is not None:
            return self._twilio_config
        
        try:
            account_sid = self._get_required_env("TWILIO_ACCOUNT_SID")
            auth_token = self._get_required_env("TWILIO_AUTH_TOKEN")
            phone_number = self._get_required_env("TWILIO_PHONE_NUMBER")
            
            self._twilio_config = TwilioConfig(
                account_sid=account_sid,
                auth_token=auth_token,
                phone_number=phone_number
            )
            
            logger.debug("Twilio configuration loaded")
            return self._twilio_config
            
        except ValidationError as e:
            error_details = self._format_validation_errors(e)
            raise ConfigurationError(
                "Invalid Twilio configuration",
                details=error_details
            )
    
    def get_elevenlabs_config(self) -> ElevenLabsConfig:
        """
        Load and validate ElevenLabs configuration.
        
        Returns:
            ElevenLabsConfig: Validated ElevenLabs configuration
            
        Raises:
            ConfigurationError: If ElevenLabs configuration is invalid or missing
        """
        if self._elevenlabs_config is not None:
            return self._elevenlabs_config
        
        try:
            # Check if ElevenLabs is enabled
            if not self._get_env_bool("ENABLE_ELEVENLABS", default=False):
                raise ConfigurationError("ElevenLabs integration is disabled")
            
            api_key = self._get_required_env("ELEVENLABS_API_KEY")
            base_url = os.getenv("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io")
            default_voice_id = os.getenv("ELEVENLABS_DEFAULT_VOICE", "21m00Tcm4TlvDq8ikWAM")
            max_text_length = int(os.getenv("ELEVENLABS_MAX_TEXT_LENGTH", "5000"))
            request_timeout = float(os.getenv("ELEVENLABS_REQUEST_TIMEOUT", "30.0"))
            enable_preview = self._get_env_bool("ELEVENLABS_PREVIEW_ENABLED", default=True)
            
            self._elevenlabs_config = ElevenLabsConfig(
                api_key=api_key,
                base_url=base_url,
                default_voice_id=default_voice_id,
                max_text_length=max_text_length,
                request_timeout=request_timeout,
                enable_preview=enable_preview
            )
            
            logger.debug("ElevenLabs configuration loaded")
            return self._elevenlabs_config
            
        except ValidationError as e:
            error_details = self._format_validation_errors(e)
            raise ConfigurationError(
                "Invalid ElevenLabs configuration",
                details=error_details
            )
        except ValueError as e:
            raise ConfigurationError(
                f"Invalid ElevenLabs configuration value: {str(e)}"
            )
    
    def is_elevenlabs_enabled(self) -> bool:
        """
        Check if ElevenLabs integration is enabled and configured.
        
        Returns:
            bool: True if ElevenLabs is enabled and configured
        """
        try:
            self.get_elevenlabs_config()
            return True
        except ConfigurationError:
            return False
    
    def validate_configuration(self) -> bool:
        """
        Validate that all required configuration is present and valid.
        
        Returns:
            bool: True if configuration is valid
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            self.load_configuration()
            logger.info("Configuration validation successful")
            return True
        except ConfigurationError:
            logger.error("Configuration validation failed")
            raise
    
    def get_config(self) -> AppConfig:
        """
        Get the loaded application configuration.
        
        Returns:
            AppConfig: The loaded configuration
            
        Raises:
            ConfigurationError: If configuration hasn't been loaded
        """
        if self._config is None:
            raise ConfigurationError("Configuration not loaded. Call load_configuration() first.")
        return self._config
    
    def _get_required_env(self, key: str) -> str:
        """
        Get a required environment variable.
        
        Args:
            key: Environment variable name
            
        Returns:
            str: Environment variable value
            
        Raises:
            ConfigurationError: If environment variable is missing
        """
        value = os.getenv(key)
        if value is None or value.strip() == "":
            raise ConfigurationError(
                f"Required environment variable '{key}' is missing or empty",
                details={"missing_variable": key}
            )
        return value.strip()
    
    def _get_env_bool(self, key: str, default: bool = False) -> bool:
        """
        Get a boolean environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not set
            
        Returns:
            bool: Boolean value
        """
        value = os.getenv(key, "").lower()
        if value in ("true", "1", "yes", "on"):
            return True
        elif value in ("false", "0", "no", "off"):
            return False
        else:
            return default
    
    def _format_validation_errors(self, error: ValidationError) -> Dict[str, Any]:
        """
        Format Pydantic validation errors into a readable format.
        
        Args:
            error: Pydantic ValidationError
            
        Returns:
            dict: Formatted error details
        """
        formatted_errors = {}
        for err in error.errors():
            field_path = ".".join(str(loc) for loc in err["loc"])
            formatted_errors[field_path] = {
                "message": err["msg"],
                "type": err["type"],
                "input": err.get("input")
            }
        return {"validation_errors": formatted_errors}


# Global configuration service instance
_config_service: Optional[ConfigService] = None


def get_config_service() -> ConfigService:
    """
    Get the global configuration service instance.
    
    Returns:
        ConfigService: The configuration service instance
    """
    global _config_service
    if _config_service is None:
        _config_service = ConfigService()
    return _config_service