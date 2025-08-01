"""
Tests for application lifecycle management including startup, shutdown, and health checks.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import (
    create_app,
    startup_sequence,
    shutdown_sequence,
    register_call,
    unregister_call,
    get_app_state,
    app_state
)
from app.services.config_service import ConfigurationError
from app.services.http_client_service import HTTPClientService
from app.exceptions import AuthenticationError, NetworkError, TimeoutError


class TestApplicationStartup:
    """Test application startup sequence."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Reset app state before each test."""
        app_state.clear()
        app_state.update({
            "startup_complete": False,
            "shutdown_initiated": False,
            "ongoing_calls": set(),
            "config_validated": False
        })
    
    @pytest.mark.asyncio
    async def test_successful_startup(self):
        """Test successful application startup sequence."""
        with patch('app.main.get_config_service') as mock_get_config:
            # Mock configuration service
            mock_config_service = Mock()
            mock_config = Mock()
            mock_config.ultravox.api_key = "test-key"
            mock_config.twilio.auth_token = "test-token"
            mock_config.debug = False
            mock_config.log_level = "INFO"
            
            mock_config_service.load_configuration.return_value = mock_config
            mock_get_config.return_value = mock_config_service
            
            with patch('app.main.setup_signal_handlers'):
                # Execute startup sequence
                await startup_sequence()
                
                # Verify state
                state = get_app_state()
                assert state["startup_complete"] is True
                assert state["config_validated"] is True
                assert state["shutdown_initiated"] is False
                assert len(state["ongoing_calls"]) == 0
    
    @pytest.mark.asyncio
    async def test_startup_with_configuration_error(self):
        """Test startup failure due to configuration error."""
        with patch('app.main.get_config_service') as mock_get_config:
            # Mock configuration service to raise error
            mock_config_service = Mock()
            mock_config_service.load_configuration.side_effect = ConfigurationError(
                "Missing required configuration",
                details={"missing_variable": "ULTRAVOX_API_KEY"}
            )
            mock_get_config.return_value = mock_config_service
            
            # Execute startup sequence and expect error
            with pytest.raises(ConfigurationError):
                await startup_sequence()
            
            # Verify state
            state = get_app_state()
            assert state["startup_complete"] is False
            assert state["config_validated"] is False
    
    @pytest.mark.asyncio
    async def test_startup_with_unexpected_error(self):
        """Test startup failure due to unexpected error."""
        with patch('app.main.get_config_service') as mock_get_config:
            # Mock configuration service to raise unexpected error
            mock_config_service = Mock()
            mock_config_service.load_configuration.side_effect = Exception("Unexpected error")
            mock_get_config.return_value = mock_config_service
            
            # Execute startup sequence and expect error
            with pytest.raises(Exception):
                await startup_sequence()
            
            # Verify state
            state = get_app_state()
            assert state["startup_complete"] is False


class TestApplicationShutdown:
    """Test application shutdown sequence."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Reset app state before each test."""
        app_state.clear()
        app_state.update({
            "startup_complete": True,
            "shutdown_initiated": False,
            "ongoing_calls": set(),
            "config_validated": True
        })
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown_no_ongoing_calls(self):
        """Test graceful shutdown with no ongoing calls."""
        with patch('app.main.close_http_client_service') as mock_close_http:
            mock_close_http.return_value = AsyncMock()
            
            # Execute shutdown sequence
            await shutdown_sequence()
            
            # Verify HTTP client was closed
            mock_close_http.assert_called_once()
            
            # Verify state was cleared
            state = get_app_state()
            assert len(state) == 0  # State should be cleared
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown_with_ongoing_calls(self):
        """Test graceful shutdown with ongoing calls that complete quickly."""
        # Add some ongoing calls
        register_call("call-1")
        register_call("call-2")
        
        with patch('app.main.close_http_client_service') as mock_close_http:
            mock_close_http.return_value = AsyncMock()
            
            # Simulate calls completing during shutdown
            async def simulate_call_completion():
                await asyncio.sleep(0.1)  # Short delay
                unregister_call("call-1")
                unregister_call("call-2")
            
            # Start call completion simulation
            completion_task = asyncio.create_task(simulate_call_completion())
            
            # Execute shutdown sequence
            await shutdown_sequence()
            
            # Wait for completion task
            await completion_task
            
            # Verify HTTP client was closed
            mock_close_http.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown_timeout_with_ongoing_calls(self):
        """Test shutdown timeout when calls don't complete in time."""
        # Add ongoing calls that won't complete
        register_call("call-1")
        register_call("call-2")
        
        with patch('app.main.close_http_client_service') as mock_close_http:
            mock_close_http.return_value = AsyncMock()
            
            # Mock asyncio.sleep to speed up the test
            original_sleep = asyncio.sleep
            
            async def fast_sleep(duration):
                if duration == 1:  # The 1-second sleep in shutdown loop
                    await original_sleep(0.01)  # Make it much faster
                else:
                    await original_sleep(duration)
            
            with patch('asyncio.sleep', side_effect=fast_sleep):
                # Execute shutdown sequence (should timeout)
                await shutdown_sequence()
            
            # Verify HTTP client was still closed despite timeout
            mock_close_http.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown_already_initiated(self):
        """Test that shutdown can only be initiated once."""
        app_state["shutdown_initiated"] = True
        
        with patch('app.main.close_http_client_service') as mock_close_http:
            mock_close_http.return_value = AsyncMock()
            
            # Execute shutdown sequence
            await shutdown_sequence()
            
            # Verify HTTP client was not closed (shutdown was skipped)
            mock_close_http.assert_not_called()


class TestCallTracking:
    """Test call tracking for graceful shutdown."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Reset app state before each test."""
        app_state.clear()
        app_state.update({
            "startup_complete": True,
            "shutdown_initiated": False,
            "ongoing_calls": set(),
            "config_validated": True
        })
    
    def test_register_call(self):
        """Test registering an ongoing call."""
        call_id = "test-call-123"
        
        # Register call
        register_call(call_id)
        
        # Verify call is tracked
        state = get_app_state()
        assert call_id in state["ongoing_calls"]
        assert len(state["ongoing_calls"]) == 1
    
    def test_unregister_call(self):
        """Test unregistering a completed call."""
        call_id = "test-call-123"
        
        # Register and then unregister call
        register_call(call_id)
        unregister_call(call_id)
        
        # Verify call is no longer tracked
        state = get_app_state()
        assert call_id not in state["ongoing_calls"]
        assert len(state["ongoing_calls"]) == 0
    
    def test_unregister_nonexistent_call(self):
        """Test unregistering a call that wasn't registered."""
        call_id = "nonexistent-call"
        
        # Unregister call that wasn't registered (should not raise error)
        unregister_call(call_id)
        
        # Verify state is unchanged
        state = get_app_state()
        assert len(state["ongoing_calls"]) == 0
    
    def test_multiple_calls(self):
        """Test tracking multiple ongoing calls."""
        call_ids = ["call-1", "call-2", "call-3"]
        
        # Register multiple calls
        for call_id in call_ids:
            register_call(call_id)
        
        # Verify all calls are tracked
        state = get_app_state()
        assert len(state["ongoing_calls"]) == 3
        for call_id in call_ids:
            assert call_id in state["ongoing_calls"]
        
        # Unregister one call
        unregister_call("call-2")
        
        # Verify correct call was removed
        state = get_app_state()
        assert len(state["ongoing_calls"]) == 2
        assert "call-1" in state["ongoing_calls"]
        assert "call-2" not in state["ongoing_calls"]
        assert "call-3" in state["ongoing_calls"]


class TestHealthChecks:
    """Test health check endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Reset app state before each test."""
        app_state.clear()
        app_state.update({
            "startup_complete": True,
            "shutdown_initiated": False,
            "ongoing_calls": set(),
            "config_validated": True
        })
    
    def test_basic_health_check_healthy(self, client):
        """Test basic health check when service is healthy."""
        with patch('app.api.routes.get_config_service') as mock_get_config:
            # Mock configuration service
            mock_config_service = Mock()
            mock_ultravox_config = Mock()
            mock_ultravox_config.api_key = "test-key"
            mock_twilio_config = Mock()
            mock_twilio_config.auth_token = "test-token"
            
            mock_config_service.get_ultravox_config.return_value = mock_ultravox_config
            mock_config_service.get_twilio_config.return_value = mock_twilio_config
            mock_get_config.return_value = mock_config_service
            
            # Make health check request
            response = client.get("/api/v1/health")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "ultravox-twilio-integration"
            assert data["uptime"]["startup_complete"] is True
            assert data["uptime"]["config_validated"] is True
            assert data["checks"]["configuration"] == "ok"
            assert data["checks"]["ultravox_config"] == "ok"
            assert data["checks"]["twilio_config"] == "ok"
    
    def test_basic_health_check_starting(self, client):
        """Test basic health check when service is starting."""
        # Set startup as incomplete
        app_state["startup_complete"] = False
        
        with patch('app.api.routes.get_config_service') as mock_get_config:
            # Mock configuration service
            mock_config_service = Mock()
            mock_ultravox_config = Mock()
            mock_ultravox_config.api_key = "test-key"
            mock_twilio_config = Mock()
            mock_twilio_config.auth_token = "test-token"
            
            mock_config_service.get_ultravox_config.return_value = mock_ultravox_config
            mock_config_service.get_twilio_config.return_value = mock_twilio_config
            mock_get_config.return_value = mock_config_service
            
            # Make health check request
            response = client.get("/api/v1/health")
            
            # Verify response
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "starting"
    
    def test_basic_health_check_degraded(self, client):
        """Test basic health check when service is degraded."""
        with patch('app.api.routes.get_config_service') as mock_get_config:
            # Mock configuration service with missing API key
            mock_config_service = Mock()
            mock_ultravox_config = Mock()
            mock_ultravox_config.api_key = None  # Missing API key
            mock_twilio_config = Mock()
            mock_twilio_config.auth_token = "test-token"
            
            mock_config_service.get_ultravox_config.return_value = mock_ultravox_config
            mock_config_service.get_twilio_config.return_value = mock_twilio_config
            mock_get_config.return_value = mock_config_service
            
            # Make health check request
            response = client.get("/api/v1/health")
            
            # Verify response
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "degraded"
            assert data["checks"]["ultravox_config"] == "missing_api_key"
    
    def test_basic_health_check_configuration_error(self, client):
        """Test basic health check when configuration fails."""
        with patch('app.api.routes.get_config_service') as mock_get_config:
            # Mock configuration service to raise error
            mock_config_service = Mock()
            mock_config_service.get_ultravox_config.side_effect = ConfigurationError("Config error")
            mock_get_config.return_value = mock_config_service
            
            # Make health check request
            response = client.get("/api/v1/health")
            
            # Verify response
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["error"] == "configuration_error"
    
    def test_detailed_health_check_configuration_error(self, client):
        """Test detailed health check when configuration fails."""
        with patch('app.api.routes.get_config_service') as mock_get_config:
            # Mock configuration service to raise error
            mock_config_service = Mock()
            mock_config_service.get_ultravox_config.side_effect = ConfigurationError("Config error")
            mock_get_config.return_value = mock_config_service
            
            # Make detailed health check request
            response = client.get("/api/v1/health/detailed")
            
            # Verify response
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy" or data["status"] == "degraded"
    
    def test_detailed_health_check_healthy_with_external_services(self, client):
        """Test detailed health check when all services are healthy."""
        with patch('app.api.routes.get_config_service') as mock_get_config:
            # Mock configuration service
            mock_config_service = Mock()
            mock_ultravox_config = Mock()
            mock_ultravox_config.api_key = "test-key"
            mock_ultravox_config.base_url = "https://api.ultravox.ai"
            mock_twilio_config = Mock()
            mock_twilio_config.auth_token = "test-token"
            mock_twilio_config.account_sid = "test-sid"
            
            mock_config_service.get_ultravox_config.return_value = mock_ultravox_config
            mock_config_service.get_twilio_config.return_value = mock_twilio_config
            mock_get_config.return_value = mock_config_service
            
            # Mock the HTTP client methods directly on the instance
            with patch.object(HTTPClientService, 'make_ultravox_request', new_callable=AsyncMock) as mock_ultravox:
                with patch.object(HTTPClientService, 'make_twilio_request', new_callable=AsyncMock) as mock_twilio:
                    with patch.object(HTTPClientService, 'close', new_callable=AsyncMock) as mock_close:
                        # Set up successful responses
                        mock_ultravox.return_value = {"agents": []}
                        mock_twilio.return_value = {"account_sid": "test-sid"}
                        
                        # Make detailed health check request
                        response = client.get("/api/v1/health/detailed")
                        
                        # Verify response
                        assert response.status_code == 200
                        data = response.json()
                        assert data["status"] == "healthy"
                        assert data["checks"]["ultravox_api"] == "ok"
                        assert data["checks"]["twilio_api"] == "ok"
    
    def test_detailed_health_check_ultravox_auth_error(self, client):
        """Test detailed health check when Ultravox authentication fails."""
        with patch('app.api.routes.get_config_service') as mock_get_config:
            # Mock configuration service
            mock_config_service = Mock()
            mock_ultravox_config = Mock()
            mock_ultravox_config.api_key = "invalid-key"
            mock_ultravox_config.base_url = "https://api.ultravox.ai"
            mock_twilio_config = Mock()
            mock_twilio_config.auth_token = "test-token"
            mock_twilio_config.account_sid = "test-sid"
            
            mock_config_service.get_ultravox_config.return_value = mock_ultravox_config
            mock_config_service.get_twilio_config.return_value = mock_twilio_config
            mock_get_config.return_value = mock_config_service
            
            # Mock the HTTP client methods directly on the instance
            with patch.object(HTTPClientService, 'make_ultravox_request', new_callable=AsyncMock) as mock_ultravox:
                with patch.object(HTTPClientService, 'make_twilio_request', new_callable=AsyncMock) as mock_twilio:
                    with patch.object(HTTPClientService, 'close', new_callable=AsyncMock) as mock_close:
                        # Set up auth error for Ultravox, success for Twilio
                        mock_ultravox.side_effect = AuthenticationError("Invalid API key")
                        mock_twilio.return_value = {"account_sid": "test-sid"}
                        
                        # Make detailed health check request
                        response = client.get("/api/v1/health/detailed")
                        
                        # Verify response
                        assert response.status_code == 503
                        data = response.json()
                        assert data["status"] == "degraded"
                        assert data["checks"]["ultravox_api"] == "auth_error"
                        assert data["checks"]["twilio_api"] == "ok"
    
    def test_detailed_health_check_twilio_connectivity_error(self, client):
        """Test detailed health check when Twilio has connectivity issues."""
        with patch('app.api.routes.get_config_service') as mock_get_config:
            # Mock configuration service
            mock_config_service = Mock()
            mock_ultravox_config = Mock()
            mock_ultravox_config.api_key = "test-key"
            mock_ultravox_config.base_url = "https://api.ultravox.ai"
            mock_twilio_config = Mock()
            mock_twilio_config.auth_token = "test-token"
            mock_twilio_config.account_sid = "test-sid"
            
            mock_config_service.get_ultravox_config.return_value = mock_ultravox_config
            mock_config_service.get_twilio_config.return_value = mock_twilio_config
            mock_get_config.return_value = mock_config_service
            
            # Mock the HTTP client methods directly on the instance
            with patch.object(HTTPClientService, 'make_ultravox_request', new_callable=AsyncMock) as mock_ultravox:
                with patch.object(HTTPClientService, 'make_twilio_request', new_callable=AsyncMock) as mock_twilio:
                    with patch.object(HTTPClientService, 'close', new_callable=AsyncMock) as mock_close:
                        # Set up success for Ultravox, connectivity error for Twilio
                        mock_ultravox.return_value = {"agents": []}
                        mock_twilio.side_effect = NetworkError("Connection failed")
                        
                        # Make detailed health check request
                        response = client.get("/api/v1/health/detailed")
                        
                        # Verify response
                        assert response.status_code == 503
                        data = response.json()
                        assert data["status"] == "degraded"
                        assert data["checks"]["ultravox_api"] == "ok"
                        assert data["checks"]["twilio_api"] == "connectivity_error"
    
    def test_detailed_health_check_both_services_error(self, client):
        """Test detailed health check when both external services have errors."""
        with patch('app.api.routes.get_config_service') as mock_get_config:
            # Mock configuration service
            mock_config_service = Mock()
            mock_ultravox_config = Mock()
            mock_ultravox_config.api_key = "test-key"
            mock_ultravox_config.base_url = "https://api.ultravox.ai"
            mock_twilio_config = Mock()
            mock_twilio_config.auth_token = "test-token"
            mock_twilio_config.account_sid = "test-sid"
            
            mock_config_service.get_ultravox_config.return_value = mock_ultravox_config
            mock_config_service.get_twilio_config.return_value = mock_twilio_config
            mock_get_config.return_value = mock_config_service
            
            # Mock the HTTP client methods directly on the instance
            with patch.object(HTTPClientService, 'make_ultravox_request', new_callable=AsyncMock) as mock_ultravox:
                with patch.object(HTTPClientService, 'make_twilio_request', new_callable=AsyncMock) as mock_twilio:
                    with patch.object(HTTPClientService, 'close', new_callable=AsyncMock) as mock_close:
                        # Set up errors for both services
                        mock_ultravox.side_effect = TimeoutError("ultravox_request", 30.0)
                        mock_twilio.side_effect = AuthenticationError("Invalid credentials")
                        
                        # Make detailed health check request
                        response = client.get("/api/v1/health/detailed")
                        
                        # Verify response
                        assert response.status_code == 503
                        data = response.json()
                        assert data["status"] == "degraded"
                        assert data["checks"]["ultravox_api"] == "connectivity_error"
                        assert data["checks"]["twilio_api"] == "auth_error"


class TestApplicationIntegration:
    """Integration tests for complete application lifecycle."""
    
    @pytest.mark.asyncio
    async def test_complete_application_lifecycle(self):
        """Test complete application lifecycle from startup to shutdown."""
        # Reset state
        app_state.clear()
        app_state.update({
            "startup_complete": False,
            "shutdown_initiated": False,
            "ongoing_calls": set(),
            "config_validated": False
        })
        
        with patch('app.main.get_config_service') as mock_get_config:
            with patch('app.main.setup_signal_handlers'):
                with patch('app.main.close_http_client_service') as mock_close_http:
                    # Mock configuration service
                    mock_config_service = Mock()
                    mock_config = Mock()
                    mock_config.ultravox.api_key = "test-key"
                    mock_config.twilio.auth_token = "test-token"
                    mock_config.debug = False
                    mock_config.log_level = "INFO"
                    
                    mock_config_service.load_configuration.return_value = mock_config
                    mock_get_config.return_value = mock_config_service
                    mock_close_http.return_value = AsyncMock()
                    
                    # Test startup
                    await startup_sequence()
                    state = get_app_state()
                    assert state["startup_complete"] is True
                    assert state["config_validated"] is True
                    
                    # Test call tracking
                    register_call("test-call-1")
                    register_call("test-call-2")
                    state = get_app_state()
                    assert len(state["ongoing_calls"]) == 2
                    
                    # Complete one call
                    unregister_call("test-call-1")
                    state = get_app_state()
                    assert len(state["ongoing_calls"]) == 1
                    
                    # Test shutdown with ongoing call
                    unregister_call("test-call-2")  # Complete remaining call
                    await shutdown_sequence()
                    
                    # Verify cleanup
                    mock_close_http.assert_called_once()