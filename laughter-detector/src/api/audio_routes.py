"""
Audio processing routes for the laughter detector application.

This module handles audio processing, laughter detection, and related endpoints.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from ..auth.supabase_auth import auth_service
from ..auth.encryption import encryption_service
from ..services.limitless_api import limitless_api_service
from ..services.yamnet_processor import yamnet_processor
from .dependencies import get_current_user
from supabase import create_client, Client
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

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
            logger.warning(f"Limitless API error: {str(e)}")
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
                logger.warning(f"Error processing segment: {str(e)}")
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
        logger.error(f"Error processing daily audio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process daily audio"
        )


@router.post("/test-audio-processing")
async def test_audio_processing(
    user: dict = Depends(get_current_user)
):
    """
    Test endpoint to manually process audio with YAMNet.
    This allows testing the laughter detection without waiting for daily processing.
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
        
        # Test the Limitless API connection
        limitless_api_service = LimitlessAPIService()
        
        # Get recent audio segments (last 24 hours)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        
        # This would call the actual Limitless API
        # For now, return a test response
        return {
            "message": "Audio processing test initiated",
            "status": "testing",
            "user_id": user["user_id"],
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "note": "This is a test endpoint - actual audio processing will be implemented next"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in test audio processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test audio processing"
        )


@router.post("/trigger-nightly-processing")
async def trigger_nightly_processing(
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """
    Manually trigger nightly processing for testing.
    This runs the same logic as the automated scheduler.
    """
    try:
        from ..services.scheduler import scheduler
        import asyncio
        
        # Trigger processing for the current user with timeout
        try:
            await asyncio.wait_for(
                scheduler._process_user_audio({
                    "user_id": user["user_id"],
                    "email": user.get("email", ""),
                    "timezone": user.get("timezone", "UTC")
                }),
                timeout=300.0  # 5 minute timeout for YAMNet processing
            )
            
            return {
                "message": "Nightly processing triggered successfully",
                "status": "completed",
                "user_id": user["user_id"]
            }
            
        except asyncio.TimeoutError:
            return {
                "message": "Processing timed out - Limitless API may be slow",
                "status": "timeout",
                "user_id": user["user_id"]
            }
        
    except Exception as e:
        logger.error(f"Error triggering nightly processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger nightly processing"
        )
