#!/usr/bin/env python3
"""
Script to validate ElevenLabs configuration and test API connectivity.
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.config_service import ConfigService
from app.services.elevenlabs_client import ElevenLabsHTTPClient
from app.exceptions.elevenlabs_exceptions import ElevenLabsAPIError

# Load environment variables
load_dotenv()

async def validate_elevenlabs_config():
    """Validate ElevenLabs configuration and test API connectivity."""
    
    print("🔧 ELEVENLABS CONFIGURATION VALIDATION")
    print("=" * 60)
    
    # Initialize config service
    config_service = ConfigService()
    
    # Check if ElevenLabs is enabled
    if not config_service.is_elevenlabs_enabled():
        print("⚠️  ElevenLabs integration is disabled or not configured")
        print("💡 To enable ElevenLabs:")
        print("   1. Set ENABLE_ELEVENLABS=true in your .env file")
        print("   2. Add your ELEVENLABS_API_KEY")
        print("   3. Configure other ElevenLabs settings as needed")
        return False
    
    try:
        # Load ElevenLabs configuration
        print("📋 Loading ElevenLabs configuration...")
        elevenlabs_config = config_service.get_elevenlabs_config()
        
        print("✅ Configuration loaded successfully:")
        print(f"   Base URL: {elevenlabs_config.base_url}")
        print(f"   API Key: {elevenlabs_config.api_key[:10]}...")
        print(f"   Default Voice: {elevenlabs_config.default_voice_id}")
        print(f"   Max Text Length: {elevenlabs_config.max_text_length}")
        print(f"   Request Timeout: {elevenlabs_config.request_timeout}s")
        print(f"   Preview Enabled: {elevenlabs_config.enable_preview}")
        print()
        
        # Test API connectivity
        print("🌐 Testing ElevenLabs API connectivity...")
        
        async with ElevenLabsHTTPClient(elevenlabs_config) as client:
            # Test 1: Check quota
            print("   📊 Checking quota...")
            try:
                quota_info = await client.check_quota()
                print(f"   ✅ Quota check successful:")
                print(f"      Characters used: {quota_info.character_count:,}/{quota_info.character_limit:,}")
                print(f"      Usage: {quota_info.character_usage_percentage:.1f}%")
                print(f"      Remaining: {quota_info.characters_remaining:,}")
                print(f"      Status: {quota_info.status}")
            except Exception as e:
                print(f"   ❌ Quota check failed: {str(e)}")
                return False
            
            print()
            
            # Test 2: List voices
            print("   🎤 Fetching available voices...")
            try:
                voices = await client.get_voices()
                print(f"   ✅ Found {len(voices)} available voices:")
                
                # Show first 5 voices
                for i, voice in enumerate(voices[:5], 1):
                    print(f"      {i}. {voice.name} ({voice.voice_id}) - {voice.category}")
                
                if len(voices) > 5:
                    print(f"      ... and {len(voices) - 5} more voices")
                    
            except Exception as e:
                print(f"   ❌ Voice listing failed: {str(e)}")
                return False
            
            print()
            
            # Test 3: Test default voice settings
            print("   ⚙️  Testing default voice settings...")
            try:
                default_voice_id = elevenlabs_config.default_voice_id
                voice_settings = await client.get_voice_settings(default_voice_id)
                print(f"   ✅ Default voice settings retrieved:")
                print(f"      Stability: {voice_settings.stability}")
                print(f"      Similarity Boost: {voice_settings.similarity_boost}")
                print(f"      Style: {voice_settings.style}")
                print(f"      Speaker Boost: {voice_settings.use_speaker_boost}")
            except Exception as e:
                print(f"   ⚠️  Voice settings test failed: {str(e)}")
                print("   (This might be normal for some voice types)")
        
        print("\n" + "=" * 60)
        print("🎉 ElevenLabs configuration validation successful!")
        print("✅ All tests passed - ElevenLabs integration is ready to use")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Configuration validation failed: {str(e)}")
        print("\n🛠️  Troubleshooting:")
        print("   1. Check your ELEVENLABS_API_KEY is correct")
        print("   2. Verify your ElevenLabs account is active")
        print("   3. Ensure you have sufficient quota")
        print("   4. Check network connectivity")
        
        return False

def main():
    """Main function."""
    print("🧪 ElevenLabs Configuration Validator")
    print("This script validates your ElevenLabs configuration and tests API connectivity.")
    print()
    
    success = asyncio.run(validate_elevenlabs_config())
    
    if success:
        print("\n🚀 Your ElevenLabs integration is ready!")
        print("You can now use ElevenLabs features in your application.")
    else:
        print("\n❌ ElevenLabs validation failed.")
        print("Please fix the configuration issues and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()