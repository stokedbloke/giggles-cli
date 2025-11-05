import sys
sys.path.insert(0, '.')
import os
os.chdir('/Users/neilsethi/git/giggles-cli/laughter-detector')
from dotenv import load_dotenv
load_dotenv(override=True)
from supabase import create_client
from datetime import datetime
import pytz

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

user_id = 'd223fee9-b279-4dc7-8cd1-188dc09ccdd1'
user_tz = pytz.timezone('America/Los_Angeles')

print("=" * 80)
print("STEP 2 VERIFICATION: CRON JOB RESULTS")
print("=" * 80)
print()

# Calculate UTC range for 11/3 PST
start_utc = user_tz.localize(datetime(2025, 11, 3, 0, 0, 0)).astimezone(pytz.UTC)
end_utc = user_tz.localize(datetime(2025, 11, 4, 0, 0, 0)).astimezone(pytz.UTC)

# 1. Check processing_logs
print("1. PROCESSING_LOGS (11/3):")
logs = supabase.table('processing_logs').select('*').eq('user_id', user_id).eq('date', '2025-11-03').order('created_at', desc=True).execute()
print(f"   Found: {len(logs.data)} log(s)")
for log in logs.data:
    print(f"   - Created: {log['created_at'][:19]}")
    print(f"     Status: {log.get('status')}")
    print(f"     Trigger: {log.get('trigger_type')}")
    print(f"     Audio downloaded: {log.get('audio_files_downloaded', 0)}")
    print(f"     Laughter events: {log.get('laughter_events_found', 0)}")
    print(f"     Duplicates skipped: {log.get('duplicates_skipped', 0)}")
print()

# 2. Check laughter_detections
print("2. LAUGHTER_DETECTIONS (11/3):")
dets = supabase.table('laughter_detections').select('id, timestamp, clip_path, created_at').eq('user_id', user_id).gte('timestamp', start_utc.isoformat()).lt('timestamp', end_utc.isoformat()).order('timestamp', desc=False).execute()
print(f"   Found: {len(dets.data)} detection(s)")
print()

# Check file existence
missing_count = 0
existing_count = 0
for det in dets.data:
    clip_path = det.get('clip_path', '')
    if clip_path:
        full_path = os.path.join(os.getcwd(), clip_path)
        if os.path.exists(full_path):
            existing_count += 1
        else:
            missing_count += 1

print(f"   ✅ Files exist: {existing_count}")
print(f"   ❌ Files missing: {missing_count}")
print()

# 3. Check audio_segments
print("3. AUDIO_SEGMENTS (11/3):")
# FIX: Use .lte() instead of .lt() to include boundary segments (e.g., chunk ending exactly at end_utc)
segments = supabase.table('audio_segments').select('id, start_time, end_time, processed').eq('user_id', user_id).gte('start_time', start_utc.isoformat()).lte('end_time', end_utc.isoformat()).order('start_time', desc=False).execute()
print(f"   Found: {len(segments.data)} segment(s)")
processed = sum(1 for s in segments.data if s.get('processed'))
print(f"   Processed: {processed}")
print()

# Summary
print("=" * 80)
print("STEP 2 SUMMARY:")
print(f"  - Processing logs: {len(logs.data)}")
print(f"  - Laughter detections: {len(dets.data)}")
status_msg = "✅ ALL EXIST" if missing_count == 0 else f"❌ {missing_count} MISSING"
print(f"  - Files on disk: {existing_count} / {len(dets.data)} ({status_msg})")
print(f"  - Audio segments: {len(segments.data)} ({processed} processed)")
print()

# Compare with expected (from reprocessing)
expected_detections = 18
expected_segments = 12

match_detections = len(dets.data) == expected_detections
match_segments = len(segments.data) == expected_segments
all_files_exist = missing_count == 0

if match_detections and match_segments and all_files_exist:
    print("✅ CRON JOB PASSED: Results match reprocessing exactly!")
else:
    print("❌ CRON JOB MISMATCH:")
    if not match_detections:
        print(f"   - Detections: {len(dets.data)} (expected {expected_detections})")
    if not match_segments:
        print(f"   - Segments: {len(segments.data)} (expected {expected_segments})")
    if not all_files_exist:
        print(f"   - Files missing: {missing_count}")

print("=" * 80)
