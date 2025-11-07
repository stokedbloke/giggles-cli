"""
Background processing scheduler for nightly audio processing.

This module handles scheduled tasks including nightly audio processing,
cleanup operations, and maintenance tasks.
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Optional
import pytz

from ..config.settings import settings
from ..services.limitless_api import limitless_api_service
from ..services.yamnet_processor import yamnet_processor
from ..auth.encryption import encryption_service


def _norm_iso(ts: str) -> str:
    """Normalize ISO timestamp microseconds to 6 digits."""
    if '.' in ts:
        main, rest = ts.split('.', 1)
        us_part, tz_part = (rest.split('+', 1) + [''])[:2] if '+' in rest else (rest, '')
        us_part = us_part.rstrip('Z')
        us_part = (us_part + '000000')[:6]
        return f"{main}.{us_part}" + (f"+{tz_part}" if tz_part else '')
    return ts


class Scheduler:
    """Service for managing background processing tasks."""
    
    def __init__(self):
        """Initialize the scheduler."""
        self.running = False
        self.cleanup_interval = settings.cleanup_interval
        self.processing_time = "02:00"  # 2 AM daily processing
    
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
                    print(f"❌ Error processing audio for user {user['user_id']}: {str(e)}")
                    continue
            
            
        except Exception as e:
            print(f"❌ Daily audio processing failed: {str(e)}")
    
    async def _process_user_audio(self, user: dict):
        """
        Process audio for a specific user with enhanced logging.
        
        This is the main entry point for processing a user's audio. It handles:
        - Incremental processing (resumes from last processed timestamp)
        - Timezone-aware date range calculation
        - 30-minute chunk processing (prevents OOM on 2GB VPS)
        - Enhanced logging for database tracking
        
        Args:
            user: User dictionary with user_id, email, and timezone fields
            
        Called by:
            - "Update Today's Count" button (via current_day_routes.py)
            - Manual reprocessing (via manual_reprocess_yesterday.py)
            - Future: Scheduled daily processing (if scheduler.start() is enabled)
        """
        user_id = user["user_id"]
        trigger_type = getattr(self, '_trigger_type', 'manual')  # Default to manual for backward compatibility
        
        # Initialize enhanced logger - for scheduled/Update Today processing, always use today's date
        # For reprocessing, process_date is set by caller (manual_reprocess_yesterday)
        # The enhanced logger tracks API calls, laughter events, duplicates, and saves to processing_logs table
        from .enhanced_logger import get_enhanced_logger
        from datetime import date
        enhanced_logger = get_enhanced_logger(user_id, trigger_type, process_date=date.today())
        
        
        try:
            # Get encrypted API key
            encrypted_api_key = await self._get_user_limitless_key(user_id)
            if not encrypted_api_key:
                print(f"⚠️ No Limitless API key found for user {user_id}")
                enhanced_logger.add_error("no_api_key", "No Limitless API key found for user")
                await enhanced_logger.save_to_database("failed", "No Limitless API key found")
                return
            
            # Decrypt API key
            api_key = encryption_service.decrypt(
                encrypted_api_key,
                associated_data=user_id.encode('utf-8')
            )
            
            # Calculate date range (process full day in 2-hour chunks)
            # Uses user's timezone from database to determine "today" boundaries
            now = datetime.now(pytz.timezone(user.get('timezone', 'UTC')))
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)  # Start of day
            
            # CRITICAL FIX: Check if we already processed today - start from latest timestamp
            # Implements requirement: "only retrieve audio after the latest timestamp of audio retrieved"
            # Convert start_of_day to UTC for comparison with DB timestamps
            start_of_day_utc = start_of_day.astimezone(pytz.UTC)
            print(f"🔍 Checking for already processed audio today (from {start_of_day_utc.strftime('%Y-%m-%d %H:%M')} UTC / {start_of_day.strftime('%Y-%m-%d %H:%M')} {user.get('timezone', 'UTC')})")
            # Convert now to UTC for API calls (Limitless uses UTC)
            now_utc = now.astimezone(pytz.UTC)
            
            latest_processed = await self._get_latest_processed_timestamp(user_id, start_of_day_utc)
            print(f"🔍 Latest processed timestamp (UTC): {latest_processed.strftime('%Y-%m-%d %H:%M')}")
            
            # Cap latest_processed at now_utc to handle data from "future" dates due to timezone issues
            if latest_processed > now_utc:
                print(f"⚠️ Latest processed ({latest_processed.strftime('%Y-%m-%d %H:%M')}) is in future relative to now ({now_utc.strftime('%Y-%m-%d %H:%M')}), capping to now")
                latest_processed = now_utc
            
            start_time = latest_processed if latest_processed > start_of_day_utc else start_of_day_utc
            
            if latest_processed > start_of_day_utc:
                latest_in_user_tz = latest_processed.astimezone(pytz.timezone(user.get('timezone', 'UTC')))
                print(f"⏩ Resuming from last processed time: {latest_in_user_tz.strftime('%Y-%m-%d %H:%M')} {user.get('timezone', 'UTC')} / {latest_processed.strftime('%Y-%m-%d %H:%M')} UTC")
            else:
                print(f"🆕 Starting fresh from beginning of day")
            
            print(f"📊 Processing range (UTC): {start_time.strftime('%Y-%m-%d %H:%M')} to {now_utc.strftime('%Y-%m-%d %H:%M')}")
            
            # Process the full day in 30-minute chunks
            # Each chunk downloads one OGG file from Limitless API
            # CRITICAL: 30-minute chunks prevent OOM kills on 2GB VPS
            # 48 chunks per day (24 hours / 0.5 hours) ensures all data is processed
            # total_segments_processed = count of NEW segments stored (skips duplicates)
            current_time = start_time  # Start from latest processed time, not midnight
            chunk_count = 0
            total_segments_processed = 0
            
            while current_time < now_utc:
                chunk_end = min(current_time + timedelta(minutes=30), now_utc)
                print(f"📦 Processing chunk {chunk_count + 1}: {current_time.strftime('%H:%M')} UTC to {chunk_end.strftime('%H:%M')} UTC")
                
                segments_processed = await self._process_date_range(user_id, api_key, current_time, chunk_end)
                total_segments_processed += segments_processed
                
                current_time = chunk_end
                chunk_count += 1
            
            
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
            await enhanced_logger.save_to_database("completed", "Audio processing completed successfully")
            
            # Log processing summary to console
            enhanced_logger.log_processing_summary()
            
            # Final orphan cleanup - run ONCE after all chunks are processed
            # Cleans up OGG files older than 2 days that have no references
            # NOTE: Cleanup runs silently in background - check enhanced logger for summary
            now_utc = datetime.utcnow()
            start_window = now_utc - timedelta(days=2)
            await self._cleanup_orphaned_files(user_id, start_window, now_utc)
            
        except Exception as e:
            print(f"❌ Error processing user audio: {str(e)}")
            enhanced_logger.add_error("processing_failed", str(e), context={"user_id": user_id})
            await enhanced_logger.save_to_database("failed", f"Processing failed: {str(e)}")
            enhanced_logger.log_processing_summary()
    
    async def _process_date_range(self, user_id: str, api_key: str, start_time: datetime, end_time: datetime) -> int:
        """
        Process audio for a specific date range with enhanced logging.
        
        This method orchestrates the processing of a single 30-minute chunk:
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
            Number of NEW segments processed and stored (excludes duplicates)
            
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
                print(f"⏭️  SKIPPED (already fully processed): Time range {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')} UTC - Already processed, skipping download")
                return 0
            
            # Get audio segments from Limitless API
            segments = await limitless_api_service.get_audio_segments(
                api_key, start_time, end_time, user_id
            )
            
            if not segments:
                return 0
            
            # Process each segment, checking for duplicates
            # CRITICAL: Process ONE file at a time with memory cleanup between files
            # This prevents OOM kills on 2GB VPS by ensuring memory is freed before next file
            processed_count = 0
            for segment in segments:
                # Get file_path for logging (handle both dict and object formats)
                file_path = segment['file_path'] if isinstance(segment, dict) else segment.file_path
                
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
                    # CRITICAL: Check file size before processing to prevent OOM
                    import os
                    if os.path.exists(file_path):
                        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                        if file_size_mb > 50:
                            print(f"⚠️ ⚠️ SKIPPING file {os.path.basename(file_path)}: too large ({file_size_mb:.1f}MB) for 2GB VPS")
                            # Delete the file immediately to prevent disk buildup
                            await self._delete_audio_file(file_path, user_id)
                            continue
                    
                    # Process the audio segment
                    try:
                        await self._process_audio_segment(user_id, segment, segment_id)
                        processed_count += 1
                    except Exception as process_error:
                        # If processing fails, delete file immediately
                        print(f"⚠️ Processing failed, deleting file: {os.path.basename(file_path)}")
                        await self._delete_audio_file(file_path, user_id)
                        raise  # Re-raise to be caught by outer handler
                    
                    # CRITICAL: Add delay between files to allow memory cleanup
                    # This gives TensorFlow and Python GC time to free memory before next file
                    import asyncio
                    await asyncio.sleep(5)  # Increased to 5 seconds for better memory cleanup
            
            # Already handled by run-once guard earlier; keep end-of-chunk cleanup disabled
            
            return processed_count
            
        except Exception as e:
            print(f"❌ Error processing date range: {str(e)}")
            # Get current logger if available (may be None if not in processing context)
            from .enhanced_logger import get_current_logger
            enhanced_logger = get_current_logger()
            if enhanced_logger:
                enhanced_logger.add_error("date_range_error", str(e), 
                    context={"start_time": start_time.isoformat(), "end_time": end_time.isoformat()})
            return 0
    
    async def _store_audio_segment(self, user_id: str, segment) -> Optional[str]:
        """Store audio segment in database."""
        try:
            import os
            from dotenv import load_dotenv
            from supabase import create_client, Client
            import uuid
            
            # Load environment variables
            load_dotenv()
            
            # Use service role key for admin operations
            SUPABASE_URL = os.getenv('SUPABASE_URL')
            SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
                print(f"❌ Supabase credentials not found")
                return None
            
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            
            # Generate UUID for the segment
            segment_id = str(uuid.uuid4())
            
            # Handle both dict and object formats
            if isinstance(segment, dict):
                date = segment['date']
                start_time = segment['start_time']
                end_time = segment['end_time']
                file_path = segment['file_path']
            else:
                date = segment.date.isoformat() if hasattr(segment.date, 'isoformat') else segment.date
                start_time = segment.start_time.isoformat() if hasattr(segment.start_time, 'isoformat') else segment.start_time
                end_time = segment.end_time.isoformat() if hasattr(segment.end_time, 'isoformat') else segment.end_time
                file_path = segment.file_path
            
            # Insert audio segment into database
            result = supabase.table("audio_segments").insert({
                "id": segment_id,
                "user_id": user_id,
                "date": date,
                "start_time": start_time,
                "end_time": end_time,
                "file_path": file_path,
                "processed": False
            }).execute()
            
            if result.data:
                return segment_id
            else:
                print(f"❌ Failed to store audio segment {segment_id}")
                return None
                
        except Exception as e:
            print(f"❌ Error storing audio segment: {str(e)}")
            return None

    async def _process_audio_segment(self, user_id: str, segment, segment_id: str):
        """Process a single audio segment for laughter detection."""
        # Extract file_path FIRST so it's always available for cleanup
        if isinstance(segment, dict):
            file_path = segment['file_path']
        else:
            file_path = segment.file_path
        
        try:
            # Run YAMNet processing on actual audio file
            laughter_events = await yamnet_processor.process_audio_file(
                file_path, user_id
            )
            
            # Track laughter events found for database logging
            # DATABASE FIELD: This increments laughter_events_found counter which is saved to processing_logs.laughter_events_found
            # TRIGGER: Called here after YAMNet processing, before storing detections (which may skip duplicates)
            # Note: This counts ALL detections from YAMNet, even if some are later skipped as duplicates
            from .enhanced_logger import get_current_logger
            enhanced_logger = get_current_logger()
            if enhanced_logger and laughter_events:
                enhanced_logger.increment_laughter_events(len(laughter_events))
            
            if laughter_events:
                # Store laughter detection results in database with duplicate prevention
                # DATABASE WRITE: Inserts into laughter_detections table (some may be skipped as duplicates)
                # TRIGGER: enhanced_logger.increment_skipped_*() methods are called inside _store_laughter_detections()
                # for each duplicate that is skipped (time-window, clip-path, missing-file)
                await self._store_laughter_detections(user_id, segment_id, laughter_events)
            
            # Mark segment as processed
            await self._mark_segment_processed(segment_id)
            
        except Exception as e:
            print(f"❌ ❌ Error processing audio segment {segment_id}: {str(e)}")
            print(f"❌ 🔍 DEBUG: Exception type: {type(e).__name__}")
            import traceback
            print(f"❌ 🔍 DEBUG: Full traceback: {traceback.format_exc()}")
        finally:
            # ALWAYS delete the audio file after processing (success or failure)
            # This prevents disk space buildup from failed processing attempts
            # CRITICAL: This runs even if process is killed by OOM, but only if Python gets a chance
            print(f"🧹 [FINALLY] Starting cleanup for file: {os.path.basename(file_path)}")
            try:
                await self._delete_audio_file(file_path, user_id)
                print(f"🗑️ ✅ [FINALLY] Cleaned up audio file: {os.path.basename(file_path)}")
            except Exception as cleanup_error:
                print(f"⚠️ ❌ [FINALLY] Failed to cleanup file {file_path}: {str(cleanup_error)}")
                import traceback
                print(f"⚠️ [FINALLY] Cleanup error traceback: {traceback.format_exc()}")
            
            # AGGRESSIVE memory cleanup to prevent OOM kills
            # TensorFlow can hold onto memory even after clear_session()
            try:
                import tensorflow as tf
                import gc
                
                # Clear TensorFlow session
                tf.keras.backend.clear_session()
                
                # Force garbage collection multiple times
                for _ in range(3):
                    gc.collect()
                
                # Clear any cached operations
                tf.compat.v1.reset_default_graph()
                
                print(f"🧹 [FINALLY] Memory cleanup completed for {os.path.basename(file_path)}")
            except Exception as mem_error:
                print(f"⚠️ [FINALLY] Failed to clear TensorFlow memory: {str(mem_error)}")
                import traceback
                print(f"⚠️ [FINALLY] Memory cleanup error traceback: {traceback.format_exc()}")
    
    async def _get_active_users(self) -> list:
        """Get all users with active Limitless API keys."""
        try:
            from ..auth.supabase_auth import auth_service
            
            # Get all users with active Limitless API keys
            result = auth_service.supabase.table("limitless_keys").select(
                "user_id, users!inner(email, timezone)"
            ).eq("is_active", True).execute()
            
            if result.data:
                return [{
                    "user_id": row["user_id"],
                    "email": row["users"]["email"],
                    "timezone": row["users"].get("timezone", "UTC")
                } for row in result.data]
            
            return []
            
        except Exception as e:
            print(f"❌ Error getting active users: {str(e)}")
            return []
    
    # REMOVED: _create_processing_log - replaced by enhanced_logger
    
    async def _get_user_limitless_key(self, user_id: str) -> Optional[str]:
        """Get encrypted Limitless API key for user."""
        try:
            import os
            from dotenv import load_dotenv
            from supabase import create_client, Client
            
            # Load environment variables
            load_dotenv()
            
            # Use service role key for admin operations
            SUPABASE_URL = os.getenv('SUPABASE_URL')
            SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
                print(f"❌ Supabase credentials not found")
                return None
            
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            result = supabase.table("limitless_keys").select("encrypted_api_key").eq("user_id", user_id).eq("is_active", True).execute()
            
            if result.data:
                return result.data[0]["encrypted_api_key"]
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting user limitless key: {str(e)}")
            return None
    
    async def _get_latest_processed_timestamp(self, user_id: str, start_of_day: datetime) -> datetime:
        """Get the latest processed timestamp for today to enable incremental processing."""
        try:
            import os
            from dotenv import load_dotenv
            from supabase import create_client
            
            # Load environment variables
            load_dotenv()
            
            # Use service role key for admin operations
            SUPABASE_URL = os.getenv('SUPABASE_URL')
            SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
                print(f"❌ Supabase credentials not found")
                return start_of_day
            
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            
            # Query audio_segments for today's data to find latest end_time
            # This tells us what's already been downloaded from Limitless
            result = supabase.table("audio_segments").select("start_time,end_time").eq("user_id", user_id).gte("start_time", start_of_day.isoformat()).order("end_time", desc=True).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                latest_end = result.data[0]['end_time']
                latest_start = result.data[0]['start_time']
                print(f"  📋 Found latest segment: {latest_start} to {latest_end}")
                # Parse and return latest processed timestamp
                if isinstance(latest_end, str):
                    latest_dt = datetime.fromisoformat(_norm_iso(latest_end.replace('Z', '+00:00')))
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
    
    async def _is_time_range_processed(self, user_id: str, start_time: datetime, end_time: datetime) -> bool:
        """Check if time range has already been processed for user.
        
        Uses overlap detection: Two time ranges overlap if:
        (segment_start < our_end) AND (segment_end > our_start)
        
        FIX: Uses SERVICE_ROLE_KEY to bypass RLS (needed for cron context without user JWT)
        """
        try:
            import os
            from dotenv import load_dotenv
            from supabase import create_client
            import pytz
            
            # Ensure timezone-aware
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=pytz.UTC)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=pytz.UTC)
            
            # Load environment variables
            load_dotenv()
            
            # Use service role key (bypasses RLS - needed for cron context without user JWT)
            # Consistent with _get_latest_processed_timestamp() pattern
            SUPABASE_URL = os.getenv('SUPABASE_URL')
            SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
                print(f"❌ Supabase credentials not found in _is_time_range_processed")
                return False
            
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            
            # Check for any processed segments that overlap with this time range
            # Overlap condition: segment_start < our_end AND segment_end > our_start
            result = supabase.table("audio_segments").select("id").eq("user_id", user_id).eq("processed", True).lt("start_time", end_time.isoformat()).gt("end_time", start_time.isoformat()).execute()
            
            found_count = len(result.data) if result.data else 0
            if found_count > 0:
                print(f"🔍 Pre-download check: Found {found_count} processed segment(s) overlapping {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')} UTC")
            
            return found_count > 0
            
        except Exception as e:
            print(f"❌ Error checking if time range processed: {str(e)}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return False
    
    async def _mark_time_range_processed(self, user_id: str, start_time: datetime, end_time: datetime):
        """Mark time range as processed for user."""
        try:
            from ..auth.supabase_auth import auth_service
            
            # Update all audio segments for this time range to processed
            auth_service.supabase.table("audio_segments").update({
                "processed": True
            }).eq("user_id", user_id).gte("start_time", start_time.isoformat()).lte("end_time", end_time.isoformat()).execute()
            
        except Exception as e:
            print(f"❌ Error marking time range as processed: {str(e)}")
    
    async def _store_laughter_detections(self, user_id: str, segment_id: str, laughter_events: list):
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
            None (prints summary statistics)
        """
        try:
            import os
            from dotenv import load_dotenv
            from supabase import create_client, Client
            from datetime import datetime, timedelta
            import pytz
            from .enhanced_logger import get_current_logger
            
            # Track statistics
            total_detected = len(laughter_events)
            skipped_time_window = 0
            skipped_clip_path = 0
            skipped_missing_file = 0
            stored_count = 0
            
            # CRITICAL DEBUG: Entry point
            
            # Load environment variables
            load_dotenv()
            
            # Use service role key for admin operations
            SUPABASE_URL = os.getenv('SUPABASE_URL')
            SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
                print(f"❌ Supabase credentials not found")
                return
            
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            
            # Store each laughter detection event with duplicate prevention
            for event in laughter_events:
                # Convert timestamp to proper datetime
                if isinstance(event.timestamp, datetime):
                    event_datetime = event.timestamp
                else:
                    # Get the segment start time from the database
                    segment_result = supabase.table("audio_segments").select("start_time").eq("id", segment_id).execute()
                    if segment_result.data:
                        raw_start = segment_result.data[0]["start_time"].replace('Z', '+00:00')
                        segment_start = datetime.fromisoformat(_norm_iso(raw_start))
                        # Ensure timezone-aware
                        if segment_start.tzinfo is None:
                            segment_start = segment_start.replace(tzinfo=pytz.UTC)
                        # Add the event timestamp (in seconds) to the segment start time
                        if isinstance(event.timestamp, (int, float)):
                            event_datetime = segment_start + timedelta(seconds=float(event.timestamp))
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
                
                event_class_id = getattr(event, 'class_id', None)
                # Query database for existing detections in the time window
                # Selects: id, timestamp, class_id - we only need class_id to match for duplicates
                existing_detections = supabase.table("laughter_detections").select("id, timestamp, class_id").eq("user_id", user_id).gte("timestamp", start_window.isoformat()).lte("timestamp", end_window.isoformat()).execute()
                
                # Filter to only check detections with the SAME class_id (different class_ids at same timestamp are unique)
                # This matches the database constraint unique_laughter_timestamp_user_class behavior
                if existing_detections.data:
                    matching_class_detections = [
                        d for d in existing_detections.data 
                        if d.get('class_id') == event_class_id
                    ]
                    if matching_class_detections:
                        skipped_time_window += 1
                        enhanced_logger = get_current_logger()
                        if enhanced_logger:
                            enhanced_logger.increment_skipped_time_window()
                        ts_str = event_datetime.astimezone(pytz.timezone('America/Los_Angeles')).strftime('%H:%M:%S')
                        print(f"⏭️  SKIPPED (duplicate within 5s): {ts_str} prob={event.probability:.3f} - Already exists at {matching_class_detections[0]['timestamp']} (class_id={event_class_id})")
                        # Delete duplicate clip file immediately (before it gets stored in DB)
                        try:
                            if getattr(event, 'clip_path', None):
                                import os
                                # Resolve path - handle both relative and absolute paths
                                clip_path = event.clip_path
                                if not os.path.isabs(clip_path):
                                    # Relative path - resolve from project root
                                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                    clip_path = os.path.join(project_root, clip_path)
                                
                                if os.path.exists(clip_path):
                                    os.remove(clip_path)
                                    print(f"🧹 Deleted duplicate clip (time-window): {os.path.basename(event.clip_path)}")
                                else:
                                    print(f"⚠️ Duplicate clip file not found at: {clip_path}")
                        except Exception as cleanup_err:
                            print(f"⚠️ Failed to delete duplicate clip: {str(cleanup_err)}")
                        continue  # Skip this duplicate
                
                # DUPLICATE PREVENTION: Check for existing clip path
                if event.clip_path:
                    existing_clip = supabase.table("laughter_detections").select("id").eq("clip_path", event.clip_path).execute()
                    if existing_clip.data:
                        skipped_clip_path += 1
                        enhanced_logger = get_current_logger()
                        if enhanced_logger:
                            enhanced_logger.increment_skipped_clip_path()
                        ts_str = event_datetime.astimezone(pytz.timezone('America/Los_Angeles')).strftime('%H:%M:%S')
                        print(f"⏭️  SKIPPED (duplicate clip path): {ts_str} prob={event.probability:.3f} - Clip already exists: {os.path.basename(event.clip_path)}")
                        # Delete duplicate clip file immediately (before it gets stored in DB)
                        try:
                            import os
                            # Resolve path - handle both relative and absolute paths
                            clip_path = event.clip_path
                            if not os.path.isabs(clip_path):
                                # Relative path - resolve from project root
                                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                clip_path = os.path.join(project_root, clip_path)
                            
                            if os.path.exists(clip_path):
                                os.remove(clip_path)
                                print(f"🧹 Deleted duplicate clip (path): {os.path.basename(event.clip_path)}")
                            else:
                                print(f"⚠️ Duplicate clip file not found at: {clip_path}")
                        except Exception as cleanup_err:
                            print(f"⚠️ Failed to delete duplicate clip by path: {str(cleanup_err)}")
                        continue  # Skip this duplicate
                
                # Store the laughter detection (no duplicates found)
                # Only store if clip file actually exists (prevent 404s)
                clip_exists = False
                if event.clip_path:
                    clip_path = event.clip_path
                    if not os.path.isabs(clip_path):
                        # Relative path - resolve from project root
                        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        clip_path = os.path.join(project_root, clip_path)
                    clip_exists = os.path.exists(clip_path)
                if not clip_exists:
                    skipped_missing_file += 1
                    enhanced_logger = get_current_logger()
                    if enhanced_logger:
                        enhanced_logger.increment_skipped_missing_file()
                    ts_str = event_datetime.astimezone(pytz.timezone('America/Los_Angeles')).strftime('%H:%M:%S')
                    print(f"⏭️  SKIPPED (missing clip file): {ts_str} prob={event.probability:.3f} - File not found: {os.path.basename(event.clip_path) if event.clip_path else 'None'}")
                    continue
                
                # Log clip file status before database insertion
                file_size = os.path.getsize(event.clip_path) if event.clip_path else 0
                
                try:
                    supabase.table("laughter_detections").insert({
                        "user_id": user_id,
                        "audio_segment_id": segment_id,
                        "timestamp": event_datetime.isoformat(),
                        "probability": event.probability,
                        "clip_path": event.clip_path,
                        "class_id": getattr(event, 'class_id', None),
                        "class_name": getattr(event, 'class_name', None),
                        "notes": ""
                    }).execute()
                    stored_count += 1
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
                    if "unique_laughter_timestamp_user_class" in str(insert_error) or "unique_laughter_clip_path" in str(insert_error):
                        skipped_time_window += 1
                        ts_str = event_datetime.astimezone(pytz.timezone('America/Los_Angeles')).strftime('%H:%M:%S')
                        print(f"⏭️  SKIPPED (database constraint): {ts_str} prob={event.probability:.3f} - Unique constraint violation (same user_id, timestamp, AND class_id already exists)")
                        # Delete duplicate clip file immediately (database constraint caught it)
                        try:
                            import os
                            if getattr(event, 'clip_path', None):
                                # Resolve path - handle both relative and absolute paths
                                clip_path = event.clip_path
                                if not os.path.isabs(clip_path):
                                    # Relative path - resolve from project root
                                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                    clip_path = os.path.join(project_root, clip_path)
                                
                                if os.path.exists(clip_path):
                                    os.remove(clip_path)
                                    print(f"🧹 Deleted clip after constraint duplicate: {os.path.basename(event.clip_path)}")
                                else:
                                    print(f"⚠️ Duplicate clip file not found at: {clip_path}")
                        except Exception as cleanup_err:
                            print(f"⚠️ Failed to delete clip after duplicate constraint: {str(cleanup_err)}")
                    else:
                        print(f"❌ Error inserting laughter detection: {str(insert_error)}")
            
            # Summary logging - use print() for visibility with uvicorn
            # DATABASE MAPPING: These counters are aggregated by EnhancedProcessingLogger and saved to processing_logs table:
            # - total_detected -> used to calculate laughter_events_found (set via enhanced_logger.increment_laughter_events())
            # - skipped_time_window + skipped_clip_path + skipped_missing_file -> duplicates_skipped field
            # - stored_count -> actual rows inserted into laughter_detections table
            #
            # TRIGGER: enhanced_logger.increment_laughter_events(len(laughter_events)) is called from
            # _process_audio_segment() to track total detected. Skip counters are incremented above via
            # enhanced_logger.increment_skipped_*() methods which update the logger's internal counters.
            print("=" * 80)
            print(f"📊 DETECTION SUMMARY for segment {segment_id[:8]}:")
            print(f"   🎭 Total detected by YAMNet:     {total_detected}")
            print(f"   ⏭️  Skipped (time window dup):   {skipped_time_window}")
            print(f"   ⏭️  Skipped (clip path dup):      {skipped_clip_path}")
            print(f"   ⏭️  Skipped (missing file):      {skipped_missing_file}")
            print(f"   ✅ Successfully stored:           {stored_count}")
            print(f"   📉 Total skipped:                 {skipped_time_window + skipped_clip_path + skipped_missing_file}")
            print("=" * 80)
            
            # Skip counters already incremented above during the loop via enhanced_logger.increment_skipped_*() methods
            
        except Exception as e:
            print(f"❌ Error storing laughter detections: {str(e)}")
    
    async def _segment_already_processed(self, user_id: str, segment) -> bool:
        """Check if a specific segment already exists and is processed."""
        try:
            import os
            from dotenv import load_dotenv
            from supabase import create_client, Client
            from datetime import datetime
            
            # Load environment variables
            load_dotenv()
            
            # Use service role key for admin operations
            SUPABASE_URL = os.getenv('SUPABASE_URL')
            SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
                print(f"❌ Supabase credentials not found")
                return False
            
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            
            # Handle both dict and object formats
            if isinstance(segment, dict):
                start_time = segment['start_time']
                end_time = segment['end_time']
            else:
                start_time = segment.start_time.isoformat() if hasattr(segment.start_time, 'isoformat') else segment.start_time
                end_time = segment.end_time.isoformat() if hasattr(segment.end_time, 'isoformat') else segment.end_time
            
            # Parse the new segment times
            try:
                new_start = datetime.fromisoformat(_norm_iso(start_time.replace('Z', '+00:00')))
                new_end = datetime.fromisoformat(_norm_iso(end_time.replace('Z', '+00:00')))
            except Exception as e:
                print(f"❌ Error parsing segment times: {str(e)}")
                return False
            
            # Get all existing segments for this user
            result = supabase.table("audio_segments").select("id, start_time, end_time, processed").eq("user_id", user_id).execute()
            
            if not result.data:
                return False
            
            # Check for overlapping segments
            for existing_segment in result.data:
                try:
                    existing_start = datetime.fromisoformat(_norm_iso(existing_segment['start_time'].replace('Z', '+00:00')))
                    existing_end = datetime.fromisoformat(_norm_iso(existing_segment['end_time'].replace('Z', '+00:00')))
                    
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
                        seg_id = existing_segment.get('id', 'unknown')
                        # If already processed, don't reprocess
                        if existing_segment['processed']:
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
            import os
            
            if os.path.exists(file_path):
                os.remove(file_path)
            else:
                print(f"⚠️ ⚠️ Audio file not found: {file_path}")
                
        except Exception as e:
            print(f"❌ ❌ Error deleting audio file: {str(e)}")

    async def _cleanup_orphaned_files(self, user_id: str, start_time: datetime, end_time: datetime):
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
            
        Called by:
            - _process_user_audio() - once after all chunks are processed
            - Future: Could be called by scheduled cleanup job
            
        Note: This runs silently - only prints messages when files are found and deleted
        """
        try:
            import os
            from dotenv import load_dotenv
            from supabase import create_client
            
            # Load environment variables
            load_dotenv()
            
            SUPABASE_URL = os.getenv('SUPABASE_URL')
            SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
                print(f"CLEANUP: Supabase credentials not found - skipping orphan cleanup")
                return
            
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            
            # Find all processed segments for this user (check ALL processed segments)
            # This catches orphaned files from any previous run
            result = supabase.table("audio_segments").select("id, file_path, start_time, end_time").eq("user_id", user_id).eq("processed", True).execute()
            
            # Step 1: Check files from database segments
            db_files_cleaned = 0
            if result.data:
                for segment in result.data:
                    file_path = segment.get("file_path")
                    if file_path:
                        # Normalize path - remove ./ prefix if present, handle relative paths
                        normalized_path = file_path.lstrip('./')
                        # Construct full path relative to project root
                        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        full_path = os.path.join(project_root, normalized_path)
                        
                        if os.path.exists(full_path):
                            print(f"⚠️ 🗑️ CLEANUP: Deleting orphaned OGG: {os.path.basename(full_path)}")
                            await self._delete_audio_file(full_path, user_id)
                            db_files_cleaned += 1
                        elif os.path.exists(file_path):
                            # Also try original path (in case it's absolute)
                            print(f"⚠️ 🗑️ CLEANUP: Deleting orphaned OGG: {os.path.basename(file_path)}")
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
                        normalized = fp.lstrip('./')
                        all_db_paths.add(normalized.lower())  # Case-insensitive comparison
            
            # Get all clip_paths from laughter_detections table
            laughter_result = supabase.table("laughter_detections").select("clip_path").eq("user_id", user_id).execute()
            all_clip_paths = set()
            if laughter_result.data:
                for detection in laughter_result.data:
                    cp = detection.get("clip_path", "")
                    if cp:
                        # Normalize to just filename for comparison
                        clip_filename = os.path.basename(cp)
                        all_clip_paths.add(clip_filename.lower())
            
            # Scan user's audio directory for OGG files
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            user_audio_dir = os.path.join(project_root, "uploads", "audio", user_id)
            
            if os.path.exists(user_audio_dir):
                for filename in os.listdir(user_audio_dir):
                    if filename.endswith('.ogg'):
                        file_path = os.path.join(user_audio_dir, filename)
                        # Check if this file is in the database
                        relative_path = os.path.join("uploads", "audio", user_id, filename)
                        if relative_path.lower() not in all_db_paths:
                            # File exists on disk but not in database - true orphan
                            print(f"⚠️ 🗑️ CLEANUP: Deleting orphaned OGG: {filename}")
                            await self._delete_audio_file(file_path, user_id)
                            disk_files_cleaned += 1
            
            # Clean up orphaned WAV clips
            # Clips can be in two locations:
            # 1. Legacy: uploads/clips/*.wav (old format)
            # 2. Current: uploads/clips/{user_id}/*.wav (per-user folders)
            clips_dir = os.path.join(project_root, "uploads", "clips")
            if os.path.exists(clips_dir):
                # Check legacy location (direct in clips/)
                for filename in os.listdir(clips_dir):
                    if filename.endswith('.wav') and os.path.isfile(os.path.join(clips_dir, filename)):
                        file_path = os.path.join(clips_dir, filename)
                        if filename.lower() not in all_clip_paths:
                            # WAV file exists on disk but not referenced in laughter_detections - true orphan
                            print(f"⚠️ 🗑️ CLEANUP: Deleting orphaned WAV clip (legacy location): {filename}")
                            await self._delete_audio_file(file_path, user_id)
                            disk_files_cleaned += 1
                
                # Check per-user folder location
                user_clips_dir = os.path.join(clips_dir, user_id)
                if os.path.exists(user_clips_dir):
                    for filename in os.listdir(user_clips_dir):
                        if filename.endswith('.wav'):
                            file_path = os.path.join(user_clips_dir, filename)
                            if filename.lower() not in all_clip_paths:
                                # WAV file exists on disk but not referenced in laughter_detections - true orphan
                                print(f"⚠️ 🗑️ CLEANUP: Deleting orphaned WAV clip (user folder): {filename}")
                                await self._delete_audio_file(file_path, user_id)
                                disk_files_cleaned += 1
            
            total_cleaned = db_files_cleaned + disk_files_cleaned
            
            if total_cleaned > 0:
                print(f"🧹 CLEANUP: Deleted {total_cleaned} orphaned file(s)")
            
        except Exception as e:
            print(f"❌ Error in orphan cleanup: {str(e)}")
            # Silent success if no orphans found - don't clutter logs
                
        except Exception as e:
            print(f"❌ ❌ CLEANUP ERROR: Error cleaning up orphaned files: {str(e)}")
            import traceback
            print(f"❌ 🔍 CLEANUP DEBUG: Full traceback: {traceback.format_exc()}")

    async def _mark_segment_processed(self, segment_id: str):
        """Mark audio segment as processed."""
        try:
            import os
            from dotenv import load_dotenv
            from supabase import create_client, Client
            
            # Load environment variables
            load_dotenv()
            
            # Use service role key for admin operations
            SUPABASE_URL = os.getenv('SUPABASE_URL')
            SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
                print(f"❌ Supabase credentials not found")
                return
            
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            
            supabase.table("audio_segments").update({
                "processed": True
            }).eq("id", segment_id).execute()
            
        except Exception as e:
            print(f"❌ Error marking segment as processed: {str(e)}")


# Global scheduler instance
scheduler = Scheduler()
