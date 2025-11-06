#!/usr/bin/env python3
"""
Clean up orphaned audio files that have been processed but not deleted.
"""

import os
import shutil
from pathlib import Path

# Configuration
uploads_dir = Path('./uploads/audio')

print("🗑️  Cleaning up orphaned audio files...")
print()

# Find all user directories
if not uploads_dir.exists():
    print("No audio directory found")
    exit(0)

user_dirs = [d for d in uploads_dir.iterdir() if d.is_dir()]
print(f"Found {len(user_dirs)} user directories")

total_deleted = 0
total_size = 0

for user_dir in user_dirs:
    user_id = user_dir.name
    print(f"\n📁 User: {user_id}")
    
    # Find all .ogg files
    ogg_files = list(user_dir.glob('*.ogg'))
    print(f"  Found {len(ogg_files)} .ogg files")
    
    # Delete all .ogg files (they've been processed)
    for ogg_file in ogg_files:
        try:
            file_size = ogg_file.stat().st_size
            ogg_file.unlink()
            total_deleted += 1
            total_size += file_size
            print(f"  ✅ Deleted: {ogg_file.name} ({file_size / 1024 / 1024:.2f} MB)")
        except Exception as e:
            print(f"  ❌ Failed to delete {ogg_file.name}: {str(e)}")

print()
print("=" * 50)
print(f"✅ Cleanup complete!")
print(f"   Total files deleted: {total_deleted}")
print(f"   Total space freed: {total_size / 1024 / 1024:.2f} MB")
print()
