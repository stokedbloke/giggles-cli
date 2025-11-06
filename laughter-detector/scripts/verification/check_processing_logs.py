#!/usr/bin/env python3
"""Quick script to check processing_logs entries."""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime
import pytz

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

result = supabase.table("processing_logs").select("*").order("created_at", desc=True).limit(15).execute()

pst = pytz.timezone('America/Los_Angeles')

print("Recent processing_logs entries:\n")
for log in result.data:
    # Handle various timestamp formats
    created_str = log["created_at"]
    if created_str.endswith("Z"):
        created_str = created_str.replace("Z", "+00:00")
    elif "+" not in created_str and ":" in created_str:
        # Handle format like '2025-11-04T06:21:12.82617+00:00' with missing timezone
        if created_str.count(":") == 2 and "." in created_str:
            # Try to parse and reformat
            try:
                parts = created_str.split("+")
                if len(parts) == 1:
                    created_str = created_str + "+00:00"
            except:
                pass
    
    try:
        created = datetime.fromisoformat(created_str)
        created_pst = created.astimezone(pst)
        date_processed = log.get("date")
        
        print(f"Entry:")
        print(f"  created_at: {created.strftime('%Y-%m-%d %H:%M')} UTC ({created_pst.strftime('%Y-%m-%d %H:%M')} PST)")
        print(f"  date (processed): {date_processed}")
        print(f"  trigger_type: {log.get('trigger_type')}")
        print(f"  laughter_events: {log.get('laughter_events_found', 0)}")
        print(f"  duration: {log.get('processing_duration_seconds', 0)}s")
        print(f"  status: {log.get('status')}")
        
        if date_processed and "2025-11-02" in str(date_processed):
            print(f"  *** THIS IS THE 11/2 ENTRY YOU ASKED ABOUT ***")
            print(f"  Explanation: This entry was created at {created.strftime('%Y-%m-%d %H:%M')} UTC")
            print(f"               but processed date 2025-11-02. This could be:")
            print(f"               - A manual reprocess of 11/2 data")
            print(f"               - An old entry from a previous day")
        print("-" * 60)
    except Exception as e:
        print(f"Error parsing entry: {log.get('created_at')} - {e}")
        print(f"  date: {log.get('date')}")
        print(f"  trigger_type: {log.get('trigger_type')}")
        print("-" * 60)
