"""
Supabase authentication integration for secure user management.

This module handles user registration, login, MFA, and session management
using Supabase Auth with proper security practices.
"""

import re
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from supabase import create_client, Client
from fastapi import HTTPException, status
from passlib.context import CryptContext
from jose import JWTError, jwt

from ..config.settings import settings

# Configure logging
logger = logging.getLogger(__name__)


class AuthService:
    """Service for handling authentication and user management."""
    
    def __init__(self):
        """Initialize Supabase client and password context."""
        self.supabase: Client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = settings.secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
    
    def validate_email(self, email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_password_strength(self, password: str) -> bool:
        """
        Validate password strength.
        
        Args:
            password: Password to validate
            
        Returns:
            True if strong enough, False otherwise
        """
        if len(password) < 8:
            return False
        
        # Check for uppercase, lowercase, digit, and special character
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        return has_upper and has_lower and has_digit and has_special
    
    async def register_user(self, email: str, password: str, timezone: str = "UTC") -> Dict[str, Any]:
        """
        Register a new user with Supabase Auth.
        
        Args:
            email: User email address
            password: User password
            timezone: User's timezone (IANA format, e.g., 'America/Los_Angeles')
            
        Returns:
            User data and session information
            
        Raises:
            HTTPException: If registration fails
        """
        # Validate input
        if not self.validate_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        if not self.validate_password_strength(password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters with uppercase, lowercase, digit, and special character"
            )
        
        try:
            # Register with Supabase
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if response.user is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Registration failed"
                )
            
            # Enable MFA by default
            await self.enable_mfa(response.user.id)
            
            # Create user in our custom users table with timezone
            await self.create_user_profile(response.user.id, response.user.email, timezone)
            
            return {
                "user_id": response.user.id,
                "email": response.user.email,
                "created_at": response.user.created_at,
                "session": response.session
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Registration failed: {str(e)}"
            )
    
    async def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user with email and password.
        
        Args:
            email: User email address
            password: User password
            
        Returns:
            User data and session information
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user is None or response.session is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
            
            return {
                "user_id": response.user.id,
                "email": response.user.email,
                "session": response.session
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
    
    async def create_user_profile(self, user_id: str, email: str, timezone: str = "UTC") -> None:
        """
        Create user profile in our custom users table.
        
        Args:
            user_id: User ID from Supabase auth
            email: User email address
            timezone: User's timezone (IANA format, e.g., 'America/Los_Angeles')
        """
        try:
            # Insert user into our custom users table with timezone
            result = self.supabase.table("users").insert({
                "id": user_id,
                "email": email,
                "is_active": True,
                "mfa_enabled": True,
                "timezone": timezone  # Store detected timezone
            }).execute()
            
            if not result.data:
                raise Exception("Failed to create user profile")
                
        except Exception as e:
            print(f"Error creating user profile: {str(e)}")
            raise

    async def enable_mfa(self, user_id: str) -> bool:
        """
        Enable multi-factor authentication for user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if MFA enabled successfully
        """
        try:
            # Enable MFA using Supabase service role
            service_client = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key
            )
            
            # Update user to enable MFA
            response = service_client.auth.admin.update_user_by_id(
                user_id,
                {"app_metadata": {"mfa_enabled": True}}
            )
            
            return response is not None
            
        except Exception:
            return False
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token.
        
        Args:
            data: Token payload data
            expires_delta: Token expiration time
            
        Returns:
            JWT token string
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    async def get_current_user(self, token: str) -> Dict[str, Any]:
        """
        Get current user using Supabase's JWT token.
        
        SECURITY FIX: Extract user_id from JWT and query specific user to prevent
        authentication bypass where any valid token could return the first user in the table.
        
        Args:
            token: Supabase JWT access token
            
        Returns:
            Current user data
            
        Raises:
            HTTPException: If token is invalid or user not found
        """
        try:
            # First, decode JWT to extract user_id (without full verification since Supabase will validate)
            try:
                unverified_payload = jwt.get_unverified_claims(token)
                user_id = unverified_payload.get("sub")
                
                if not user_id:
                    logger.error("No user_id found in JWT token")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token: missing user_id"
                    )
            except Exception as e:
                logger.error(f"Failed to extract user_id from JWT: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token format"
                )
            
            # Create a temporary Supabase client with the user's token
            temp_client = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
            
            # Set the Authorization header on the postgrest client
            temp_client.postgrest.auth(token)
            
            # SECURITY FIX: Query specific user by user_id from JWT (not just limit(1))
            result = temp_client.table("users").select("*").eq("id", user_id).single().execute()
            
            if not result.data:
                logger.error(f"User {user_id} not found in database")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            user_data = result.data
            
            # Verify that the JWT user_id matches the database user_id
            if user_data.get('id') != user_id:
                logger.error(f"User ID mismatch: JWT user_id={user_id}, DB user_id={user_data.get('id')}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication error"
                )
            
            return {
                "user_id": user_data['id'],
                "email": user_data['email'],
                "timezone": user_data.get('timezone', 'UTC'),  # Include timezone
                "created_at": user_data.get('created_at', datetime.utcnow().isoformat())
            }
            
        except HTTPException:
            # Re-raise HTTPExceptions as-is
            raise
        except Exception as e:
            logger.error(f"❌ get_current_user error: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )


# Global auth service instance
auth_service = AuthService()
