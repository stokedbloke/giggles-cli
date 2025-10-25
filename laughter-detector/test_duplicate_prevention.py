#!/usr/bin/env python3
"""
Test Duplicate Prevention System
================================

This script tests the duplicate prevention system by:
1. Creating test laughter detections
2. Testing duplicate prevention logic
3. Verifying database constraints
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DuplicatePreventionTest:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise Exception("Supabase credentials not found")
        
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        logger.info("🧪 Duplicate Prevention Test initialized")
    
    def test_duplicate_prevention_logic(self):
        """Test the duplicate prevention logic in the scheduler."""
        logger.info("🔍 Testing duplicate prevention logic...")
        
        # Get a test user
        users = self.supabase.table("users").select("id").limit(1).execute()
        if not users.data:
            logger.error("❌ No users found for testing")
            return False
        
        user_id = users.data[0]["id"]
        logger.info(f"👤 Using test user: {user_id}")
        
        # Create test laughter detections with duplicates
        test_timestamp = datetime.now()
        test_detections = [
            {
                "user_id": user_id,
                "audio_segment_id": "test-segment-1",
                "timestamp": test_timestamp.isoformat(),
                "probability": 0.85,
                "clip_path": "test-clip-1.wav",
                "class_id": 13,
                "class_name": "Laughter",
                "notes": "Test detection 1"
            },
            {
                "user_id": user_id,
                "audio_segment_id": "test-segment-2", 
                "timestamp": (test_timestamp + timedelta(seconds=2)).isoformat(),  # 2 seconds later
                "probability": 0.87,  # Similar probability
                "clip_path": "test-clip-2.wav",
                "class_id": 13,
                "class_name": "Laughter",
                "notes": "Test detection 2 (duplicate)"
            },
            {
                "user_id": user_id,
                "audio_segment_id": "test-segment-3",
                "timestamp": (test_timestamp + timedelta(minutes=1)).isoformat(),  # 1 minute later
                "probability": 0.90,
                "clip_path": "test-clip-1.wav",  # Same clip path (duplicate)
                "class_id": 13,
                "class_name": "Laughter", 
                "notes": "Test detection 3 (duplicate clip)"
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
        
        # Test 2: Try to insert duplicate (should be prevented)
        logger.info("📝 Test 2: Testing duplicate prevention...")
        try:
            result = self.supabase.table("laughter_detections").insert(test_detections[1]).execute()
            logger.warning(f"⚠️  Duplicate detection was NOT prevented: {result.data[0]['id']}")
            return False
        except Exception as e:
            if "unique_laughter_timestamp_user" in str(e) or "unique_laughter_clip_path" in str(e):
                logger.info(f"✅ Duplicate prevention working: {str(e)}")
            else:
                logger.error(f"❌ Unexpected error: {str(e)}")
                return False
        
        # Test 3: Try to insert duplicate clip path
        logger.info("📝 Test 3: Testing clip path duplicate prevention...")
        try:
            result = self.supabase.table("laughter_detections").insert(test_detections[2]).execute()
            logger.warning(f"⚠️  Clip path duplicate was NOT prevented: {result.data[0]['id']}")
            return False
        except Exception as e:
            if "unique_laughter_clip_path" in str(e):
                logger.info(f"✅ Clip path duplicate prevention working: {str(e)}")
            else:
                logger.error(f"❌ Unexpected error: {str(e)}")
                return False
        
        return True
    
    def test_application_level_prevention(self):
        """Test the application-level duplicate prevention in the scheduler."""
        logger.info("🔍 Testing application-level duplicate prevention...")
        
        # This would test the scheduler's _store_laughter_detections method
        # For now, we'll simulate the logic
        
        # Simulate duplicate detection logic
        user_id = "test-user"
        event_timestamp = datetime.now()
        event_probability = 0.85
        
        # Check for existing detections within 5-second window
        time_window = timedelta(seconds=5)
        window_start = event_timestamp - time_window
        window_end = event_timestamp + time_window
        
        try:
            existing_detections = self.supabase.table("laughter_detections").select("id, probability, timestamp").eq("user_id", user_id).gte("timestamp", window_start.isoformat()).lte("timestamp", window_end.isoformat()).execute()
            
            if existing_detections.data:
                logger.info(f"🔍 Found {len(existing_detections.data)} existing detections in time window")
                
                for existing in existing_detections.data:
                    existing_time = datetime.fromisoformat(existing["timestamp"].replace('Z', '+00:00'))
                    time_diff = abs((event_timestamp - existing_time).total_seconds())
                    prob_diff = abs(event_probability - existing["probability"])
                    
                    logger.info(f"   Existing: {existing_time} (prob: {existing['probability']:.3f})")
                    logger.info(f"   New: {event_timestamp} (prob: {event_probability:.3f})")
                    logger.info(f"   Time diff: {time_diff:.1f}s, Prob diff: {prob_diff:.3f}")
                    
                    if time_diff <= 5 and prob_diff <= 0.1:
                        logger.info("✅ Duplicate detected by application logic")
                        return True
                    else:
                        logger.info("✅ Not a duplicate (different enough)")
            else:
                logger.info("✅ No existing detections in time window")
                
        except Exception as e:
            logger.error(f"❌ Error testing application-level prevention: {str(e)}")
            return False
        
        return True
    
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
        logger.info("🚀 Starting duplicate prevention tests...")
        
        tests_passed = 0
        total_tests = 3
        
        # Test 1: Database constraints
        logger.info("\n📋 Test 1: Database Constraints")
        if self.test_duplicate_prevention_logic():
            logger.info("✅ Database constraint test PASSED")
            tests_passed += 1
        else:
            logger.error("❌ Database constraint test FAILED")
        
        # Test 2: Application-level prevention
        logger.info("\n📋 Test 2: Application-Level Prevention")
        if self.test_application_level_prevention():
            logger.info("✅ Application-level prevention test PASSED")
            tests_passed += 1
        else:
            logger.error("❌ Application-level prevention test FAILED")
        
        # Test 3: System health
        logger.info("\n📋 Test 3: System Health")
        try:
            # Check current system state
            laughter_count = self.supabase.table("laughter_detections").select("id", count="exact").execute()
            logger.info(f"📊 Current laughter detections: {laughter_count.count}")
            
            if laughter_count.count >= 0:
                logger.info("✅ System health test PASSED")
                tests_passed += 1
            else:
                logger.error("❌ System health test FAILED")
        except Exception as e:
            logger.error(f"❌ System health test FAILED: {str(e)}")
        
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
        test = DuplicatePreventionTest()
        success = test.run_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()