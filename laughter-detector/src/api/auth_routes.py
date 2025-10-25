"""
Authentication routes for the laughter detector application.

This module handles user registration, login, and authentication-related endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends
import logging

from ..auth.supabase_auth import auth_service
from ..models.user import UserCreate, UserLogin, UserResponse
from .dependencies import get_current_user

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.post("/auth/register", response_model=UserResponse)
async def register_user(user_data: UserCreate):
    """
    Register a new user account.
    
    Args:
        user_data: User registration data
        
    Returns:
        Created user information
        
    Raises:
        HTTPException: If registration fails
    """
    try:
        result = await auth_service.register_user(
            user_data.email, 
            user_data.password
        )
        
        return UserResponse(
            id=result["user_id"],
            email=result["email"],
            created_at=result["created_at"],
            is_active=True,
            mfa_enabled=True
        )
        
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please check your email and password."
        )


@router.post("/auth/login")
async def login_user(credentials: UserLogin):
    """
    Authenticate user and return session token.
    
    Args:
        credentials: User login credentials
        
    Returns:
        Authentication token and user information
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        result = await auth_service.login_user(
            credentials.email, 
            credentials.password
        )
        
        # Return Supabase session token instead of creating our own
        return {
            "access_token": result["session"].access_token,
            "token_type": "bearer",
            "user": {
                "id": result["user_id"],
                "email": result["email"]
            }
        }
        
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@router.get("/auth/me")
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """
    Get current authenticated user information.
    
    Args:
        user: Current authenticated user from dependency
        
    Returns:
        Current user information
        
    Raises:
        HTTPException: If user is not authenticated
    """
    try:
        return {
            "user_id": user["user_id"],
            "email": user["email"],
            "is_authenticated": True
        }
        
    except Exception as e:
        logger.error(f"Failed to get user info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
