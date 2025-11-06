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
print("STEP 1 VERIFICATION: CLEANUP RESULTS")
print("=" * 80)
print()

# Calculate UTC range for 11/3 PST
start_utc = user_tz.localize(datetime(2025, 11, 3, 0, 0, 0)).astimezone(pytz.UTC)
end_utc = user_tz.localize(datetime(2025, 11, 4, 0, 0, 0)).astimezone(pytz.UTC)

print(f"Checking UTC range: {start_utc.isoformat()} to {end_utc.isoformat()}")
print()

# 1. Check processing_logs
print("1. PROCESSING_LOGS (11/3):")
logs = supabase.table('processing_logs').select('*').eq('user_id', user_id).eq('date', '2025-11-03').execute()
print(f"   Found: {len(logs.data)} log(s)")
if len(logs.data) > 0:
    print("   ❌ FAIL: Still has processing logs!")
else:
    print("   ✅ PASS: All processing logs deleted")
print()

# 2. Check laughter_detections
print("2. LAUGHTER_DETECTIONS (11/3):")
dets = supabase.table('laughter_detections').select('id, timestamp').eq('user_id', user_id).gte('timestamp', start_utc.isoformat()).lt('timestamp', end_utc.isoformat()).execute()
print(f"   Found: {len(dets.data)} detection(s)")
if len(dets.data) > 0:
    print("   ❌ FAIL: Still has detections!")
else:
    print("   ✅ PASS: All detections deleted")
print()

# 3. Check audio_segments
print("3. AUDIO_SEGMENTS (11/3):")
# FIX: Use .lte() instead of .lt() to include boundary segments (e.g., chunk ending exactly at end_utc)
segments = supabase.table('audio_segments').select('id, start_time, end_time').eq('user_id', user_id).gte('start_time', start_utc.isoformat()).lte('end_time', end_utc.isoformat()).execute()
print(f"   Found: {len(segments.data)} segment(s)")
if len(segments.data) > 0:
    print("   ❌ FAIL: Still has segments!")
else:
    print("   ✅ PASS: All segments deleted")
print()

# 4. Check files on disk
print("4. FILES ON DISK (11/3):")
clips_dir = os.path.join(os.getcwd(), 'uploads', 'clips', user_id)
files_11_3 = []
if os.path.exists(clips_dir):
    files_on_disk = [f for f in os.listdir(clips_dir) if f.endswith('.wav')]
    files_11_3 = [f for f in files_on_disk if '20251103' in f]
    print(f"   Found: {len(files_11_3)} WAV file(s) matching 11/3 pattern")
    if len(files_11_3) > 0:
        print("   ❌ FAIL: Still has files on disk!")
        for f in files_11_3[:5]:
            print(f"      - {f}")
    else:
        print("   ✅ PASS: All 11/3 files deleted from disk")
else:
    print("   ✅ PASS: Clips directory doesn't exist (no files)")
print()

# Summary
print("=" * 80)
print("STEP 1 SUMMARY:")
all_passed = len(logs.data) == 0 and len(dets.data) == 0 and len(segments.data) == 0 and len(files_11_3) == 0
if all_passed:
    print("✅ CLEANUP PASSED: All 11/3 data deleted from DB and disk")
else:
    print("❌ CLEANUP FAILED: Some data still exists")
print("=" * 80)
