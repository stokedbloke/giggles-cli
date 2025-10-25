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
import logging
import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
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
    Process current day audio directly without scheduler.
    """
    try:
        user_id = user["id"]
        logger.info(f"🎯 Processing current day audio for user {user_id}")
        
        # Get unprocessed audio segments for today
        today = datetime.now(pytz.UTC).date()
        tomorrow = today + timedelta(days=1)
        
        # Create RLS-compliant client
        supabase = create_user_supabase_client(credentials)
        
        # Get unprocessed segments for today (RLS will ensure user can only access their own)
        segments = supabase.table("audio_segments").select("*").eq("processed", False).gte("start_time", today.isoformat()).lt("start_time", tomorrow.isoformat()).execute()
        
        if not segments.data:
            logger.info("✅ No unprocessed segments for today")
            return {"status": "success", "message": "No unprocessed segments for today", "processed": 0}
        
        logger.info(f"📊 Found {len(segments.data)} unprocessed segments for today")
        
        processed_count = 0
        
        for segment in segments.data:
            try:
                segment_id = segment["id"]
                file_path = segment["file_path"]
                
                logger.info(f"🎵 Processing segment {segment_id}")
                
                # Decrypt file path
                from ..auth.encryption import encryption_service
                decrypted_path = encryption_service.decrypt(file_path)
                
                if not os.path.exists(decrypted_path):
                    logger.warning(f"⚠️  Audio file not found: {decrypted_path}")
                    continue
                
                # Run YAMNet processing
                logger.info(f"🧠 Running YAMNet on {os.path.basename(decrypted_path)}")
                laughter_events = await yamnet_processor.process_audio_file(decrypted_path, user_id)
                
                if laughter_events:
                    logger.info(f"🎭 Found {len(laughter_events)} laughter events")
                    
                    # Store laughter detections
                    for event in laughter_events:
                        try:
                            # Calculate proper timestamp
                            segment_start = datetime.fromisoformat(segment["start_time"].replace('Z', '+00:00'))
                            event_datetime = segment_start + timedelta(seconds=float(event.timestamp))
                            # Truncate microseconds to avoid PostgreSQL issues
                            event_datetime = event_datetime.replace(microsecond=0)
                            
                            # Store detection (RLS will ensure user can only insert their own)
                            supabase.table("laughter_detections").insert({
                                "user_id": user_id,
                                "audio_segment_id": segment_id,
                                "timestamp": event_datetime.isoformat(),
                                "probability": event.probability,
                                "clip_path": event.clip_path,
                                "class_id": getattr(event, 'class_id', None),
                                "class_name": getattr(event, 'class_name', None),
                                "notes": "Current day processing"
                            }).execute()
                            
                            logger.info(f"✅ Stored laughter detection: {event_datetime} (prob: {event.probability:.3f})")
                            
                        except Exception as e:
                            logger.error(f"❌ Error storing laughter detection: {str(e)}")
                            continue
                else:
                    logger.info("😴 No laughter detected in this segment")
                
                # Mark segment as processed (RLS will ensure user can only update their own)
                supabase.table("audio_segments").update({"processed": True}).eq("id", segment_id).execute()
                logger.info(f"✅ Marked segment {segment_id} as processed")
                processed_count += 1
                
            except Exception as e:
                logger.error(f"❌ Error processing segment {segment_id}: {str(e)}")
                continue
        
        logger.info(f"🎉 Processed {processed_count} segments for current day")
        return {"status": "success", "message": f"Processed {processed_count} segments", "processed": processed_count}
        
    except Exception as e:
        logger.error(f"❌ Error in current day processing: {str(e)}")
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
        logger.error(f"❌ Error getting current day status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
