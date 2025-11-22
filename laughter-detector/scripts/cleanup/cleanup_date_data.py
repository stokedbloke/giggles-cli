#!/usr/bin/env python3
"""
Cleanup script to delete all data for a specific date (in user's timezone).

WARNING: This permanently deletes data from database and disk.
Use with caution - this is for testing purposes only.

REUSES CODE: Uses deletion functions from manual_reprocess_yesterday.py to avoid duplication.

Usage:
    python cleanup_date_data.py 2025-11-03

TIMEZONE BEHAVIOR:
    This script now deletes data by date in the USER'S timezone (not UTC).
    It queries each user's timezone from the database and calculates the correct UTC range.
    This matches how the cron job processes "yesterday" for each user.

    Example (PST user, UTC-8):
        - To delete "Nov 3 PST" (local date):
          python cleanup_date_data.py 2025-11-03
          
        - The script will:
          1. Query user's timezone (e.g., "America/Los_Angeles")
          2. Calculate Nov 3 PST range: Nov 3 00:00 PST → Nov 4 00:00 PST
          3. Convert to UTC: Nov 3 08:00 UTC → Nov 4 08:00 UTC
          4. Delete all data in that UTC range

    This ensures complete deletion of all files/database entries for that local date.
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import pytz

# Add project root and scripts directory to path
project_root = Path(__file__).parent.parent.parent
scripts_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(scripts_dir))

# Load .env BEFORE importing anything that uses settings
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from supabase import create_client
from typing import Optional

# REUSE EXISTING CODE: Import deletion functions from manual_reprocess_yesterday
# (This import happens AFTER load_dotenv to ensure settings can initialize)
from maintenance.manual_reprocess_yesterday import clear_database_records, clear_disk_files


async def delete_date_data(target_date_str: str, user_id: Optional[str] = None):
    """
    Delete all data for a specific date (in user's timezone) from database and disk.
    
    REUSES CODE: Uses clear_database_records() and clear_disk_files() from manual_reprocess_yesterday.py
    
    TIMEZONE-AWARE: Queries each user's timezone and calculates the correct UTC range for deletion.
    This matches how the cron job processes dates (in user's timezone).
    
    Args:
        target_date_str: Date in YYYY-MM-DD format (interpreted in user's timezone)
        user_id: Optional user ID to limit deletion (if None, deletes for all users)
    """
    try:
        import asyncio
        
        # Parse date
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        
        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_service_key:
            print("❌ Supabase credentials not found in environment")
            return
        
        supabase = create_client(supabase_url, supabase_service_key)
        
        # Get users (with timezone) if not provided
        if user_id:
            user_result = supabase.table("users").select("id, timezone").eq("id", user_id).execute()
            users = user_result.data if user_result.data else []
        else:
            # Get all users with their timezones
            users_result = supabase.table("users").select("id, timezone").execute()
            users = users_result.data if users_result.data else []
        
        if not users:
            print(f"❌ No users found")
            return
        
        print(f"🗑️  Deleting all data for {target_date_str} (in each user's timezone)")
        print(f"👥 Found {len(users)} user(s)")
        print(f"\n   ⚠️  TIMEZONE-AWARE: Each user's timezone will be used to calculate UTC deletion range.")
        print(f"      This matches how the cron job processes dates.\n")
        
        # REUSE EXISTING CODE: Use functions from manual_reprocess_yesterday.py
        # CRITICAL ORDER: Delete files FIRST (while database records still exist)
        # clear_disk_files() reads paths from database, then deletes files
        for user in users:
            uid = user['id']
            user_timezone = user.get('timezone', 'UTC')
            
            print(f"\n🔍 Processing user: {uid[:8]}... (timezone: {user_timezone})")
            
            # TIMEZONE-AWARE: Calculate UTC range for this user's timezone
            # This matches the logic in process_nightly_audio.py for calculating "yesterday"
            user_tz = pytz.timezone(user_timezone)
            start_of_day_local = user_tz.localize(datetime.combine(target_date, datetime.min.time()))
            end_of_day_local = start_of_day_local + timedelta(days=1)
            
            # Convert to UTC for deletion (database stores all timestamps in UTC)
            start_of_day_utc = start_of_day_local.astimezone(pytz.UTC)
            end_of_day_utc = end_of_day_local.astimezone(pytz.UTC)
            
            print(f"   Local date: {target_date_str} ({user_timezone})")
            print(f"   UTC range: {start_of_day_utc.strftime('%Y-%m-%d %H:%M')} → {end_of_day_utc.strftime('%Y-%m-%d %H:%M')}")
            
            # Clear disk files FIRST (reuses clear_disk_files from manual_reprocess_yesterday.py)
            await clear_disk_files(uid, start_of_day_utc, end_of_day_utc, supabase)
            
            # Then clear database records (after files are deleted)
            await clear_database_records(uid, start_of_day_utc, end_of_day_utc, supabase)
        
        print(f"\n{'='*60}")
        print(f"✅ Cleanup Complete for {target_date_str}")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {str(e)}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    
    if len(sys.argv) < 2:
        print("Usage: python cleanup_date_data.py YYYY-MM-DD [user_id]")
        print("Example: python cleanup_date_data.py 2025-11-03")
        print("Example: python cleanup_date_data.py 2025-11-03 d223fee9-b279-4dc7-8cd1-188dc09ccdd1")
        print("\nTIMEZONE-AWARE: The date is interpreted in each user's timezone (from database).")
        print("The script calculates the correct UTC range for deletion, matching cron job behavior.")
        sys.exit(1)
    
    target_date = sys.argv[1]
    user_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Confirmation prompt
    print("⚠️  WARNING: This will permanently delete all data for this date!")
    print(f"   Date: {target_date} (interpreted in each user's timezone)")
    if user_id:
        print(f"   User ID: {user_id}")
    else:
        print(f"   All users")
    
    response = input("Are you sure you want to continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        sys.exit(0)
    
    # Run async function
    asyncio.run(delete_date_data(target_date, user_id))
