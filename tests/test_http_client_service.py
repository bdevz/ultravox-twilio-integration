"""
Unit tests for HTTP client service.
"""

import pytest
import pytest_asyncio
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientResponseError, ClientConnectionError, ServerTimeoutError

from app.services.http_client_service import (
    HTTPClientService,
    HTTPClientError,
    HTTPClientTimeoutError,
    HTTPClientConnectionError,
    HTTPClientResponseError,
    RetryConfig,
    get_http_client_service,
    close_http_client_service
)


class TestHTTPClientService:
    """Test cases for HTTPClientService."""
    
    @pytest_asyncio.fixture
    async def http_service(self):
        """Create HTTP client service for testing."""
        service = HTTPClientService(timeout=5.0)
        try:
            yield service
        finally:
            await service.close()
    
    @pytest.mark.asyncio
    async def test_successful_request(self, http_service):
        """Test successful HTTP request."""
        test_data = {"result": "success", "id": 123}
        
        # Mock the _handle_response method to return test data
        with patch.object(http_service, '_handle_response', return_value=test_data) as mock_handle:
            # Mock the session and its request method
            mock_session = AsyncMock()
            mock_session.closed = False
            mock_response = AsyncMock()
            
            # Create async context manager for session.request
            async def async_context_manager(*args, **kwargs):
                return mock_response
            
            mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)
            
            http_service._session = mock_session
            
            # Execute
            result = await http_service.make_request(
                method="GET",
                url="https://api.example.com/test",
                headers={"Custom-Header": "value"}
            )
            
            # Verify
            assert result == test_data
            mock_handle.assert_called_once_with(mock_response)
            mock_session.request.assert_called_once_with(
                method="GET",
                url="https://api.example.com/test",
                headers={"Custom-Header": "value"},
                data=None,
                params=None
            )
    
    @pytest.mark.asyncio
    async def test_request_with_json_data(self, http_service):
        """Test HTTP request with JSON data."""
        request_data = {"name": "test", "value": 42}
        response_data = {"id": 1, "status": "created"}
        
        with patch.object(http_service, '_handle_response', return_value=response_data):
            mock_session = AsyncMock()
            mock_session.closed = False
            mock_response = AsyncMock()
            
            mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)
            
            http_service._session = mock_session
            
            result = await http_service.make_request(
                method="POST",
                url="https://api.example.com/create",
                data=request_data,
                auth_token="test-token"
            )
            
            assert result == response_data
            mock_session.request.assert_called_once_with(
                method="POST",
                url="https://api.example.com/create",
                headers={
                    "Authorization": "Bearer test-token",
                    "Content-Type": "application/json"
                },
                data=json.dumps(request_data),
                params=None
            )
    
    @pytest.mark.asyncio
    async def test_handle_response_success(self, http_service):
        """Test successful response handling."""
        test_data = {"result": "success"}
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.status = 200
        mock_response.text.return_value = json.dumps(test_data)
        
        result = await http_service._handle_response(mock_response)
        assert result == test_data
    
    @pytest.mark.asyncio
    async def test_handle_response_empty(self, http_service):
        """Test empty response handling."""
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.status = 200
        mock_response.text.return_value = ""
        
        result = await http_service._handle_response(mock_response)
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_handle_response_error(self, http_service):
        """Test error response handling."""
        error_data = {"error": "NOT_FOUND", "message": "Resource not found"}
        mock_response = AsyncMock()
        mock_response.ok = False
        mock_response.status = 404
        mock_response.text.return_value = json.dumps(error_data)
        mock_response.url = "https://api.example.com/notfound"
        mock_response.headers = {}
        
        with pytest.raises(HTTPClientResponseError) as exc_info:
            await http_service._handle_response(mock_response)
        
        error = exc_info.value
        assert error.status_code == 404
        assert "Resource not found" in error.message
        assert error.details["error_data"] == error_data
    
    @pytest.mark.asyncio
    async def test_handle_response_invalid_json(self, http_service):
        """Test invalid JSON response handling."""
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.status = 200
        mock_response.text.return_value = "invalid json {"
        
        with pytest.raises(HTTPClientError) as exc_info:
            await http_service._handle_response(mock_response)
        
        error = exc_info.value
        assert "Failed to parse JSON response" in error.message
        assert error.status_code == 200
    
    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, http_service):
        """Test timeout error handling with retries."""
        mock_session = AsyncMock()
        mock_session.closed = False
        mock_session.request.side_effect = asyncio.TimeoutError()
        
        http_service._session = mock_session
        http_service.retry_config.max_retries = 1
        http_service.retry_config.base_delay = 0.01  # Fast retry for testing
        
        with pytest.raises(HTTPClientTimeoutError) as exc_info:
            await http_service.make_request("GET", "https://api.example.com/slow")
        
        error = exc_info.value
        assert "Request timeout" in error.message
        assert error.details["attempt"] == 2  # Last attempt number
        assert mock_session.request.call_count == 2  # Initial + 1 retry
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, http_service):
        """Test connection error handling with retries."""
        mock_session = AsyncMock()
        mock_session.closed = False
        mock_session.request.side_effect = ClientConnectionError("Connection refused")
        
        http_service._session = mock_session
        http_service.retry_config.max_retries = 1
        http_service.retry_config.base_delay = 0.01
        
        with pytest.raises(HTTPClientConnectionError) as exc_info:
            await http_service.make_request("GET", "https://api.example.com/unreachable")
        
        error = exc_info.value
        assert "Connection error" in error.message
        assert "Connection refused" in error.message
        assert mock_session.request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(self, http_service):
        """Test that client errors (4xx) are not retried."""
        mock_response = AsyncMock()
        mock_response.ok = False
        mock_response.status = 400
        mock_response.text.return_value = '{"error": "Bad Request"}'
        mock_response.url = "https://api.example.com/bad"
        mock_response.headers = {}
        
        mock_session = AsyncMock()
        mock_session.closed = False
        mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)
        
        http_service._session = mock_session
        
        with pytest.raises(HTTPClientResponseError) as exc_info:
            await http_service.make_request("POST", "https://api.example.com/bad")
        
        error = exc_info.value
        assert error.status_code == 400
        # Should only be called once (no retries for 4xx)
        assert mock_session.request.call_count == 1
    
    def test_calculate_retry_delay(self, http_service):
        """Test retry delay calculation."""
        http_service.retry_config.base_delay = 1.0
        http_service.retry_config.exponential_base = 2.0
        http_service.retry_config.max_delay = 10.0
        http_service.retry_config.jitter = False
        
        # Test exponential backoff
        assert http_service._calculate_retry_delay(0) == 1.0
        assert http_service._calculate_retry_delay(1) == 2.0
        assert http_service._calculate_retry_delay(2) == 4.0
        assert http_service._calculate_retry_delay(3) == 8.0
        
        # Test max delay cap
        assert http_service._calculate_retry_delay(10) == 10.0
    
    def test_calculate_retry_delay_with_jitter(self, http_service):
        """Test retry delay calculation with jitter."""
        http_service.retry_config.base_delay = 2.0
        http_service.retry_config.exponential_base = 2.0
        http_service.retry_config.jitter = True
        
        delay = http_service._calculate_retry_delay(1)
        # With jitter, delay should be between 1.0 and 4.0 (50% to 100% of base delay * 2^1)
        assert 1.0 <= delay <= 4.0
    
    @pytest.mark.asyncio
    async def test_ultravox_request(self, http_service):
        """Test Ultravox-specific request method."""
        response_data = {"agent_id": "agent_123", "status": "active"}
        
        with patch.object(http_service, 'make_request', return_value=response_data) as mock_make_request:
            result = await http_service.make_ultravox_request(
                method="POST",
                endpoint="/api/agents",
                data={"name": "test-agent"},
                api_key="ultravox-key-123"
            )
            
            assert result == response_data
            mock_make_request.assert_called_once_with(
                method="POST",
                url="https://api.ultravox.ai/api/agents",
                data={"name": "test-agent"},
                auth_token="ultravox-key-123"
            )
    
    @pytest.mark.asyncio
    async def test_twilio_request(self, http_service):
        """Test Twilio-specific request method."""
        response_data = {"sid": "CA123", "status": "queued"}
        
        with patch.object(http_service, 'make_request', return_value=response_data) as mock_make_request:
            result = await http_service.make_twilio_request(
                method="POST",
                endpoint="/2010-04-01/Accounts/AC123/Calls.json",
                data={"To": "+1234567890", "From": "+0987654321"},
                account_sid="AC123",
                auth_token="twilio-token"
            )
            
            assert result == response_data
            
            # Check that Basic Auth headers were added
            call_args = mock_make_request.call_args
            headers = call_args[1]["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"].startswith("Basic ")
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test using HTTP client as context manager."""
        async with HTTPClientService() as client:
            assert client._session is not None
            assert not client._session.closed
        
        # Session should be closed after exiting context
        assert client._session is None or client._session.closed
    
    @pytest.mark.asyncio
    async def test_session_recreation(self, http_service):
        """Test that session is recreated if closed."""
        # Ensure session exists
        await http_service._ensure_session()
        first_session = http_service._session
        
        # Close session
        await http_service.close()
        assert http_service._session is None
        
        # Ensure session is recreated
        await http_service._ensure_session()
        second_session = http_service._session
        
        assert second_session is not None
        assert second_session != first_session


class TestRetryConfig:
    """Test cases for RetryConfig."""
    
    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
    
    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=30.0,
            exponential_base=1.5,
            jitter=False
        )
        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.exponential_base == 1.5
        assert config.jitter is False


class TestGlobalService:
    """Test cases for global service functions."""
    
    @pytest.mark.asyncio
    async def test_get_global_service(self):
        """Test getting global HTTP client service."""
        # Clean up any existing service
        await close_http_client_service()
        
        # Get service
        service1 = await get_http_client_service()
        service2 = await get_http_client_service()
        
        # Should return same instance
        assert service1 is service2
        assert service1._session is not None
        
        # Clean up
        await close_http_client_service()
    
    @pytest.mark.asyncio
    async def test_close_global_service(self):
        """Test closing global HTTP client service."""
        # Get service
        service = await get_http_client_service()
        assert service._session is not None
        
        # Close service
        await close_http_client_service()
        
        # Service should be closed
        assert service._session is None or service._session.closed


class TestHTTPClientExceptions:
    """Test cases for HTTP client exceptions."""
    
    def test_http_client_error(self):
        """Test HTTPClientError exception."""
        error = HTTPClientError(
            "Test error",
            status_code=500,
            details={"key": "value"}
        )
        assert error.message == "Test error"
        assert error.status_code == 500
        assert error.details == {"key": "value"}
        assert str(error) == "Test error"
    
    def test_http_client_timeout_error(self):
        """Test HTTPClientTimeoutError exception."""
        error = HTTPClientTimeoutError("Timeout occurred")
        assert error.message == "Timeout occurred"
        assert error.status_code is None
        assert error.details == {}
    
    def test_http_client_connection_error(self):
        """Test HTTPClientConnectionError exception."""
        error = HTTPClientConnectionError(
            "Connection failed",
            details={"host": "example.com"}
        )
        assert error.message == "Connection failed"
        assert error.details == {"host": "example.com"}
    
    def test_http_client_response_error(self):
        """Test HTTPClientResponseError exception."""
        error = HTTPClientResponseError(
            "Bad request",
            status_code=400,
            details={"field": "invalid"}
        )
        assert error.message == "Bad request"
        assert error.status_code == 400
        assert error.details == {"field": "invalid"}