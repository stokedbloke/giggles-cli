#!/usr/bin/env python3
"""
Compare detection counts between two users to understand differences.

This will help us understand why User 1 had 47 events and User 2 had 49.
"""

import sys
from pathlib import Path
from datetime import datetime
import pytz

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment
env_paths = [
    Path(__file__).parent.parent.parent / ".env",
    Path.home() / ".env",
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

from src.services.supabase_client import get_service_role_client


def compare_detections():
    """Compare detection counts between two users."""
    
    user1_id = "d26444bc-e441-4f36-91aa-bfee24cb39fb"
    user2_id = "eb719f30-fe9e-42e4-8bb3-d5b4bb8b3327"
    
    # Nov 19 in America/Los_Angeles timezone
    tz = pytz.timezone("America/Los_Angeles")
    nov_19_start = tz.localize(datetime(2025, 11, 19, 0, 0, 0))
    nov_19_end = tz.localize(datetime(2025, 11, 20, 0, 0, 0))
    start_utc = nov_19_start.astimezone(pytz.UTC).isoformat()
    end_utc = nov_19_end.astimezone(pytz.UTC).isoformat()
    
    supabase = get_service_role_client()
    
    print("="*60)
    print("Comparing User Detections")
    print("="*60)
    print(f"Date range: Nov 19, 2025 (America/Los_Angeles)")
    print(f"UTC range: {start_utc} to {end_utc}\n")
    
    # Get User 1 detections
    user1_result = supabase.table("laughter_detections").select("id, timestamp, clip_path, created_at").eq("user_id", user1_id).gte("timestamp", start_utc).lt("timestamp", end_utc).order("timestamp").execute()
    
    # Get User 2 detections
    user2_result = supabase.table("laughter_detections").select("id, timestamp, clip_path, created_at").eq("user_id", user2_id).gte("timestamp", start_utc).lt("timestamp", end_utc).order("timestamp").execute()
    
    print(f"User 1 ({user1_id[:8]}...):")
    print(f"  Total detections: {len(user1_result.data)}")
    
    print(f"\nUser 2 ({user2_id[:8]}...):")
    print(f"  Total detections: {len(user2_result.data)}")
    
    print(f"\nDifference: {len(user2_result.data) - len(user1_result.data)} events")
    
    # Group by hour to see patterns
    print("\n" + "="*60)
    print("Detections by Hour (UTC)")
    print("="*60)
    
    user1_by_hour = {}
    user2_by_hour = {}
    
    for det in user1_result.data:
        hour = datetime.fromisoformat(det['timestamp'].replace('Z', '+00:00')).hour
        user1_by_hour[hour] = user1_by_hour.get(hour, 0) + 1
    
    for det in user2_result.data:
        hour = datetime.fromisoformat(det['timestamp'].replace('Z', '+00:00')).hour
        user2_by_hour[hour] = user2_by_hour.get(hour, 0) + 1
    
    all_hours = sorted(set(list(user1_by_hour.keys()) + list(user2_by_hour.keys())))
    
    print(f"{'Hour (UTC)':<12} {'User 1':<10} {'User 2':<10} {'Diff':<10}")
    print("-" * 50)
    for hour in all_hours:
        u1_count = user1_by_hour.get(hour, 0)
        u2_count = user2_by_hour.get(hour, 0)
        diff = u2_count - u1_count
        print(f"{hour:02d}:00-{hour+1:02d}:00  {u1_count:<10} {u2_count:<10} {diff:+d}")
    
    # Check processing logs
    print("\n" + "="*60)
    print("Processing Logs")
    print("="*60)
    
    user1_logs = supabase.table("processing_logs").select("*").eq("user_id", user1_id).eq("date", "2025-11-19").execute()
    user2_logs = supabase.table("processing_logs").select("*").eq("user_id", user2_id).eq("date", "2025-11-19").execute()
    
    print(f"User 1 processing logs: {len(user1_logs.data)}")
    for log in user1_logs.data:
        print(f"  - Trigger: {log.get('trigger_type')}")
        print(f"    Events found: {log.get('laughter_events_found')}")
        print(f"    Duplicates skipped: {log.get('duplicates_skipped')}")
        print(f"    Created: {log.get('created_at')}")
    
    print(f"\nUser 2 processing logs: {len(user2_logs.data)}")
    for log in user2_logs.data:
        print(f"  - Trigger: {log.get('trigger_type')}")
        print(f"    Events found: {log.get('laughter_events_found')}")
        print(f"    Duplicates skipped: {log.get('duplicates_skipped')}")
        print(f"    Created: {log.get('created_at')}")


if __name__ == "__main__":
    compare_detections()

