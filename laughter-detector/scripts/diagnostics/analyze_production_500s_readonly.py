#!/usr/bin/env python3
"""
Read-only analysis of production 500 errors.

SAFE: This script only READS from production Supabase - no changes made.
Use this to find the best days to test retry logic.

Usage:
    # On MacBook - uses .env.production
    python scripts/diagnostics/analyze_production_500s_readonly.py --days 60
"""

import sys
from pathlib import Path
import json
import argparse
from collections import defaultdict
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load production environment
import os
from dotenv import load_dotenv

# Load production env
prod_env = PROJECT_ROOT / ".env.production"
if prod_env.exists():
    load_dotenv(prod_env)
    print(f"✅ Loaded production environment from {prod_env}")
else:
    print(f"⚠️  {prod_env} not found - using default .env")
    load_dotenv()

from supabase import create_client

def get_production_client():
    """Get production Supabase client (read-only operations)."""
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("Production Supabase credentials not found in .env.production")
    
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def analyze_production_500s(days=60, min_500_errors=1):
    """Analyze production logs for 500 errors (read-only)."""
    print("=" * 80)
    print("READ-ONLY ANALYSIS: Production 500 Errors")
    print("=" * 80)
    print(f"\n⚠️  This script only READS from production - no changes made")
    print(f"Analyzing last {days} days for days with {min_500_errors}+ 500 errors...")
    
    supabase = get_production_client()
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get users
    users = supabase.table("users").select("id, email").execute()
    user_map = {user["id"]: user["email"] for user in users.data} if users.data else {}
    
    # Get processing logs
    print(f"\n📊 Fetching processing logs from {start_date} to {end_date}...")
    logs = (
        supabase.table("processing_logs")
        .select("user_id, date, api_calls, laughter_events_found, duplicates_skipped")
        .gte("date", str(start_date))
        .lte("date", str(end_date))
        .execute()
    )
    
    print(f"   Found {len(logs.data) if logs.data else 0} processing log(s)")
    
    # Analyze
    test_cases = []
    
    for log in logs.data or []:
        api_calls = log.get("api_calls", [])
        if isinstance(api_calls, str):
            try:
                api_calls = json.loads(api_calls)
            except:
                api_calls = []
        
        # Count status codes
        status_counts = defaultdict(int)
        for call in api_calls:
            status = call.get("status_code", "unknown")
            status_counts[status] += 1
        
        error_500_count = status_counts[500]
        
        if error_500_count >= min_500_errors:
            # Check for retry patterns
            retry_patterns = 0
            for i in range(len(api_calls) - 1):
                if api_calls[i].get("status_code") == 500 and api_calls[i+1].get("status_code") == 200:
                    retry_patterns += 1
            
            test_cases.append({
                "date": log["date"],
                "user_id": log["user_id"],
                "user_email": user_map.get(log["user_id"], "Unknown"),
                "500_errors": error_500_count,
                "200_success": status_counts[200],
                "404_no_data": status_counts[404],
                "retry_patterns": retry_patterns,
                "laughter_events": log.get("laughter_events_found", 0),
                "duplicates_skipped": log.get("duplicates_skipped", 0),
            })
    
    # Sort by 500 count
    test_cases.sort(key=lambda x: x["500_errors"], reverse=True)
    
    return test_cases

def main():
    parser = argparse.ArgumentParser(description="Read-only analysis of production 500 errors")
    parser.add_argument("--days", type=int, default=60, help="Look back N days")
    parser.add_argument("--min-500-errors", type=int, default=1, help="Minimum 500 errors to show")
    args = parser.parse_args()
    
    test_cases = analyze_production_500s(days=args.days, min_500_errors=args.min_500_errors)
    
    if not test_cases:
        print(f"\n❌ No days found with {args.min_500_errors}+ 500 errors")
        return
    
    print(f"\n✅ Found {len(test_cases)} day(s) with {args.min_500_errors}+ 500 errors:")
    print("\n" + "=" * 80)
    print(f"{'Date':<12} {'User':<30} {'500 Errors':<12} {'200 Success':<12} {'Retry Patterns':<15} {'Laughter':<12}")
    print("-" * 100)
    
    for tc in test_cases:
        print(f"{tc['date']:<12} {tc['user_email'][:29]:<30} {tc['500_errors']:<12} {tc['200_success']:<12} {tc['retry_patterns']:<15} {tc['laughter_events']:<12}")
    
    # Best test candidates
    print("\n" + "=" * 80)
    print("BEST TEST CANDIDATES")
    print("=" * 80)
    
    # Prioritize: more 500 errors, fewer retry patterns (means retries might help)
    best_candidates = sorted(
        [tc for tc in test_cases if tc['retry_patterns'] == 0],
        key=lambda x: x['500_errors'],
        reverse=True
    )[:5]
    
    if best_candidates:
        print("\n📋 Days with 500 errors but NO retry patterns (retries might help):")
        for i, tc in enumerate(best_candidates, 1):
            print(f"\n   {i}. {tc['date']} - {tc['user_email'][:30]}")
            print(f"      - 500 Errors: {tc['500_errors']}")
            print(f"      - 200 Success: {tc['200_success']}")
            print(f"      - Laughter Events: {tc['laughter_events']}")
            print(f"      - Test command:")
            print(f"        python scripts/diagnostics/test_retry_methodical.py --date {tc['date']} --user-id {tc['user_id']}")
    else:
        print("\n⚠️  All days with 500 errors already have retry patterns")
        print("   This suggests retry logic is already deployed and working")
    
    print("\n" + "=" * 80)
    print("SAFETY NOTE")
    print("=" * 80)
    print("✅ This script only READS from production - no changes made")
    print("✅ Safe to run anytime - just analyzes existing data")

if __name__ == "__main__":
    main()

