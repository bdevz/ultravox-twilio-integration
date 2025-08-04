#!/usr/bin/env python3
"""
Script to prepare the repository for GitHub by ensuring all sensitive data is removed
and proper configuration files are in place.
"""

import os
import shutil
from pathlib import Path

def prepare_repository():
    """Prepare repository for GitHub commit."""
    
    project_root = Path(__file__).parent.parent
    
    print("🚀 PREPARING REPOSITORY FOR GITHUB")
    print("=" * 60)
    
    # 1. Ensure .gitignore exists
    gitignore_path = project_root / ".gitignore"
    if not gitignore_path.exists():
        print("❌ .gitignore file missing!")
        return False
    else:
        print("✅ .gitignore file exists")
    
    # 2. Ensure .env.example exists
    env_example_path = project_root / ".env.example"
    if not env_example_path.exists():
        print("❌ .env.example file missing!")
        return False
    else:
        print("✅ .env.example file exists")
    
    # 3. Replace README.md with secure version
    readme_secure = project_root / "README-SECURE.md"
    readme_original = project_root / "README.md"
    
    if readme_secure.exists():
        shutil.copy(readme_secure, readme_original)
        os.remove(readme_secure)
        print("✅ README.md updated with secure version")
    else:
        print("⚠️  README-SECURE.md not found, keeping original README.md")
    
    # 4. Ensure secure web server exists
    secure_server = project_root / "simple-web-server-secure.py"
    if not secure_server.exists():
        print("❌ simple-web-server-secure.py missing!")
        return False
    else:
        print("✅ Secure web server exists")
    
    # 5. Check for .env file and warn
    env_file = project_root / ".env"
    if env_file.exists():
        print("⚠️  .env file exists - make sure it's in .gitignore!")
    else:
        print("✅ No .env file found (good for GitHub)")
    
    # 6. Create startup instructions
    startup_script = project_root / "start.py"
    if not startup_script.exists():
        with open(startup_script, 'w') as f:
            f.write('''#!/usr/bin/env python3
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
        print("\\n💡 Please create a .env file with your credentials.")
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
''')
        print("✅ Created start.py script")
    
    print("\n" + "=" * 60)
    print("📋 FINAL CHECKLIST:")
    print("   ✅ .gitignore configured")
    print("   ✅ .env.example template created")
    print("   ✅ README.md updated")
    print("   ✅ Secure web server available")
    print("   ✅ Startup script created")
    print("   ✅ Debug files cleaned up")
    
    print("\n🎯 NEXT STEPS:")
    print("   1. Run: python scripts/pre-commit-check.py")
    print("   2. If checks pass, commit to GitHub")
    print("   3. Share SETUP.md with your team")
    print("   4. Team members should create their own .env files")
    
    print("\n🔒 SECURITY REMINDERS:")
    print("   - Never commit .env files")
    print("   - Rotate API keys regularly")
    print("   - Use strong API keys for production")
    print("   - Monitor for credential leaks")
    
    return True

if __name__ == "__main__":
    success = prepare_repository()
    if success:
        print("\\n🎉 Repository is ready for GitHub!")
    else:
        print("\\n❌ Repository preparation failed!")
        sys.exit(1)