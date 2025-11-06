#!/usr/bin/env python3
"""Check if Limitless API is returning timestamps with a 1-hour offset."""
import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timedelta
import pytz

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

user_email = "neilsethi@hotmail.com"
user_id = supabase.table("users").select("id").eq("email", user_email).execute().data[0]["id"]

print("=" * 80)
print("LIMITLESS API TIMESTAMP OFFSET CHECK")
print("=" * 80)

# Check the 14:00-16:00 UTC segment (should be 6:00-8:00 AM PST)
# If user says 6:38 AM felt like 7:38 AM, then:
# - Stored: 14:38:50 UTC = 6:38:50 AM PST
# - Should be: 15:38:50 UTC = 7:38:50 AM PST
# - Difference: +1 hour

print("\n" + "=" * 80)
print("AUDIO SEGMENT: 14:00-16:00 UTC (6:00-8:00 AM PST)")
print("=" * 80)

seg = supabase.table("audio_segments").select("id, start_time, end_time, date").eq("user_id", user_id).eq("start_time", "2025-11-06T14:00:00+00:00").execute()

if seg.data:
    seg_data = seg.data[0]
    stored_start = datetime.fromisoformat(seg_data['start_time'].replace('Z', '+00:00'))
    stored_end = datetime.fromisoformat(seg_data['end_time'].replace('Z', '+00:00'))
    
    pst = pytz.timezone('America/Los_Angeles')
    stored_start_pst = stored_start.astimezone(pst)
    stored_end_pst = stored_end.astimezone(pst)
    
    print(f"\nStored in database:")
    print(f"  UTC: {stored_start.strftime('%Y-%m-%d %H:%M:%S')} to {stored_end.strftime('%H:%M:%S')}")
    print(f"  PST: {stored_start_pst.strftime('%Y-%m-%d %H:%M:%S %Z')} to {stored_end_pst.strftime('%H:%M:%S %Z')}")
    
    # What we REQUESTED from Limitless
    print(f"\nWhat we REQUESTED from Limitless API:")
    print(f"  UTC: 2025-11-06 14:00:00 to 16:00:00")
    print(f"  PST: 2025-11-06 06:00:00 to 08:00:00")
    
    # What it SHOULD be if user is right (1 hour later)
    print(f"\nIf 6:38 AM felt like 7:38 AM, then:")
    print(f"  Should be UTC: 2025-11-06 15:00:00 to 17:00:00")
    print(f"  Should be PST: 2025-11-06 07:00:00 to 09:00:00")
    print(f"  Offset: +1 hour")
    
    print(f"\n" + "=" * 80)
    print("POSSIBLE CAUSES")
    print("=" * 80)
    print(f"\n1. Limitless API might interpret startMs/endMs in a different timezone")
    print(f"   - We send: milliseconds since epoch (UTC)")
    print(f"   - Limitless might: interpret as local timezone or different UTC offset")
    
    print(f"\n2. Device/Pendant timezone might be different")
    print(f"   - Device might be set to PDT (UTC-7) instead of PST (UTC-8)")
    print(f"   - Or device might be in a different timezone entirely")
    
    print(f"\n3. DST transition issue")
    print(f"   - DST ended Nov 2, 2025")
    print(f"   - Nov 6 should be PST (UTC-8)")
    print(f"   - But maybe Limitless/device is still using PDT (UTC-7)?")
    
    # Check laughter detections in this segment
    print(f"\n" + "=" * 80)
    print("LAUGHTER DETECTIONS IN THIS SEGMENT")
    print("=" * 80)
    
    dets = supabase.table("laughter_detections").select("id, timestamp").eq("user_id", user_id).gte("timestamp", stored_start.isoformat()).lt("timestamp", stored_end.isoformat()).order("timestamp", desc=False).execute()
    
    print(f"\nFound {len(dets.data)} detections:")
    for det in dets.data[:5]:
        ts_utc = datetime.fromisoformat(det['timestamp'].replace('Z', '+00:00'))
        ts_pst = ts_utc.astimezone(pst)
        ts_pst_plus_1h = (ts_utc + timedelta(hours=1)).astimezone(pst)
        
        print(f"  Stored: {ts_pst.strftime('%I:%M:%S %p %Z')} ({ts_utc.strftime('%H:%M:%S UTC')})")
        print(f"  If +1h: {ts_pst_plus_1h.strftime('%I:%M:%S %p %Z')} ({(ts_utc + timedelta(hours=1)).strftime('%H:%M:%S UTC')})")
    
    print(f"\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print(f"\nThe 1-hour offset suggests Limitless API or device is using a different timezone.")
    print(f"Options:")
    print(f"  1. Check Limitless API documentation for timezone requirements")
    print(f"  2. Add +1 hour offset when storing timestamps (if confirmed to be consistent)")
    print(f"  3. Check device/pendant timezone settings")
    
else:
    print("Segment not found")

