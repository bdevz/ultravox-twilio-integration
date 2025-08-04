"""
Exception package for the Ultravox-Twilio integration service.
"""

# Import all exceptions from the base exceptions module
from app.exceptions.base import *

# Import ElevenLabs-specific exceptions if available
try:
    from app.exceptions.elevenlabs_exceptions import *
except ImportError:
    # ElevenLabs exceptions not available - this is fine if ElevenLabs is not configured
    pass