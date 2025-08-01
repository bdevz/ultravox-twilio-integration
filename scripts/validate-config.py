#!/usr/bin/env python3
"""
Configuration validation script for different environments.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.config_service import ConfigService, ConfigurationError


class ConfigValidator:
    """Validates configuration for different environments."""
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.project_root = Path(__file__).parent.parent
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def load_environment_config(self) -> Dict[str, str]:
        """Load environment-specific configuration."""
        # Load base .env file first
        base_env_file = self.project_root / ".env"
        if base_env_file.exists():
            load_dotenv(base_env_file)
        
        # Load environment-specific config
        env_file = self.project_root / f".env.{self.environment}"
        if env_file.exists():
            load_dotenv(env_file, override=True)
            print(f"✅ Loaded {self.environment} environment configuration")
        else:
            self.warnings.append(f"No .env.{self.environment} file found")
        
        return dict(os.environ)
    
    def validate_required_variables(self, config: Dict[str, str]) -> None:
        """Validate that all required environment variables are present."""
        required_vars = [
            "ULTRAVOX_API_KEY",
            "TWILIO_ACCOUNT_SID", 
            "TWILIO_AUTH_TOKEN",
            "TWILIO_PHONE_NUMBER"
        ]
        
        for var in required_vars:
            value = config.get(var)
            if not value:
                self.errors.append(f"Required environment variable {var} is not set")
            elif value.startswith("your_") and value.endswith("_here"):
                self.errors.append(f"Environment variable {var} contains placeholder value")
    
    def validate_configuration_service(self) -> None:
        """Validate configuration using the ConfigService."""
        try:
            config_service = ConfigService()
            config = config_service.load_configuration()
            print("✅ Configuration service validation passed")
            
            # Additional validations
            if config.debug and self.environment == "production":
                self.warnings.append("DEBUG mode is enabled in production environment")
            
            if config.cors_origins == ["*"] and self.environment == "production":
                self.warnings.append("CORS is set to allow all origins in production")
            
        except ConfigurationError as e:
            self.errors.append(f"Configuration service validation failed: {e.message}")
            if e.details:
                for key, detail in e.details.items():
                    self.errors.append(f"  {key}: {detail}")
    
    def validate_api_endpoints(self, config: Dict[str, str]) -> None:
        """Validate API endpoint configurations."""
        ultravox_url = config.get("ULTRAVOX_BASE_URL", "")
        if ultravox_url and not ultravox_url.startswith("https://"):
            if self.environment == "production":
                self.errors.append("ULTRAVOX_BASE_URL should use HTTPS in production")
            else:
                self.warnings.append("ULTRAVOX_BASE_URL is not using HTTPS")
    
    def validate_security_settings(self, config: Dict[str, str]) -> None:
        """Validate security-related settings."""
        if self.environment == "production":
            # Check for secure settings in production
            if config.get("LOG_REQUEST_BODY", "false").lower() == "true":
                self.warnings.append("LOG_REQUEST_BODY is enabled in production (may log sensitive data)")
            
            if config.get("LOG_RESPONSE_BODY", "false").lower() == "true":
                self.warnings.append("LOG_RESPONSE_BODY is enabled in production (may log sensitive data)")
            
            if config.get("DEBUG", "false").lower() == "true":
                self.errors.append("DEBUG mode should not be enabled in production")
    
    def validate_phone_number_format(self, config: Dict[str, str]) -> None:
        """Validate Twilio phone number format."""
        phone_number = config.get("TWILIO_PHONE_NUMBER", "")
        if phone_number and not phone_number.startswith("+"):
            self.warnings.append("TWILIO_PHONE_NUMBER should be in E.164 format (starting with +)")
    
    def validate(self) -> bool:
        """Run all validations and return True if valid."""
        print(f"🔍 Validating {self.environment} environment configuration...")
        
        # Load configuration
        config = self.load_environment_config()
        
        # Run validations
        self.validate_required_variables(config)
        self.validate_configuration_service()
        self.validate_api_endpoints(config)
        self.validate_security_settings(config)
        self.validate_phone_number_format(config)
        
        # Report results
        if self.errors:
            print("\n❌ Configuration validation failed:")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print("\n⚠️  Configuration warnings:")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        if not self.errors and not self.warnings:
            print("✅ Configuration validation passed with no issues")
        elif not self.errors:
            print("✅ Configuration validation passed with warnings")
        
        return len(self.errors) == 0


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Validate environment configuration")
    parser.add_argument("--env", default="development",
                       help="Environment to validate (default: development)")
    parser.add_argument("--strict", action="store_true",
                       help="Treat warnings as errors")
    args = parser.parse_args()
    
    validator = ConfigValidator(args.env)
    is_valid = validator.validate()
    
    if args.strict and validator.warnings:
        print("\n❌ Strict mode: treating warnings as errors")
        is_valid = False
    
    if is_valid:
        print(f"\n🎉 {args.env.title()} environment configuration is valid!")
        sys.exit(0)
    else:
        print(f"\n💥 {args.env.title()} environment configuration is invalid!")
        sys.exit(1)


if __name__ == "__main__":
    main()