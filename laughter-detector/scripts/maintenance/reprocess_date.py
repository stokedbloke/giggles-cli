#!/usr/bin/env python3
"""
Reprocess audio for a specific date.
Usage: python reprocess_date.py YYYY-MM-DD
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

if len(sys.argv) < 2:
    print("Usage: python reprocess_date.py YYYY-MM-DD")
    sys.exit(1)

date_str = sys.argv[1]
date = datetime.strptime(date_str, '%Y-%m-%d')
date_next = (date + timedelta(days=1))

supabase = create_client(
    os.getenv('SUPABASE_URL'), 
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Get user ID (your test user)
user_id = 'd223fee9-b279-4dc7-8cd1-188dc09ccdd1'

print(f"Finding segments for {date_str}...")
segments = supabase.table('audio_segments').select('*').eq('user_id', user_id).gte('start_time', date.isoformat()).lt('start_time', date_next.isoformat()).execute()

if not segments.data:
    print(f"No segments found for {date_str}")
    sys.exit(0)

print(f"Found {len(segments.data)} segments")

# Reprocess each segment
for seg in segments.data:
    print(f"\nProcessing segment: {seg['id'][:8]}...")
    print(f"  File: {seg['file_path']}")
    
    # Check if file exists
    file_path = os.path.abspath(seg['file_path'])
    if not os.path.exists(file_path):
        print(f"  File not found: {file_path}")
        continue
    
    # Import scheduler
    sys.path.insert(0, os.path.dirname(__file__))
    from src.services.scheduler import scheduler
    
    # Reprocess
    import asyncio
    asyncio.run(scheduler._process_audio_segment(user_id, seg, seg['id']))
    print(f"  Reprocessed segment {seg['id'][:8]}")

print("\n✅ Reprocessing complete")
