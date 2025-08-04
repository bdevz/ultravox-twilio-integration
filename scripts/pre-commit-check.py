#!/usr/bin/env python3
"""
Pre-commit hook to check for hardcoded credentials and sensitive information.
Run this before committing to ensure no secrets are accidentally committed.
"""

import os
import re
import sys
import glob
from pathlib import Path

def check_for_credentials():
    """Check for hardcoded credentials in files."""
    
    # Patterns that indicate hardcoded credentials
    sensitive_patterns = [
        # Ultravox API keys
        r'vPcLLMZx\.[a-zA-Z0-9]+',
        r'ULTRAVOX_API_KEY.*=.*["\'][^"\']+["\']',
        
        # Twilio credentials
        r'AC[a-z0-9]{32}',  # Twilio Account SID pattern
        r'TWILIO_ACCOUNT_SID.*=.*["\'][^"\']+["\']',
        r'TWILIO_AUTH_TOKEN.*=.*["\'][^"\']+["\']',
        
        # Phone numbers (specific ones we used)
        r'\+17142536558',
        r'\+12123900111',
        
        # Generic patterns
        r'api_key.*=.*["\'][a-zA-Z0-9]{20,}["\']',
        r'secret.*=.*["\'][^"\']+["\']',
        r'token.*=.*["\'][a-zA-Z0-9]{20,}["\']',
        r'password.*=.*["\'][^"\']+["\']',
    ]
    
    # File patterns to check
    file_patterns = [
        "*.py",
        "*.md", 
        "*.txt",
        "*.json",
        "*.yaml",
        "*.yml",
        "*.env*",
        "*.conf",
        "*.config"
    ]
    
    # Files to skip
    skip_files = [
        ".env.example",
        "scripts/pre-commit-check.py",  # This file itself
        "scripts/cleanup-debug-files.py",
        ".gitignore",
        "docs/",  # Documentation files with examples
        "tests/integration/README.md"  # Test documentation
    ]
    
    project_root = Path(__file__).parent.parent
    issues_found = []
    
    print("🔍 Checking for hardcoded credentials...")
    print("=" * 50)
    
    for pattern in file_patterns:
        files = glob.glob(str(project_root / "**" / pattern), recursive=True)
        
        for file_path in files:
            file_name = os.path.basename(file_path)
            relative_path = os.path.relpath(file_path, project_root)
            
            # Skip files we don't want to check
            if any(skip in relative_path for skip in skip_files):
                continue
                
            # Skip hidden directories and files
            if "/.git/" in file_path or "/__pycache__/" in file_path:
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                for i, line in enumerate(content.split('\n'), 1):
                    for pattern in sensitive_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            issues_found.append({
                                'file': relative_path,
                                'line': i,
                                'content': line.strip()[:100],
                                'pattern': pattern
                            })
                            
            except Exception as e:
                print(f"⚠️  Warning: Could not read {relative_path}: {e}")
    
    # Report findings
    if issues_found:
        print("❌ POTENTIAL CREDENTIALS FOUND:")
        print("=" * 50)
        
        for issue in issues_found:
            print(f"📄 File: {issue['file']}")
            print(f"📍 Line: {issue['line']}")
            print(f"🔍 Content: {issue['content']}")
            print(f"🎯 Pattern: {issue['pattern']}")
            print("-" * 30)
        
        print(f"\n🚨 Found {len(issues_found)} potential credential issues!")
        print("🛠️  Please remove hardcoded credentials before committing.")
        print("💡 Use environment variables instead (.env file).")
        return False
    else:
        print("✅ No hardcoded credentials found!")
        print("🎉 Repository is safe to commit.")
        return True

def check_env_file():
    """Check if .env file exists and warn about it."""
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"
    
    if env_file.exists():
        print("\n⚠️  WARNING: .env file detected!")
        print("🔒 Make sure .env is in .gitignore and not committed.")
        
        # Check if .env is in .gitignore
        gitignore_file = project_root / ".gitignore"
        if gitignore_file.exists():
            with open(gitignore_file, 'r') as f:
                gitignore_content = f.read()
                if ".env" in gitignore_content:
                    print("✅ .env is properly listed in .gitignore")
                else:
                    print("❌ .env is NOT in .gitignore - this is dangerous!")
                    return False
        else:
            print("❌ No .gitignore file found!")
            return False
    
    return True

def main():
    """Main function to run all checks."""
    print("🛡️  PRE-COMMIT SECURITY CHECK")
    print("=" * 60)
    
    # Run checks
    credentials_ok = check_for_credentials()
    env_ok = check_env_file()
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY:")
    print(f"   Credentials check: {'✅ PASS' if credentials_ok else '❌ FAIL'}")
    print(f"   Environment check: {'✅ PASS' if env_ok else '❌ FAIL'}")
    
    if credentials_ok and env_ok:
        print("\n🎉 All checks passed! Safe to commit.")
        return 0
    else:
        print("\n🚨 Security issues found! Please fix before committing.")
        print("\n🛠️  Quick fixes:")
        print("   1. Remove hardcoded API keys and use environment variables")
        print("   2. Add .env to .gitignore")
        print("   3. Run: python scripts/cleanup-debug-files.py")
        return 1

if __name__ == "__main__":
    sys.exit(main())