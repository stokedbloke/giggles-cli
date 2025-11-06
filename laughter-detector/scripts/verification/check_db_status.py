#!/usr/bin/env python3
"""
Check if audio segments are marked as processed in the database.
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Get all audio segments
result = supabase.table("audio_segments").select("*").execute()

print(f"Total segments: {len(result.data)}")
print("\nProcessing status:")
processed = sum(1 for s in result.data if s.get('processed'))
print(f"  Processed: {processed}")
print(f"  Not processed: {len(result.data) - processed}")

print("\nRecent segments:")
for segment in result.data[:5]:
    print(f"  ID: {segment['id'][:8]}...")
    print(f"    Processed: {segment.get('processed', False)}")
    print(f"    Date: {segment.get('date')}")
    print(f"    Start: {segment.get('start_time')}")
    print()
