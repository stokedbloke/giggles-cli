"""
API key management routes for the laughter detector application.

This module handles Limitless API key storage, validation, and management.
"""

from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..auth.encryption import encryption_service
from ..config.settings import settings
from ..models.user import LimitlessKeyCreate, LimitlessKeyResponse
from ..services.limitless_api import limitless_api_service
from .dependencies import get_current_user


# Create router
router = APIRouter()


async def supabase_rest_request(
    method: str,
    resource: str,
    token: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
    prefer: Optional[str] = None,
) -> httpx.Response:
    """
    Execute a Supabase REST API request scoped to the authenticated user.

    Args:
        method: HTTP method to use.
        resource: Supabase REST resource path (e.g., 'limitless_keys').
        token: Supabase JWT access token from the logged-in user.
        params: Optional query parameters.
        json: Optional JSON payload.
        prefer: Optional Prefer header value.

    Returns:
        httpx.Response object.

    Raises:
        HTTPException: If the Supabase request fails.
    """

    url = f"{settings.supabase_url}/rest/v1/{resource}"
    headers = {
        "apikey": settings.supabase_key,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if json is not None:
        headers["Content-Type"] = "application/json"
    if prefer:
        headers["Prefer"] = prefer

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method, url, params=params, json=json, headers=headers
        )

    if response.status_code >= 400:
        detail = (
            response.json()
            if response.headers.get("content-type", "").startswith("application/json")
            else response.text
        )
        print(f"❌ Supabase REST error ({response.status_code}): {detail}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Supabase request failed ({response.status_code}): {detail}",
        )

    return response


@router.get("/limitless-key/status")
async def check_limitless_key_status(
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
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
        params = {
            "select": "id",
            "user_id": f"eq.{user['user_id']}",
            "is_active": "eq.true",
        }
        response = await supabase_rest_request(
            "GET",
            "limitless_keys",
            credentials.credentials,
            params=params,
            prefer="count=exact",
        )
        data = response.json()
        print(f"🔑 Found {len(data)} active API keys")
        return {"has_key": len(data) > 0}

    except Exception as e:
        print(f"❌ Error checking API key status: {str(e)}")
        import traceback

        print(f"❌ {traceback.format_exc()}")
        return {"has_key": False}


@router.post("/limitless-key", response_model=LimitlessKeyResponse)
async def store_limitless_key(
    key_data: LimitlessKeyCreate,
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
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
                detail="Invalid Limitless API key. Please check your key and try again.",
            )

        # Encrypt API key
        encrypted_key = encryption_service.encrypt(
            key_data.api_key, associated_data=user["user_id"].encode("utf-8")
        )

        # Create RLS-compliant client
        now_iso = datetime.utcnow().isoformat()
        token = credentials.credentials

        # Deactivate existing keys
        await supabase_rest_request(
            "PATCH",
            "limitless_keys",
            token,
            params={
                "user_id": f"eq.{user['user_id']}",
                "is_active": "eq.true",
            },
            json={
                "is_active": False,
                "updated_at": now_iso,
            },
            prefer="return=minimal",
        )

        # Insert new key
        response = await supabase_rest_request(
            "POST",
            "limitless_keys",
            token,
            json={
                "user_id": user["user_id"],
                "encrypted_api_key": encrypted_key,
                "is_active": True,
                "created_at": now_iso,
                "updated_at": now_iso,
            },
            prefer="return=representation",
        )
        data = response.json()

        return LimitlessKeyResponse(
            id=data[0]["id"] if data else "stored_key_id",
            created_at=datetime.utcnow(),
            is_active=True,
        )

    except HTTPException as e:
        # Re-raise HTTP exceptions with their original status and detail
        raise e
    except Exception as e:
        print(f"❌ Database error storing API key: {str(e)}")

        # Check if it's a constraint violation (unique index)
        if "duplicate key value violates unique constraint" in str(
            e
        ) or "idx_limitless_keys_one_active_per_user" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active API key. Please delete your existing key first or contact support if you need assistance.",
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store API key in database",
        )


@router.delete("/limitless-key")
async def delete_limitless_key(
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
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
        response = await supabase_rest_request(
            "DELETE",
            "limitless_keys",
            credentials.credentials,
            params={"user_id": f"eq.{user['user_id']}"},
            prefer="return=representation",
        )

        data = response.json()
        if not data:
            # No keys found to delete
            return {"message": "No API key found to delete"}

        print(f"Deleted {len(data)} API key(s) for user {user['user_id']}")

        return {"message": "API key deleted successfully"}

    except Exception as e:
        print(f"❌ Error deleting API key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete API key",
        )
