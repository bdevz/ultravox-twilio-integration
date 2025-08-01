#!/usr/bin/env python3
"""
Development environment validation script.
Checks if the development environment is properly configured.
"""

import sys
import os
import subprocess
import importlib
from pathlib import Path
from typing import List, Tuple, Dict, Any

def check_python_version() -> Tuple[bool, str]:
    """Check if Python version meets requirements."""
    required_version = (3, 11)
    current_version = sys.version_info[:2]
    
    if current_version >= required_version:
        return True, f"✅ Python {sys.version.split()[0]} (meets requirement >= {'.'.join(map(str, required_version))})"
    else:
        return False, f"❌ Python {sys.version.split()[0]} (requires >= {'.'.join(map(str, required_version))})"

def check_virtual_environment() -> Tuple[bool, str]:
    """Check if running in a virtual environment."""
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    if in_venv:
        return True, f"✅ Virtual environment active: {sys.prefix}"
    else:
        return False, "❌ No virtual environment detected (recommended to use .venv)"

def check_required_packages() -> Tuple[bool, str]:
    """Check if required packages are installed."""
    required_packages = [
        'fastapi',
        'uvicorn',
        'aiohttp',
        'httpx',
        'pydantic',
        'twilio',
        'python-dotenv',
        'structlog',
        'pytest',
        'black',
        'flake8',
        'mypy'
    ]
    
    missing_packages = []
    installed_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package.replace('-', '_'))
            installed_packages.append(package)
        except ImportError:
            missing_packages.append(package)
    
    if not missing_packages:
        return True, f"✅ All required packages installed ({len(installed_packages)} packages)"
    else:
        return False, f"❌ Missing packages: {', '.join(missing_packages)}"

def check_project_structure() -> Tuple[bool, str]:
    """Check if project structure is correct."""
    required_dirs = ['app', 'tests', 'scripts', 'docs']
    required_files = [
        'requirements.txt',
        'dev-requirements.txt',
        '.env.example',
        'app/main.py',
        'app/api/routes.py'
    ]
    
    project_root = Path(__file__).parent.parent
    missing_items = []
    
    # Check directories
    for dir_name in required_dirs:
        if not (project_root / dir_name).exists():
            missing_items.append(f"directory: {dir_name}")
    
    # Check files
    for file_path in required_files:
        if not (project_root / file_path).exists():
            missing_items.append(f"file: {file_path}")
    
    if not missing_items:
        return True, "✅ Project structure is correct"
    else:
        return False, f"❌ Missing: {', '.join(missing_items)}"

def check_environment_file() -> Tuple[bool, str]:
    """Check if .env file exists and has required variables."""
    project_root = Path(__file__).parent.parent
    env_file = project_root / '.env'
    
    if not env_file.exists():
        return False, "❌ .env file not found (copy from .env.example)"
    
    # Read environment variables
    env_vars = {}
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except Exception as e:
        return False, f"❌ Error reading .env file: {e}"
    
    required_vars = [
        'ULTRAVOX_API_KEY',
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN',
        'TWILIO_PHONE_NUMBER'
    ]
    
    missing_vars = []
    placeholder_vars = []
    
    for var in required_vars:
        if var not in env_vars:
            missing_vars.append(var)
        elif env_vars[var].startswith('your_') or not env_vars[var]:
            placeholder_vars.append(var)
    
    if missing_vars:
        return False, f"❌ Missing environment variables: {', '.join(missing_vars)}"
    elif placeholder_vars:
        return False, f"⚠️  Placeholder values detected: {', '.join(placeholder_vars)} (update with actual values)"
    else:
        return True, f"✅ Environment variables configured ({len(required_vars)} variables)"

def check_port_availability() -> Tuple[bool, str]:
    """Check if development port (8000) is available."""
    import socket
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 8000))
            return True, "✅ Port 8000 is available"
    except OSError:
        return False, "❌ Port 8000 is already in use"

def check_git_repository() -> Tuple[bool, str]:
    """Check if this is a git repository."""
    project_root = Path(__file__).parent.parent
    
    if (project_root / '.git').exists():
        try:
            result = subprocess.run(['git', 'status'], 
                                  capture_output=True, 
                                  text=True, 
                                  cwd=project_root)
            if result.returncode == 0:
                return True, "✅ Git repository initialized"
            else:
                return False, "❌ Git repository corrupted"
        except FileNotFoundError:
            return False, "❌ Git not installed"
    else:
        return False, "⚠️  Not a git repository (optional but recommended)"

def run_basic_import_test() -> Tuple[bool, str]:
    """Test if the main application can be imported."""
    try:
        # Add project root to Python path
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        # Try to import main modules
        from app.main import app
        from app.api.routes import router
        from app.services.config_service import get_config_service
        
        return True, "✅ Application modules can be imported successfully"
    except Exception as e:
        return False, f"❌ Import error: {str(e)}"

def main():
    """Run all development environment checks."""
    print("🔍 Checking Development Environment")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_environment),
        ("Required Packages", check_required_packages),
        ("Project Structure", check_project_structure),
        ("Environment File", check_environment_file),
        ("Port Availability", check_port_availability),
        ("Git Repository", check_git_repository),
        ("Import Test", run_basic_import_test),
    ]
    
    results = []
    all_passed = True
    
    for check_name, check_func in checks:
        try:
            passed, message = check_func()
            results.append((check_name, passed, message))
            if not passed:
                all_passed = False
        except Exception as e:
            results.append((check_name, False, f"❌ Error: {str(e)}"))
            all_passed = False
    
    # Display results
    for check_name, passed, message in results:
        print(f"{check_name:20} {message}")
    
    print("=" * 50)
    
    if all_passed:
        print("🎉 Development environment is ready!")
        print("\nNext steps:")
        print("  1. Start development server: python scripts/dev.py")
        print("  2. Open API docs: http://localhost:8000/docs")
        print("  3. Run tests: pytest")
    else:
        print("❌ Development environment has issues that need to be resolved.")
        print("\nRecommended actions:")
        
        failed_checks = [name for name, passed, _ in results if not passed]
        
        if "Required Packages" in failed_checks:
            print("  • Install missing packages: pip install -r requirements.txt -r dev-requirements.txt")
        
        if "Environment File" in failed_checks:
            print("  • Copy and configure environment: cp .env.example .env")
            print("  • Edit .env with your actual API keys")
        
        if "Port Availability" in failed_checks:
            print("  • Stop process using port 8000: lsof -i :8000")
        
        if "Python Version" in failed_checks:
            print("  • Upgrade Python to 3.11 or higher")
        
        if "Virtual Environment" in failed_checks:
            print("  • Create and activate virtual environment:")
            print("    python -m venv .venv")
            print("    source .venv/bin/activate")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())