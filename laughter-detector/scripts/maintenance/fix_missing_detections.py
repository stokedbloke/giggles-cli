#!/usr/bin/env python3
"""
Fix Missing Laughter Detections
===============================

This script fixes the issue where real laughter detections were generated
but not stored in the database due to the manual processing bypass.
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

class MissingDetectionsFixer:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise Exception("Supabase credentials not found")
        
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        self.encryption_service = EncryptionService()
        logger.info("🔧 Missing Detections Fixer initialized")
    
    def analyze_clips_vs_database(self):
        """Analyze the discrepancy between clips and database."""
        logger.info("🔍 Analyzing clips vs database...")
        
        # Check clips on disk
        clips_dir = "uploads/clips"
        if os.path.exists(clips_dir):
            clips = [f for f in os.listdir(clips_dir) if f.endswith('.wav')]
            logger.info(f"📁 Found {len(clips)} clips on disk")
            
            for clip in clips:
                logger.info(f"   - {clip}")
        else:
            logger.info("📁 No clips directory found")
            return False
        
        # Check database detections
        result = self.supabase.table("laughter_detections").select("*").execute()
        logger.info(f"📊 Found {len(result.data)} detections in database")
        
        for detection in result.data:
            logger.info(f"   - {detection['timestamp']}: {detection.get('clip_path', 'NULL')}")
        
        return True
    
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
                # Create the detection record
                detection_data = {
                    "user_id": detection['user_id'],
                    "audio_segment_id": detection['audio_segment_id'],
                    "timestamp": f"2025-10-25T{int(detection['timestamp']//3600):02d}:{int((detection['timestamp']%3600)//60):02d}:{int(detection['timestamp']%60):02d}.000000+00:00",
                    "probability": 0.5,  # Default probability (we don't have the actual value)
                    "clip_path": f"uploads/clips/{detection['clip_filename']}",
                    "class_id": 137,  # Laughter class ID from YAMNet
                    "class_name": "Laughter",
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
        logger.info("🚀 Starting missing detections fix...")
        
        # Step 1: Analyze current state
        logger.info("\n📋 Step 1: Analyzing Current State")
        if not self.analyze_clips_vs_database():
            logger.error("❌ Analysis failed")
            return False
        
        # Step 2: Extract detection info from clips
        logger.info("\n📋 Step 2: Extracting Detection Info")
        detections = self.extract_detection_info_from_clips()
        
        if not detections:
            logger.warning("⚠️  No detections to store")
            return True
        
        # Step 3: Store missing detections
        logger.info("\n📋 Step 3: Storing Missing Detections")
        stored_count = self.store_missing_detections(detections)
        
        if stored_count > 0:
            logger.info(f"✅ Successfully stored {stored_count} missing detections")
            return True
        else:
            logger.warning("⚠️  No detections were stored")
            return False

def main():
    try:
        fixer = MissingDetectionsFixer()
        success = fixer.run_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Fix failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
