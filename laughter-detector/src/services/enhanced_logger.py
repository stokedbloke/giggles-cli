"""
Enhanced Processing Logger Service - SIMPLIFIED

Tracks only the metrics we actually need:
- processing_duration_seconds
- audio_files_downloaded
- laughter_events_found
- duplicates_skipped (with breakdown)
"""

import os
from datetime import datetime, date
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import pytz



@dataclass
class APICall:
    """Represents a Limitless API call with response details."""
    endpoint: str
    timestamp: str
    status_code: int
    duration_ms: int
    response_size_bytes: Optional[int] = None
    error: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


class EnhancedProcessingLogger:
    """
    Simplified logger that tracks only the metrics we need.
    
    No more add_step() complexity - just direct counters.
    """
    
    def __init__(self, user_id: str, trigger_type: str = "manual", process_date: Optional[date] = None):
        """Initialize logger with simple counters."""
        self.user_id = user_id
        self.trigger_type = trigger_type
        self.process_date = process_date or date.today()
        
        # Simple counters - no complex step tracking
        self.audio_files_downloaded = 0
        self.laughter_events_found = 0
        self.skipped_time_window = 0
        self.skipped_clip_path = 0
        self.skipped_missing_file = 0
        
        # Keep API calls and errors for debugging (optional)
        self.api_calls: List[APICall] = []
        self.error_details: Dict[str, Any] = {}
        
        self.start_time = datetime.now(pytz.UTC)
    
    def increment_audio_files(self):
        """Increment audio files downloaded counter."""
        self.audio_files_downloaded += 1
    
    def increment_laughter_events(self, count: int = 1):
        """Increment laughter events found counter."""
        self.laughter_events_found += count
    
    def increment_skipped_time_window(self):
        """Increment time window duplicate skip counter."""
        self.skipped_time_window += 1
    
    def increment_skipped_clip_path(self):
        """Increment clip path duplicate skip counter."""
        self.skipped_clip_path += 1
    
    def increment_skipped_missing_file(self):
        """Increment missing file skip counter."""
        self.skipped_missing_file += 1
    
    def add_api_call(self, endpoint: str, status_code: int, duration_ms: int, response_size_bytes: Optional[int] = None, error: Optional[str] = None, params: Optional[Dict[str, Any]] = None):
        """Add a Limitless API call record (for debugging)."""
        api_call = APICall(
            endpoint=endpoint,
            timestamp=datetime.now(pytz.UTC).isoformat(),
            status_code=status_code,
            duration_ms=duration_ms,
            response_size_bytes=response_size_bytes,
            error=error,
            params=params
        )
        self.api_calls.append(api_call)
        
        if status_code == 200:
            print(f"🌐 API Call: {endpoint} - SUCCESS ({status_code}) - {duration_ms}ms")
        elif status_code == 404:
            print(f"⚠️ 🌐 API Call: {endpoint} - NO DATA ({status_code}) - {duration_ms}ms")
        else:
            print(f"❌ 🌐 API Call: {endpoint} - ERROR ({status_code}) - {duration_ms}ms - {error}")
    
    def add_error(self, error_type: str, error_message: str, stack_trace: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        """Add detailed error information."""
        self.error_details[error_type] = {
            "message": error_message,
            "timestamp": datetime.now(pytz.UTC).isoformat(),
            "stack_trace": stack_trace,
            "context": context or {}
        }
        print(f"❌ ❌ Error: {error_type} - {error_message}")
    
    def get_processing_duration_seconds(self) -> int:
        """Calculate total processing duration."""
        end_time = datetime.now(pytz.UTC)
        duration = end_time - self.start_time
        return int(duration.total_seconds())
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics - now just returns counters directly."""
        return {
            "processing_duration_seconds": self.get_processing_duration_seconds(),
            "audio_files_downloaded": self.audio_files_downloaded,
            "laughter_events_found": self.laughter_events_found,
            "duplicates_skipped": self.skipped_time_window + self.skipped_clip_path + self.skipped_missing_file,
            "skipped_time_window": self.skipped_time_window,
            "skipped_clip_path": self.skipped_clip_path,
            "skipped_missing_file": self.skipped_missing_file
        }
    
    async def save_to_database(self, status: str, message: str):
        """
        Save the processing log to the database.
        
        DATABASE TABLE: processing_logs
        DATABASE UNIQUENESS: One row per (user_id, date) - updates existing row if present
        TRIGGER: Called from scheduler._process_user_audio() after processing completes (status='completed' or 'failed')
        
        DATABASE FIELDS POPULATED:
        - user_id: User ID from logger initialization
        - date: Date being processed (date.today() for Update Today, specific date for reprocess)
        - status: 'completed' or 'failed'
        - message: Human-readable status message
        - trigger_type: 'manual' (Update Today button), 'scheduled' (cron job), 'cron' (manual cron script)
        - processing_duration_seconds: Time from logger start_time to now (calculated)
        - audio_files_downloaded: Count of OGG files downloaded (incremented by limitless_api._fetch_audio_segments)
        - laughter_events_found: Total detections from YAMNet (incremented by increment_laughter_events)
        - duplicates_skipped: Sum of all skip counters (time_window + clip_path + missing_file)
        - last_processed: Current UTC timestamp
        - api_calls: JSONB array of Limitless API calls (populated by add_api_call)
        - error_details: JSONB object with error information (populated by add_error)
        """
        try:
            import os
            from dotenv import load_dotenv
            from supabase import create_client
            
            load_dotenv()
            SUPABASE_URL = os.getenv('SUPABASE_URL')
            SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
                print(f"❌ Supabase credentials not found")
                return
            
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            stats = self.get_summary_stats()
            
            # Check if log already exists for this (user_id, date) combination
            existing_logs = supabase.table('processing_logs').select('*').eq('user_id', self.user_id).eq('date', self.process_date.isoformat()).execute().data
            
            # Build log data dictionary - maps directly to processing_logs table columns
            log_data = {
                'status': status,  # 'completed' or 'failed'
                'message': message,  # Human-readable message
                'trigger_type': self.trigger_type,  # 'manual', 'scheduled', or 'cron'
                # Keep api_calls and error_details for debugging (optional)
                'api_calls': [asdict(call) for call in self.api_calls],  # JSONB array of API call objects
                'error_details': self.error_details,  # JSONB object with error information
                # Direct counters - no more processing_steps complexity
                'processing_duration_seconds': stats['processing_duration_seconds'],  # Calculated from start_time
                'audio_files_downloaded': stats['audio_files_downloaded'],  # Count from increment_audio_files()
                'laughter_events_found': stats['laughter_events_found'],  # Count from increment_laughter_events()
                'duplicates_skipped': stats['duplicates_skipped'],  # Sum of all skip counters
                'last_processed': datetime.now(pytz.UTC).isoformat()  # Current UTC timestamp
            }
            
            if existing_logs:
                log_id = existing_logs[0]['id']
                supabase.table('processing_logs').update(log_data).eq('id', log_id).execute()
                print(f"📊 Updated processing log for user {self.user_id}: {status} - {message}")
            else:
                log_data.update({
                    'user_id': self.user_id,
                    'date': self.process_date.isoformat(),
                })
                supabase.table('processing_logs').insert(log_data).execute()
                print(f"📊 Created processing log for user {self.user_id} for date {self.process_date.isoformat()}: {status} - {message}")
                
        except Exception as e:
            print(f"❌ Error saving processing log: {str(e)}")
    
    def log_processing_summary(self):
        """Log a summary of the processing session.
        
        NOTE: These counts reflect what was newly processed in THIS session, not total counts for the date.
        If segments were already fully processed, they are skipped and won't be counted here.
        """
        stats = self.get_summary_stats()
        
        print("\n" + "=" * 60)
        print("📊 PROCESSING SESSION SUMMARY")
        print("=" * 60)
        print(f"👤 User ID: {self.user_id[:8]}")
        print(f"🔧 Trigger: {self.trigger_type}")
        print(f"⏱️  Duration: {stats['processing_duration_seconds']} seconds")
        print(f"📁 Audio Files Downloaded: {stats['audio_files_downloaded']} (newly downloaded OGG files from Limitless API)")
        print(f"🎭 Laughter Events Found: {stats['laughter_events_found']} (newly detected by YAMNet in this session)")
        if stats.get('duplicates_skipped', 0) > 0:
            print(f"⏭️  Duplicates Skipped: {stats['duplicates_skipped']} laughter events (time-window: {stats.get('skipped_time_window', 0)}, clip-path: {stats.get('skipped_clip_path', 0)}, missing-file: {stats.get('skipped_missing_file', 0)})")
        
        # Note when all segments were skipped (already processed)
        if stats['audio_files_downloaded'] == 0 and stats['laughter_events_found'] == 0:
            print(f"ℹ️  All segments were already fully processed - no new files downloaded or laughter detected in this run")
        
        if self.error_details:
            print(f"❌ Errors: {len(self.error_details)}")
            for error_type, error_info in self.error_details.items():
                print(f"   - {error_type}: {error_info['message']}")
        
        print("=" * 60 + "\n")


# Global instance for easy access
enhanced_logger = None


def get_enhanced_logger(user_id: str, trigger_type: str = "manual", process_date: Optional[date] = None) -> EnhancedProcessingLogger:
    """Get or create a logger instance."""
    global enhanced_logger
    enhanced_logger = EnhancedProcessingLogger(user_id, trigger_type, process_date)
    return enhanced_logger


def get_current_logger() -> Optional[EnhancedProcessingLogger]:
    """Get the current logger instance."""
    return enhanced_logger
