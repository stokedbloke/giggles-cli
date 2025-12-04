#!/usr/bin/env python3
"""
Diagnostic script to check user processing status.

Shows comprehensive information about:
- Audio segments processed (from audio_segments table)
- Limitless recordings downloaded (from processing_logs.audio_files_downloaded)
- Total recording duration (calculated from audio_segments)
- Laughter detections found
- Processing status and errors

PROCESSING PIPELINE EXPLANATION:
==================================

1. LIMITLESS API STAGE (Limitless API → Audio Files)
   - API Calls: All HTTP requests to Limitless API (includes 200, 404, 5xx)
   - Audio Files Downloaded: Only successful 200 responses with audio data
   - Why they differ: 404 responses mean no audio for that time window (normal)
     Example: 32 API calls (21×200 + 11×404) = 21 Audio Files Downloaded

2. YAMNET DETECTION STAGE (Audio Files → Laughter Events)
   - Laughter Events Found: All laughter detections from YAMNet (before duplicate check)
   - This is the raw count of potential laughter events detected in audio files

3. DUPLICATE FILTERING STAGE (Laughter Events → Final Stored)
   - Duplicates Skipped: Events filtered out as duplicates (time-window, clip-path, missing-file)
   - Final Stored = Laughter Events Found - Duplicates Skipped
   - This is what actually gets saved to laughter_detections table

TIMEZONE HANDLING:
==================

This script correctly handles users in different timezones:

1. audio_segments.date and processing_logs.date:
   - Already stored in user's timezone (calendar date)
   - Direct date comparison works - no conversion needed

2. laughter_detections.timestamp:
   - Stored in UTC (TIMESTAMPTZ)
   - For date filtering: Converts user timezone date to UTC range
   - Matches API approach in src/api/data_routes.py get_laughter_detections()
   - Ensures midnight-to-midnight in user's timezone, not UTC
   - Example: Nov 3 PST (UTC-8) = Nov 3 00:00 PST to Nov 4 00:00 PST = Nov 3 08:00 UTC to Nov 4 08:00 UTC

3. Date grouping for display:
   - Converts UTC timestamps to user's timezone for date grouping
   - Matches API approach in src/api/data_routes.py get_daily_summary()

TECHNICAL DEBT / CODE REUSE:
============================

✅ REUSES EXISTING PATTERNS:
- Pagination: Same pattern as src/api/data_routes.py (lines 95-110)
- Timezone conversion: Same approach as src/api/data_routes.py (lines 220-227)
- UTC range queries: Same approach as API for date filtering

⚠️ MINOR TECHNICAL DEBT:
- Timezone conversion logic is duplicated (not extracted to shared utility)
- However, it's simple and matches API exactly, so low maintenance burden
- If API timezone logic changes, this script should be updated to match

Usage:
    # On PRODUCTION server (recommended for security):
    python3 check_user_processing_status.py <user_id> [date]
    
    # On staging/local machine, connect to PRODUCTION database:
    python3 check_user_processing_status.py <user_id> [date] --production
    
    # On staging/local machine, use staging database (default):
    python3 check_user_processing_status.py <user_id> [date] --staging
    
Arguments:
    user_id: Required - User UUID
    date: Optional - Date in YYYY-MM-DD format (defaults to all dates)
    
Options:
    --production: Use production database credentials (from env vars or .env.production)
    --staging: Use staging database credentials (default, from .env)
    
Security Note:
    For production data, it's recommended to run this script directly on the production
    server where credentials are already configured. Use --production flag only when
    necessary for remote debugging.
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import pytz
from typing import Optional, Dict, Any, List

# Setup
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.httpx_patch import enable_proxy_keyword_compat
enable_proxy_keyword_compat()

from supabase import create_client
from dotenv import load_dotenv


def load_environment(use_production: bool = False) -> tuple[str, str]:
    """
    Load environment variables for database connection.
    
    Args:
        use_production: If True, load production credentials. If False, load staging.
        
    Returns:
        Tuple of (supabase_url, supabase_service_role_key)
        
    Raises:
        SystemExit: If required credentials are missing
    """
    if use_production:
        # Try production-specific env file first
        prod_env = project_root / '.env.production'
        if prod_env.exists():
            load_dotenv(prod_env, override=True)
            print("📋 Loaded .env.production")
        else:
            # Fall back to environment variables (for production server)
            load_dotenv(project_root / '.env', override=False)
            print("📋 Using production environment variables")
    else:
        # Default: staging/local
        load_dotenv(project_root / '.env')
        print("📋 Loaded .env (staging/local)")
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ ERROR: Missing Supabase credentials")
        print(f"   SUPABASE_URL: {'✅' if supabase_url else '❌'}")
        print(f"   SUPABASE_SERVICE_ROLE_KEY: {'✅' if supabase_key else '❌'}")
        if use_production:
            print("\n   For production, ensure:")
            print("   1. .env.production file exists with production credentials, OR")
            print("   2. Environment variables are set (if running on production server)")
        else:
            print("\n   For staging, ensure .env file exists with staging credentials")
        sys.exit(1)
    
    return supabase_url, supabase_key


def initialize_supabase(use_production: bool = False):
    """Initialize Supabase client with appropriate credentials."""
    supabase_url, supabase_key = load_environment(use_production)
    return create_client(supabase_url, supabase_key)


def get_user_info(supabase, user_id: str) -> Optional[Dict[str, Any]]:
    """Get user information from database."""
    try:
        result = supabase.table('users').select('id, email, timezone, is_active').eq('id', user_id).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        print(f"❌ Error fetching user info: {e}")
        return None


def check_limitless_key(supabase, user_id: str) -> Dict[str, Any]:
    """Check if user has an active Limitless API key."""
    try:
        result = supabase.table('limitless_keys').select('id, is_active, created_at').eq('user_id', user_id).execute()
        if result.data:
            active_keys = [k for k in result.data if k.get('is_active', False)]
            return {
                'has_key': True,
                'is_active': len(active_keys) > 0,
                'total_keys': len(result.data),
                'active_keys': len(active_keys)
            }
        return {'has_key': False, 'is_active': False, 'total_keys': 0, 'active_keys': 0}
    except Exception as e:
        print(f"⚠️  Error checking Limitless key: {e}")
        return {'has_key': False, 'is_active': False, 'error': str(e)}


def get_audio_segments(supabase, user_id: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get audio segments for user, optionally filtered by date.
    
    TIMEZONE HANDLING:
    - audio_segments.date field is already stored in user's timezone (calendar date)
    - No timezone conversion needed - date field is already correct
    - Direct date comparison works because date is stored as user's local calendar date
    
    Args:
        supabase: Supabase client
        user_id: User UUID
        date: Optional date in YYYY-MM-DD format (matches audio_segments.date field)
    
    Returns:
        List of audio segment dictionaries
    """
    try:
        query = supabase.table('audio_segments').select('*').eq('user_id', user_id).order('date')
        
        if date:
            # Direct date comparison works - audio_segments.date is already in user's timezone
            query = query.eq('date', date)
        
        result = query.execute()
        return result.data or []
    except Exception as e:
        print(f"❌ Error fetching audio segments: {e}")
        return []


def get_processing_logs(supabase, user_id: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get processing logs for user, optionally filtered by date.
    
    TIMEZONE HANDLING:
    - processing_logs.date field is already stored in user's timezone (calendar date)
    - No timezone conversion needed - date field is already correct
    - Direct date comparison works because date is stored as user's local calendar date
    
    Args:
        supabase: Supabase client
        user_id: User UUID
        date: Optional date in YYYY-MM-DD format (matches processing_logs.date field)
    
    Returns:
        List of processing log dictionaries
    """
    try:
        query = supabase.table('processing_logs').select('*').eq('user_id', user_id).order('date', desc=True)
        
        if date:
            # Direct date comparison works - processing_logs.date is already in user's timezone
            query = query.eq('date', date)
        
        result = query.execute()
        return result.data or []
    except Exception as e:
        print(f"❌ Error fetching processing logs: {e}")
        return []


def get_laughter_detections(supabase, user_id: str, date: Optional[str] = None, user_timezone: str = 'UTC') -> List[Dict[str, Any]]:
    """
    Get laughter detections for user, optionally filtered by date.
    
    TIMEZONE HANDLING:
    - If date is provided, converts user timezone date to UTC range for database query
    - Matches the approach in src/api/data_routes.py get_laughter_detections()
    - This ensures midnight-to-midnight in user's timezone, not UTC
    
    PAGINATION:
    - Uses same pagination pattern as src/api/data_routes.py get_daily_summary()
    - Supabase limits to 1000 records by default, so we paginate to get all records
    
    Args:
        supabase: Supabase client
        user_id: User UUID
        date: Optional date in YYYY-MM-DD format (interpreted in user_timezone)
        user_timezone: User's timezone (IANA string, e.g., 'America/Los_Angeles')
    
    Returns:
        List of detection dictionaries
    """
    try:
        # If date is specified, calculate UTC range for that date in user's timezone
        # This matches the API's approach: convert user timezone date to UTC range
        # Example: Nov 3 PST (UTC-8) = Nov 3 00:00 PST to Nov 4 00:00 PST = Nov 3 08:00 UTC to Nov 4 08:00 UTC
        if date:
            user_tz = pytz.timezone(user_timezone)
            # Parse date as midnight in user's timezone
            start_of_day_local = user_tz.localize(datetime.strptime(date, "%Y-%m-%d"))
            end_of_day_local = start_of_day_local + timedelta(days=1)
            # Convert to UTC for database query (all timestamps stored in UTC)
            start_of_day_utc = start_of_day_local.astimezone(pytz.UTC)
            end_of_day_utc = end_of_day_local.astimezone(pytz.UTC)
        else:
            start_of_day_utc = None
            end_of_day_utc = None
        
        # Fetch all detections with pagination (Supabase limits to 1000 by default)
        # REUSES PATTERN: Same pagination logic as src/api/data_routes.py get_daily_summary()
        offset = 0
        page_size = 1000
        all_detections = []
        
        while True:
            query = (
                supabase.table('laughter_detections')
                .select('id, timestamp, audio_segment_id')
                .eq('user_id', user_id)
                .order('timestamp')
            )
            
            # Add UTC range filter if date specified (matches API approach)
            if date:
                query = query.gte('timestamp', start_of_day_utc.isoformat()).lt('timestamp', end_of_day_utc.isoformat())
            
            result = query.range(offset, offset + page_size - 1).execute()
            
            if not result.data:
                break
            
            all_detections.extend(result.data)
            
            if len(result.data) < page_size:
                break
            
            offset += page_size
        
        return all_detections
    except Exception as e:
        print(f"❌ Error fetching laughter detections: {e}")
        return []


def calculate_segment_duration(segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate total duration from audio segments.
    
    DATA SOURCE: audio_segments table
    - Reads start_time and end_time fields (UTC timestamps)
    - Calculates duration as (end_time - start_time) for each segment
    - Sums all segment durations to get total recording time
    - NOT stored in database - computed on-the-fly
    
    Returns:
        Dictionary with total_seconds, total_minutes, total_hours, and processed/unprocessed breakdown
    """
    total_seconds = 0
    processed_seconds = 0
    unprocessed_seconds = 0
    
    for seg in segments:
        try:
            start_time = datetime.fromisoformat(seg['start_time'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(seg['end_time'].replace('Z', '+00:00'))
            duration = (end_time - start_time).total_seconds()
            total_seconds += duration
            
            if seg.get('processed', False):
                processed_seconds += duration
            else:
                unprocessed_seconds += duration
        except Exception as e:
            print(f"⚠️  Error calculating duration for segment {seg.get('id')}: {e}")
    
    return {
        'total_seconds': total_seconds,
        'total_minutes': total_seconds / 60,
        'total_hours': total_seconds / 3600,
        'processed_seconds': processed_seconds,
        'processed_minutes': processed_seconds / 60,
        'unprocessed_seconds': unprocessed_seconds,
        'unprocessed_minutes': unprocessed_seconds / 60
    }


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def analyze_api_calls(api_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze Limitless API calls from processing logs.
    
    Categorizes API calls by HTTP status code:
    - 200: Success - audio data returned (counted in 'audio_files_downloaded')
    - 404: No data - no audio available for time window (normal, not an error)
    - 5xx: Server errors - API or gateway issues
    
    Returns:
        Dictionary with total_calls, successful (200), failed (404/5xx), and status breakdown
    """
    if not api_calls:
        return {'total_calls': 0, 'successful': 0, 'failed': 0, 'statuses': {}}
    
    statuses = defaultdict(int)
    successful = 0  # HTTP 200 responses (audio data returned)
    failed = 0  # HTTP 404 (no data) or 5xx (errors)
    
    for call in api_calls:
        status = call.get('status_code', 'unknown')
        statuses[status] += 1
        if 200 <= status < 300:
            successful += 1  # 200 = audio data successfully downloaded
        else:
            failed += 1  # 404 = no audio (normal), 5xx = errors
    
    return {
        'total_calls': len(api_calls),  # All HTTP requests to Limitless API
        'successful': successful,  # 200 responses (audio files)
        'failed': failed,  # 404 (no data) + 5xx (errors)
        'statuses': dict(statuses)  # Breakdown by HTTP status code
    }


def print_user_summary(supabase, user_id: str, date: Optional[str] = None, is_production: bool = False):
    """Print comprehensive user processing status."""
    env_label = "PRODUCTION" if is_production else "STAGING"
    print(f"\n{'='*80}")
    print(f"USER PROCESSING STATUS DIAGNOSTIC [{env_label}]")
    print(f"{'='*80}")
    print(f"User ID: {user_id}")
    if date:
        print(f"Date: {date}")
    else:
        print(f"Date: ALL DATES")
    print(f"{'='*80}\n")
    
    # Get user info
    user_info = get_user_info(supabase, user_id)
    if not user_info:
        print(f"❌ User not found: {user_id}")
        return
    
    print(f"👤 USER INFORMATION")
    print(f"   Email: {user_info.get('email', 'N/A')}")
    print(f"   Timezone: {user_info.get('timezone', 'UTC')}")
    print(f"   Active: {user_info.get('is_active', False)}")
    
    # Check Limitless key
    key_info = check_limitless_key(supabase, user_id)
    print(f"\n🔑 LIMITLESS API KEY")
    print(f"   Has Key: {key_info.get('has_key', False)}")
    print(f"   Active: {key_info.get('is_active', False)}")
    print(f"   Total Keys: {key_info.get('total_keys', 0)}")
    print(f"   Active Keys: {key_info.get('active_keys', 0)}")
    
    # Get audio segments
    # DATA SOURCE: audio_segments table
    # - Contains all audio segments downloaded from Limitless API
    # - Each row represents one audio file (OGG) with start_time and end_time
    # - Segment count and duration are calculated from this table, NOT from processing_logs
    segments = get_audio_segments(supabase, user_id, date)
    print(f"\n📁 AUDIO SEGMENTS (from audio_segments table)")
    print(f"   Total Segments: {len(segments)}")  # Count of rows in audio_segments table
    
    if segments:
        processed = sum(1 for s in segments if s.get('processed', False))
        unprocessed = len(segments) - processed
        print(f"   Processed: {processed}")
        print(f"   Unprocessed: {unprocessed}")
        
        # Calculate duration from audio_segments table
        # DURATION CALCULATION: Sum of (end_time - start_time) for all segments
        # - Calculated from start_time and end_time fields in audio_segments table
        # - NOT stored in database - computed on-the-fly from segment timestamps
        # - Shows total Limitless recording time (hours and minutes)
        duration_info = calculate_segment_duration(segments)
        print(f"\n   📊 RECORDING DURATION (calculated from audio_segments.start_time/end_time):")
        print(f"      Total: {format_duration(duration_info['total_seconds'])} ({duration_info['total_hours']:.2f} hours)")
        print(f"      Processed: {format_duration(duration_info['processed_seconds'])}")
        print(f"      Unprocessed: {format_duration(duration_info['unprocessed_seconds'])}")
        
        # Group by date
        segments_by_date = defaultdict(list)
        for seg in segments:
            seg_date = seg.get('date')
            if isinstance(seg_date, str):
                segments_by_date[seg_date].append(seg)
            else:
                # Handle datetime objects
                if hasattr(seg_date, 'strftime'):
                    segments_by_date[seg_date.strftime('%Y-%m-%d')].append(seg)
        
        if not date:
            print(f"\n   📅 SEGMENTS BY DATE (from audio_segments.date field):")
            for seg_date in sorted(segments_by_date.keys()):
                date_segments = segments_by_date[seg_date]
                date_processed = sum(1 for s in date_segments if s.get('processed', False))
                date_duration = calculate_segment_duration(date_segments)
                # Segment count and duration per day from audio_segments table
                print(f"      {seg_date}: {len(date_segments)} segments ({date_processed} processed, {format_duration(date_duration['total_seconds'])})")
    else:
        print(f"   ⚠️  No audio segments found")
    
    # Get processing logs
    logs = get_processing_logs(supabase, user_id, date)
    print(f"\n📋 PROCESSING LOGS (processing_logs table)")
    print(f"   Total Log Entries: {len(logs)}")
    
    if logs:
        for log in logs:
            log_date = log.get('date')
            if isinstance(log_date, str):
                date_str = log_date
            else:
                date_str = log_date.strftime('%Y-%m-%d') if hasattr(log_date, 'strftime') else str(log_date)
            
            print(f"\n   📅 DATE: {date_str}")
            print(f"      Status: {log.get('status', 'N/A')}")  # 'completed', 'failed', 'processing', 'pending'
            print(f"      Message: {log.get('message', 'N/A')}")  # Human-readable status message
            print(f"      Trigger: {log.get('trigger_type', 'N/A')}")  # 'manual', 'scheduled', or 'cron'
            print(f"      Duration: {log.get('processing_duration_seconds', 0)}s")  # Total processing time
            
            # LIMITLESS API METRICS (from Limitless API responses)
            # Audio Files Downloaded: Count of successful 200 responses from Limitless API
            # - Only counts HTTP 200 responses that returned actual audio data (OGG files)
            # - 404 responses are NOT counted (no audio available for that time window - this is normal)
            # - 5xx errors are NOT counted (API/server errors)
            # - This represents actual audio segments downloaded and available for processing
            audio_downloaded = log.get('audio_files_downloaded', 0)
            print(f"      Audio Files Downloaded: {audio_downloaded}")  # Only 200 responses with audio data
            
            # YAMNET DETECTION METRICS (from YAMNet audio processing)
            # Laughter Events Found: Total laughter detections from YAMNet before duplicate filtering
            # - Counts ALL laughter events detected by YAMNet in the downloaded audio files
            # - This is BEFORE duplicate filtering is applied
            # - Each detection represents a potential laughter event that needs to be checked for duplicates
            laughter_found = log.get('laughter_events_found', 0)
            print(f"      Laughter Events Found: {laughter_found}")  # YAMNet detections (before duplicate check)
            
            # DUPLICATE PREVENTION METRICS (from duplicate detection logic)
            # Duplicates Skipped: Laughter events filtered out as duplicates
            # - Prevents storing the same laughter event multiple times
            # - Includes: time-window duplicates, clip-path duplicates, missing-file skips
            # - Final stored count = Laughter Events Found - Duplicates Skipped
            duplicates_skipped = log.get('duplicates_skipped', 0)
            print(f"      Duplicates Skipped: {duplicates_skipped}")  # Events filtered as duplicates
            if laughter_found > 0:
                final_stored = laughter_found - duplicates_skipped
                print(f"      → Final Stored Detections: {final_stored}")  # What actually gets saved to DB
            
            print(f"      Last Processed: {log.get('last_processed', 'N/A')}")  # UTC timestamp of last processing
            
            # API CALL ANALYSIS (detailed breakdown of all Limitless API HTTP requests)
            # API Calls: Total HTTP requests made to Limitless API
            # - Includes ALL requests: 200 (success), 404 (no data), 5xx (errors)
            # - 404 responses are NORMAL - they mean no audio for that time window
            # - Why API Calls ≠ Audio Files Downloaded:
            #   * 200 responses → counted in both API Calls AND Audio Files Downloaded
            #   * 404 responses → counted in API Calls but NOT in Audio Files Downloaded
            #   * 5xx errors → counted in API Calls but NOT in Audio Files Downloaded
            # Example: 32 API calls (21×200 + 11×404) = 21 Audio Files Downloaded
            api_calls = log.get('api_calls', [])
            if api_calls:
                api_analysis = analyze_api_calls(api_calls)
                print(f"\n      🌐 LIMITLESS API CALL BREAKDOWN:")
                print(f"         Total API Calls: {api_analysis['total_calls']}")  # All HTTP requests
                print(f"         Successful (200): {api_analysis['successful']}")  # Returned audio data
                print(f"         Failed (404/5xx): {api_analysis['failed']}")  # No data or errors
                if api_analysis['statuses']:
                    print(f"         Status Codes: {api_analysis['statuses']}")  # Breakdown by HTTP status
                # Explain the relationship
                if api_analysis['total_calls'] != audio_downloaded:
                    diff = api_analysis['total_calls'] - audio_downloaded
                    print(f"         → {diff} calls returned 404 (no audio) or errors - this is normal")
                else:
                    print(f"         → All API calls returned audio data (100% success rate)")
            
            # Check for errors
            error_details = log.get('error_details', {})
            if error_details:
                print(f"      ⚠️  ERRORS:")
                for key, value in error_details.items():
                    print(f"         {key}: {value}")
    else:
        print(f"   ⚠️  No processing logs found")
    
    # Get laughter detections
    # TIMEZONE HANDLING: Uses UTC range query (matches API approach in data_routes.py)
    # - If date specified: Converts user timezone date to UTC range for efficient database query
    # - This ensures midnight-to-midnight in user's timezone, not UTC
    # - Example: Nov 3 PST = Nov 3 08:00 UTC to Nov 4 08:00 UTC
    user_tz_str = user_info.get('timezone', 'UTC')
    detections = get_laughter_detections(supabase, user_id, date, user_tz_str)
    
    print(f"\n🎭 LAUGHTER DETECTIONS (laughter_detections table)")
    print(f"   Total Detections: {len(detections)}")
    
    if detections and not date:
        # Group by date
        user_tz_str = user_info.get('timezone', 'UTC')
        user_tz = pytz.timezone(user_tz_str)
        detections_by_date = defaultdict(int)
        
        for det in detections:
            timestamp_str = det['timestamp']
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            timestamp_utc = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            timestamp_local = timestamp_utc.astimezone(user_tz)
            date_key = timestamp_local.strftime('%Y-%m-%d')
            detections_by_date[date_key] += 1
        
        if detections_by_date:
            print(f"\n   📅 DETECTIONS BY DATE:")
            for det_date in sorted(detections_by_date.keys()):
                print(f"      {det_date}: {detections_by_date[det_date]} detections")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    if segments:
        duration_info = calculate_segment_duration(segments)
        print(f"✅ Total Limitless Recordings: {format_duration(duration_info['total_seconds'])}")
    else:
        print(f"❌ No Limitless recordings found")
    
    if logs:
        total_downloaded = sum(log.get('audio_files_downloaded', 0) for log in logs)
        total_found = sum(log.get('laughter_events_found', 0) for log in logs)
        print(f"✅ Audio Files Downloaded (from API): {total_downloaded}")
        print(f"✅ Laughter Events Found: {total_found}")
        print(f"✅ Final Stored Detections: {len(detections)}")
    else:
        print(f"⚠️  No processing logs found - processing may not have run")
    
    print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Check user processing status',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # On PRODUCTION server (recommended):
  python3 check_user_processing_status.py 94fdf2fb-5ed9-4c15-a8b7-c0a3518b309
  
  # On PRODUCTION server, specific date:
  python3 check_user_processing_status.py 94fdf2fb-5ed9-4c15-a8b7-c0a3518b309 2024-12-02
  
  # On staging/local, connect to PRODUCTION (requires .env.production or env vars):
  python3 check_user_processing_status.py 94fdf2fb-5ed9-4c15-a8b7-c0a3518b309 --production
  
  # On staging/local, use staging database (default):
  python3 check_user_processing_status.py 94fdf2fb-5ed9-4c15-a8b7-c0a3518b309 --staging
        """
    )
    parser.add_argument('user_id', help='User UUID')
    parser.add_argument('date', nargs='?', help='Date in YYYY-MM-DD format (optional, defaults to all dates)')
    
    env_group = parser.add_mutually_exclusive_group()
    env_group.add_argument('--production', action='store_true', 
                          help='Use production database (requires .env.production or production env vars)')
    env_group.add_argument('--staging', action='store_true', 
                          help='Use staging database (default, uses .env)')
    
    args = parser.parse_args()
    
    # Validate date format if provided
    if args.date:
        try:
            datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print(f"❌ Invalid date format: {args.date}. Use YYYY-MM-DD format.")
            sys.exit(1)
    
    # Determine environment
    use_production = args.production
    if not args.staging and not args.production:
        # Default: staging if not specified
        use_production = False
    
    # Initialize Supabase with appropriate environment
    try:
        supabase = initialize_supabase(use_production)
    except SystemExit:
        sys.exit(1)
    
    # Print summary
    print_user_summary(supabase, args.user_id, args.date, use_production)


if __name__ == '__main__':
    main()

