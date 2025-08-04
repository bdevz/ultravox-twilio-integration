"""
Tests for API routes.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import create_app
from app.models.agent import Agent, AgentConfig, AgentStatus
from app.models.call import CallRequest, CallResult, CallStatus
from app.services.agent_service import AgentServiceError, AgentNotFoundError, AgentCreationError
from app.services.call_service import CallServiceError
from app.api.routes import get_agent_service_dependency, get_call_service_dependency


@pytest.fixture
def app():
    """Create FastAPI app."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_agent_config():
    """Sample agent configuration."""
    return AgentConfig(
        name="Test Agent",
        prompt="You are a helpful assistant",
        voice="default",
        language="en",
        template_variables={"greeting": "Hello"}
    )


@pytest.fixture
def sample_agent():
    """Sample agent."""
    return Agent(
        id="agent_123",
        config=AgentConfig(
            name="Test Agent",
            prompt="You are a helpful assistant",
            voice="default",
            language="en",
            template_variables={"greeting": "Hello"}
        ),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        status=AgentStatus.ACTIVE
    )


@pytest.fixture
def sample_call_request():
    """Sample call request."""
    return CallRequest(
        phone_number="+1234567890",
        template_context={"name": "John"},
        agent_id="agent_123"
    )


@pytest.fixture
def sample_call_result():
    """Sample call result."""
    return CallResult(
        call_sid="CA" + "a" * 32,  # Valid Twilio SID format
        join_url="wss://example.com/join",
        status=CallStatus.INITIATED,
        created_at=datetime.now(timezone.utc),
        agent_id="agent_123",
        phone_number="+1234567890"
    )


class TestAgentEndpoints:
    """Test agent-related endpoints."""
    
    def test_create_agent_success(self, app, client, sample_agent_config, sample_agent):
        """Test successful agent creation."""
        # Mock the service
        mock_service = AsyncMock()
        mock_service.create_agent.return_value = sample_agent
        
        # Override the dependency
        app.dependency_overrides[get_agent_service_dependency] = lambda: mock_service
        
        try:
            # Make request
            response = client.post(
                "/api/v1/agents",
                json=sample_agent_config.model_dump()
            )
            
            # Verify response
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == sample_agent.id
            assert data["config"]["name"] == sample_agent.config.name
            assert data["status"] == sample_agent.status.value
            
            # Verify service was called
            mock_service.create_agent.assert_called_once()
        finally:
            # Clean up
            app.dependency_overrides.clear()
    
    def test_create_agent_failure(self, app, client, sample_agent_config):
        """Test agent creation failure."""
        # Mock the service to raise an error
        mock_service = AsyncMock()
        mock_service.create_agent.side_effect = AgentCreationError(
            "Creation failed",
            details={"error": "test_error"}
        )
        
        # Override the dependency
        app.dependency_overrides[get_agent_service_dependency] = lambda: mock_service
        
        try:
            # Make request
            response = client.post(
                "/api/v1/agents",
                json=sample_agent_config.model_dump()
            )
            
            # Verify response
            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["error"] == "agent_creation_failed"
            assert "Creation failed" in data["detail"]["message"]
        finally:
            # Clean up
            app.dependency_overrides.clear()
    
    def test_list_agents_success(self, app, client, sample_agent):
        """Test successful agent listing."""
        # Mock the service
        mock_service = AsyncMock()
        mock_service.list_agents.return_value = [sample_agent]
        
        # Override the dependency
        app.dependency_overrides[get_agent_service_dependency] = lambda: mock_service
        
        try:
            # Make request
            response = client.get("/api/v1/agents")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == sample_agent.id
            
            # Verify service was called
            mock_service.list_agents.assert_called_once_with(limit=None, offset=None)
        finally:
            # Clean up
            app.dependency_overrides.clear()
    
    def test_list_agents_with_pagination(self, app, client, sample_agent):
        """Test agent listing with pagination."""
        # Mock the service
        mock_service = AsyncMock()
        mock_service.list_agents.return_value = [sample_agent]
        
        # Override the dependency
        app.dependency_overrides[get_agent_service_dependency] = lambda: mock_service
        
        try:
            # Make request with pagination
            response = client.get("/api/v1/agents?limit=10&offset=5")
            
            # Verify response
            assert response.status_code == 200
            
            # Verify service was called with pagination
            mock_service.list_agents.assert_called_once_with(limit=10, offset=5)
        finally:
            # Clean up
            app.dependency_overrides.clear()
    
    def test_get_agent_success(self, app, client, sample_agent):
        """Test successful agent retrieval."""
        # Mock the service
        mock_service = AsyncMock()
        mock_service.get_agent.return_value = sample_agent
        
        # Override the dependency
        app.dependency_overrides[get_agent_service_dependency] = lambda: mock_service
        
        try:
            # Make request
            response = client.get(f"/api/v1/agents/{sample_agent.id}")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == sample_agent.id
            
            # Verify service was called
            mock_service.get_agent.assert_called_once_with(sample_agent.id)
        finally:
            # Clean up
            app.dependency_overrides.clear()
    
    def test_get_agent_not_found(self, app, client):
        """Test agent not found."""
        # Mock the service to raise not found error
        mock_service = AsyncMock()
        mock_service.get_agent.side_effect = AgentNotFoundError(
            "Agent not found",
            details={"agent_id": "nonexistent"}
        )
        
        # Override the dependency
        app.dependency_overrides[get_agent_service_dependency] = lambda: mock_service
        
        try:
            # Make request
            response = client.get("/api/v1/agents/nonexistent")
            
            # Verify response
            assert response.status_code == 404
            data = response.json()
            assert data["detail"]["error"] == "agent_not_found"
        finally:
            # Clean up
            app.dependency_overrides.clear()
    
    def test_update_agent_success(self, app, client, sample_agent, sample_agent_config):
        """Test successful agent update."""
        # Mock the service
        mock_service = AsyncMock()
        mock_service.update_agent.return_value = sample_agent
        
        # Override the dependency
        app.dependency_overrides[get_agent_service_dependency] = lambda: mock_service
        
        try:
            # Make request
            response = client.put(
                f"/api/v1/agents/{sample_agent.id}",
                json=sample_agent_config.model_dump()
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == sample_agent.id
            
            # Verify service was called
            mock_service.update_agent.assert_called_once()
        finally:
            # Clean up
            app.dependency_overrides.clear()


class TestCallEndpoints:
    """Test call-related endpoints."""
    
    def test_initiate_call_success(self, app, client, sample_call_request, sample_call_result):
        """Test successful call initiation."""
        # Mock the service
        mock_service = AsyncMock()
        mock_service.initiate_call.return_value = sample_call_result
        
        # Override the dependency
        app.dependency_overrides[get_call_service_dependency] = lambda: mock_service
        
        try:
            # Make request
            response = client.post(
                f"/api/v1/calls/{sample_call_request.agent_id}",
                json=sample_call_request.model_dump()
            )
            
            # Verify response
            assert response.status_code == 201
            data = response.json()
            assert data["call_sid"] == sample_call_result.call_sid
            assert data["agent_id"] == sample_call_result.agent_id
            
            # Verify service was called
            mock_service.initiate_call.assert_called_once()
        finally:
            # Clean up
            app.dependency_overrides.clear()
    
    def test_initiate_call_agent_id_mismatch(self, app, client, sample_call_request):
        """Test call initiation with agent ID mismatch."""
        # Mock the service
        mock_service = AsyncMock()
        
        # Override the dependency
        app.dependency_overrides[get_call_service_dependency] = lambda: mock_service
        
        try:
            # Make request with mismatched agent ID
            response = client.post(
                "/api/v1/calls/different_agent_id",
                json=sample_call_request.model_dump()
            )
            
            # Verify response
            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["error"] == "agent_id_mismatch"
            
            # Verify service was not called
            mock_service.initiate_call.assert_not_called()
        finally:
            # Clean up
            app.dependency_overrides.clear()
    
    def test_initiate_call_failure(self, app, client, sample_call_request):
        """Test call initiation failure."""
        # Mock the service to raise an error
        mock_service = AsyncMock()
        mock_service.initiate_call.side_effect = CallServiceError(
            "Call failed",
            details={"error": "test_error"}
        )
        
        # Override the dependency
        app.dependency_overrides[get_call_service_dependency] = lambda: mock_service
        
        try:
            # Make request
            response = client.post(
                f"/api/v1/calls/{sample_call_request.agent_id}",
                json=sample_call_request.model_dump()
            )
            
            # Verify response
            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["error"] == "call_initiation_failed"
        finally:
            # Clean up
            app.dependency_overrides.clear()


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    @patch('app.api.routes.get_config_service')
    def test_health_check_healthy(self, mock_get_config, client):
        """Test healthy status."""
        # Mock config service
        mock_config_service = MagicMock()
        mock_ultravox_config = MagicMock()
        mock_ultravox_config.api_key = "test_key"
        mock_twilio_config = MagicMock()
        mock_twilio_config.auth_token = "test_token"
        
        mock_config_service.get_ultravox_config.return_value = mock_ultravox_config
        mock_config_service.get_twilio_config.return_value = mock_twilio_config
        mock_get_config.return_value = mock_config_service
        
        # Make request
        response = client.get("/api/v1/health")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ultravox-twilio-integration"
        assert data["checks"]["configuration"] == "ok"
    
    @patch('app.api.routes.get_config_service')
    def test_health_check_degraded(self, mock_get_config, client):
        """Test degraded status."""
        # Mock config service with missing API key
        mock_config_service = MagicMock()
        mock_ultravox_config = MagicMock()
        mock_ultravox_config.api_key = None
        mock_twilio_config = MagicMock()
        mock_twilio_config.auth_token = "test_token"
        
        mock_config_service.get_ultravox_config.return_value = mock_ultravox_config
        mock_config_service.get_twilio_config.return_value = mock_twilio_config
        mock_get_config.return_value = mock_config_service
        
        # Make request
        response = client.get("/api/v1/health")
        
        # Verify response
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["checks"]["ultravox_config"] == "missing_api_key"
    
    @patch('app.api.routes.get_config_service')
    def test_health_check_unhealthy(self, mock_get_config, client):
        """Test unhealthy status."""
        # Mock config service to raise an error
        mock_get_config.side_effect = Exception("Config error")
        
        # Make request
        response = client.get("/api/v1/health")
        
        # Verify response
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["error"] == "health_check_failed"