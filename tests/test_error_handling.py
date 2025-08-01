"""
Tests for error handling system.
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.exceptions import (
    BaseServiceException,
    ConfigurationError,
    ValidationError as CustomValidationError,
    ExternalServiceError,
    UltravoxAPIError,
    TwilioAPIError,
    NetworkError,
    RateLimitError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    BusinessLogicError,
    TimeoutError
)
from app.error_handlers import (
    base_service_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
    register_exception_handlers
)
from app.logging_config import configure_logging, set_correlation_id


class TestCustomExceptions:
    """Test custom exception classes."""
    
    def test_base_service_exception(self):
        """Test BaseServiceException functionality."""
        details = {"key": "value"}
        exc = BaseServiceException(
            message="Test error",
            error_code="test_error",
            details=details,
            status_code=400
        )
        
        assert exc.message == "Test error"
        assert exc.error_code == "test_error"
        assert exc.details == details
        assert exc.status_code == 400
        assert isinstance(exc.timestamp, datetime)
        
        # Test to_dict method
        exc_dict = exc.to_dict()
        assert exc_dict["error"] == "test_error"
        assert exc_dict["message"] == "Test error"
        assert exc_dict["details"] == details
        assert "timestamp" in exc_dict
    
    def test_configuration_error(self):
        """Test ConfigurationError."""
        exc = ConfigurationError("Config missing", {"config": "missing"})
        
        assert exc.error_code == "configuration_error"
        assert exc.status_code == 500
        assert exc.message == "Config missing"
    
    def test_validation_error(self):
        """Test ValidationError."""
        exc = CustomValidationError("Invalid input", {"field": "name"})
        
        assert exc.error_code == "validation_error"
        assert exc.status_code == 400
        assert exc.message == "Invalid input"
    
    def test_external_service_error(self):
        """Test ExternalServiceError."""
        exc = ExternalServiceError("Service down", "test_service", {"code": 500})
        
        assert exc.error_code == "external_service_error"
        assert exc.service_name == "test_service"
        assert exc.details["service"] == "test_service"
        assert exc.status_code == 502
    
    def test_ultravox_api_error(self):
        """Test UltravoxAPIError."""
        exc = UltravoxAPIError("API error", {"endpoint": "/agents"}, 400)
        
        assert exc.error_code == "external_service_error"
        assert exc.service_name == "ultravox"
        assert exc.status_code == 400
    
    def test_twilio_api_error(self):
        """Test TwilioAPIError."""
        exc = TwilioAPIError("Call failed", {"sid": "123"})
        
        assert exc.error_code == "external_service_error"
        assert exc.service_name == "twilio"
        assert exc.status_code == 502
    
    def test_network_error(self):
        """Test NetworkError."""
        exc = NetworkError("Connection failed", {"host": "api.example.com"})
        
        assert exc.error_code == "network_error"
        assert exc.status_code == 503
    
    def test_rate_limit_error(self):
        """Test RateLimitError."""
        exc = RateLimitError("Rate limited", retry_after=60)
        
        assert exc.error_code == "rate_limit_exceeded"
        assert exc.status_code == 429
        assert exc.details["retry_after"] == 60
    
    def test_authentication_error(self):
        """Test AuthenticationError."""
        exc = AuthenticationError("Invalid token")
        
        assert exc.error_code == "authentication_error"
        assert exc.status_code == 401
    
    def test_authorization_error(self):
        """Test AuthorizationError."""
        exc = AuthorizationError("Access denied")
        
        assert exc.error_code == "authorization_error"
        assert exc.status_code == 403
    
    def test_resource_not_found_error(self):
        """Test ResourceNotFoundError."""
        exc = ResourceNotFoundError("agent", "123")
        
        assert exc.error_code == "resource_not_found"
        assert exc.status_code == 404
        assert exc.message == "agent '123' not found"
        assert exc.details["resource_type"] == "agent"
        assert exc.details["resource_id"] == "123"
    
    def test_business_logic_error(self):
        """Test BusinessLogicError."""
        exc = BusinessLogicError("Invalid state transition")
        
        assert exc.error_code == "business_logic_error"
        assert exc.status_code == 422
    
    def test_timeout_error(self):
        """Test TimeoutError."""
        exc = TimeoutError("API call", 30.0)
        
        assert exc.error_code == "timeout_error"
        assert exc.status_code == 504
        assert "API call" in exc.message
        assert exc.details["operation"] == "API call"
        assert exc.details["timeout_seconds"] == 30.0


class TestErrorHandlers:
    """Test error handler functions."""
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request object."""
        request = Mock()
        request.url = Mock()
        request.url.__str__ = Mock(return_value="http://test.com/api/test")
        request.method = "POST"
        return request
    
    @pytest.mark.asyncio
    async def test_base_service_exception_handler(self, mock_request):
        """Test base service exception handler."""
        set_correlation_id("test-correlation-id")
        
        exc = BaseServiceException(
            message="Test error",
            error_code="test_error",
            details={"key": "value"},
            status_code=400
        )
        
        response = await base_service_exception_handler(mock_request, exc)
        
        assert response.status_code == 400
        response_data = json.loads(response.body)
        assert response_data["error"] == "test_error"
        assert response_data["message"] == "Test error"
        assert response_data["details"]["key"] == "value"
        assert response_data["correlation_id"] == "test-correlation-id"
    
    @pytest.mark.asyncio
    async def test_http_exception_handler(self, mock_request):
        """Test HTTP exception handler."""
        set_correlation_id("test-correlation-id")
        
        exc = HTTPException(status_code=404, detail="Not found")
        
        response = await http_exception_handler(mock_request, exc)
        
        assert response.status_code == 404
        response_data = json.loads(response.body)
        assert response_data["error"] == "http_error"
        assert response_data["message"] == "Not found"
        assert response_data["correlation_id"] == "test-correlation-id"
    
    @pytest.mark.asyncio
    async def test_validation_exception_handler(self, mock_request):
        """Test validation exception handler."""
        set_correlation_id("test-correlation-id")
        
        # Create mock validation error
        exc = Mock(spec=RequestValidationError)
        exc.errors.return_value = [
            {
                "loc": ("body", "name"),
                "msg": "field required",
                "type": "value_error.missing",
                "input": None
            }
        ]
        
        response = await validation_exception_handler(mock_request, exc)
        
        assert response.status_code == 422
        response_data = json.loads(response.body)
        assert response_data["error"] == "validation_error"
        assert response_data["message"] == "Request validation failed"
        assert len(response_data["details"]["validation_errors"]) == 1
        assert response_data["correlation_id"] == "test-correlation-id"
    
    @pytest.mark.asyncio
    async def test_generic_exception_handler(self, mock_request):
        """Test generic exception handler."""
        set_correlation_id("test-correlation-id")
        
        exc = ValueError("Something went wrong")
        
        response = await generic_exception_handler(mock_request, exc)
        
        assert response.status_code == 500
        response_data = json.loads(response.body)
        assert response_data["error"] == "internal_server_error"
        assert "unexpected error occurred" in response_data["message"].lower()
        assert response_data["details"]["exception_type"] == "ValueError"
        assert response_data["correlation_id"] == "test-correlation-id"


class TestErrorHandlerIntegration:
    """Test error handler integration with FastAPI."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app with error handlers."""
        app = FastAPI()
        register_exception_handlers(app)
        
        @app.get("/test-base-exception")
        async def test_base_exception():
            raise BaseServiceException("Test error", "test_error", status_code=400)
        
        @app.get("/test-http-exception")
        async def test_http_exception():
            raise HTTPException(status_code=404, detail="Not found")
        
        @app.get("/test-generic-exception")
        async def test_generic_exception():
            raise ValueError("Generic error")
        
        @app.post("/test-validation")
        async def test_validation(data: dict):
            return data
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_base_service_exception_handling(self, client):
        """Test base service exception handling in FastAPI."""
        response = client.get("/test-base-exception")
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "test_error"
        assert data["message"] == "Test error"
    
    def test_http_exception_handling(self, client):
        """Test HTTP exception handling in FastAPI."""
        response = client.get("/test-http-exception")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "http_error"
        assert data["message"] == "Not found"
    
    @pytest.mark.asyncio
    async def test_generic_exception_handling_direct(self):
        """Test generic exception handler directly."""
        from app.error_handlers import generic_exception_handler
        
        # Create mock request
        mock_request = Mock()
        mock_request.url = Mock()
        mock_request.url.__str__ = Mock(return_value="http://test.com/api/test")
        mock_request.method = "GET"
        
        set_correlation_id("test-correlation-id")
        
        exc = ValueError("Generic error")
        
        response = await generic_exception_handler(mock_request, exc)
        
        assert response.status_code == 500
        response_data = json.loads(response.body)
        assert response_data["error"] == "internal_server_error"
        assert "unexpected error occurred" in response_data["message"].lower()
        assert response_data["details"]["exception_type"] == "ValueError"
        assert response_data["correlation_id"] == "test-correlation-id"
    
    def test_validation_error_handling(self, client):
        """Test validation error handling in FastAPI."""
        # Send invalid JSON to trigger validation error
        response = client.post(
            "/test-validation",
            json="invalid json structure"
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "validation_error"


class TestLoggingConfiguration:
    """Test logging configuration."""
    
    def test_configure_logging_json_format(self):
        """Test JSON logging configuration."""
        configure_logging(level="DEBUG", format_type="json")
        
        import logging
        logger = logging.getLogger("test")
        
        # Test that logger is configured
        assert logger.level <= logging.DEBUG
    
    def test_configure_logging_text_format(self):
        """Test text logging configuration."""
        configure_logging(level="INFO", format_type="text")
        
        import logging
        logger = logging.getLogger("test")
        
        # Test that logger is configured
        assert logger.level <= logging.INFO
    
    @patch('app.logging_config.correlation_id')
    def test_correlation_id_context(self, mock_correlation_id):
        """Test correlation ID context management."""
        from app.logging_config import set_correlation_id, get_correlation_id
        
        # Mock the context variable
        mock_correlation_id.get.return_value = "test-id"
        mock_correlation_id.set.return_value = None
        
        # Test setting and getting correlation ID
        set_correlation_id("test-id")
        mock_correlation_id.set.assert_called_with("test-id")
        
        result = get_correlation_id()
        mock_correlation_id.get.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])