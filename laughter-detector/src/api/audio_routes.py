"""
Audio processing routes for the laughter detector application.

This module handles audio processing, laughter detection, and related endpoints.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..auth.supabase_auth import auth_service
from ..auth.encryption import encryption_service
from ..services.limitless_api import limitless_api_service
from ..services.yamnet_processor import yamnet_processor
from .dependencies import get_current_user
from supabase import create_client, Client
import os
from dotenv import load_dotenv


# Create router
router = APIRouter()

def create_user_supabase_client(credentials: HTTPAuthorizationCredentials) -> Client:
    """Create RLS-compliant Supabase client for user operations."""
    load_dotenv()
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database configuration error"
        )
    
    # Create user-specific client with their JWT token (RLS will enforce user can only access their own data)
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabase.postgrest.auth(credentials.credentials)
    return supabase


@router.post("/process-daily-audio")
async def process_daily_audio(
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """
    Process daily audio for laughter detection.
    
    Args:
        user: Current authenticated user
        
    Returns:
        Processing results
        
    Raises:
        HTTPException: If processing fails
    """
    try:
        # Create RLS-compliant client
        supabase = create_user_supabase_client(credentials)
        
        # Get user's encrypted API key (RLS will ensure user can only access their own)
        result = supabase.table("limitless_keys").select("*").eq("is_active", True).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Limitless API key found for user"
            )
        
        # Decrypt the API key
        encrypted_key = result.data[0]["encrypted_api_key"]
        api_key = encryption_service.decrypt(encrypted_key, user["user_id"].encode('utf-8'))
        
        # Process audio for the last 2 hours (Limitless API limit)
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=2)
        
        try:
            # Get audio segments from Limitless API with timeout
            import asyncio
            segments = await asyncio.wait_for(
                limitless_api_service.get_audio_segments(
                    api_key, start_date, end_date, user["user_id"]
                ),
                timeout=30.0  # 30 second timeout
            )
        except asyncio.TimeoutError:
            return {
                "message": "Audio processing timed out - Limitless API may be slow",
                "segments_processed": 0,
                "laughter_events_found": 0,
                "status": "timeout"
            }
        except Exception as e:
            print(f"⚠️ Limitless API error: {str(e)}")
            return {
                "message": "Audio processing completed with limited data",
                "segments_processed": 0,
                "laughter_events_found": 0,
                "status": "limited"
            }
        
        # Process each segment for laughter detection
        laughter_count = 0
        for segment in segments:
            try:
                laughter_events = await yamnet_processor.process_audio_file(
                    segment.file_path, user["user_id"]
                )
                laughter_count += len(laughter_events)
            except Exception as e:
                print(f"⚠️ Error processing segment: {str(e)}")
                continue
        
        return {
            "message": "Daily audio processing completed",
            "segments_processed": len(segments),
            "laughter_events_found": laughter_count,
            "status": "success"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Error processing daily audio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process daily audio"
        )


@router.post("/trigger-nightly-processing")
async def trigger_nightly_processing(
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """
    Manually trigger nightly processing for testing with enhanced logging.
    This runs the same logic as the automated scheduler.
    
    Called when user clicks "Update Today's Count" button.
    
    Flow:
    1. Get user info (from JWT token) including timezone
    2. Initialize enhanced logging
    3. Call scheduler._process_user_audio which:
       - Calculates date range (start of today to now in user's timezone)
       - Splits into 2-hour chunks
       - For each chunk: calls Limitless API to download audio
       - Processes audio with YAMNet to detect laughter
       - Stores laughter events in database
       - Deletes OGG files after processing
    """
    try:
        from ..services.scheduler import scheduler
        from ..services.enhanced_logger import get_enhanced_logger
        import asyncio
        
        print(f"🎯 Starting nightly processing for user {user['user_id'][:8]}...")
        
        # Initialize enhanced logger for manual trigger
        # This creates detailed step-by-step logs stored in processing_logs table
        enhanced_logger = get_enhanced_logger(user["user_id"], "manual")
        
        # Set trigger type on scheduler for logging purposes
        scheduler._trigger_type = "manual"
        
        # Trigger processing for the current user with timeout
        # user["timezone"] comes from get_current_user -> users table -> timezone field
        # This determines which timezone to use for calculating "today"
        try:
            await asyncio.wait_for(
                scheduler._process_user_audio({
                    "user_id": user["user_id"],
                    "email": user.get("email", ""),
                    "timezone": user.get("timezone", "UTC")  # User's IANA timezone from DB
                }),
                timeout=300.0  # 5 minute timeout for YAMNet processing
            )
            
            print(f"✅ Nightly processing completed for user {user['user_id'][:8]}")
            
            return {
                "message": "Nightly processing triggered successfully",
                "status": "completed",
                "user_id": user["user_id"],
                "trigger_type": "manual"
            }
            
        except asyncio.TimeoutError:
            return {
                "message": "Processing timed out - Limitless API may be slow",
                "status": "timeout",
                "user_id": user["user_id"],
                "trigger_type": "manual"
            }
        
    except Exception as e:
        print(f"❌ Error triggering nightly processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger nightly processing"
        )
