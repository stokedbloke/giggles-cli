#!/usr/bin/env python3
"""
Analyze duplicate detections to understand what's happening.
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client
import pytz
from collections import defaultdict

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

# Check processing logs
print("\n📋 Processing Logs Analysis:")
print("=" * 60)

logs_result = supabase.table("processing_logs").select("*").eq("user_id", user_id).in_("date", ["2025-10-29", "2025-10-30"]).execute()

if logs_result.data:
    for log in logs_result.data:
        print(f"\nDate: {log.get('date')}")
        print(f"  Status: {log.get('status')}")
        print(f"  Message: {log.get('message')}")
        print(f"  Laughter events found (from log): {log.get('laughter_events_found', 'N/A')}")
        print(f"  Processed segments: {log.get('processed_segments', 0)}")
        print(f"  Total segments: {log.get('total_segments', 0)}")
        
        # Check if there are processing steps
        if log.get('processing_steps'):
            steps = log.get('processing_steps', [])
            yamnet_steps = [s for s in steps if 'yamnet' in s.get('step_name', '').lower() or 'laughter' in s.get('step_name', '').lower()]
            if yamnet_steps:
                print(f"  YAMNet steps found: {len(yamnet_steps)}")
                for step in yamnet_steps[:5]:  # Show first 5
                    print(f"    - {step.get('step_name')}: {step.get('message', '')}")
else:
    print("  No processing logs found for these dates")

# Now check actual detections vs what would be duplicates
print("\n\n🔍 Duplicate Detection Analysis:")
print("=" * 60)

# Dates to check
start_date_str = "2025-10-29"
end_date_str = "2025-10-30"

start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

start_date = user_tz.localize(start_date)
end_date = user_tz.localize(end_date)

start_time = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
end_time = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

start_utc = start_time.astimezone(pytz.UTC)
end_utc = end_time.astimezone(pytz.UTC)

# Get all detections
detections_result = supabase.table("laughter_detections").select(
    "id, timestamp, probability, audio_segment_id"
).eq("user_id", user_id).gte("timestamp", start_utc.isoformat()).lte("timestamp", end_utc.isoformat()).execute()

detections = detections_result.data if detections_result.data else []

# Group by date
by_date = defaultdict(list)
for det in detections:
    ts = datetime.fromisoformat(det["timestamp"].replace('Z', '+00:00'))
    ts_local = ts.astimezone(user_tz)
    date_key = ts_local.strftime('%Y-%m-%d')
    by_date[date_key].append(det)

print(f"\n✅ Stored in laughter_detections table:")
for date_key in sorted(by_date.keys()):
    detections_for_date = by_date[date_key]
    print(f"\n  {date_key}: {len(detections_for_date)} detections stored")
    
    # Check for potential duplicates (within 5 seconds)
    sorted_dets = sorted(detections_for_date, key=lambda x: x["timestamp"])
    duplicate_groups = []
    for i, det1 in enumerate(sorted_dets):
        ts1 = datetime.fromisoformat(det1["timestamp"].replace('Z', '+00:00'))
        nearby = []
        for det2 in sorted_dets[i+1:]:
            ts2 = datetime.fromisoformat(det2["timestamp"].replace('Z', '+00:00'))
            diff = abs((ts2 - ts1).total_seconds())
            if diff <= 5:
                nearby.append(det2)
        if nearby:
            duplicate_groups.append((det1, nearby))
    
    if duplicate_groups:
        print(f"    ⚠️  Found {len(duplicate_groups)} detection(s) that have others within 5 seconds:")
        for det, nearby in duplicate_groups[:3]:  # Show first 3
            ts = datetime.fromisoformat(det["timestamp"].replace('Z', '+00:00'))
            ts_local = ts.astimezone(user_tz)
            print(f"      {ts_local.strftime('%H:%M:%S')} has {len(nearby)} nearby detection(s)")

print(f"\n\n💡 Summary:")
print(f"  - October 29: {len(by_date.get('2025-10-29', []))} detections stored")
print(f"  - October 30: {len(by_date.get('2025-10-30', []))} detections stored")
print(f"\n  Note: The UI should show these same counts if querying correctly.")

print()

