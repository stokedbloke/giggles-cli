#!/usr/bin/env python3
"""
Check database for orphaned file by path.
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Supabase credentials not found")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# The file path from the user
file_path = "uploads/audio/d223fee9-b279-4dc7-8cd1-188dc09ccdd1/20251029_080000-20251029_095108.ogg"
user_id = "d223fee9-b279-4dc7-8cd1-188dc09ccdd1"

print(f"🔍 Checking for file: {file_path}")
print(f"🔍 User ID: {user_id}")
print()

# Check if file exists on disk
full_path = f"/Users/neilsethi/git/giggles-cli/laughter-detector/{file_path}"
print(f"📁 File exists on disk: {os.path.exists(full_path)}")
print()

# Query database for this file path
print("📊 Querying database for segments with this file_path...")
result = supabase.table("audio_segments").select("*").eq("user_id", user_id).ilike("file_path", f"%{os.path.basename(file_path)}%").execute()

print(f"📊 Found {len(result.data) if result.data else 0} segment(s) matching file path")
print()

if result.data:
    for segment in result.data:
        print(f"  ID: {segment.get('id')}")
        print(f"  File Path: {segment.get('file_path')}")
        print(f"  Processed: {segment.get('processed')}")
        print(f"  Start Time: {segment.get('start_time')}")
        print(f"  End Time: {segment.get('end_time')}")
        print()
else:
    print("❌ No segments found with this file path in database")
    print()
    print("🔍 Checking all processed segments for this user...")
    all_result = supabase.table("audio_segments").select("id, file_path, processed").eq("user_id", user_id).eq("processed", True).execute()
    print(f"📊 Found {len(all_result.data) if all_result.data else 0} total processed segments")
    
    if all_result.data:
        print("  Sample file paths:")
        for seg in all_result.data[:5]:  # Show first 5
            print(f"    - {seg.get('file_path')}")

