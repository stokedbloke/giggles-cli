"""
Current Day Processing Routes
============================

Direct processing for current day audio without scheduler complexity.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..api.dependencies import get_current_user
from ..services.yamnet_processor import yamnet_processor
from ..auth.supabase_auth import auth_service
from supabase import create_client, Client
import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

router = APIRouter()

def create_user_supabase_client(credentials: HTTPAuthorizationCredentials) -> Client:
    """Create RLS-compliant Supabase client for user operations."""
    load_dotenv()
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
    
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=500,
            detail="Database configuration error"
        )
    
    # Create user-specific client with their JWT token (RLS will enforce user can only access their own data)
    supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    supabase.auth.set_auth(credentials.credentials)
    return supabase

@router.post("/process-current-day")
async def process_current_day(
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """
    Process current day audio with enhanced logging.
    
    ENHANCED LOGGING (2025-11-20): Now uses enhanced_logger to create processing_logs entries,
    matching the behavior of cron jobs and reprocessing. This provides:
    - Audit trail of when/why processing occurred
    - Statistics: laughter_events_found, duplicates_skipped, audio_files_downloaded
    - Consistent logging across all processing paths
    
    This endpoint processes already-downloaded audio segments (unlike cron which downloads new audio).
    It uses scheduler._store_laughter_detections() for duplicate prevention and consistent storage.
    """
    try:
        user_id = user["id"]
        print(f"🔄 Processing current day audio for user {user_id}")
        
        # ENHANCED LOGGING: Create logger for this processing run
        from ..services.enhanced_logger import get_enhanced_logger
        from datetime import date
        
        today = date.today()
        enhanced_logger = get_enhanced_logger(user_id, "manual", process_date=today)
        
        # Get unprocessed audio segments for today
        tomorrow_date = today + timedelta(days=1)
        tomorrow = datetime.combine(tomorrow_date, datetime.min.time()).replace(tzinfo=pytz.UTC)
        today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=pytz.UTC)
        
        # Create RLS-compliant client
        supabase = create_user_supabase_client(credentials)
        
        # Get unprocessed segments for today (RLS will ensure user can only access their own)
        segments = supabase.table("audio_segments").select("*").eq("processed", False).gte("start_time", today_start.isoformat()).lt("start_time", tomorrow.isoformat()).execute()
        
        if not segments.data:
            print("✅ No unprocessed segments for today")
            # Save log even if no processing occurred
            await enhanced_logger.save_to_database(
                "completed", "No unprocessed segments for today"
            )
            return {"status": "success", "message": "No unprocessed segments for today", "processed": 0}
        
        print(f"📊 Found {len(segments.data)} unprocessed segments for today")
        
        # Track metrics
        processed_count = 0
        total_laughter_events = 0
        
        # Use scheduler for storing detections (handles duplicates and logging)
        from ..services.scheduler import scheduler
        
        for segment in segments.data:
            try:
                segment_id = segment["id"]
                file_path = segment["file_path"]
                
                print(f"🔄 Processing segment {segment_id}")
                
                # Track audio file (even though it's already downloaded)
                enhanced_logger.increment_audio_files()
                
                # Decrypt file path
                from ..auth.encryption import encryption_service
                decrypted_path = encryption_service.decrypt(file_path)
                
                if not os.path.exists(decrypted_path):
                    print(f"⚠️  Audio file not found: {decrypted_path}")
                    enhanced_logger.add_error("missing_file", f"Audio file not found: {decrypted_path}")
                    continue
                
                # Run YAMNet processing
                print(f"🧠 Running YAMNet on {os.path.basename(decrypted_path)}")
                laughter_events = await yamnet_processor.process_audio_file(decrypted_path, user_id)
                
                if laughter_events:
                    print(f"🎭 Found {len(laughter_events)} laughter events")
                    total_laughter_events += len(laughter_events)
                    
                    # ENHANCED LOGGING: Track total detected (before duplicates filtered)
                    enhanced_logger.increment_laughter_events(len(laughter_events))
                    
                    # Use scheduler._store_laughter_detections() for duplicate prevention and consistent storage
                    # scheduler handles float timestamps by looking up segment start time from database
                    stored_clip_paths = await scheduler._store_laughter_detections(
                        user_id, segment_id, laughter_events
                    )
                    print(f"✅ Stored {len(stored_clip_paths)} laughter detection(s) (duplicates skipped)")
                else:
                    print("😴 No laughter detected in this segment")
                
                # Mark segment as processed (RLS will ensure user can only update their own)
                supabase.table("audio_segments").update({"processed": True}).eq("id", segment_id).execute()
                print(f"✅ Marked segment {segment_id} as processed")
                processed_count += 1
                
            except Exception as e:
                print(f"❌ Error processing segment {segment_id}: {str(e)}")
                enhanced_logger.add_error("segment_processing_failed", f"Segment {segment_id}: {str(e)}")
                continue
        
        # Save processing log to database
        await enhanced_logger.save_to_database(
            "completed", f"Processed {processed_count} segments for current day"
        )
        enhanced_logger.log_processing_summary()
        
        print(f"🎉 Processed {processed_count} segments for current day")
        return {
            "status": "success",
            "message": f"Processed {processed_count} segments",
            "processed": processed_count,
            "laughter_events_found": total_laughter_events,
        }
        
    except Exception as e:
        print(f"❌ Error in current day processing: {str(e)}")
        # Save error log if logger exists
        if 'enhanced_logger' in locals():
            enhanced_logger.add_error("processing_failed", str(e))
            await enhanced_logger.save_to_database("failed", f"Processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.get("/current-day-status")
async def get_current_day_status(
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """
    Get status of current day processing.
    """
    try:
        user_id = user["id"]
        today = datetime.now(pytz.UTC).date()
        tomorrow = today + timedelta(days=1)
        
        # Create RLS-compliant client
        supabase = create_user_supabase_client(credentials)
        
        # Get segments for today (RLS will ensure user can only access their own)
        segments = supabase.table("audio_segments").select("*").gte("start_time", today.isoformat()).lt("start_time", tomorrow.isoformat()).execute()
        
        processed = [s for s in segments.data if s['processed']]
        unprocessed = [s for s in segments.data if not s['processed']]
        
        # Get laughter detections for today (RLS will ensure user can only access their own)
        detections = supabase.table("laughter_detections").select("*").gte("timestamp", today.isoformat()).lt("timestamp", tomorrow.isoformat()).execute()
        
        return {
            "date": today.isoformat(),
            "total_segments": len(segments.data),
            "processed_segments": len(processed),
            "unprocessed_segments": len(unprocessed),
            "laughter_detections": len(detections.data),
            "status": "ready" if unprocessed else "complete"
        }
        
    except Exception as e:
        print(f"❌ Error getting current day status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
