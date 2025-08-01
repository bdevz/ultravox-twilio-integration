"""
Test configuration validation for integration tests.

This module provides utilities to validate that integration test configuration
is properly set up before running the actual tests.
"""

import os
import pytest
from typing import Dict, List, Optional


def get_integration_config() -> Dict[str, Optional[str]]:
    """Get integration test configuration from environment variables."""
    return {
        "ultravox_api_key": os.getenv("TEST_ULTRAVOX_API_KEY"),
        "ultravox_base_url": os.getenv("TEST_ULTRAVOX_BASE_URL", "https://api.ultravox.ai"),
        "twilio_account_sid": os.getenv("TEST_TWILIO_ACCOUNT_SID"),
        "twilio_auth_token": os.getenv("TEST_TWILIO_AUTH_TOKEN"),
        "twilio_phone_number": os.getenv("TEST_TWILIO_PHONE_NUMBER"),
        "test_phone_number": os.getenv("TEST_PHONE_NUMBER", "+15551234567"),
    }


def validate_ultravox_config(config: Dict[str, Optional[str]]) -> List[str]:
    """Validate Ultravox configuration and return list of issues."""
    issues = []
    
    if not config.get("ultravox_api_key"):
        issues.append("TEST_ULTRAVOX_API_KEY is not set")
    elif len(config["ultravox_api_key"]) < 10:
        issues.append("TEST_ULTRAVOX_API_KEY appears to be too short")
    
    base_url = config.get("ultravox_base_url", "")
    if not base_url.startswith("https://"):
        issues.append("TEST_ULTRAVOX_BASE_URL should start with https://")
    
    return issues


def validate_twilio_config(config: Dict[str, Optional[str]]) -> List[str]:
    """Validate Twilio configuration and return list of issues."""
    issues = []
    
    account_sid = config.get("twilio_account_sid")
    if not account_sid:
        issues.append("TEST_TWILIO_ACCOUNT_SID is not set")
    elif not account_sid.startswith("AC") or len(account_sid) != 34:
        issues.append("TEST_TWILIO_ACCOUNT_SID should start with 'AC' and be 34 characters long")
    
    auth_token = config.get("twilio_auth_token")
    if not auth_token:
        issues.append("TEST_TWILIO_AUTH_TOKEN is not set")
    elif len(auth_token) != 32:
        issues.append("TEST_TWILIO_AUTH_TOKEN should be 32 characters long")
    
    phone_number = config.get("twilio_phone_number")
    if not phone_number:
        issues.append("TEST_TWILIO_PHONE_NUMBER is not set")
    elif not phone_number.startswith("+"):
        issues.append("TEST_TWILIO_PHONE_NUMBER should start with '+' (E.164 format)")
    
    test_phone = config.get("test_phone_number")
    if test_phone and not test_phone.startswith("+"):
        issues.append("TEST_PHONE_NUMBER should start with '+' (E.164 format)")
    
    return issues


def validate_integration_config() -> Dict[str, List[str]]:
    """
    Validate complete integration test configuration.
    
    Returns:
        Dict with 'ultravox' and 'twilio' keys containing lists of validation issues
    """
    config = get_integration_config()
    
    return {
        "ultravox": validate_ultravox_config(config),
        "twilio": validate_twilio_config(config),
        "config": config
    }


class TestConfigurationValidation:
    """Test cases for configuration validation."""
    
    def test_config_loading(self):
        """Test that configuration can be loaded from environment."""
        config = get_integration_config()
        
        # Should always have default values
        assert config["ultravox_base_url"] == "https://api.ultravox.ai"
        assert config["test_phone_number"] == "+15551234567"
        
        # Other values may be None if not set
        assert "ultravox_api_key" in config
        assert "twilio_account_sid" in config
        assert "twilio_auth_token" in config
        assert "twilio_phone_number" in config
    
    def test_ultravox_config_validation(self):
        """Test Ultravox configuration validation logic."""
        # Test with missing API key
        config = {"ultravox_api_key": None, "ultravox_base_url": "https://api.ultravox.ai"}
        issues = validate_ultravox_config(config)
        assert any("TEST_ULTRAVOX_API_KEY is not set" in issue for issue in issues)
        
        # Test with short API key
        config = {"ultravox_api_key": "short", "ultravox_base_url": "https://api.ultravox.ai"}
        issues = validate_ultravox_config(config)
        assert any("appears to be too short" in issue for issue in issues)
        
        # Test with invalid base URL
        config = {"ultravox_api_key": "valid_key_12345", "ultravox_base_url": "http://insecure.com"}
        issues = validate_ultravox_config(config)
        assert any("should start with https://" in issue for issue in issues)
        
        # Test with valid config
        config = {"ultravox_api_key": "valid_key_12345", "ultravox_base_url": "https://api.ultravox.ai"}
        issues = validate_ultravox_config(config)
        assert len(issues) == 0
    
    def test_twilio_config_validation(self):
        """Test Twilio configuration validation logic."""
        # Test with missing values
        config = {}
        issues = validate_twilio_config(config)
        assert len(issues) >= 3  # Should have issues for missing SID, token, and phone
        
        # Test with invalid Account SID format
        config = {
            "twilio_account_sid": "invalid_sid",
            "twilio_auth_token": "a" * 32,
            "twilio_phone_number": "+1234567890"
        }
        issues = validate_twilio_config(config)
        assert any("should start with 'AC'" in issue for issue in issues)
        
        # Test with invalid auth token length
        config = {
            "twilio_account_sid": "AC" + "a" * 32,
            "twilio_auth_token": "short_token",
            "twilio_phone_number": "+1234567890"
        }
        issues = validate_twilio_config(config)
        assert any("should be 32 characters long" in issue for issue in issues)
        
        # Test with invalid phone number format
        config = {
            "twilio_account_sid": "AC" + "a" * 32,
            "twilio_auth_token": "a" * 32,
            "twilio_phone_number": "1234567890"  # Missing +
        }
        issues = validate_twilio_config(config)
        assert any("should start with '+'" in issue for issue in issues)
        
        # Test with valid config
        config = {
            "twilio_account_sid": "AC" + "a" * 32,
            "twilio_auth_token": "a" * 32,
            "twilio_phone_number": "+1234567890",
            "test_phone_number": "+15551234567"
        }
        issues = validate_twilio_config(config)
        assert len(issues) == 0
    
    def test_full_config_validation(self):
        """Test full configuration validation."""
        validation_result = validate_integration_config()
        
        # Should have both sections
        assert "ultravox" in validation_result
        assert "twilio" in validation_result
        assert "config" in validation_result
        
        # Config should be a dictionary
        assert isinstance(validation_result["config"], dict)
        
        # Issues should be lists
        assert isinstance(validation_result["ultravox"], list)
        assert isinstance(validation_result["twilio"], list)


def print_config_status():
    """Print current configuration status for debugging."""
    validation_result = validate_integration_config()
    config = validation_result["config"]
    
    print("Integration Test Configuration Status")
    print("=" * 50)
    
    print("\nUltravox Configuration:")
    print(f"  API Key: {'✓ Set' if config['ultravox_api_key'] else '✗ Not set'}")
    print(f"  Base URL: {config['ultravox_base_url']}")
    
    ultravox_issues = validation_result["ultravox"]
    if ultravox_issues:
        print("  Issues:")
        for issue in ultravox_issues:
            print(f"    - {issue}")
    else:
        print("  Status: ✓ Valid")
    
    print("\nTwilio Configuration:")
    print(f"  Account SID: {'✓ Set' if config['twilio_account_sid'] else '✗ Not set'}")
    print(f"  Auth Token: {'✓ Set' if config['twilio_auth_token'] else '✗ Not set'}")
    print(f"  Phone Number: {config['twilio_phone_number'] or '✗ Not set'}")
    print(f"  Test Phone: {config['test_phone_number']}")
    
    twilio_issues = validation_result["twilio"]
    if twilio_issues:
        print("  Issues:")
        for issue in twilio_issues:
            print(f"    - {issue}")
    else:
        print("  Status: ✓ Valid")
    
    print("\nOverall Status:")
    total_issues = len(ultravox_issues) + len(twilio_issues)
    if total_issues == 0:
        print("  ✓ All configurations are valid")
        print("  Ready to run integration tests!")
    else:
        print(f"  ✗ {total_issues} configuration issue(s) found")
        print("  Please fix the issues above before running integration tests.")
    
    print("\nTo run integration tests:")
    print("  pytest tests/integration/ -v")
    print("\nTo run specific test categories:")
    print("  pytest tests/integration/ -v -m ultravox")
    print("  pytest tests/integration/ -v -m twilio")
    print("  pytest tests/integration/ -v -m e2e")


if __name__ == "__main__":
    print_config_status()