#!/usr/bin/env python3
"""
Reprocess a date range for ALL users with active Limitless API keys.

Usage:
    python reprocess_all_users.py 2025-11-29 2025-11-29

This script:
1. Gets all users with active Limitless keys
2. Reprocesses the date range for each user sequentially
3. Logs progress and errors for each user
"""

import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# CRITICAL: Enable httpx patch BEFORE importing supabase
from src.utils.httpx_patch import enable_proxy_keyword_compat
enable_proxy_keyword_compat()

from src.services.supabase_client import get_service_role_client
from scripts.maintenance.manual_reprocess_yesterday import reprocess_date_range

# Load .env
load_dotenv()

async def main():
    if len(sys.argv) < 3:
        print("Usage: python reprocess_all_users.py START_DATE END_DATE")
        print("Example: python reprocess_all_users.py 2025-11-29 2025-11-29")
        sys.exit(1)
    
    start_date = sys.argv[1]
    end_date = sys.argv[2]
    
    print(f"\n🔄 Reprocessing {start_date} to {end_date} for ALL users\n")
    print("=" * 60)
    
    # Get all users with active Limitless keys
    supabase = get_service_role_client()
    result = (
        supabase.table("limitless_keys")
        .select("user_id, users!inner(email, timezone)")
        .eq("is_active", True)
        .execute()
    )
    
    if not result.data:
        print("❌ No users with active Limitless API keys found")
        sys.exit(1)
    
    users = [
        {
            "user_id": row["user_id"],
            "email": row["users"]["email"],
            "timezone": row["users"].get("timezone", "UTC"),
        }
        for row in result.data
    ]
    
    print(f"📋 Found {len(users)} user(s) with active API keys:\n")
    for user in users:
        print(f"   - {user['email']} ({user['user_id'][:8]}...)")
    
    print("\n" + "=" * 60)
    print("Starting reprocessing...\n")
    
    success_count = 0
    error_count = 0
    
    for i, user in enumerate(users, 1):
        print(f"\n[{i}/{len(users)}] Processing {user['email']} ({user['user_id'][:8]}...)")
        print("-" * 60)
        
        try:
            await reprocess_date_range(
                start_date_str=start_date,
                end_date_str=end_date,
                user_id=user["user_id"]
            )
            print(f"✅ Successfully processed {user['email']}")
            success_count += 1
        except Exception as e:
            print(f"❌ Error processing {user['email']}: {str(e)}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            error_count += 1
    
    print("\n" + "=" * 60)
    print(f"📊 REPROCESSING SUMMARY")
    print("=" * 60)
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {error_count}")
    print(f"📋 Total: {len(users)}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())

