"""
Unit tests for AgentService with mocked Ultravox API responses.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone
from app.services.agent_service import (
    AgentService,
    AgentServiceError,
    AgentNotFoundError,
    AgentCreationError,
    AgentUpdateError
)
from app.models.agent import Agent, AgentConfig, AgentStatus
from app.services.http_client_service import HTTPClientError, HTTPClientResponseError
from app.services.config_service import UltravoxConfig


@pytest.fixture
def mock_http_client():
    """Mock HTTP client service."""
    return AsyncMock()


@pytest.fixture
def mock_config_service():
    """Mock configuration service."""
    config_service = Mock()
    config_service.get_ultravox_config.return_value = UltravoxConfig(
        api_key="test-api-key",
        base_url="https://api.ultravox.ai"
    )
    return config_service


@pytest.fixture
def agent_service(mock_http_client, mock_config_service):
    """Agent service instance with mocked dependencies."""
    return AgentService(mock_http_client, mock_config_service)


@pytest.fixture
def sample_agent_config():
    """Sample agent configuration for testing."""
    return AgentConfig(
        name="Test Agent",
        prompt="You are a helpful assistant",
        voice="default",
        language="en",
        template_variables={"greeting": "Hello"}
    )


@pytest.fixture
def sample_ultravox_response():
    """Sample Ultravox API response."""
    return {
        "agentId": "agent-123",
        "name": "Test Agent",
        "systemPrompt": "You are a helpful assistant",
        "voice": "default",
        "language": "en",
        "templateVariables": {"greeting": "Hello"},
        "status": "active",
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z"
    }


class TestAgentService:
    """Test cases for AgentService."""
    
    @pytest.mark.asyncio
    async def test_create_agent_success(self, agent_service, mock_http_client, sample_agent_config, sample_ultravox_response):
        """Test successful agent creation."""
        # Setup mock response
        mock_http_client.make_ultravox_request.return_value = sample_ultravox_response
        
        # Call create_agent
        result = await agent_service.create_agent(sample_agent_config)
        
        # Verify API call
        mock_http_client.make_ultravox_request.assert_called_once_with(
            method="POST",
            endpoint="/api/agents",
            data={
                "name": "Test Agent",
                "systemPrompt": "You are a helpful assistant",
                "voice": "default",
                "language": "en",
                "templateVariables": {"greeting": "Hello"}
            },
            api_key="test-api-key",
            base_url="https://api.ultravox.ai"
        )
        
        # Verify result
        assert isinstance(result, Agent)
        assert result.id == "agent-123"
        assert result.config.name == "Test Agent"
        assert result.config.prompt == "You are a helpful assistant"
        assert result.status == AgentStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_create_agent_missing_id(self, agent_service, mock_http_client, sample_agent_config):
        """Test agent creation with missing agent ID in response."""
        # Setup mock response without agent ID
        mock_http_client.make_ultravox_request.return_value = {"name": "Test Agent"}
        
        # Call create_agent and expect error
        with pytest.raises(AgentCreationError) as exc_info:
            await agent_service.create_agent(sample_agent_config)
        
        assert "No agent ID in response" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_create_agent_http_error(self, agent_service, mock_http_client, sample_agent_config):
        """Test agent creation with HTTP error."""
        # Setup mock to raise HTTP error
        mock_http_client.make_ultravox_request.side_effect = HTTPClientError(
            "API error", status_code=400, details={"error": "Bad request"}
        )
        
        # Call create_agent and expect error
        with pytest.raises(AgentCreationError) as exc_info:
            await agent_service.create_agent(sample_agent_config)
        
        assert "Failed to create agent" in str(exc_info.value)
        assert exc_info.value.details["http_error"]["error"] == "Bad request"
    
    @pytest.mark.asyncio
    async def test_get_agent_success(self, agent_service, mock_http_client, sample_ultravox_response):
        """Test successful agent retrieval."""
        # Setup mock response
        mock_http_client.make_ultravox_request.return_value = sample_ultravox_response
        
        # Call get_agent
        result = await agent_service.get_agent("agent-123")
        
        # Verify API call
        mock_http_client.make_ultravox_request.assert_called_once_with(
            method="GET",
            endpoint="/api/agents/agent-123",
            api_key="test-api-key",
            base_url="https://api.ultravox.ai"
        )
        
        # Verify result
        assert isinstance(result, Agent)
        assert result.id == "agent-123"
        assert result.config.name == "Test Agent"
    
    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, agent_service, mock_http_client):
        """Test agent retrieval when agent is not found."""
        # Setup mock to raise 404 error
        mock_http_client.make_ultravox_request.side_effect = HTTPClientResponseError(
            "Not found", status_code=404
        )
        
        # Call get_agent and expect error
        with pytest.raises(AgentNotFoundError) as exc_info:
            await agent_service.get_agent("nonexistent-agent")
        
        assert "Agent nonexistent-agent not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_agents_success(self, agent_service, mock_http_client, sample_ultravox_response):
        """Test successful agent listing."""
        # Setup mock response
        mock_http_client.make_request.return_value = {
            "results": [sample_ultravox_response, {
                "agentId": "agent-456",
                "name": "Another Agent",
                "systemPrompt": "Another prompt",
                "voice": "default",
                "language": "en",
                "templateVariables": {},
                "status": "active",
                "createdAt": "2024-01-02T00:00:00Z",
                "updatedAt": "2024-01-02T00:00:00Z"
            }]
        }
        
        # Call list_agents
        result = await agent_service.list_agents()
        
        # Verify API call
        mock_http_client.make_request.assert_called_once_with(
            method="GET",
            url="https://api.ultravox.ai/api/agents",
            params={},
            auth_token="test-api-key"
        )
        
        # Verify result
        assert len(result) == 2
        assert all(isinstance(agent, Agent) for agent in result)
        assert result[0].id == "agent-123"
        assert result[1].id == "agent-456"
    
    @pytest.mark.asyncio
    async def test_list_agents_with_pagination(self, agent_service, mock_http_client):
        """Test agent listing with pagination parameters."""
        # Setup mock response
        mock_http_client.make_request.return_value = {"results": []}
        
        # Call list_agents with pagination
        await agent_service.list_agents(limit=10, offset=20)
        
        # Verify API call with pagination params
        mock_http_client.make_request.assert_called_once_with(
            method="GET",
            url="https://api.ultravox.ai/api/agents",
            params={"limit": "10", "offset": "20"},
            auth_token="test-api-key"
        )
    
    @pytest.mark.asyncio
    async def test_update_agent_success(self, agent_service, mock_http_client, sample_agent_config, sample_ultravox_response):
        """Test successful agent update."""
        # Setup mock response
        updated_response = sample_ultravox_response.copy()
        updated_response["name"] = "Updated Agent"
        mock_http_client.make_ultravox_request.return_value = updated_response
        
        # Update config
        updated_config = sample_agent_config.model_copy()
        updated_config.name = "Updated Agent"
        
        # Call update_agent
        result = await agent_service.update_agent("agent-123", updated_config)
        
        # Verify API call
        mock_http_client.make_ultravox_request.assert_called_once_with(
            method="PUT",
            endpoint="/api/agents/agent-123",
            data={
                "name": "Updated Agent",
                "systemPrompt": "You are a helpful assistant",
                "voice": "default",
                "language": "en",
                "templateVariables": {"greeting": "Hello"}
            },
            api_key="test-api-key",
            base_url="https://api.ultravox.ai"
        )
        
        # Verify result
        assert isinstance(result, Agent)
        assert result.id == "agent-123"
        assert result.config.name == "Updated Agent"
    
    @pytest.mark.asyncio
    async def test_update_agent_not_found(self, agent_service, mock_http_client, sample_agent_config):
        """Test agent update when agent is not found."""
        # Setup mock to raise 404 error
        mock_http_client.make_ultravox_request.side_effect = HTTPClientResponseError(
            "Not found", status_code=404
        )
        
        # Call update_agent and expect error
        with pytest.raises(AgentNotFoundError) as exc_info:
            await agent_service.update_agent("nonexistent-agent", sample_agent_config)
        
        assert "Agent nonexistent-agent not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_delete_agent_success(self, agent_service, mock_http_client):
        """Test successful agent deletion."""
        # Setup mock response
        mock_http_client.make_ultravox_request.return_value = {}
        
        # Call delete_agent
        result = await agent_service.delete_agent("agent-123")
        
        # Verify API call
        mock_http_client.make_ultravox_request.assert_called_once_with(
            method="DELETE",
            endpoint="/api/agents/agent-123",
            api_key="test-api-key",
            base_url="https://api.ultravox.ai"
        )
        
        # Verify result
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_agent_not_found(self, agent_service, mock_http_client):
        """Test agent deletion when agent is not found."""
        # Setup mock to raise 404 error
        mock_http_client.make_ultravox_request.side_effect = HTTPClientResponseError(
            "Not found", status_code=404
        )
        
        # Call delete_agent and expect error
        with pytest.raises(AgentNotFoundError) as exc_info:
            await agent_service.delete_agent("nonexistent-agent")
        
        assert "Agent nonexistent-agent not found" in str(exc_info.value)
    
    def test_parse_agent_response_success(self, agent_service, sample_ultravox_response):
        """Test successful agent response parsing."""
        result = agent_service._parse_agent_response(sample_ultravox_response)
        
        assert isinstance(result, Agent)
        assert result.id == "agent-123"
        assert result.config.name == "Test Agent"
        assert result.config.prompt == "You are a helpful assistant"
        assert result.status == AgentStatus.ACTIVE
    
    def test_parse_agent_response_missing_id(self, agent_service):
        """Test agent response parsing with missing ID."""
        response_data = {"name": "Test Agent"}
        
        with pytest.raises(AgentServiceError) as exc_info:
            agent_service._parse_agent_response(response_data)
        
        assert "Missing agent ID in response" in str(exc_info.value)
    
    def test_parse_agent_response_with_external_id(self, agent_service):
        """Test agent response parsing with externally provided ID."""
        response_data = {
            "name": "Test Agent",
            "systemPrompt": "Test prompt",
            "voice": "default",
            "language": "en",
            "templateVariables": {},
            "status": "active",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z"
        }
        
        result = agent_service._parse_agent_response(response_data, "external-123")
        
        assert result.id == "external-123"
        assert result.config.name == "Test Agent"
    
    def test_parse_timestamp_valid(self, agent_service):
        """Test timestamp parsing with valid ISO format."""
        timestamp_str = "2024-01-01T12:00:00Z"
        result = agent_service._parse_timestamp(timestamp_str)
        
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
    
    def test_parse_timestamp_invalid(self, agent_service):
        """Test timestamp parsing with invalid format."""
        timestamp_str = "invalid-timestamp"
        result = agent_service._parse_timestamp(timestamp_str)
        
        # Should return current time for invalid timestamps
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
    
    def test_parse_timestamp_none(self, agent_service):
        """Test timestamp parsing with None value."""
        result = agent_service._parse_timestamp(None)
        
        # Should return current time for None
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc


class TestAgentServiceIntegration:
    """Integration-style tests for AgentService."""
    
    @pytest.mark.asyncio
    async def test_create_and_retrieve_agent_flow(self, agent_service, mock_http_client, sample_agent_config, sample_ultravox_response):
        """Test the flow of creating and then retrieving an agent."""
        # Setup mocks for create and get operations
        mock_http_client.make_ultravox_request.side_effect = [
            sample_ultravox_response,  # create response
            sample_ultravox_response   # get response
        ]
        
        # Create agent
        created_agent = await agent_service.create_agent(sample_agent_config)
        assert created_agent.id == "agent-123"
        
        # Retrieve agent
        retrieved_agent = await agent_service.get_agent("agent-123")
        assert retrieved_agent.id == "agent-123"
        assert retrieved_agent.config.name == created_agent.config.name
        
        # Verify both API calls were made
        assert mock_http_client.make_ultravox_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_error_handling_chain(self, agent_service, mock_http_client, sample_agent_config):
        """Test error handling across multiple operations."""
        # Setup different errors for different operations
        mock_http_client.make_ultravox_request.side_effect = [
            HTTPClientError("Network error"),  # create fails
            HTTPClientResponseError("Not found", status_code=404),  # get fails with 404
            HTTPClientResponseError("Server error", status_code=500)  # update fails with 500
        ]
        
        # Test create error
        with pytest.raises(AgentCreationError):
            await agent_service.create_agent(sample_agent_config)
        
        # Test get error (404 -> AgentNotFoundError)
        with pytest.raises(AgentNotFoundError):
            await agent_service.get_agent("agent-123")
        
        # Test update error (500 -> AgentUpdateError)
        with pytest.raises(AgentUpdateError):
            await agent_service.update_agent("agent-123", sample_agent_config)


@pytest.mark.asyncio
async def test_get_agent_service_dependency():
    """Test the dependency injection helper function."""
    from app.services.agent_service import get_agent_service
    
    mock_http_client = AsyncMock()
    mock_config_service = Mock()
    
    service = await get_agent_service(mock_http_client, mock_config_service)
    
    assert isinstance(service, AgentService)
    assert service.http_client == mock_http_client
    assert service.config_service == mock_config_service