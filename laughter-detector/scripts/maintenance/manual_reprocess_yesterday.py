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
from supabase import Client
import pytz
import logging
from typing import Optional

# Add project root to path (where src/ directory is located)
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# CRITICAL: Enable httpx patch BEFORE importing supabase
# This fixes: TypeError: Client.__init__() got an unexpected keyword argument 'proxy'
# The httpx_patch module patches httpx.Client to accept the legacy 'proxy' argument
# that Supabase's Python client still uses (httpx >=0.25 removed 'proxy' in favor of 'proxies')
from src.utils.httpx_patch import enable_proxy_keyword_compat
enable_proxy_keyword_compat()

from src.services.limitless_keys import (
    LimitlessKeyError,
    fetch_decrypted_limitless_key,
)
from src.services.supabase_client import get_service_role_client

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

try:
    SERVICE_SUPABASE: Client = get_service_role_client()
except Exception as exc:  # pragma: no cover - script startup guard
    logger.error(f"Failed to create Supabase service client: {exc}")
    sys.exit(1)


async def clear_database_records(
    user_id: str,
    start_time: datetime,
    end_time: datetime,
    supabase: Optional[Client] = None,
):
    """
    Clear database records for the date range.

    NOTE: This should be called AFTER clear_disk_files() to ensure file paths
    are retrieved from database before records are deleted.
    """
    supabase = supabase or SERVICE_SUPABASE
    logger.info("🗑️  Clearing database records...")
    print("🗑️  Clearing database records...")

    # Delete laughter detections first (due to foreign key constraints)
    # FIX: Use .lt() instead of .lte() for end_time to exclude records exactly at boundary
    # end_time is the START of the next day, so we want [start_time, end_time) (exclusive end)
    laughter_result = (
        supabase.table("laughter_detections")
        .select("id")
        .eq("user_id", user_id)
        .gte("timestamp", start_time.isoformat())
        .lt("timestamp", end_time.isoformat())
        .execute()
    )
    laughter_count = len(laughter_result.data) if laughter_result.data else 0

    if laughter_count > 0:
        # Get all laughter detection IDs to delete
        laughter_ids = [row["id"] for row in laughter_result.data]
        for laughter_id in laughter_ids:
            supabase.table("laughter_detections").delete().eq(
                "id", laughter_id
            ).execute()
        logger.info(f"  ✅ Deleted {laughter_count} laughter detections")
        print(f"  ✅ Deleted {laughter_count} laughter detections")
    else:
        logger.info("  ℹ️  No laughter detections to delete")
        print("  ℹ️  No laughter detections to delete")

    # Delete audio segments
    # FIX: Use .lt() instead of .lte() for end_time to avoid edge cases
    # Also check both start_time and end_time overlap with cleanup range
    # A segment should be deleted if:
    # - Its start_time is within the cleanup range, OR
    # - Its end_time is within the cleanup range, OR
    # - It spans the entire cleanup range
    # Using: (start_time >= cleanup_start AND start_time < cleanup_end) OR
    #        (end_time > cleanup_start AND end_time <= cleanup_end) OR
    #        (start_time < cleanup_start AND end_time > cleanup_end)
    # Simplified to: segments where (start_time < cleanup_end) AND (end_time > cleanup_start)
    segments_result = (
        supabase.table("audio_segments")
        .select("id, file_path, start_time, end_time")
        .eq("user_id", user_id)
        .lt("start_time", end_time.isoformat())
        .gt("end_time", start_time.isoformat())
        .execute()
    )
    segments_count = len(segments_result.data) if segments_result.data else 0

    if segments_count > 0:
        segment_ids = [row["id"] for row in segments_result.data]
        for segment_id in segment_ids:
            supabase.table("audio_segments").delete().eq("id", segment_id).execute()
        logger.info(f"  ✅ Deleted {segments_count} audio segments")
        print(f"  ✅ Deleted {segments_count} audio segments")
    else:
        logger.info("  ℹ️  No audio segments to delete")
        print("  ℹ️  No audio segments to delete")

    # Delete processing logs for the date range
    # Processing logs use date field, so we need to check dates in the range
    start_date = start_time.date()
    end_date = end_time.date()
    current_date = start_date
    logs_deleted = 0

    while current_date <= end_date:
        logs_result = (
            supabase.table("processing_logs")
            .select("id")
            .eq("user_id", user_id)
            .eq("date", current_date.isoformat())
            .execute()
        )
        if logs_result.data:
            for log_row in logs_result.data:
                supabase.table("processing_logs").delete().eq(
                    "id", log_row["id"]
                ).execute()
                logs_deleted += 1
        current_date += timedelta(days=1)

    if logs_deleted > 0:
        logger.info(f"  ✅ Deleted {logs_deleted} processing logs")
    else:
        logger.info("  ℹ️  No processing logs to delete")

    logger.info("✅ Database cleanup complete\n")
    print("✅ Database cleanup complete\n")


async def clear_disk_files(
    user_id: str, start_time: datetime, end_time: datetime, supabase=None
):
    """
    Clear disk files (ogg and wav) for the date range.

    FIXED: Now uses database paths instead of scanning directories.
    Handles user-specific folder structure: clips/{user_id}/ and audio/{user_id}/

    Args:
        user_id: User ID to delete files for
        start_time: Start of date range (timezone-aware datetime)
        end_time: End of date range (timezone-aware datetime)
        supabase: Supabase client (optional, will create if not provided)
    """
    logger.info("🗑️  Clearing disk files...")
    print("🗑️  Clearing disk files...")

    import os  # Needed for os.path.exists, os.remove, os.path.basename

    # Create supabase client if not provided
    if supabase is None:
        supabase = SERVICE_SUPABASE

    files_deleted = {"ogg": 0, "wav": 0}

    # CRITICAL: Get file paths from database BEFORE deleting records
    # This ensures we know exactly which files to delete, even if they're in user-specific folders

    # 1. Get clip_paths from laughter_detections table
    # FIX: Use .lt() instead of .lte() for end_time to match clear_database_records()
    detections_result = (
        supabase.table("laughter_detections")
        .select("clip_path")
        .eq("user_id", user_id)
        .gte("timestamp", start_time.isoformat())
        .lt("timestamp", end_time.isoformat())
        .execute()
    )

    clip_paths = []
    if detections_result.data:
        clip_paths = [
            d["clip_path"] for d in detections_result.data if d.get("clip_path")
        ]
        logger.info(f"  📋 Found {len(clip_paths)} clip paths in database")

    # 2. Get file_paths from audio_segments table
    segments_result = (
        supabase.table("audio_segments")
        .select("file_path")
        .eq("user_id", user_id)
        .gte("start_time", start_time.isoformat())
        .lte("end_time", end_time.isoformat())
        .execute()
    )

    audio_paths = []
    if segments_result.data:
        audio_paths = [
            s["file_path"] for s in segments_result.data if s.get("file_path")
        ]
        logger.info(f"  📋 Found {len(audio_paths)} audio file paths in database")

    # 3. Delete WAV clip files using database paths
    # Resolve relative paths to absolute
    # CRITICAL FIX: Handle both relative and absolute paths correctly
    # - Absolute paths (VPS): Use as-is (e.g., /var/lib/giggles/uploads/clips/...)
    # - Relative paths (MacBook): Resolve from project root (e.g., ./uploads/clips/...)
    # Match scheduler.py path normalization: lstrip("./") then join with project root
    script_project_root = Path(__file__).resolve().parent.parent.parent
    for clip_path in clip_paths:
        if clip_path:
            # Resolve relative paths to absolute
            if not os.path.isabs(clip_path):
                # Relative path - resolve from project root
                # Database stores paths like: ./uploads/clips/{user_id}/filename.wav
                # Match scheduler.py normalization: lstrip("./") then join
                normalized_path = clip_path.lstrip("./")
                clip_path = os.path.join(str(script_project_root), normalized_path)

            if os.path.exists(clip_path):
                try:
                    os.remove(clip_path)
                    files_deleted["wav"] += 1
                    print(f"  🗑️  Deleted WAV clip: {os.path.basename(clip_path)}")
                except Exception as e:
                    logger.warning(
                        f"  ⚠️  Failed to delete clip {os.path.basename(clip_path)}: {str(e)}"
                    )
                    print(
                        f"  ⚠️  Failed to delete clip {os.path.basename(clip_path)}: {str(e)}"
                    )
            else:
                logger.debug(
                    f"  ℹ️  Clip file not found (may already be deleted): {clip_path}"
                )
                print(f"  ℹ️  Clip file not found: {clip_path}")

    if files_deleted["wav"] > 0:
        logger.info(f"  ✅ Deleted {files_deleted['wav']} WAV clip files")
        print(f"  ✅ Deleted {files_deleted['wav']} WAV clip files")
    else:
        logger.info("  ℹ️  No WAV clip files to delete")
        print("  ℹ️  No WAV clip files to delete")

    # 4. Delete OGG audio files using database paths
    # Resolve relative paths to absolute
    # Use same project_root as above (already calculated)
    # Note: audio_segments.file_path may be encrypted, but we handle plaintext paths here
    for audio_path in audio_paths:
        if audio_path:
            # Resolve relative paths to absolute
            if not os.path.isabs(audio_path):
                # Relative path - resolve from project root
                # Match scheduler.py normalization: lstrip("./") then join
                normalized_path = audio_path.lstrip("./")
                audio_path = os.path.join(str(script_project_root), normalized_path)

            if os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                    files_deleted["ogg"] += 1
                    print(f"  🗑️  Deleted OGG file: {os.path.basename(audio_path)}")
                except Exception as e:
                    logger.warning(
                        f"  ⚠️  Failed to delete audio {os.path.basename(audio_path)}: {str(e)}"
                    )
                    print(
                        f"  ⚠️  Failed to delete audio {os.path.basename(audio_path)}: {str(e)}"
                    )
            else:
                logger.debug(
                    f"  ℹ️  Audio file not found (may already be deleted): {audio_path}"
                )
                print(f"  ℹ️  Audio file not found: {audio_path}")

    if files_deleted["ogg"] > 0:
        logger.info(f"  ✅ Deleted {files_deleted['ogg']} OGG files")
        print(f"  ✅ Deleted {files_deleted['ogg']} OGG files")
    else:
        logger.info("  ℹ️  No OGG files to delete")
        print("  ℹ️  No OGG files to delete")

    logger.info("✅ Disk cleanup complete\n")
    print("✅ Disk cleanup complete\n")


async def reprocess_date_range(
    start_date_str: str, end_date_str: str, user_id: str = None
):
    """Reprocess audio data for a date range."""

    # Get user ID
    supabase = SERVICE_SUPABASE

    if not user_id:
        user_id = os.getenv("TEST_USER_ID")

    if not user_id:
        # Try to get the most recent user as a fallback
        users = (
            supabase.table("users")
            .select("id, email")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if users.data:
            user_id = users.data[0]["id"]
            logger.info(f"Using most recent user: {users.data[0]['email']} ({user_id})")
        else:
            logger.error("ERROR: No users found. Please set TEST_USER_ID in .env")
            sys.exit(1)

    # Get user's timezone
    user_result = supabase.table("users").select("timezone").eq("id", user_id).execute()
    timezone = user_result.data[0].get("timezone", "UTC") if user_result.data else "UTC"
    logger.info(f"User timezone: {timezone}")

    # Parse dates and convert to datetime in user's timezone
    user_tz = pytz.timezone(timezone)

    try:
        # Parse dates (assumed to be in user's timezone)
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

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

    # Step 1: Clear disk files FIRST (reads paths from database before deleting records)
    await clear_disk_files(user_id, start_time, end_time, supabase)

    # Step 2: Clear database records (after files are deleted)
    await clear_database_records(user_id, start_time, end_time, supabase)

    # Step 3: Get API key
    try:
        api_key = fetch_decrypted_limitless_key(user_id, supabase=supabase)
        logger.info("✅ API key decrypted\n")
    except LimitlessKeyError as exc:
        logger.error(f"ERROR: {exc}")
        sys.exit(1)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.error(f"ERROR: Failed to decrypt API key: {exc}")
        sys.exit(1)

    # Step 4: Reprocess using scheduler
    from src.services.scheduler import (
        scheduler,
        generate_time_chunks,
        DEFAULT_CHUNK_MINUTES,
    )
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

        chunk_count = 0
        total_segments = 0
        all_stored_clip_paths = set()  # Track clip paths created in this reprocessing session

        for chunk_count, (current_time, chunk_end) in enumerate(
            generate_time_chunks(
                start_utc,
                end_utc,
                chunk_minutes=DEFAULT_CHUNK_MINUTES,
            ),
            start=1,
        ):
            # Check if we've crossed into a new day - create new logger if needed
            chunk_date = current_time.date()
            if current_date != chunk_date:
                # Save previous day's log if it exists
                if enhanced_logger and current_date:
                    await enhanced_logger.save_to_database(
                        "completed",
                        f"Manual reprocessing completed for {current_date.isoformat()}",
                    )
                    enhanced_logger.log_processing_summary()

                # Create new logger for this day
                current_date = chunk_date
                enhanced_logger = get_enhanced_logger(
                    user_id, "manual", process_date=current_date
                )
                logger.info(f"\n📅 Processing date: {current_date.isoformat()}")

            logger.info(
                f"\n📦 Processing chunk {chunk_count}: {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')} to {chunk_end.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )

            # Process this chunk
            processed, chunk_clip_paths = await scheduler._process_date_range(
                user_id, api_key, current_time, chunk_end
            )
            total_segments += processed
            # Accumulate clip paths created in this reprocessing session
            # These will be excluded from orphan cleanup to prevent race condition
            all_stored_clip_paths.update(chunk_clip_paths)

            logger.info(f"  ✅ Processed {processed} segment(s) in this chunk")

        # Save final day's log
        if enhanced_logger and current_date:
            await enhanced_logger.save_to_database(
                "completed",
                f"Manual reprocessing completed for {current_date.isoformat()}",
            )
            enhanced_logger.log_processing_summary()

        logger.info("\n" + "=" * 60)
        logger.info(f"✅ Reprocessing complete!")
        logger.info(
            f"   Processed {chunk_count} chunk(s) across {len(set([d for d in [start_utc.date(), end_utc.date()]]))} day(s)"
        )
        logger.info(f"   Total segments processed: {total_segments}")
        logger.info(f"   UI will update automatically when queries refresh\n")

    except Exception as e:
        logger.error(f"\n❌ Error during reprocessing: {str(e)}")
        # Save error log for current day if logger exists
        if enhanced_logger and current_date:
            enhanced_logger.add_error("reprocessing_failed", str(e))
            await enhanced_logger.save_to_database(
                "failed", f"Manual reprocessing failed: {str(e)}"
            )
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        # ALWAYS run orphan cleanup, even if processing failed
        # This ensures no orphaned files remain from crashed/failed processing
        try:
            from datetime import timedelta
            now_utc = datetime.utcnow()
            start_window = now_utc - timedelta(days=2)
            # Exclude clip paths created during reprocessing to prevent race condition
            session_clip_paths = all_stored_clip_paths if 'all_stored_clip_paths' in locals() else set()
            logger.info(f"🧹 Running orphan cleanup (2-day window)")
            logger.info(f"🧹 Excluding {len(session_clip_paths)} clip paths from cleanup")
            await scheduler._cleanup_orphaned_files(user_id, start_window, now_utc, exclude_clip_paths=session_clip_paths)
            logger.info("🧹 Orphan cleanup completed")
        except Exception as cleanup_err:
            logger.warning(f"⚠️ Orphan cleanup failed (non-fatal): {str(cleanup_err)}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Reprocess audio data for a date range",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reprocess October 29-30, 2024 (in user's timezone)
  python manual_reprocess_yesterday.py 2024-10-29 2024-10-30
  
  # Reprocess for specific user
  python manual_reprocess_yesterday.py 2024-10-29 2024-10-30 --user-id USER_ID
        """,
    )
    parser.add_argument("start_date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("end_date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument(
        "--user-id",
        type=str,
        help="User ID (optional, defaults to TEST_USER_ID or most recent user)",
    )

    args = parser.parse_args()

    asyncio.run(reprocess_date_range(args.start_date, args.end_date, args.user_id))


if __name__ == "__main__":
    main()
