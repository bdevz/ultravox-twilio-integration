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

# ElevenLabs imports (optional)
try:
    from app.models.elevenlabs import (
        ElevenLabsCallRequest,
        ElevenLabsConversationalCallRequest,
        ElevenLabsCallResult,
        UnifiedCallRequest
    )
    from app.services.elevenlabs_conversation_service import ElevenLabsConversationService
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False


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
    
    def __init__(
        self, 
        config_service: ConfigService, 
        http_client: HTTPClientService,
        elevenlabs_conversation_service: Optional['ElevenLabsConversationService'] = None
    ):
        """
        Initialize call service.
        
        Args:
            config_service: Configuration service instance
            http_client: HTTP client service instance
            elevenlabs_conversation_service: ElevenLabs conversation service (optional)
        """
        self.config_service = config_service
        self.http_client = http_client
        self.elevenlabs_conversation_service = elevenlabs_conversation_service
    
    async def initiate_unified_call(
        self, 
        agent_id: str, 
        phone_number: str, 
        agent_type: str,
        template_context: Optional[Dict[str, Any]] = None
    ) -> CallResult:
        """
        Route call based on agent type.
        
        Args:
            agent_id: Agent ID to use for the call
            phone_number: Phone number to call
            agent_type: Type of agent ("ultravox" or "elevenlabs")
            template_context: Template context variables
            
        Returns:
            CallResult: Call result
            
        Raises:
            CallServiceError: For call orchestration errors
        """
        correlation_id = get_correlation_id()
        
        self.logger.info(
            f"Initiating unified call with {agent_type} agent",
            extra={
                "agent_id": agent_id,
                "agent_type": agent_type,
                "phone_number": phone_number,
                "correlation_id": correlation_id
            }
        )
        
        if agent_type == "ultravox":
            # Create Ultravox call request
            call_request = CallRequest(
                agent_id=agent_id,
                phone_number=phone_number,
                template_context=template_context or {}
            )
            return await self.initiate_call(call_request)
            
        elif agent_type == "elevenlabs":
            if not ELEVENLABS_AVAILABLE or not self.elevenlabs_conversation_service:
                raise CallServiceError(
                    "ElevenLabs conversational AI is not available",
                    details={"agent_type": agent_type}
                )
            
            # Create ElevenLabs conversational call
            elevenlabs_request = ElevenLabsConversationalCallRequest(
                phone_number=phone_number,
                agent_id=agent_id,
                template_context=template_context or {}
            )
            return await self._initiate_elevenlabs_conversational_call(elevenlabs_request)
            
        else:
            raise CallServiceError(
                f"Unknown agent type: {agent_type}",
                details={"agent_type": agent_type, "supported_types": ["ultravox", "elevenlabs"]}
            )

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
            
            # Prepare request payload (Ultravox expects empty twilio object)
            payload = {
                "medium": {
                    "twilio": {}
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
    
    async def create_elevenlabs_call(self, elevenlabs_request, audio_file_path: str) -> CallResult:
        """
        Create an ElevenLabs call by uploading audio and creating Twilio call.
        
        Args:
            elevenlabs_request: ElevenLabs call request
            audio_file_path: Path to generated audio file
            
        Returns:
            CallResult: Call result with SID and status
            
        Raises:
            CallServiceError: For call creation errors
        """
        from app.metrics import record_metric
        from app.logging_config import get_correlation_id
        
        correlation_id = get_correlation_id()
        start_time = datetime.now(timezone.utc)
        call_id = None
        
        try:
            logger.info(
                f"Creating ElevenLabs call to {elevenlabs_request.phone_number}",
                extra={
                    "phone_number": elevenlabs_request.phone_number,
                    "voice_id": elevenlabs_request.voice_id,
                    "text_length": len(elevenlabs_request.text),
                    "correlation_id": correlation_id
                }
            )
            
            # Record call initiation attempt
            record_metric(
                "elevenlabs_call_attempts_total",
                1,
                tags={"voice_id": elevenlabs_request.voice_id},
                correlation_id=correlation_id
            )
            
            # Step 1: Upload audio to a publicly accessible location
            # For now, we'll use a simple approach with Twilio's media capabilities
            logger.debug("Step 1: Creating Twilio call with audio playback")
            twilio_call_start = datetime.now(timezone.utc)
            
            # Create TwiML that plays the audio file
            # Note: In production, you'd want to upload the audio to a CDN or cloud storage
            # For now, we'll create a simple playback TwiML
            twiml = self._create_audio_playback_twiml(audio_file_path)
            
            # Get Twilio configuration
            twilio_config = self.config_service.get_twilio_config()
            
            # Prepare Twilio API request
            payload = {
                "To": elevenlabs_request.phone_number,
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
            
            twilio_call_duration = (datetime.now(timezone.utc) - twilio_call_start).total_seconds()
            record_metric(
                "twilio_elevenlabs_call_duration_seconds",
                twilio_call_duration,
                tags={"phone_number": elevenlabs_request.phone_number},
                correlation_id=correlation_id
            )
            
            logger.debug(
                f"Successfully created ElevenLabs Twilio call",
                extra={
                    "call_sid": response["sid"],
                    "phone_number": elevenlabs_request.phone_number,
                    "twilio_call_duration_seconds": round(twilio_call_duration, 3),
                    "correlation_id": correlation_id
                }
            )
            
            # Step 2: Register call for graceful shutdown tracking
            call_id = response["sid"]
            try:
                from app.main import register_call
                register_call(call_id)
                logger.debug(f"Registered ElevenLabs call for shutdown tracking: {call_id}")
            except ImportError:
                logger.debug("Could not register call for shutdown tracking")
            
            # Step 3: Create call result
            call_result = CallResult(
                call_sid=response["sid"],
                join_url=None,  # ElevenLabs calls don't have join URLs
                status=CallStatus.INITIATED,
                created_at=datetime.now(timezone.utc),
                agent_id=f"elevenlabs_{elevenlabs_request.voice_id}",
                phone_number=elevenlabs_request.phone_number
            )
            
            # Record successful call initiation metrics
            total_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            record_metric(
                "elevenlabs_call_success_total",
                1,
                tags={"voice_id": elevenlabs_request.voice_id},
                correlation_id=correlation_id
            )
            
            logger.info(
                f"ElevenLabs call created successfully: {call_result.call_sid}",
                extra={
                    "call_sid": call_result.call_sid,
                    "voice_id": elevenlabs_request.voice_id,
                    "phone_number": elevenlabs_request.phone_number,
                    "total_duration_seconds": round(total_duration, 3),
                    "correlation_id": correlation_id
                }
            )
            return call_result
            
        except Exception as e:
            # Record failure metrics
            total_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            record_metric(
                "elevenlabs_call_failures_total",
                1,
                tags={
                    "voice_id": elevenlabs_request.voice_id,
                    "error_type": type(e).__name__
                },
                correlation_id=correlation_id
            )
            
            # If call registration happened but call failed, unregister it
            if call_id:
                try:
                    from app.main import unregister_call
                    unregister_call(call_id)
                    logger.debug(f"Unregistered failed ElevenLabs call: {call_id}")
                except ImportError:
                    pass
            
            logger.error(
                f"ElevenLabs call creation failed: {str(e)}",
                extra={
                    "voice_id": elevenlabs_request.voice_id,
                    "phone_number": elevenlabs_request.phone_number,
                    "error_type": type(e).__name__,
                    "total_duration_seconds": round(total_duration, 3),
                    "correlation_id": correlation_id
                },
                exc_info=True
            )
            raise CallServiceError(
                f"Failed to create ElevenLabs call: {str(e)}",
                details={
                    'voice_id': elevenlabs_request.voice_id,
                    'phone_number': elevenlabs_request.phone_number,
                    'error_type': type(e).__name__
                }
            )
    
    def _create_audio_playback_twiml(self, audio_file_path: str) -> str:
        """
        Create TwiML for playing an audio file.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            str: TwiML XML string
            
        Note:
            In production, you should upload the audio file to a publicly accessible URL
            (like AWS S3, Google Cloud Storage, etc.) and use that URL in the Play element.
            For development/testing, this creates a placeholder TwiML.
        """
        # For now, create a simple Say element as a fallback
        # In production, you'd replace this with a proper audio URL
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">This is a placeholder for ElevenLabs generated audio. In production, this would play the generated speech.</Say>
    <Hangup/>
</Response>"""
        
        logger.debug("Created TwiML for audio playback (placeholder)")
        logger.warning(
            "Audio playback TwiML is using placeholder. "
            "In production, upload audio to public URL and use <Play> element."
        )
        return twiml

    async def _initiate_elevenlabs_conversational_call(
        self, 
        elevenlabs_request: 'ElevenLabsConversationalCallRequest'
    ) -> CallResult:
        """
        Handle ElevenLabs conversational call flow.
        
        Args:
            elevenlabs_request: ElevenLabs conversational call request
            
        Returns:
            CallResult: Call result
            
        Raises:
            CallServiceError: For call orchestration errors
        """
        from app.metrics import record_metric
        from app.logging_config import get_correlation_id
        
        correlation_id = get_correlation_id()
        start_time = datetime.now(timezone.utc)
        conversation_id = None
        call_id = None
        
        try:
            logger.info(
                f"Initiating ElevenLabs conversational call to {elevenlabs_request.phone_number}",
                extra={
                    "agent_id": elevenlabs_request.agent_id,
                    "phone_number": elevenlabs_request.phone_number,
                    "correlation_id": correlation_id
                }
            )
            
            # Record call initiation attempt
            record_metric(
                "elevenlabs_conversational_call_attempts_total",
                1,
                tags={"agent_id": elevenlabs_request.agent_id},
                correlation_id=correlation_id
            )
            
            # Step 1: Create conversation
            logger.debug("Step 1: Creating ElevenLabs conversation")
            conversation_start = datetime.now(timezone.utc)
            
            conversation = await self.elevenlabs_conversation_service.create_conversation(
                elevenlabs_request.agent_id
            )
            conversation_id = conversation.id
            
            conversation_duration = (datetime.now(timezone.utc) - conversation_start).total_seconds()
            record_metric(
                "elevenlabs_conversation_creation_duration_seconds",
                conversation_duration,
                tags={"agent_id": elevenlabs_request.agent_id},
                correlation_id=correlation_id
            )
            
            logger.debug(
                f"Successfully created conversation: {conversation_id}",
                extra={
                    "conversation_id": conversation_id,
                    "agent_id": elevenlabs_request.agent_id,
                    "conversation_duration_seconds": round(conversation_duration, 3),
                    "correlation_id": correlation_id
                }
            )
            
            # Step 2: Start phone call
            logger.debug("Step 2: Starting ElevenLabs phone call")
            phone_call_start = datetime.now(timezone.utc)
            
            call_result = await self.elevenlabs_conversation_service.start_phone_call(
                conversation_id,
                elevenlabs_request.phone_number
            )
            call_id = call_result.call_sid
            
            phone_call_duration = (datetime.now(timezone.utc) - phone_call_start).total_seconds()
            record_metric(
                "elevenlabs_phone_call_initiation_duration_seconds",
                phone_call_duration,
                tags={"agent_id": elevenlabs_request.agent_id},
                correlation_id=correlation_id
            )
            
            logger.debug(
                f"Successfully started phone call: {call_id}",
                extra={
                    "call_sid": call_id,
                    "conversation_id": conversation_id,
                    "phone_call_duration_seconds": round(phone_call_duration, 3),
                    "correlation_id": correlation_id
                }
            )
            
            # Step 3: Register call for graceful shutdown tracking
            try:
                from app.main import register_call
                register_call(call_id)
                logger.debug(f"Registered ElevenLabs conversational call for shutdown tracking: {call_id}")
            except ImportError:
                logger.debug("Could not register call for shutdown tracking")
            
            # Step 4: Create enhanced call result
            enhanced_call_result = CallResult(
                call_sid=call_result.call_sid,
                join_url="",  # ElevenLabs handles connection internally
                status=call_result.status,
                created_at=call_result.created_at,
                agent_id=elevenlabs_request.agent_id,
                phone_number=elevenlabs_request.phone_number
            )
            
            # Record successful call initiation metrics
            total_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            record_metric(
                "elevenlabs_conversational_call_success_total",
                1,
                tags={"agent_id": elevenlabs_request.agent_id},
                correlation_id=correlation_id
            )
            
            record_metric(
                "elevenlabs_conversational_call_duration_seconds",
                total_duration,
                tags={
                    "agent_id": elevenlabs_request.agent_id,
                    "success": "true"
                },
                correlation_id=correlation_id
            )
            
            logger.info(
                f"ElevenLabs conversational call initiated successfully: {call_id}",
                extra={
                    "call_sid": call_id,
                    "conversation_id": conversation_id,
                    "agent_id": elevenlabs_request.agent_id,
                    "phone_number": elevenlabs_request.phone_number,
                    "total_duration_seconds": round(total_duration, 3),
                    "conversation_duration_seconds": round(conversation_duration, 3),
                    "phone_call_duration_seconds": round(phone_call_duration, 3),
                    "correlation_id": correlation_id
                }
            )
            
            return enhanced_call_result
            
        except Exception as e:
            # Record failure metrics
            total_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            record_metric(
                "elevenlabs_conversational_call_failures_total",
                1,
                tags={
                    "agent_id": elevenlabs_request.agent_id,
                    "error_type": type(e).__name__
                },
                correlation_id=correlation_id
            )
            
            record_metric(
                "elevenlabs_conversational_call_duration_seconds",
                total_duration,
                tags={
                    "agent_id": elevenlabs_request.agent_id,
                    "success": "false",
                    "error_type": type(e).__name__
                },
                correlation_id=correlation_id
            )
            
            # Cleanup on failure
            if conversation_id:
                try:
                    await self.elevenlabs_conversation_service.end_conversation(conversation_id)
                    logger.debug(f"Cleaned up failed conversation: {conversation_id}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup conversation {conversation_id}: {cleanup_error}")
            
            if call_id:
                try:
                    from app.main import unregister_call
                    unregister_call(call_id)
                    logger.debug(f"Unregistered failed ElevenLabs call: {call_id}")
                except ImportError:
                    pass
            
            logger.error(
                f"ElevenLabs conversational call initiation failed: {str(e)}",
                extra={
                    "agent_id": elevenlabs_request.agent_id,
                    "phone_number": elevenlabs_request.phone_number,
                    "conversation_id": conversation_id,
                    "error_type": type(e).__name__,
                    "total_duration_seconds": round(total_duration, 3),
                    "correlation_id": correlation_id
                },
                exc_info=True
            )
            
            raise CallServiceError(
                f"Failed to initiate ElevenLabs conversational call: {str(e)}",
                details={
                    'agent_id': elevenlabs_request.agent_id,
                    'phone_number': elevenlabs_request.phone_number,
                    'conversation_id': conversation_id,
                    'error_type': type(e).__name__
                }
            )

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