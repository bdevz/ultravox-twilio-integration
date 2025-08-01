"""
Integration tests for Ultravox API interactions.

These tests require actual Ultravox API credentials and test real API calls.
Set TEST_ULTRAVOX_API_KEY environment variable to run these tests.
"""

import pytest
from datetime import datetime, timezone
from app.models.agent import AgentConfig, AgentStatus
from app.services.agent_service import AgentService
from app.services.call_service import CallService
from app.exceptions import ResourceNotFoundError, UltravoxAPIError


@pytest.mark.ultravox
@pytest.mark.slow
class TestUltravoxAgentIntegration:
    """Integration tests for Ultravox agent operations."""
    
    @pytest.mark.asyncio
    async def test_create_agent_real_api(self, agent_service: AgentService, test_agent_config: AgentConfig, cleanup_agents):
        """Test creating an agent with real Ultravox API."""
        # Create agent
        agent = await agent_service.create_agent(test_agent_config)
        cleanup_agents(agent.id)
        
        # Verify agent creation
        assert agent.id is not None
        assert len(agent.id) > 0
        assert agent.config.name == test_agent_config.name
        assert agent.config.prompt == test_agent_config.prompt
        assert agent.config.voice == test_agent_config.voice
        assert agent.config.language == test_agent_config.language
        assert agent.config.template_variables == test_agent_config.template_variables
        assert agent.status == AgentStatus.ACTIVE
        assert isinstance(agent.created_at, datetime)
        assert isinstance(agent.updated_at, datetime)
    
    @pytest.mark.asyncio
    async def test_get_agent_real_api(self, agent_service: AgentService, test_agent_config: AgentConfig, cleanup_agents):
        """Test retrieving an agent with real Ultravox API."""
        # First create an agent
        created_agent = await agent_service.create_agent(test_agent_config)
        cleanup_agents(created_agent.id)
        
        # Retrieve the agent
        retrieved_agent = await agent_service.get_agent(created_agent.id)
        
        # Verify retrieved agent matches created agent
        assert retrieved_agent.id == created_agent.id
        assert retrieved_agent.config.name == created_agent.config.name
        assert retrieved_agent.config.prompt == created_agent.config.prompt
        assert retrieved_agent.config.voice == created_agent.config.voice
        assert retrieved_agent.config.language == created_agent.config.language
        assert retrieved_agent.status == AgentStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_agent_real_api(self, agent_service: AgentService):
        """Test retrieving a nonexistent agent with real Ultravox API."""
        nonexistent_id = "nonexistent_agent_12345"
        
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await agent_service.get_agent(nonexistent_id)
        
        assert "agent" in str(exc_info.value).lower()
        assert nonexistent_id in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_agents_real_api(self, agent_service: AgentService, test_agent_config: AgentConfig, cleanup_agents):
        """Test listing agents with real Ultravox API."""
        # Create a test agent to ensure we have at least one
        created_agent = await agent_service.create_agent(test_agent_config)
        cleanup_agents(created_agent.id)
        
        # List agents
        agents = await agent_service.list_agents()
        
        # Verify we get a list and our agent is included
        assert isinstance(agents, list)
        assert len(agents) >= 1
        
        # Find our created agent in the list
        found_agent = None
        for agent in agents:
            if agent.id == created_agent.id:
                found_agent = agent
                break
        
        assert found_agent is not None
        assert found_agent.config.name == test_agent_config.name
    
    @pytest.mark.asyncio
    async def test_list_agents_with_pagination_real_api(self, agent_service: AgentService):
        """Test listing agents with pagination parameters."""
        # Test with small limit
        agents_limited = await agent_service.list_agents(limit=2)
        
        # Verify we get at most 2 agents
        assert isinstance(agents_limited, list)
        assert len(agents_limited) <= 2
        
        # Test with offset
        agents_offset = await agent_service.list_agents(limit=1, offset=1)
        
        # Verify we get at most 1 agent
        assert isinstance(agents_offset, list)
        assert len(agents_offset) <= 1
    
    @pytest.mark.asyncio
    async def test_update_agent_real_api(self, agent_service: AgentService, test_agent_config: AgentConfig, cleanup_agents):
        """Test updating an agent with real Ultravox API."""
        # Create an agent
        created_agent = await agent_service.create_agent(test_agent_config)
        cleanup_agents(created_agent.id)
        
        # Update the agent configuration
        updated_config = AgentConfig(
            name="Updated Integration Test Agent",
            prompt="You are an updated test assistant. Respond with 'Updated!' to confirm.",
            voice="default",
            language="en",
            template_variables={"updated": "true", "version": "2.0"}
        )
        
        # Update the agent
        updated_agent = await agent_service.update_agent(created_agent.id, updated_config)
        
        # Verify the update
        assert updated_agent.id == created_agent.id
        assert updated_agent.config.name == "Updated Integration Test Agent"
        assert updated_agent.config.prompt == updated_config.prompt
        assert updated_agent.config.template_variables == updated_config.template_variables
        assert updated_agent.updated_at >= created_agent.updated_at
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_agent_real_api(self, agent_service: AgentService, test_agent_config: AgentConfig):
        """Test updating a nonexistent agent with real Ultravox API."""
        nonexistent_id = "nonexistent_agent_12345"
        
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await agent_service.update_agent(nonexistent_id, test_agent_config)
        
        assert "agent" in str(exc_info.value).lower()
        assert nonexistent_id in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_delete_agent_real_api(self, agent_service: AgentService, test_agent_config: AgentConfig):
        """Test deleting an agent with real Ultravox API."""
        # Create an agent
        created_agent = await agent_service.create_agent(test_agent_config)
        
        # Delete the agent
        result = await agent_service.delete_agent(created_agent.id)
        
        # Verify deletion was successful
        assert result is True
        
        # Verify agent is no longer accessible
        with pytest.raises(ResourceNotFoundError):
            await agent_service.get_agent(created_agent.id)
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_agent_real_api(self, agent_service: AgentService):
        """Test deleting a nonexistent agent with real Ultravox API."""
        nonexistent_id = "nonexistent_agent_12345"
        
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await agent_service.delete_agent(nonexistent_id)
        
        assert "agent" in str(exc_info.value).lower()
        assert nonexistent_id in str(exc_info.value)


@pytest.mark.ultravox
@pytest.mark.slow
class TestUltravoxCallIntegration:
    """Integration tests for Ultravox call operations."""
    
    @pytest.mark.asyncio
    async def test_get_join_url_real_api(self, call_service: CallService, agent_service: AgentService, 
                                       test_agent_config: AgentConfig, cleanup_agents):
        """Test getting join URL from real Ultravox API."""
        # Create an agent first
        agent = await agent_service.create_agent(test_agent_config)
        cleanup_agents(agent.id)
        
        # Get join URL
        context = {
            "user_name": "Integration Test User",
            "test_scenario": "join_url_test"
        }
        
        join_url = await call_service.get_join_url(agent.id, context)
        
        # Verify join URL format
        assert isinstance(join_url, str)
        assert len(join_url) > 0
        assert join_url.startswith("wss://") or join_url.startswith("ws://")
        assert "ultravox" in join_url.lower() or "stream" in join_url.lower()
    
    @pytest.mark.asyncio
    async def test_get_join_url_with_empty_context_real_api(self, call_service: CallService, 
                                                          agent_service: AgentService, 
                                                          test_agent_config: AgentConfig, cleanup_agents):
        """Test getting join URL with empty context from real Ultravox API."""
        # Create an agent first
        agent = await agent_service.create_agent(test_agent_config)
        cleanup_agents(agent.id)
        
        # Get join URL with empty context
        join_url = await call_service.get_join_url(agent.id, {})
        
        # Verify join URL is still valid
        assert isinstance(join_url, str)
        assert len(join_url) > 0
        assert join_url.startswith("wss://") or join_url.startswith("ws://")
    
    @pytest.mark.asyncio
    async def test_get_join_url_nonexistent_agent_real_api(self, call_service: CallService):
        """Test getting join URL for nonexistent agent with real Ultravox API."""
        nonexistent_id = "nonexistent_agent_12345"
        
        with pytest.raises(Exception) as exc_info:
            await call_service.get_join_url(nonexistent_id, {})
        
        # Should raise some kind of error (exact type depends on API response)
        assert "agent" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_get_join_url_with_complex_context_real_api(self, call_service: CallService, 
                                                            agent_service: AgentService, 
                                                            test_agent_config: AgentConfig, cleanup_agents):
        """Test getting join URL with complex template context from real Ultravox API."""
        # Create an agent first
        agent = await agent_service.create_agent(test_agent_config)
        cleanup_agents(agent.id)
        
        # Get join URL with complex context
        complex_context = {
            "user_name": "John Doe",
            "user_id": "user_12345",
            "session_id": "session_abcdef",
            "preferences": {
                "language": "en",
                "voice_speed": "normal"
            },
            "metadata": {
                "source": "integration_test",
                "timestamp": "2024-01-01T00:00:00Z",
                "version": "1.0"
            }
        }
        
        join_url = await call_service.get_join_url(agent.id, complex_context)
        
        # Verify join URL is valid
        assert isinstance(join_url, str)
        assert len(join_url) > 0
        assert join_url.startswith("wss://") or join_url.startswith("ws://")


@pytest.mark.ultravox
class TestUltravoxErrorHandling:
    """Integration tests for Ultravox API error handling."""
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_handling(self, integration_config_service, http_client):
        """Test handling of invalid API key."""
        from app.models.config import UltravoxConfig
        
        # Create config with invalid API key
        invalid_config = UltravoxConfig(
            api_key="invalid_key_12345",
            base_url=integration_config_service.get_ultravox_config().base_url
        )
        
        # Override config service to return invalid config
        integration_config_service.get_ultravox_config = lambda: invalid_config
        
        agent_service = AgentService(http_client, integration_config_service)
        
        # Try to create agent with invalid key
        test_config = AgentConfig(
            name="Test Agent",
            prompt="Test prompt",
            voice="default",
            language="en"
        )
        
        with pytest.raises(UltravoxAPIError) as exc_info:
            await agent_service.create_agent(test_config)
        
        # Verify error contains authentication-related information
        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in ["auth", "unauthorized", "invalid", "key"])
    
    @pytest.mark.asyncio
    async def test_invalid_base_url_handling(self, integration_config_service, http_client):
        """Test handling of invalid base URL."""
        from app.models.config import UltravoxConfig
        
        # Create config with invalid base URL
        invalid_config = UltravoxConfig(
            api_key=integration_config_service.get_ultravox_config().api_key,
            base_url="https://invalid-ultravox-api.example.com"
        )
        
        # Override config service to return invalid config
        integration_config_service.get_ultravox_config = lambda: invalid_config
        
        agent_service = AgentService(http_client, integration_config_service)
        
        # Try to create agent with invalid URL
        test_config = AgentConfig(
            name="Test Agent",
            prompt="Test prompt",
            voice="default",
            language="en"
        )
        
        with pytest.raises(Exception) as exc_info:
            await agent_service.create_agent(test_config)
        
        # Verify error is related to connection/network
        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in ["connection", "network", "resolve", "timeout"])