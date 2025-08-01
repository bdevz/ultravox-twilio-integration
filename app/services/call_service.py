"""
Call service for orchestrating calls between Ultravox and Twilio.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from urllib.parse import quote

from app.models.call import CallRequest, CallResult, TwilioCallResult, CallStatus
from app.services.config_service import ConfigService
from app.services.http_client_service import HTTPClientService, HTTPClientError


logger = logging.getLogger(__name__)


class CallServiceError(Exception):
    """Base exception for call service errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class UltravoxCallError(CallServiceError):
    """Exception for Ultravox call-related errors."""
    pass


class TwilioCallError(CallServiceError):
    """Exception for Twilio call-related errors."""
    pass


class CallService:
    """Service for orchestrating calls between Ultravox and Twilio."""
    
    def __init__(self, config_service: ConfigService, http_client: HTTPClientService):
        """
        Initialize call service.
        
        Args:
            config_service: Configuration service instance
            http_client: HTTP client service instance
        """
        self.config_service = config_service
        self.http_client = http_client
    
    async def initiate_call(self, call_request: CallRequest) -> CallResult:
        """
        Initiate a call by getting join URL from Ultravox and creating Twilio call.
        
        Args:
            call_request: Call request details
            
        Returns:
            CallResult: Call result with SID, join URL, and status
            
        Raises:
            CallServiceError: For call orchestration errors
        """
        from app.metrics import record_metric
        from app.logging_config import get_correlation_id
        
        correlation_id = get_correlation_id()
        start_time = datetime.now(timezone.utc)
        call_id = None
        
        try:
            logger.info(
                f"Initiating call for agent {call_request.agent_id} to {call_request.phone_number}",
                extra={
                    "agent_id": call_request.agent_id,
                    "phone_number": call_request.phone_number,
                    "has_template_context": bool(call_request.template_context),
                    "template_context_keys": list(call_request.template_context.keys()) if call_request.template_context else [],
                    "correlation_id": correlation_id
                }
            )
            
            # Record call initiation attempt
            record_metric(
                "call_initiation_attempts_total",
                1,
                tags={"agent_id": call_request.agent_id},
                correlation_id=correlation_id
            )
            
            # Step 1: Get join URL from Ultravox
            logger.debug("Step 1: Getting join URL from Ultravox")
            join_url_start = datetime.now(timezone.utc)
            
            join_url = await self.get_join_url(
                agent_id=call_request.agent_id,
                context=call_request.template_context
            )
            
            join_url_duration = (datetime.now(timezone.utc) - join_url_start).total_seconds()
            record_metric(
                "ultravox_join_url_duration_seconds",
                join_url_duration,
                tags={"agent_id": call_request.agent_id},
                correlation_id=correlation_id
            )
            
            logger.debug(
                f"Successfully obtained join URL from Ultravox",
                extra={
                    "agent_id": call_request.agent_id,
                    "join_url_duration_seconds": round(join_url_duration, 3),
                    "correlation_id": correlation_id
                }
            )
            
            # Step 2: Create Twilio call
            logger.debug("Step 2: Creating Twilio call")
            twilio_call_start = datetime.now(timezone.utc)
            
            twilio_result = await self.create_twilio_call(
                join_url=join_url,
                phone_number=call_request.phone_number
            )
            
            twilio_call_duration = (datetime.now(timezone.utc) - twilio_call_start).total_seconds()
            record_metric(
                "twilio_call_creation_duration_seconds",
                twilio_call_duration,
                tags={"phone_number": call_request.phone_number},
                correlation_id=correlation_id
            )
            
            logger.debug(
                f"Successfully created Twilio call",
                extra={
                    "call_sid": twilio_result.sid,
                    "phone_number": call_request.phone_number,
                    "twilio_call_duration_seconds": round(twilio_call_duration, 3),
                    "correlation_id": correlation_id
                }
            )
            
            # Step 3: Register call for graceful shutdown tracking
            call_id = twilio_result.sid
            try:
                from app.main import register_call
                register_call(call_id)
                logger.debug(f"Registered call for shutdown tracking: {call_id}")
            except ImportError:
                # Handle case where main module isn't available (e.g., in tests)
                logger.debug("Could not register call for shutdown tracking")
            
            # Step 4: Create call result
            call_result = CallResult(
                call_sid=twilio_result.sid,
                join_url=join_url,
                status=CallStatus.INITIATED,
                created_at=datetime.now(timezone.utc),
                agent_id=call_request.agent_id,
                phone_number=call_request.phone_number
            )
            
            # Record successful call initiation metrics
            total_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            record_metric(
                "call_initiation_duration_seconds",
                total_duration,
                tags={
                    "agent_id": call_request.agent_id,
                    "success": "true"
                },
                correlation_id=correlation_id
            )
            
            record_metric(
                "call_initiation_success_total",
                1,
                tags={"agent_id": call_request.agent_id},
                correlation_id=correlation_id
            )
            
            logger.info(
                f"Call initiated successfully: {call_result.call_sid}",
                extra={
                    "call_sid": call_result.call_sid,
                    "agent_id": call_request.agent_id,
                    "phone_number": call_request.phone_number,
                    "total_duration_seconds": round(total_duration, 3),
                    "join_url_duration_seconds": round(join_url_duration, 3),
                    "twilio_call_duration_seconds": round(twilio_call_duration, 3),
                    "correlation_id": correlation_id
                }
            )
            return call_result
            
        except (UltravoxCallError, TwilioCallError) as e:
            # Record failure metrics
            total_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            record_metric(
                "call_initiation_duration_seconds",
                total_duration,
                tags={
                    "agent_id": call_request.agent_id,
                    "success": "false",
                    "error_type": type(e).__name__
                },
                correlation_id=correlation_id
            )
            
            record_metric(
                "call_initiation_failures_total",
                1,
                tags={
                    "agent_id": call_request.agent_id,
                    "error_type": type(e).__name__
                },
                correlation_id=correlation_id
            )
            
            # If call registration happened but call failed, unregister it
            if call_id:
                try:
                    from app.main import unregister_call
                    unregister_call(call_id)
                    logger.debug(f"Unregistered failed call: {call_id}")
                except ImportError:
                    pass
            
            logger.error(
                f"Call initiation failed: {str(e)}",
                extra={
                    "agent_id": call_request.agent_id,
                    "phone_number": call_request.phone_number,
                    "error_type": type(e).__name__,
                    "total_duration_seconds": round(total_duration, 3),
                    "correlation_id": correlation_id
                }
            )
            raise
            
        except Exception as e:
            # Record failure metrics
            total_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            record_metric(
                "call_initiation_failures_total",
                1,
                tags={
                    "agent_id": call_request.agent_id,
                    "error_type": "UnexpectedError"
                },
                correlation_id=correlation_id
            )
            
            # If call registration happened but call failed, unregister it
            if call_id:
                try:
                    from app.main import unregister_call
                    unregister_call(call_id)
                    logger.debug(f"Unregistered failed call: {call_id}")
                except ImportError:
                    pass
            
            logger.error(
                f"Unexpected error initiating call: {str(e)}",
                extra={
                    "agent_id": call_request.agent_id,
                    "phone_number": call_request.phone_number,
                    "error_type": type(e).__name__,
                    "total_duration_seconds": round(total_duration, 3),
                    "correlation_id": correlation_id
                },
                exc_info=True
            )
            raise CallServiceError(
                f"Failed to initiate call: {str(e)}",
                details={
                    'agent_id': call_request.agent_id,
                    'phone_number': call_request.phone_number,
                    'error_type': type(e).__name__
                }
            )
    
    async def get_join_url(self, agent_id: str, context: Dict[str, Any]) -> str:
        """
        Get join URL from Ultravox agent calls API.
        
        Args:
            agent_id: Ultravox agent ID
            context: Template context variables
            
        Returns:
            str: WebSocket join URL for streaming
            
        Raises:
            UltravoxCallError: For Ultravox API errors
        """
        try:
            logger.debug(f"Getting join URL for agent {agent_id}")
            
            # Get Ultravox configuration
            ultravox_config = self.config_service.get_ultravox_config()
            twilio_config = self.config_service.get_twilio_config()
            
            # Prepare request payload
            payload = {
                "medium": {
                    "twilio": {
                        "phoneNumber": twilio_config.phone_number
                    }
                }
            }
            
            # Add template context if provided
            if context:
                payload["templateContext"] = context
            
            # Make API call to Ultravox
            endpoint = f"api/agents/{agent_id}/calls"
            response = await self.http_client.make_ultravox_request(
                method="POST",
                endpoint=endpoint,
                data=payload,
                api_key=ultravox_config.api_key,
                base_url=ultravox_config.base_url
            )
            
            # Extract join URL from response
            join_url = response.get("joinUrl")
            if not join_url:
                raise UltravoxCallError(
                    "No join URL returned from Ultravox API",
                    details={
                        'agent_id': agent_id,
                        'response': response
                    }
                )
            
            logger.debug(f"Successfully obtained join URL for agent {agent_id}")
            return join_url
            
        except HTTPClientError as e:
            logger.error(f"Ultravox API error getting join URL: {e.message}")
            raise UltravoxCallError(
                f"Failed to get join URL from Ultravox: {e.message}",
                details={
                    'agent_id': agent_id,
                    'context': context,
                    'status_code': e.status_code,
                    'api_details': e.details
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error getting join URL: {str(e)}")
            raise UltravoxCallError(
                f"Unexpected error getting join URL: {str(e)}",
                details={
                    'agent_id': agent_id,
                    'context': context,
                    'error_type': type(e).__name__
                }
            )
    
    async def create_twilio_call(self, join_url: str, phone_number: str) -> TwilioCallResult:
        """
        Create Twilio call with TwiML streaming configuration.
        
        Args:
            join_url: WebSocket join URL from Ultravox
            phone_number: Phone number to call
            
        Returns:
            TwilioCallResult: Twilio call result with SID and status
            
        Raises:
            TwilioCallError: For Twilio API errors
        """
        try:
            logger.debug(f"Creating Twilio call to {phone_number}")
            
            # Get Twilio configuration
            twilio_config = self.config_service.get_twilio_config()
            
            # Create TwiML with streaming configuration
            twiml = self._create_streaming_twiml(join_url)
            
            # Prepare Twilio API request
            payload = {
                "To": phone_number,
                "From": twilio_config.phone_number,
                "Twiml": twiml
            }
            
            # Make API call to Twilio
            endpoint = f"2010-04-01/Accounts/{twilio_config.account_sid}/Calls.json"
            response = await self.http_client.make_twilio_request(
                method="POST",
                endpoint=endpoint,
                data=payload,
                account_sid=twilio_config.account_sid,
                auth_token=twilio_config.auth_token
            )
            
            # Create Twilio call result
            twilio_result = TwilioCallResult(
                sid=response["sid"],
                status=response["status"],
                from_number=response["from"],
                to_number=response["to"],
                created_at=datetime.now(timezone.utc)
            )
            
            logger.info(f"Twilio call created successfully: {twilio_result.sid}")
            return twilio_result
            
        except HTTPClientError as e:
            logger.error(f"Twilio API error creating call: {e.message}")
            raise TwilioCallError(
                f"Failed to create Twilio call: {e.message}",
                details={
                    'phone_number': phone_number,
                    'join_url': join_url,
                    'status_code': e.status_code,
                    'api_details': e.details
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error creating Twilio call: {str(e)}")
            raise TwilioCallError(
                f"Unexpected error creating Twilio call: {str(e)}",
                details={
                    'phone_number': phone_number,
                    'join_url': join_url,
                    'error_type': type(e).__name__
                }
            )
    
    def _create_streaming_twiml(self, join_url: str) -> str:
        """
        Create TwiML with streaming configuration for Ultravox integration.
        
        Args:
            join_url: WebSocket join URL from Ultravox
            
        Returns:
            str: TwiML XML string
        """
        # For TwiML, we don't need to URL encode the join URL
        # Twilio handles the URL properly in the Stream element
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{join_url}" />
    </Connect>
</Response>"""
        
        logger.debug("Created TwiML for streaming configuration")
        return twiml
    
    def complete_call(self, call_sid: str):
        """
        Mark a call as completed and unregister it from tracking.
        
        Args:
            call_sid: Twilio call SID
        """
        try:
            from app.main import unregister_call
            unregister_call(call_sid)
            logger.info(f"Call completed and unregistered: {call_sid}")
        except ImportError:
            # Handle case where main module isn't available (e.g., in tests)
            logger.debug("Could not unregister call from shutdown tracking")


# Global call service instance
_call_service: Optional[CallService] = None


def get_call_service(
    config_service: Optional[ConfigService] = None,
    http_client: Optional[HTTPClientService] = None
) -> CallService:
    """
    Get the global call service instance.
    
    Args:
        config_service: Configuration service instance (optional)
        http_client: HTTP client service instance (optional)
        
    Returns:
        CallService: The call service instance
    """
    global _call_service
    if _call_service is None:
        from app.services.config_service import get_config_service
        from app.services.http_client_service import HTTPClientService
        
        if config_service is None:
            config_service = get_config_service()
        if http_client is None:
            http_client = HTTPClientService()
        
        _call_service = CallService(config_service, http_client)
    
    return _call_service