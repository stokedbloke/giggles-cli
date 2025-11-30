"""
Background processing scheduler for nightly audio processing.

This module handles scheduled tasks including nightly audio processing,
cleanup operations, and maintenance tasks.
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Optional, Iterator, Tuple
import pytz
from supabase import Client
from fastapi import HTTPException, status

from ..config.settings import settings
from ..services.limitless_api import limitless_api_service
from ..services.limitless_keys import (
    LimitlessKeyError,
    fetch_decrypted_limitless_key,
)
# Lazy import to avoid TensorFlow mutex crash on macOS startup
# yamnet_processor will be imported when actually needed
def _get_yamnet_processor():
    """Lazy import of yamnet_processor to avoid TensorFlow crash on startup."""
    from ..services.yamnet_processor import yamnet_processor
    return yamnet_processor
from ..services.supabase_client import get_service_role_client
from ..utils.path_utils import strip_leading_dot_slash


def _norm_iso(ts: str) -> str:
    """Normalize ISO timestamp microseconds to 6 digits."""
    if "." in ts:
        main, rest = ts.split(".", 1)
        us_part, tz_part = (
            (rest.split("+", 1) + [""])[:2] if "+" in rest else (rest, "")
        )
        us_part = us_part.rstrip("Z")
        us_part = (us_part + "000000")[:6]
        return f"{main}.{us_part}" + (f"+{tz_part}" if tz_part else "")
    return ts


DEFAULT_CHUNK_MINUTES = 30
VERBOSE_PROCESSING_LOGS = settings.verbose_processing_logs


def _verbose_log(message: str) -> None:
    """
    Print verbose-only processing logs when enabled.

    Args:
        message: Text to print.
    """
    if VERBOSE_PROCESSING_LOGS:
        print(message)


def _ensure_absolute_path(path: str) -> str:
    """
    Resolve a path to absolute, handling both relative and absolute paths.
    
    Args:
        path: Path that may be relative (e.g., ./uploads/clips/...) or absolute
        
    Returns:
        Absolute path
    """
    if not path:
        return path
    if os.path.isabs(path):
        return path
    # Relative path - resolve from project root
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    return os.path.normpath(
        os.path.join(project_root, strip_leading_dot_slash(path))
    )


def generate_time_chunks(
    start_time: datetime,
    end_time: datetime,
    *,
    chunk_minutes: int = DEFAULT_CHUNK_MINUTES,
) -> Iterator[Tuple[datetime, datetime]]:
    """
    Yield sequential time ranges covering [start_time, end_time) using fixed-size chunks.

    Args:
        start_time: Start of the window (UTC).
        end_time: End of the window (UTC).
        chunk_minutes: Size of each chunk in minutes (must be positive).
    """
    if chunk_minutes <= 0:
        raise ValueError("chunk_minutes must be positive")

    current = start_time
    delta = timedelta(minutes=chunk_minutes)
    while current < end_time:
        chunk_end = min(current + delta, end_time)
        yield current, chunk_end
        current = chunk_end


class Scheduler:
    """
    Service for managing background processing tasks.
    
    REFACTORING NOTE (2025-11-20): Added reprocess_date_range() method to consolidate
    reprocessing logic. This allows both API endpoints and CLI scripts to use the same
    code path, reducing duplication and ensuring consistent behavior.
    """

    def __init__(self):
        """Initialize the scheduler."""
        self.running = False
        self.cleanup_interval = settings.cleanup_interval
        self.processing_time = "02:00"  # 2 AM daily processing
        self._service_client: Optional[Client] = None

    def _get_service_client(self) -> Client:
        """
        Return a Supabase client authenticated with the service-role key.

        The client is cached because service-role operations do not depend on
        per-request state, and reusing the HTTP session reduces connection churn.
        """
        if self._service_client is None:
            self._service_client = get_service_role_client()
        return self._service_client

    async def start(self):
        """Start the background scheduler."""
        if self.running:
            return

        self.running = True

        # Start background tasks (removed cleanup loop - not needed)
        tasks = [
            asyncio.create_task(self._daily_processing_loop()),
        ]

        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            print(f"❌ Scheduler error: {str(e)}")
        finally:
            self.running = False

    async def stop(self):
        """Stop the background scheduler."""
        self.running = False

    async def _daily_processing_loop(self):
        """Daily processing loop for audio analysis."""
        while self.running:
            try:
                # Wait until processing time
                await self._wait_until_processing_time()

                if not self.running:
                    break

                # Run daily processing
                await self._process_daily_audio()

                # Wait for next day
                await asyncio.sleep(3600)  # Wait 1 hour before checking again

            except Exception as e:
                print(f"❌ Daily processing loop error: {str(e)}")
                await asyncio.sleep(3600)  # Wait 1 hour before retrying

    async def _wait_until_processing_time(self):
        """Wait until the scheduled processing time."""
        now = datetime.now()
        processing_time = datetime.strptime(self.processing_time, "%H:%M").time()

        # Calculate next processing time
        next_processing = datetime.combine(now.date(), processing_time)
        if next_processing <= now:
            next_processing += timedelta(days=1)

        # Wait until processing time
        wait_seconds = (next_processing - now).total_seconds()

        await asyncio.sleep(wait_seconds)

    async def _process_daily_audio(self):
        """Process daily audio for all active users."""

        try:
            # Get all users with active Limitless keys
            active_users = await self._get_active_users()

            for user in active_users:
                try:
                    await self._process_user_audio(user)
                except Exception as e:
                    print(
                        f"❌ Error processing audio for user {user['user_id']}: {str(e)}"
                    )
                    continue

        except Exception as e:
            print(f"❌ Daily audio processing failed: {str(e)}")

    async def _process_user_audio(self, user: dict):
        """
        Process audio for a specific user with enhanced logging.

        This is the main entry point for processing a user's audio. It handles:
        - Incremental processing (resumes from last processed timestamp)
        - Timezone-aware date range calculation
        - 2-hour chunk processing
        - Enhanced logging for database tracking

        Args:
            user: User dictionary with user_id, email, and timezone fields

        Called by:
            - "Update Today's Count" button (via current_day_routes.py)
            - Manual reprocessing (via manual_reprocess_yesterday.py)
            - Future: Scheduled daily processing (if scheduler.start() is enabled)
        """
        user_id = user["user_id"]
        trigger_type = getattr(
            self, "_trigger_type", "manual"
        )  # Default to manual for backward compatibility

        # Initialize enhanced logger - for scheduled/Update Today processing, always use today's date
        # For reprocessing, process_date is set by caller (manual_reprocess_yesterday)
        # The enhanced logger tracks API calls, laughter events, duplicates, and saves to processing_logs table
        from .enhanced_logger import get_enhanced_logger
        from datetime import date

        enhanced_logger = get_enhanced_logger(
            user_id, trigger_type, process_date=date.today()
        )

        # Track clip paths created in this processing session (for orphan cleanup exclusion)
        all_stored_clip_paths: set = set()

        try:
            try:
                api_key = fetch_decrypted_limitless_key(
                    user_id,
                    supabase=self._get_service_client(),
                )
            except LimitlessKeyError:
                message = "No Limitless API key found for user"
                print(f"⚠️ {message} {user_id}")
                enhanced_logger.add_error("no_api_key", message)
                await enhanced_logger.save_to_database("failed", message)
                return
            except Exception as exc:
                message = f"Failed to load Limitless API key: {exc}"
                print(f"❌ {message}")
                enhanced_logger.add_error("api_key_load_failed", message)
                await enhanced_logger.save_to_database("failed", message)
                return

            # Calculate date range (process full day in 15-minute chunks)
            # Uses user's timezone from database to determine "today" boundaries
            now = datetime.now(pytz.timezone(user.get("timezone", "UTC")))
            start_of_day = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            )  # Start of day

            # CRITICAL FIX: Check if we already processed today - start from latest timestamp
            # Implements requirement: "only retrieve audio after the latest timestamp of audio retrieved"
            # Convert start_of_day to UTC for comparison with DB timestamps
            start_of_day_utc = start_of_day.astimezone(pytz.UTC)
            _verbose_log(
                f"🔍 Checking for already processed audio today (from {start_of_day_utc.strftime('%Y-%m-%d %H:%M')} UTC / {start_of_day.strftime('%Y-%m-%d %H:%M')} {user.get('timezone', 'UTC')})"
            )
            # Convert now to UTC for API calls (Limitless uses UTC)
            now_utc = now.astimezone(pytz.UTC)

            latest_processed = await self._get_latest_processed_timestamp(
                user_id, start_of_day_utc
            )
            _verbose_log(
                f"🔍 Latest processed timestamp (UTC): {latest_processed.strftime('%Y-%m-%d %H:%M')}"
            )

            # Cap latest_processed at now_utc to handle data from "future" dates due to timezone issues
            if latest_processed > now_utc:
                _verbose_log(
                    f"⚠️ Latest processed ({latest_processed.strftime('%Y-%m-%d %H:%M')}) is in future relative to now ({now_utc.strftime('%Y-%m-%d %H:%M')}), capping to now"
                )
                latest_processed = now_utc

            start_time = (
                latest_processed
                if latest_processed > start_of_day_utc
                else start_of_day_utc
            )

            if latest_processed > start_of_day_utc:
                latest_in_user_tz = latest_processed.astimezone(
                    pytz.timezone(user.get("timezone", "UTC"))
                )
                _verbose_log(
                    f"⏩ Resuming from last processed time: {latest_in_user_tz.strftime('%Y-%m-%d %H:%M')} {user.get('timezone', 'UTC')} / {latest_processed.strftime('%Y-%m-%d %H:%M')} UTC"
                )
            else:
                _verbose_log("🆕 Starting fresh from beginning of day")

            _verbose_log(
                f"📊 Processing range (UTC): {start_time.strftime('%Y-%m-%d %H:%M')} to {now_utc.strftime('%Y-%m-%d %H:%M')}"
            )

            # Pre-flight orphan cleanup - catch any orphans from previous failed runs
            # This ensures we start with a clean slate before processing new chunks
            # No session clip paths to exclude (this is before processing)
            try:
                await self._cleanup_orphaned_files(user_id, start_time, now_utc, exclude_clip_paths=None)
            except Exception as cleanup_err:
                print(
                    f"⚠️ Pre-flight orphan cleanup failed (non-fatal): {str(cleanup_err)}"
                )

            total_segments_processed = 0
            # all_stored_clip_paths initialized before try block
            for chunk_index, (chunk_start, chunk_end) in enumerate(
                generate_time_chunks(
                    start_time,
                    now_utc,
                    chunk_minutes=DEFAULT_CHUNK_MINUTES,
                ),
                start=1,
            ):
                _verbose_log(
                    f"📦 Processing chunk {chunk_index}: {chunk_start.strftime('%H:%M')} UTC to {chunk_end.strftime('%H:%M')} UTC"
                )
                segments_processed, chunk_clip_paths = await self._process_date_range(
                    user_id, api_key, chunk_start, chunk_end
                )
                total_segments_processed += segments_processed
                # Accumulate clip paths created in this chunk to exclude from orphan cleanup
                # This prevents race condition where cleanup runs before DB inserts are visible
                all_stored_clip_paths.update(chunk_clip_paths)

            # Save processing log to database
            # DATABASE WRITE: Creates or updates ONE row in processing_logs table for (user_id, date) combination
            # DATABASE FIELDS POPULATED:
            #   - processing_duration_seconds: Calculated from logger start_time to now
            #   - audio_files_downloaded: Count of OGG files downloaded (incremented by limitless_api._fetch_audio_segments)
            #   - laughter_events_found: Total detections from YAMNet (incremented by enhanced_logger.increment_laughter_events)
            #   - duplicates_skipped: Sum of all skip counters (incremented by enhanced_logger.increment_skipped_* methods)
            #   - trigger_type: 'manual' for Update Today button, 'scheduled' for cron jobs
            #   - status: 'completed' or 'failed'
            # TRIGGER: Called after all chunks are processed for the day
            await enhanced_logger.save_to_database(
                "completed", "Audio processing completed successfully"
            )

            # Log processing summary to console
            enhanced_logger.log_processing_summary()

            # Final orphan cleanup - run ONCE after all chunks are processed
            # Cleans up OGG files older than 2 days that have no references
            # NOTE: Cleanup runs silently in background - check enhanced logger for summary
            # CRITICAL FIX: Exclude clip paths created in this session to prevent race condition
            # where cleanup runs before database inserts are fully visible (read-after-write consistency,
            # connection pooling, etc.). This ensures newly created files are not deleted.
            now_utc = datetime.utcnow()
            start_window = now_utc - timedelta(days=2)
            await self._cleanup_orphaned_files(user_id, start_window, now_utc, exclude_clip_paths=all_stored_clip_paths)

        except Exception as e:
            print(f"❌ Error processing user audio: {str(e)}")
            enhanced_logger.add_error(
                "processing_failed", str(e), context={"user_id": user_id}
            )
            await enhanced_logger.save_to_database(
                "failed", f"Processing failed: {str(e)}"
            )
            enhanced_logger.log_processing_summary()
        finally:
            # ALWAYS run orphan cleanup, even if processing failed
            # This ensures no orphaned files remain from crashed/failed processing
            # CRITICAL FIX: Exclude clip paths created in this session to prevent race condition
            # where cleanup runs before database inserts are fully visible. This ensures newly
            # created files are not deleted even if DB query doesn't see them yet.
            try:
                now_utc = datetime.utcnow()
                start_window = now_utc - timedelta(days=2)
                # all_stored_clip_paths initialized before try block, safe to use here
                await self._cleanup_orphaned_files(user_id, start_window, now_utc, exclude_clip_paths=all_stored_clip_paths)
            except Exception as cleanup_err:
                print(f"⚠️ Orphan cleanup failed (non-fatal): {str(cleanup_err)}")

    async def _process_date_range(
        self, user_id: str, api_key: str, start_time: datetime, end_time: datetime
    ) -> tuple[int, set]:
        """
        Process audio for a specific date range with enhanced logging.

        This method orchestrates the processing of a single 15-minute chunk:
        1. Pre-download check (prevents wasteful OGG downloads)
        2. Download OGG file from Limitless API
        3. Store segment metadata in database
        4. Process audio with YAMNet (detect laughter)
        5. Store laughter detections (with duplicate prevention)
        6. Mark segment as processed
        7. Delete OGG file after processing

        Args:
            user_id: User ID for tracking and folder structure
            api_key: Decrypted Limitless API key
            start_time: Start of time range (UTC, timezone-aware)
            end_time: End of time range (UTC, timezone-aware)

        Returns:
            Tuple of (number of segments processed, set of clip paths successfully stored)

        Called by:
            - _process_user_audio() - for incremental daily processing
            - process_nightly_audio.py - for cron job processing
            - manual_reprocess_yesterday.py - for reprocessing date ranges
        """
        try:
            # OPTIMIZATION: Check if this time range is already fully processed BEFORE downloading
            # This prevents wasteful OGG file downloads for already-processed segments
            # CRITICAL FIX: Uses SERVICE_ROLE_KEY to bypass RLS (needed for cron context without user JWT)
            # Overlap detection: Two time ranges overlap if (segment_start < our_end) AND (segment_end > our_start)
            if await self._is_time_range_processed(user_id, start_time, end_time):
                print(
                    f"⏭️  SKIPPED (already fully processed): Time range {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')} UTC - Already processed, skipping download"
                )
                return 0, set()

            # Get audio segments from Limitless API
            segments = await limitless_api_service.get_audio_segments(
                api_key, start_time, end_time, user_id
            )

            if not segments:
                return 0, set()

            # Process each segment, checking for duplicates
            processed_count = 0
            all_stored_clip_paths = set()  # Track all clip paths created in this processing session
            for segment in segments:
                # Get file_path for logging (handle both dict and object formats)
                file_path = (
                    segment["file_path"]
                    if isinstance(segment, dict)
                    else segment.file_path
                )

                # Check if this specific segment already exists and is processed
                # Uses time range overlap detection to identify duplicates
                if await self._segment_already_processed(user_id, segment):
                    # CRITICAL: Delete the audio file even if already processed
                    # Prevents disk space buildup from duplicate downloads
                    await self._delete_audio_file(file_path, user_id)
                    continue  # Don't increment processed_count

                # Store the segment in the database first
                segment_id = await self._store_audio_segment(user_id, segment)
                if segment_id:
                    # Process the audio segment
                    segment_clip_paths = await self._process_audio_segment(user_id, segment, segment_id)
                    if segment_clip_paths:
                        # Accumulate clip paths created in this processing session
                        # These will be excluded from orphan cleanup to prevent race condition
                        all_stored_clip_paths.update(segment_clip_paths)
                        processed_count += 1

            # Already handled by run-once guard earlier; keep end-of-chunk cleanup disabled

            return processed_count, all_stored_clip_paths

        except Exception as e:
            print(f"❌ Error processing date range: {str(e)}")
            # Get current logger if available (may be None if not in processing context)
            from .enhanced_logger import get_current_logger

            enhanced_logger = get_current_logger()
            if enhanced_logger:
                enhanced_logger.add_error(
                    "date_range_error",
                    str(e),
                    context={
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                    },
                )
            return 0, set()

    async def _store_audio_segment(self, user_id: str, segment) -> Optional[str]:
        """Store audio segment in database."""
        try:
            import uuid

            supabase = self._get_service_client()

            # Generate UUID for the segment
            segment_id = str(uuid.uuid4())

            # Handle both dict and object formats
            if isinstance(segment, dict):
                date = segment["date"]
                start_time = segment["start_time"]
                end_time = segment["end_time"]
                file_path = segment["file_path"]
            else:
                date = (
                    segment.date.isoformat()
                    if hasattr(segment.date, "isoformat")
                    else segment.date
                )
                start_time = (
                    segment.start_time.isoformat()
                    if hasattr(segment.start_time, "isoformat")
                    else segment.start_time
                )
                end_time = (
                    segment.end_time.isoformat()
                    if hasattr(segment.end_time, "isoformat")
                    else segment.end_time
                )
                file_path = segment.file_path

            # Insert audio segment into database
            result = (
                supabase.table("audio_segments")
                .insert(
                    {
                        "id": segment_id,
                        "user_id": user_id,
                        "date": date,
                        "start_time": start_time,
                        "end_time": end_time,
                        "file_path": file_path,
                        "processed": False,
                    }
                )
                .execute()
            )

            if result.data:
                return segment_id
            else:
                print(f"❌ Failed to store audio segment {segment_id}")
                return None

        except Exception as e:
            print(f"❌ Error storing audio segment: {str(e)}")
            return None

    async def _process_audio_segment(self, user_id: str, segment, segment_id: str) -> set:
        """
        Process a single audio segment for laughter detection.
        
        Returns:
            set: Clip paths that were successfully stored in database
        """
        file_path: Optional[str] = None
        audio_deleted = False
        stored_clip_paths = set()
        try:
            # Handle both dict and object formats
            if isinstance(segment, dict):
                file_path = segment["file_path"]
            else:
                file_path = segment.file_path

            # Run YAMNet processing on actual audio file
            yamnet_processor = _get_yamnet_processor()  # Lazy import to avoid TensorFlow crash
            laughter_events = await yamnet_processor.process_audio_file(
                file_path, user_id
            )

            # Track laughter events found for database logging
            # DATABASE FIELD: This increments laughter_events_found counter which is saved to processing_logs.laughter_events_found
            # TRIGGER: Called here after YAMNet processing, before storing detections (which may skip duplicates)
            # Note: This counts ALL detections from YAMNet, even if some are later skipped as duplicates
            from .enhanced_logger import get_current_logger

            if laughter_events:
                # FIX (2025-11-20): Increment by total_detected (before duplicates filtered), not stored_count (after duplicates filtered)
                # 
                # BUG FIXED: Previously, laughter_events_found was incremented by stored_count (line 1074), which caused:
                #   - laughter_events_found = sum of stored_count across segments (WRONG)
                #   - Math didn't work: laughter_events_found - duplicates_skipped ≠ stored_count
                # 
                # CORRECT BEHAVIOR: Increment by total_detected (len(laughter_events)) BEFORE duplicate filtering:
                #   - laughter_events_found = sum of total_detected across segments (CORRECT)
                #   - Math works: laughter_events_found - duplicates_skipped = stored_count
                #
                # IMPACT: This fix ONLY affects the processing_logs.laughter_events_found metric. It does NOT affect:
                #   - Database records (laughter_detections table) - UI reads from here, unchanged
                #   - Disk files (WAV clips) - Created by yamnet_processor, unchanged
                #   - UI display - Reads from laughter_detections table, unchanged
                #   - Debug statements - Print statements unchanged
                #
                # TESTED: Verified on staging with user d26444bc-e441-4f36-91aa-bfee24cb39fb (2025-11-19)
                #   - Before fix: laughter_events_found = 22 (wrong, should be 77)
                #   - After fix: laughter_events_found = 77 (correct, matches segment totals)
                logger = get_current_logger()
                if logger:
                    logger.increment_laughter_events(len(laughter_events))
                
                # CRITICAL FIX (2025-11-23): Add clip paths to exclude set IMMEDIATELY after file creation
                # This prevents orphan cleanup from deleting files if an exception occurs between
                # file creation and DB insert. Previously, paths were only added after successful DB insert,
                # creating a window where files could be deleted by cleanup.
                for event in laughter_events:
                    event_clip_path = getattr(event, "clip_path", None)
                    if event_clip_path:
                        # Add ALL clip paths to exclusion set, regardless of file existence
                        # Files were just created by yamnet_processor._create_audio_clip(), so they should exist.
                        # We exclude them from cleanup anyway because they're part of the current processing session.
                        stored_clip_paths.add(event_clip_path)
                
                # Store laughter detection results in database with duplicate prevention
                # DATABASE WRITE: Inserts into laughter_detections table (some may be skipped as duplicates)
                # TRIGGER: enhanced_logger.increment_skipped_*() methods are called inside _store_laughter_detections()
                # for each duplicate that is skipped (time-window, clip-path, missing-file)
                segment_clip_paths = await self._store_laughter_detections(
                    user_id, segment_id, laughter_events
                )
                # Update with any additional paths that were successfully stored (redundant but safe)
                stored_clip_paths.update(segment_clip_paths)

            # Mark segment as processed
            await self._mark_segment_processed(segment_id)

            # SECURITY: Delete the audio file after processing (as per requirements)
            await self._delete_audio_file(file_path, user_id)
            audio_deleted = True

        except Exception as e:
            print(f"❌ Error processing audio segment {segment_id}: {str(e)}")
        finally:
            # Always attempt to delete the file even if processing failed early
            if file_path and not audio_deleted:
                try:
                    import os as os_module  # Use explicit import to avoid shadowing issues
                    _verbose_log(
                        f"🧹 [FINALLY] Starting cleanup for file: {os_module.path.basename(file_path)}"
                    )
                    await self._delete_audio_file(file_path, user_id)
                    _verbose_log(
                        f"🗑️ ✅ [FINALLY] Cleaned up audio file: {os_module.path.basename(file_path)}"
                    )
                except Exception as cleanup_error:
                    print(
                        f"⚠️ ❌ [FINALLY] Failed to cleanup file {file_path}: {cleanup_error}"
                    )
                    import traceback

                    print(f"⚠️ [FINALLY] Cleanup error traceback: {traceback.format_exc()}")
        
        # Return stored clip paths (outside finally block)
        return stored_clip_paths

        # ========================================================================
        # SEGMENT-LEVEL MEMORY CLEANUP
        # ========================================================================
        # Purpose: Release TensorFlow/NumPy memory after processing each audio segment.
        #          Prevents memory accumulation during long processing runs.
        #
        # Strategy: Clear TensorFlow session and run garbage collection.
        #           Less aggressive than user-level cleanup (3x GC vs 10x) since
        #           we're cleaning up more frequently (per segment vs per user).
        #
        # Test Results: Reduces memory spikes from ~2.4 GB to manageable levels
        #              between segments. Works in conjunction with user-level cleanup.
        # ========================================================================
        try:
            import tensorflow as tf
            import gc

            # Clear TensorFlow session and reset default graph
            # Reason: TensorFlow maintains state between inferences. Clearing releases
            #         internal buffers and graph structures that can accumulate.
            tf.keras.backend.clear_session()
            tf.compat.v1.reset_default_graph()
            
            # Run garbage collection multiple times to collect circular references
            # Reason: TensorFlow objects can have complex reference cycles. Multiple
            #         GC passes ensure they're collected. 3 passes is sufficient for
            #         segment-level cleanup (more aggressive cleanup happens at user level).
            for _ in range(3):
                gc.collect()
            
            # Log memory usage for monitoring and debugging
            # Reason: Track memory patterns and detect leaks. Memory logs help identify
            #         problematic segments or users that consume excessive memory.
            try:
                import psutil
                import os
                process = psutil.Process(os.getpid())
                mem_mb = process.memory_info().rss / 1024 / 1024
                _verbose_log(
                    f"🧠 [FINALLY] TensorFlow/GC cleanup complete - Memory: {mem_mb:.1f} MB"
                )
            except ImportError:
                # psutil not available - log without memory info
                _verbose_log("🧠 [FINALLY] TensorFlow/GC cleanup complete")
        except Exception as mem_error:
            # Non-fatal: Log error but don't fail segment processing
            # Reason: Memory cleanup failures shouldn't prevent audio processing.
            #         Log for debugging but continue execution.
            print(f"⚠️ [FINALLY] Memory cleanup failed: {mem_error}")

    async def _get_active_users(self) -> list:
        """Get all users with active Limitless API keys."""
        try:
            from ..auth.supabase_auth import auth_service

            # Get all users with active Limitless API keys
            result = (
                auth_service.supabase.table("limitless_keys")
                .select("user_id, users!inner(email, timezone)")
                .eq("is_active", True)
                .execute()
            )

            if result.data:
                return [
                    {
                        "user_id": row["user_id"],
                        "email": row["users"]["email"],
                        "timezone": row["users"].get("timezone", "UTC"),
                    }
                    for row in result.data
                ]

            return []

        except Exception as e:
            print(f"❌ Error getting active users: {str(e)}")
            return []

    # REMOVED: _create_processing_log - replaced by enhanced_logger

    async def _get_latest_processed_timestamp(
        self, user_id: str, start_of_day: datetime
    ) -> datetime:
        """Get the latest processed timestamp for today to enable incremental processing."""
        try:
            supabase = self._get_service_client()

            # Query audio_segments for today's data to find latest end_time
            # This tells us what's already been downloaded from Limitless
            result = (
                supabase.table("audio_segments")
                .select("start_time,end_time")
                .eq("user_id", user_id)
                .gte("start_time", start_of_day.isoformat())
                .order("end_time", desc=True)
                .limit(1)
                .execute()
            )

            if result.data and len(result.data) > 0:
                latest_end = result.data[0]["end_time"]
                latest_start = result.data[0]["start_time"]
                print(f"  📋 Found latest segment: {latest_start} to {latest_end}")
                # Parse and return latest processed timestamp
                if isinstance(latest_end, str):
                    latest_dt = datetime.fromisoformat(
                        _norm_iso(latest_end.replace("Z", "+00:00"))
                    )
                    # Ensure timezone-aware
                    if latest_dt.tzinfo is None:
                        latest_dt = latest_dt.replace(tzinfo=pytz.UTC)
                    return latest_dt

            print(f"  📋 No segments found for today - starting fresh")
            # No data processed today - start from beginning of day
            return start_of_day

        except Exception as e:
            print(f"❌ Error getting latest processed timestamp: {str(e)}")
            return start_of_day

    async def _is_time_range_processed(
        self, user_id: str, start_time: datetime, end_time: datetime
    ) -> bool:
        """Check if time range has already been processed for user.

        Uses overlap detection: Two time ranges overlap if:
        (segment_start < our_end) AND (segment_end > our_start)

        FIX: Uses SERVICE_ROLE_KEY to bypass RLS (needed for cron context without user JWT)
        """
        try:
            import pytz

            # Ensure timezone-aware
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=pytz.UTC)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=pytz.UTC)

            supabase = self._get_service_client()

            # Check for any processed segments that overlap with this time range
            # Overlap condition: segment_start < our_end AND segment_end > our_start
            result = (
                supabase.table("audio_segments")
                .select("id")
                .eq("user_id", user_id)
                .eq("processed", True)
                .lt("start_time", end_time.isoformat())
                .gt("end_time", start_time.isoformat())
                .execute()
            )

            found_count = len(result.data) if result.data else 0
            if found_count > 0:
                print(
                    f"🔍 Pre-download check: Found {found_count} processed segment(s) overlapping {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')} UTC"
                )

            return found_count > 0

        except Exception as e:
            print(f"❌ Error checking if time range processed: {str(e)}")
            import traceback

            print(f"❌ Traceback: {traceback.format_exc()}")
            return False

    async def _mark_time_range_processed(
        self, user_id: str, start_time: datetime, end_time: datetime
    ):
        """Mark time range as processed for user."""
        try:
            from ..auth.supabase_auth import auth_service

            # Update all audio segments for this time range to processed
            auth_service.supabase.table("audio_segments").update(
                {"processed": True}
            ).eq("user_id", user_id).gte("start_time", start_time.isoformat()).lte(
                "end_time", end_time.isoformat()
            ).execute()

        except Exception as e:
            print(f"❌ Error marking time range as processed: {str(e)}")

    async def _store_laughter_detections(
        self, user_id: str, segment_id: str, laughter_events: list
    ):
        """
        Store laughter detection results in database with duplicate prevention.

        This method implements THREE layers of duplicate detection:
        1. TIME-WINDOW DUPLICATE: Same class_id within 5 seconds (catches YAMNet's overlapping detection windows)
        2. CLIP-PATH DUPLICATE: Exact same filename already exists (catches reprocessing same file)
        3. DATABASE CONSTRAINT: Unique constraint on (user_id, timestamp, class_id) - final safety net

        IMPORTANT: Different class_ids at the same timestamp are NOT duplicates (e.g., Laughter class_id=13
        and Giggle class_id=15 at same timestamp are unique detections). This is enforced by the database
        constraint unique_laughter_timestamp_user_class which includes class_id.

        Args:
            user_id: User ID for database insertion
            segment_id: Audio segment ID that these detections belong to
            laughter_events: List of LaughterEvent objects from YAMNet processing

        Database Operations:
            - Queries laughter_detections table for duplicate checks
            - Inserts new laughter_detections rows
            - Increments enhanced_logger skip counters for duplicates
            - Deletes duplicate WAV files immediately after detection

        Returns:
            set: Clip paths that were successfully stored in database (to exclude from orphan cleanup)
        """
        try:
            from .enhanced_logger import get_current_logger

            # Track statistics
            total_detected = len(laughter_events)
            skipped_time_window = 0
            skipped_clip_path = 0
            skipped_missing_file = 0
            stored_count = 0
            stored_clip_paths = set()  # Track successfully stored clip paths

            # CRITICAL DEBUG: Entry point

            supabase = self._get_service_client()

            # Store each laughter detection event with duplicate prevention
            for event in laughter_events:
                # Convert timestamp to proper datetime
                if isinstance(event.timestamp, datetime):
                    event_datetime = event.timestamp
                else:
                    # Get the segment start time from the database
                    segment_result = (
                        supabase.table("audio_segments")
                        .select("start_time")
                        .eq("id", segment_id)
                        .execute()
                    )
                    if segment_result.data:
                        raw_start = segment_result.data[0]["start_time"].replace(
                            "Z", "+00:00"
                        )
                        segment_start = datetime.fromisoformat(_norm_iso(raw_start))
                        # Ensure timezone-aware
                        if segment_start.tzinfo is None:
                            segment_start = segment_start.replace(tzinfo=pytz.UTC)
                        # Add the event timestamp (in seconds) to the segment start time
                        if isinstance(event.timestamp, (int, float)):
                            event_datetime = segment_start + timedelta(
                                seconds=float(event.timestamp)
                            )
                            # Truncate microseconds to avoid PostgreSQL issues
                            event_datetime = event_datetime.replace(microsecond=0)
                        else:
                            event_datetime = datetime.now(pytz.UTC)
                    else:
                        event_datetime = datetime.now(pytz.UTC)

                # DUPLICATE PREVENTION: Check for existing laughter detection within 5 seconds
                # IMPORTANT: Also check class_id - same timestamp with different class_id is NOT a duplicate
                # (e.g., Laughter class_id=13 and Giggle class_id=15 at same timestamp are different detections)
                #
                # WHY 5 SECONDS: YAMNet uses overlapping detection windows (patch_duration=0.48s), so the same
                # laughter event can be detected multiple times at slightly different timestamps. A 5-second
                # window catches these false duplicates while still allowing genuine laughter events that are
                # close together.
                #
                # DATABASE RELATIONSHIP: This is a "soft" duplicate check (time window) before attempting
                # database insertion. The database also has a "hard" constraint (unique_laughter_timestamp_user_class)
                # that prevents exact duplicates at the same (user_id, timestamp, class_id).
                time_window = timedelta(seconds=5)
                start_window = event_datetime - time_window
                end_window = event_datetime + time_window

                event_class_id = getattr(event, "class_id", None)
                # Query database for existing detections in the time window
                # Selects: id, timestamp, class_id - we only need class_id to match for duplicates
                existing_detections = (
                    supabase.table("laughter_detections")
                    .select("id, timestamp, class_id")
                    .eq("user_id", user_id)
                    .gte("timestamp", start_window.isoformat())
                    .lte("timestamp", end_window.isoformat())
                    .execute()
                )

                # Filter to only check detections with the SAME class_id (different class_ids at same timestamp are unique)
                # This matches the database constraint unique_laughter_timestamp_user_class behavior
                if existing_detections.data:
                    matching_class_detections = [
                        d
                        for d in existing_detections.data
                        if d.get("class_id") == event_class_id
                    ]
                    if matching_class_detections:
                        # CRITICAL FIX (2025-11-27): Orphaned Records Prevention
                        # 
                        # PROBLEM: When duplicate detection finds an existing DB record, the code previously
                        # deleted the new file immediately. However, if the existing record's file was already
                        # deleted (by cleanup, manual deletion, or filesystem issues), this created an orphaned
                        # DB record - a record pointing to a non-existent file, causing "audio file not available"
                        # errors in the UI.
                        #
                        # SOLUTION: Before deleting the new file, verify the existing record's file still exists.
                        # - If existing file exists: Delete new file (true duplicate) - same behavior as before
                        # - If existing file missing: Update orphaned record with new file instead of deleting it
                        #
                        # This ensures every DB record has a corresponding file on disk, preventing UI errors.
                        existing_record = matching_class_detections[0]
                        existing_record_id = existing_record.get("id")
                        
                        # Fetch the existing record's clip_path to check if its file exists
                        existing_record_full = (
                            supabase.table("laughter_detections")
                            .select("id, clip_path")
                            .eq("id", existing_record_id)
                            .execute()
                        )
                        
                        existing_file_exists = False
                        if existing_record_full.data:
                            existing_clip_path = existing_record_full.data[0].get("clip_path")
                            if existing_clip_path:
                                # Resolve existing file path (handle both relative and absolute paths)
                                # NOTE: This duplicates path resolution logic - could be refactored to use
                                # path_utils.py helpers in the future, but kept as-is for minimal change
                                if not os.path.isabs(existing_clip_path):
                                    # Relative path (e.g., ./uploads/clips/user/file.wav)
                                    # Resolve from project root
                                    project_root_check = os.path.dirname(
                                        os.path.dirname(
                                            os.path.dirname(os.path.abspath(__file__))
                                        )
                                    )
                                    existing_resolved = os.path.normpath(
                                        os.path.join(project_root_check, strip_leading_dot_slash(existing_clip_path))
                                    )
                                else:
                                    # Absolute path (e.g., /var/lib/giggles/uploads/clips/user/file.wav)
                                    existing_resolved = existing_clip_path
                                existing_file_exists = os.path.exists(existing_resolved)
                        
                        if existing_file_exists:
                            # CASE 1: Existing file exists - this is a true duplicate
                            # Delete the new file and skip DB insertion (same behavior as before fix)
                            skipped_time_window += 1
                            enhanced_logger = get_current_logger()
                            if enhanced_logger:
                                enhanced_logger.increment_skipped_time_window()
                            ts_str = event_datetime.astimezone(
                                pytz.timezone("America/Los_Angeles")
                            ).strftime("%H:%M:%S")
                            # Delete duplicate clip file immediately (before it gets stored in DB)
                            try:
                                if getattr(event, "clip_path", None):
                                    # Resolve path - handle both relative and absolute paths
                                    clip_path = event.clip_path
                                    if not os.path.isabs(clip_path):
                                        # Relative path - resolve from project root
                                        project_root = os.path.dirname(
                                            os.path.dirname(
                                                os.path.dirname(os.path.abspath(__file__))
                                            )
                                        )
                                        clip_path = os.path.join(project_root, clip_path)

                                    if os.path.exists(clip_path):
                                        os.remove(clip_path)
                            except Exception as cleanup_err:
                                # Silently ignore cleanup errors (file may already be deleted)
                                pass
                            continue  # Skip this duplicate - don't insert into DB
                        else:
                            # CASE 2: Existing file is missing - orphaned DB record detected
                            # Instead of deleting the new file (which would create another orphan),
                            # update the existing orphaned record to point to the new file.
                            # This recovers the orphaned record and ensures data integrity.
                            try:
                                if getattr(event, "clip_path", None) and existing_record_id:
                                    # Update the orphaned record with the new file path and latest probability
                                    # (probability may have changed slightly if reprocessing same segment)
                                    # CRITICAL FIX (2025-11-30): Store absolute path (uniform path format)
                                    # event.clip_path is now absolute from yamnet_processor, use it directly
                                    supabase.table("laughter_detections").update({
                                        "clip_path": event.clip_path,  # Store absolute path (uniform format)
                                        "probability": event.probability,
                                    }).eq("id", existing_record_id).execute()
                                    
                                    # Track this as successfully stored (even though it was an update, not insert)
                                    if event.clip_path:
                                        stored_clip_paths.add(event.clip_path)
                                    stored_count += 1
                                    continue  # Skip inserting a new record (we updated the existing one)
                            except Exception as update_err:
                                # If update fails (e.g., DB error), fall through to normal processing
                                # This ensures we don't lose the detection if update fails
                                enhanced_logger = get_current_logger()
                                if enhanced_logger:
                                    enhanced_logger.add_error("orphaned_record_update_failed", f"Failed to update orphaned record {existing_record_id}: {str(update_err)}")
                                # Fall through to normal processing if update fails

                # DUPLICATE PREVENTION: Check for existing clip path
                if event.clip_path:
                    # CRITICAL FIX (2025-11-30): Compare absolute paths directly (uniform path format)
                    # event.clip_path is now absolute from yamnet_processor
                    # For backwards compatibility during migration, normalize old relative paths in DB
                    new_path_absolute = event.clip_path  # Already absolute from yamnet_processor
                    
                    # Get all records and compare paths
                    # During migration period, DB may have both relative (old) and absolute (new) paths
                    existing_clip = (
                        supabase.table("laughter_detections")
                        .select("id, clip_path")
                        .execute()
                    )
                    # Filter by path comparison (normalize old relative paths for comparison)
                    if new_path_absolute and existing_clip.data:
                        matching_records = [
                            r for r in existing_clip.data
                            if r.get("clip_path") and (
                                r["clip_path"] == new_path_absolute or  # Direct match (both absolute)
                                _ensure_absolute_path(r["clip_path"]) == new_path_absolute  # Normalize old relative paths
                            )
                        ]
                        existing_clip.data = matching_records
                    else:
                        existing_clip.data = []
                    if existing_clip.data:
                        # CRITICAL FIX (2025-11-27): Orphaned Records Prevention (Duplicate by clip_path)
                        # 
                        # Same fix as time-window duplicate check above, but for exact clip_path matches.
                        # When the same clip_path is found (same segment + timestamp + class_id), verify
                        # the existing record's file exists before deleting the new file.
                        #
                        # NOTE: If clip_path is the same, the new file we just created is at the same path
                        # as the missing file, so we keep it and just update the probability.
                        existing_clip_record = existing_clip.data[0]
                        existing_clip_id = existing_clip_record.get("id")
                        existing_clip_path_db = existing_clip_record.get("clip_path")
                        
                        existing_file_exists = False
                        if existing_clip_path_db:
                            # Resolve existing file path (handle both relative and absolute paths)
                            # NOTE: Path resolution logic duplicated from above - could be refactored
                            if not os.path.isabs(existing_clip_path_db):
                                # Relative path - resolve from project root
                                project_root_check = os.path.dirname(
                                    os.path.dirname(
                                        os.path.dirname(os.path.abspath(__file__))
                                    )
                                )
                                existing_resolved = os.path.normpath(
                                    os.path.join(project_root_check, strip_leading_dot_slash(existing_clip_path_db))
                                )
                            else:
                                # Absolute path - use as-is
                                existing_resolved = existing_clip_path_db
                            existing_file_exists = os.path.exists(existing_resolved)
                        
                        if existing_file_exists:
                            # CASE 1: Existing file exists - this is a true duplicate
                            # Delete the new file and skip DB insertion (same behavior as before fix)
                            skipped_clip_path += 1
                            enhanced_logger = get_current_logger()
                            if enhanced_logger:
                                enhanced_logger.increment_skipped_clip_path()
                            ts_str = event_datetime.astimezone(
                                pytz.timezone("America/Los_Angeles")
                            ).strftime("%H:%M:%S")
                            # Delete duplicate clip file immediately (before it gets stored in DB)
                            try:
                                # Resolve path - handle both relative and absolute paths
                                clip_path = event.clip_path
                                if not os.path.isabs(clip_path):
                                    # Relative path - resolve from project root
                                    project_root = os.path.dirname(
                                        os.path.dirname(
                                            os.path.dirname(os.path.abspath(__file__))
                                        )
                                    )
                                    clip_path = os.path.join(project_root, clip_path)

                                if os.path.exists(clip_path):
                                    os.remove(clip_path)
                            except Exception as cleanup_err:
                                # Silently ignore cleanup errors (file may already be deleted)
                                pass
                            continue  # Skip this duplicate - don't insert into DB
                        else:
                            # CASE 2: Existing file is missing - orphaned DB record detected
                            # Since clip_path is the same, the new file we just created is at the same path
                            # as the missing file. Keep the new file and update the existing record's probability
                            # (probability may have changed slightly if reprocessing the same segment).
                            try:
                                if existing_clip_id:
                                    # Update probability in case it's slightly different (reprocessing same segment)
                                    # clip_path is the same, so no need to update it - the new file is already there
                                    supabase.table("laughter_detections").update({
                                        "probability": event.probability,
                                    }).eq("id", existing_clip_id).execute()
                                    
                                    # Track this as successfully stored (even though it was an update, not insert)
                                    if event.clip_path:
                                        stored_clip_paths.add(event.clip_path)
                                    stored_count += 1
                                    continue  # Skip inserting a new record (we updated the existing one)
                            except Exception as update_err:
                                # If update fails (e.g., DB error), fall through to normal processing
                                # This ensures we don't lose the detection if update fails
                                enhanced_logger = get_current_logger()
                                if enhanced_logger:
                                    enhanced_logger.add_error("orphaned_record_update_failed", f"Failed to update orphaned record {existing_clip_id}: {str(update_err)}")
                                # Fall through to normal processing if update fails

                # Store the laughter detection (no duplicates found)
                # Only store if clip file actually exists (prevent 404s)
                clip_exists = False
                # CRITICAL GUARD (2025-11-23): Never store DB record if file doesn't exist
                # This prevents orphaned DB records pointing to non-existent files
                if not event.clip_path:
                    # No clip path means file creation failed - skip this detection
                    skipped_missing_file += 1
                    enhanced_logger = get_current_logger()
                    if enhanced_logger:
                        enhanced_logger.increment_skipped_missing_file()
                    ts_str = event_datetime.astimezone(
                        pytz.timezone("America/Los_Angeles")
                    ).strftime("%H:%M:%S")
                    print(
                        f"⏭️  SKIPPED (no clip path): {ts_str} prob={event.probability:.3f} - File creation failed (clip_path is None)"
                    )
                    continue

                clip_path = event.clip_path
                clip_exists = False
                
                # CRITICAL FIX (2025-11-30): event.clip_path is now always absolute from yamnet_processor
                # However, during migration period, we may encounter old relative paths from DB
                # Keep resolution logic for backwards compatibility during migration
                if not os.path.isabs(clip_path):
                    # Relative path (old data during migration) - resolve from project root
                    project_root = os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    )
                    resolved_path = os.path.normpath(
                        os.path.join(project_root, strip_leading_dot_slash(clip_path))
                    )
                else:
                    # Absolute path (new format) - use as-is
                    resolved_path = clip_path
                
                clip_exists = os.path.exists(resolved_path)
                
                # CRITICAL GUARD: If file doesn't exist, DO NOT store in DB
                # This is the last line of defense against orphaned records
                if not clip_exists:
                    skipped_missing_file += 1
                    enhanced_logger = get_current_logger()
                    if enhanced_logger:
                        enhanced_logger.increment_skipped_missing_file()
                    ts_str = event_datetime.astimezone(
                        pytz.timezone("America/Los_Angeles")
                    ).strftime("%H:%M:%S")
                    print(
                        f"⏭️  SKIPPED (missing clip file): {ts_str} prob={event.probability:.3f} - File not found: {resolved_path}"
                    )
                    print(
                        f"    Original path in event: {event.clip_path}"
                    )
                    continue
                
                # Use resolved path for file operations, but store original path in DB
                clip_path = resolved_path

                # Log clip file status before database insertion
                # BUG FIX (2025-11-20): Use resolved clip_path, not event.clip_path
                # The resolved path is what we verified exists, so use it for getsize
                # But store the original event.clip_path in DB (as it was created by yamnet_processor)
                # CRITICAL GUARD (2025-11-23): Double-check file exists before getting size
                # This is redundant but ensures we never proceed if file was deleted between checks
                if not os.path.exists(clip_path):
                    print(f"❌ CRITICAL: File disappeared between checks: {clip_path}")
                    skipped_missing_file += 1
                    enhanced_logger = get_current_logger()
                    if enhanced_logger:
                        enhanced_logger.increment_skipped_missing_file()
                    continue
                
                file_size = os.path.getsize(clip_path) if clip_path else 0

                try:
                    supabase.table("laughter_detections").insert(
                        {
                            "user_id": user_id,
                            "audio_segment_id": segment_id,
                            "timestamp": event_datetime.isoformat(),
                            "probability": event.probability,
                            "clip_path": event.clip_path,  # CRITICAL FIX (2025-11-30): Store absolute path (uniform format). event.clip_path is now absolute from yamnet_processor
                            "class_id": getattr(event, "class_id", None),
                            "class_name": getattr(event, "class_name", None),
                            "notes": "",
                        }
                    ).execute()
                    stored_count += 1
                    # Track successfully stored clip path for orphan cleanup exclusion
                    # This prevents race condition where cleanup deletes files before DB inserts are visible
                    if event.clip_path:
                        stored_clip_paths.add(event.clip_path)
                except Exception as insert_error:
                    # Handle unique constraint violations gracefully
                    # DATABASE CONSTRAINT: unique_laughter_timestamp_user_class on (user_id, timestamp, class_id)
                    # This is the final safety net - catches duplicates that passed the time-window check
                    # (e.g., exact same timestamp+class_id detected in different processing sessions)
                    #
                    # CONSTRAINT NAME: unique_laughter_timestamp_user_class
                    # CONSTRAINT FIELDS: (user_id, timestamp, class_id) - all three must match for violation
                    # CONSTRAINT PURPOSE: Ensures database-level uniqueness even if application-level checks miss something
                    #
                    # Note: unique_laughter_timestamp_user_class includes class_id, so different classes at same timestamp are allowed
                    # Also check unique_laughter_clip_path constraint (prevents duplicate clip file paths)
                    if "unique_laughter_timestamp_user_class" in str(
                        insert_error
                    ) or "unique_laughter_clip_path" in str(insert_error):
                        skipped_time_window += 1
                        ts_str = event_datetime.astimezone(
                            pytz.timezone("America/Los_Angeles")
                        ).strftime("%H:%M:%S")
                        print(
                            f"⏭️  SKIPPED (database constraint): {ts_str} prob={event.probability:.3f} - Unique constraint violation (same user_id, timestamp, AND class_id already exists)"
                        )
                        # Delete duplicate clip file immediately (database constraint caught it)
                        try:
                            if getattr(event, "clip_path", None):
                                # Resolve path - handle both relative and absolute paths
                                clip_path = event.clip_path
                                if not os.path.isabs(clip_path):
                                    # Relative path - resolve from project root
                                    project_root = os.path.dirname(
                                        os.path.dirname(
                                            os.path.dirname(os.path.abspath(__file__))
                                        )
                                    )
                                    clip_path = os.path.join(project_root, clip_path)

                                if os.path.exists(clip_path):
                                    os.remove(clip_path)
                                    print(
                                        f"🧹 Deleted clip after constraint duplicate: {os.path.basename(event.clip_path)}"
                                    )
                                else:
                                    print(
                                        f"⚠️ Duplicate clip file not found at: {clip_path}"
                                    )
                        except Exception as cleanup_err:
                            print(
                                f"⚠️ Failed to delete clip after duplicate constraint: {str(cleanup_err)}"
                            )
                    else:
                        # Non-duplicate insert error - delete the WAV file to prevent orphan
                        print(
                            f"❌ Error inserting laughter detection: {str(insert_error)}"
                        )
                        # Delete the clip file since DB insert failed (prevents orphan)
                        try:
                            if getattr(event, "clip_path", None):
                                clip_path = event.clip_path
                                if not os.path.isabs(clip_path):
                                    project_root = os.path.dirname(
                                        os.path.dirname(
                                            os.path.dirname(os.path.abspath(__file__))
                                        )
                                    )
                                    clip_path = os.path.join(project_root, clip_path)
                                if os.path.exists(clip_path):
                                    os.remove(clip_path)
                                    print(
                                        f"🧹 Deleted clip after DB insert failure: {os.path.basename(event.clip_path)}"
                                    )
                        except Exception as cleanup_err:
                            print(
                                f"⚠️ Failed to delete clip after DB insert failure: {str(cleanup_err)}"
                            )

            # Summary logging - use print() for visibility with uvicorn
            # DATABASE MAPPING: These counters are aggregated by EnhancedProcessingLogger and saved to processing_logs table:
            # - total_detected -> used to calculate laughter_events_found (set via enhanced_logger.increment_laughter_events())
            # - skipped_time_window + skipped_clip_path + skipped_missing_file -> duplicates_skipped field
            # - stored_count -> actual rows inserted into laughter_detections table
            #
            # TRIGGER: enhanced_logger.increment_laughter_events(len(laughter_events)) is called from
            # _process_audio_segment() to track total detected (BEFORE duplicate filtering).
            # Skip counters are incremented above via enhanced_logger.increment_skipped_*() methods which
            # update the logger's internal counters.
            _verbose_log("=" * 80)

            # REMOVED (2025-11-20): Don't increment by stored_count here - we already incremented by total_detected above
            # 
            # BUG FIXED: Previously, this line incremented laughter_events_found by stored_count (after duplicates filtered),
            # which caused the metric to be wrong. The fix moved the increment to BEFORE duplicate filtering (line 518),
            # so we increment by total_detected instead.
            #
            # OLD CODE (REMOVED):
            #   post_store_logger = get_current_logger()
            #   if post_store_logger and stored_count:
            #       post_store_logger.increment_laughter_events(stored_count)
            #
            # The total was already incremented before duplicate filtering, so this would double-count if left here.
            # Keeping this commented for reference and to prevent accidental re-addition.
            _verbose_log(f"📊 DETECTION SUMMARY for segment {segment_id[:8]}:")
            _verbose_log(f"   🎭 Total detected by YAMNet:     {total_detected}")
            _verbose_log(
                f"   ⏭️  Skipped (time window dup):   {skipped_time_window}"
            )
            _verbose_log(f"   ⏭️  Skipped (clip path dup):      {skipped_clip_path}")
            _verbose_log(f"   ⏭️  Skipped (missing file):      {skipped_missing_file}")
            _verbose_log(f"   ✅ Successfully stored:           {stored_count}")
            _verbose_log(
                f"   📉 Total skipped:                 {skipped_time_window + skipped_clip_path + skipped_missing_file}"
            )
            _verbose_log("=" * 80)

            # Skip counters already incremented above during the loop via enhanced_logger.increment_skipped_*() methods
            
            return stored_clip_paths

        except Exception as e:
            print(f"❌ Error storing laughter detections: {str(e)}")
            return set()  # Return empty set on error

    async def _segment_already_processed(self, user_id: str, segment) -> bool:
        """Check if a specific segment already exists and is processed."""
        try:
            from datetime import datetime

            supabase = self._get_service_client()

            # Handle both dict and object formats
            if isinstance(segment, dict):
                start_time = segment["start_time"]
                end_time = segment["end_time"]
            else:
                start_time = (
                    segment.start_time.isoformat()
                    if hasattr(segment.start_time, "isoformat")
                    else segment.start_time
                )
                end_time = (
                    segment.end_time.isoformat()
                    if hasattr(segment.end_time, "isoformat")
                    else segment.end_time
                )

            # Parse the new segment times
            try:
                new_start = datetime.fromisoformat(
                    _norm_iso(start_time.replace("Z", "+00:00"))
                )
                new_end = datetime.fromisoformat(
                    _norm_iso(end_time.replace("Z", "+00:00"))
                )
            except Exception as e:
                print(f"❌ Error parsing segment times: {str(e)}")
                return False

            # Get all existing segments for this user
            result = (
                supabase.table("audio_segments")
                .select("id, start_time, end_time, processed")
                .eq("user_id", user_id)
                .execute()
            )

            if not result.data:
                return False

            # Check for overlapping segments
            for existing_segment in result.data:
                try:
                    existing_start = datetime.fromisoformat(
                        _norm_iso(existing_segment["start_time"].replace("Z", "+00:00"))
                    )
                    existing_end = datetime.fromisoformat(
                        _norm_iso(existing_segment["end_time"].replace("Z", "+00:00"))
                    )

                    # Ensure timezone-aware
                    if existing_start.tzinfo is None:
                        existing_start = existing_start.replace(tzinfo=pytz.UTC)
                    if existing_end.tzinfo is None:
                        existing_end = existing_end.replace(tzinfo=pytz.UTC)
                    if new_start.tzinfo is None:
                        new_start = new_start.replace(tzinfo=pytz.UTC)
                    if new_end.tzinfo is None:
                        new_end = new_end.replace(tzinfo=pytz.UTC)

                    # Check if time ranges overlap
                    # Two time ranges overlap if: start1 < end2 AND start2 < end1
                    if new_start < existing_end and existing_start < new_end:
                        seg_id = existing_segment.get("id", "unknown")
                        # If already processed, don't reprocess
                        if existing_segment["processed"]:
                            return True

                except Exception as e:
                    print(f"⚠️ Error parsing existing segment times: {str(e)}")
                    continue

            return False

        except Exception as e:
            print(f"❌ Error checking if segment already processed: {str(e)}")
            return False

    async def _delete_audio_file(self, file_path: str, user_id: str):
        """Delete audio file after processing (plaintext path, no encryption)."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            else:
                print(f"⚠️ ⚠️ Audio file not found: {file_path}")

        except Exception as e:
            print(f"❌ ❌ Error deleting audio file: {str(e)}")

    async def _cleanup_orphaned_files(
        self, user_id: str, start_time: datetime, end_time: datetime, exclude_clip_paths: set = None
    ):
        """
        Clean up orphaned audio files from previous runs that should have been deleted.

        This method performs two-pass cleanup:
        1. Check database-referenced files: Delete OGG files from audio_segments table that still exist on disk
           (these should have been deleted after processing, but may remain if processing failed)
        2. Scan disk for unreferenced files: Find OGG/WAV files on disk that have no database records

        File Locations Scanned:
        - OGG files: uploads/audio/{user_id}/*.ogg
        - WAV clips (legacy): uploads/clips/*.wav
        - WAV clips (current): uploads/clips/{user_id}/*.wav

        Args:
            user_id: User ID for user-specific folder scanning
            start_time: Start of time window (currently unused, scans all files)
            end_time: End of time window (currently unused, scans all files)
            exclude_clip_paths: Optional set of clip paths to exclude from cleanup.
                Used to prevent race condition where cleanup runs immediately after
                processing, before database inserts are fully visible. Files in this
                set are skipped even if not found in database query results.

        Called by:
            - _process_user_audio() - once after all chunks are processed
            - process_nightly_audio.py - after nightly processing completes
            - manual_reprocess_yesterday.py - after reprocessing completes
            - Future: Could be called by scheduled cleanup job

        Note: This runs silently - only prints messages when files are found and deleted
        """
        try:
            supabase = self._get_service_client()

            # Find all processed segments for this user (check ALL processed segments)
            # This catches orphaned files from any previous run
            result = (
                supabase.table("audio_segments")
                .select("id, file_path, start_time, end_time")
                .eq("user_id", user_id)
                .eq("processed", True)
                .execute()
            )

            # Step 1: Check files from database segments
            db_files_cleaned = 0
            if result.data:
                for segment in result.data:
                    file_path = segment.get("file_path")
                    if file_path:
                        # Normalize path - remove ./ prefix if present, handle relative paths
                        normalized_path = strip_leading_dot_slash(file_path)
                        # Construct full path relative to project root
                        project_root = os.path.dirname(
                            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        )
                        full_path = os.path.join(project_root, normalized_path)

                        if os.path.exists(full_path):
                            _verbose_log(
                                f"⚠️ 🗑️ CLEANUP: Deleting orphaned OGG: {os.path.basename(full_path)}"
                            )
                            await self._delete_audio_file(full_path, user_id)
                            db_files_cleaned += 1
                        elif os.path.exists(file_path):
                            # Also try original path (in case it's absolute)
                            _verbose_log(
                                f"⚠️ 🗑️ CLEANUP: Deleting orphaned OGG: {os.path.basename(file_path)}"
                            )
                            await self._delete_audio_file(file_path, user_id)
                            db_files_cleaned += 1

            # Step 2: Scan disk for files without database records
            disk_files_cleaned = 0

            # Get all file_paths from database (for comparison)
            all_db_paths = set()
            if result.data:
                for seg in result.data:
                    fp = seg.get("file_path", "")
                    if fp:
                        normalized = strip_leading_dot_slash(fp)
                        all_db_paths.add(
                            normalized.lower()
                        )  # Case-insensitive comparison

            # Get all clip_paths from laughter_detections table
            # 
            # CRITICAL FIX (2025-11-24): Supabase limits results to 1000 by default.
            # We must paginate to fetch ALL records, not just the first 1000.
            # 
            # WHY THIS IS CRITICAL:
            # - Without pagination, cleanup only sees the first 1000 detections
            # - Files from detections 1001+ are not in the exclusion set
            # - These files get deleted as "orphaned" even though they're legitimate
            # - This causes data loss for users with >1000 detections
            # 
            # PAGINATION LOGIC:
            # - Start at offset 0, fetch 1000 records at a time
            # - Continue until we get fewer than 1000 records (end of data)
            # - Accumulate all clip_paths in exclusion set
            # - This ensures ALL legitimate files are protected from cleanup
            all_clip_paths = set()
            offset = 0
            limit = 1000
            while True:
                # range() is [start, end) - exclusive on end: range(0, 1000) = records 0-999 (1000 records)
                laughter_result = (
                    supabase.table("laughter_detections")
                    .select("clip_path")
                    .eq("user_id", user_id)
                    .range(offset, offset + limit)
                    .execute()
                )
                if not laughter_result.data:
                    # No more records, we're done
                    break
                for detection in laughter_result.data:
                    cp = detection.get("clip_path", "")
                    if cp:
                        # Normalize to just filename for comparison
                        clip_filename = os.path.basename(cp)
                        all_clip_paths.add(clip_filename.lower())
                # Continue to next page if we got a full page (limit records)
                # If we got fewer, we've reached the end
                if len(laughter_result.data) < limit:
                    break
                offset += limit

            # Scan user's audio directory for OGG files
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            user_audio_dir = os.path.join(project_root, "uploads", "audio", user_id)

            if os.path.exists(user_audio_dir):
                for filename in os.listdir(user_audio_dir):
                    if filename.endswith(".ogg"):
                        file_path = os.path.join(user_audio_dir, filename)
                        # Check if this file is in the database
                        relative_path = os.path.join(
                            "uploads", "audio", user_id, filename
                        )
                        if relative_path.lower() not in all_db_paths:
                            # File exists on disk but not in database - true orphan
                            _verbose_log(
                                f"⚠️ 🗑️ CLEANUP: Deleting orphaned OGG: {filename}"
                            )
                            await self._delete_audio_file(file_path, user_id)
                            disk_files_cleaned += 1

            # Clean up orphaned WAV clips
            # Clips can be in two locations:
            # 1. Legacy: uploads/clips/*.wav (old format)
            # 2. Current: uploads/clips/{user_id}/*.wav (per-user folders)
            # 
            # CRITICAL FIX: Exclude files created in the current processing session to avoid race condition
            # where cleanup runs before database inserts are fully visible (connection pooling, read-after-write
            # consistency, etc.). This prevents deleting files that were just created and inserted.
            exclude_filenames = set()
            if exclude_clip_paths:
                for path in exclude_clip_paths:
                    exclude_filenames.add(os.path.basename(path).lower())
            
            clips_dir = os.path.join(project_root, "uploads", "clips")
            if os.path.exists(clips_dir):
                # Check legacy location (direct in clips/)
                for filename in os.listdir(clips_dir):
                    if filename.endswith(".wav") and os.path.isfile(
                        os.path.join(clips_dir, filename)
                    ):
                        file_path = os.path.join(clips_dir, filename)
                        # Skip files created in current session
                        if filename.lower() in exclude_filenames:
                            continue
                        
                        if filename.lower() not in all_clip_paths:
                            # WAV file exists on disk but not referenced in laughter_detections - true orphan
                            _verbose_log(
                                f"⚠️ 🗑️ CLEANUP: Deleting orphaned WAV clip (legacy location): {filename}"
                            )
                            await self._delete_audio_file(file_path, user_id)
                            disk_files_cleaned += 1

                # Check per-user folder location
                user_clips_dir = os.path.join(clips_dir, user_id)
                if os.path.exists(user_clips_dir):
                    wav_files = [f for f in os.listdir(user_clips_dir) if f.endswith(".wav")]
                    for filename in wav_files:
                        file_path = os.path.join(user_clips_dir, filename)
                        filename_lower = filename.lower()
                        # Skip files created in current session (race condition fix)
                        if filename_lower in exclude_filenames:
                            continue
                        
                        if filename_lower not in all_clip_paths:
                            # WAV file exists on disk but not referenced in laughter_detections - true orphan
                            _verbose_log(
                                f"⚠️ 🗑️ CLEANUP: Deleting orphaned WAV clip (user folder): {filename}"
                            )
                            await self._delete_audio_file(file_path, user_id)
                            disk_files_cleaned += 1

            total_cleaned = db_files_cleaned + disk_files_cleaned

            if total_cleaned > 0:
                _verbose_log(f"🧹 CLEANUP: Deleted {total_cleaned} orphaned file(s)")

        except Exception as e:
            print(f"❌ Error in orphan cleanup: {str(e)}")
            # Silent success if no orphans found - don't clutter logs

        except Exception as e:
            print(f"❌ Error in orphan cleanup: {str(e)}")

    async def _mark_segment_processed(self, segment_id: str):
        """Mark audio segment as processed."""
        try:
            supabase = self._get_service_client()

            supabase.table("audio_segments").update({"processed": True}).eq(
                "id", segment_id
            ).execute()

        except Exception as e:
            print(f"❌ Error marking segment as processed: {str(e)}")

    async def reprocess_date_range(
        self,
        user_id: str,
        start_date_str: str,
        end_date_str: str,
        trigger_type: str = "manual",
    ):
        """
        Reprocess audio data for a date range with cleanup and enhanced logging.
        
        REFACTORING (2025-11-20): This method consolidates reprocessing logic that was
        previously duplicated between API endpoints and CLI scripts. It handles:
        1. Cleanup of existing data (database records and disk files)
        2. Reprocessing using shared scheduler code path
        3. Enhanced logging for audit trail
        4. Orphan cleanup after processing
        
        Args:
            user_id: User ID to reprocess for
            start_date_str: Start date in YYYY-MM-DD format (interpreted in user's timezone)
            end_date_str: End date in YYYY-MM-DD format (interpreted in user's timezone)
            trigger_type: Type of trigger ('manual', 'scheduled', 'cron')
        
        Returns:
            Dict with processing summary (segments_processed, chunks_processed, etc.)
        
        Called by:
            - API endpoint: /reprocess-date-range
            - CLI script: manual_reprocess_yesterday.py (can be refactored to use this)
        
        REFACTORING BENEFITS:
        - Single code path for all reprocessing (API, CLI, future scheduled)
        - Consistent logging and error handling
        - Easier to maintain and test
        - Ensures all reprocessing uses enhanced_logger
        """
        try:
            from datetime import date
            import sys
            from pathlib import Path
            
            # Import cleanup functions from manual_reprocess_yesterday (reuse existing code)
            maintenance_dir = Path(__file__).resolve().parents[2] / "scripts" / "maintenance"
            maintenance_path = str(maintenance_dir)
            if maintenance_path not in sys.path:
                sys.path.insert(0, maintenance_path)
            
            from maintenance.manual_reprocess_yesterday import (
                clear_database_records,
                clear_disk_files,
            )
            
            # Get user's timezone
            supabase = self._get_service_client()
            user_result = (
                supabase.table("users")
                .select("timezone")
                .eq("id", user_id)
                .execute()
            )
            timezone = (
                user_result.data[0].get("timezone", "UTC")
                if user_result.data
                else "UTC"
            )
            user_tz = pytz.timezone(timezone)
            
            # Parse dates in user's timezone
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            start_time = user_tz.localize(start_date.replace(hour=0, minute=0, second=0, microsecond=0))
            end_time = user_tz.localize(end_date.replace(hour=23, minute=59, second=59, microsecond=999999))
            
            # Convert to UTC for processing
            start_utc = start_time.astimezone(pytz.UTC)
            end_utc = end_time.astimezone(pytz.UTC)
            
            print(f"\n📅 Reprocessing date range:")
            print(f"   From: {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"   To: {end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"   User ID: {user_id[:8]}...\n")
            
            # Step 1: Cleanup disk files FIRST (reads paths from database before deleting records)
            await clear_disk_files(user_id, start_utc, end_utc, supabase)
            
            # Step 2: Cleanup database records (after files are deleted)
            await clear_database_records(user_id, start_utc, end_utc, supabase)
            
            # Step 3: Get API key
            try:
                api_key = fetch_decrypted_limitless_key(user_id, supabase=supabase)
            except LimitlessKeyError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No Limitless API key found for user: {exc}",
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to decrypt API key: {exc}",
                )
            
            # Step 4: Process date range with enhanced logging
            # Create separate logs for each day in the date range
            current_date = None
            enhanced_logger = None
            chunk_count = 0
            total_segments = 0
            all_stored_clip_paths = set()
            
            from .enhanced_logger import get_enhanced_logger
            
            for chunk_count, (chunk_start, chunk_end) in enumerate(
                generate_time_chunks(start_utc, end_utc, chunk_minutes=DEFAULT_CHUNK_MINUTES),
                start=1,
            ):
                # Check if we've crossed into a new day - create new logger if needed
                chunk_date = chunk_start.date()
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
                        user_id, trigger_type, process_date=current_date
                    )
                    print(f"\n📅 Processing date: {current_date.isoformat()}")
                
                print(
                    f"\n📦 Processing chunk {chunk_count}: {chunk_start.strftime('%Y-%m-%d %H:%M:%S UTC')} to {chunk_end.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                )
                
                # Process this chunk
                processed, chunk_clip_paths = await self._process_date_range(
                    user_id, api_key, chunk_start, chunk_end
                )
                total_segments += processed
                all_stored_clip_paths.update(chunk_clip_paths)
                
                _verbose_log(f"  ✅ Processed {processed} segment(s) in this chunk")
            
            # Save final day's log
            if enhanced_logger and current_date:
                await enhanced_logger.save_to_database(
                    "completed",
                    f"Manual reprocessing completed for {current_date.isoformat()}",
                )
                enhanced_logger.log_processing_summary()
            
            # Step 5: Orphan cleanup (exclude files created in this session)
            try:
                now_utc = datetime.utcnow()
                start_window = now_utc - timedelta(days=2)
                await self._cleanup_orphaned_files(
                    user_id, start_window, now_utc, exclude_clip_paths=all_stored_clip_paths
                )
                print("🧹 Orphan cleanup completed")
            except Exception as cleanup_err:
                print(f"⚠️ Orphan cleanup failed (non-fatal): {str(cleanup_err)}")
            
            print("\n" + "=" * 60)
            print(f"✅ Reprocessing complete!")
            print(f"   Processed {chunk_count} chunk(s) across {len(set([start_utc.date(), end_utc.date()]))} day(s)")
            print(f"   Total segments processed: {total_segments}")
            print("=" * 60 + "\n")
            
            return {
                "message": "Reprocessing completed successfully",
                "start_date": start_date_str,
                "end_date": end_date_str,
                "chunks_processed": chunk_count,
                "segments_processed": total_segments,
                "status": "completed",
            }
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Error during reprocessing: {str(e)}")
            import traceback
            print(f"❌ {traceback.format_exc()}")
            # Save error log for current day if logger exists
            if 'enhanced_logger' in locals() and enhanced_logger and 'current_date' in locals() and current_date:
                enhanced_logger.add_error("reprocessing_failed", str(e))
                await enhanced_logger.save_to_database(
                    "failed", f"Manual reprocessing failed: {str(e)}"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to reprocess date range: {str(e)}",
            )


# Global scheduler instance
scheduler = Scheduler()
