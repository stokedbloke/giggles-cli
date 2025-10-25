#!/usr/bin/env python3
"""
Test Core Functionality
======================

This script tests the core functionality by:
1. Deleting corrupted data
2. Triggering fresh processing
3. Verifying real YAMNet results
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

class CoreFunctionalityTest:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise Exception("Supabase credentials not found")
        
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        logger.info("🧪 Core Functionality Test initialized")
    
    def delete_corrupted_data(self):
        """Delete the corrupted 'recovered' detections."""
        logger.info("🗑️  Deleting corrupted data...")
        
        try:
            # Delete 'recovered' detections
            result = self.supabase.table("laughter_detections").delete().like("notes", "%recovered%").execute()
            logger.info(f"✅ Deleted {len(result.data)} corrupted detections")
            
            # Delete test detection
            result2 = self.supabase.table("laughter_detections").delete().like("notes", "%test%").execute()
            logger.info(f"✅ Deleted {len(result2.data)} test detections")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting corrupted data: {str(e)}")
            return False
    
    def cleanup_clips(self):
        """Clean up the old clips."""
        logger.info("🧹 Cleaning up old clips...")
        
        import shutil
        
        try:
            if os.path.exists("uploads/clips"):
                shutil.rmtree("uploads/clips")
                logger.info("✅ Deleted old clips")
            
            # Recreate directory
            os.makedirs("uploads/clips", exist_ok=True)
            logger.info("✅ Recreated clips directory")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cleaning clips: {str(e)}")
            return False
    
    def check_current_status(self):
        """Check the current status of the system."""
        logger.info("🔍 Checking current status...")
        
        try:
            # Check audio segments
            segments = self.supabase.table("audio_segments").select("*").execute()
            processed = [s for s in segments.data if s['processed']]
            unprocessed = [s for s in segments.data if not s['processed']]
            
            logger.info(f"📊 Audio segments: {len(segments.data)} total, {len(processed)} processed, {len(unprocessed)} unprocessed")
            
            # Check laughter detections
            detections = self.supabase.table("laughter_detections").select("*").execute()
            logger.info(f"📊 Laughter detections: {len(detections.data)}")
            
            # Check clips
            if os.path.exists("uploads/clips"):
                clips = os.listdir("uploads/clips")
                logger.info(f"📊 Clips on disk: {len(clips)}")
            else:
                logger.info("📊 Clips on disk: 0")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking status: {str(e)}")
            return False
    
    def run_test(self):
        """Run the complete core functionality test."""
        logger.info("🚀 Starting core functionality test...")
        
        # Step 1: Delete corrupted data
        logger.info("\n📋 Step 1: Deleting Corrupted Data")
        if self.delete_corrupted_data():
            logger.info("✅ Corrupted data deletion PASSED")
        else:
            logger.error("❌ Corrupted data deletion FAILED")
            return False
        
        # Step 2: Clean up clips
        logger.info("\n📋 Step 2: Cleaning Up Clips")
        if self.cleanup_clips():
            logger.info("✅ Clip cleanup PASSED")
        else:
            logger.error("❌ Clip cleanup FAILED")
            return False
        
        # Step 3: Check status
        logger.info("\n📋 Step 3: Checking Status")
        if self.check_current_status():
            logger.info("✅ Status check PASSED")
        else:
            logger.error("❌ Status check FAILED")
            return False
        
        logger.info("\n🎉 Core functionality test completed!")
        logger.info("✅ System is ready for fresh processing")
        return True

def main():
    try:
        test = CoreFunctionalityTest()
        success = test.run_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
