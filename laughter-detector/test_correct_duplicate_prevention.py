#!/usr/bin/env python3
"""
Correct Duplicate Prevention Test
=================================

This script tests the CORRECT duplicate prevention system:
- Duplicates detected on EXACT timestamps
- No time windows or probability variance nonsense
- Simple, clear logic
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client
import uuid

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CorrectDuplicateTest:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise Exception("Supabase credentials not found")
        
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        logger.info("🧪 Correct Duplicate Prevention Test initialized")
    
    def test_exact_timestamp_duplicates(self):
        """Test duplicate prevention on EXACT timestamps."""
        logger.info("🔍 Testing exact timestamp duplicate prevention...")
        
        # Get a test user
        users = self.supabase.table("users").select("id").limit(1).execute()
        if not users.data:
            logger.error("❌ No users found for testing")
            return False
        
        user_id = users.data[0]["id"]
        logger.info(f"👤 Using test user: {user_id}")
        
        # Get a real audio segment for testing
        audio_segments = self.supabase.table("audio_segments").select("id").eq("user_id", user_id).limit(1).execute()
        if not audio_segments.data:
            logger.error("❌ No audio segments found for testing")
            return False
        
        audio_segment_id = audio_segments.data[0]["id"]
        logger.info(f"🎵 Using audio segment: {audio_segment_id}")
        
        # Create test laughter detections with EXACT same timestamp
        test_timestamp = datetime.now()
        test_detections = [
            {
                "user_id": user_id,
                "audio_segment_id": audio_segment_id,
                "timestamp": test_timestamp.isoformat(),
                "probability": 0.85,
                "clip_path": "test-clip-1.wav",
                "notes": "Test detection 1"
            },
            {
                "user_id": user_id,
                "audio_segment_id": audio_segment_id,
                "timestamp": test_timestamp.isoformat(),  # EXACT same timestamp
                "probability": 0.90,  # Different probability (shouldn't matter)
                "clip_path": "test-clip-2.wav",
                "notes": "Test detection 2 (exact duplicate)"
            }
        ]
        
        # Test 1: Insert first detection
        logger.info("📝 Test 1: Inserting first detection...")
        try:
            result = self.supabase.table("laughter_detections").insert(test_detections[0]).execute()
            logger.info(f"✅ First detection inserted: {result.data[0]['id']}")
        except Exception as e:
            logger.error(f"❌ Failed to insert first detection: {str(e)}")
            return False
        
        # Test 2: Try to insert EXACT timestamp duplicate (should be prevented)
        logger.info("📝 Test 2: Testing exact timestamp duplicate prevention...")
        try:
            result = self.supabase.table("laughter_detections").insert(test_detections[1]).execute()
            logger.warning(f"⚠️  Exact timestamp duplicate was NOT prevented: {result.data[0]['id']}")
            return False
        except Exception as e:
            if "unique_laughter_timestamp_user" in str(e) or "duplicate" in str(e).lower():
                logger.info(f"✅ Exact timestamp duplicate prevention working: {str(e)}")
            else:
                logger.error(f"❌ Unexpected error: {str(e)}")
                return False
        
        return True
    
    def test_clip_path_duplicates(self):
        """Test clip path duplicate prevention."""
        logger.info("🔍 Testing clip path duplicate prevention...")
        
        # Get a test user
        users = self.supabase.table("users").select("id").limit(1).execute()
        if not users.data:
            logger.error("❌ No users found for testing")
            return False
        
        user_id = users.data[0]["id"]
        
        # Get a real audio segment for testing
        audio_segments = self.supabase.table("audio_segments").select("id").eq("user_id", user_id).limit(1).execute()
        if not audio_segments.data:
            logger.error("❌ No audio segments found for testing")
            return False
        
        audio_segment_id = audio_segments.data[0]["id"]
        
        # Test clip path uniqueness
        test_clip_path = "test-duplicate-clip.wav"
        test_timestamp = datetime.now() + timedelta(minutes=1)  # Different timestamp
        
        # Try to insert with same clip path
        try:
            result = self.supabase.table("laughter_detections").insert({
                "user_id": user_id,
                "audio_segment_id": audio_segment_id,
                "timestamp": test_timestamp.isoformat(),
                "probability": 0.80,
                "clip_path": test_clip_path,
                "notes": "Test clip path duplicate"
            }).execute()
            
            logger.warning(f"⚠️  Clip path duplicate was NOT prevented: {result.data[0]['id']}")
            return False
        except Exception as e:
            if "unique_laughter_clip_path" in str(e) or "duplicate" in str(e).lower():
                logger.info(f"✅ Clip path duplicate prevention working: {str(e)}")
                return True
            else:
                logger.error(f"❌ Unexpected error: {str(e)}")
                return False
    
    def test_different_timestamps_allowed(self):
        """Test that different timestamps are allowed (not duplicates)."""
        logger.info("🔍 Testing that different timestamps are allowed...")
        
        # Get a test user
        users = self.supabase.table("users").select("id").limit(1).execute()
        if not users.data:
            logger.error("❌ No users found for testing")
            return False
        
        user_id = users.data[0]["id"]
        
        # Get a real audio segment for testing
        audio_segments = self.supabase.table("audio_segments").select("id").eq("user_id", user_id).limit(1).execute()
        if not audio_segments.data:
            logger.error("❌ No audio segments found for testing")
            return False
        
        audio_segment_id = audio_segments.data[0]["id"]
        
        # Create detections with different timestamps (should be allowed)
        timestamp1 = datetime.now()
        timestamp2 = timestamp1 + timedelta(seconds=10)  # 10 seconds later
        
        try:
            # Insert first detection
            result1 = self.supabase.table("laughter_detections").insert({
                "user_id": user_id,
                "audio_segment_id": audio_segment_id,
                "timestamp": timestamp1.isoformat(),
                "probability": 0.85,
                "clip_path": "test-clip-3.wav",
                "notes": "Test detection 1 (different time)"
            }).execute()
            
            # Insert second detection with different timestamp (should work)
            result2 = self.supabase.table("laughter_detections").insert({
                "user_id": user_id,
                "audio_segment_id": audio_segment_id,
                "timestamp": timestamp2.isoformat(),
                "probability": 0.90,
                "clip_path": "test-clip-4.wav",
                "notes": "Test detection 2 (different time)"
            }).execute()
            
            logger.info(f"✅ Different timestamps allowed: {result1.data[0]['id']}, {result2.data[0]['id']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Different timestamps should be allowed: {str(e)}")
            return False
    
    def cleanup_test_data(self):
        """Clean up test data."""
        logger.info("🧹 Cleaning up test data...")
        
        try:
            # Delete test laughter detections
            result = self.supabase.table("laughter_detections").delete().like("notes", "Test detection%").execute()
            logger.info(f"🗑️  Deleted {len(result.data)} test detections")
        except Exception as e:
            logger.error(f"❌ Error cleaning up test data: {str(e)}")
    
    def run_tests(self):
        """Run all correct duplicate prevention tests."""
        logger.info("🚀 Starting correct duplicate prevention tests...")
        
        tests_passed = 0
        total_tests = 3
        
        # Test 1: Exact timestamp duplicates
        logger.info("\n📋 Test 1: Exact Timestamp Duplicates")
        if self.test_exact_timestamp_duplicates():
            logger.info("✅ Exact timestamp duplicate prevention test PASSED")
            tests_passed += 1
        else:
            logger.error("❌ Exact timestamp duplicate prevention test FAILED")
        
        # Test 2: Clip path duplicates
        logger.info("\n📋 Test 2: Clip Path Duplicates")
        if self.test_clip_path_duplicates():
            logger.info("✅ Clip path duplicate prevention test PASSED")
            tests_passed += 1
        else:
            logger.error("❌ Clip path duplicate prevention test FAILED")
        
        # Test 3: Different timestamps allowed
        logger.info("\n📋 Test 3: Different Timestamps Allowed")
        if self.test_different_timestamps_allowed():
            logger.info("✅ Different timestamps allowed test PASSED")
            tests_passed += 1
        else:
            logger.error("❌ Different timestamps allowed test FAILED")
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        logger.info(f"\n📊 TEST SUMMARY")
        logger.info(f"   Tests passed: {tests_passed}/{total_tests}")
        logger.info(f"   Success rate: {(tests_passed/total_tests)*100:.1f}%")
        
        if tests_passed == total_tests:
            logger.info("🎉 All correct duplicate prevention tests PASSED!")
            return True
        else:
            logger.error("❌ Some correct duplicate prevention tests FAILED!")
            return False

def main():
    try:
        test = CorrectDuplicateTest()
        success = test.run_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
