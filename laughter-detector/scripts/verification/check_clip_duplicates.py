#!/usr/bin/env python3
"""
Check for duplicate laughter clips.
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

user_id = "d223fee9-b279-4dc7-8cd1-188dc09ccdd1"

# Get all laughter detections
print("📊 Checking laughter detections...")
result = supabase.table("laughter_detections").select("id, timestamp, clip_path, probability").eq("user_id", user_id).order("timestamp").execute()

print(f"📊 Found {len(result.data) if result.data else 0} laughter detections in database")
print()

# Group by clip_path to find duplicates
clip_counts = {}
for detection in result.data:
    clip_path = detection.get('clip_path', '')
    clip_counts[clip_path] = clip_counts.get(clip_path, 0) + 1

# Find duplicates
duplicates = {path: count for path, count in clip_counts.items() if count > 1}

print(f"🎯 Unique clips: {len(clip_counts)}")
print(f"⚠️  Duplicate clip_paths: {len(duplicates)}")
print()

if duplicates:
    print("📋 Duplicate clips:")
    for path, count in sorted(duplicates.items()):
        print(f"  {path}: {count} detections")
        # Show all detections with this clip_path
        for det in result.data:
            if det.get('clip_path') == path:
                print(f"    - {det.get('id')[:8]}: {det.get('timestamp')} (prob: {det.get('probability', 0):.3f})")
    print()

# Check files on disk
print("📁 Checking files on disk...")
clips_dir = "/Users/neilsethi/git/giggles-cli/laughter-detector/uploads/clips"
disk_files = []
if os.path.exists(clips_dir):
    disk_files = [f for f in os.listdir(clips_dir) if f.endswith('.wav')]
    print(f"📁 Found {len(disk_files)} .wav files on disk")
else:
    print(f"❌ Clips directory not found: {clips_dir}")

print()
print(f"📊 Summary:")
print(f"  Database detections: {len(result.data)}")
print(f"  Unique clip_paths: {len(clip_counts)}")
print(f"  Files on disk: {len(disk_files)}")
print(f"  Discrepancy: {len(disk_files) - len(clip_counts)} files")
print()

# Find files on disk that don't have database records
db_filenames = set()
for detection in result.data:
    clip_path = detection.get('clip_path', '')
    if clip_path:
        db_filenames.add(os.path.basename(clip_path))

orphaned_clips = []
for disk_file in disk_files:
    if disk_file not in db_filenames:
        orphaned_clips.append(disk_file)

print(f"🗑️  Orphaned clip files on disk (no DB record): {len(orphaned_clips)}")
if orphaned_clips:
    for clip in orphaned_clips:
        print(f"  - {clip}")

