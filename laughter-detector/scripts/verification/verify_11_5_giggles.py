#!/usr/bin/env python3
"""Verify giggles count for 11/5 by checking database records."""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timezone
import pytz

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

# User info (from logs)
user_email = "solutionsethi@gmail.com"
user_tz = "America/Los_Angeles"
target_date = "2025-11-05"  # Nov 5 in PST

# Calculate UTC ranges for Nov 5 PST
# Nov 5 PST = Nov 5 00:00 PST to Nov 6 00:00 PST
# = Nov 5 08:00 UTC to Nov 6 08:00 UTC
pst = pytz.timezone(user_tz)
target_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()

# Start: Nov 5 00:00 PST = Nov 5 08:00 UTC
start_local = pst.localize(datetime.combine(target_date_obj, datetime.min.time()))
start_utc = start_local.astimezone(pytz.UTC)

# End: Nov 6 00:00 PST = Nov 6 08:00 UTC
end_local = pst.localize(datetime.combine(target_date_obj.replace(day=target_date_obj.day+1), datetime.min.time()))
end_utc = end_local.astimezone(pytz.UTC)

# Split point: Nov 6 00:00 UTC (chunks 1-8 end, chunks 9-12 start)
split_utc = datetime(2025, 11, 6, 0, 0, 0, tzinfo=timezone.utc)

print("=" * 80)
print(f"VERIFYING GIGGLES FOR {target_date} ({user_tz})")
print("=" * 80)
print(f"\nUTC Range: {start_utc.isoformat()} to {end_utc.isoformat()}")
print(f"Split point (chunks 1-8 vs 9-12): {split_utc.isoformat()}")
print(f"\nChunks 1-8: {start_utc.isoformat()} to {split_utc.isoformat()}")
print(f"Chunks 9-12: {split_utc.isoformat()} to {end_utc.isoformat()}")

# Get user ID
users = supabase.table("users").select("id").eq("email", user_email).execute()
if not users.data:
    print(f"\n❌ ERROR: User {user_email} not found!")
    sys.exit(1)

user_id = users.data[0]["id"]
print(f"\n👤 User ID: {user_id}")

# 1. Check processing_logs for 11/5
print("\n" + "=" * 80)
print("1. PROCESSING LOGS")
print("=" * 80)
logs = supabase.table("processing_logs").select("*").eq("user_id", user_id).eq("date", target_date).order("created_at", desc=False).execute()

if logs.data:
    print(f"\nFound {len(logs.data)} processing log(s) for {target_date}:")
    for i, log in enumerate(logs.data, 1):
        print(f"\n  Log #{i}:")
        print(f"    Created: {log.get('created_at')}")
        print(f"    Trigger: {log.get('trigger_type', 'N/A')}")
        print(f"    Status: {log.get('status')}")
        print(f"    Laughter events found: {log.get('laughter_events_found', 0)}")
        print(f"    Audio files downloaded: {log.get('audio_files_downloaded', 0)}")
        print(f"    Duplicates skipped: {log.get('duplicates_skipped', 0)}")
        print(f"    Duration: {log.get('processing_duration_seconds', 0)}s")
else:
    print(f"\n⚠️  No processing logs found for {target_date}")

# 2. Count giggles in first 8 chunks (08:00 UTC to 00:00 UTC next day)
print("\n" + "=" * 80)
print("2. GIGGLES IN FIRST 8 CHUNKS (08:00 UTC to 00:00 UTC)")
print("=" * 80)
chunks_1_8 = supabase.table("laughter_detections").select("id, timestamp, clip_path").eq("user_id", user_id).gte("timestamp", start_utc.isoformat()).lt("timestamp", split_utc.isoformat()).execute()

print(f"\nFound {len(chunks_1_8.data)} giggles in chunks 1-8")
if chunks_1_8.data:
    print(f"\nFirst few giggles:")
    for det in chunks_1_8.data[:5]:
        print(f"  - {det['timestamp']}")

# 3. Count giggles in last 4 chunks (00:00 UTC to 08:00 UTC)
print("\n" + "=" * 80)
print("3. GIGGLES IN LAST 4 CHUNKS (00:00 UTC to 08:00 UTC)")
print("=" * 80)
chunks_9_12 = supabase.table("laughter_detections").select("id, timestamp, clip_path").eq("user_id", user_id).gte("timestamp", split_utc.isoformat()).lt("timestamp", end_utc.isoformat()).execute()

print(f"\nFound {len(chunks_9_12.data)} giggles in chunks 9-12")
if chunks_9_12.data:
    print(f"\nFirst few giggles:")
    for det in chunks_9_12.data[:5]:
        print(f"  - {det['timestamp']}")

# 4. Total count for the day
print("\n" + "=" * 80)
print("4. TOTAL GIGGLES FOR 11/5")
print("=" * 80)
total = supabase.table("laughter_detections").select("id").eq("user_id", user_id).gte("timestamp", start_utc.isoformat()).lt("timestamp", end_utc.isoformat()).execute()

print(f"\nTotal giggles for {target_date}: {len(total.data)}")
print(f"  - Chunks 1-8: {len(chunks_1_8.data)}")
print(f"  - Chunks 9-12: {len(chunks_9_12.data)}")
print(f"  - Sum: {len(chunks_1_8.data) + len(chunks_9_12.data)}")

# 5. Verify against expected counts
print("\n" + "=" * 80)
print("5. VERIFICATION")
print("=" * 80)
expected_chunks_9_12 = 87  # From disk count
expected_chunks_1_8 = 15   # 102 total - 87 from chunks 9-12

print(f"\nExpected:")
print(f"  - Chunks 1-8: {expected_chunks_1_8} giggles")
print(f"  - Chunks 9-12: {expected_chunks_9_12} giggles")
print(f"  - Total: {expected_chunks_1_8 + expected_chunks_9_12} giggles")

print(f"\nActual:")
print(f"  - Chunks 1-8: {len(chunks_1_8.data)} giggles")
print(f"  - Chunks 9-12: {len(chunks_9_12.data)} giggles")
print(f"  - Total: {len(total.data)} giggles")

if len(chunks_1_8.data) == expected_chunks_1_8:
    print(f"\n✅ CONFIRMED: {expected_chunks_1_8} giggles in chunks 1-8 matches expected!")
else:
    print(f"\n⚠️  MISMATCH: Expected {expected_chunks_1_8} giggles in chunks 1-8, found {len(chunks_1_8.data)}")

if len(chunks_9_12.data) == expected_chunks_9_12:
    print(f"✅ CONFIRMED: {expected_chunks_9_12} giggles in chunks 9-12 matches expected!")
else:
    print(f"⚠️  MISMATCH: Expected {expected_chunks_9_12} giggles in chunks 9-12, found {len(chunks_9_12.data)}")

if len(total.data) == 102:
    print(f"✅ CONFIRMED: Total 102 giggles matches expected!")
else:
    print(f"⚠️  MISMATCH: Expected 102 total giggles, found {len(total.data)}")

print("\n" + "=" * 80)

