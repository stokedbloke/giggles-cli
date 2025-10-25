#!/usr/bin/env python3
"""
Fix Missing Laughter Detections (Simple Version)
===============================================

This script fixes the issue where real laughter detections were generated
but not stored in the database, without requiring class_id/class_name columns.
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

class SimpleMissingDetectionsFixer:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise Exception("Supabase credentials not found")
        
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        self.encryption_service = EncryptionService()
        logger.info("🔧 Simple Missing Detections Fixer initialized")
    
    def extract_detection_info_from_clips(self):
        """Extract detection information from clip filenames."""
        logger.info("🔍 Extracting detection info from clips...")
        
        clips_dir = "uploads/clips"
        if not os.path.exists(clips_dir):
            logger.error("❌ Clips directory not found")
            return []
        
        clips = [f for f in os.listdir(clips_dir) if f.endswith('.wav')]
        detections = []
        
        for clip in clips:
            # Parse filename: 20251025_001628-20251025_021628_laughter_410.wav
            try:
                parts = clip.replace('.wav', '').split('_laughter_')
                if len(parts) == 2:
                    base_name = parts[0]
                    timestamp = float(parts[1])
                    
                    # Get audio segment ID from the base name
                    audio_segments = self.supabase.table("audio_segments").select("*").execute()
                    matching_segment = None
                    
                    for segment in audio_segments.data:
                        # Decrypt and check if this clip belongs to this segment
                        try:
                            decrypted_path = self.encryption_service.decrypt(segment['file_path'])
                            if base_name in decrypted_path:
                                matching_segment = segment
                                break
                        except:
                            continue
                    
                    if matching_segment:
                        detection_info = {
                            'clip_filename': clip,
                            'timestamp': timestamp,
                            'audio_segment_id': matching_segment['id'],
                            'user_id': matching_segment['user_id'],
                            'base_name': base_name
                        }
                        detections.append(detection_info)
                        logger.info(f"   ✅ {clip} -> {timestamp}s (segment: {matching_segment['id']})")
                    else:
                        logger.warning(f"   ⚠️  Could not match {clip} to audio segment")
                        
            except Exception as e:
                logger.error(f"   ❌ Error parsing {clip}: {str(e)}")
        
        return detections
    
    def store_missing_detections(self, detections):
        """Store the missing laughter detections in the database."""
        logger.info(f"💾 Storing {len(detections)} missing detections...")
        
        stored_count = 0
        
        for detection in detections:
            try:
                # Create timestamp in proper format
                hours = int(detection['timestamp'] // 3600)
                minutes = int((detection['timestamp'] % 3600) // 60)
                seconds = int(detection['timestamp'] % 60)
                
                timestamp_str = f"2025-10-25T{hours:02d}:{minutes:02d}:{seconds:02d}.000000+00:00"
                
                # Create the detection record (without class_id/class_name)
                detection_data = {
                    "user_id": detection['user_id'],
                    "audio_segment_id": detection['audio_segment_id'],
                    "timestamp": timestamp_str,
                    "probability": 0.5,  # Default probability
                    "clip_path": f"uploads/clips/{detection['clip_filename']}",
                    "notes": "Recovered from manual processing"
                }
                
                # Store in database
                result = self.supabase.table("laughter_detections").insert(detection_data).execute()
                
                if result.data:
                    logger.info(f"   ✅ Stored detection: {detection['clip_filename']}")
                    stored_count += 1
                else:
                    logger.error(f"   ❌ Failed to store: {detection['clip_filename']}")
                    
            except Exception as e:
                logger.error(f"   ❌ Error storing {detection['clip_filename']}: {str(e)}")
        
        logger.info(f"🎉 Successfully stored {stored_count} missing detections")
        return stored_count
    
    def run_fix(self):
        """Run the complete fix."""
        logger.info("🚀 Starting simple missing detections fix...")
        
        # Step 1: Extract detection info from clips
        logger.info("\n📋 Step 1: Extracting Detection Info")
        detections = self.extract_detection_info_from_clips()
        
        if not detections:
            logger.warning("⚠️  No detections to store")
            return True
        
        # Step 2: Store missing detections
        logger.info("\n📋 Step 2: Storing Missing Detections")
        stored_count = self.store_missing_detections(detections)
        
        if stored_count > 0:
            logger.info(f"✅ Successfully stored {stored_count} missing detections")
            return True
        else:
            logger.warning("⚠️  No detections were stored")
            return False

def main():
    try:
        fixer = SimpleMissingDetectionsFixer()
        success = fixer.run_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Fix failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
