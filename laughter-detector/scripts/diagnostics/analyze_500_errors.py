#!/usr/bin/env python3
"""
Analyze 500 errors from staging database for a given day.

Shows per user:
- Number of 500 errors that occurred during processing
- Number of chunks that were skipped due to 500 errors
- Total laughter detections for that day
- API call breakdown (200, 404, 500, etc.)

Usage:
    cd /path/to/laughter-detector && source venv/bin/activate
    python scripts/diagnostics/analyze_500_errors.py YYYY-MM-DD
"""

import os
import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta
import pytz

# Bootstrap
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import src  # noqa: F401
from src.services.supabase_client import get_service_role_client

supabase = get_service_role_client()


def analyze_500_errors_for_day(date: str):
    """
    Analyze 500 errors from processing_logs for a given day.
    
    Args:
        date: Date in YYYY-MM-DD format
    """
    print("=" * 80)
    print(f"500 ERROR ANALYSIS FOR {date}")
    print("=" * 80)
    
    # Get all users
    users = supabase.table("users").select("id, email, timezone").execute()
    
    if not users.data:
        print("❌ No users found")
        return
    
    for user in users.data:
        user_id = user["id"]
        user_email = user["email"]
        user_timezone = user.get("timezone") or "UTC"
        
        print(f"\n{'=' * 80}")
        print(f"👤 {user_email} ({user_id})")
        print(f"{'=' * 80}")
        
        # Get processing log for this date
        logs = (
            supabase.table("processing_logs")
            .select("*")
            .eq("user_id", user_id)
            .eq("date", date)
            .execute()
        )
        
        if not logs.data:
            print(f"   ⚠️  No processing log found for {date}")
            continue
        
        log = logs.data[0]  # Should be one log per user per day
        
        print(f"\n   📋 Processing Log Summary:")
        print(f"      Status: {log.get('status', 'N/A')}")
        print(f"      Audio files downloaded: {log.get('audio_files_downloaded', 0)}")
        print(f"      Laughter events found: {log.get('laughter_events_found', 0)}")
        print(f"      Duplicates skipped: {log.get('duplicates_skipped', 0)}")
        
        # Analyze API calls
        api_calls = log.get('api_calls')
        if api_calls:
            if isinstance(api_calls, str):
                try:
                    api_calls = json.loads(api_calls)
                except:
                    api_calls = []
            
            if isinstance(api_calls, list) and api_calls:
                status_counts = defaultdict(int)
                error_500_details = []
                
                for call in api_calls:
                    status = call.get('status_code', 'unknown')
                    status_counts[status] += 1
                    
                    if status == 500:
                        error_500_details.append({
                            'timestamp': call.get('timestamp', 'N/A'),
                            'error': call.get('error', 'N/A'),
                            'duration_ms': call.get('duration_ms', 0)
                        })
                
                print(f"\n   🌐 API Calls Breakdown:")
                print(f"      Total API calls: {len(api_calls)}")
                for status, count in sorted(status_counts.items()):
                    print(f"      Status {status}: {count}")
                
                if status_counts[500] > 0:
                    print(f"\n   ⚠️  500 ERRORS FOUND: {status_counts[500]}")
                    print(f"      These chunks were skipped (no retry in original code)")
                    print(f"      First 5 500 errors:")
                    for i, error in enumerate(error_500_details[:5], 1):
                        print(f"         {i}. {error['timestamp']}: {error['error']}")
                    if len(error_500_details) > 5:
                        print(f"         ... and {len(error_500_details) - 5} more")
                else:
                    print(f"\n   ✅ No 500 errors for this user on {date}")
        
        # Get actual laughter detections for this day
        try:
            user_tz = pytz.timezone(user_timezone)
        except:
            user_tz = pytz.UTC
        
        # Convert date to UTC range
        start_of_day = user_tz.localize(datetime.strptime(date, "%Y-%m-%d"))
        end_of_day = start_of_day + timedelta(days=1)
        start_utc = start_of_day.astimezone(pytz.UTC)
        end_utc = end_of_day.astimezone(pytz.UTC)
        
        detections = (
            supabase.table("laughter_detections")
            .select("id")
            .eq("user_id", user_id)
            .gte("timestamp", start_utc.isoformat())
            .lt("timestamp", end_utc.isoformat())
            .execute()
        )
        
        detection_count = len(detections.data) if detections.data else 0
        print(f"\n   🎭 Final Laughter Detections (stored in DB): {detection_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze 500 errors for a given day")
    parser.add_argument("date", help="Date in YYYY-MM-DD format")
    args = parser.parse_args()
    
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print(f"❌ Invalid date format: {args.date}. Use YYYY-MM-DD format.")
        sys.exit(1)
    
    analyze_500_errors_for_day(args.date)

