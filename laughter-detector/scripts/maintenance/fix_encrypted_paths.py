#!/usr/bin/env python3
"""
Fix Encrypted Paths
===================

This script fixes the corrupted encrypted file paths in the database
by re-encrypting the correct file paths.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from supabase import create_client, Client
from src.auth.encryption import EncryptionService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EncryptedPathsFixer:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise Exception("Supabase credentials not found")
        
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        self.encryption_service = EncryptionService()
        logger.info("🔧 Encrypted Paths Fixer initialized")
    
    def fix_encrypted_paths(self):
        """Fix corrupted encrypted file paths."""
        logger.info("🔍 Fixing corrupted encrypted file paths...")
        
        try:
            # Get all audio segments
            result = self.supabase.table("audio_segments").select("*").execute()
            
            if not result.data:
                logger.info("✅ No audio segments found")
                return True
            
            logger.info(f"📊 Found {len(result.data)} audio segments")
            
            fixed_count = 0
            
            for segment in result.data:
                segment_id = segment["id"]
                user_id = segment["user_id"]
                old_encrypted_path = segment["file_path"]
                
                logger.info(f"🔧 Fixing segment {segment_id}")
                
                # Find the correct file in the user directory
                user_dir = f"uploads/audio/{user_id}/"
                if os.path.exists(user_dir):
                    files = [f for f in os.listdir(user_dir) if f.endswith('.ogg')]
                    
                    if files:
                        # Use the first OGG file (they should be in chronological order)
                        correct_file = os.path.join(user_dir, files[0])
                        logger.info(f"   Found file: {os.path.basename(correct_file)}")
                        
                        # Encrypt the correct path
                        new_encrypted_path = self.encryption_service.encrypt(correct_file)
                        
                        # Update the database
                        self.supabase.table("audio_segments").update({
                            "file_path": new_encrypted_path
                        }).eq("id", segment_id).execute()
                        
                        logger.info(f"   ✅ Updated encrypted path")
                        fixed_count += 1
                        
                        # Remove the file from the list so we don't reuse it
                        files.pop(0)
                    else:
                        logger.warning(f"   ⚠️  No OGG files found in {user_dir}")
                else:
                    logger.warning(f"   ⚠️  User directory not found: {user_dir}")
            
            logger.info(f"🎉 Fixed {fixed_count} encrypted paths")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error fixing encrypted paths: {str(e)}")
            return False
    
    def test_fixed_paths(self):
        """Test that the fixed paths work."""
        logger.info("🧪 Testing fixed encrypted paths...")
        
        try:
            # Get one audio segment
            result = self.supabase.table("audio_segments").select("*").limit(1).execute()
            
            if result.data:
                segment = result.data[0]
                encrypted_path = segment["file_path"]
                
                # Try to decrypt
                decrypted_path = self.encryption_service.decrypt(encrypted_path)
                logger.info(f"   Decrypted path: {decrypted_path}")
                
                if os.path.exists(decrypted_path):
                    logger.info("   ✅ File exists at decrypted path")
                    return True
                else:
                    logger.error("   ❌ File does not exist at decrypted path")
                    return False
            else:
                logger.info("   ✅ No audio segments to test")
                return True
                
        except Exception as e:
            logger.error(f"   ❌ Error testing fixed paths: {str(e)}")
            return False
    
    def run_fix(self):
        """Run the complete fix."""
        logger.info("🚀 Starting encrypted paths fix...")
        
        # Step 1: Fix encrypted paths
        logger.info("\n📋 Step 1: Fixing Encrypted Paths")
        if self.fix_encrypted_paths():
            logger.info("✅ Encrypted paths fix PASSED")
        else:
            logger.error("❌ Encrypted paths fix FAILED")
            return False
        
        # Step 2: Test fixed paths
        logger.info("\n📋 Step 2: Testing Fixed Paths")
        if self.test_fixed_paths():
            logger.info("✅ Fixed paths test PASSED")
        else:
            logger.error("❌ Fixed paths test FAILED")
            return False
        
        logger.info("\n🎉 Encrypted paths fix completed successfully!")
        return True

def main():
    try:
        fixer = EncryptedPathsFixer()
        success = fixer.run_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Fix failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
