#!/usr/bin/env python3
"""
Find all days with laughter for a specific user.

Usage:
    python scripts/diagnostics/find_user_laughter_days.py USER_ID
"""

import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import pytz

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.supabase_client import get_service_role_client

supabase = get_service_role_client()

def get_user_laughter_days(user_id: str):
    """Get all days with laughter counts for a user."""
    # Get user timezone
    user_result = supabase.table("users").select("timezone").eq("id", user_id).execute()
    if not user_result.data:
        print(f"❌ User {user_id} not found")
        return
    
    user_timezone = user_result.data[0].get("timezone", "UTC")
    try:
        user_tz = pytz.timezone(user_timezone)
    except:
        user_tz = pytz.UTC
    
    print(f"User timezone: {user_timezone}")
    print(f"Fetching laughter detections...")
    
    # Fetch all detections with pagination
    detections_per_day = defaultdict(int)
    
    offset = 0
    page_size = 1000
    
    while True:
        page = (
            supabase.table("laughter_detections")
            .select("timestamp")
            .eq("user_id", user_id)
            .order("timestamp")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        
        if not page.data:
            break
        
        for det in page.data:
            timestamp_str = det["timestamp"]
            if timestamp_str.endswith("Z"):
                timestamp_str = timestamp_str[:-1] + "+00:00"
            timestamp_utc = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            timestamp_local = timestamp_utc.astimezone(user_tz)
            day = timestamp_local.strftime("%Y-%m-%d")
            detections_per_day[day] += 1
        
        if len(page.data) < page_size:
            break
        offset += page_size
    
    # Print results
    print(f"\n{'='*80}")
    print(f"Days with laughter for user {user_id[:8]}...")
    print(f"{'='*80}\n")
    
    if not detections_per_day:
        print("  No laughter detections found")
        return
    
    # Sort by date
    sorted_days = sorted(detections_per_day.items())
    
    print(f"{'Date':<12} {'Laughter Count':<15}")
    print("-" * 30)
    
    for day, count in sorted_days:
        print(f"{day:<12} {count:<15}")
    
    # Find days with 7 laughs
    days_with_7 = [day for day, count in sorted_days if count == 7]
    if days_with_7:
        print(f"\n{'='*80}")
        print(f"Days with exactly 7 laughs:")
        for day in days_with_7:
            print(f"  - {day}")
            print(f"    Test command:")
            print(f"      bash scripts/diagnostics/test_single_day_production.sh {day} {user_id}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_user_laughter_days.py USER_ID")
        sys.exit(1)
    
    user_id = sys.argv[1]
    get_user_laughter_days(user_id)

