#!/usr/bin/env python3
"""
Development server script with hot reload and enhanced logging.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from dotenv import load_dotenv

def load_environment_config(env_name: str = "development"):
    """Load environment-specific configuration."""
    project_root = Path(__file__).parent.parent
    
    # Load base .env file first
    base_env_file = project_root / ".env"
    if base_env_file.exists():
        load_dotenv(base_env_file)
    
    # Load environment-specific config
    env_file = project_root / f".env.{env_name}"
    if env_file.exists():
        load_dotenv(env_file, override=True)
        print(f"✅ Loaded {env_name} environment configuration")
    else:
        print(f"⚠️  No .env.{env_name} file found, using defaults")

def main():
    """Start the development server with hot reload."""
    parser = argparse.ArgumentParser(description="Start development server")
    parser.add_argument("--env", default="development", 
                       help="Environment configuration to load (default: development)")
    parser.add_argument("--port", type=int, default=8000,
                       help="Port to run the server on (default: 8000)")
    parser.add_argument("--host", default="0.0.0.0",
                       help="Host to bind the server to (default: 0.0.0.0)")
    parser.add_argument("--no-reload", action="store_true",
                       help="Disable hot reload")
    args = parser.parse_args()
    
    # Ensure we're in the project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Load environment configuration
    load_environment_config(args.env)
    
    # Set development environment variables (can be overridden by env files)
    env = os.environ.copy()
    default_env = {
        "DEBUG": "true",
        "LOG_LEVEL": "DEBUG",
        "LOG_FORMAT": "console",  # More readable for development
        "LOG_REQUEST_BODY": "true",
        "LOG_RESPONSE_BODY": "true",
        "CORS_ORIGINS": "*",  # Allow all origins in development
        "ENABLE_API_DOCS": "true",
        "ENABLE_METRICS_ENDPOINT": "true",
    }
    
    # Only set defaults if not already set
    for key, value in default_env.items():
        if key not in env:
            env[key] = value
    
    # Check if base .env file exists
    env_file = project_root / ".env"
    if not env_file.exists():
        print("⚠️  No .env file found. Creating from .env.example...")
        example_file = project_root / ".env.example"
        if example_file.exists():
            env_file.write_text(example_file.read_text())
            print("✅ Created .env file from .env.example")
            print("📝 Please edit .env file with your actual API keys")
        else:
            print("❌ No .env.example file found")
            sys.exit(1)
    
    # Display startup information
    print("🚀 Starting development server...")
    print(f"📍 Server will be available at: http://{args.host}:{args.port}")
    print(f"📚 API documentation at: http://{args.host}:{args.port}/docs")
    print(f"🌍 Environment: {args.env}")
    if not args.no_reload:
        print("🔄 Hot reload enabled - changes will restart the server")
    print("🛑 Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        # Build uvicorn command
        cmd = [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", args.host,
            "--port", str(args.port),
            "--log-level", "info",
            "--access-log"
        ]
        
        # Add reload options if not disabled
        if not args.no_reload:
            cmd.extend([
                "--reload",
                "--reload-dir", "app",
                "--reload-dir", "tests",
            ])
        
        # Start uvicorn
        subprocess.run(cmd, env=env, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Development server stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()