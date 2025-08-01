"""
Unit tests for call service.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone

from app.services.call_service import (
    CallService, 
    CallServiceError, 
    UltravoxCallError, 
    TwilioCallError,
    get_call_service
)
from app.models.call import CallRequest, CallResult, TwilioCallResult, CallStatus
from app.models.config import UltravoxConfig, TwilioConfig
from app.services.config_service import ConfigService
from app.services.http_client_service import HTTPClientService, HTTPClientError


@pytest.fixture
def mock_config_service():
    """Mock configuration service."""
    config_service = Mock(spec=ConfigService)
    
    # Mock Ultravox config
    ultravox_config = UltravoxConfig(
        api_key="test_ultravox_key_1234567890",
        base_url="https://api.ultravox.ai"
    )
    config_service.get_ultravox_config.return_value = ultravox_config
    
    # Mock Twilio config with valid format
    twilio_config = TwilioConfig(
        account_sid="ACtest_fake_account_sid_for_testing",
        auth_token="fake_test_auth_token_for_testing",
        phone_number="+1234567890"
    )
    config_service.get_twilio_config.return_value = twilio_config
    
    return config_service


@pytest.fixture
def mock_http_client():
    """Mock HTTP client service."""
    return Mock(spec=HTTPClientService)


@pytest.fixture
def call_service(mock_config_service, mock_http_client):
    """Call service instance with mocked dependencies."""
    return CallService(mock_config_service, mock_http_client)


@pytest.fixture
def sample_call_request():
    """Sample call request for testing."""
    return CallRequest(
        phone_number="+1987654321",
        template_context={"user_name": "John", "order_id": "12345"},
        agent_id="agent_123"
    )


class TestCallService:
    """Test cases for CallService class."""
    
    @pytest.mark.asyncio
    async def test_initiate_call_success(self, call_service, sample_call_request, mock_http_client):
        """Test successful call initiation."""
        # Mock get_join_url response
        join_url = "wss://api.ultravox.ai/stream/test_join_url"
        
        # Mock Twilio response
        twilio_response = TwilioCallResult(
            sid="CA1234567890abcdef1234567890abcdef",
            status="queued",
            from_number="+1234567890",
            to_number="+1987654321"
        )
        
        # Setup mocks
        with patch.object(call_service, 'get_join_url', return_value=join_url) as mock_get_join_url, \
             patch.object(call_service, 'create_twilio_call', return_value=twilio_response) as mock_create_call:
            
            result = await call_service.initiate_call(sample_call_request)
            
            # Verify method calls
            mock_get_join_url.assert_called_once_with(
                agent_id="agent_123",
                context={"user_name": "John", "order_id": "12345"}
            )
            mock_create_call.assert_called_once_with(
                join_url=join_url,
                phone_number="+1987654321"
            )
            
            # Verify result
            assert isinstance(result, CallResult)
            assert result.call_sid == "CA1234567890abcdef1234567890abcdef"
            assert result.join_url == join_url
            assert result.status == CallStatus.INITIATED
            assert result.agent_id == "agent_123"
            assert result.phone_number == "+1987654321"
            assert isinstance(result.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_initiate_call_ultravox_error(self, call_service, sample_call_request):
        """Test call initiation with Ultravox error."""
        with patch.object(call_service, 'get_join_url', side_effect=UltravoxCallError("Ultravox API error")):
            with pytest.raises(UltravoxCallError, match="Ultravox API error"):
                await call_service.initiate_call(sample_call_request)
    
    @pytest.mark.asyncio
    async def test_initiate_call_twilio_error(self, call_service, sample_call_request):
        """Test call initiation with Twilio error."""
        join_url = "wss://api.ultravox.ai/stream/test_join_url"
        
        with patch.object(call_service, 'get_join_url', return_value=join_url), \
             patch.object(call_service, 'create_twilio_call', side_effect=TwilioCallError("Twilio API error")):
            
            with pytest.raises(TwilioCallError, match="Twilio API error"):
                await call_service.initiate_call(sample_call_request)
    
    @pytest.mark.asyncio
    async def test_initiate_call_unexpected_error(self, call_service, sample_call_request):
        """Test call initiation with unexpected error."""
        with patch.object(call_service, 'get_join_url', side_effect=Exception("Unexpected error")):
            with pytest.raises(CallServiceError, match="Failed to initiate call: Unexpected error"):
                await call_service.initiate_call(sample_call_request)
    
    @pytest.mark.asyncio
    async def test_get_join_url_success(self, call_service, mock_http_client):
        """Test successful join URL retrieval."""
        # Mock HTTP response
        mock_response = {
            "joinUrl": "wss://api.ultravox.ai/stream/test_join_url",
            "callId": "call_123"
        }
        mock_http_client.make_ultravox_request.return_value = mock_response
        
        result = await call_service.get_join_url(
            agent_id="agent_123",
            context={"user_name": "John"}
        )
        
        # Verify HTTP request
        mock_http_client.make_ultravox_request.assert_called_once_with(
            method="POST",
            endpoint="api/agents/agent_123/calls",
            data={
                "medium": {
                    "twilio": {
                        "phoneNumber": "+1234567890"
                    }
                },
                "templateContext": {"user_name": "John"}
            },
            api_key="test_ultravox_key_1234567890",
            base_url="https://api.ultravox.ai"
        )
        
        assert result == "wss://api.ultravox.ai/stream/test_join_url"
    
    @pytest.mark.asyncio
    async def test_get_join_url_no_context(self, call_service, mock_http_client):
        """Test join URL retrieval without template context."""
        mock_response = {"joinUrl": "wss://api.ultravox.ai/stream/test_join_url"}
        mock_http_client.make_ultravox_request.return_value = mock_response
        
        result = await call_service.get_join_url(
            agent_id="agent_123",
            context={}
        )
        
        # Verify request payload doesn't include templateContext
        call_args = mock_http_client.make_ultravox_request.call_args
        assert "templateContext" not in call_args[1]["data"]
        assert result == "wss://api.ultravox.ai/stream/test_join_url"
    
    @pytest.mark.asyncio
    async def test_get_join_url_missing_join_url(self, call_service, mock_http_client):
        """Test join URL retrieval with missing joinUrl in response."""
        mock_response = {"callId": "call_123"}  # Missing joinUrl
        mock_http_client.make_ultravox_request.return_value = mock_response
        
        with pytest.raises(UltravoxCallError, match="No join URL returned from Ultravox API"):
            await call_service.get_join_url("agent_123", {})
    
    @pytest.mark.asyncio
    async def test_get_join_url_http_error(self, call_service, mock_http_client):
        """Test join URL retrieval with HTTP error."""
        http_error = HTTPClientError("API error", status_code=400, details={"error": "invalid_agent"})
        mock_http_client.make_ultravox_request.side_effect = http_error
        
        with pytest.raises(UltravoxCallError, match="Failed to get join URL from Ultravox: API error"):
            await call_service.get_join_url("agent_123", {})
    
    @pytest.mark.asyncio
    async def test_get_join_url_unexpected_error(self, call_service, mock_http_client):
        """Test join URL retrieval with unexpected error."""
        mock_http_client.make_ultravox_request.side_effect = Exception("Unexpected error")
        
        with pytest.raises(UltravoxCallError, match="Unexpected error getting join URL: Unexpected error"):
            await call_service.get_join_url("agent_123", {})
    
    @pytest.mark.asyncio
    async def test_create_twilio_call_success(self, call_service, mock_http_client):
        """Test successful Twilio call creation."""
        # Mock Twilio API response
        mock_response = {
            "sid": "CA1234567890abcdef1234567890abcdef",
            "status": "queued",
            "from": "+1234567890",
            "to": "+1987654321"
        }
        mock_http_client.make_twilio_request.return_value = mock_response
        
        join_url = "wss://api.ultravox.ai/stream/test_join_url"
        phone_number = "+1987654321"
        
        result = await call_service.create_twilio_call(join_url, phone_number)
        
        # Verify HTTP request
        expected_twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://api.ultravox.ai/stream/test_join_url" />
    </Connect>
</Response>"""
        
        mock_http_client.make_twilio_request.assert_called_once_with(
            method="POST",
            endpoint="2010-04-01/Accounts/ACtest_fake_account_sid_for_testing/Calls.json",
            data={
                "To": phone_number,
                "From": "+1234567890",
                "Twiml": expected_twiml
            },
            account_sid="ACtest_fake_account_sid_for_testing",
            auth_token="fake_test_auth_token_for_testing"
        )
        
        # Verify result
        assert isinstance(result, TwilioCallResult)
        assert result.sid == "CA1234567890abcdef1234567890abcdef"
        assert result.status == "queued"
        assert result.from_number == "+1234567890"
        assert result.to_number == "+1987654321"
        assert isinstance(result.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_create_twilio_call_http_error(self, call_service, mock_http_client):
        """Test Twilio call creation with HTTP error."""
        http_error = HTTPClientError("Twilio API error", status_code=400, details={"error": "invalid_number"})
        mock_http_client.make_twilio_request.side_effect = http_error
        
        with pytest.raises(TwilioCallError, match="Failed to create Twilio call: Twilio API error"):
            await call_service.create_twilio_call("wss://test.com", "+1987654321")
    
    @pytest.mark.asyncio
    async def test_create_twilio_call_unexpected_error(self, call_service, mock_http_client):
        """Test Twilio call creation with unexpected error."""
        mock_http_client.make_twilio_request.side_effect = Exception("Unexpected error")
        
        with pytest.raises(TwilioCallError, match="Unexpected error creating Twilio call: Unexpected error"):
            await call_service.create_twilio_call("wss://test.com", "+1987654321")
    
    def test_create_streaming_twiml(self, call_service):
        """Test TwiML creation for streaming."""
        join_url = "wss://api.ultravox.ai/stream/test_join_url?param=value&other=test"
        
        result = call_service._create_streaming_twiml(join_url)
        
        expected_twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://api.ultravox.ai/stream/test_join_url?param=value&other=test" />
    </Connect>
</Response>"""
        
        assert result == expected_twiml
    
    def test_create_streaming_twiml_special_characters(self, call_service):
        """Test TwiML creation with special characters in URL."""
        join_url = "wss://api.ultravox.ai/stream/test?token=abc123&user=john@example.com"
        
        result = call_service._create_streaming_twiml(join_url)
        
        # Verify URL is included as-is (Twilio handles URL encoding)
        assert "wss://api.ultravox.ai/stream/test?token=abc123&user=john@example.com" in result
        assert result.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert "<Connect>" in result
        assert "<Stream url=" in result


class TestCallServiceIntegration:
    """Integration tests for call service."""
    
    @pytest.mark.asyncio
    async def test_full_call_flow_integration(self, mock_config_service):
        """Test complete call flow integration."""
        # Create real HTTP client (will be mocked)
        http_client = Mock(spec=HTTPClientService)
        call_service = CallService(mock_config_service, http_client)
        
        # Mock Ultravox response
        ultravox_response = {
            "joinUrl": "wss://api.ultravox.ai/stream/test_join_url",
            "callId": "call_123"
        }
        
        # Mock Twilio response
        twilio_response = {
            "sid": "CA1234567890abcdef1234567890abcdef",
            "status": "queued",
            "from": "+1234567890",
            "to": "+1987654321"
        }
        
        # Setup HTTP client mocks
        http_client.make_ultravox_request.return_value = ultravox_response
        http_client.make_twilio_request.return_value = twilio_response
        
        # Create call request
        call_request = CallRequest(
            phone_number="+1987654321",
            template_context={"user_name": "John", "order_id": "12345"},
            agent_id="agent_123"
        )
        
        # Execute call
        result = await call_service.initiate_call(call_request)
        
        # Verify Ultravox call
        http_client.make_ultravox_request.assert_called_once()
        ultravox_call_args = http_client.make_ultravox_request.call_args
        assert ultravox_call_args[1]["method"] == "POST"
        assert ultravox_call_args[1]["endpoint"] == "api/agents/agent_123/calls"
        assert ultravox_call_args[1]["data"]["templateContext"] == {"user_name": "John", "order_id": "12345"}
        
        # Verify Twilio call
        http_client.make_twilio_request.assert_called_once()
        twilio_call_args = http_client.make_twilio_request.call_args
        assert twilio_call_args[1]["method"] == "POST"
        assert twilio_call_args[1]["data"]["To"] == "+1987654321"
        assert twilio_call_args[1]["data"]["From"] == "+1234567890"
        
        # Verify final result
        assert result.call_sid == "CA1234567890abcdef1234567890abcdef"
        assert result.join_url == "wss://api.ultravox.ai/stream/test_join_url"
        assert result.status == CallStatus.INITIATED


class TestCallServiceFactory:
    """Test cases for call service factory function."""
    
    def test_get_call_service_default(self):
        """Test getting call service with default dependencies."""
        with patch('app.services.config_service.get_config_service') as mock_get_config:
            
            mock_config = Mock()
            mock_get_config.return_value = mock_config
            
            # Clear global instance
            import app.services.call_service
            app.services.call_service._call_service = None
            
            service = get_call_service()
            
            assert isinstance(service, CallService)
            mock_get_config.assert_called_once()
    
    def test_get_call_service_with_dependencies(self):
        """Test getting call service with provided dependencies."""
        mock_config = Mock()
        mock_http_client = Mock()
        
        # Clear global instance
        import app.services.call_service
        app.services.call_service._call_service = None
        
        service = get_call_service(mock_config, mock_http_client)
        
        assert isinstance(service, CallService)
        assert service.config_service == mock_config
        assert service.http_client == mock_http_client
    
    def test_get_call_service_singleton(self):
        """Test that get_call_service returns the same instance."""
        # Clear global instance
        import app.services.call_service
        app.services.call_service._call_service = None
        
        with patch('app.services.config_service.get_config_service') as mock_get_config:
            
            service1 = get_call_service()
            service2 = get_call_service()
            
            assert service1 is service2


if __name__ == "__main__":
    pytest.main([__file__])