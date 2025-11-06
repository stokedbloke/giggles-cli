#!/usr/bin/env python3
"""Analyze if there's a 1-hour offset in timestamps from Limitless API."""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime
import pytz

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

user_email = "neilsethi@hotmail.com"  # New user
user_id = supabase.table("users").select("id").eq("email", user_email).execute().data[0]["id"]

print("=" * 80)
print("TIMESTAMP OFFSET ANALYSIS")
print("=" * 80)
print(f"\nUser: {user_email}")
print(f"User ID: {user_id}")

# Get audio segments for Nov 6
print("\n" + "=" * 80)
print("AUDIO SEGMENTS FOR NOV 6, 2025")
print("=" * 80)

# Nov 6 in PST = Nov 6 00:00 PST to Nov 7 00:00 PST = Nov 6 08:00 UTC to Nov 7 08:00 UTC
pst = pytz.timezone('America/Los_Angeles')
nov6_start_pst = pst.localize(datetime(2025, 11, 6, 0, 0, 0))
nov6_end_pst = pst.localize(datetime(2025, 11, 7, 0, 0, 0))
nov6_start_utc = nov6_start_pst.astimezone(pytz.UTC)
nov6_end_utc = nov6_end_pst.astimezone(pytz.UTC)

print(f"\nNov 6 PST range: {nov6_start_pst.strftime('%Y-%m-%d %H:%M:%S %Z')} to {nov6_end_pst.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"Nov 6 UTC range: {nov6_start_utc.strftime('%Y-%m-%d %H:%M:%S %Z')} to {nov6_end_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")

segments = supabase.table("audio_segments").select("id, start_time, end_time, date").eq("user_id", user_id).gte("start_time", nov6_start_utc.isoformat()).lt("end_time", nov6_end_utc.isoformat()).order("start_time", desc=False).execute()

print(f"\nFound {len(segments.data)} audio segments:")
for seg in segments.data:
    start_utc = datetime.fromisoformat(seg['start_time'].replace('Z', '+00:00'))
    end_utc = datetime.fromisoformat(seg['end_time'].replace('Z', '+00:00'))
    start_pst = start_utc.astimezone(pst)
    end_pst = end_utc.astimezone(pst)
    
    print(f"\n  Segment: {seg['id'][:8]}...")
    print(f"    UTC:   {start_utc.strftime('%Y-%m-%d %H:%M:%S')} to {end_utc.strftime('%H:%M:%S')}")
    print(f"    PST:   {start_pst.strftime('%Y-%m-%d %H:%M:%S %Z')} to {end_pst.strftime('%H:%M:%S %Z')}")
    print(f"    Date:  {seg['date']}")

# Get laughter detections for Nov 6
print("\n" + "=" * 80)
print("LAUGHTER DETECTIONS FOR NOV 6, 2025")
print("=" * 80)

dets = supabase.table("laughter_detections").select("id, timestamp").eq("user_id", user_id).gte("timestamp", nov6_start_utc.isoformat()).lt("timestamp", nov6_end_utc.isoformat()).order("timestamp", desc=False).limit(10).execute()

print(f"\nFirst 10 laughter detections:")
for det in dets.data:
    ts_utc = datetime.fromisoformat(det['timestamp'].replace('Z', '+00:00'))
    ts_pst = ts_utc.astimezone(pst)
    
    print(f"  {ts_pst.strftime('%I:%M:%S %p %Z')} ({ts_utc.strftime('%H:%M:%S UTC')})")

# Check if there's a pattern
print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)
print("\nIf you see 6:38 AM clips in the UI:")
print(f"  - UTC time stored: 14:38:50 UTC")
print(f"  - PST time displayed: 06:38:50 AM PST")
print(f"  - This conversion is CORRECT (UTC-8 = PST)")
print(f"\nIf you think you weren't up at 6 AM, possible causes:")
print(f"  1. Limitless API returned audio from 1 hour earlier than requested")
print(f"  2. Timestamps are being stored 1 hour off")
print(f"  3. The audio is actually from 7:38 AM (if Limitless is 1 hour ahead)")
print(f"\nCheck the actual timestamps above to see if they match what you expect.")

