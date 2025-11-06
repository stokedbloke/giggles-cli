#!/usr/bin/env python3
"""
Check if file paths in database are still encrypted or corrupted.
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Get all segments
result = supabase.table("audio_segments").select("id, file_path, processed").execute()

print(f"Total segments: {len(result.data)}")
print("\nFile path analysis:")
for segment in result.data[:3]:
    print(f"\nSegment ID: {segment['id'][:8]}...")
    print(f"  Processed: {segment.get('processed', False)}")
    encrypted_path = segment.get('file_path', '')
    print(f"  Encrypted path: {encrypted_path[:80]}...")
    print(f"  Path length: {len(encrypted_path)}")
