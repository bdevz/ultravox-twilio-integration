"""
ElevenLabs HTTP client service for voice synthesis API integration.
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientError, ClientResponseError

from app.models.elevenlabs import (
    ElevenLabsConfig, 
    Voice, 
    VoiceSettings, 
    AudioData, 
    QuotaInfo,
    AudioFormat
)
from app.exceptions.elevenlabs_exceptions import (
    ElevenLabsAPIError,
    VoiceNotFoundError,
    QuotaExceededError,
    VoiceGenerationError,
    AudioProcessingError
)
from app.logging_config import LoggerMixin, get_correlation_id


logger = logging.getLogger(__name__)


class ElevenLabsHTTPClient(LoggerMixin):
    """HTTP client for ElevenLabs API interactions."""
    
    def __init__(self, config: ElevenLabsConfig):
        """
        Initialize ElevenLabs HTTP client.
        
        Args:
            config: ElevenLabs configuration
        """
        self.config = config
        self.timeout = ClientTimeout(total=config.request_timeout)
        self._session: Optional[ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure aiohttp session is created."""
        if self._session is None or self._session.closed:
            self._session = ClientSession(
                timeout=self.timeout,
                headers={
                    'User-Agent': 'Ultravox-Twilio-Integration/1.0',
                    'Accept': 'application/json',
                    'xi-api-key': self.config.api_key
                }
            )
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def get_voices(self) -> List[Voice]:
        """
        Get list of available voices from ElevenLabs.
        
        Returns:
            List[Voice]: List of available voices
            
        Raises:
            ElevenLabsAPIError: If API request fails
        """
        correlation_id = get_correlation_id()
        
        try:
            self.logger.info(
                "Fetching voices from ElevenLabs",
                extra={"correlation_id": correlation_id}
            )
            
            response_data = await self._make_request(
                method="GET",
                endpoint="/v1/voices",
                correlation_id=correlation_id
            )
            
            voices = []
            for voice_data in response_data.get("voices", []):
                try:
                    voice = Voice(
                        voice_id=voice_data["voice_id"],
                        name=voice_data["name"],
                        category=voice_data.get("category", "premade"),
                        description=voice_data.get("description"),
                        preview_url=voice_data.get("preview_url"),
                        labels=voice_data.get("labels", {}),
                        available_for_tiers=voice_data.get("available_for_tiers", [])
                    )
                    voices.append(voice)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to parse voice data: {e}",
                        extra={"voice_data": voice_data, "correlation_id": correlation_id}
                    )
                    continue
            
            self.logger.info(
                f"Successfully fetched {len(voices)} voices",
                extra={"voice_count": len(voices), "correlation_id": correlation_id}
            )
            
            return voices
            
        except ElevenLabsAPIError:
            raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error fetching voices: {str(e)}",
                extra={"correlation_id": correlation_id},
                exc_info=True
            )
            raise ElevenLabsAPIError(f"Failed to fetch voices: {str(e)}")
    
    async def synthesize_speech(
        self, 
        text: str, 
        voice_id: str, 
        voice_settings: Optional[VoiceSettings] = None,
        audio_format: AudioFormat = AudioFormat.MP3_44100_128
    ) -> AudioData:
        """
        Synthesize speech using ElevenLabs API.
        
        Args:
            text: Text to synthesize
            voice_id: Voice ID to use
            voice_settings: Voice synthesis settings
            audio_format: Audio format for output
            
        Returns:
            AudioData: Generated audio data
            
        Raises:
            ElevenLabsAPIError: If synthesis fails
            VoiceNotFoundError: If voice is not found
            QuotaExceededError: If quota is exceeded
        """
        correlation_id = get_correlation_id()
        
        try:
            self.logger.info(
                f"Synthesizing speech with voice {voice_id}",
                extra={
                    "voice_id": voice_id,
                    "text_length": len(text),
                    "audio_format": audio_format.value,
                    "correlation_id": correlation_id
                }
            )
            
            # Prepare request data
            settings = voice_settings or self.config.default_voice_settings
            request_data = {
                "text": text,
                "voice_settings": settings.to_elevenlabs_dict()
            }
            
            # Make synthesis request
            audio_content = await self._make_request(
                method="POST",
                endpoint=f"/v1/text-to-speech/{voice_id}",
                data=request_data,
                params={"output_format": audio_format.value},
                expect_json=False,
                correlation_id=correlation_id
            )
            
            # Create audio data object
            audio_data = AudioData.from_response(audio_content, audio_format)
            
            self.logger.info(
                f"Successfully synthesized speech",
                extra={
                    "voice_id": voice_id,
                    "audio_size_bytes": audio_data.size_bytes,
                    "correlation_id": correlation_id
                }
            )
            
            return audio_data
            
        except ElevenLabsAPIError:
            raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error synthesizing speech: {str(e)}",
                extra={"voice_id": voice_id, "correlation_id": correlation_id},
                exc_info=True
            )
            raise VoiceGenerationError(str(e), voice_id=voice_id)
    
    async def get_voice_settings(self, voice_id: str) -> VoiceSettings:
        """
        Get voice settings for a specific voice.
        
        Args:
            voice_id: Voice ID
            
        Returns:
            VoiceSettings: Voice settings
            
        Raises:
            ElevenLabsAPIError: If API request fails
            VoiceNotFoundError: If voice is not found
        """
        correlation_id = get_correlation_id()
        
        try:
            self.logger.debug(
                f"Fetching voice settings for {voice_id}",
                extra={"voice_id": voice_id, "correlation_id": correlation_id}
            )
            
            response_data = await self._make_request(
                method="GET",
                endpoint=f"/v1/voices/{voice_id}/settings",
                correlation_id=correlation_id
            )
            
            return VoiceSettings(
                stability=response_data.get("stability", 0.75),
                similarity_boost=response_data.get("similarity_boost", 0.75),
                style=response_data.get("style", 0.0),
                use_speaker_boost=response_data.get("use_speaker_boost", False)
            )
            
        except ElevenLabsAPIError:
            raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error fetching voice settings: {str(e)}",
                extra={"voice_id": voice_id, "correlation_id": correlation_id},
                exc_info=True
            )
            raise ElevenLabsAPIError(f"Failed to fetch voice settings: {str(e)}")
    
    async def check_quota(self) -> QuotaInfo:
        """
        Check current quota usage.
        
        Returns:
            QuotaInfo: Current quota information
            
        Raises:
            ElevenLabsAPIError: If API request fails
        """
        correlation_id = get_correlation_id()
        
        try:
            self.logger.debug(
                "Checking ElevenLabs quota",
                extra={"correlation_id": correlation_id}
            )
            
            response_data = await self._make_request(
                method="GET",
                endpoint="/v1/user/subscription",
                correlation_id=correlation_id
            )
            
            quota_info = QuotaInfo(**response_data)
            
            self.logger.info(
                f"Quota check: {quota_info.character_count}/{quota_info.character_limit} characters used",
                extra={
                    "character_usage": quota_info.character_usage_percentage,
                    "characters_remaining": quota_info.characters_remaining,
                    "correlation_id": correlation_id
                }
            )
            
            return quota_info
            
        except ElevenLabsAPIError:
            raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error checking quota: {str(e)}",
                extra={"correlation_id": correlation_id},
                exc_info=True
            )
            raise ElevenLabsAPIError(f"Failed to check quota: {str(e)}")
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
        expect_json: bool = True,
        correlation_id: Optional[str] = None
    ) -> Any:
        """
        Make HTTP request to ElevenLabs API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data
            params: Query parameters
            expect_json: Whether to expect JSON response
            correlation_id: Request correlation ID
            
        Returns:
            Any: Response data
            
        Raises:
            ElevenLabsAPIError: If request fails
        """
        await self._ensure_session()
        
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        correlation_id = correlation_id or get_correlation_id()
        
        start_time = time.time()
        
        try:
            self.logger.debug(
                f"Making {method} request to {endpoint}",
                extra={
                    "method": method,
                    "endpoint": endpoint,
                    "has_data": bool(data),
                    "correlation_id": correlation_id
                }
            )
            
            # Prepare request kwargs
            kwargs = {
                "method": method,
                "url": url,
                "params": params
            }
            
            if data:
                kwargs["json"] = data
            
            async with self._session.request(**kwargs) as response:
                duration_ms = (time.time() - start_time) * 1000
                
                # Handle different response types
                if expect_json:
                    response_data = await self._handle_json_response(response, correlation_id)
                else:
                    response_data = await self._handle_binary_response(response, correlation_id)
                
                self.logger.info(
                    f"ElevenLabs API request successful: {method} {endpoint}",
                    extra={
                        "method": method,
                        "endpoint": endpoint,
                        "status_code": response.status,
                        "duration_ms": round(duration_ms, 2),
                        "correlation_id": correlation_id
                    }
                )
                
                return response_data
                
        except ElevenLabsAPIError:
            raise
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                f"ElevenLabs API request failed: {method} {endpoint}",
                extra={
                    "method": method,
                    "endpoint": endpoint,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                    "correlation_id": correlation_id
                },
                exc_info=True
            )
            raise ElevenLabsAPIError(f"Request failed: {str(e)}")
    
    async def _handle_json_response(self, response: aiohttp.ClientResponse, correlation_id: str) -> Dict[str, Any]:
        """Handle JSON response from ElevenLabs API."""
        try:
            response_text = await response.text()
            
            if not response.ok:
                await self._handle_error_response(response, response_text, correlation_id)
            
            if not response_text:
                return {}
            
            return json.loads(response_text)
            
        except json.JSONDecodeError as e:
            self.logger.error(
                f"Failed to parse JSON response: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            raise ElevenLabsAPIError(f"Invalid JSON response: {str(e)}")
    
    async def _handle_binary_response(self, response: aiohttp.ClientResponse, correlation_id: str) -> bytes:
        """Handle binary response from ElevenLabs API."""
        try:
            if not response.ok:
                response_text = await response.text()
                await self._handle_error_response(response, response_text, correlation_id)
            
            return await response.read()
            
        except Exception as e:
            self.logger.error(
                f"Failed to read binary response: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            raise AudioProcessingError(f"Failed to read audio response: {str(e)}")
    
    async def _handle_error_response(self, response: aiohttp.ClientResponse, response_text: str, correlation_id: str):
        """Handle error responses from ElevenLabs API."""
        status_code = response.status
        
        # Try to parse error details
        error_details = {"status_code": status_code, "response_text": response_text}
        error_message = f"ElevenLabs API error {status_code}"
        
        try:
            error_data = json.loads(response_text) if response_text else {}
            if isinstance(error_data, dict):
                detail = error_data.get("detail", {})
                if isinstance(detail, dict):
                    error_message = detail.get("message", error_message)
                elif isinstance(detail, str):
                    error_message = detail
                error_details.update(error_data)
        except json.JSONDecodeError:
            pass
        
        self.logger.error(
            f"ElevenLabs API error: {error_message}",
            extra={
                "status_code": status_code,
                "error_details": error_details,
                "correlation_id": correlation_id
            }
        )
        
        # Raise specific exceptions based on status code
        if status_code == 401:
            raise ElevenLabsAPIError("Authentication failed - check API key", status_code=401)
        elif status_code == 404:
            raise VoiceNotFoundError("Voice not found", details=error_details)
        elif status_code == 429:
            raise QuotaExceededError(details=error_details)
        elif status_code >= 500:
            raise ElevenLabsAPIError(f"ElevenLabs server error: {error_message}", status_code=status_code)
        else:
            raise ElevenLabsAPIError(error_message, status_code=status_code, details=error_details)