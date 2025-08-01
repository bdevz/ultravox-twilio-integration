"""
API routes for Ultravox-Twilio Integration Service.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from app.models.agent import Agent, AgentConfig
from app.models.call import CallRequest, CallResult
from app.services.agent_service import (
    AgentService, 
    AgentServiceError, 
    AgentNotFoundError, 
    AgentCreationError, 
    AgentUpdateError,
    get_agent_service
)
from app.services.call_service import CallService, CallServiceError, get_call_service
from app.services.config_service import ConfigService, get_config_service
from app.services.http_client_service import HTTPClientService
from app.exceptions import AuthenticationError, NetworkError, TimeoutError

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()

# Dependency injection functions
async def get_agent_service_dependency() -> AgentService:
    """Get agent service instance with dependencies."""
    config_service = get_config_service()
    http_client = HTTPClientService()
    return await get_agent_service(http_client, config_service)

async def get_call_service_dependency() -> CallService:
    """Get call service instance with dependencies."""
    config_service = get_config_service()
    http_client = HTTPClientService()
    return get_call_service(config_service, http_client)

# Agent endpoints
@router.post(
    "/agents", 
    response_model=Agent, 
    status_code=status.HTTP_201_CREATED,
    tags=["agents"],
    summary="Create a new agent",
    description="""
    Create a new Ultravox AI agent with the specified configuration.
    
    The agent will be created in Ultravox and can immediately be used for voice calls.
    Template variables in the prompt will be replaced with values provided during calls.
    
    **Example Request:**
    ```json
    {
        "name": "Customer Support Agent",
        "prompt": "You are a helpful customer support agent for {{company_name}}.",
        "voice": "default",
        "language": "en",
        "template_variables": {
            "company_name": "Acme Corp"
        }
    }
    ```
    """,
    responses={
        201: {
            "description": "Agent created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "agent_123456",
                        "config": {
                            "name": "Customer Support Agent",
                            "prompt": "You are a helpful customer support agent for {{company_name}}.",
                            "voice": "default",
                            "language": "en",
                            "template_variables": {"company_name": "Acme Corp"}
                        },
                        "created_at": "2024-01-01T12:00:00Z",
                        "updated_at": "2024-01-01T12:00:00Z",
                        "status": "active"
                    }
                }
            }
        },
        400: {
            "description": "Invalid agent configuration",
            "content": {
                "application/json": {
                    "example": {
                        "error": "validation_error",
                        "message": "Agent name can only contain letters, numbers, spaces, hyphens, and underscores",
                        "details": {"field": "name"},
                        "timestamp": "2024-01-01T12:00:00Z",
                        "request_id": "req_123456"
                    }
                }
            }
        },
        401: {"description": "Missing or invalid API key"},
        500: {"description": "Internal server error"}
    }
)
async def create_agent(
    config: AgentConfig,
    agent_service: AgentService = Depends(get_agent_service_dependency)
) -> Agent:
    """
    Create a new Ultravox agent.
    
    Args:
        config: Agent configuration
        agent_service: Agent service dependency
        
    Returns:
        Agent: Created agent with ID and metadata
        
    Raises:
        HTTPException: For creation errors
    """
    try:
        logger.info(f"Creating agent with name: {config.name}")
        agent = await agent_service.create_agent(config)
        logger.info(f"Successfully created agent: {agent.id}")
        return agent
        
    except AgentCreationError as e:
        logger.error(f"Agent creation failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "agent_creation_failed",
                "message": e.message,
                "details": e.details
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error creating agent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "message": "An unexpected error occurred while creating the agent"
            }
        )

@router.get(
    "/agents", 
    response_model=List[Agent],
    tags=["agents"],
    summary="List all agents",
    description="""
    Retrieve a list of all agents with optional pagination.
    
    Use the `limit` and `offset` parameters to implement pagination:
    - `limit`: Maximum number of agents to return (default: no limit)
    - `offset`: Number of agents to skip (default: 0)
    
    **Example:** Get agents 11-20: `GET /agents?limit=10&offset=10`
    """,
    responses={
        200: {
            "description": "List of agents retrieved successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "agent_123456",
                            "config": {
                                "name": "Customer Support Agent",
                                "prompt": "You are a helpful customer support agent.",
                                "voice": "default",
                                "language": "en",
                                "template_variables": {}
                            },
                            "created_at": "2024-01-01T12:00:00Z",
                            "updated_at": "2024-01-01T12:00:00Z",
                            "status": "active"
                        }
                    ]
                }
            }
        },
        401: {"description": "Missing or invalid API key"},
        500: {"description": "Internal server error"}
    }
)
async def list_agents(
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    agent_service: AgentService = Depends(get_agent_service_dependency)
) -> List[Agent]:
    """
    List all agents.
    
    Args:
        limit: Maximum number of agents to return
        offset: Number of agents to skip
        agent_service: Agent service dependency
        
    Returns:
        List[Agent]: List of agents
        
    Raises:
        HTTPException: For listing errors
    """
    try:
        logger.debug("Listing agents")
        agents = await agent_service.list_agents(limit=limit, offset=offset)
        logger.debug(f"Successfully listed {len(agents)} agents")
        return agents
        
    except AgentServiceError as e:
        logger.error(f"Agent listing failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "agent_listing_failed",
                "message": e.message,
                "details": e.details
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error listing agents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "message": "An unexpected error occurred while listing agents"
            }
        )

@router.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(
    agent_id: str,
    agent_service: AgentService = Depends(get_agent_service_dependency)
) -> Agent:
    """
    Get agent details by ID.
    
    Args:
        agent_id: Agent identifier
        agent_service: Agent service dependency
        
    Returns:
        Agent: Agent details
        
    Raises:
        HTTPException: For retrieval errors
    """
    try:
        logger.debug(f"Getting agent: {agent_id}")
        agent = await agent_service.get_agent(agent_id)
        logger.debug(f"Successfully retrieved agent: {agent_id}")
        return agent
        
    except AgentNotFoundError as e:
        logger.warning(f"Agent not found: {agent_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "agent_not_found",
                "message": e.message,
                "details": e.details
            }
        )
    except AgentServiceError as e:
        logger.error(f"Agent retrieval failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "agent_retrieval_failed",
                "message": e.message,
                "details": e.details
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "message": "An unexpected error occurred while retrieving the agent"
            }
        )

@router.put("/agents/{agent_id}", response_model=Agent)
async def update_agent(
    agent_id: str,
    config: AgentConfig,
    agent_service: AgentService = Depends(get_agent_service_dependency)
) -> Agent:
    """
    Update an existing agent.
    
    Args:
        agent_id: Agent identifier
        config: Updated agent configuration
        agent_service: Agent service dependency
        
    Returns:
        Agent: Updated agent
        
    Raises:
        HTTPException: For update errors
    """
    try:
        logger.info(f"Updating agent: {agent_id}")
        agent = await agent_service.update_agent(agent_id, config)
        logger.info(f"Successfully updated agent: {agent_id}")
        return agent
        
    except AgentNotFoundError as e:
        logger.warning(f"Agent not found for update: {agent_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "agent_not_found",
                "message": e.message,
                "details": e.details
            }
        )
    except AgentUpdateError as e:
        logger.error(f"Agent update failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "agent_update_failed",
                "message": e.message,
                "details": e.details
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error updating agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "message": "An unexpected error occurred while updating the agent"
            }
        )

# Call endpoints
@router.post(
    "/calls/{agent_id}", 
    response_model=CallResult, 
    status_code=status.HTTP_201_CREATED,
    tags=["calls"],
    summary="Initiate a voice call",
    description="""
    Initiate a voice call using the specified agent.
    
    This endpoint:
    1. Creates a call session with Ultravox using the agent
    2. Receives a WebSocket join URL for the AI conversation
    3. Initiates a Twilio voice call to the specified phone number
    4. Connects the call to the Ultravox AI agent via streaming
    
    **Template Context:**
    Use the `template_context` to provide dynamic values that will replace 
    template variables in the agent's prompt. For example, if your agent 
    prompt contains `{{customer_name}}`, provide `{"customer_name": "John Doe"}`.
    
    **Phone Number Format:**
    Phone numbers must be in international format starting with `+` followed 
    by country code and number (e.g., `+1234567890`).
    
    **Example Request:**
    ```json
    {
        "phone_number": "+1234567890",
        "template_context": {
            "customer_name": "John Doe",
            "order_id": "ORD-12345"
        },
        "agent_id": "agent_123456"
    }
    ```
    """,
    responses={
        201: {
            "description": "Call initiated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "call_sid": "CA1234567890abcdef1234567890abcdef",
                        "join_url": "wss://api.ultravox.ai/calls/call_789/join",
                        "status": "initiated",
                        "created_at": "2024-01-01T12:00:00Z",
                        "agent_id": "agent_123456",
                        "phone_number": "+1234567890"
                    }
                }
            }
        },
        400: {
            "description": "Invalid call request",
            "content": {
                "application/json": {
                    "example": {
                        "error": "validation_error",
                        "message": "Phone number must be in valid international format",
                        "details": {"field": "phone_number"},
                        "timestamp": "2024-01-01T12:00:00Z",
                        "request_id": "req_123456"
                    }
                }
            }
        },
        401: {"description": "Missing or invalid API key"},
        404: {"description": "Agent not found"},
        500: {"description": "Internal server error"}
    }
)
async def initiate_call(
    agent_id: str,
    call_request: CallRequest,
    call_service: CallService = Depends(get_call_service_dependency)
) -> CallResult:
    """
    Initiate a call with the specified agent.
    
    Args:
        agent_id: Agent identifier
        call_request: Call request details
        call_service: Call service dependency
        
    Returns:
        CallResult: Call result with SID, join URL, and status
        
    Raises:
        HTTPException: For call initiation errors
    """
    try:
        # Validate that agent_id matches the one in call_request
        if call_request.agent_id != agent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "agent_id_mismatch",
                    "message": "Agent ID in URL path must match agent ID in request body"
                }
            )
        
        logger.info(f"Initiating call for agent {agent_id} to {call_request.phone_number}")
        call_result = await call_service.initiate_call(call_request)
        logger.info(f"Successfully initiated call: {call_result.call_sid}")
        return call_result
        
    except CallServiceError as e:
        logger.error(f"Call initiation failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "call_initiation_failed",
                "message": e.message,
                "details": e.details
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error initiating call: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "message": "An unexpected error occurred while initiating the call"
            }
        )

# Metrics endpoints
@router.get("/metrics")
async def get_metrics():
    """
    Get application metrics.
    
    Returns:
        dict: Application metrics and statistics
    """
    try:
        from app.metrics import get_metrics_collector
        
        logger.debug("Metrics endpoint requested")
        
        metrics_collector = get_metrics_collector()
        metrics_data = metrics_collector.get_all_metrics()
        
        logger.debug("Successfully retrieved metrics data")
        return metrics_data
        
    except Exception as e:
        logger.error(f"Error retrieving metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "metrics_retrieval_failed",
                "message": "Failed to retrieve application metrics"
            }
        )


@router.get("/metrics/events")
async def get_recent_events(limit: int = 100):
    """
    Get recent metric events.
    
    Args:
        limit: Maximum number of events to return (default: 100)
        
    Returns:
        dict: Recent metric events
    """
    try:
        from app.metrics import get_metrics_collector
        
        logger.debug(f"Recent events requested (limit: {limit})")
        
        if limit > 1000:
            limit = 1000  # Cap the limit to prevent excessive memory usage
        
        metrics_collector = get_metrics_collector()
        events = metrics_collector.get_recent_events(limit)
        
        return {
            "events": events,
            "count": len(events),
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error retrieving recent events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "events_retrieval_failed",
                "message": "Failed to retrieve recent metric events"
            }
        )


@router.get("/metrics/api-calls")
async def get_recent_api_calls(limit: int = 100):
    """
    Get recent API call metrics.
    
    Args:
        limit: Maximum number of API calls to return (default: 100)
        
    Returns:
        dict: Recent API call metrics
    """
    try:
        from app.metrics import get_metrics_collector
        
        logger.debug(f"Recent API calls requested (limit: {limit})")
        
        if limit > 1000:
            limit = 1000  # Cap the limit to prevent excessive memory usage
        
        metrics_collector = get_metrics_collector()
        api_calls = metrics_collector.get_recent_api_calls(limit)
        
        return {
            "api_calls": api_calls,
            "count": len(api_calls),
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error retrieving recent API calls: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "api_calls_retrieval_failed",
                "message": "Failed to retrieve recent API call metrics"
            }
        )


# Health check endpoints
@router.get(
    "/health",
    tags=["health"],
    summary="Basic health check",
    description="""
    Basic service health check endpoint that verifies:
    - Service is running and responsive
    - Configuration is valid
    - Required environment variables are set
    
    This endpoint does not require authentication and can be used for:
    - Load balancer health checks
    - Monitoring system probes
    - Basic service verification
    
    **Status Values:**
    - `healthy`: Service is fully operational
    - `starting`: Service is starting up
    - `degraded`: Service is running but has issues
    - `unhealthy`: Service has critical problems
    """,
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "ultravox-twilio-integration",
                        "version": "1.0.0",
                        "timestamp": "2024-01-01T12:00:00Z",
                        "uptime": {
                            "startup_complete": True,
                            "config_validated": True,
                            "ongoing_calls": 2
                        },
                        "checks": {
                            "configuration": "ok",
                            "ultravox_config": "ok",
                            "twilio_config": "ok"
                        }
                    }
                }
            }
        },
        503: {
            "description": "Service is unhealthy or starting",
            "content": {
                "application/json": {
                    "example": {
                        "status": "starting",
                        "service": "ultravox-twilio-integration",
                        "version": "1.0.0",
                        "timestamp": "2024-01-01T12:00:00Z",
                        "uptime": {
                            "startup_complete": False,
                            "config_validated": True,
                            "ongoing_calls": 0
                        },
                        "checks": {
                            "configuration": "ok",
                            "ultravox_config": "ok",
                            "twilio_config": "ok"
                        }
                    }
                }
            }
        }
    }
)
async def health_check():
    """
    Basic service health check endpoint.
    
    Returns:
        dict: Health status information
    """
    from datetime import datetime, timezone
    from app.main import get_app_state
    
    try:
        logger.debug("Basic health check requested")
        
        # Get application state
        app_state = get_app_state()
        
        # Try to get configuration to ensure basic setup is working
        config_service = get_config_service()
        
        # Validate that required configurations are available
        try:
            ultravox_config = config_service.get_ultravox_config()
            twilio_config = config_service.get_twilio_config()
            
            health_status = {
                "status": "healthy",
                "service": "ultravox-twilio-integration",
                "version": "1.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime": {
                    "startup_complete": app_state.get("startup_complete", False),
                    "config_validated": app_state.get("config_validated", False),
                    "ongoing_calls": len(app_state.get("ongoing_calls", set()))
                },
                "checks": {
                    "configuration": "ok",
                    "ultravox_config": "ok" if ultravox_config.api_key else "missing_api_key",
                    "twilio_config": "ok" if twilio_config.auth_token else "missing_auth_token"
                }
            }
            
            # Determine overall status
            if not app_state.get("startup_complete", False):
                health_status["status"] = "starting"
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content=health_status
                )
            elif any(check != "ok" for check in health_status["checks"].values()):
                health_status["status"] = "degraded"
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content=health_status
                )
            
            return health_status
            
        except Exception as config_error:
            logger.error(f"Configuration error in health check: {str(config_error)}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "service": "ultravox-twilio-integration",
                    "version": "1.0.0",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": "configuration_error",
                    "message": "Service configuration is invalid or missing"
                }
            )
            
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "ultravox-twilio-integration",
                "version": "1.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "health_check_failed",
                "message": "Health check encountered an unexpected error"
            }
        )


@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check endpoint that verifies external service connectivity.
    
    Returns:
        dict: Detailed health status with external service checks
    """
    from datetime import datetime, timezone
    from app.main import get_app_state
    from app.services.http_client_service import HTTPClientService
    
    try:
        logger.debug("Detailed health check requested")
        
        # Get application state
        app_state = get_app_state()
        
        # Get configuration
        config_service = get_config_service()
        
        health_status = {
            "status": "healthy",
            "service": "ultravox-twilio-integration",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime": {
                "startup_complete": app_state.get("startup_complete", False),
                "config_validated": app_state.get("config_validated", False),
                "ongoing_calls": len(app_state.get("ongoing_calls", set()))
            },
            "checks": {
                "configuration": "ok",
                "ultravox_api": "unknown",
                "twilio_api": "unknown"
            }
        }
        
        # Check configuration
        try:
            ultravox_config = config_service.get_ultravox_config()
            twilio_config = config_service.get_twilio_config()
            
            health_status["checks"]["ultravox_config"] = "ok" if ultravox_config.api_key else "missing_api_key"
            health_status["checks"]["twilio_config"] = "ok" if twilio_config.auth_token else "missing_auth_token"
            
        except Exception as config_error:
            health_status["checks"]["configuration"] = "error"
            health_status["status"] = "unhealthy"
            logger.error(f"Configuration error in detailed health check: {str(config_error)}")
        
        # Check external services if configuration is valid
        if health_status["checks"]["configuration"] == "ok":
            http_client = HTTPClientService()
            
            try:
                # Check Ultravox API connectivity
                try:
                    # Make a simple request to check connectivity - use a lightweight endpoint
                    await http_client.make_ultravox_request(
                        method="GET",
                        endpoint="api/agents",  # List agents endpoint for connectivity check
                        api_key=ultravox_config.api_key,
                        base_url=ultravox_config.base_url
                    )
                    health_status["checks"]["ultravox_api"] = "ok"
                    logger.debug("Ultravox API connectivity check passed")
                    
                except AuthenticationError:
                    health_status["checks"]["ultravox_api"] = "auth_error"
                    health_status["status"] = "degraded"
                    logger.warning("Ultravox API connectivity check failed: authentication error")
                    
                except (NetworkError, TimeoutError) as connectivity_error:
                    health_status["checks"]["ultravox_api"] = "connectivity_error"
                    health_status["status"] = "degraded"
                    logger.warning(f"Ultravox API connectivity check failed: {str(connectivity_error)}")
                    
                except Exception as ultravox_error:
                    health_status["checks"]["ultravox_api"] = "error"
                    health_status["status"] = "degraded"
                    logger.warning(f"Ultravox API connectivity check failed: {str(ultravox_error)}")
                
                # Check Twilio API connectivity
                try:
                    # Make a simple request to check Twilio connectivity - get account info
                    await http_client.make_twilio_request(
                        method="GET",
                        endpoint=f"2010-04-01/Accounts/{twilio_config.account_sid}.json",
                        account_sid=twilio_config.account_sid,
                        auth_token=twilio_config.auth_token
                    )
                    health_status["checks"]["twilio_api"] = "ok"
                    logger.debug("Twilio API connectivity check passed")
                    
                except AuthenticationError:
                    health_status["checks"]["twilio_api"] = "auth_error"
                    health_status["status"] = "degraded"
                    logger.warning("Twilio API connectivity check failed: authentication error")
                    
                except (NetworkError, TimeoutError) as connectivity_error:
                    health_status["checks"]["twilio_api"] = "connectivity_error"
                    health_status["status"] = "degraded"
                    logger.warning(f"Twilio API connectivity check failed: {str(connectivity_error)}")
                    
                except Exception as twilio_error:
                    health_status["checks"]["twilio_api"] = "error"
                    health_status["status"] = "degraded"
                    logger.warning(f"Twilio API connectivity check failed: {str(twilio_error)}")
                
            finally:
                await http_client.close()
        
        # Determine final status
        if not app_state.get("startup_complete", False):
            health_status["status"] = "starting"
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif health_status["status"] == "unhealthy":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif health_status["status"] == "degraded":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_200_OK
        
        return JSONResponse(
            status_code=status_code,
            content=health_status
        )
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "ultravox-twilio-integration",
                "version": "1.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "health_check_failed",
                "message": "Detailed health check encountered an unexpected error"
            }
        )