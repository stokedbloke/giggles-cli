"""
API key management routes for the laughter detector application.

This module handles Limitless API key storage, validation, and management.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..auth.supabase_auth import auth_service
from ..auth.encryption import encryption_service
from ..services.limitless_api import limitless_api_service
from ..models.user import LimitlessKeyCreate, LimitlessKeyResponse
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
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')  # Use SUPABASE_KEY instead of SUPABASE_ANON_KEY
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database configuration error"
        )
    
    # Create user-specific client with their JWT token (RLS will enforce user can only access their own data)
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabase.postgrest.auth(credentials.credentials)
    return supabase


@router.get("/limitless-key/status")
async def check_limitless_key_status(
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """
    Check if user has an active Limitless API key.
    
    Args:
        user: Current authenticated user
        
    Returns:
        Simple boolean indicating if API key exists
    """
    try:
        print(f"🔑 Checking API key status for user: {user.get('user_id')}")
        
        # Create RLS-compliant client
        supabase = create_user_supabase_client(credentials)
        
        # Check if user has an active API key (RLS will ensure user can only access their own)
        result = supabase.table("limitless_keys").select("id").eq("is_active", True).execute()
        
        print(f"🔑 Found {len(result.data)} active API keys")
        
        return {"has_key": len(result.data) > 0}
        
    except Exception as e:
        print(f"❌ Error checking API key status: {str(e)}")
        import traceback
        print(f"❌ {traceback.format_exc()}")
        return {"has_key": False}


@router.post("/limitless-key", response_model=LimitlessKeyResponse)
async def store_limitless_key(
    key_data: LimitlessKeyCreate,
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """
    Store encrypted Limitless API key for user.
    
    Args:
        key_data: API key data
        user: Current authenticated user
        
    Returns:
        Created key information
        
    Raises:
        HTTPException: If storage fails
    """
    try:
        # Validate API key
        if not await limitless_api_service.validate_api_key(key_data.api_key):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Limitless API key. Please check your key and try again."
            )
        
        # Encrypt API key
        encrypted_key = encryption_service.encrypt(
            key_data.api_key,
            associated_data=user["user_id"].encode('utf-8')
        )
        
        # Create RLS-compliant client
        supabase = create_user_supabase_client(credentials)
        
        # First, deactivate any existing active keys for this user (RLS will ensure user can only access their own)
        supabase.table("limitless_keys").update({
            "is_active": False,
            "updated_at": datetime.now().isoformat()
        }).eq("is_active", True).execute()
        
        # Then insert the new key (RLS will ensure user can only insert their own)
        result = supabase.table("limitless_keys").insert({
            "user_id": user["user_id"],
            "encrypted_api_key": encrypted_key,
            "is_active": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }).execute()
        
        return LimitlessKeyResponse(
            id=result.data[0]["id"] if result.data else "stored_key_id",
            created_at=datetime.now(),
            is_active=True
        )
        
    except HTTPException as e:
        # Re-raise HTTP exceptions with their original status and detail
        raise e
    except Exception as e:
        print(f"❌ Database error storing API key: {str(e)}")
        
        # Check if it's a constraint violation (unique index)
        if "duplicate key value violates unique constraint" in str(e) or "idx_limitless_keys_one_active_per_user" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active API key. Please delete your existing key first or contact support if you need assistance."
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store API key in database"
        )


@router.delete("/limitless-key")
async def delete_limitless_key(
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """
    Delete Limitless API key for user.
    
    Args:
        user: Current authenticated user
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If deletion fails
    """
    try:
        # Create RLS-compliant client
        supabase = create_user_supabase_client(credentials)
        
        # Actually delete the API key row from the database (RLS will ensure user can only delete their own)
        # Need a WHERE clause - RLS policies will limit to the user's own data
        result = supabase.table("limitless_keys").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        
        if not result.data:
            # No keys found to delete
            return {"message": "No API key found to delete"}
        
        print(f"Deleted {len(result.data)} API key(s) for user {user['user_id']}")
        
        return {"message": "API key deleted successfully"}
        
    except Exception as e:
        print(f"❌ Error deleting API key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete API key"
        )
