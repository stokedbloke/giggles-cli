"""
Data management routes for the laughter detector application.

This module handles laughter detection data retrieval, updates, and deletion.
"""

from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from ..auth.supabase_auth import auth_service
from ..models.audio import (
    AudioSegmentResponse, 
    LaughterDetectionResponse, 
    DailyLaughterSummary,
    LaughterDetectionUpdate
)
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


@router.get("/daily-summary", response_model=List[DailyLaughterSummary])
async def get_daily_summary(
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """
    Get daily laughter summary for user.
    
    Args:
        user: Current authenticated user
        
    Returns:
        List of daily laughter summaries
        
    Raises:
        HTTPException: If retrieval fails
    """
    try:
        # Create RLS-compliant client
        supabase = create_user_supabase_client(credentials)
        
        # Get audio segments grouped by date (RLS will ensure user can only access their own)
        segments_result = supabase.table("audio_segments").select(
            "id, date, processed"
        ).execute()
        
        if not segments_result.data:
            return []
        
        # Get laughter detections grouped by date (RLS will ensure user can only access their own)
        detections_result = supabase.table("laughter_detections").select(
            "*, audio_segments!inner(date, user_id)"
        ).execute()
        
        # Group by date and calculate summaries
        summaries = {}
        
        # Process audio segments
        for segment in segments_result.data:
            date = segment["date"]
            if date not in summaries:
                summaries[date] = {
                    "date": date,
                    "total_laughter_events": 0,
                    "average_probability": 0.0,
                    "audio_segments_processed": 0
                }
            
            if segment["processed"]:
                summaries[date]["audio_segments_processed"] += 1
        
        # Process laughter detections (filter out detections with wrong timestamps)
        for detection in detections_result.data:
            # Skip detections with obviously wrong timestamps (like 1969 dates)
            timestamp = detection["timestamp"]
            if timestamp and "1969" in timestamp:
                continue  # Skip detections with 1969 timestamps (broken data)
            
            date = detection["audio_segments"]["date"]
            if date not in summaries:
                summaries[date] = {
                    "date": date,
                    "total_laughter_events": 0,
                    "average_probability": 0.0,
                    "audio_segments_processed": 0
                }
            
            summaries[date]["total_laughter_events"] += 1
            summaries[date]["average_probability"] += detection["probability"]
        
        # Calculate averages and return
        summary_list = []
        for date, summary in summaries.items():
            if summary["total_laughter_events"] > 0:
                summary["average_probability"] /= summary["total_laughter_events"]
            summary_list.append(DailyLaughterSummary(**summary))
        
        return sorted(summary_list, key=lambda x: x.date, reverse=True)
        
    except Exception as e:
        logger.error(f"Error getting daily summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get daily summary"
        )


@router.get("/laughter-detections/{date}", response_model=List[LaughterDetectionResponse])
async def get_laughter_detections(
    date: str,
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """
    Get laughter detections for a specific date.
    
    Args:
        date: Date in YYYY-MM-DD format
        user: Current authenticated user
        
    Returns:
        List of laughter detection events
        
    Raises:
        HTTPException: If retrieval fails
    """
    try:
        # Create RLS-compliant client
        supabase = create_user_supabase_client(credentials)
        
        # Get laughter detections for the specified date (RLS will ensure user can only access their own)
        result = supabase.table("laughter_detections").select(
            "*, audio_segments!inner(date, user_id)"
        ).eq("audio_segments.date", date).execute()
        
        if not result.data:
            return []
        
        # Convert to response model
        detections = []
        for detection in result.data:
            detections.append(LaughterDetectionResponse(
                id=detection["id"],
                audio_segment_id=detection.get("audio_segment_id", ""),
                timestamp=detection["timestamp"],
                probability=detection["probability"],
                clip_path=detection["clip_path"],
                notes=detection["notes"],
                class_id=detection.get("class_id"),
                class_name=detection.get("class_name"),
                created_at=detection.get("created_at", "")
            ))
        
        return detections
        
    except Exception as e:
        logger.error(f"Error getting laughter detections: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get laughter detections"
        )


@router.put("/laughter-detections/{detection_id}")
async def update_laughter_detection(
    detection_id: str,
    update_data: LaughterDetectionUpdate,
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """
    Update laughter detection notes.
    
    Args:
        detection_id: Detection ID to update
        update_data: Update data
        user: Current authenticated user
        
    Returns:
        Updated detection information
        
    Raises:
        HTTPException: If update fails
    """
    try:
        # Create RLS-compliant client
        supabase = create_user_supabase_client(credentials)
        
        # Update the detection (RLS will ensure user can only update their own)
        result = supabase.table("laughter_detections").update({
            "notes": update_data.notes,
            "updated_at": datetime.now().isoformat()
        }).eq("id", detection_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Detection not found"
            )
        
        return {"message": "Detection updated successfully"}
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating detection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update detection"
        )


@router.delete("/laughter-detections/{detection_id}")
async def delete_laughter_detection(
    detection_id: str,
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """
    Delete laughter detection and its audio clip file.
    
    Args:
        detection_id: Detection ID to delete
        user: Current authenticated user
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If deletion fails
    """
    try:
        logger.info(f"🗑️ DELETE request for detection_id: {detection_id}, user_id: {user['user_id']}")
        
        # Create RLS-compliant client
        supabase = create_user_supabase_client(credentials)
        
        # First, get the clip path before deleting (RLS will ensure user can only access their own)
        logger.info(f"📋 Fetching detection record for ID: {detection_id}")
        detection_result = supabase.table("laughter_detections").select("clip_path").eq("id", detection_id).execute()
        
        logger.info(f"📋 Detection fetch result: {detection_result.data}")
        
        if not detection_result.data:
            logger.error(f"❌ Detection not found: {detection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Detection not found"
            )
        
        clip_path = detection_result.data[0]["clip_path"]
        logger.info(f"📁 Clip path (encrypted): {clip_path}")
        
        # Decrypt the file path
        from ..auth.encryption import encryption_service
        try:
            decrypted_path = encryption_service.decrypt(clip_path)
            logger.info(f"🔓 Decrypted path: {decrypted_path}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to decrypt clip path {clip_path}: {str(e)}")
            decrypted_path = None
        
        # Delete the audio clip file if it exists
        if decrypted_path:
            import os
            if os.path.exists(decrypted_path):
                try:
                    os.remove(decrypted_path)
                    logger.info(f"✅ Deleted audio clip: {decrypted_path}")
                except Exception as e:
                    logger.error(f"❌ Failed to delete audio clip {decrypted_path}: {str(e)}")
            else:
                logger.warning(f"⚠️ Audio clip file not found: {decrypted_path}")
        
        # Delete the detection from the database (RLS will ensure user can only delete their own)
        logger.info(f"🗑️ Attempting database deletion for detection_id: {detection_id}")
        result = supabase.table("laughter_detections").delete().eq("id", detection_id).execute()
        
        logger.info(f"🗑️ Database deletion result: {result.data}")
        
        if not result.data:
            logger.error(f"❌ No data returned from database delete for detection_id: {detection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Detection not found or already deleted"
            )
        
        logger.info(f"✅ Successfully deleted detection {detection_id}")
        return {"message": "Detection deleted successfully"}
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting detection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete detection"
        )


@router.get("/audio-clips/{clip_id}")
async def get_audio_clip(
    clip_id: str,
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """
    Get audio clip file.
    
    Args:
        clip_id: Clip ID
        user: Current authenticated user
        
    Returns:
        Audio clip file
        
    Raises:
        HTTPException: If retrieval fails
    """
    try:
        # Create RLS-compliant client
        supabase = create_user_supabase_client(credentials)
        
        # Get the clip path from the detection (RLS will ensure user can only access their own)
        result = supabase.table("laughter_detections").select("clip_path").eq("id", clip_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audio clip not found"
            )
        
        clip_path = result.data[0]["clip_path"]
        
        # Decrypt the file path
        from ..auth.encryption import encryption_service
        decrypted_path = encryption_service.decrypt(clip_path)
        
        # Return the audio file
        from fastapi.responses import FileResponse
        return FileResponse(decrypted_path, media_type="audio/wav")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting audio clip: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get audio clip"
        )


@router.delete("/user-data")
async def delete_user_data(
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """
    Delete user audio and laughter data (preserves API key).
    
    Args:
        user: Current authenticated user
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If deletion fails
    """
    try:
        # Delete only audio and laughter data (NOT the API key)
        # Use the user's JWT token to create an RLS-compliant client
        from supabase import create_client, Client
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_KEY = os.getenv('SUPABASE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database configuration error"
            )
        
        # Create user-specific client with their JWT token (RLS will enforce user can only delete their own data)
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Set the user's JWT token for RLS context
        supabase.postgrest.auth(credentials.credentials)
        
        # Delete laughter detections (RLS will ensure user can only delete their own)
        # Need a WHERE clause - RLS policies will limit to the user's own data
        laughter_result = supabase.table("laughter_detections").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        logger.info(f"Deleted {len(laughter_result.data)} laughter detections")
        
        # Delete audio segments (RLS will ensure user can only delete their own)
        # Need a WHERE clause - RLS policies will limit to the user's own data
        segments_result = supabase.table("audio_segments").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        logger.info(f"Deleted {len(segments_result.data)} audio segments")
        
        # Also clean up orphaned files
        import os
        import shutil
        from pathlib import Path
        
        # Clean up all audio files (they're not user-specific)
        audio_dir = Path("uploads/audio")
        if audio_dir.exists():
            shutil.rmtree(audio_dir)
            audio_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Cleaned up all audio files")
        
        # Clean up all laughter clips (they're not user-specific)
        clips_dir = Path("uploads/clips")
        if clips_dir.exists():
            shutil.rmtree(clips_dir)
            clips_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Cleaned up all laughter clips")
        
        return {"message": "User data deleted successfully (API key preserved)"}
        
    except Exception as e:
        logger.error(f"Error deleting user data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user data"
        )
