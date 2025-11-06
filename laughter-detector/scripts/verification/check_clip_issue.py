#!/usr/bin/env python3
"""
Check for clip files that are in DB but not on disk.
"""

from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv('SUPABASE_URL'), 
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Get all detections
result = supabase.table('laughter_detections').select('*').execute()

missing = []
for d in result.data:
    clip_path = d.get('clip_path', '')
    if not clip_path:
        continue
        
    # Try absolute path
    abs_path = clip_path if clip_path.startswith('/') else os.path.abspath(clip_path.lstrip('./'))
    
    if not os.path.exists(abs_path):
        missing.append((d['id'], clip_path, abs_path))

print(f"Total detections: {len(result.data)}")
print(f"Missing clips: {len(missing)}")
print()

for det_id, db_path, abs_path in missing[:10]:
    print(f"Detection: {det_id[:8]}...")
    print(f"  DB path: {db_path}")
    print(f"  Absolute: {abs_path}")
    print()

