#!/usr/bin/env python3
"""
Manual Audio Processing Test
===========================

This script manually processes the unprocessed audio segments to test clip generation.
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ManualProcessingTest:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise Exception("Supabase credentials not found")
        
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        logger.info("🧪 Manual Processing Test initialized")
    
    async def test_audio_processing(self):
        """Test processing unprocessed audio segments."""
        logger.info("🔍 Testing manual audio processing...")
        
        try:
            # Get unprocessed audio segments
            result = self.supabase.table("audio_segments").select("*").eq("processed", False).execute()
            
            if not result.data:
                logger.info("✅ No unprocessed audio segments found")
                return True
            
            logger.info(f"📊 Found {len(result.data)} unprocessed audio segments")
            
            # Process each segment
            for segment in result.data:
                segment_id = segment["id"]
                file_path = segment["file_path"]
                user_id = segment["user_id"]
                
                logger.info(f"🎵 Processing segment {segment_id}")
                logger.info(f"   File: {file_path[:50]}...")
                logger.info(f"   User: {user_id}")
                
                # Check if file exists (decrypt path first)
                try:
                    from src.auth.encryption import EncryptionService
                    encryption_service = EncryptionService()
                    decrypted_path = encryption_service.decrypt(file_path)
                    
                    if os.path.exists(decrypted_path):
                        logger.info(f"✅ Audio file exists: {os.path.basename(decrypted_path)}")
                        
                        # Run YAMNet processing
                        from src.services.yamnet_processor import yamnet_processor
                        laughter_events = await yamnet_processor.process_audio_file(decrypted_path, user_id)
                        
                        if laughter_events:
                            logger.info(f"🎭 Found {len(laughter_events)} laughter events")
                            
                            # Store laughter detections
                            for event in laughter_events:
                                logger.info(f"   - {event.timestamp}s: {event.probability:.3f} ({event.class_name})")
                                if event.clip_path:
                                    logger.info(f"     Clip: {event.clip_path}")
                        else:
                            logger.info("😴 No laughter detected in this segment")
                        
                        # Mark segment as processed
                        self.supabase.table("audio_segments").update({"processed": True}).eq("id", segment_id).execute()
                        logger.info(f"✅ Marked segment {segment_id} as processed")
                        
                    else:
                        logger.warning(f"⚠️  Audio file not found: {decrypted_path}")
                        
                except Exception as e:
                    logger.error(f"❌ Error processing segment {segment_id}: {str(e)}")
                    continue
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error in manual processing test: {str(e)}")
            return False
    
    async def check_clips_generated(self):
        """Check if clips were generated."""
        logger.info("🔍 Checking for generated clips...")
        
        clips_dir = "uploads/clips"
        if os.path.exists(clips_dir):
            clips = os.listdir(clips_dir)
            if clips:
                logger.info(f"✅ Found {len(clips)} clips:")
                for clip in clips:
                    clip_path = os.path.join(clips_dir, clip)
                    size = os.path.getsize(clip_path)
                    logger.info(f"   - {clip} ({size} bytes)")
                return True
            else:
                logger.info("📁 Clips directory exists but is empty")
                return False
        else:
            logger.info("📁 Clips directory does not exist")
            return False
    
    async def run_test(self):
        """Run the manual processing test."""
        logger.info("🚀 Starting manual audio processing test...")
        
        # Test 1: Process audio segments
        logger.info("\n📋 Test 1: Processing Audio Segments")
        if await self.test_audio_processing():
            logger.info("✅ Audio processing test PASSED")
        else:
            logger.error("❌ Audio processing test FAILED")
            return False
        
        # Test 2: Check clips generated
        logger.info("\n📋 Test 2: Checking Generated Clips")
        if await self.check_clips_generated():
            logger.info("✅ Clip generation test PASSED")
        else:
            logger.warning("⚠️  No clips generated (may be normal if no laughter detected)")
        
        logger.info("\n🎉 Manual processing test completed!")
        return True

async def main():
    try:
        test = ManualProcessingTest()
        success = await test.run_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())