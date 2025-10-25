#!/usr/bin/env python3
"""
Start Fresh Script
=================

This script deletes all data and starts from scratch.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FreshStart:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise Exception("Supabase credentials not found")
        
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        logger.info("🧹 Fresh Start initialized")
    
    def delete_all_data(self):
        """Delete all data except users and API keys."""
        logger.info("🗑️  Deleting all data...")
        
        try:
            # Delete laughter detections
            result1 = self.supabase.table("laughter_detections").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            logger.info(f"✅ Deleted {len(result1.data)} laughter detections")
            
            # Delete audio segments
            result2 = self.supabase.table("audio_segments").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            logger.info(f"✅ Deleted {len(result2.data)} audio segments")
            
            # Delete processing logs
            result3 = self.supabase.table("processing_logs").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            logger.info(f"✅ Deleted {len(result3.data)} processing logs")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting data: {str(e)}")
            return False
    
    def cleanup_files(self):
        """Clean up audio and clip files."""
        logger.info("🧹 Cleaning up files...")
        
        import shutil
        
        try:
            # Remove audio files
            if os.path.exists("uploads/audio"):
                shutil.rmtree("uploads/audio")
                logger.info("✅ Deleted audio files")
            
            # Remove clip files
            if os.path.exists("uploads/clips"):
                shutil.rmtree("uploads/clips")
                logger.info("✅ Deleted clip files")
            
            # Recreate directories
            os.makedirs("uploads/audio", exist_ok=True)
            os.makedirs("uploads/clips", exist_ok=True)
            logger.info("✅ Recreated directories")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cleaning files: {str(e)}")
            return False
    
    def run_fresh_start(self):
        """Run the complete fresh start."""
        logger.info("🚀 Starting fresh...")
        
        # Step 1: Delete all data
        logger.info("\n📋 Step 1: Deleting All Data")
        if self.delete_all_data():
            logger.info("✅ Data deletion PASSED")
        else:
            logger.error("❌ Data deletion FAILED")
            return False
        
        # Step 2: Clean up files
        logger.info("\n📋 Step 2: Cleaning Up Files")
        if self.cleanup_files():
            logger.info("✅ File cleanup PASSED")
        else:
            logger.error("❌ File cleanup FAILED")
            return False
        
        logger.info("\n🎉 Fresh start completed!")
        logger.info("✅ Ready to start from scratch")
        return True

def main():
    try:
        fresh_start = FreshStart()
        success = fresh_start.run_fresh_start()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Fresh start failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
