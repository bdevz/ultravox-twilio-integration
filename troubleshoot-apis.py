#!/usr/bin/env python3
"""
Comprehensive API troubleshooting script.
Tests each API individually to identify the exact issue.
"""

import os
import sys
import asyncio
import aiohttp
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_ultravox_api():
    """Test Ultravox API connectivity."""
    print("🧪 Testing Ultravox API...")
    
    api_key = os.getenv("ULTRAVOX_API_KEY")
    base_url = os.getenv("ULTRAVOX_BASE_URL", "https://api.ultravox.ai")
    
    if not api_key:
        print("❌ ULTRAVOX_API_KEY not found in environment")
        return False
    
    print(f"   API Key: {api_key[:10]}...")
    print(f"   Base URL: {base_url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test basic connectivity - Ultravox uses X-API-Key header
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Try to list agents
            async with session.get(f"{base_url}/api/agents", headers=headers) as response:
                print(f"   Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Ultravox API working - found {len(data.get('results', []))} agents")
                    return True
                elif response.status == 401:
                    print("   ❌ Authentication failed - check API key")
                    return False
                else:
                    text = await response.text()
                    print(f"   ❌ API error: {text}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return False

async def test_elevenlabs_api():
    """Test ElevenLabs API connectivity."""
    print("🧪 Testing ElevenLabs API...")
    
    api_key = os.getenv("ELEVENLABS_API_KEY")
    base_url = os.getenv("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io/v1")
    
    if not api_key:
        print("❌ ELEVENLABS_API_KEY not found in environment")
        return False
    
    print(f"   API Key: {api_key[:10]}...")
    print(f"   Base URL: {base_url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test basic connectivity
            headers = {
                "xi-api-key": api_key,
                "Content-Type": "application/json"
            }
            
            # Try to list voices
            async with session.get(f"{base_url}/voices", headers=headers) as response:
                print(f"   Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    voices = data.get('voices', [])
                    print(f"   ✅ ElevenLabs API working - found {len(voices)} voices")
                    return True
                elif response.status == 401:
                    print("   ❌ Authentication failed - check API key")
                    return False
                else:
                    text = await response.text()
                    print(f"   ❌ API error: {text}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return False

async def test_twilio_api():
    """Test Twilio API connectivity."""
    print("🧪 Testing Twilio API...")
    
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    if not account_sid or not auth_token:
        print("❌ Twilio credentials not found in environment")
        return False
    
    print(f"   Account SID: {account_sid[:10]}...")
    print(f"   Auth Token: {auth_token[:10]}...")
    
    try:
        import base64
        
        # Create basic auth header
        credentials = f"{account_sid}:{auth_token}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Try to get account info
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json"
            async with session.get(url, headers=headers) as response:
                print(f"   Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Twilio API working - Account: {data.get('friendly_name', 'Unknown')}")
                    return True
                elif response.status == 401:
                    print("   ❌ Authentication failed - check credentials")
                    return False
                else:
                    text = await response.text()
                    print(f"   ❌ API error: {text}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return False

def check_environment_variables():
    """Check all required environment variables."""
    print("🔍 Checking environment variables...")
    
    required_vars = {
        "ULTRAVOX_API_KEY": os.getenv("ULTRAVOX_API_KEY"),
        "ULTRAVOX_BASE_URL": os.getenv("ULTRAVOX_BASE_URL"),
        "TWILIO_ACCOUNT_SID": os.getenv("TWILIO_ACCOUNT_SID"),
        "TWILIO_AUTH_TOKEN": os.getenv("TWILIO_AUTH_TOKEN"),
        "TWILIO_PHONE_NUMBER": os.getenv("TWILIO_PHONE_NUMBER"),
        "ELEVENLABS_API_KEY": os.getenv("ELEVENLABS_API_KEY"),
        "ENABLE_ELEVENLABS": os.getenv("ENABLE_ELEVENLABS")
    }
    
    missing = []
    for var, value in required_vars.items():
        if value:
            if "KEY" in var or "TOKEN" in var:
                print(f"   ✅ {var}: {value[:10]}...")
            else:
                print(f"   ✅ {var}: {value}")
        else:
            print(f"   ❌ {var}: NOT SET")
            missing.append(var)
    
    if missing:
        print(f"\n❌ Missing variables: {', '.join(missing)}")
        return False
    else:
        print("✅ All environment variables are set")
        return True

async def test_service_initialization():
    """Test service initialization without making API calls."""
    print("🔧 Testing service initialization...")
    
    try:
        from app.services.config_service import ConfigService
        config_service = ConfigService()
        print("   ✅ ConfigService initialized")
        
        # Test Ultravox config
        try:
            ultravox_config = config_service.get_ultravox_config()
            print("   ✅ Ultravox config loaded")
        except Exception as e:
            print(f"   ❌ Ultravox config failed: {e}")
        
        # Test ElevenLabs config
        try:
            if config_service.is_elevenlabs_enabled():
                elevenlabs_config = config_service.get_elevenlabs_config()
                print("   ✅ ElevenLabs config loaded")
            else:
                print("   ⚠️  ElevenLabs disabled")
        except Exception as e:
            print(f"   ❌ ElevenLabs config failed: {e}")
        
        # Test HTTP client
        from app.services.http_client_service import HTTPClientService
        http_client = HTTPClientService()
        print("   ✅ HTTPClientService initialized")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Service initialization failed: {e}")
        return False

async def main():
    """Main troubleshooting function."""
    print("🚀 API Troubleshooting Script")
    print("=" * 50)
    
    # Check environment variables
    env_ok = check_environment_variables()
    print()
    
    if not env_ok:
        print("❌ Fix environment variables first!")
        return
    
    # Test service initialization
    services_ok = await test_service_initialization()
    print()
    
    if not services_ok:
        print("❌ Fix service initialization first!")
        return
    
    # Test external APIs
    print("🌐 Testing external API connectivity...")
    
    ultravox_ok = await test_ultravox_api()
    print()
    
    elevenlabs_ok = await test_elevenlabs_api()
    print()
    
    twilio_ok = await test_twilio_api()
    print()
    
    # Summary
    print("📊 Summary:")
    print(f"   Environment: {'✅' if env_ok else '❌'}")
    print(f"   Services: {'✅' if services_ok else '❌'}")
    print(f"   Ultravox API: {'✅' if ultravox_ok else '❌'}")
    print(f"   ElevenLabs API: {'✅' if elevenlabs_ok else '❌'}")
    print(f"   Twilio API: {'✅' if twilio_ok else '❌'}")
    
    if all([env_ok, services_ok, ultravox_ok, elevenlabs_ok, twilio_ok]):
        print("\n🎉 All systems working! The server should run properly.")
    else:
        print("\n❌ Issues found. Fix the failing components above.")

if __name__ == "__main__":
    asyncio.run(main())