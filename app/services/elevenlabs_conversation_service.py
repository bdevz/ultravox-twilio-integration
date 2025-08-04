"""
ElevenLabs Conversation Service for managing conversations and phone call integration.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import uuid4

from app.models.elevenlabs import (
    ElevenLabsConversation,
    ConversationStatus,
    ElevenLabsConfig,
    ElevenLabsConversationalCallRequest
)
from app.models.call import CallResult, CallStatus
from app.services.elevenlabs_client import ElevenLabsHTTPClient
from app.exceptions.elevenlabs_exceptions import (
    ElevenLabsAPIError,
    ConversationError,
    ConversationNotFoundError,
    ConversationCreationError,
    PhoneCallInitiationError
)
from app.logging_config import LoggerMixin, get_correlation_id

logger = logging.getLogger(__name__)


class ElevenLabsConversationService(LoggerMixin):
    """Service for managing ElevenLabs conversations and phone call integration."""
    
    def __init__(self, config: ElevenLabsConfig):
        """
        Initialize ElevenLabs Conversation Service.
        
        Args:
            config: ElevenLabs configuration
        """
        self.config = config
        self._active_conversations: Dict[str, ElevenLabsConversation] = {}
    
    async def create_conversation(self, agent_id: str) -> ElevenLabsConversation:
        """
        Create a new conversation with an agent.
        
        Args:
            agent_id: Agent ID to create conversation with
            
        Returns:
            ElevenLabsConversation: Created conversation
            
        Raises:
            ConversationCreationError: If conversation creation fails
        """
        correlation_id = get_correlation_id()
        
        try:
            self.logger.info(
                f"Creating conversation with agent: {agent_id}",
                extra={
                    "agent_id": agent_id,
                    "correlation_id": correlation_id
                }
            )
            
            # Create conversation via ElevenLabs API
            conversation_data = await self._create_conversation_api(agent_id)
            
            # Create conversation model
            conversation = ElevenLabsConversation(
                id=conversation_data["id"],
                agent_id=agent_id,
                status=ConversationStatus.CREATED,
                created_at=datetime.now(timezone.utc),
                metadata={"api_data": conversation_data}
            )
            
            # Track active conversation
            self._active_conversations[conversation.id] = conversation
            
            self.logger.info(
                f"Successfully created conversation: {conversation.id}",
                extra={
                    "conversation_id": conversation.id,
                    "agent_id": agent_id,
                    "correlation_id": correlation_id
                }
            )
            
            return conversation
            
        except ElevenLabsAPIError as e:
            self.logger.error(
                f"ElevenLabs API error creating conversation: {str(e)}",
                extra={
                    "agent_id": agent_id,
                    "correlation_id": correlation_id
                },
                exc_info=True
            )
            raise ConversationCreationError(str(e), agent_id=agent_id)
        except Exception as e:
            self.logger.error(
                f"Unexpected error creating conversation: {str(e)}",
                extra={
                    "agent_id": agent_id,
                    "correlation_id": correlation_id
                },
                exc_info=True
            )
            raise ConversationCreationError(f"Unexpected error: {str(e)}", agent_id=agent_id)
    
    async def start_phone_call(
        self, 
        conversation_id: str, 
        phone_number: str
    ) -> CallResult:
        """
        Start a phone conversation.
        
        Args:
            conversation_id: Conversation ID to start phone call for
            phone_number: Phone number to call
            
        Returns:
            CallResult: Call result information
            
        Raises:
            ConversationNotFoundError: If conversation is not found
            PhoneCallInitiationError: If phone call initiation fails
        """
        correlation_id = get_correlation_id()
        
        try:
            self.logger.info(
                f"Starting phone call for conversation: {conversation_id}",
                extra={
                    "conversation_id": conversation_id,
                    "phone_number": phone_number,
                    "correlation_id": correlation_id
                }
            )
            
            # Get conversation
            conversation = await self.get_conversation_status(conversation_id)
            
            # Start phone call via ElevenLabs API
            call_data = await self._start_phone_call_api(conversation_id, phone_number)
            
            # Update conversation status
            conversation.status = ConversationStatus.ACTIVE
            conversation.started_at = datetime.now(timezone.utc)
            conversation.phone_number = phone_number
            self._active_conversations[conversation_id] = conversation
            
            # Create call result
            call_result = CallResult(
                call_sid=call_data.get("call_sid", f"elevenlabs_{conversation_id}"),
                join_url="",  # ElevenLabs handles the connection internally
                status=CallStatus.INITIATED,
                created_at=datetime.now(timezone.utc),
                agent_id=conversation.agent_id,
                phone_number=phone_number
            )
            
            self.logger.info(
                f"Successfully started phone call: {call_result.call_sid}",
                extra={
                    "conversation_id": conversation_id,
                    "call_sid": call_result.call_sid,
                    "phone_number": phone_number,
                    "correlation_id": correlation_id
                }
            )
            
            return call_result
            
        except ConversationNotFoundError:
            raise
        except ElevenLabsAPIError as e:
            self.logger.error(
                f"ElevenLabs API error starting phone call: {str(e)}",
                extra={
                    "conversation_id": conversation_id,
                    "phone_number": phone_number,
                    "correlation_id": correlation_id
                },
                exc_info=True
            )
            raise PhoneCallInitiationError(
                str(e), 
                conversation_id=conversation_id,
                phone_number=phone_number
            )
        except Exception as e:
            self.logger.error(
                f"Unexpected error starting phone call: {str(e)}",
                extra={
                    "conversation_id": conversation_id,
                    "phone_number": phone_number,
                    "correlation_id": correlation_id
                },
                exc_info=True
            )
            raise PhoneCallInitiationError(
                f"Unexpected error: {str(e)}", 
                conversation_id=conversation_id,
                phone_number=phone_number
            )
    
    async def get_conversation_status(self, conversation_id: str) -> ElevenLabsConversation:
        """
        Get current conversation status.
        
        Args:
            conversation_id: Conversation ID to get status for
            
        Returns:
            ElevenLabsConversation: Conversation status
            
        Raises:
            ConversationNotFoundError: If conversation is not found
        """
        correlation_id = get_correlation_id()
        
        try:
            # Check local cache first
            if conversation_id in self._active_conversations:
                conversation = self._active_conversations[conversation_id]
                
                # Refresh status from API if conversation is active
                if conversation.is_active:
                    try:
                        status_data = await self._get_conversation_status_api(conversation_id)
                        conversation.status = ConversationStatus(status_data.get("status", "active"))
                        conversation.metadata.update(status_data)
                        
                        # Update end time if conversation ended
                        if conversation.status == ConversationStatus.ENDED and not conversation.ended_at:
                            conversation.ended_at = datetime.now(timezone.utc)
                            
                    except ElevenLabsAPIError as e:
                        self.logger.warning(
                            f"Failed to refresh conversation status: {str(e)}",
                            extra={
                                "conversation_id": conversation_id,
                                "correlation_id": correlation_id
                            }
                        )
                
                return conversation
            
            # Fetch from API
            self.logger.info(
                f"Fetching conversation status from API: {conversation_id}",
                extra={
                    "conversation_id": conversation_id,
                    "correlation_id": correlation_id
                }
            )
            
            status_data = await self._get_conversation_status_api(conversation_id)
            
            # Create conversation model from API data
            conversation = ElevenLabsConversation(
                id=conversation_id,
                agent_id=status_data.get("agent_id", "unknown"),
                status=ConversationStatus(status_data.get("status", "created")),
                created_at=datetime.fromisoformat(
                    status_data.get("created_at", datetime.now(timezone.utc).isoformat())
                ),
                started_at=datetime.fromisoformat(status_data["started_at"]) if status_data.get("started_at") else None,
                ended_at=datetime.fromisoformat(status_data["ended_at"]) if status_data.get("ended_at") else None,
                phone_number=status_data.get("phone_number"),
                metadata=status_data
            )
            
            # Cache the conversation
            self._active_conversations[conversation_id] = conversation
            
            return conversation
            
        except ConversationNotFoundError:
            raise
        except ElevenLabsAPIError as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise ConversationNotFoundError(conversation_id)
            raise ConversationError(f"Failed to get conversation status: {str(e)}")
        except Exception as e:
            self.logger.error(
                f"Unexpected error getting conversation status: {str(e)}",
                extra={
                    "conversation_id": conversation_id,
                    "correlation_id": correlation_id
                },
                exc_info=True
            )
            raise ConversationError(f"Unexpected error: {str(e)}")
    
    async def end_conversation(self, conversation_id: str) -> bool:
        """
        End conversation and cleanup resources.
        
        Args:
            conversation_id: Conversation ID to end
            
        Returns:
            bool: True if conversation was ended successfully
            
        Raises:
            ConversationNotFoundError: If conversation is not found
        """
        correlation_id = get_correlation_id()
        
        try:
            self.logger.info(
                f"Ending conversation: {conversation_id}",
                extra={
                    "conversation_id": conversation_id,
                    "correlation_id": correlation_id
                }
            )
            
            # End conversation via API
            await self._end_conversation_api(conversation_id)
            
            # Update local state
            if conversation_id in self._active_conversations:
                conversation = self._active_conversations[conversation_id]
                conversation.status = ConversationStatus.ENDED
                conversation.ended_at = datetime.now(timezone.utc)
                
                # Remove from active conversations after a delay to allow status queries
                asyncio.create_task(self._cleanup_conversation_later(conversation_id))
            
            self.logger.info(
                f"Successfully ended conversation: {conversation_id}",
                extra={
                    "conversation_id": conversation_id,
                    "correlation_id": correlation_id
                }
            )
            
            return True
            
        except ConversationNotFoundError:
            raise
        except ElevenLabsAPIError as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise ConversationNotFoundError(conversation_id)
            raise ConversationError(f"Failed to end conversation: {str(e)}")
        except Exception as e:
            self.logger.error(
                f"Unexpected error ending conversation: {str(e)}",
                extra={
                    "conversation_id": conversation_id,
                    "correlation_id": correlation_id
                },
                exc_info=True
            )
            raise ConversationError(f"Unexpected error: {str(e)}")
    
    async def _create_conversation_api(self, agent_id: str) -> Dict[str, Any]:
        """Create conversation via ElevenLabs API."""
        async with ElevenLabsHTTPClient(self.config) as client:
            payload = {"agent_id": agent_id}
            response = await client._make_request(
                method="POST",
                endpoint="v1/convai/conversations",
                data=payload
            )
            return response
    
    async def _start_phone_call_api(
        self, 
        conversation_id: str, 
        phone_number: str
    ) -> Dict[str, Any]:
        """Start phone call via ElevenLabs API."""
        async with ElevenLabsHTTPClient(self.config) as client:
            payload = {"phone_number": phone_number}
            response = await client._make_request(
                method="POST",
                endpoint=f"v1/convai/conversations/{conversation_id}/phone",
                data=payload
            )
            return response
    
    async def _get_conversation_status_api(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation status via ElevenLabs API."""
        async with ElevenLabsHTTPClient(self.config) as client:
            response = await client._make_request(
                method="GET",
                endpoint=f"v1/convai/conversations/{conversation_id}"
            )
            return response
    
    async def _end_conversation_api(self, conversation_id: str) -> None:
        """End conversation via ElevenLabs API."""
        async with ElevenLabsHTTPClient(self.config) as client:
            await client._make_request(
                method="DELETE",
                endpoint=f"v1/convai/conversations/{conversation_id}"
            )
    
    async def _cleanup_conversation_later(self, conversation_id: str, delay_seconds: int = 300):
        """Clean up conversation from cache after delay."""
        await asyncio.sleep(delay_seconds)
        if conversation_id in self._active_conversations:
            del self._active_conversations[conversation_id]
            self.logger.debug(f"Cleaned up conversation from cache: {conversation_id}")
    
    def get_active_conversations(self) -> Dict[str, ElevenLabsConversation]:
        """Get all active conversations."""
        return {
            conv_id: conv 
            for conv_id, conv in self._active_conversations.items() 
            if conv.is_active
        }
    
    def cleanup_ended_conversations(self) -> int:
        """Clean up ended conversations from cache."""
        ended_conversations = [
            conv_id for conv_id, conv in self._active_conversations.items()
            if conv.status == ConversationStatus.ENDED
        ]
        
        for conv_id in ended_conversations:
            del self._active_conversations[conv_id]
        
        if ended_conversations:
            self.logger.info(f"Cleaned up {len(ended_conversations)} ended conversations")
        
        return len(ended_conversations)


# Global conversation service instance
_conversation_service: Optional[ElevenLabsConversationService] = None


def get_elevenlabs_conversation_service(
    config: Optional[ElevenLabsConfig] = None
) -> ElevenLabsConversationService:
    """
    Get the global ElevenLabs conversation service instance.
    
    Args:
        config: ElevenLabs configuration (optional)
        
    Returns:
        ElevenLabsConversationService: The conversation service instance
    """
    global _conversation_service
    if _conversation_service is None:
        if config is None:
            raise ValueError("Config is required for first initialization")
        
        _conversation_service = ElevenLabsConversationService(config)
    
    return _conversation_service