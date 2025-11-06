#!/usr/bin/env python3
"""
Fix Timestamps Properly
=======================

This script fixes the incorrect timestamps for the recovered laughter detections.
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

class TimestampFixer:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise Exception("Supabase credentials not found")
        
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        logger.info("🔧 Timestamp Fixer initialized")
    
    def fix_timestamps(self):
        """Fix the incorrect timestamps for recovered detections."""
        logger.info("🔍 Fixing timestamps for recovered detections...")
        
        # Get all laughter detections
        result = self.supabase.table("laughter_detections").select("*").execute()
        
        fixed_count = 0
        
        for detection in result.data:
            if "recovered from manual processing" in detection.get("notes", ""):
                logger.info(f"🔧 Fixing detection: {detection['id']}")
                
                # Parse the clip filename to get correct timestamp
                clip_path = detection.get("clip_path", "")
                if "laughter_" in clip_path:
                    parts = clip_path.split("_laughter_")
                    if len(parts) == 2:
                        base_name = parts[0]
                        laughter_seconds = float(parts[1].replace(".wav", ""))
                        
                        # Parse base name: uploads/clips/20251025_001628-20251025_021628
                        # Extract the start time: 20251025_001628
                        start_part = base_name.split("/")[-1].split("-")[0]  # 20251025_001628
                        date_part, time_part = start_part.split("_")
                        
                        # Convert 001628 to seconds: 0*3600 + 16*60 + 28 = 988 seconds
                        hours = int(time_part[:2])
                        minutes = int(time_part[2:4])
                        seconds = int(time_part[4:6])
                        start_seconds = hours * 3600 + minutes * 60 + seconds
                        
                        # Calculate actual laughter time
                        actual_seconds = start_seconds + laughter_seconds
                        
                        # Convert to proper timestamp
                        actual_hours = int(actual_seconds // 3600)
                        actual_minutes = int((actual_seconds % 3600) // 60)
                        actual_secs = int(actual_seconds % 60)
                        
                        # Create proper timestamp
                        corrected_timestamp = f"2025-10-25T{actual_hours:02d}:{actual_minutes:02d}:{actual_secs:02d}.000000+00:00"
                        
                        logger.info(f"  Original: {detection['timestamp']}")
                        logger.info(f"  Corrected: {corrected_timestamp}")
                        logger.info(f"  Laughter at: {actual_hours:02d}:{actual_minutes:02d}:{actual_secs:02d}")
                        
                        # Update the database
                        self.supabase.table("laughter_detections").update({
                            "timestamp": corrected_timestamp
                        }).eq("id", detection["id"]).execute()
                        
                        logger.info(f"  ✅ Updated timestamp")
                        fixed_count += 1
        
        logger.info(f"🎉 Fixed {fixed_count} timestamps")
        return fixed_count
    
    def run_fix(self):
        """Run the complete timestamp fix."""
        logger.info("🚀 Starting timestamp fix...")
        
        fixed_count = self.fix_timestamps()
        
        if fixed_count > 0:
            logger.info(f"✅ Successfully fixed {fixed_count} timestamps")
            return True
        else:
            logger.warning("⚠️  No timestamps were fixed")
            return False

def main():
    try:
        fixer = TimestampFixer()
        success = fixer.run_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Fix failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
