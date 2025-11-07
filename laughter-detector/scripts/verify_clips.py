#!/usr/bin/env python3
"""
Quick script to verify clip files on disk match database records.
Run this on the VPS to check data integrity.

Usage:
    /var/lib/giggles/venv/bin/python3 scripts/verify_clips.py <user_id>
    OR
    source /var/lib/giggles/venv/bin/activate
    python3 scripts/verify_clips.py <user_id>
"""
import os
import sys
from pathlib import Path

# Add project root to path so we can import from src
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
# Try multiple locations for .env file
env_paths = [
    project_root / ".env",
    Path("/var/lib/giggles/.env"),
    Path.home() / ".env"
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        print(f"📄 Loaded .env from: {env_path}")
        break
else:
    # Fallback: try loading from default location
    load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment")
    sys.exit(1)

# Get user_id from command line or use default
user_id = sys.argv[1] if len(sys.argv) > 1 else None
if not user_id:
    print("Usage: python verify_clips.py <user_id>")
    print("Example: python verify_clips.py 8edf813f-3a9a-4a53-92d4-43734355949d")
    sys.exit(1)

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Get upload directory from env or use default
upload_dir = os.getenv('UPLOAD_DIR', '/var/lib/giggles/uploads')
clips_dir = Path(upload_dir) / "clips" / user_id

print(f"🔍 Verifying clips for user: {user_id}")
print(f"📁 Clips directory: {clips_dir}")
print()

# Get all laughter detections from database
print("📊 Querying database...")
detections_result = supabase.table("laughter_detections").select(
    "id, timestamp, clip_path, probability, class_id, class_name"
).eq("user_id", user_id).execute()

if not detections_result.data:
    print("❌ No laughter detections found in database for this user")
    sys.exit(1)

print(f"✅ Found {len(detections_result.data)} laughter detections in database")
print()

# Get all clip files on disk
disk_clips = {}
if clips_dir.exists():
    for clip_file in clips_dir.glob("*.wav"):
        disk_clips[clip_file.name] = clip_file
    print(f"✅ Found {len(disk_clips)} WAV files on disk")
else:
    print(f"⚠️ Clips directory does not exist: {clips_dir}")
    print(f"   Creating it for reference...")
    clips_dir.mkdir(parents=True, exist_ok=True)

print()

# Check database clips vs disk
db_clips = {}
missing_on_disk = []
missing_in_db = []

print("🔍 Comparing database records with disk files...")
print()

for detection in detections_result.data:
    clip_path = detection.get("clip_path", "")
    if not clip_path:
        continue
    
    # Extract just the filename from the path
    clip_filename = os.path.basename(clip_path)
    db_clips[clip_filename] = detection
    
    # Check if file exists on disk
    if clip_filename in disk_clips:
        file_path = disk_clips[clip_filename]
        if file_path.exists():
            file_size = file_path.stat().st_size
            print(f"✅ MATCH: {clip_filename} ({file_size} bytes)")
        else:
            missing_on_disk.append(clip_filename)
            print(f"❌ MISSING ON DISK: {clip_filename}")
    else:
        missing_on_disk.append(clip_filename)
        print(f"❌ MISSING ON DISK: {clip_filename}")

print()

# Check for files on disk that aren't in database
for disk_filename in disk_clips:
    if disk_filename not in db_clips:
        missing_in_db.append(disk_filename)
        print(f"⚠️ EXTRA ON DISK (not in DB): {disk_filename}")

print()
print("=" * 80)
print("📊 SUMMARY")
print("=" * 80)
print(f"Database records: {len(db_clips)}")
print(f"Files on disk: {len(disk_clips)}")
print(f"Matches: {len(db_clips) - len(missing_on_disk)}")
print(f"Missing on disk: {len(missing_on_disk)}")
print(f"Extra on disk (not in DB): {len(missing_in_db)}")
print()

if missing_on_disk:
    print("❌ CLIPS MISSING ON DISK:")
    for clip in missing_on_disk:
        detection = db_clips[clip]
        print(f"   - {clip}")
        print(f"     Timestamp: {detection.get('timestamp')}")
        print(f"     Probability: {detection.get('probability')}")
        print()

if missing_in_db:
    print("⚠️ FILES ON DISK NOT IN DATABASE:")
    for clip in missing_in_db:
        print(f"   - {clip}")
        print(f"     File size: {disk_clips[clip].stat().st_size} bytes")
        print()

if not missing_on_disk and not missing_in_db:
    print("✅ Perfect match! All database records have corresponding files on disk.")
else:
    print("⚠️ Data integrity issues found. See details above.")

