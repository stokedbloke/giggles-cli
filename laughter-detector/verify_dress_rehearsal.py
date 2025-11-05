#!/usr/bin/env python3
"""
Dress Rehearsal Verification Script

This script automates the verification steps from the True Dress Rehearsal Plan.
It checks database state, file system state, and consistency between them.
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import pytz

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Configuration
USER_ID = 'd223fee9-b279-4dc7-8cd1-188dc09ccdd1'
USER_TIMEZONE = 'America/Los_Angeles'

def get_supabase():
    """Get Supabase client with service role key."""
    return create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    )

def calculate_utc_range(test_date_str: str, user_tz_str: str) -> Tuple[datetime, datetime]:
    """
    Calculate UTC range for a local date in user's timezone.
    
    Args:
        test_date_str: Date string in format 'YYYY-MM-DD' (local date)
        user_tz_str: User's timezone (e.g., 'America/Los_Angeles')
    
    Returns:
        Tuple of (start_utc, end_utc) datetime objects
    """
    user_tz = pytz.timezone(user_tz_str)
    test_date = datetime.strptime(test_date_str, '%Y-%m-%d').date()
    
    # Start of day in user's timezone
    start_local = user_tz.localize(datetime.combine(test_date, datetime.min.time()))
    end_local = user_tz.localize(datetime.combine(test_date + timedelta(days=1), datetime.min.time()))
    
    # Convert to UTC
    start_utc = start_local.astimezone(pytz.UTC)
    end_utc = end_local.astimezone(pytz.UTC)
    
    return start_utc, end_utc

def verify_database(supabase, user_id: str, test_date: str, start_utc: datetime, end_utc: datetime) -> Dict:
    """Verify database state."""
    results = {
        'processing_logs': [],
        'laughter_detections': [],
        'audio_segments': [],
        'errors': []
    }
    
    try:
        # 1. Processing logs
        logs = supabase.table('processing_logs').select('*').eq('user_id', user_id).eq('date', test_date).order('created_at', desc=True).execute()
        results['processing_logs'] = logs.data
        
        # 2. Laughter detections
        dets = supabase.table('laughter_detections').select('id, timestamp, clip_path, created_at').eq('user_id', user_id).gte('timestamp', start_utc.isoformat()).lt('timestamp', end_utc.isoformat()).execute()
        results['laughter_detections'] = dets.data
        
        # 3. Audio segments
        # FIX: Use .lte() instead of .lt() to include boundary segments (e.g., chunk ending exactly at end_utc)
        segs = supabase.table('audio_segments').select('id, start_time, end_time, file_path, processed, created_at').eq('user_id', user_id).gte('start_time', start_utc.isoformat()).lte('end_time', end_utc.isoformat()).order('start_time', desc=False).execute()
        results['audio_segments'] = segs.data
        
    except Exception as e:
        results['errors'].append(f"Database query error: {str(e)}")
    
    return results

def verify_files(user_id: str, test_date: str, base_dir: Path) -> Dict:
    """Verify files on disk."""
    results = {
        'ogg_files': [],
        'wav_files': [],
        'missing_ogg': [],
        'missing_wav': [],
        'orphaned_ogg': [],
        'orphaned_wav': []
    }
    
    # Find OGG files
    audio_dir = base_dir / 'uploads' / 'audio' / user_id
    if audio_dir.exists():
        for f in audio_dir.glob(f'*{test_date.replace("-", "")}*.ogg'):
            results['ogg_files'].append(f)
    
    # Find WAV files
    clips_dir = base_dir / 'uploads' / 'clips' / user_id
    if clips_dir.exists():
        for f in clips_dir.glob(f'*{test_date.replace("-", "")}*.wav'):
            results['wav_files'].append(f)
    
    return results

def verify_consistency(db_results: Dict, file_results: Dict, base_dir: Path) -> Dict:
    """Verify consistency between database and files."""
    issues = []
    
    # Check OGG files
    db_ogg_paths = {os.path.normpath(seg.get('file_path', '')) for seg in db_results['audio_segments'] if seg.get('file_path')}
    disk_ogg_files = {str(f.relative_to(base_dir)) for f in file_results['ogg_files']}
    
    missing_ogg = db_ogg_paths - disk_ogg_files
    orphaned_ogg = disk_ogg_files - db_ogg_paths
    
    if missing_ogg:
        issues.append(f"Missing OGG files (in DB but not on disk): {len(missing_ogg)}")
        for path in list(missing_ogg)[:5]:  # Show first 5
            issues.append(f"  - {path}")
    
    if orphaned_ogg:
        issues.append(f"Orphaned OGG files (on disk but not in DB): {len(orphaned_ogg)}")
        for path in list(orphaned_ogg)[:5]:  # Show first 5
            issues.append(f"  - {path}")
    
    # Check WAV files
    db_wav_paths = {os.path.normpath(det.get('clip_path', '')) for det in db_results['laughter_detections'] if det.get('clip_path')}
    disk_wav_files = {str(f.relative_to(base_dir)) for f in file_results['wav_files']}
    
    missing_wav = db_wav_paths - disk_wav_files
    orphaned_wav = disk_wav_files - db_wav_paths
    
    if missing_wav:
        issues.append(f"Missing WAV files (in DB but not on disk): {len(missing_wav)}")
        for path in list(missing_wav)[:5]:  # Show first 5
            issues.append(f"  - {path}")
    
    if orphaned_wav:
        issues.append(f"Orphaned WAV files (on disk but not in DB): {len(orphaned_wav)}")
        for path in list(orphaned_wav)[:5]:  # Show first 5
            issues.append(f"  - {path}")
    
    return {
        'issues': issues,
        'missing_ogg': missing_ogg,
        'orphaned_ogg': orphaned_ogg,
        'missing_wav': missing_wav,
        'orphaned_wav': orphaned_wav
    }

def print_summary(step_name: str, db_results: Dict, file_results: Dict, consistency: Dict):
    """Print verification summary."""
    print("=" * 80)
    print(f"{step_name.upper()} VERIFICATION")
    print("=" * 80)
    print()
    
    print("DATABASE:")
    print(f"  Processing logs: {len(db_results['processing_logs'])}")
    print(f"  Laughter detections: {len(db_results['laughter_detections'])}")
    print(f"  Audio segments: {len(db_results['audio_segments'])}")
    
    if db_results['processing_logs']:
        latest_log = db_results['processing_logs'][0]
        print(f"\n  Latest processing log:")
        print(f"    - Created: {latest_log.get('created_at', 'N/A')}")
        print(f"    - Trigger: {latest_log.get('trigger_type', 'N/A')}")
        print(f"    - Status: {latest_log.get('status', 'N/A')}")
        print(f"    - Audio downloaded: {latest_log.get('audio_files_downloaded', 0)}")
        print(f"    - Laughter events: {latest_log.get('laughter_events_found', 0)}")
        print(f"    - Duplicates skipped: {latest_log.get('duplicates_skipped', 0)}")
    
    print()
    print("FILES ON DISK:")
    print(f"  OGG files: {len(file_results['ogg_files'])}")
    print(f"  WAV files: {len(file_results['wav_files'])}")
    
    print()
    print("CONSISTENCY:")
    if consistency['issues']:
        print("  ❌ Issues found:")
        for issue in consistency['issues']:
            print(f"    - {issue}")
    else:
        print("  ✅ No issues - database and files are consistent")
    
    print()
    
    # Check counts match
    log = db_results['processing_logs'][0] if db_results['processing_logs'] else {}
    expected_ogg = log.get('audio_files_downloaded', 0)
    expected_wav = log.get('laughter_events_found', 0) - log.get('duplicates_skipped', 0)
    
    if expected_ogg and expected_ogg != len(db_results['audio_segments']):
        print(f"  ⚠️  WARNING: Processing log says {expected_ogg} OGG files, but DB has {len(db_results['audio_segments'])} segments")
    
    if expected_ogg and expected_ogg != len(file_results['ogg_files']):
        print(f"  ⚠️  WARNING: Processing log says {expected_ogg} OGG files, but disk has {len(file_results['ogg_files'])} files")
    
    if expected_wav and expected_wav != len(db_results['laughter_detections']):
        print(f"  ⚠️  WARNING: Expected {expected_wav} WAV files (after dedup), but DB has {len(db_results['laughter_detections'])} detections")
    
    if expected_wav and expected_wav != len(file_results['wav_files']):
        print(f"  ⚠️  WARNING: Expected {expected_wav} WAV files, but disk has {len(file_results['wav_files'])} files")
    
    print()

def main():
    """Main verification function."""
    if len(sys.argv) < 2:
        print("Usage: python3 verify_dress_rehearsal.py <test_date> [step_name]")
        print("  test_date: Date in format YYYY-MM-DD (local date in user's timezone)")
        print("  step_name: Optional step name (baseline, after_cleanup, after_cron)")
        sys.exit(1)
    
    test_date = sys.argv[1]
    step_name = sys.argv[2] if len(sys.argv) > 2 else 'verification'
    
    print(f"Verifying: {step_name}")
    print(f"Test date: {test_date} ({USER_TIMEZONE})")
    print()
    
    # Calculate UTC range
    start_utc, end_utc = calculate_utc_range(test_date, USER_TIMEZONE)
    print(f"UTC range: {start_utc.isoformat()} to {end_utc.isoformat()}")
    print()
    
    # Verify
    base_dir = Path(__file__).parent
    supabase = get_supabase()
    
    db_results = verify_database(supabase, USER_ID, test_date, start_utc, end_utc)
    file_results = verify_files(USER_ID, test_date, base_dir)
    consistency = verify_consistency(db_results, file_results, base_dir)
    
    # Print summary
    print_summary(step_name, db_results, file_results, consistency)
    
    # Determine pass/fail
    if consistency['issues']:
        print("❌ VERIFICATION FAILED - See issues above")
        sys.exit(1)
    elif step_name == 'after_cleanup':
        if len(db_results['processing_logs']) == 0 and len(db_results['laughter_detections']) == 0 and len(db_results['audio_segments']) == 0:
            print("✅ VERIFICATION PASSED - All data cleaned")
            sys.exit(0)
        else:
            print("❌ VERIFICATION FAILED - Data still exists after cleanup")
            sys.exit(1)
    else:
        print("✅ VERIFICATION PASSED")
        sys.exit(0)

if __name__ == '__main__':
    main()
