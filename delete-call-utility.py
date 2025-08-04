#!/usr/bin/env python3
"""
Utility script to delete specific calls by ID.
Keep this for sporadic use when you need to clean up mistaken calls.

Usage:
    python delete-call-utility.py <call_id>
    python delete-call-utility.py 9cf214f0-5023-4d9d-a297-0bc48bdd42aa
"""

import os

import sys
import asyncio
import aiohttp

async def delete_call(call_id: str):
    """Delete a specific call by ID."""
    
    # Load credentials from environment
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("ULTRAVOX_API_KEY")
    base_url = os.getenv("ULTRAVOX_BASE_URL", "https://api.ultravox.ai")
    
    if not api_key:
        print("❌ ULTRAVOX_API_KEY not found in environment variables")
        print("💡 Please set it in your .env file")
        return
    
    print(f"🗑️  Attempting to delete call: {call_id}")
    print(f"🔑 Using API key: {api_key[:10]}...")
    print(f"🌐 Base URL: {base_url}")
    print()
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Try to delete the call
            url = f"{base_url}/api/calls/{call_id}"
            
            async with session.delete(url, headers=headers) as response:
                print(f"📡 DELETE {url}")
                print(f"📊 Status: {response.status}")
                
                if response.status in [200, 204]:
                    print("✅ Call deleted successfully!")
                    return True
                elif response.status == 404:
                    print("⚠️  Call not found - it may have already been deleted")
                    return True
                else:
                    response_text = await response.text()
                    print(f"❌ Failed to delete call")
                    print(f"📄 Response: {response_text}")
                    return False
                    
    except Exception as e:
        print(f"💥 Error: {str(e)}")
        return False

async def main():
    """Main function."""
    
    if len(sys.argv) != 2:
        print("🚨 CALL DELETION UTILITY")
        print("=" * 40)
        print("Usage: python delete-call-utility.py <call_id>")
        print()
        print("Examples:")
        print("  python delete-call-utility.py 9cf214f0-5023-4d9d-a297-0bc48bdd42aa")
        print("  python delete-call-utility.py 0127c318-feda-477b-9395-31c7932de1ed")
        print()
        print("💡 This utility helps you delete mistaken calls quickly.")
        sys.exit(1)
    
    call_id = sys.argv[1].strip()
    
    print("🚨 CALL DELETION UTILITY")
    print("=" * 40)
    print(f"Call ID: {call_id}")
    print("=" * 40)
    
    # Validate call ID format (basic UUID check)
    if len(call_id) != 36 or call_id.count('-') != 4:
        print("⚠️  Warning: Call ID doesn't look like a valid UUID format")
        print("   Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        confirm = input("   Continue anyway? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("❌ Operation cancelled")
            sys.exit(1)
    
    success = await delete_call(call_id)
    
    if success:
        print("\n🎉 Operation completed successfully!")
        print("📞 The mistaken call has been handled.")
    else:
        print("\n❌ Operation failed!")
        print("\n🛠️  Possible reasons:")
        print("   - Call ID doesn't exist")
        print("   - Call was already deleted")
        print("   - API credentials issue")
        print("   - Network connectivity problem")

if __name__ == "__main__":
    asyncio.run(main())