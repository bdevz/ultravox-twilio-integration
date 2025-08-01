"""
Unit tests for the configuration service.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from app.services.config_service import ConfigService, ConfigurationError, get_config_service
from app.models.config import UltravoxConfig, TwilioConfig, AppConfig


class TestConfigService:
    """Test cases for ConfigService class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config_service = ConfigService()
        # Clear any cached configurations
        self.config_service._config = None
        self.config_service._ultravox_config = None
        self.config_service._twilio_config = None
    
    @patch.dict(os.environ, {
        'ULTRAVOX_API_KEY': 'test_ultravox_key_12345',
        'ULTRAVOX_BASE_URL': 'https://api.ultravox.ai',
        'TWILIO_ACCOUNT_SID': 'AC' + 'a' * 32,
        'TWILIO_AUTH_TOKEN': 'a' * 32,
        'TWILIO_PHONE_NUMBER': '+1234567890',
        'DEBUG': 'true',
        'LOG_LEVEL': 'DEBUG'
    })
    def test_load_configuration_success(self):
        """Test successful configuration loading."""
        config = self.config_service.load_configuration()
        
        assert isinstance(config, AppConfig)
        assert config.ultravox.api_key == 'test_ultravox_key_12345'
        assert config.ultravox.base_url == 'https://api.ultravox.ai'
        assert config.twilio.account_sid == 'AC' + 'a' * 32
        assert config.twilio.auth_token == 'a' * 32
        assert config.twilio.phone_number == '+1234567890'
        assert config.debug is True
        assert config.log_level == 'DEBUG'
    
    @patch.dict(os.environ, {
        'ULTRAVOX_API_KEY': 'test_key_12345',
        'TWILIO_ACCOUNT_SID': 'AC' + 'a' * 32,
        'TWILIO_AUTH_TOKEN': 'a' * 32,
        'TWILIO_PHONE_NUMBER': '+1234567890'
    })
    def test_load_configuration_with_defaults(self):
        """Test configuration loading with default values."""
        config = self.config_service.load_configuration()
        
        assert config.ultravox.base_url == 'https://api.ultravox.ai'
        assert config.debug is False
        assert config.log_level == 'INFO'
    
    @patch.dict(os.environ, {}, clear=True)
    def test_load_configuration_missing_required_vars(self):
        """Test configuration loading with missing required variables."""
        with pytest.raises(ConfigurationError) as exc_info:
            self.config_service.load_configuration()
        
        assert "Required environment variable" in str(exc_info.value)
        assert exc_info.value.details is not None
    
    @patch.dict(os.environ, {
        'ULTRAVOX_API_KEY': 'valid_key_12345',
        'ULTRAVOX_BASE_URL': 'https://api.ultravox.ai'
    })
    def test_get_ultravox_config_success(self):
        """Test successful Ultravox configuration loading."""
        config = self.config_service.get_ultravox_config()
        
        assert isinstance(config, UltravoxConfig)
        assert config.api_key == 'valid_key_12345'
        assert config.base_url == 'https://api.ultravox.ai'
    
    @patch.dict(os.environ, {
        'ULTRAVOX_API_KEY': 'valid_key_12345'
    })
    def test_get_ultravox_config_with_default_url(self):
        """Test Ultravox configuration with default base URL."""
        config = self.config_service.get_ultravox_config()
        
        assert config.base_url == 'https://api.ultravox.ai'
    
    @patch.dict(os.environ, {}, clear=True)
    def test_get_ultravox_config_missing_api_key(self):
        """Test Ultravox configuration with missing API key."""
        with pytest.raises(ConfigurationError) as exc_info:
            self.config_service.get_ultravox_config()
        
        assert "ULTRAVOX_API_KEY" in str(exc_info.value)
        assert exc_info.value.details["missing_variable"] == "ULTRAVOX_API_KEY"
    
    @patch.dict(os.environ, {
        'ULTRAVOX_API_KEY': 'short'  # Too short, should fail validation
    })
    def test_get_ultravox_config_invalid_api_key(self):
        """Test Ultravox configuration with invalid API key."""
        with pytest.raises(ConfigurationError) as exc_info:
            self.config_service.get_ultravox_config()
        
        assert "Invalid Ultravox configuration" in str(exc_info.value)
        assert "validation_errors" in exc_info.value.details
    
    @patch.dict(os.environ, {
        'ULTRAVOX_API_KEY': 'valid_key_12345',
        'ULTRAVOX_BASE_URL': 'invalid-url'  # Invalid URL format
    })
    def test_get_ultravox_config_invalid_url(self):
        """Test Ultravox configuration with invalid base URL."""
        with pytest.raises(ConfigurationError) as exc_info:
            self.config_service.get_ultravox_config()
        
        assert "Invalid Ultravox configuration" in str(exc_info.value)
    
    @patch.dict(os.environ, {
        'TWILIO_ACCOUNT_SID': 'AC' + 'a' * 32,
        'TWILIO_AUTH_TOKEN': 'a' * 32,
        'TWILIO_PHONE_NUMBER': '+1234567890'
    })
    def test_get_twilio_config_success(self):
        """Test successful Twilio configuration loading."""
        config = self.config_service.get_twilio_config()
        
        assert isinstance(config, TwilioConfig)
        assert config.account_sid == 'AC' + 'a' * 32
        assert config.auth_token == 'a' * 32
        assert config.phone_number == '+1234567890'
    
    @patch.dict(os.environ, {}, clear=True)
    def test_get_twilio_config_missing_vars(self):
        """Test Twilio configuration with missing variables."""
        with pytest.raises(ConfigurationError) as exc_info:
            self.config_service.get_twilio_config()
        
        assert "TWILIO_ACCOUNT_SID" in str(exc_info.value)
    
    @patch.dict(os.environ, {
        'TWILIO_ACCOUNT_SID': 'invalid_sid',  # Invalid format
        'TWILIO_AUTH_TOKEN': 'a' * 32,
        'TWILIO_PHONE_NUMBER': '+1234567890'
    })
    def test_get_twilio_config_invalid_account_sid(self):
        """Test Twilio configuration with invalid Account SID."""
        with pytest.raises(ConfigurationError) as exc_info:
            self.config_service.get_twilio_config()
        
        assert "Invalid Twilio configuration" in str(exc_info.value)
    
    @patch.dict(os.environ, {
        'TWILIO_ACCOUNT_SID': 'AC' + 'a' * 32,
        'TWILIO_AUTH_TOKEN': 'invalid_token',  # Invalid format
        'TWILIO_PHONE_NUMBER': '+1234567890'
    })
    def test_get_twilio_config_invalid_auth_token(self):
        """Test Twilio configuration with invalid auth token."""
        with pytest.raises(ConfigurationError) as exc_info:
            self.config_service.get_twilio_config()
        
        assert "Invalid Twilio configuration" in str(exc_info.value)
    
    @patch.dict(os.environ, {
        'TWILIO_ACCOUNT_SID': 'AC' + 'a' * 32,
        'TWILIO_AUTH_TOKEN': 'a' * 32,
        'TWILIO_PHONE_NUMBER': 'invalid_phone'  # Invalid format
    })
    def test_get_twilio_config_invalid_phone_number(self):
        """Test Twilio configuration with invalid phone number."""
        with pytest.raises(ConfigurationError) as exc_info:
            self.config_service.get_twilio_config()
        
        assert "Invalid Twilio configuration" in str(exc_info.value)
    
    @patch.dict(os.environ, {
        'ULTRAVOX_API_KEY': 'test_key_12345',
        'TWILIO_ACCOUNT_SID': 'AC' + 'a' * 32,
        'TWILIO_AUTH_TOKEN': 'a' * 32,
        'TWILIO_PHONE_NUMBER': '+1234567890'
    })
    def test_validate_configuration_success(self):
        """Test successful configuration validation."""
        result = self.config_service.validate_configuration()
        assert result is True
    
    @patch.dict(os.environ, {}, clear=True)
    def test_validate_configuration_failure(self):
        """Test configuration validation failure."""
        with pytest.raises(ConfigurationError):
            self.config_service.validate_configuration()
    
    def test_get_config_before_loading(self):
        """Test getting config before loading."""
        with pytest.raises(ConfigurationError) as exc_info:
            self.config_service.get_config()
        
        assert "Configuration not loaded" in str(exc_info.value)
    
    @patch.dict(os.environ, {
        'ULTRAVOX_API_KEY': 'test_key_12345',
        'TWILIO_ACCOUNT_SID': 'AC' + 'a' * 32,
        'TWILIO_AUTH_TOKEN': 'a' * 32,
        'TWILIO_PHONE_NUMBER': '+1234567890'
    })
    def test_get_config_after_loading(self):
        """Test getting config after loading."""
        self.config_service.load_configuration()
        config = self.config_service.get_config()
        
        assert isinstance(config, AppConfig)
    
    def test_caching_behavior(self):
        """Test that configurations are cached after first load."""
        with patch.dict(os.environ, {
            'ULTRAVOX_API_KEY': 'test_key_12345',
            'ULTRAVOX_BASE_URL': 'https://api.ultravox.ai'
        }):
            # First call
            config1 = self.config_service.get_ultravox_config()
            # Second call should return cached version
            config2 = self.config_service.get_ultravox_config()
            
            assert config1 is config2  # Same object reference
    
    def test_get_required_env_success(self):
        """Test successful required environment variable retrieval."""
        with patch.dict(os.environ, {'TEST_VAR': 'test_value'}):
            value = self.config_service._get_required_env('TEST_VAR')
            assert value == 'test_value'
    
    def test_get_required_env_missing(self):
        """Test required environment variable missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                self.config_service._get_required_env('MISSING_VAR')
            
            assert "MISSING_VAR" in str(exc_info.value)
            assert exc_info.value.details["missing_variable"] == "MISSING_VAR"
    
    def test_get_required_env_empty(self):
        """Test required environment variable empty."""
        with patch.dict(os.environ, {'EMPTY_VAR': '   '}):
            with pytest.raises(ConfigurationError) as exc_info:
                self.config_service._get_required_env('EMPTY_VAR')
            
            assert "EMPTY_VAR" in str(exc_info.value)
    
    def test_get_env_bool_true_values(self):
        """Test boolean environment variable parsing for true values."""
        true_values = ['true', 'True', '1', 'yes', 'YES', 'on', 'ON']
        
        for value in true_values:
            with patch.dict(os.environ, {'BOOL_VAR': value}):
                result = self.config_service._get_env_bool('BOOL_VAR')
                assert result is True, f"Failed for value: {value}"
    
    def test_get_env_bool_false_values(self):
        """Test boolean environment variable parsing for false values."""
        false_values = ['false', 'False', '0', 'no', 'NO', 'off', 'OFF']
        
        for value in false_values:
            with patch.dict(os.environ, {'BOOL_VAR': value}):
                result = self.config_service._get_env_bool('BOOL_VAR')
                assert result is False, f"Failed for value: {value}"
    
    def test_get_env_bool_default(self):
        """Test boolean environment variable with default value."""
        with patch.dict(os.environ, {}, clear=True):
            # Test default False
            result = self.config_service._get_env_bool('MISSING_VAR')
            assert result is False
            
            # Test custom default
            result = self.config_service._get_env_bool('MISSING_VAR', default=True)
            assert result is True
    
    def test_get_env_bool_invalid_value(self):
        """Test boolean environment variable with invalid value."""
        with patch.dict(os.environ, {'BOOL_VAR': 'maybe'}):
            result = self.config_service._get_env_bool('BOOL_VAR', default=True)
            assert result is True  # Should return default
    
    def test_format_validation_errors(self):
        """Test validation error formatting."""
        # Create a mock ValidationError
        mock_error = MagicMock(spec=ValidationError)
        mock_error.errors.return_value = [
            {
                'loc': ('field1',),
                'msg': 'Field is required',
                'type': 'value_error.missing',
                'input': None
            },
            {
                'loc': ('nested', 'field2'),
                'msg': 'Invalid format',
                'type': 'value_error.format',
                'input': 'invalid_value'
            }
        ]
        
        result = self.config_service._format_validation_errors(mock_error)
        
        assert 'validation_errors' in result
        errors = result['validation_errors']
        assert 'field1' in errors
        assert 'nested.field2' in errors
        assert errors['field1']['message'] == 'Field is required'
        assert errors['nested.field2']['message'] == 'Invalid format'


class TestConfigServiceGlobal:
    """Test cases for global configuration service functions."""
    
    def test_get_config_service_singleton(self):
        """Test that get_config_service returns the same instance."""
        service1 = get_config_service()
        service2 = get_config_service()
        
        assert service1 is service2
        assert isinstance(service1, ConfigService)


class TestConfigurationError:
    """Test cases for ConfigurationError exception."""
    
    def test_configuration_error_basic(self):
        """Test basic ConfigurationError creation."""
        error = ConfigurationError("Test error")
        
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == {}
    
    def test_configuration_error_with_details(self):
        """Test ConfigurationError with details."""
        details = {"field": "value", "code": 123}
        error = ConfigurationError("Test error", details)
        
        assert error.message == "Test error"
        assert error.details == details