"""
FastAPI dependencies for authentication and authorization.

This module provides dependency injection for user authentication,
rate limiting, and other common API requirements.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.api_key import APIKeyHeader

from ..auth.supabase_auth import auth_service
from ..services.limitless_api import limitless_api_service

security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        Current user data
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        user = await auth_service.get_current_user(credentials.credentials)
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Get current user if authenticated, otherwise return None.
    
    Args:
        credentials: Optional HTTP Bearer token credentials
        
    Returns:
        Current user data or None
    """
    if not credentials:
        return None
    
    try:
        user = await auth_service.get_current_user(credentials.credentials)
        return user
    except Exception:
        return None


async def verify_limitless_api_key(api_key: str) -> bool:
    """
    Verify Limitless API key is valid.
    
    Args:
        api_key: Limitless API key to verify
        
    Returns:
        True if valid, False otherwise
    """
    return await limitless_api_service.validate_api_key(api_key)


async def check_rate_limit(user_id: str) -> bool:
    """
    Check if user has exceeded rate limits.
    
    Args:
        user_id: User ID to check
        
    Returns:
        True if within limits, False if exceeded
    """
    # In a real implementation, this would check against a database
    # or cache to track API usage per user
    # For now, return True (no rate limiting)
    return True


class RateLimitChecker:
    """Rate limiting dependency class."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    async def __call__(self, user: dict = Depends(get_current_user)) -> dict:
        """
        Check rate limit for user.
        
        Args:
            user: Current user data
            
        Returns:
            User data if within limits
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        if not await check_rate_limit(user["user_id"]):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        return user


# Rate limiting dependency instances
rate_limit_standard = RateLimitChecker(max_requests=100, window_seconds=3600)
rate_limit_strict = RateLimitChecker(max_requests=10, window_seconds=3600)
