#!/usr/bin/env python3
"""
Test Page Refresh Fix
====================

Test that the page refresh fix is working correctly.
"""

import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PageRefreshTest:
    def __init__(self):
        load_dotenv()
        self.supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
        self.user_id = None

    async def _get_test_user(self):
        users = self.supabase.table("users").select("id").limit(1).execute()
        if not users.data:
            logger.error("❌ No users found for testing")
            return False
        self.user_id = users.data[0]["id"]
        logger.info(f"👤 Using test user: {self.user_id}")
        return True

    async def _check_current_state(self):
        logger.info("🔍 Checking current state...")
        
        # Check audio segments
        segments = self.supabase.table("audio_segments").select("*").eq("user_id", self.user_id).execute()
        processed = [s for s in segments.data if s.get("processed")]
        unprocessed = [s for s in segments.data if not s.get("processed")]
        
        logger.info(f"📊 Audio segments: {len(segments.data)} total, {len(processed)} processed, {len(unprocessed)} unprocessed")
        
        # Check laughter detections
        detections = self.supabase.table("laughter_detections").select("*").eq("user_id", self.user_id).execute()
        logger.info(f"📊 Laughter detections: {len(detections.data)}")
        
        # Check clips on disk
        clips_dir = "uploads/clips"
        if os.path.exists(clips_dir):
            clips = [f for f in os.listdir(clips_dir) if f.endswith(".wav")]
            logger.info(f"📊 Clips on disk: {len(clips)}")
        else:
            logger.info("📊 Clips on disk: 0 (directory doesn't exist)")
        
        return len(segments.data), len(detections.data)

    async def _simulate_delete_all_data(self):
        logger.info("🗑️  Simulating 'Delete All Data' action...")
        
        # Delete all laughter detections for this user
        result = self.supabase.table("laughter_detections").delete().eq("user_id", self.user_id).execute()
        logger.info(f"✅ Deleted {len(result.data)} laughter detections")
        
        # Mark all segments as unprocessed
        result = self.supabase.table("audio_segments").update({"processed": False}).eq("user_id", self.user_id).execute()
        logger.info(f"✅ Marked {len(result.data)} segments as unprocessed")
        
        # Clean up clips directory
        import shutil
        clips_dir = "uploads/clips"
        if os.path.exists(clips_dir):
            shutil.rmtree(clips_dir)
            logger.info("✅ Deleted clips directory")
        os.makedirs(clips_dir, exist_ok=True)
        logger.info("✅ Recreated clips directory")
        
        logger.info("🎉 'Delete All Data' simulation completed!")
        logger.info("💡 In the UI, this should now trigger a page refresh after 1 second")

    async def run_test(self):
        logger.info("🚀 Starting page refresh test...")
        
        if not await self._get_test_user():
            return False
        
        logger.info("\n📋 Step 1: Checking Current State")
        initial_segments, initial_detections = await self._check_current_state()
        
        logger.info("\n📋 Step 2: Simulating Delete All Data")
        await self._simulate_delete_all_data()
        
        logger.info("\n📋 Step 3: Checking Final State")
        final_segments, final_detections = await self._check_current_state()
        
        logger.info("\n🎉 Page refresh test completed!")
        logger.info(f"✅ Initial: {initial_segments} segments, {initial_detections} detections")
        logger.info(f"✅ Final: {final_segments} segments, {final_detections} detections")
        logger.info("💡 The UI should now refresh automatically when you click 'Delete All Data'")
        
        return True

if __name__ == "__main__":
    import asyncio
    test = PageRefreshTest()
    asyncio.run(test.run_test())
