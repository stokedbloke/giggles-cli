#!/usr/bin/env python3
"""
Migrate clip_path values from relative to absolute paths in the database.

This script converts all relative paths (./uploads/clips/...) to absolute paths
(/var/lib/giggles/.../uploads/clips/...) in the laughter_detections table.

Usage:
    # Test: One user, one date
    python migrate_paths_to_absolute.py --user-id USER_ID --date 2025-11-27

    # Test: One user, all dates
    python migrate_paths_to_absolute.py --user-id USER_ID

    # Production: All users, all dates
    python migrate_paths_to_absolute.py --all

Safety:
    - Dry-run mode by default (use --execute to actually update)
    - Logs all changes
    - Can be run multiple times safely (skips already absolute paths)
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import pytz

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()

from src.services.supabase_client import get_service_role_client
from src.utils.path_utils import strip_leading_dot_slash


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).resolve().parent.parent.parent


def convert_relative_to_absolute(relative_path: str, project_root: Path) -> str:
    """
    Convert a relative path to absolute.
    
    Args:
        relative_path: Relative path like ./uploads/clips/...
        project_root: Project root directory
        
    Returns:
        Absolute path
    """
    if not relative_path:
        return relative_path
    
    if os.path.isabs(relative_path):
        return relative_path  # Already absolute
    
    # Remove leading ./ if present
    normalized = strip_leading_dot_slash(relative_path)
    
    # Join with project root
    absolute_path = os.path.normpath(project_root / normalized)
    
    return absolute_path


def migrate_paths(
    user_id: str = None,
    date: str = None,
    all_users: bool = False,
    execute: bool = False,
    dry_run: bool = True,
):
    """
    Migrate clip_path values from relative to absolute.
    
    Args:
        user_id: User ID to migrate (optional, required if not --all)
        date: Date to migrate in YYYY-MM-DD format (optional)
        all_users: Migrate all users (optional)
        execute: Actually update the database (default: dry-run)
        dry_run: Show what would be changed without updating (default: True)
    """
    supabase = get_service_role_client()
    project_root = get_project_root()
    
    print(f"🔧 Path Migration Script")
    print(f"   Project root: {project_root}")
    print(f"   Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print()
    
    # Build query
    query = supabase.table("laughter_detections").select("id, clip_path, user_id, timestamp")
    
    if user_id:
        query = query.eq("user_id", user_id)
        print(f"   Filter: user_id = {user_id}")
    
    if date:
        # CRITICAL FIX: Use user's timezone for date boundaries (matches UI behavior)
        # Get user's timezone from database
        if user_id:
            user_result = supabase.table("users").select("timezone").eq("id", user_id).execute()
            if user_result.data and user_result.data[0].get("timezone"):
                user_timezone = user_result.data[0]["timezone"]
            else:
                user_timezone = "UTC"
        else:
            user_timezone = "UTC"
        
        user_tz = pytz.timezone(user_timezone)
        
        # Parse date as midnight in user's timezone, then convert to UTC
        # This matches how the UI groups detections by date
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_start_local = user_tz.localize(date_obj.replace(hour=0, minute=0, second=0, microsecond=0))
        date_end_local = user_tz.localize(date_obj.replace(hour=23, minute=59, second=59, microsecond=999999))
        
        # Convert to UTC for database query (timestamps are stored in UTC)
        date_start_utc = date_start_local.astimezone(pytz.UTC)
        date_end_utc = date_end_local.astimezone(pytz.UTC)
        
        query = query.gte("timestamp", date_start_utc.isoformat()).lt("timestamp", date_end_utc.isoformat())
        print(f"   Filter: date = {date} (user timezone: {user_timezone})")
        print(f"   UTC range: {date_start_utc.isoformat()} to {date_end_utc.isoformat()}")
    
    if not user_id and not all_users:
        print("❌ Error: Must specify --user-id or --all")
        sys.exit(1)
    
    # Execute query
    print("   Fetching records...")
    result = query.execute()
    
    if not result.data:
        print("   ℹ️  No records found")
        return
    
    print(f"   Found {len(result.data)} records")
    print()
    
    # Process records
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for record in result.data:
        clip_path = record.get("clip_path")
        record_id = record.get("id")
        
        if not clip_path:
            skipped_count += 1
            continue
        
        # Check if already absolute
        if os.path.isabs(clip_path):
            skipped_count += 1
            continue
        
        # Convert to absolute
        absolute_path = convert_relative_to_absolute(clip_path, project_root)
        
        print(f"   Record {record_id[:8]}...")
        print(f"      Old: {clip_path}")
        print(f"      New: {absolute_path}")
        
        if execute and not dry_run:
            try:
                supabase.table("laughter_detections").update({
                    "clip_path": absolute_path
                }).eq("id", record_id).execute()
                updated_count += 1
                print(f"      ✅ Updated")
            except Exception as e:
                error_count += 1
                print(f"      ❌ Error: {str(e)}")
        else:
            updated_count += 1
            print(f"      ⚠️  Would update (dry-run)")
        
        print()
    
    # Summary
    print("=" * 60)
    print("Summary:")
    print(f"   Total records: {len(result.data)}")
    print(f"   Would update: {updated_count}")
    print(f"   Skipped (already absolute): {skipped_count}")
    if error_count > 0:
        print(f"   Errors: {error_count}")
    print()
    
    if dry_run:
        print("⚠️  DRY RUN MODE - No changes made")
        print("   Run with --execute to actually update the database")
    else:
        print(f"✅ Updated {updated_count} records")


def main():
    parser = argparse.ArgumentParser(description="Migrate clip_path values from relative to absolute")
    parser.add_argument("--user-id", help="User ID to migrate")
    parser.add_argument("--date", help="Date to migrate (YYYY-MM-DD)")
    parser.add_argument("--all", action="store_true", help="Migrate all users")
    parser.add_argument("--execute", action="store_true", help="Actually update database (default: dry-run)")
    
    args = parser.parse_args()
    
    dry_run = not args.execute
    
    migrate_paths(
        user_id=args.user_id,
        date=args.date,
        all_users=args.all,
        execute=args.execute,
        dry_run=dry_run,
    )


if __name__ == "__main__":
    main()

