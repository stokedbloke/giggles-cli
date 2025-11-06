#!/usr/bin/env python3
"""
Clean up all data for a specific date or today to start fresh for testing.
Usage: python cleanup_today_data.py [YYYY-MM-DD]
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client
from pathlib import Path

load_dotenv()

supabase = create_client(
    os.getenv('SUPABASE_URL'), 
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Get date from command line or use today
if len(sys.argv) > 1:
    date_str = sys.argv[1]
    date = datetime.strptime(date_str, '%Y-%m-%d')
else:
    date = datetime.now()

date_prefix = date.strftime('%Y%m%d')
date_start = date.strftime('%Y-%m-%d')
date_next = (date + timedelta(days=1)).strftime('%Y-%m-%d')

print(f"Deleting all data for {date_start}...")

# Delete laughter detections
print("Deleting laughter detections...")
result = supabase.table('laughter_detections').delete().gte('timestamp', f'{date_start}T00:00:00Z').lt('timestamp', f'{date_next}T00:00:00Z').execute()
print(f"Deleted {len(result.data) if result.data else 0} detections")

# Delete audio segments
print("Deleting audio segments...")
result = supabase.table('audio_segments').delete().gte('start_time', f'{date_start}T00:00:00Z').lt('start_time', f'{date_next}T00:00:00Z').execute()
print(f"Deleted {len(result.data) if result.data else 0} segments")

# Delete any WAV clips for the date
clips_dir = Path("uploads/clips")
if clips_dir.exists():
    today_clips = list(clips_dir.glob(f"{date_prefix}_*.wav"))
    print(f"Deleting {len(today_clips)} WAV clips for {date_start}...")
    for clip in today_clips:
        clip.unlink()
        print(f"  Deleted {clip.name}")

# Delete any OGG files for the date
audio_dir = Path("uploads/audio")
if audio_dir.exists():
    for user_dir in audio_dir.iterdir():
        if user_dir.is_dir():
            today_ogg = list(user_dir.glob(f"{date_prefix}_*.ogg"))
            print(f"Deleting {len(today_ogg)} OGG files for {date_start}...")
            for ogg in today_ogg:
                ogg.unlink()
                print(f"  Deleted {ogg.name}")

print("\n✅ Cleanup complete - ready for fresh test run")

