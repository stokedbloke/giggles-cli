#!/usr/bin/env python3
"""
Check if orphaned files have database records.

This will help us understand why User 1 had 3 orphaned files.
"""

import sys
from pathlib import Path

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


def check_orphaned_files():
    """Check if the 3 orphaned files have DB records."""
    
    # The 3 orphaned files from User 1
    orphaned_files = [
        "20251119_210000-20251119_211911_laughter_204-48_13.wav",
        "20251119_160000-20251119_163000_laughter_177-60_13.wav",
        "20251119_160000-20251119_163000_laughter_185-28_13.wav",
    ]
    
    user_id = "d26444bc-e441-4f36-91aa-bfee24cb39fb"
    
    supabase = get_service_role_client()
    
    print("="*60)
    print("Checking Orphaned Files in Database")
    print("="*60)
    print(f"User ID: {user_id[:8]}...")
    print(f"Files to check: {len(orphaned_files)}\n")
    
    for filename in orphaned_files:
        print(f"Checking: {filename}")
        
        # Extract clip path (assuming standard format)
        # Format: uploads/clips/{user_id}/{filename}
        clip_path = f"uploads/clips/{user_id}/{filename}"
        
        # Check laughter_detections table
        result = supabase.table("laughter_detections").select("id, timestamp, clip_path").eq("user_id", user_id).eq("clip_path", clip_path).execute()
        
        if result.data:
            print(f"  ✅ Found {len(result.data)} record(s) in laughter_detections:")
            for record in result.data:
                print(f"     - ID: {record['id']}")
                print(f"       Timestamp: {record['timestamp']}")
                print(f"       Clip path: {record['clip_path']}")
        else:
            print(f"  ❌ No records found in laughter_detections")
        
        # Check if file exists on disk
        file_path = Path("uploads/clips") / user_id / filename
        if file_path.exists():
            print(f"  ✅ File exists on disk: {file_path}")
        else:
            print(f"  ❌ File does NOT exist on disk")
        
        print()


if __name__ == "__main__":
    check_orphaned_files()

