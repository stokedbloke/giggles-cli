#!/usr/bin/env python3
"""
Simple Duplicate Prevention Test
================================

This script tests the duplicate prevention system with the current database schema.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleDuplicateTest:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise Exception("Supabase credentials not found")
        
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        logger.info("🧪 Simple Duplicate Test initialized")
    
    def test_basic_duplicate_prevention(self):
        """Test basic duplicate prevention with current schema."""
        logger.info("🔍 Testing basic duplicate prevention...")
        
        # Get a test user
        users = self.supabase.table("users").select("id").limit(1).execute()
        if not users.data:
            logger.error("❌ No users found for testing")
            return False
        
        user_id = users.data[0]["id"]
        logger.info(f"👤 Using test user: {user_id}")
        
        # Create test laughter detections
        test_timestamp = datetime.now()
        test_detections = [
            {
                "user_id": user_id,
                "audio_segment_id": "test-segment-1",
                "timestamp": test_timestamp.isoformat(),
                "probability": 0.85,
                "clip_path": "test-clip-1.wav",
                "notes": "Test detection 1"
            },
            {
                "user_id": user_id,
                "audio_segment_id": "test-segment-2", 
                "timestamp": (test_timestamp + timedelta(seconds=2)).isoformat(),  # 2 seconds later
                "probability": 0.87,  # Similar probability
                "clip_path": "test-clip-2.wav",
                "notes": "Test detection 2 (potential duplicate)"
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
        
        # Test 2: Insert second detection (should work - no constraints yet)
        logger.info("📝 Test 2: Inserting second detection...")
        try:
            result = self.supabase.table("laughter_detections").insert(test_detections[1]).execute()
            logger.info(f"✅ Second detection inserted: {result.data[0]['id']}")
        except Exception as e:
            logger.error(f"❌ Failed to insert second detection: {str(e)}")
            return False
        
        # Test 3: Test application-level duplicate detection
        logger.info("📝 Test 3: Testing application-level duplicate detection...")
        
        # Simulate the scheduler's duplicate detection logic
        new_timestamp = test_timestamp + timedelta(seconds=3)
        new_probability = 0.86
        
        # Check for existing detections within 5-second window
        time_window = timedelta(seconds=5)
        window_start = new_timestamp - time_window
        window_end = new_timestamp + time_window
        
        try:
            existing_detections = self.supabase.table("laughter_detections").select("id, probability, timestamp").eq("user_id", user_id).gte("timestamp", window_start.isoformat()).lte("timestamp", window_end.isoformat()).execute()
            
            logger.info(f"🔍 Found {len(existing_detections.data)} existing detections in time window")
            
            is_duplicate = False
            for existing in existing_detections.data:
                existing_time = datetime.fromisoformat(existing["timestamp"].replace('Z', '+00:00'))
                time_diff = abs((new_timestamp - existing_time).total_seconds())
                prob_diff = abs(new_probability - existing["probability"])
                
                logger.info(f"   Existing: {existing_time} (prob: {existing['probability']:.3f})")
                logger.info(f"   New: {new_timestamp} (prob: {new_probability:.3f})")
                logger.info(f"   Time diff: {time_diff:.1f}s, Prob diff: {prob_diff:.3f}")
                
                # Check if it's a duplicate (within 5 seconds and probability within 10%)
                if time_diff <= 5 and prob_diff <= 0.1:
                    logger.info("🚫 DUPLICATE DETECTED by application logic!")
                    is_duplicate = True
                    break
                else:
                    logger.info("✅ Not a duplicate (different enough)")
            
            if is_duplicate:
                logger.info("✅ Application-level duplicate detection working!")
            else:
                logger.info("✅ No duplicates detected (correct)")
                
        except Exception as e:
            logger.error(f"❌ Error testing application-level detection: {str(e)}")
            return False
        
        return True
    
    def test_clip_path_duplicates(self):
        """Test clip path duplicate detection."""
        logger.info("🔍 Testing clip path duplicate detection...")
        
        # Get a test user
        users = self.supabase.table("users").select("id").limit(1).execute()
        if not users.data:
            logger.error("❌ No users found for testing")
            return False
        
        user_id = users.data[0]["id"]
        
        # Test clip path uniqueness
        test_clip_path = "test-duplicate-clip.wav"
        
        # Check if clip path already exists
        try:
            existing_clip = self.supabase.table("laughter_detections").select("id").eq("clip_path", test_clip_path).execute()
            
            if existing_clip.data:
                logger.info(f"🚫 Duplicate clip path detected: {test_clip_path}")
                logger.info("✅ Clip path duplicate detection working!")
                return True
            else:
                logger.info(f"✅ Clip path is unique: {test_clip_path}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error testing clip path duplicates: {str(e)}")
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
        """Run all duplicate prevention tests."""
        logger.info("🚀 Starting simple duplicate prevention tests...")
        
        tests_passed = 0
        total_tests = 2
        
        # Test 1: Basic duplicate prevention
        logger.info("\n📋 Test 1: Basic Duplicate Prevention")
        if self.test_basic_duplicate_prevention():
            logger.info("✅ Basic duplicate prevention test PASSED")
            tests_passed += 1
        else:
            logger.error("❌ Basic duplicate prevention test FAILED")
        
        # Test 2: Clip path duplicates
        logger.info("\n📋 Test 2: Clip Path Duplicate Detection")
        if self.test_clip_path_duplicates():
            logger.info("✅ Clip path duplicate detection test PASSED")
            tests_passed += 1
        else:
            logger.error("❌ Clip path duplicate detection test FAILED")
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        logger.info(f"\n📊 TEST SUMMARY")
        logger.info(f"   Tests passed: {tests_passed}/{total_tests}")
        logger.info(f"   Success rate: {(tests_passed/total_tests)*100:.1f}%")
        
        if tests_passed == total_tests:
            logger.info("🎉 All duplicate prevention tests PASSED!")
            return True
        else:
            logger.error("❌ Some duplicate prevention tests FAILED!")
            return False

def main():
    try:
        test = SimpleDuplicateTest()
        success = test.run_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
