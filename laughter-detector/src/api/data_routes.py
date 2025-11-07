"""
Data management routes for the laughter detector application.

This module handles laughter detection data retrieval, updates, and deletion.
"""

from typing import List
from datetime import datetime, timedelta
import re
import pytz
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..auth.supabase_auth import auth_service
from ..models.audio import (
    AudioSegmentResponse, 
    LaughterDetectionResponse, 
    DailyLaughterSummary,
    ReprocessDateRangeRequest,
    LaughterDetectionUpdate
)
from .dependencies import get_current_user
from supabase import create_client, Client
import os
from dotenv import load_dotenv


# Create router
router = APIRouter()

def validate_uuid(uuid_string: str) -> bool:
    """
    Validate UUID format.
    
    Args:
        uuid_string: UUID string to validate
        
    Returns:
        bool: True if valid UUID format
    """
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(uuid_string))

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
        # Get user's timezone (default to UTC if not set)
        user_timezone = user.get('timezone', 'UTC')
        user_tz = pytz.timezone(user_timezone)
        
        # Create RLS-compliant client
        supabase = create_user_supabase_client(credentials)
        
        # Get all laughter detections with timestamps (RLS will ensure user can only access their own)
        detections_result = supabase.table("laughter_detections").select(
            "id, timestamp, probability"
        ).execute()
        
        if not detections_result.data:
            return []
        
        # Group detections by date in user's timezone
        # TIMEZONE FIX: Same approach as get_laughter_detections() - convert UTC timestamps to user's timezone
        # to group by local date (ensures "Friday" shows Friday's data regardless of timezone)
        summaries = {}
        
        for detection in detections_result.data:
            # Parse UTC timestamp (database stores all timestamps in UTC)
            timestamp_utc = datetime.fromisoformat(detection["timestamp"].replace('Z', '+00:00'))
            
            # Convert to user's timezone for date grouping
            timestamp_local = timestamp_utc.astimezone(user_tz)
            
            # Get date in user's timezone (used as key for grouping)
            date = timestamp_local.strftime('%Y-%m-%d')
            
            if date not in summaries:
                summaries[date] = {
                    "date": date,
                    "total_laughter_events": 0,
                    "average_probability": 0.0,
                    "audio_segments_processed": 0
                }
            
            summaries[date]["total_laughter_events"] += 1
            summaries[date]["average_probability"] += detection["probability"]
        
        # Calculate averages
        summary_list = []
        for date, summary in summaries.items():
            if summary["total_laughter_events"] > 0:
                summary["average_probability"] /= summary["total_laughter_events"]
            summary_list.append(DailyLaughterSummary(**summary))
        
        return sorted(summary_list, key=lambda x: x.date, reverse=True)
        
    except Exception as e:
        print(f"❌ Error getting daily summary: {str(e)}")
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
    
    This endpoint retrieves all laughter detections for a given date, interpreted in the
    user's timezone. The date string is parsed as midnight in the user's timezone, then
    converted to UTC for database queries (since all timestamps are stored in UTC).
    
    TIMEZONE FIX: Previously, date boundaries were calculated in UTC, causing dates to shift
    by timezone offset (e.g., clicking "Friday" showed Thursday's data for PST users).
    The fix ensures the UI shows the correct day's data regardless of user's timezone.
    
    Args:
        date: Date in YYYY-MM-DD format (interpreted in user's timezone)
        user: Current authenticated user (contains timezone field from database)
        credentials: JWT token for RLS authentication
        
    Returns:
        List of LaughterDetectionResponse objects, sorted chronologically by timestamp
        
    Database Query:
        - Selects from laughter_detections table with timestamp filter (UTC range)
        - RLS (Row Level Security) ensures user can only access their own data
        - ORDER BY timestamp ensures chronological sorting for UI display
        
    Raises:
        HTTPException: If retrieval fails or date format is invalid
    """
    # Validate date format
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    try:
        # Get user's timezone (default to UTC if not set)
        user_timezone = user.get('timezone', 'UTC')
        
        # Create RLS-compliant client
        supabase = create_user_supabase_client(credentials)
        
        # TIMEZONE FIX: Calculate day boundaries in user's timezone
        # PROBLEM SOLVED: Previously, date boundaries were calculated in UTC, causing dates to shift
        # by timezone offset (e.g., clicking "Friday" showed Thursday's data for PST users).
        #
        # SOLUTION: Parse the date string as midnight in user's timezone, then convert to UTC for database query.
        # This ensures the UI shows the correct day's data regardless of user's timezone.
        #
        # DATABASE: All timestamps in laughter_detections table are stored in UTC (see scheduler._store_laughter_detections)
        # The conversion here ensures we query the correct UTC range for the user's local date.
        # Parse the date as midnight in user's timezone
        user_tz = pytz.timezone(user_timezone)
        start_of_day_local = user_tz.localize(datetime.strptime(date, '%Y-%m-%d'))
        end_of_day_local = start_of_day_local + timedelta(days=1)
        
        # Convert to UTC for database query (database stores all timestamps in UTC)
        start_of_day_utc = start_of_day_local.astimezone(pytz.UTC)
        end_of_day_utc = end_of_day_local.astimezone(pytz.UTC)
        
        # Get laughter detections for the specified date range in UTC
        # DATABASE QUERY: Selects from laughter_detections table with timestamp filter
        # RLS (Row Level Security) will ensure user can only access their own data
        # ORDER BY: Chronological order for UI display (fixes issue where laughs weren't sorted)
        result = supabase.table("laughter_detections").select(
            "*, audio_segments!inner(date, user_id)"
        ).gte("timestamp", start_of_day_utc.isoformat()).lt("timestamp", end_of_day_utc.isoformat()).order("timestamp").execute()
        
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
        print(f"❌ Error getting laughter detections: {str(e)}")
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
        HTTPException: If update fails or detection_id is invalid
    """
    # Validate detection_id format
    if not validate_uuid(detection_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid detection ID format"
        )
    
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
        print(f"❌ Error updating detection: {str(e)}")
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
        HTTPException: If deletion fails or detection_id is invalid
    """
    # Validate detection_id format
    if not validate_uuid(detection_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid detection ID format"
        )
    
    try:
        print(f"🗑️ DELETE request for detection_id: {detection_id}, user_id: {user['user_id']}")
        
        # Create RLS-compliant client
        supabase = create_user_supabase_client(credentials)
        
        # First, get the clip path before deleting (RLS will ensure user can only access their own)
        print(f"📋 Fetching detection record for ID: {detection_id}")
        detection_result = supabase.table("laughter_detections").select("clip_path").eq("id", detection_id).execute()
        
        print(f"📋 Detection fetch result: {detection_result.data}")
        
        if not detection_result.data:
            print(f"❌ ❌ Detection not found: {detection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Detection not found"
            )
        
        clip_path = detection_result.data[0]["clip_path"]
        print(f"📁 Clip path: {clip_path}")
        
        # Delete the audio clip file if it exists (plaintext path, no decryption needed)
        import os
        if os.path.exists(clip_path):
            try:
                os.remove(clip_path)
                print(f"✅ Deleted audio clip: {clip_path}")
            except Exception as e:
                print(f"❌ ❌ Failed to delete audio clip {clip_path}: {str(e)}")
        else:
            print(f"⚠️ ⚠️ Audio clip file not found: {clip_path}")
        
        # Delete the detection from the database (RLS will ensure user can only delete their own)
        print(f"🗑️ Attempting database deletion for detection_id: {detection_id}")
        result = supabase.table("laughter_detections").delete().eq("id", detection_id).execute()
        
        print(f"🗑️ Database deletion result: {result.data}")
        
        if not result.data:
            print(f"❌ ❌ No data returned from database delete for detection_id: {detection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Detection not found or already deleted"
            )
        
        print(f"✅ Successfully deleted detection {detection_id}")
        return {"message": "Detection deleted successfully"}
        
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Error deleting detection: {str(e)}")
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
        HTTPException: If retrieval fails or clip_id is invalid
    """
    # Validate clip_id format
    if not validate_uuid(clip_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid clip ID format"
        )
    
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
        
        # Decrypt the path if it's encrypted (for old data)
        # New data has plaintext paths, old data has encrypted paths
        try:
            from ..auth.encryption import encryption_service
            # Try to decrypt - if it fails, it's already plaintext
            clip_path = encryption_service.decrypt(clip_path)
        except:
            pass  # Already plaintext, keep as is
        
        # Convert relative path to absolute path
        if not os.path.isabs(clip_path):
            # Path is relative, make it absolute relative to the laughter-detector directory
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Go up to laughter-detector/
            clip_path = os.path.join(base_dir, clip_path.lstrip('./'))
        
        # Check if file exists
        if not os.path.exists(clip_path):
            print(f"❌ Audio file not found: {clip_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audio file not found on disk"
            )
        
        # Return the audio file
        from fastapi.responses import FileResponse
        return FileResponse(clip_path, media_type="audio/wav")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Error getting audio clip: {str(e)}")
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
        print(f"Deleted {len(laughter_result.data)} laughter detections")
        
        # Delete audio segments (RLS will ensure user can only delete their own)
        # Need a WHERE clause - RLS policies will limit to the user's own data
        segments_result = supabase.table("audio_segments").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"Deleted {len(segments_result.data)} audio segments")
        
        # Clean up user-specific audio files and clips from disk
        import shutil
        from pathlib import Path
        from ..config.settings import settings
        
        user_id = user['user_id']
        
        # Delete user's audio files (OGG files from Limitless API)
        user_audio_dir = Path(settings.upload_dir) / "audio" / user_id
        if user_audio_dir.exists():
            shutil.rmtree(user_audio_dir)
            print(f"🗑️ Deleted user audio files: {user_audio_dir}")
        else:
            print(f"⚠️ User audio directory not found: {user_audio_dir}")
        
        # Delete user's laughter clip files (WAV clips extracted by YAMNet)
        user_clips_dir = Path(settings.upload_dir) / "clips" / user_id
        if user_clips_dir.exists():
            shutil.rmtree(user_clips_dir)
            print(f"🗑️ Deleted user clip files: {user_clips_dir}")
        else:
            print(f"⚠️ User clips directory not found: {user_clips_dir}")
        
        return {"message": "User data deleted successfully (API key preserved)"}
        
    except Exception as e:
        print(f"❌ Error deleting user data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user data"
        )


@router.post("/reprocess-date-range")
async def reprocess_date_range_api(
    request: ReprocessDateRangeRequest,
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """
    Reprocess audio data for a date range.
    
    This clears existing data for the date range and redownloads/reprocesses from Limitless API.
    
    Args:
        request: Request body with start_date and end_date (YYYY-MM-DD format)
        user: Current authenticated user
        
    Returns:
        Success message with processing summary
        
    Raises:
        HTTPException: If reprocessing fails or dates are invalid
    """
    try:
        user_id = user["user_id"]
        start_date = request.start_date
        end_date = request.end_date
        
        print(f"🔄 Starting reprocess for {start_date} to {end_date}, user {user_id[:8]}")
        
        # Import the reprocess function from manual_reprocess_yesterday
        import sys
        import os
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        sys.path.insert(0, script_dir)
        from manual_reprocess_yesterday import reprocess_date_range as reprocess_func
        
        # Call the reprocess function (it handles all the work)
        await reprocess_func(start_date, end_date, user_id)
        
        print(f"✅ Reprocess complete for {start_date} to {end_date}")
        
        return {
            "message": "Reprocessing completed successfully",
            "start_date": start_date,
            "end_date": end_date,
            "status": "completed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error reprocessing date range: {str(e)}")
        import traceback
        print(f"❌ {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reprocess date range: {str(e)}"
        )
