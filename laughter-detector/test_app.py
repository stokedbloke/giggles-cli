#!/usr/bin/env python3
"""
Test script to verify the application can start without Supabase configuration.

This script tests the basic functionality without requiring Supabase setup.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported."""
    try:
        print("Testing imports...")
        
        # Test basic imports
        from src.config.settings import Settings
        print("✅ Settings imported")
        
        from src.auth.encryption import EncryptionService
        print("✅ EncryptionService imported")
        
        from src.models.user import UserCreate, UserResponse
        print("✅ User models imported")
        
        from src.models.audio import AudioSegmentCreate, LaughterDetectionResponse
        print("✅ Audio models imported")
        
        from src.utils.audio_utils import AudioUtils
        print("✅ AudioUtils imported")
        
        from src.utils.security import SecurityUtils
        print("✅ SecurityUtils imported")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_encryption():
    """Test encryption functionality."""
    try:
        print("\nTesting encryption...")
        
        from src.auth.encryption import EncryptionService
        import secrets
        
        # Create encryption service with test key (64 hex chars = 32 bytes)
        test_key = secrets.token_hex(32)
        encryption_service = EncryptionService(test_key)
        
        # Test encryption/decryption
        test_data = "test_api_key_12345"
        encrypted = encryption_service.encrypt(test_data)
        decrypted = encryption_service.decrypt(encrypted)
        
        if decrypted == test_data:
            print("✅ Encryption/decryption working")
            return True
        else:
            print("❌ Encryption/decryption failed")
            return False
            
    except Exception as e:
        print(f"❌ Encryption test failed: {e}")
        return False

def test_models():
    """Test data models."""
    try:
        print("\nTesting data models...")
        
        from src.models.user import UserCreate, UserResponse
        
        # Test user creation
        user_data = UserCreate(
            email="test@example.com",
            password="TestPass123!"
        )
        
        if user_data.email == "test@example.com":
            print("✅ User models working")
            return True
        else:
            print("❌ User models failed")
            return False
            
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False

def test_security():
    """Test security utilities."""
    try:
        print("\nTesting security utilities...")
        
        from src.utils.security import SecurityUtils
        
        # Test email validation
        if SecurityUtils.validate_email("test@example.com"):
            print("✅ Email validation working")
        else:
            print("❌ Email validation failed")
            return False
        
        # Test password validation
        if SecurityUtils.validate_password_strength("TestPass123!"):
            print("✅ Password validation working")
        else:
            print("❌ Password validation failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Security test failed: {e}")
        return False

def main():
    """Main test function."""
    print("🎭 Giggles - Basic Tests")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_encryption,
        test_models,
        test_security
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Tests: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All basic tests passed!")
        print("\n📋 Next steps:")
        print("1. Set up your Supabase project")
        print("2. Update your .env file with Supabase credentials")
        print("3. Run the database setup script")
        print("4. Start the application with: python3 -m uvicorn src.main:app --reload")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
