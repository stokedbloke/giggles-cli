#!/usr/bin/env python3
"""
Manually reprocess audio data for a date range to test audio processing pipeline.

This script:
1. Clears database records for the date range (audio_segments, laughter_detections, processing_logs)
2. Clears disk files (ogg and wav) for the date range
3. Redownloads from Limitless API for the date range
4. Reruns YAMNet processing
5. Updates UI automatically via database

Usage: 
    python manual_reprocess_yesterday.py 2024-10-29 2024-10-30
    python manual_reprocess_yesterday.py 2024-10-29 2024-10-30 --user-id USER_ID

Note: Dates should be in YYYY-MM-DD format. They will be interpreted in the user's timezone.
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import pytz
import logging

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def clear_database_records(user_id: str, start_time: datetime, end_time: datetime, supabase):
    """Clear database records for the date range."""
    logger.info("🗑️  Clearing database records...")
    
    # Delete laughter detections first (due to foreign key constraints)
    laughter_result = supabase.table("laughter_detections").select("id").eq("user_id", user_id).gte("timestamp", start_time.isoformat()).lte("timestamp", end_time.isoformat()).execute()
    laughter_count = len(laughter_result.data) if laughter_result.data else 0
    
    if laughter_count > 0:
        # Get all laughter detection IDs to delete
        laughter_ids = [row["id"] for row in laughter_result.data]
        for laughter_id in laughter_ids:
            supabase.table("laughter_detections").delete().eq("id", laughter_id).execute()
        logger.info(f"  ✅ Deleted {laughter_count} laughter detections")
    else:
        logger.info("  ℹ️  No laughter detections to delete")
    
    # Delete audio segments
    segments_result = supabase.table("audio_segments").select("id, file_path").eq("user_id", user_id).gte("start_time", start_time.isoformat()).lte("end_time", end_time.isoformat()).execute()
    segments_count = len(segments_result.data) if segments_result.data else 0
    
    if segments_count > 0:
        segment_ids = [row["id"] for row in segments_result.data]
        for segment_id in segment_ids:
            supabase.table("audio_segments").delete().eq("id", segment_id).execute()
        logger.info(f"  ✅ Deleted {segments_count} audio segments")
    else:
        logger.info("  ℹ️  No audio segments to delete")
    
    # Delete processing logs for the date range
    # Processing logs use date field, so we need to check dates in the range
    start_date = start_time.date()
    end_date = end_time.date()
    current_date = start_date
    logs_deleted = 0
    
    while current_date <= end_date:
        logs_result = supabase.table("processing_logs").select("id").eq("user_id", user_id).eq("date", current_date.isoformat()).execute()
        if logs_result.data:
            for log_row in logs_result.data:
                supabase.table("processing_logs").delete().eq("id", log_row["id"]).execute()
                logs_deleted += 1
        current_date += timedelta(days=1)
    
    if logs_deleted > 0:
        logger.info(f"  ✅ Deleted {logs_deleted} processing logs")
    else:
        logger.info("  ℹ️  No processing logs to delete")
    
    logger.info("✅ Database cleanup complete\n")


async def clear_disk_files(user_id: str, start_time: datetime, end_time: datetime):
    """Clear disk files (ogg and wav) for the date range."""
    logger.info("🗑️  Clearing disk files...")
    
    from src.config.settings import settings
    
    # Get base upload directory
    upload_dir = Path(settings.upload_dir)
    audio_dir = upload_dir / "audio" / user_id
    clips_dir = upload_dir / "clips"
    
    files_deleted = {"ogg": 0, "wav": 0}
    
    # Delete OGG files from audio directory
    if audio_dir.exists():
        # Get all OGG files in the user's directory
        ogg_files = list(audio_dir.glob("*.ogg"))
        for ogg_file in ogg_files:
            try:
                # Check if file modification time is within the date range
                file_mtime = datetime.fromtimestamp(ogg_file.stat().st_mtime)
                # Use a timezone-aware comparison if the file time is naive
                if file_mtime.tzinfo is None:
                    file_mtime = pytz.UTC.localize(file_mtime)
                
                # Compare in UTC for consistency
                start_utc = start_time.astimezone(pytz.UTC)
                end_utc = end_time.astimezone(pytz.UTC)
                file_utc = file_mtime.astimezone(pytz.UTC)
                
                if start_utc <= file_utc <= end_utc:
                    ogg_file.unlink()
                    files_deleted["ogg"] += 1
            except Exception as e:
                logger.warning(f"  ⚠️  Failed to delete {ogg_file.name}: {str(e)}")
        
        if files_deleted["ogg"] > 0:
            logger.info(f"  ✅ Deleted {files_deleted['ogg']} OGG files")
        else:
            logger.info("  ℹ️  No OGG files to delete")
    else:
        logger.info("  ℹ️  Audio directory does not exist")
    
    # Delete WAV clip files
    # Since we deleted laughter_detections, we should delete all clips that might be in the range
    # We'll delete clips that were created during the date range based on filename patterns
    if clips_dir.exists():
        wav_files = list(clips_dir.glob("*.wav"))
        for wav_file in wav_files:
            try:
                # Check file modification time
                file_mtime = datetime.fromtimestamp(wav_file.stat().st_mtime)
                if file_mtime.tzinfo is None:
                    file_mtime = pytz.UTC.localize(file_mtime)
                
                start_utc = start_time.astimezone(pytz.UTC)
                end_utc = end_time.astimezone(pytz.UTC)
                file_utc = file_mtime.astimezone(pytz.UTC)
                
                if start_utc <= file_utc <= end_utc:
                    wav_file.unlink()
                    files_deleted["wav"] += 1
            except Exception as e:
                logger.warning(f"  ⚠️  Failed to delete {wav_file.name}: {str(e)}")
        
        if files_deleted["wav"] > 0:
            logger.info(f"  ✅ Deleted {files_deleted['wav']} WAV clip files")
        else:
            logger.info("  ℹ️  No WAV clip files to delete")
    else:
        logger.info("  ℹ️  Clips directory does not exist")
    
    logger.info("✅ Disk cleanup complete\n")


async def reprocess_date_range(start_date_str: str, end_date_str: str, user_id: str = None):
    """Reprocess audio data for a date range."""
    
    # Get user ID
    if not user_id:
        user_id = os.getenv('TEST_USER_ID')
    
    if not user_id:
        # Try to get the most recent user as a fallback
        supabase = create_client(
            os.getenv('SUPABASE_URL'), 
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
        users = supabase.table('users').select('id, email').order('created_at', desc=True).limit(1).execute()
        if users.data:
            user_id = users.data[0]['id']
            logger.info(f"Using most recent user: {users.data[0]['email']} ({user_id})")
        else:
            logger.error("ERROR: No users found. Please set TEST_USER_ID in .env")
            sys.exit(1)
    
    # Get user's timezone
    supabase = create_client(
        os.getenv('SUPABASE_URL'), 
        os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    )
    user_result = supabase.table('users').select('timezone').eq('id', user_id).execute()
    timezone = user_result.data[0].get('timezone', 'UTC') if user_result.data else 'UTC'
    logger.info(f"User timezone: {timezone}")
    
    # Parse dates and convert to datetime in user's timezone
    user_tz = pytz.timezone(timezone)
    
    try:
        # Parse dates (assumed to be in user's timezone)
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        # Make them timezone-aware
        start_date = user_tz.localize(start_date)
        end_date = user_tz.localize(end_date)
        
        # Set to start and end of day
        start_time = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        logger.error("Dates must be in YYYY-MM-DD format")
        sys.exit(1)
    
    logger.info(f"\n📅 Reprocessing date range:")
    logger.info(f"   From: {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info(f"   To: {end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info(f"   User ID: {user_id[:8]}...\n")
    
    # Step 1: Clear database records
    await clear_database_records(user_id, start_time, end_time, supabase)
    
    # Step 2: Clear disk files
    await clear_disk_files(user_id, start_time, end_time)
    
    # Step 3: Get API key
    keys_result = supabase.table('limitless_keys').select('encrypted_api_key').eq('user_id', user_id).eq('is_active', True).limit(1).execute()
    if not keys_result.data:
        logger.error("ERROR: No active Limitless API key found for user")
        sys.exit(1)
    
    encrypted_key = keys_result.data[0]['encrypted_api_key']
    from src.auth.encryption import encryption_service as encryption_service_module
    api_key = encryption_service_module.decrypt(encrypted_key, associated_data=user_id.encode('utf-8'))
    logger.info("✅ API key decrypted\n")
    
    # Step 4: Reprocess using scheduler
    from src.services.scheduler import scheduler
    from src.services.enhanced_logger import get_enhanced_logger
    
    # CRITICAL FIX: Create separate logs for each day in the date range
    # When reprocessing 11/24-11/25, create separate processing_logs entries for each day
    # This ensures logs are correctly attributed to the right date
    scheduler._trigger_type = "manual"
    
    logger.info("🔄 Starting reprocessing...")
    logger.info("=" * 60)
    
    try:
        # Convert to UTC for processing (scheduler expects UTC)
        start_utc = start_time.astimezone(pytz.UTC)
        end_utc = end_time.astimezone(pytz.UTC)
        
        # Track current date for per-day logging
        current_date = None
        enhanced_logger = None
        
        # Process in 2-hour chunks to avoid API timeouts
        current_time = start_utc
        chunk_count = 0
        total_segments = 0
        
        while current_time < end_utc:
            chunk_end = min(current_time + timedelta(hours=2), end_utc)
            
            # Check if we've crossed into a new day - create new logger if needed
            chunk_date = current_time.date()
            if current_date != chunk_date:
                # Save previous day's log if it exists
                if enhanced_logger and current_date:
                    await enhanced_logger.save_to_database("completed", 
                        f"Manual reprocessing completed for {current_date.isoformat()}")
                    enhanced_logger.log_processing_summary()
                
                # Create new logger for this day
                current_date = chunk_date
                enhanced_logger = get_enhanced_logger(user_id, "manual", process_date=current_date)
                logger.info(f"\n📅 Processing date: {current_date.isoformat()}")
            
            logger.info(f"\n📦 Processing chunk {chunk_count + 1}: {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')} to {chunk_end.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            # Process this chunk
            processed = await scheduler._process_date_range(user_id, api_key, current_time, chunk_end)
            total_segments += processed
            
            logger.info(f"  ✅ Processed {processed} segment(s) in this chunk")
            
            current_time = chunk_end
            chunk_count += 1
        
        # Save final day's log
        if enhanced_logger and current_date:
            await enhanced_logger.save_to_database("completed", 
                f"Manual reprocessing completed for {current_date.isoformat()}")
            enhanced_logger.log_processing_summary()
        
        logger.info("\n" + "=" * 60)
        logger.info(f"✅ Reprocessing complete!")
        logger.info(f"   Processed {chunk_count} chunk(s) across {len(set([d for d in [start_utc.date(), end_utc.date()]]))} day(s)")
        logger.info(f"   Total segments processed: {total_segments}")
        logger.info(f"   UI will update automatically when queries refresh\n")
        
    except Exception as e:
        logger.error(f"\n❌ Error during reprocessing: {str(e)}")
        # Save error log for current day if logger exists
        if enhanced_logger and current_date:
            enhanced_logger.add_error("reprocessing_failed", str(e))
            await enhanced_logger.save_to_database("failed", f"Manual reprocessing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Reprocess audio data for a date range',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reprocess October 29-30, 2024 (in user's timezone)
  python manual_reprocess_yesterday.py 2024-10-29 2024-10-30
  
  # Reprocess for specific user
  python manual_reprocess_yesterday.py 2024-10-29 2024-10-30 --user-id USER_ID
        """
    )
    parser.add_argument('start_date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('end_date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--user-id', type=str, help='User ID (optional, defaults to TEST_USER_ID or most recent user)')
    
    args = parser.parse_args()
    
    asyncio.run(reprocess_date_range(args.start_date, args.end_date, args.user_id))


if __name__ == "__main__":
    main()
