#!/usr/bin/env python3
"""
Check the results of the reprocessing to understand discrepancies.
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client
import pytz

load_dotenv()

# Get user ID
user_id = os.getenv('TEST_USER_ID')
if not user_id:
    supabase = create_client(
        os.getenv('SUPABASE_URL'), 
        os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    )
    users = supabase.table('users').select('id, email').order('created_at', desc=True).limit(1).execute()
    if users.data:
        user_id = users.data[0]['id']
        print(f"Using user: {users.data[0]['email']} ({user_id})")
    else:
        print("ERROR: No users found")
        sys.exit(1)

# Get user timezone
supabase = create_client(
    os.getenv('SUPABASE_URL'), 
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)
user_result = supabase.table('users').select('timezone').eq('id', user_id).execute()
timezone = user_result.data[0].get('timezone', 'UTC') if user_result.data else 'UTC'
user_tz = pytz.timezone(timezone)

# Dates to check
start_date_str = "2025-10-29"
end_date_str = "2025-10-30"

start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

start_date = user_tz.localize(start_date)
end_date = user_tz.localize(end_date)

start_time = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
end_time = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

# Convert to UTC for query
start_utc = start_time.astimezone(pytz.UTC)
end_utc = end_time.astimezone(pytz.UTC)

print(f"\n📊 Checking results for date range:")
print(f"   {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')} to {end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"   (UTC: {start_utc.strftime('%Y-%m-%d %H:%M:%S UTC')} to {end_utc.strftime('%Y-%m-%d %H:%M:%S UTC')})\n")

# Get laughter detections
detections_result = supabase.table("laughter_detections").select(
    "id, timestamp, probability, audio_segment_id"
).eq("user_id", user_id).gte("timestamp", start_utc.isoformat()).lte("timestamp", end_utc.isoformat()).execute()

detections = detections_result.data if detections_result.data else []

print(f"✅ Total laughter detections in database: {len(detections)}")

# Group by date
by_date = {}
for det in detections:
    ts = datetime.fromisoformat(det["timestamp"].replace('Z', '+00:00'))
    ts_local = ts.astimezone(user_tz)
    date_key = ts_local.strftime('%Y-%m-%d')
    
    if date_key not in by_date:
        by_date[date_key] = []
    by_date[date_key].append(det)

for date_key in sorted(by_date.keys()):
    print(f"\n📅 {date_key}: {len(by_date[date_key])} detections")
    for det in by_date[date_key]:
        ts = datetime.fromisoformat(det["timestamp"].replace('Z', '+00:00'))
        ts_local = ts.astimezone(user_tz)
        print(f"   - {ts_local.strftime('%H:%M:%S')} (prob: {det['probability']:.3f})")

# Get audio segments
segments_result = supabase.table("audio_segments").select(
    "id, start_time, end_time, processed"
).eq("user_id", user_id).gte("start_time", start_utc.isoformat()).lte("end_time", end_utc.isoformat()).execute()

segments = segments_result.data if segments_result.data else []
print(f"\n📁 Total audio segments: {len(segments)}")
print(f"   Processed: {sum(1 for s in segments if s.get('processed'))}")
print(f"   Not processed: {sum(1 for s in segments if not s.get('processed'))}")

# Check for segments with many detections
print(f"\n🔍 Segments with detections:")
segment_detection_count = {}
segment_info = {}
for det in detections:
    seg_id = det.get("audio_segment_id")
    if seg_id:
        segment_detection_count[seg_id] = segment_detection_count.get(seg_id, 0) + 1
        if seg_id not in segment_info:
            segment_info[seg_id] = []

# Get segment details
for seg in segments:
    seg_id = seg["id"]
    if seg_id in segment_detection_count:
        segment_info[seg_id] = seg

for seg_id, count in sorted(segment_detection_count.items(), key=lambda x: x[1], reverse=True):
    seg_info = segment_info.get(seg_id, {})
    start_time_str = seg_info.get("start_time", "unknown")
    print(f"   Segment {seg_id[:8]}...: {count} detections (start: {start_time_str})")

# Check how UI queries work - group by local date
print(f"\n📊 UI Query Analysis (grouped by local date in {timezone}):")
from collections import defaultdict
ui_grouped = defaultdict(list)

for det in detections:
    ts = datetime.fromisoformat(det["timestamp"].replace('Z', '+00:00'))
    ts_local = ts.astimezone(user_tz)
    date_key = ts_local.strftime('%Y-%m-%d')
    ui_grouped[date_key].append(det)

for date_key in sorted(ui_grouped.keys()):
    print(f"   {date_key}: {len(ui_grouped[date_key])} detections (UI would show this count)")

print()

