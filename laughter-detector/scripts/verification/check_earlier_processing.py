#!/usr/bin/env python3
"""Check for earlier processing of chunks 1-8 on 11/5."""
import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timezone
import pytz

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

user_email = "solutionsethi@gmail.com"
user_id = "d223fee9-b279-4dc7-8cd1-188dc09ccdd1"

# Check audio_segments to see when chunks 1-8 were processed
print("=" * 80)
print("AUDIO SEGMENTS FOR CHUNKS 1-8 (11/5 08:00 UTC to 11/6 00:00 UTC)")
print("=" * 80)

start_utc = datetime(2025, 11, 5, 8, 0, 0, tzinfo=timezone.utc)
split_utc = datetime(2025, 11, 6, 0, 0, 0, tzinfo=timezone.utc)

segments = supabase.table("audio_segments").select("id, start_time, end_time, processed, created_at").eq("user_id", user_id).gte("start_time", start_utc.isoformat()).lt("end_time", split_utc.isoformat()).order("start_time", desc=False).execute()

print(f"\nFound {len(segments.data)} audio segments for chunks 1-8:")
if segments.data:
    print(f"\nFirst segment created: {segments.data[0].get('created_at')}")
    print(f"Last segment created: {segments.data[-1].get('created_at')}")
    print(f"\nAll segments:")
    for seg in segments.data:
        print(f"  - {seg['start_time']} to {seg['end_time']} (created: {seg['created_at']}, processed: {seg.get('processed', False)})")

# Check laughter_detections created_at timestamps for chunks 1-8
print("\n" + "=" * 80)
print("LAUGHTER DETECTIONS CREATED_AT TIMESTAMPS FOR CHUNKS 1-8")
print("=" * 80)

dets = supabase.table("laughter_detections").select("id, timestamp, created_at").eq("user_id", user_id).gte("timestamp", start_utc.isoformat()).lt("timestamp", split_utc.isoformat()).order("created_at", desc=False).execute()

if dets.data:
    print(f"\nFirst detection created: {dets.data[0].get('created_at')}")
    print(f"Last detection created: {dets.data[-1].get('created_at')}")
    print(f"\nSample timestamps:")
    for det in dets.data[:10]:
        print(f"  - Detection at {det['timestamp']} (created: {det['created_at']})")

print("\n" + "=" * 80)

