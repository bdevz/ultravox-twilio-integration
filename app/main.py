"""
FastAPI application entry point for Ultravox-Twilio Integration Service.
"""

import os
import signal
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.error_handlers import register_exception_handlers
from app.middleware import (
    CorrelationIdMiddleware,
    RequestLoggingMiddleware,
    RequestValidationMiddleware,
    SecurityHeadersMiddleware,
    APIKeyValidationMiddleware,
    RateLimitingMiddleware,
    InputSanitizationMiddleware
)
from app.logging_config import configure_logging, get_logger
from app.services.config_service import get_config_service, ConfigurationError
from app.services.http_client_service import close_http_client_service

# Configure logging
configure_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format_type=os.getenv("LOG_FORMAT", "json"),
    log_file=os.getenv("LOG_FILE")
)

logger = get_logger(__name__)

# Global state for tracking ongoing operations
app_state: Dict[str, Any] = {
    "startup_complete": False,
    "shutdown_initiated": False,
    "ongoing_calls": set(),
    "config_validated": False
}

async def startup_sequence():
    """
    Execute application startup sequence with proper error handling.
    
    Raises:
        ConfigurationError: If configuration validation fails
        Exception: For other startup errors
    """
    logger.info("Starting Ultravox-Twilio Integration Service")
    
    try:
        # Step 1: Validate configuration
        logger.info("Validating configuration...")
        config_service = get_config_service()
        
        # Load and validate all configuration
        config = config_service.load_configuration()
        app_state["config_validated"] = True
        
        logger.info("Configuration validated successfully", extra={
            "ultravox_configured": bool(config.ultravox.api_key),
            "twilio_configured": bool(config.twilio.auth_token),
            "debug_mode": config.debug,
            "log_level": config.log_level
        })
        
        # Step 2: Initialize services (if needed)
        logger.info("Initializing services...")
        
        # Step 3: Set up signal handlers for graceful shutdown
        setup_signal_handlers()
        
        # Mark startup as complete
        app_state["startup_complete"] = True
        logger.info("Application startup completed successfully")
        
    except ConfigurationError as e:
        logger.error("Configuration validation failed during startup", extra={
            "error": e.message,
            "details": e.details
        })
        app_state["config_validated"] = False
        raise
    except Exception as e:
        logger.error("Unexpected error during startup", extra={
            "error": str(e)
        })
        app_state["startup_complete"] = False
        raise


async def shutdown_sequence():
    """
    Execute graceful shutdown sequence.
    """
    if app_state["shutdown_initiated"]:
        logger.warning("Shutdown already initiated")
        return
    
    app_state["shutdown_initiated"] = True
    logger.info("Initiating graceful shutdown...")
    
    try:
        # Step 1: Stop accepting new requests (handled by FastAPI)
        logger.info("Stopping acceptance of new requests")
        
        # Step 2: Wait for ongoing calls to complete (with timeout)
        if app_state["ongoing_calls"]:
            logger.info(f"Waiting for {len(app_state['ongoing_calls'])} ongoing calls to complete...")
            
            # Wait up to 30 seconds for calls to complete
            timeout = 30
            start_time = asyncio.get_event_loop().time()
            
            while app_state["ongoing_calls"] and (asyncio.get_event_loop().time() - start_time) < timeout:
                await asyncio.sleep(1)
            
            if app_state["ongoing_calls"]:
                logger.warning(f"Shutdown timeout reached. {len(app_state['ongoing_calls'])} calls still ongoing")
            else:
                logger.info("All ongoing calls completed successfully")
        
        # Step 3: Close HTTP client connections
        logger.info("Closing HTTP client connections...")
        await close_http_client_service()
        
        # Step 4: Final cleanup
        logger.info("Performing final cleanup...")
        app_state.clear()
        
        logger.info("Graceful shutdown completed")
        
    except Exception as e:
        logger.error("Error during shutdown sequence", extra={
            "error": str(e)
        })


def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        # Create a task to run the shutdown sequence
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(shutdown_sequence())
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager for startup and shutdown.
    
    Args:
        app: FastAPI application instance
    """
    # Startup
    try:
        await startup_sequence()
        yield
    except Exception as e:
        logger.error("Failed to start application", extra={"error": str(e)})
        raise
    finally:
        # Shutdown
        await shutdown_sequence()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="Ultravox-Twilio Integration Service",
        description="""
        ## Overview
        
        The Ultravox-Twilio Integration Service provides a REST API for creating and managing 
        Ultravox AI agents with Twilio voice integration. This service acts as a bridge between 
        Ultravox's AI capabilities and Twilio's telecommunications infrastructure.
        
        ## Features
        
        - **Agent Management**: Create, update, and manage Ultravox AI agents
        - **Voice Calls**: Initiate phone calls that connect users to AI agents
        - **Template Variables**: Dynamic context injection for personalized conversations
        - **Health Monitoring**: Comprehensive health checks and metrics
        - **Rate Limiting**: Built-in protection against abuse
        - **Security**: API key authentication and input validation
        
        ## Authentication
        
        All API endpoints (except health checks) require API key authentication via the `X-API-Key` header:
        
        ```
        X-API-Key: your-api-key-here
        ```
        
        ## Rate Limits
        
        - 60 requests per minute
        - 1000 requests per hour
        - Burst limit of 10 requests
        
        ## External Services
        
        This service integrates with:
        - **Ultravox API**: For AI agent management and call orchestration
        - **Twilio API**: For voice call initiation and management
        
        ## Support
        
        - [API Documentation](./docs)
        - [Usage Examples](./examples)
        - [Troubleshooting Guide](./troubleshooting)
        """,
        version="1.0.0",
        contact={
            "name": "API Support",
            "url": "https://github.com/your-org/ultravox-twilio-integration",
            "email": "support@yourcompany.com"
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        },
        servers=[
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            },
            {
                "url": "https://api.yourcompany.com",
                "description": "Production server"
            }
        ],
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {
                "name": "agents",
                "description": "Agent management operations. Create, read, update, and list Ultravox AI agents."
            },
            {
                "name": "calls",
                "description": "Call management operations. Initiate voice calls using AI agents."
            },
            {
                "name": "health",
                "description": "Health check endpoints for monitoring service status and connectivity."
            },
            {
                "name": "metrics",
                "description": "Application metrics and performance monitoring endpoints."
            }
        ],
        lifespan=lifespan
    )
    
    # Register exception handlers
    register_exception_handlers(app)
    
    # Add middleware (order matters - first added is outermost)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        RequestLoggingMiddleware,
        log_request_body=os.getenv("LOG_REQUEST_BODY", "false").lower() == "true",
        log_response_body=os.getenv("LOG_RESPONSE_BODY", "false").lower() == "true"
    )
    app.add_middleware(
        RateLimitingMiddleware,
        requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
        requests_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "1000")),
        burst_limit=int(os.getenv("RATE_LIMIT_BURST", "10"))
    )
    app.add_middleware(
        APIKeyValidationMiddleware,
        required_for_paths=["/api/v1/agents", "/api/v1/calls"]
    )
    app.add_middleware(InputSanitizationMiddleware)
    app.add_middleware(
        RequestValidationMiddleware,
        max_content_length=int(os.getenv("MAX_CONTENT_LENGTH", "1048576"))  # 1MB default
    )
    app.add_middleware(CorrelationIdMiddleware)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(router, prefix="/api/v1")
    
    return app


def register_call(call_id: str):
    """
    Register an ongoing call for graceful shutdown tracking.
    
    Args:
        call_id: Unique identifier for the call
    """
    app_state["ongoing_calls"].add(call_id)
    logger.debug(f"Registered ongoing call: {call_id}")


def unregister_call(call_id: str):
    """
    Unregister a completed call.
    
    Args:
        call_id: Unique identifier for the call
    """
    app_state["ongoing_calls"].discard(call_id)
    logger.debug(f"Unregistered call: {call_id}")


def get_app_state() -> Dict[str, Any]:
    """
    Get current application state.
    
    Returns:
        dict: Current application state
    """
    return app_state.copy()

# Create the app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)