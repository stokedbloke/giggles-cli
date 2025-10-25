#!/usr/bin/env python3
"""
Simple test script to validate the laughter detector project structure.

This script checks that all required files exist and basic imports work.
"""

import os
import sys
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists and report status."""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (missing)")
        return False

def check_directory_exists(dir_path, description):
    """Check if a directory exists and report status."""
    if os.path.isdir(dir_path):
        print(f"✅ {description}: {dir_path}")
        return True
    else:
        print(f"❌ {description}: {dir_path} (missing)")
        return False

def main():
    """Main test function."""
    print("🎭 Giggles - Structure Validation")
    print("=" * 50)
    
    # Check project structure
    checks = [
        # Core application files
        ("src/main.py", "Main FastAPI application"),
        ("src/config/settings.py", "Configuration settings"),
        ("src/auth/supabase_auth.py", "Supabase authentication"),
        ("src/auth/encryption.py", "Encryption service"),
        ("src/models/user.py", "User data models"),
        ("src/models/audio.py", "Audio data models"),
        ("src/models/laughter.py", "Laughter detection models"),
        ("src/services/limitless_api.py", "Limitless API service"),
        ("src/services/yamnet_processor.py", "YAMNet processor"),
        ("src/services/cleanup.py", "Cleanup service"),
        ("src/services/scheduler.py", "Background scheduler"),
        ("src/api/routes.py", "API routes"),
        ("src/api/dependencies.py", "API dependencies"),
        ("src/utils/audio_utils.py", "Audio utilities"),
        ("src/utils/security.py", "Security utilities"),
        
        # Frontend files
        ("templates/index.html", "Main HTML template"),
        ("static/css/style.css", "CSS styles"),
        ("static/js/app.js", "JavaScript application"),
        
        # Configuration files
        ("requirements.txt", "Python dependencies"),
        ("env.example", "Environment configuration example"),
        ("README.md", "Project documentation"),
        ("Dockerfile", "Docker configuration"),
        ("docker-compose.yml", "Docker Compose configuration"),
        
        # Test files
        ("tests/conftest.py", "Test configuration"),
        ("tests/test_auth.py", "Authentication tests"),
        ("tests/test_audio_processing.py", "Audio processing tests"),
        ("tests/test_api.py", "API endpoint tests"),
    ]
    
    passed = 0
    total = len(checks)
    
    for file_path, description in checks:
        if check_file_exists(file_path, description):
            passed += 1
    
    print("\n" + "=" * 50)
    
    # Check directories
    directories = [
        ("src", "Source code directory"),
        ("src/config", "Configuration module"),
        ("src/auth", "Authentication module"),
        ("src/models", "Data models module"),
        ("src/services", "Services module"),
        ("src/api", "API module"),
        ("src/utils", "Utilities module"),
        ("tests", "Test suite"),
        ("templates", "HTML templates"),
        ("static", "Static assets"),
        ("static/css", "CSS files"),
        ("static/js", "JavaScript files"),
        ("uploads", "Upload directory"),
    ]
    
    print("\nDirectory Structure:")
    for dir_path, description in directories:
        check_directory_exists(dir_path, description)
    
    print("\n" + "=" * 50)
    print(f"File Structure Check: {passed}/{total} files present")
    
    if passed == total:
        print("🎉 All required files are present!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Configure environment: cp env.example .env")
        print("3. Set up Supabase project and add credentials to .env")
        print("4. Run the application: python -m uvicorn src.main:app --reload")
        return True
    else:
        print(f"⚠️  {total - passed} files are missing. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
