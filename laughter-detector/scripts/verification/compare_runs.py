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
print("COMPARISON: THIS MORNING vs NOW")
print("=" * 80)
print()

# Calculate UTC range for 11/3 PST
start_utc = user_tz.localize(datetime(2025, 11, 3, 0, 0, 0)).astimezone(pytz.UTC)
end_utc = user_tz.localize(datetime(2025, 11, 4, 0, 0, 0)).astimezone(pytz.UTC)

# Check processing_logs
print("1. PROCESSING_LOGS:")
logs = supabase.table('processing_logs').select('*').eq('user_id', user_id).eq('date', '2025-11-03').order('created_at', desc=False).execute()
print(f"   Total logs: {len(logs.data)}")
for i, log in enumerate(logs.data, 1):
    print(f"\n   Run #{i}:")
    created_dt = datetime.fromisoformat(log['created_at'].replace('Z', '+00:00'))
    print(f"   - Created: {created_dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"   - Trigger: {log.get('trigger_type')}")
    print(f"   - Audio downloaded: {log.get('audio_files_downloaded', 0)}")
    print(f"   - Laughter events: {log.get('laughter_events_found', 0)}")
    print(f"   - Duplicates skipped: {log.get('duplicates_skipped', 0)}")
print()

# Check audio_segments - see which chunks exist
print("2. AUDIO_SEGMENTS (which chunks were downloaded):")
# FIX: Use .lte() instead of .lt() to include boundary segments (e.g., chunk ending exactly at end_utc)
segments = supabase.table('audio_segments').select('id, start_time, end_time, processed, created_at').eq('user_id', user_id).gte('start_time', start_utc.isoformat()).lte('end_time', end_utc.isoformat()).order('start_time', desc=False).execute()

print(f"   Found: {len(segments.data)} segment(s)")

# Extract chunk hours
actual_hours = []
for seg in segments.data:
    start = datetime.fromisoformat(seg['start_time'].replace('Z', '+00:00'))
    actual_hours.append(start.hour)

expected_hours = list(range(0, 24, 2))  # 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22
missing_hours = sorted(set(expected_hours) - set(actual_hours))

print(f"   Expected chunks: 12 (hours: {expected_hours})")
print(f"   Actual chunks downloaded: {len(actual_hours)} (hours: {sorted(actual_hours)})")
if missing_hours:
    print(f"   ❌ Missing chunks: {missing_hours}")
    for hour in missing_hours:
        print(f"      - {hour:02d}:00-{hour+2:02d}:00 UTC")
else:
    print(f"   ✅ All chunks downloaded")

print()
