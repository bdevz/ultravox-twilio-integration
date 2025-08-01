"""
End-to-end integration tests for complete call flow.

These tests require both Ultravox and Twilio API credentials and test the complete
flow from agent creation to call initiation.

Set TEST_ULTRAVOX_API_KEY, TEST_TWILIO_ACCOUNT_SID, TEST_TWILIO_AUTH_TOKEN, 
and TEST_TWILIO_PHONE_NUMBER environment variables to run these tests.

WARNING: These tests create actual agents and calls, which may incur charges.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from app.services.agent_service import AgentService
from app.services.call_service import CallService
from app.models.agent import AgentConfig
from app.models.call import CallRequest, CallStatus


@pytest.mark.e2e
@pytest.mark.ultravox
@pytest.mark.twilio
@pytest.mark.slow
class TestEndToEndCallFlow:
    """End-to-end integration tests for complete call flow."""
    
    @pytest.mark.asyncio
    async def test_complete_call_flow(self, agent_service: AgentService, call_service: CallService, 
                                    integration_config, cleanup_agents):
        """
        Test complete flow: create agent -> get join URL -> create Twilio call.
        
        This is the primary end-to-end test that validates the entire system works together.
        """
        # Step 1: Create an agent
        agent_config = AgentConfig(
            name="E2E Test Agent",
            prompt="You are a helpful assistant for end-to-end testing. Greet the user with their name from the template variables.",
            voice="default",
            language="en",
            template_variables={
                "greeting": "Hello from E2E test",
                "test_type": "integration"
            }
        )
        
        agent = await agent_service.create_agent(agent_config)
        cleanup_agents(agent.id)
        
        # Verify agent creation
        assert agent.id is not None
        assert agent.config.name == "E2E Test Agent"
        
        # Step 2: Create call request
        call_request = CallRequest(
            phone_number=integration_config["test_phone_number"],
            template_context={
                "user_name": "E2E Test User",
                "session_id": "e2e_test_session_123",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            agent_id=agent.id
        )
        
        # Step 3: Initiate the complete call flow
        call_result = await call_service.initiate_call(call_request)
        
        # Verify call result
        assert call_result.call_sid is not None
        assert call_result.call_sid.startswith("CA")  # Twilio call SID format
        assert call_result.join_url is not None
        assert call_result.join_url.startswith("wss://") or call_result.join_url.startswith("ws://")
        assert call_result.status == CallStatus.INITIATED
        assert call_result.agent_id == agent.id
        assert call_result.phone_number == integration_config["test_phone_number"]
        assert isinstance(call_result.created_at, datetime)
        
        # Step 4: Verify we can still retrieve the agent after call creation
        retrieved_agent = await agent_service.get_agent(agent.id)
        assert retrieved_agent.id == agent.id
        assert retrieved_agent.config.name == agent.config.name
    
    @pytest.mark.asyncio
    async def test_multiple_calls_same_agent(self, agent_service: AgentService, call_service: CallService,
                                           integration_config, cleanup_agents):
        """Test creating multiple calls with the same agent."""
        # Create an agent
        agent_config = AgentConfig(
            name="Multi-Call Test Agent",
            prompt="You are a test assistant that can handle multiple concurrent calls.",
            voice="default",
            language="en",
            template_variables={"agent_type": "multi_call"}
        )
        
        agent = await agent_service.create_agent(agent_config)
        cleanup_agents(agent.id)
        
        # Create multiple call requests
        call_requests = [
            CallRequest(
                phone_number=integration_config["test_phone_number"],
                template_context={
                    "user_name": f"User {i}",
                    "call_number": str(i),
                    "session_id": f"multi_call_session_{i}"
                },
                agent_id=agent.id
            )
            for i in range(3)
        ]
        
        # Initiate calls concurrently
        call_tasks = [call_service.initiate_call(req) for req in call_requests]
        call_results = await asyncio.gather(*call_tasks, return_exceptions=True)
        
        # Verify all calls were successful
        successful_calls = [r for r in call_results if not isinstance(r, Exception)]
        assert len(successful_calls) >= 1  # At least one should succeed
        
        # Verify each call has unique SID but same agent
        for call_result in successful_calls:
            assert call_result.call_sid.startswith("CA")
            assert call_result.agent_id == agent.id
            assert call_result.status == CallStatus.INITIATED
        
        # Verify all call SIDs are unique
        sids = [call.call_sid for call in successful_calls]
        assert len(set(sids)) == len(sids)
    
    @pytest.mark.asyncio
    async def test_call_with_complex_template_context(self, agent_service: AgentService, call_service: CallService,
                                                    integration_config, cleanup_agents):
        """Test call flow with complex template context variables."""
        # Create agent with template variables
        agent_config = AgentConfig(
            name="Complex Context Agent",
            prompt="You are a customer service agent. Use the customer information provided in template variables to personalize the conversation.",
            voice="default",
            language="en",
            template_variables={
                "company_name": "Test Company",
                "support_level": "premium"
            }
        )
        
        agent = await agent_service.create_agent(agent_config)
        cleanup_agents(agent.id)
        
        # Create call with complex context
        complex_context = {
            "customer": {
                "name": "John Doe",
                "id": "CUST_12345",
                "tier": "gold",
                "account_balance": 1500.50
            },
            "issue": {
                "type": "billing",
                "priority": "high",
                "description": "Incorrect charge on account"
            },
            "session": {
                "id": "SESSION_ABC123",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "channel": "phone",
                "agent_id": "AGENT_789"
            },
            "metadata": {
                "source": "e2e_integration_test",
                "version": "1.0",
                "test_run": True
            }
        }
        
        call_request = CallRequest(
            phone_number=integration_config["test_phone_number"],
            template_context=complex_context,
            agent_id=agent.id
        )
        
        # Initiate call
        call_result = await call_service.initiate_call(call_request)
        
        # Verify call was created successfully with complex context
        assert call_result.call_sid.startswith("CA")
        assert call_result.join_url.startswith("wss://") or call_result.join_url.startswith("ws://")
        assert call_result.status == CallStatus.INITIATED
        assert call_result.agent_id == agent.id
    
    @pytest.mark.asyncio
    async def test_call_flow_error_recovery(self, agent_service: AgentService, call_service: CallService,
                                          integration_config, cleanup_agents):
        """Test error recovery in call flow - create agent, fail call, retry successfully."""
        # Create agent
        agent_config = AgentConfig(
            name="Error Recovery Test Agent",
            prompt="You are a test agent for error recovery scenarios.",
            voice="default",
            language="en"
        )
        
        agent = await agent_service.create_agent(agent_config)
        cleanup_agents(agent.id)
        
        # First, try call with invalid phone number (should fail)
        invalid_call_request = CallRequest(
            phone_number="invalid_phone",
            template_context={"test": "error_recovery"},
            agent_id=agent.id
        )
        
        with pytest.raises(Exception):  # Should fail due to invalid phone number
            await call_service.initiate_call(invalid_call_request)
        
        # Then, try call with valid phone number (should succeed)
        valid_call_request = CallRequest(
            phone_number=integration_config["test_phone_number"],
            template_context={"test": "error_recovery_success"},
            agent_id=agent.id
        )
        
        call_result = await call_service.initiate_call(valid_call_request)
        
        # Verify successful call after error
        assert call_result.call_sid.startswith("CA")
        assert call_result.status == CallStatus.INITIATED
        assert call_result.agent_id == agent.id
    
    @pytest.mark.asyncio
    async def test_agent_update_then_call(self, agent_service: AgentService, call_service: CallService,
                                        integration_config, cleanup_agents):
        """Test updating an agent and then making a call with the updated agent."""
        # Create initial agent
        initial_config = AgentConfig(
            name="Initial Agent",
            prompt="You are the initial version of this agent.",
            voice="default",
            language="en",
            template_variables={"version": "1.0"}
        )
        
        agent = await agent_service.create_agent(initial_config)
        cleanup_agents(agent.id)
        
        # Update the agent
        updated_config = AgentConfig(
            name="Updated Agent",
            prompt="You are the updated version of this agent with new capabilities.",
            voice="default",
            language="en",
            template_variables={"version": "2.0", "updated": "true"}
        )
        
        updated_agent = await agent_service.update_agent(agent.id, updated_config)
        
        # Verify update
        assert updated_agent.config.name == "Updated Agent"
        assert updated_agent.config.template_variables["version"] == "2.0"
        
        # Make call with updated agent
        call_request = CallRequest(
            phone_number=integration_config["test_phone_number"],
            template_context={
                "user_name": "Test User",
                "test_scenario": "agent_update_then_call"
            },
            agent_id=agent.id
        )
        
        call_result = await call_service.initiate_call(call_request)
        
        # Verify call works with updated agent
        assert call_result.call_sid.startswith("CA")
        assert call_result.status == CallStatus.INITIATED
        assert call_result.agent_id == agent.id


@pytest.mark.e2e
@pytest.mark.ultravox
@pytest.mark.twilio
class TestEndToEndErrorScenarios:
    """End-to-end tests for error scenarios."""
    
    @pytest.mark.asyncio
    async def test_call_with_nonexistent_agent(self, call_service: CallService, integration_config):
        """Test call flow with nonexistent agent ID."""
        call_request = CallRequest(
            phone_number=integration_config["test_phone_number"],
            template_context={"test": "nonexistent_agent"},
            agent_id="nonexistent_agent_12345"
        )
        
        # Should fail when trying to get join URL for nonexistent agent
        with pytest.raises(Exception) as exc_info:
            await call_service.initiate_call(call_request)
        
        # Verify error is related to agent not found
        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in ["agent", "not found", "nonexistent"])
    
    @pytest.mark.asyncio
    async def test_call_flow_with_network_issues(self, agent_service: AgentService, call_service: CallService,
                                               integration_config, cleanup_agents):
        """Test call flow resilience to network issues (simulated by invalid URLs)."""
        # Create agent with valid API
        agent_config = AgentConfig(
            name="Network Test Agent",
            prompt="You are a test agent for network resilience testing.",
            voice="default",
            language="en"
        )
        
        agent = await agent_service.create_agent(agent_config)
        cleanup_agents(agent.id)
        
        # Now simulate network issues by temporarily changing the base URL
        original_get_config = call_service.config_service.get_ultravox_config
        
        def get_invalid_config():
            config = original_get_config()
            config.base_url = "https://invalid-ultravox-api.example.com"
            return config
        
        call_service.config_service.get_ultravox_config = get_invalid_config
        
        call_request = CallRequest(
            phone_number=integration_config["test_phone_number"],
            template_context={"test": "network_issues"},
            agent_id=agent.id
        )
        
        # Should fail due to network issues
        with pytest.raises(Exception) as exc_info:
            await call_service.initiate_call(call_request)
        
        # Verify error is network-related
        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in ["connection", "network", "timeout", "resolve"])
        
        # Restore original config
        call_service.config_service.get_ultravox_config = original_get_config


@pytest.mark.e2e
@pytest.mark.ultravox
@pytest.mark.twilio
@pytest.mark.slow
class TestEndToEndPerformance:
    """End-to-end performance and load tests."""
    
    @pytest.mark.asyncio
    async def test_sequential_call_creation_performance(self, agent_service: AgentService, call_service: CallService,
                                                      integration_config, cleanup_agents):
        """Test performance of creating multiple calls sequentially."""
        import time
        
        # Create agent
        agent_config = AgentConfig(
            name="Performance Test Agent",
            prompt="You are a test agent for performance testing.",
            voice="default",
            language="en"
        )
        
        agent = await agent_service.create_agent(agent_config)
        cleanup_agents(agent.id)
        
        # Measure time for sequential call creation
        start_time = time.time()
        
        call_results = []
        for i in range(3):  # Small number to avoid excessive API calls
            call_request = CallRequest(
                phone_number=integration_config["test_phone_number"],
                template_context={"call_index": str(i), "test": "performance"},
                agent_id=agent.id
            )
            
            call_result = await call_service.initiate_call(call_request)
            call_results.append(call_result)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify all calls were successful
        assert len(call_results) == 3
        for call_result in call_results:
            assert call_result.call_sid.startswith("CA")
            assert call_result.status == CallStatus.INITIATED
        
        # Performance assertion (adjust based on expected performance)
        avg_time_per_call = total_time / 3
        assert avg_time_per_call < 10.0  # Each call should take less than 10 seconds
        
        print(f"Sequential call creation: {total_time:.2f}s total, {avg_time_per_call:.2f}s per call")
    
    @pytest.mark.asyncio
    async def test_concurrent_call_creation_performance(self, agent_service: AgentService, call_service: CallService,
                                                      integration_config, cleanup_agents):
        """Test performance of creating multiple calls concurrently."""
        import time
        
        # Create agent
        agent_config = AgentConfig(
            name="Concurrent Performance Test Agent",
            prompt="You are a test agent for concurrent performance testing.",
            voice="default",
            language="en"
        )
        
        agent = await agent_service.create_agent(agent_config)
        cleanup_agents(agent.id)
        
        # Measure time for concurrent call creation
        start_time = time.time()
        
        call_requests = [
            CallRequest(
                phone_number=integration_config["test_phone_number"],
                template_context={"call_index": str(i), "test": "concurrent_performance"},
                agent_id=agent.id
            )
            for i in range(3)
        ]
        
        call_tasks = [call_service.initiate_call(req) for req in call_requests]
        call_results = await asyncio.gather(*call_tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify results
        successful_calls = [r for r in call_results if not isinstance(r, Exception)]
        assert len(successful_calls) >= 1  # At least one should succeed
        
        # Performance assertion
        assert total_time < 15.0  # Concurrent calls should complete within 15 seconds
        
        print(f"Concurrent call creation: {total_time:.2f}s total for {len(successful_calls)} successful calls")