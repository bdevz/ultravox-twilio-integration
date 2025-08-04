"""
ElevenLabs Agent Service for conversational AI agent management.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import uuid4

from app.models.elevenlabs import (
    ElevenLabsAgent,
    ElevenLabsAgentConfig,
    ElevenLabsAgentStatus,
    ElevenLabsConfig,
    Voice
)
from app.services.elevenlabs_client import ElevenLabsHTTPClient
from app.services.voice_service import VoiceService
from app.exceptions.elevenlabs_exceptions import (
    ElevenLabsAPIError,
    VoiceNotFoundError,
    ElevenLabsAgentError,
    ElevenLabsAgentNotFoundError,
    ElevenLabsAgentValidationError,
    ElevenLabsAgentCreationError
)
from app.logging_config import LoggerMixin, get_correlation_id

logger = logging.getLogger(__name__)


class ElevenLabsAgentService(LoggerMixin):
    """Service for managing ElevenLabs conversational AI agents."""
    
    def __init__(self, config: ElevenLabsConfig, voice_service: VoiceService):
        """
        Initialize ElevenLabs Agent Service.
        
        Args:
            config: ElevenLabs configuration
            voice_service: Voice service for voice validation
        """
        self.config = config
        self.voice_service = voice_service
        self._agent_cache: Dict[str, ElevenLabsAgent] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutes
    
    async def create_agent(self, agent_config: ElevenLabsAgentConfig) -> ElevenLabsAgent:
        """
        Create a new ElevenLabs conversational agent.
        
        Args:
            agent_config: Agent configuration
            
        Returns:
            ElevenLabsAgent: Created agent
            
        Raises:
            ElevenLabsAgentValidationError: If configuration is invalid
            VoiceNotFoundError: If specified voice doesn't exist
            ElevenLabsAgentCreationError: If agent creation fails
        """
        correlation_id = get_correlation_id()
        
        try:
            self.logger.info(
                f"Creating ElevenLabs agent: {agent_config.name}",
                extra={
                    "agent_name": agent_config.name,
                    "voice_id": agent_config.voice_id,
                    "correlation_id": correlation_id
                }
            )
            
            # Validate agent configuration
            await self._validate_agent_config(agent_config)
            
            # Verify voice exists
            await self._verify_voice_exists(agent_config.voice_id)
            
            # Create agent via ElevenLabs API
            agent_data = await self._create_agent_api(agent_config)
            
            # Create agent model
            agent = ElevenLabsAgent(
                id=agent_data["id"],
                config=agent_config,
                created_at=datetime.now(timezone.utc),
                status=ElevenLabsAgentStatus.ACTIVE
            )
            
            # Cache the agent
            self._cache_agent(agent)
            
            self.logger.info(
                f"Successfully created ElevenLabs agent: {agent.id}",
                extra={
                    "agent_id": agent.id,
                    "agent_name": agent_config.name,
                    "correlation_id": correlation_id
                }
            )
            
            return agent
            
        except (ElevenLabsAgentValidationError, VoiceNotFoundError):
            raise
        except ElevenLabsAPIError as e:
            self.logger.error(
                f"ElevenLabs API error creating agent: {str(e)}",
                extra={"correlation_id": correlation_id},
                exc_info=True
            )
            raise ElevenLabsAgentCreationError(f"API error: {str(e)}")
        except Exception as e:
            self.logger.error(
                f"Unexpected error creating agent: {str(e)}",
                extra={"correlation_id": correlation_id},
                exc_info=True
            )
            raise ElevenLabsAgentCreationError(f"Unexpected error: {str(e)}")
    
    async def list_agents(self, force_refresh: bool = False) -> List[ElevenLabsAgent]:
        """
        List all ElevenLabs agents with caching.
        
        Args:
            force_refresh: Force refresh of agent cache
            
        Returns:
            List[ElevenLabsAgent]: List of agents
            
        Raises:
            ElevenLabsAPIError: If API request fails
        """
        correlation_id = get_correlation_id()
        
        # Check cache first
        if not force_refresh and self._is_cache_valid():
            self.logger.debug(
                "Returning cached agents",
                extra={
                    "agent_count": len(self._agent_cache),
                    "correlation_id": correlation_id
                }
            )
            return list(self._agent_cache.values())
        
        try:
            self.logger.info(
                "Fetching agents from ElevenLabs API",
                extra={
                    "force_refresh": force_refresh,
                    "correlation_id": correlation_id
                }
            )
            
            # Fetch agents from API
            agents_data = await self._list_agents_api()
            
            # Convert to agent models
            agents = []
            for agent_data in agents_data:
                try:
                    agent = await self._agent_data_to_model(agent_data)
                    agents.append(agent)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to convert agent data to model: {str(e)}",
                        extra={
                            "agent_id": agent_data.get("id", "unknown"),
                            "correlation_id": correlation_id
                        }
                    )
            
            # Update cache
            self._agent_cache = {agent.id: agent for agent in agents}
            self._cache_timestamp = datetime.now(timezone.utc)
            
            self.logger.info(
                f"Successfully cached {len(agents)} agents",
                extra={
                    "agent_count": len(agents),
                    "correlation_id": correlation_id
                }
            )
            
            return agents
            
        except ElevenLabsAPIError:
            raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error listing agents: {str(e)}",
                extra={"correlation_id": correlation_id},
                exc_info=True
            )
            raise ElevenLabsAPIError(f"Failed to list agents: {str(e)}")
    
    async def get_agent(self, agent_id: str) -> ElevenLabsAgent:
        """
        Get a specific agent by ID.
        
        Args:
            agent_id: Agent ID to retrieve
            
        Returns:
            ElevenLabsAgent: Agent information
            
        Raises:
            ElevenLabsAgentNotFoundError: If agent is not found
            ElevenLabsAPIError: If API request fails
        """
        correlation_id = get_correlation_id()
        
        try:
            # Check cache first
            if agent_id in self._agent_cache and self._is_cache_valid():
                self.logger.debug(
                    f"Returning cached agent: {agent_id}",
                    extra={"agent_id": agent_id, "correlation_id": correlation_id}
                )
                return self._agent_cache[agent_id]
            
            self.logger.info(
                f"Fetching agent from API: {agent_id}",
                extra={"agent_id": agent_id, "correlation_id": correlation_id}
            )
            
            # Fetch from API
            agent_data = await self._get_agent_api(agent_id)
            agent = await self._agent_data_to_model(agent_data)
            
            # Cache the agent
            self._cache_agent(agent)
            
            self.logger.debug(
                f"Successfully retrieved agent: {agent_id}",
                extra={"agent_id": agent_id, "correlation_id": correlation_id}
            )
            
            return agent
            
        except ElevenLabsAgentNotFoundError:
            raise
        except ElevenLabsAPIError:
            raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error retrieving agent {agent_id}: {str(e)}",
                extra={"agent_id": agent_id, "correlation_id": correlation_id},
                exc_info=True
            )
            raise ElevenLabsAPIError(f"Failed to retrieve agent: {str(e)}")
    
    async def update_agent(
        self, 
        agent_id: str, 
        agent_config: ElevenLabsAgentConfig
    ) -> ElevenLabsAgent:
        """
        Update an existing agent.
        
        Args:
            agent_id: Agent ID to update
            agent_config: New agent configuration
            
        Returns:
            ElevenLabsAgent: Updated agent
            
        Raises:
            ElevenLabsAgentNotFoundError: If agent is not found
            ElevenLabsAgentValidationError: If configuration is invalid
            VoiceNotFoundError: If specified voice doesn't exist
            ElevenLabsAPIError: If API request fails
        """
        correlation_id = get_correlation_id()
        
        try:
            self.logger.info(
                f"Updating ElevenLabs agent: {agent_id}",
                extra={
                    "agent_id": agent_id,
                    "agent_name": agent_config.name,
                    "correlation_id": correlation_id
                }
            )
            
            # Validate agent configuration
            await self._validate_agent_config(agent_config)
            
            # Verify voice exists
            await self._verify_voice_exists(agent_config.voice_id)
            
            # Update agent via API
            agent_data = await self._update_agent_api(agent_id, agent_config)
            
            # Create updated agent model
            agent = ElevenLabsAgent(
                id=agent_data["id"],
                config=agent_config,
                created_at=datetime.fromisoformat(agent_data.get("created_at", datetime.now(timezone.utc).isoformat())),
                updated_at=datetime.now(timezone.utc),
                status=ElevenLabsAgentStatus.ACTIVE
            )
            
            # Update cache
            self._cache_agent(agent)
            
            self.logger.info(
                f"Successfully updated ElevenLabs agent: {agent_id}",
                extra={
                    "agent_id": agent_id,
                    "agent_name": agent_config.name,
                    "correlation_id": correlation_id
                }
            )
            
            return agent
            
        except (ElevenLabsAgentNotFoundError, ElevenLabsAgentValidationError, VoiceNotFoundError):
            raise
        except ElevenLabsAPIError:
            raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error updating agent {agent_id}: {str(e)}",
                extra={"agent_id": agent_id, "correlation_id": correlation_id},
                exc_info=True
            )
            raise ElevenLabsAPIError(f"Failed to update agent: {str(e)}")
    
    async def delete_agent(self, agent_id: str) -> bool:
        """
        Delete an agent and cleanup resources.
        
        Args:
            agent_id: Agent ID to delete
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            ElevenLabsAgentNotFoundError: If agent is not found
            ElevenLabsAPIError: If API request fails
        """
        correlation_id = get_correlation_id()
        
        try:
            self.logger.info(
                f"Deleting ElevenLabs agent: {agent_id}",
                extra={"agent_id": agent_id, "correlation_id": correlation_id}
            )
            
            # Delete agent via API
            await self._delete_agent_api(agent_id)
            
            # Remove from cache
            if agent_id in self._agent_cache:
                del self._agent_cache[agent_id]
            
            self.logger.info(
                f"Successfully deleted ElevenLabs agent: {agent_id}",
                extra={"agent_id": agent_id, "correlation_id": correlation_id}
            )
            
            return True
            
        except ElevenLabsAgentNotFoundError:
            raise
        except ElevenLabsAPIError:
            raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error deleting agent {agent_id}: {str(e)}",
                extra={"agent_id": agent_id, "correlation_id": correlation_id},
                exc_info=True
            )
            raise ElevenLabsAPIError(f"Failed to delete agent: {str(e)}")
    
    async def _validate_agent_config(self, config: ElevenLabsAgentConfig) -> None:
        """Validate agent configuration."""
        try:
            # Pydantic validation is automatic, but we can add custom checks
            if not config.name.strip():
                raise ElevenLabsAgentValidationError("Agent name cannot be empty")
            
            if not config.system_prompt.strip():
                raise ElevenLabsAgentValidationError("System prompt cannot be empty")
            
            if not config.voice_id.strip():
                raise ElevenLabsAgentValidationError("Voice ID cannot be empty")
            
            # Validate template variables
            if config.template_variables:
                for key, value in config.template_variables.items():
                    if not isinstance(key, str) or not isinstance(value, str):
                        raise ElevenLabsAgentValidationError(
                            "Template variables must be string key-value pairs"
                        )
            
        except Exception as e:
            if isinstance(e, ElevenLabsAgentValidationError):
                raise
            raise ElevenLabsAgentValidationError(f"Configuration validation failed: {str(e)}")
    
    async def _verify_voice_exists(self, voice_id: str) -> None:
        """Verify that the specified voice exists."""
        try:
            await self.voice_service.get_voice_by_id(voice_id)
        except Exception as e:
            raise VoiceNotFoundError(voice_id)
    
    async def _create_agent_api(self, config: ElevenLabsAgentConfig) -> Dict[str, Any]:
        """Create agent via ElevenLabs API."""
        async with ElevenLabsHTTPClient(self.config) as client:
            payload = config.to_elevenlabs_dict()
            response = await client._make_request(
                method="POST",
                endpoint="v1/convai/agents",
                data=payload
            )
            return response
    
    async def _list_agents_api(self) -> List[Dict[str, Any]]:
        """List agents via ElevenLabs API."""
        async with ElevenLabsHTTPClient(self.config) as client:
            response = await client._make_request(
                method="GET",
                endpoint="v1/convai/agents"
            )
            return response.get("agents", [])
    
    async def _get_agent_api(self, agent_id: str) -> Dict[str, Any]:
        """Get agent via ElevenLabs API."""
        async with ElevenLabsHTTPClient(self.config) as client:
            try:
                response = await client._make_request(
                    method="GET",
                    endpoint=f"v1/convai/agents/{agent_id}"
                )
                return response
            except ElevenLabsAPIError as e:
                if "404" in str(e) or "not found" in str(e).lower():
                    raise ElevenLabsAgentNotFoundError(agent_id)
                raise
    
    async def _update_agent_api(
        self, 
        agent_id: str, 
        config: ElevenLabsAgentConfig
    ) -> Dict[str, Any]:
        """Update agent via ElevenLabs API."""
        async with ElevenLabsHTTPClient(self.config) as client:
            payload = config.to_elevenlabs_dict()
            try:
                response = await client._make_request(
                    method="PUT",
                    endpoint=f"v1/convai/agents/{agent_id}",
                    data=payload
                )
                return response
            except ElevenLabsAPIError as e:
                if "404" in str(e) or "not found" in str(e).lower():
                    raise ElevenLabsAgentNotFoundError(agent_id)
                raise
    
    async def _delete_agent_api(self, agent_id: str) -> None:
        """Delete agent via ElevenLabs API."""
        async with ElevenLabsHTTPClient(self.config) as client:
            try:
                await client._make_request(
                    method="DELETE",
                    endpoint=f"v1/convai/agents/{agent_id}"
                )
            except ElevenLabsAPIError as e:
                if "404" in str(e) or "not found" in str(e).lower():
                    raise ElevenLabsAgentNotFoundError(agent_id)
                raise
    
    async def _agent_data_to_model(self, agent_data: Dict[str, Any]) -> ElevenLabsAgent:
        """Convert API response data to agent model."""
        try:
            # Extract configuration from API response
            config = ElevenLabsAgentConfig(
                name=agent_data["name"],
                system_prompt=agent_data["system_prompt"],
                voice_id=agent_data["voice_id"],
                # conversation_config will use defaults if not provided
            )
            
            # Parse timestamps
            created_at = datetime.fromisoformat(
                agent_data.get("created_at", datetime.now(timezone.utc).isoformat())
            )
            updated_at = None
            if agent_data.get("updated_at"):
                updated_at = datetime.fromisoformat(agent_data["updated_at"])
            
            return ElevenLabsAgent(
                id=agent_data["id"],
                config=config,
                created_at=created_at,
                updated_at=updated_at,
                status=ElevenLabsAgentStatus(agent_data.get("status", "active"))
            )
            
        except Exception as e:
            raise ElevenLabsAPIError(f"Failed to parse agent data: {str(e)}")
    
    def _cache_agent(self, agent: ElevenLabsAgent) -> None:
        """Cache an agent."""
        self._agent_cache[agent.id] = agent
        if not self._cache_timestamp:
            self._cache_timestamp = datetime.now(timezone.utc)
    
    def _is_cache_valid(self) -> bool:
        """Check if agent cache is still valid."""
        if not self._cache_timestamp:
            return False
        
        age_seconds = (datetime.now(timezone.utc) - self._cache_timestamp).total_seconds()
        return age_seconds < self._cache_ttl_seconds
    
    def clear_cache(self) -> None:
        """Clear the agent cache."""
        self._agent_cache.clear()
        self._cache_timestamp = None
        self.logger.debug("Agent cache cleared")


# Global agent service instance
_agent_service: Optional[ElevenLabsAgentService] = None


def get_elevenlabs_agent_service(
    config: Optional[ElevenLabsConfig] = None,
    voice_service: Optional[VoiceService] = None
) -> ElevenLabsAgentService:
    """
    Get the global ElevenLabs agent service instance.
    
    Args:
        config: ElevenLabs configuration (optional)
        voice_service: Voice service instance (optional)
        
    Returns:
        ElevenLabsAgentService: The agent service instance
    """
    global _agent_service
    if _agent_service is None:
        if config is None or voice_service is None:
            raise ValueError("Config and voice_service are required for first initialization")
        
        _agent_service = ElevenLabsAgentService(config, voice_service)
    
    return _agent_service