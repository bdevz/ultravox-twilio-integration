"""
Agent service for Ultravox integration with CRUD operations.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.models.agent import Agent, AgentConfig, AgentStatus
from app.services.http_client_service import HTTPClientService, HTTPClientError
from app.services.config_service import ConfigService
from app.exceptions import (
    ResourceNotFoundError,
    UltravoxAPIError,
    ValidationError,
    BusinessLogicError,
    ConfigurationError
)
from app.logging_config import LoggerMixin


logger = logging.getLogger(__name__)


class AgentServiceError(Exception):
    """Base exception for agent service errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AgentNotFoundError(AgentServiceError):
    """Exception raised when an agent is not found."""
    pass


class AgentCreationError(AgentServiceError):
    """Exception raised when agent creation fails."""
    pass


class AgentUpdateError(AgentServiceError):
    """Exception raised when agent update fails."""
    pass


class AgentService(LoggerMixin):
    """Service for managing Ultravox agents with CRUD operations."""
    
    def __init__(self, http_client: HTTPClientService, config_service: ConfigService):
        """
        Initialize agent service.
        
        Args:
            http_client: HTTP client service for API calls
            config_service: Configuration service for API credentials
        """
        self.http_client = http_client
        self.config_service = config_service
        self._ultravox_config = None
    
    def _get_ultravox_config(self):
        """Get Ultravox configuration with caching."""
        if self._ultravox_config is None:
            self._ultravox_config = self.config_service.get_ultravox_config()
        return self._ultravox_config
    
    async def create_agent(self, config: AgentConfig) -> Agent:
        """
        Create a new Ultravox agent.
        
        Args:
            config: Agent configuration
            
        Returns:
            Agent: Created agent with ID and metadata
            
        Raises:
            AgentCreationError: If agent creation fails
        """
        from app.metrics import record_metric
        from app.logging_config import get_correlation_id
        
        correlation_id = get_correlation_id()
        start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(
                f"Creating agent with name: {config.name}",
                extra={
                    "agent_name": config.name,
                    "agent_voice": config.voice,
                    "agent_language": config.language,
                    "has_template_variables": bool(config.template_variables),
                    "correlation_id": correlation_id
                }
            )
            
            # Record agent creation attempt metric
            record_metric(
                "agent_creation_attempts_total",
                1,
                tags={"agent_name": config.name},
                correlation_id=correlation_id
            )
            
            # Validate configuration
            if not config.name or not config.name.strip():
                self.logger.error("Agent creation failed: name is required")
                raise ValidationError("Agent name is required")
            
            if not config.prompt or not config.prompt.strip():
                self.logger.error("Agent creation failed: prompt is required")
                raise ValidationError("Agent prompt is required")
            
            ultravox_config = self._get_ultravox_config()
            
            # Validate agent name format (Ultravox requirement: ^[a-zA-Z0-9_-]{1,64}$)
            import re
            if not re.match(r'^[a-zA-Z0-9_-]{1,64}$', config.name):
                self.logger.error(f"Agent creation failed: invalid name format: {config.name}")
                raise ValidationError(
                    f"Agent name '{config.name}' is invalid. Must contain only letters, numbers, underscores, and hyphens (no spaces), max 64 characters."
                )
            
            # Prepare agent data for Ultravox API (correct format)
            agent_data = {
                "name": config.name,
                "callTemplate": {
                    "systemPrompt": config.prompt,
                    "voice": config.voice or "9dc1c0e9-db7c-46a5-a610-b04e7ebf37ee"  # Use working voice ID
                }
            }
            
            # Note: Template variables are handled in the prompt itself with {{variable}} syntax
            # The language setting might not be directly supported in this API version
            if config.template_variables:
                self.logger.debug(
                    f"Agent template variables will be handled via prompt substitution: {list(config.template_variables.keys())}",
                    extra={"correlation_id": correlation_id}
                )
            
            # Make API call to create agent
            self.logger.debug("Making Ultravox API call to create agent")
            response = await self.http_client.make_ultravox_request(
                method="POST",
                endpoint="/api/agents",
                data=agent_data,
                api_key=ultravox_config.api_key,
                base_url=ultravox_config.base_url
            )
            
            # Parse response and create Agent model
            agent_id = response.get("agentId")
            if not agent_id:
                self.logger.error("Agent creation failed: No agent ID in response", extra={
                    "response_keys": list(response.keys()),
                    "correlation_id": correlation_id
                })
                raise BusinessLogicError(
                    "Agent creation failed: No agent ID in response",
                    details={"response": response}
                )
            
            # Create Agent instance
            now = datetime.now(timezone.utc)
            agent = Agent(
                id=agent_id,
                config=config,
                created_at=now,
                updated_at=now,
                status=AgentStatus.ACTIVE
            )
            
            # Record successful creation metrics
            creation_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            record_metric(
                "agent_creation_duration_seconds",
                creation_duration,
                tags={"agent_name": config.name, "success": "true"},
                correlation_id=correlation_id
            )
            
            record_metric(
                "agent_creation_success_total",
                1,
                tags={"agent_name": config.name},
                correlation_id=correlation_id
            )
            
            self.logger.info(
                f"Successfully created agent {agent_id}",
                extra={
                    "agent_id": agent_id,
                    "agent_name": config.name,
                    "creation_duration_seconds": round(creation_duration, 3),
                    "correlation_id": correlation_id
                }
            )
            return agent
            
        except (ValidationError, BusinessLogicError, UltravoxAPIError) as e:
            # Record failure metrics
            creation_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            record_metric(
                "agent_creation_duration_seconds",
                creation_duration,
                tags={"agent_name": config.name, "success": "false", "error_type": type(e).__name__},
                correlation_id=correlation_id
            )
            
            record_metric(
                "agent_creation_failures_total",
                1,
                tags={"agent_name": config.name, "error_type": type(e).__name__},
                correlation_id=correlation_id
            )
            
            self.logger.error(
                f"Agent creation failed: {str(e)}",
                extra={
                    "agent_name": config.name,
                    "error_type": type(e).__name__,
                    "creation_duration_seconds": round(creation_duration, 3),
                    "correlation_id": correlation_id
                }
            )
            # Re-raise specific exceptions
            raise
        except HTTPClientError as e:
            # Record failure metrics
            creation_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            record_metric(
                "agent_creation_failures_total",
                1,
                tags={"agent_name": config.name, "error_type": "HTTPClientError"},
                correlation_id=correlation_id
            )
            
            self.logger.error(
                f"HTTP error creating agent: {e.message}",
                extra={
                    "agent_name": config.name,
                    "http_status_code": e.status_code,
                    "creation_duration_seconds": round(creation_duration, 3),
                    "correlation_id": correlation_id
                }
            )
            raise UltravoxAPIError(
                f"Failed to create agent: {e.message}",
                details={"http_error": e.details, "config": config.model_dump()}
            )
        except Exception as e:
            # Record failure metrics
            creation_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            record_metric(
                "agent_creation_failures_total",
                1,
                tags={"agent_name": config.name, "error_type": "UnexpectedError"},
                correlation_id=correlation_id
            )
            
            self.logger.error(
                f"Unexpected error creating agent: {str(e)}",
                extra={
                    "agent_name": config.name,
                    "error_type": type(e).__name__,
                    "creation_duration_seconds": round(creation_duration, 3),
                    "correlation_id": correlation_id
                },
                exc_info=True
            )
            raise BusinessLogicError(
                f"Unexpected error creating agent: {str(e)}",
                details={"config": config.model_dump()}
            )
    
    async def get_agent(self, agent_id: str) -> Agent:
        """
        Retrieve an agent by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent: Agent details
            
        Raises:
            AgentNotFoundError: If agent is not found
            AgentServiceError: For other errors
        """
        try:
            logger.debug(f"Retrieving agent: {agent_id}")
            
            ultravox_config = self._get_ultravox_config()
            
            # Make API call to get agent
            response = await self.http_client.make_ultravox_request(
                method="GET",
                endpoint=f"/api/agents/{agent_id}",
                api_key=ultravox_config.api_key,
                base_url=ultravox_config.base_url
            )
            
            # Parse response and create Agent model
            agent = self._parse_agent_response(response, agent_id)
            
            logger.debug(f"Successfully retrieved agent {agent_id}")
            return agent
            
        except HTTPClientError as e:
            if e.status_code == 404:
                self.logger.warning(f"Agent not found: {agent_id}")
                raise ResourceNotFoundError("agent", agent_id)
            
            self.logger.error(f"HTTP error retrieving agent {agent_id}: {e.message}")
            raise UltravoxAPIError(
                f"Failed to retrieve agent {agent_id}: {e.message}",
                details={"http_error": e.details, "agent_id": agent_id}
            )
        except ResourceNotFoundError:
            raise
        except UltravoxAPIError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving agent {agent_id}: {str(e)}")
            raise BusinessLogicError(
                f"Unexpected error retrieving agent {agent_id}: {str(e)}",
                details={"agent_id": agent_id}
            )
    
    async def list_agents(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Agent]:
        """
        List all agents.
        
        Args:
            limit: Maximum number of agents to return
            offset: Number of agents to skip
            
        Returns:
            List[Agent]: List of agents
            
        Raises:
            AgentServiceError: If listing fails
        """
        try:
            logger.debug("Listing agents")
            
            ultravox_config = self._get_ultravox_config()
            
            # Prepare query parameters
            params = {}
            if limit is not None:
                params["limit"] = str(limit)
            if offset is not None:
                params["offset"] = str(offset)
            
            # Make API call to list agents
            response = await self.http_client.make_ultravox_request(
                method="GET",
                endpoint="/api/agents",
                api_key=ultravox_config.api_key,
                base_url=ultravox_config.base_url
            )
            
            # Parse response
            agents_data = response.get("results", [])
            agents = []
            
            for agent_data in agents_data:
                try:
                    agent = self._parse_agent_response(agent_data)
                    agents.append(agent)
                except Exception as e:
                    logger.warning(f"Failed to parse agent data: {e}")
                    continue
            
            logger.debug(f"Successfully listed {len(agents)} agents")
            return agents
            
        except HTTPClientError as e:
            logger.error(f"HTTP error listing agents: {e.message}")
            raise AgentServiceError(
                f"Failed to list agents: {e.message}",
                details={"http_error": e.details}
            )
        except Exception as e:
            logger.error(f"Unexpected error listing agents: {str(e)}")
            raise AgentServiceError(f"Unexpected error listing agents: {str(e)}")
    
    async def update_agent(self, agent_id: str, config: AgentConfig) -> Agent:
        """
        Update an existing agent.
        
        Args:
            agent_id: Agent identifier
            config: Updated agent configuration
            
        Returns:
            Agent: Updated agent
            
        Raises:
            AgentNotFoundError: If agent is not found
            AgentUpdateError: If update fails
        """
        try:
            logger.info(f"Updating agent {agent_id}")
            
            ultravox_config = self._get_ultravox_config()
            
            # Prepare update data
            update_data = {
                "name": config.name,
                "systemPrompt": config.prompt,
                "voice": config.voice or "default",
                "language": config.language or "en"
            }
            
            # Add template variables if provided
            if config.template_variables:
                update_data["templateVariables"] = config.template_variables
            
            # Make API call to update agent
            response = await self.http_client.make_ultravox_request(
                method="PUT",
                endpoint=f"/api/agents/{agent_id}",
                data=update_data,
                api_key=ultravox_config.api_key,
                base_url=ultravox_config.base_url
            )
            
            # Parse response and create updated Agent model
            agent = self._parse_agent_response(response, agent_id)
            
            logger.info(f"Successfully updated agent {agent_id}")
            return agent
            
        except HTTPClientError as e:
            if e.status_code == 404:
                logger.warning(f"Agent not found for update: {agent_id}")
                raise AgentNotFoundError(
                    f"Agent {agent_id} not found",
                    details={"agent_id": agent_id}
                )
            
            logger.error(f"HTTP error updating agent {agent_id}: {e.message}")
            raise AgentUpdateError(
                f"Failed to update agent {agent_id}: {e.message}",
                details={"http_error": e.details, "agent_id": agent_id, "config": config.model_dump()}
            )
        except AgentNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating agent {agent_id}: {str(e)}")
            raise AgentUpdateError(
                f"Unexpected error updating agent {agent_id}: {str(e)}",
                details={"agent_id": agent_id, "config": config.model_dump()}
            )
    
    async def delete_agent(self, agent_id: str) -> bool:
        """
        Delete an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            AgentNotFoundError: If agent is not found
            AgentServiceError: If deletion fails
        """
        try:
            logger.info(f"Deleting agent {agent_id}")
            
            ultravox_config = self._get_ultravox_config()
            
            # Make API call to delete agent
            await self.http_client.make_ultravox_request(
                method="DELETE",
                endpoint=f"/api/agents/{agent_id}",
                api_key=ultravox_config.api_key,
                base_url=ultravox_config.base_url
            )
            
            logger.info(f"Successfully deleted agent {agent_id}")
            return True
            
        except HTTPClientError as e:
            if e.status_code == 404:
                logger.warning(f"Agent not found for deletion: {agent_id}")
                raise AgentNotFoundError(
                    f"Agent {agent_id} not found",
                    details={"agent_id": agent_id}
                )
            
            logger.error(f"HTTP error deleting agent {agent_id}: {e.message}")
            raise AgentServiceError(
                f"Failed to delete agent {agent_id}: {e.message}",
                details={"http_error": e.details, "agent_id": agent_id}
            )
        except AgentNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting agent {agent_id}: {str(e)}")
            raise AgentServiceError(
                f"Unexpected error deleting agent {agent_id}: {str(e)}",
                details={"agent_id": agent_id}
            )
    
    def _parse_agent_response(self, response_data: Dict[str, Any], agent_id: Optional[str] = None) -> Agent:
        """
        Parse Ultravox API response into Agent model.
        
        Args:
            response_data: Response data from Ultravox API
            agent_id: Optional agent ID if not in response
            
        Returns:
            Agent: Parsed agent model
            
        Raises:
            AgentServiceError: If parsing fails
        """
        try:
            # Extract agent ID
            parsed_agent_id = agent_id or response_data.get("agentId") or response_data.get("id")
            if not parsed_agent_id:
                raise AgentServiceError(
                    "Missing agent ID in response",
                    details={"response_data": response_data}
                )
            
            # Extract agent configuration (Ultravox API structure)
            call_template = response_data.get("callTemplate", {})
            
            # Handle agent name - ensure it's not empty
            agent_name = response_data.get("name", "").strip()
            if not agent_name:
                agent_name = f"Agent-{parsed_agent_id[:8]}"  # Fallback name
            
            # Handle prompt - ensure it's within validation limits
            raw_prompt = call_template.get("systemPrompt", "").strip()
            if not raw_prompt:
                agent_prompt = "Default AI assistant prompt"  # Fallback prompt
            elif len(raw_prompt) > 10000:
                agent_prompt = raw_prompt[:9997] + "..."  # Truncate long prompts
            else:
                agent_prompt = raw_prompt
            
            config = AgentConfig(
                name=agent_name,
                prompt=agent_prompt,
                voice=call_template.get("voice", "default"),
                language=response_data.get("language", "en"),  # May not be in API response
                template_variables=response_data.get("templateVariables", {})
            )
            
            # Extract timestamps (Ultravox API uses "created" not "createdAt")
            created_at = self._parse_timestamp(response_data.get("created"))
            updated_at = self._parse_timestamp(call_template.get("updated"))
            
            # Extract status
            status_str = response_data.get("status", "active").lower()
            try:
                status = AgentStatus(status_str)
            except ValueError:
                logger.warning(f"Unknown agent status: {status_str}, defaulting to active")
                status = AgentStatus.ACTIVE
            
            return Agent(
                id=parsed_agent_id,
                config=config,
                created_at=created_at,
                updated_at=updated_at,
                status=status
            )
            
        except Exception as e:
            logger.error(f"Failed to parse agent response: {str(e)}")
            raise AgentServiceError(
                f"Failed to parse agent response: {str(e)}",
                details={"response_data": response_data}
            )
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """
        Parse timestamp string into datetime object.
        
        Args:
            timestamp_str: ISO timestamp string
            
        Returns:
            datetime: Parsed datetime object
        """
        if not timestamp_str:
            return datetime.now(timezone.utc)
        
        try:
            # Try parsing ISO format
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            return datetime.fromisoformat(timestamp_str)
        except ValueError:
            logger.warning(f"Failed to parse timestamp: {timestamp_str}")
            return datetime.now(timezone.utc)


# Dependency injection helper
async def get_agent_service(
    http_client: HTTPClientService,
    config_service: ConfigService
) -> AgentService:
    """
    Get agent service instance with dependencies.
    
    Args:
        http_client: HTTP client service
        config_service: Configuration service
        
    Returns:
        AgentService: Agent service instance
    """
    return AgentService(http_client, config_service)