"""
Voice service for ElevenLabs voice synthesis operations.
"""

import logging
from typing import List, Optional, Dict, Any
from app.models.elevenlabs import (
    Voice, 
    VoiceSettings, 
    AudioData, 
    ElevenLabsConfig,
    AudioFormat
)
from app.services.elevenlabs_client import ElevenLabsHTTPClient
from app.exceptions.elevenlabs_exceptions import (
    ElevenLabsAPIError,
    VoiceNotFoundError,
    TextTooLongError,
    VoiceGenerationError
)
from app.logging_config import LoggerMixin, get_correlation_id


logger = logging.getLogger(__name__)


class VoiceService(LoggerMixin):
    """Service for managing ElevenLabs voice operations."""
    
    def __init__(self, config: ElevenLabsConfig):
        """
        Initialize voice service.
        
        Args:
            config: ElevenLabs configuration
        """
        self.config = config
        self._client: Optional[ElevenLabsHTTPClient] = None
        self._voices_cache: Optional[List[Voice]] = None
        
    async def _ensure_client(self):
        """Ensure the HTTP client is initialized."""
        if self._client is None:
            self._client = ElevenLabsHTTPClient(self.config)
            await self._client.__aenter__()
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = ElevenLabsHTTPClient(self.config)
        await self._client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def list_voices(self, use_cache: bool = True) -> List[Voice]:
        """
        Get list of available voices.
        
        Args:
            use_cache: Whether to use cached voices
            
        Returns:
            List[Voice]: Available voices
            
        Raises:
            ElevenLabsAPIError: If API request fails
        """
        correlation_id = get_correlation_id()
        
        if use_cache and self._voices_cache:
            self.logger.debug(
                f"Returning cached voices ({len(self._voices_cache)} voices)",
                extra={"correlation_id": correlation_id}
            )
            return self._voices_cache
        
        try:
            self.logger.info(
                "Fetching voices from ElevenLabs",
                extra={"correlation_id": correlation_id}
            )
            
            await self._ensure_client()
            
            voices = await self._client.get_voices()
            self._voices_cache = voices
            
            self.logger.info(
                f"Successfully fetched {len(voices)} voices",
                extra={"voice_count": len(voices), "correlation_id": correlation_id}
            )
            
            return voices
            
        except ElevenLabsAPIError:
            raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error listing voices: {str(e)}",
                extra={"correlation_id": correlation_id},
                exc_info=True
            )
            raise ElevenLabsAPIError(f"Failed to list voices: {str(e)}")
    
    async def get_voice(self, voice_id: str) -> Optional[Voice]:
        """
        Get a specific voice by ID.
        
        Args:
            voice_id: Voice ID to find
            
        Returns:
            Voice: Voice object if found, None otherwise
        """
        voices = await self.list_voices()
        for voice in voices:
            if voice.voice_id == voice_id:
                return voice
        return None
    
    async def generate_speech(
        self, 
        text: str, 
        voice_id: str, 
        voice_settings: Optional[VoiceSettings] = None,
        audio_format: AudioFormat = AudioFormat.MP3_44100_128
    ) -> AudioData:
        """
        Generate speech from text.
        
        Args:
            text: Text to synthesize
            voice_id: Voice ID to use
            voice_settings: Voice synthesis settings
            audio_format: Audio format
            
        Returns:
            AudioData: Generated audio
            
        Raises:
            TextTooLongError: If text is too long
            VoiceNotFoundError: If voice doesn't exist
            VoiceGenerationError: If synthesis fails
        """
        correlation_id = get_correlation_id()
        
        # Validate text length
        if len(text) > self.config.max_text_length:
            raise TextTooLongError(len(text), self.config.max_text_length)
        
        # Validate voice exists
        voice = await self.get_voice(voice_id)
        if not voice:
            raise VoiceNotFoundError(voice_id)
        
        try:
            self.logger.info(
                f"Generating speech with voice {voice.name}",
                extra={
                    "voice_id": voice_id,
                    "voice_name": voice.name,
                    "text_length": len(text),
                    "correlation_id": correlation_id
                }
            )
            
            await self._ensure_client()
            
            # Use provided settings or defaults
            settings = voice_settings or self.config.default_voice_settings
            
            audio_data = await self._client.synthesize_speech(
                text=text,
                voice_id=voice_id,
                voice_settings=settings,
                audio_format=audio_format
            )
            
            self.logger.info(
                f"Successfully generated speech",
                extra={
                    "voice_id": voice_id,
                    "audio_size_bytes": audio_data.size_bytes,
                    "correlation_id": correlation_id
                }
            )
            
            return audio_data
            
        except (VoiceNotFoundError, TextTooLongError):
            raise
        except ElevenLabsAPIError:
            raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error generating speech: {str(e)}",
                extra={"voice_id": voice_id, "correlation_id": correlation_id},
                exc_info=True
            )
            raise VoiceGenerationError(str(e), voice_id=voice_id)
    
    async def preview_voice(
        self, 
        voice_id: str, 
        sample_text: str = "Hello, this is a preview of this voice."
    ) -> AudioData:
        """
        Generate a preview of a voice.
        
        Args:
            voice_id: Voice ID to preview
            sample_text: Text to use for preview
            
        Returns:
            AudioData: Preview audio
            
        Raises:
            VoiceNotFoundError: If voice doesn't exist
            VoiceGenerationError: If preview generation fails
        """
        if not self.config.enable_preview:
            raise VoiceGenerationError("Voice preview is disabled")
        
        # Use a shorter sample for preview
        preview_text = sample_text[:100] if len(sample_text) > 100 else sample_text
        
        return await self.generate_speech(
            text=preview_text,
            voice_id=voice_id,
            voice_settings=self.config.default_voice_settings,
            audio_format=AudioFormat.MP3_44100_128
        )
    
    async def validate_text(self, text: str) -> Dict[str, Any]:
        """
        Validate text for synthesis.
        
        Args:
            text: Text to validate
            
        Returns:
            dict: Validation result with details
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "character_count": len(text),
            "max_characters": self.config.max_text_length
        }
        
        # Check length
        if len(text) == 0:
            result["valid"] = False
            result["errors"].append("Text cannot be empty")
        elif len(text) > self.config.max_text_length:
            result["valid"] = False
            result["errors"].append(f"Text exceeds maximum length of {self.config.max_text_length} characters")
        
        # Check for very long text (warning)
        if len(text) > self.config.max_text_length * 0.8:
            result["warnings"].append("Text is approaching maximum length limit")
        
        # Basic content checks
        if text.strip() != text:
            result["warnings"].append("Text has leading or trailing whitespace")
        
        return result