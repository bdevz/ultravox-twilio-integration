#!/usr/bin/env python3
"""
Script to clean up debug and test files that contain hardcoded credentials.
This should be run before committing to GitHub.
"""

import os
import glob
from pathlib import Path

def cleanup_debug_files():
    """Remove debug and test files with hardcoded credentials."""
    
    # Patterns for files to remove
    patterns_to_remove = [
        "bb-*.py",
        "debug-*.py", 
        "test-*.py",
        "quick-*.py",
        "*-test.py",
        "*-debug.py"
    ]
    
    # Files to keep (important test files)
    files_to_keep = [
        "test_*.py",  # Proper test files in tests/ directory
        "tests/*.py"  # All files in tests directory
    ]
    
    project_root = Path(__file__).parent.parent
    removed_files = []
    
    print("🧹 Cleaning up debug files with hardcoded credentials...")
    print("=" * 60)
    
    for pattern in patterns_to_remove:
        files = glob.glob(str(project_root / pattern))
        for file_path in files:
            file_name = os.path.basename(file_path)
            
            # Skip if it's a file we want to keep
            should_keep = False
            for keep_pattern in files_to_keep:
                if glob.fnmatch.fnmatch(file_path, keep_pattern):
                    should_keep = True
                    break
            
            if should_keep:
                print(f"⚠️  Keeping: {file_name} (important test file)")
                continue
            
            # Check if file contains hardcoded credentials
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                # Look for hardcoded API keys or credentials
                sensitive_patterns = [
                    "vPcLLMZx",  # Ultravox API key prefix
                    "sk_",  # ElevenLabs API key prefix
                    "AC[a-f0-9]{32}",  # Twilio Account SID pattern
                    r"\+1[0-9]{10}",  # Phone number pattern
                    r"[a-f0-9]{32}"  # Generic 32-char hex tokens
                ]
                
                contains_credentials = any(pattern in content for pattern in sensitive_patterns)
                
                if contains_credentials:
                    os.remove(file_path)
                    removed_files.append(file_name)
                    print(f"🗑️  Removed: {file_name} (contained hardcoded credentials)")
                else:
                    print(f"✅ Kept: {file_name} (no hardcoded credentials found)")
                    
            except Exception as e:
                print(f"⚠️  Error checking {file_name}: {e}")
    
    print("\n" + "=" * 60)
    print(f"🎯 Cleanup Summary:")
    print(f"   Files removed: {len(removed_files)}")
    
    if removed_files:
        print(f"   Removed files:")
        for file_name in removed_files:
            print(f"     - {file_name}")
    
    print(f"\n✅ Cleanup complete! Repository is ready for GitHub.")
    
    return removed_files

if __name__ == "__main__":
    cleanup_debug_files()