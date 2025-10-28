"""
Background processing scheduler for nightly audio processing.

This module handles scheduled tasks including nightly audio processing,
cleanup operations, and maintenance tasks.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional
import pytz

from ..config.settings import settings
from ..services.limitless_api import limitless_api_service
from ..services.yamnet_processor import yamnet_processor
from ..auth.encryption import encryption_service

logger = logging.getLogger(__name__)


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
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        logger.info("Starting background scheduler")
        
        # Start background tasks (removed cleanup loop - not needed)
        tasks = [
            asyncio.create_task(self._daily_processing_loop()),
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Scheduler error: {str(e)}")
        finally:
            self.running = False
    
    async def stop(self):
        """Stop the background scheduler."""
        self.running = False
        logger.info("Stopping background scheduler")
    
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
                logger.error(f"Daily processing loop error: {str(e)}")
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
        logger.info(f"Waiting {wait_seconds} seconds until next processing time")
        
        await asyncio.sleep(wait_seconds)
    
    async def _process_daily_audio(self):
        """Process daily audio for all active users."""
        logger.info("Starting daily audio processing")
        
        try:
            # Get all users with active Limitless keys
            active_users = await self._get_active_users()
            
            for user in active_users:
                try:
                    await self._process_user_audio(user)
                except Exception as e:
                    logger.error(f"Error processing audio for user {user['user_id']}: {str(e)}")
                    continue
            
            logger.info("Daily audio processing completed")
            
        except Exception as e:
            logger.error(f"Daily audio processing failed: {str(e)}")
    
    async def _process_user_audio(self, user: dict):
        """Process audio for a specific user."""
        user_id = user["user_id"]
        logger.info(f"Processing audio for user {user_id}")
        
        try:
            # Create processing log entry
            await self._create_processing_log(user_id, "processing", "Starting audio processing")
            
            # Get encrypted API key
            encrypted_api_key = await self._get_user_limitless_key(user_id)
            if not encrypted_api_key:
                logger.warning(f"No Limitless API key found for user {user_id}")
                await self._create_processing_log(user_id, "failed", "No Limitless API key found")
                return
            
            # Decrypt API key
            api_key = encryption_service.decrypt(
                encrypted_api_key,
                associated_data=user_id.encode('utf-8')
            )
            
            # Calculate date range (process full day in 2-hour chunks)
            now = datetime.now(pytz.timezone(user.get('timezone', 'UTC')))
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)  # Start of day
            
            # Process the full day in 2-hour chunks
            current_time = start_of_day
            chunk_count = 0
            while current_time < now:
                chunk_end = min(current_time + timedelta(hours=2), now)
                logger.info(f"Processing chunk {chunk_count + 1}: {current_time} to {chunk_end}")
                await self._process_date_range(user_id, api_key, current_time, chunk_end)
                current_time = chunk_end
                chunk_count += 1
            
            logger.info(f"Processed {chunk_count} chunks for user {user_id}")
            
            # Update processing log to completed
            await self._create_processing_log(user_id, "completed", "Audio processing completed successfully")
            
        except Exception as e:
            logger.error(f"Error processing user audio: {str(e)}")
            await self._create_processing_log(user_id, "failed", f"Processing failed: {str(e)}")
    
    async def _process_date_range(self, user_id: str, api_key: str, start_time: datetime, end_time: datetime):
        """Process audio for a specific date range."""
        try:
            # Get audio segments from Limitless API
            segments = await limitless_api_service.get_audio_segments(
                api_key, start_time, end_time, user_id
            )
            
            if not segments:
                logger.info(f"No audio segments found for user {user_id} from {start_time} to {end_time}")
                return
            
            # Process each segment, checking for duplicates
            for segment in segments:
                # Check if this specific segment already exists and is processed
                if await self._segment_already_processed(user_id, segment):
                    # Get file_path for logging (handle both dict and object formats)
                    file_path = segment['file_path'] if isinstance(segment, dict) else segment.file_path
                    logger.info(f"Segment with file {os.path.basename(file_path)} already processed for user {user_id}")
                    continue
                
                # Store the segment in the database first
                segment_id = await self._store_audio_segment(user_id, segment)
                if segment_id:
                    # Process the audio segment
                    await self._process_audio_segment(user_id, segment, segment_id)
            
        except Exception as e:
            logger.error(f"Error processing date range: {str(e)}")
    
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
                logger.error("Supabase credentials not found")
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
                logger.info(f"Stored audio segment {segment_id} in database")
                return segment_id
            else:
                logger.error(f"Failed to store audio segment {segment_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error storing audio segment: {str(e)}")
            return None

    async def _process_audio_segment(self, user_id: str, segment, segment_id: str):
        """Process a single audio segment for laughter detection."""
        try:
            # Handle both dict and object formats
            if isinstance(segment, dict):
                file_path = segment['file_path']
            else:
                file_path = segment.file_path
            
            # Run YAMNet processing on actual audio file
            laughter_events = await yamnet_processor.process_audio_file(
                file_path, user_id
            )
            
            if laughter_events:
                # Store laughter detection results
                await self._store_laughter_detections(user_id, segment_id, laughter_events)
            
            # Mark segment as processed
            await self._mark_segment_processed(segment_id)
            
            # SECURITY: Delete the audio file after processing (as per requirements)
            await self._delete_audio_file(file_path, user_id)
            
        except Exception as e:
            logger.error(f"Error processing audio segment: {str(e)}")
    
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
            logger.error(f"Error getting active users: {str(e)}")
            return []
    
    async def _create_processing_log(self, user_id: str, status: str, message: str):
        """Create or update processing log entry."""
        try:
            import os
            from dotenv import load_dotenv
            from supabase import create_client, Client
            from datetime import date
            
            # Load environment variables
            load_dotenv()
            
            # Use service role key for admin operations
            SUPABASE_URL = os.getenv('SUPABASE_URL')
            SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
                logger.error("Supabase credentials not found")
                return
            
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            
            # Check if log entry exists for today
            today = date.today()
            existing_logs = supabase.table('processing_logs').select('*').eq('user_id', user_id).eq('date', today.isoformat()).execute().data
            
            if existing_logs:
                # Update existing log
                log_id = existing_logs[0]['id']
                supabase.table('processing_logs').update({
                    'status': status,
                    'message': message,
                    'last_processed': datetime.now(pytz.UTC).isoformat()
                }).eq('id', log_id).execute()
                logger.info(f"Updated processing log for user {user_id}: {status} - {message}")
            else:
                # Create new log entry
                supabase.table('processing_logs').insert({
                    'user_id': user_id,
                    'date': today.isoformat(),
                    'status': status,
                    'message': message,
                    'processed_segments': 0,
                    'total_segments': 0,
                    'last_processed': datetime.now(pytz.UTC).isoformat()
                }).execute()
                logger.info(f"Created processing log for user {user_id}: {status} - {message}")
                
        except Exception as e:
            logger.error(f"Error creating processing log: {str(e)}")
    
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
                logger.error("Supabase credentials not found")
                return None
            
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            result = supabase.table("limitless_keys").select("encrypted_api_key").eq("user_id", user_id).eq("is_active", True).execute()
            
            if result.data:
                return result.data[0]["encrypted_api_key"]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user limitless key: {str(e)}")
            return None
    
    async def _is_time_range_processed(self, user_id: str, start_time: datetime, end_time: datetime) -> bool:
        """Check if time range has already been processed for user."""
        try:
            from ..auth.supabase_auth import auth_service
            
            result = auth_service.supabase.table("audio_segments").select("id").eq("user_id", user_id).eq("processed", True).gte("start_time", start_time.isoformat()).lte("end_time", end_time.isoformat()).execute()
            
            return len(result.data) > 0 if result.data else False
            
        except Exception as e:
            logger.error(f"Error checking if time range processed: {str(e)}")
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
            logger.error(f"Error marking time range as processed: {str(e)}")
    
    async def _store_laughter_detections(self, user_id: str, segment_id: str, laughter_events: list):
        """Store laughter detection results in database with duplicate prevention."""
        try:
            import os
            from dotenv import load_dotenv
            from supabase import create_client, Client
            from datetime import datetime, timedelta
            import pytz
            
            # Load environment variables
            load_dotenv()
            
            # Use service role key for admin operations
            SUPABASE_URL = os.getenv('SUPABASE_URL')
            SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
                logger.error("Supabase credentials not found")
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
                        segment_start = datetime.fromisoformat(segment_result.data[0]["start_time"].replace('Z', '+00:00'))
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
                time_window = timedelta(seconds=5)
                start_window = event_datetime - time_window
                end_window = event_datetime + time_window
                
                existing_detections = supabase.table("laughter_detections").select("id, timestamp").eq("user_id", user_id).gte("timestamp", start_window.isoformat()).lte("timestamp", end_window.isoformat()).execute()
                
                if existing_detections.data:
                    logger.info(f"🚫 Duplicate laughter detection prevented: {event_datetime} (similar timestamp within 5s already exists)")
                    continue  # Skip this duplicate
                
                # DUPLICATE PREVENTION: Check for existing clip path
                if event.clip_path:
                    existing_clip = supabase.table("laughter_detections").select("id").eq("clip_path", event.clip_path).execute()
                    if existing_clip.data:
                        logger.info(f"🚫 Duplicate clip path prevented: {event.clip_path}")
                        continue  # Skip this duplicate
                
                # Store the laughter detection (no duplicates found)
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
                    logger.info(f"✅ Laughter detection stored: {event_datetime} (prob: {event.probability:.3f})")
                except Exception as insert_error:
                    # Handle unique constraint violations gracefully
                    if "unique_laughter_timestamp_user" in str(insert_error) or "unique_laughter_clip_path" in str(insert_error):
                        logger.info(f"🚫 Duplicate prevented by database constraint: {event_datetime}")
                    else:
                        logger.error(f"Error inserting laughter detection: {str(insert_error)}")
            
        except Exception as e:
            logger.error(f"Error storing laughter detections: {str(e)}")
    
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
                logger.error("Supabase credentials not found")
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
                new_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                new_end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except Exception as e:
                logger.error(f"Error parsing segment times: {str(e)}")
                return False
            
            # Get all existing segments for this user
            result = supabase.table("audio_segments").select("id, start_time, end_time, processed").eq("user_id", user_id).execute()
            
            if not result.data:
                return False
            
            # Check for overlapping segments
            for existing_segment in result.data:
                try:
                    existing_start = datetime.fromisoformat(existing_segment['start_time'].replace('Z', '+00:00'))
                    existing_end = datetime.fromisoformat(existing_segment['end_time'].replace('Z', '+00:00'))
                    
                    # Check if time ranges overlap
                    # Two time ranges overlap if: start1 < end2 AND start2 < end1
                    if new_start < existing_end and existing_start < new_end:
                        logger.info(f"Found overlapping segment: {existing_segment['id']} ({existing_start} - {existing_end}) overlaps with ({new_start} - {new_end})")
                        return existing_segment['processed']
                        
                except Exception as e:
                    logger.warning(f"Error parsing existing segment times: {str(e)}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if segment already processed: {str(e)}")
            return False

    async def _delete_audio_file(self, file_path: str, user_id: str):
        """Delete audio file after processing (plaintext path, no encryption)."""
        try:
            import os
            
            # Use plaintext file path directly (no decryption needed)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"✅ Deleted audio file: {file_path}")
            else:
                logger.warning(f"⚠️ Audio file not found: {file_path}")
                
        except Exception as e:
            logger.error(f"❌ Error deleting audio file: {str(e)}")

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
                logger.error("Supabase credentials not found")
                return
            
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            
            supabase.table("audio_segments").update({
                "processed": True
            }).eq("id", segment_id).execute()
            
        except Exception as e:
            logger.error(f"Error marking segment as processed: {str(e)}")


# Global scheduler instance
scheduler = Scheduler()
