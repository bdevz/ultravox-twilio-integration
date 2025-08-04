#!/usr/bin/env python3
"""
Startup script for the Ultravox-Twilio Integration Service.
This script checks for proper configuration and starts the appropriate server.
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Check if environment is properly configured."""
    required_vars = [
        "ULTRAVOX_API_KEY",
        "ULTRAVOX_BASE_URL", 
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_PHONE_NUMBER"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Please create a .env file with your credentials.")
        print("📖 See SETUP.md for detailed instructions.")
        return False
    
    return True

def main():
    """Main startup function."""
    print("🚀 Starting Ultravox-Twilio Integration Service...")
    
    # Check if .env file exists
    if Path(".env").exists():
        print("✅ Found .env file, loading environment variables...")
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Start the appropriate server
    server_choice = os.getenv("SERVER_TYPE", "simple").lower()
    
    if server_choice == "production":
        print("🏭 Starting production server...")
        os.system("python app/main.py")
    else:
        print("🌐 Starting simple web server...")
        os.system("python simple-web-server-secure.py")

if __name__ == "__main__":
    main()
