"""
Integration tests for Twilio API interactions.

These tests require actual Twilio API credentials and test real API calls.
Set TEST_TWILIO_ACCOUNT_SID, TEST_TWILIO_AUTH_TOKEN, and TEST_TWILIO_PHONE_NUMBER 
environment variables to run these tests.

WARNING: These tests may create actual Twilio calls and incur charges.
Use test credentials and phone numbers only.
"""

import pytest
from datetime import datetime
from app.services.call_service import CallService, TwilioCallError
from app.models.call import TwilioCallResult


@pytest.mark.twilio
@pytest.mark.slow
class TestTwilioCallIntegration:
    """Integration tests for Twilio call operations."""
    
    @pytest.mark.asyncio
    async def test_create_twilio_call_real_api(self, call_service: CallService, integration_config):
        """
        Test creating a Twilio call with real API.
        
        Note: This test uses a safe test phone number that won't actually connect.
        """
        # Use a test WebSocket URL (doesn't need to be real for this test)
        test_join_url = "wss://test.example.com/stream/test_session_123"
        test_phone_number = integration_config["test_phone_number"]
        
        # Create Twilio call
        result = await call_service.create_twilio_call(test_join_url, test_phone_number)
        
        # Verify result structure
        assert isinstance(result, TwilioCallResult)
        assert result.sid is not None
        assert len(result.sid) > 0
        assert result.sid.startswith("CA")  # Twilio call SIDs start with CA
        assert result.status in ["queued", "initiated", "ringing", "in-progress", "completed", "failed", "busy", "no-answer", "canceled"]
        assert result.from_number == integration_config["twilio_phone_number"]
        assert result.to_number == test_phone_number
        assert isinstance(result.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_create_twilio_call_with_complex_url_real_api(self, call_service: CallService, integration_config):
        """Test creating a Twilio call with complex WebSocket URL."""
        # Use a complex WebSocket URL with parameters
        complex_join_url = "wss://api.ultravox.ai/stream/session_abc123?token=xyz789&user=test@example.com&param=value%20with%20spaces"
        test_phone_number = integration_config["test_phone_number"]
        
        # Create Twilio call
        result = await call_service.create_twilio_call(complex_join_url, test_phone_number)
        
        # Verify result
        assert isinstance(result, TwilioCallResult)
        assert result.sid.startswith("CA")
        assert result.from_number == integration_config["twilio_phone_number"]
        assert result.to_number == test_phone_number
    
    @pytest.mark.asyncio
    async def test_create_twilio_call_invalid_phone_number_real_api(self, call_service: CallService):
        """Test creating a Twilio call with invalid phone number."""
        test_join_url = "wss://test.example.com/stream/test_session_123"
        invalid_phone_number = "invalid_phone_number"
        
        # Should raise TwilioCallError for invalid phone number
        with pytest.raises(TwilioCallError) as exc_info:
            await call_service.create_twilio_call(test_join_url, invalid_phone_number)
        
        # Verify error message contains phone number validation info
        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in ["phone", "number", "invalid", "format"])
    
    @pytest.mark.asyncio
    async def test_create_twilio_call_international_number_real_api(self, call_service: CallService):
        """Test creating a Twilio call with international phone number format."""
        test_join_url = "wss://test.example.com/stream/test_session_123"
        international_number = "+441234567890"  # UK format test number
        
        try:
            result = await call_service.create_twilio_call(test_join_url, international_number)
            
            # If successful, verify result
            assert isinstance(result, TwilioCallResult)
            assert result.sid.startswith("CA")
            assert result.to_number == international_number
            
        except TwilioCallError as e:
            # International calls might not be enabled, which is acceptable
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ["international", "country", "not permitted"]):
                pytest.skip("International calling not enabled for test account")
            else:
                raise
    
    def test_create_streaming_twiml_format(self, call_service: CallService):
        """Test TwiML generation for streaming configuration."""
        test_join_url = "wss://api.ultravox.ai/stream/test_session_123"
        
        twiml = call_service._create_streaming_twiml(test_join_url)
        
        # Verify TwiML structure
        assert isinstance(twiml, str)
        assert twiml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert "<Response>" in twiml
        assert "</Response>" in twiml
        assert "<Connect>" in twiml
        assert "</Connect>" in twiml
        assert "<Stream" in twiml
        assert f'url="{test_join_url}"' in twiml
        assert "</Stream>" in twiml
    
    def test_create_streaming_twiml_with_special_characters(self, call_service: CallService):
        """Test TwiML generation with special characters in URL."""
        special_url = "wss://api.ultravox.ai/stream/test?token=abc123&user=test@example.com&data=hello%20world"
        
        twiml = call_service._create_streaming_twiml(special_url)
        
        # Verify special characters are preserved (Twilio handles encoding)
        assert special_url in twiml
        assert "<?xml version=" in twiml
        assert "<Response>" in twiml
        assert "<Connect>" in twiml
        assert "<Stream" in twiml


@pytest.mark.twilio
class TestTwilioErrorHandling:
    """Integration tests for Twilio API error handling."""
    
    @pytest.mark.asyncio
    async def test_invalid_credentials_handling(self, integration_config_service, http_client):
        """Test handling of invalid Twilio credentials."""
        from app.models.config import TwilioConfig
        
        # Create config with invalid credentials
        invalid_config = TwilioConfig(
            account_sid="AC" + "0" * 32,  # Invalid but properly formatted SID
            auth_token="invalid_token_12345",
            phone_number=integration_config_service.get_twilio_config().phone_number
        )
        
        # Override config service to return invalid config
        integration_config_service.get_twilio_config = lambda: invalid_config
        
        call_service = CallService(integration_config_service, http_client)
        
        # Try to create call with invalid credentials
        test_join_url = "wss://test.example.com/stream/test_session_123"
        test_phone_number = "+15551234567"
        
        with pytest.raises(TwilioCallError) as exc_info:
            await call_service.create_twilio_call(test_join_url, test_phone_number)
        
        # Verify error contains authentication-related information
        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in ["auth", "unauthorized", "invalid", "credentials"])
    
    @pytest.mark.asyncio
    async def test_invalid_from_number_handling(self, integration_config_service, http_client):
        """Test handling of invalid 'from' phone number."""
        from app.models.config import TwilioConfig
        
        # Create config with invalid phone number
        invalid_config = TwilioConfig(
            account_sid=integration_config_service.get_twilio_config().account_sid,
            auth_token=integration_config_service.get_twilio_config().auth_token,
            phone_number="+1000000000"  # Invalid phone number
        )
        
        # Override config service to return invalid config
        integration_config_service.get_twilio_config = lambda: invalid_config
        
        call_service = CallService(integration_config_service, http_client)
        
        # Try to create call with invalid from number
        test_join_url = "wss://test.example.com/stream/test_session_123"
        test_phone_number = "+15551234567"
        
        with pytest.raises(TwilioCallError) as exc_info:
            await call_service.create_twilio_call(test_join_url, test_phone_number)
        
        # Verify error contains phone number-related information
        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in ["phone", "number", "from", "invalid", "not owned"])
    
    @pytest.mark.asyncio
    async def test_malformed_twiml_handling(self, call_service: CallService, integration_config):
        """Test handling of malformed TwiML (by patching the TwiML creation)."""
        import unittest.mock
        
        # Patch the TwiML creation to return malformed XML
        with unittest.mock.patch.object(call_service, '_create_streaming_twiml', return_value="<invalid>xml"):
            
            test_join_url = "wss://test.example.com/stream/test_session_123"
            test_phone_number = integration_config["test_phone_number"]
            
            with pytest.raises(TwilioCallError) as exc_info:
                await call_service.create_twilio_call(test_join_url, test_phone_number)
            
            # Verify error is related to TwiML
            error_msg = str(exc_info.value).lower()
            assert any(keyword in error_msg for keyword in ["twiml", "xml", "malformed", "invalid"])


@pytest.mark.twilio
@pytest.mark.slow
class TestTwilioCallLifecycle:
    """Integration tests for Twilio call lifecycle operations."""
    
    @pytest.mark.asyncio
    async def test_call_creation_and_status_check(self, call_service: CallService, integration_config, http_client):
        """
        Test creating a call and checking its status.
        
        Note: This test creates an actual call that will be queued but not connected
        due to using a test phone number.
        """
        test_join_url = "wss://test.example.com/stream/test_session_123"
        test_phone_number = integration_config["test_phone_number"]
        
        # Create the call
        result = await call_service.create_twilio_call(test_join_url, test_phone_number)
        
        # Verify initial call state
        assert result.sid.startswith("CA")
        assert result.status in ["queued", "initiated"]
        
        # Note: In a full integration test, you might want to:
        # 1. Wait a moment for status to update
        # 2. Query Twilio API for call status
        # 3. Verify the call progresses through expected states
        # 4. Cancel the call to avoid charges
        
        # For this test, we'll just verify the call was created successfully
        assert result.from_number == integration_config["twilio_phone_number"]
        assert result.to_number == test_phone_number
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_calls(self, call_service: CallService, integration_config):
        """
        Test creating multiple calls concurrently.
        
        Note: This test may create multiple actual calls.
        """
        import asyncio
        
        test_join_url = "wss://test.example.com/stream/test_session_123"
        test_phone_number = integration_config["test_phone_number"]
        
        # Create multiple calls concurrently
        call_tasks = [
            call_service.create_twilio_call(f"{test_join_url}_{i}", test_phone_number)
            for i in range(3)
        ]
        
        results = await asyncio.gather(*call_tasks, return_exceptions=True)
        
        # Verify all calls were created successfully
        successful_calls = [r for r in results if isinstance(r, TwilioCallResult)]
        assert len(successful_calls) >= 1  # At least one should succeed
        
        # Verify each successful call has unique SID
        sids = [call.sid for call in successful_calls]
        assert len(set(sids)) == len(sids)  # All SIDs should be unique
        
        # Verify all calls have correct phone numbers
        for call in successful_calls:
            assert call.from_number == integration_config["twilio_phone_number"]
            assert call.to_number == test_phone_number