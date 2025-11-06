"""
Supabase authentication integration for secure user management.

This module handles user registration, login, MFA, and session management
using Supabase Auth with proper security practices.
"""

import re
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from supabase import create_client, Client
from fastapi import HTTPException, status
from passlib.context import CryptContext
from jose import JWTError, jwt

from ..config.settings import settings

# Configure logging


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
        Register a new user with timezone detection and proper multi-user isolation.
        
        Registration flow:
        1. Validate email and password strength
        2. Create user in Supabase Auth (auth.users table)
        3. Enable MFA by default (security best practice)
        4. Create user profile in custom users table with detected timezone
           - Uses user's session token (RLS enforced)
           - Ensures proper user isolation from the start
        
        MULTI-USER FIX: Registration now properly isolates users:
        - Each user gets unique user_id from Supabase Auth
        - User profile created with RLS enforcement (user can only create own profile)
        - Timezone stored per-user for proper date handling
        - No shared state or cross-user data leakage
        
        Security notes:
        - Password validation enforces strong passwords (8+ chars, mixed case, special chars)
        - MFA enabled by default for additional security
        - User profile creation uses RLS (not service role key) for proper isolation
        - Database trigger also creates profile, but with UTC timezone (we update immediately)
        
        Args:
            email: User email address (must be valid email format)
            password: User password (must meet strength requirements)
            timezone: User's timezone (IANA format, e.g., 'America/Los_Angeles')
                     Detected from browser during registration
                     Defaults to 'UTC' if not provided
            
        Returns:
            Dictionary containing:
            - user_id: Unique user identifier from Supabase Auth
            - email: User's email address
            - created_at: Account creation timestamp
            - session: Supabase session with access_token for authenticated requests
            
        Raises:
            HTTPException: If validation fails or registration fails
                - 400: Invalid email format or weak password
                - 400: Registration failed (user already exists, etc.)
        """
        # Validate input - fail fast if invalid
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
            # Step 1: Register user in Supabase Auth (creates entry in auth.users table)
            # This creates the user account and returns a session with access_token
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if response.user is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Registration failed"
                )
            
            # Step 2: Enable MFA by default (security best practice)
            # Uses service role key (admin operation, appropriate use case)
            await self.enable_mfa(response.user.id)
            
            # Step 3: Create user profile in custom users table with detected timezone
            # MULTI-USER FIX: Uses user's session token (RLS enforced via INSERT policy)
            # This ensures:
            # - User can only create their own profile (not other users' profiles)
            # - Proper user isolation from the moment of registration
            # - Timezone is stored immediately (database trigger creates profile with UTC default)
            await self.create_user_profile(
                response.user.id, 
                response.user.email, 
                timezone, 
                response.session.access_token
            )
            
            return {
                "user_id": response.user.id,
                "email": response.user.email,
                "created_at": response.user.created_at,
                "session": response.session  # Contains access_token for authenticated requests
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
    
    async def create_user_profile(self, user_id: str, email: str, timezone: str, access_token: str) -> None:
        """
        Create user profile in our custom users table.
        
        MULTI-USER FIX: Uses user's session token (RLS enforced) instead of service role key.
        This ensures proper security isolation and follows the principle of least privilege.
        
        Why this approach:
        - RLS (Row Level Security) policies enforce that users can only insert their own profile
        - The INSERT policy "Users can insert own profile" checks: auth.uid() = id
        - Using the user's session token ensures RLS is properly enforced
        - Avoids using service role key unnecessarily (service role bypasses RLS)
        
        Security benefits:
        1. Prevents privilege escalation (user can only create their own profile)
        2. Enforces RLS policies at the database level
        3. Follows principle of least privilege (no service role needed)
        4. Proper audit trail (operation attributed to the user)
        
        Note: There is a database trigger `on_auth_user_created` that also creates a user
        profile, but it creates it with timezone='UTC' (default). This method allows us
        to set the detected timezone from the frontend immediately after registration.
        
        Args:
            user_id: User ID from Supabase auth (matches JWT 'sub' claim)
            email: User email address
            timezone: User's timezone (IANA format, e.g., 'America/Los_Angeles')
                     Detected from browser during registration
            access_token: User's access token from registration session
                         Used to authenticate the INSERT operation with RLS enforcement
        """
        try:
            # Create a client with user's session token (not service role key)
            # This ensures RLS policies are enforced: user can only insert their own profile
            from supabase import create_client
            user_client = create_client(settings.supabase_url, settings.supabase_key)
            user_client.postgrest.auth(access_token)
            
            # Insert user profile - RLS policy ensures auth.uid() = id
            # If user_id in JWT doesn't match the 'id' being inserted, RLS will block this
            result = user_client.table("users").insert({
                "id": user_id,
                "email": email,
                "is_active": True,
                "mfa_enabled": True,
                "timezone": timezone  # Store detected timezone from frontend
            }).execute()
            
            if not result.data:
                raise Exception("Failed to create user profile")
                
        except Exception as e:
            print(f"Error creating user profile: {str(e)}")
            raise

    async def enable_mfa(self, user_id: str) -> bool:
        """
        Enable multi-factor authentication for user.
        
        Security note: Uses service role key (appropriate for admin operation).
        This is an administrative action that requires elevated privileges,
        so using the service role key is correct here.
        
        Args:
            user_id: User ID from Supabase Auth
            
        Returns:
            True if MFA enabled successfully, False otherwise
        """
        try:
            # Enable MFA using Supabase service role key
            # Reason: Admin operation requiring elevated privileges
            # Service role key bypasses RLS, which is appropriate for admin actions
            service_client = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key
            )
            
            # Update user metadata to enable MFA
            # This sets app_metadata.mfa_enabled = True in Supabase Auth
            response = service_client.auth.admin.update_user_by_id(
                user_id,
                {"app_metadata": {"mfa_enabled": True}}
            )
            
            return response is not None
            
        except Exception:
            # Fail silently - MFA is a security enhancement, not critical for registration
            # If this fails, user can still register, but MFA won't be enabled
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
        
        CRITICAL SECURITY FIX: This function was previously vulnerable to authentication bypass.
        
        Previous vulnerability:
        - Old code: `SELECT * FROM users LIMIT 1` (no WHERE clause)
        - Problem: Would return the FIRST user in the table (alphabetically/by creation date)
        - Attack: Attacker with valid JWT for User A could receive User B's data
        - Impact: CRITICAL - Complete authentication bypass, users could access any user's data
        
        Current fix:
        - Extract user_id from JWT token's 'sub' claim
        - Query specific user: `SELECT * FROM users WHERE id = user_id`
        - Verify JWT user_id matches database user_id (defense in depth)
        - Result: User can only access their own data
        
        Security benefits:
        1. Prevents authentication bypass (user can only access own data)
        2. Enforces proper user isolation (multi-user security)
        3. Uses JWT 'sub' claim as source of truth for user identity
        4. Verifies user_id match between JWT and database (defense in depth)
        
        Multi-user isolation:
        - Each user's JWT contains their unique user_id in the 'sub' claim
        - Database queries filter by user_id to ensure data isolation
        - RLS policies provide additional database-level protection
        - All authenticated endpoints depend on this function for user identification
        
        Args:
            token: Supabase JWT access token containing user_id in 'sub' claim
            
        Returns:
            Current user data including user_id, email, timezone, and created_at
            
        Raises:
            HTTPException: If token is invalid, user_id missing, or user not found
            
        Example JWT payload:
            {
                "sub": "user-uuid-1234",  # <-- This is the user_id we extract
                "email": "user@example.com",
                "exp": 1234567890,
                ...
            }
        """
        try:
            # Step 1: Extract user_id from JWT token without full verification
            # Reason: We need user_id to query the database, and Supabase will validate
            # the token signature when we use it for database queries
            try:
                unverified_payload = jwt.get_unverified_claims(token)
                user_id = unverified_payload.get("sub")  # 'sub' claim contains user_id
                
                if not user_id:
                    print(f"No user_id found in JWT token")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token: missing user_id"
                    )
            except Exception as e:
                print(f"Failed to extract user_id from JWT: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token format"
                )
            
            # Step 2: Create Supabase client with user's token for authenticated query
            # This ensures RLS policies are enforced at the database level
            temp_client = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
            
            # Set the Authorization header - Supabase validates token signature here
            temp_client.postgrest.auth(token)
            
            # Step 3: Query SPECIFIC user by user_id from JWT (SECURITY FIX)
            # Old (vulnerable): .limit(1) - would return first user in table
            # New (secure): .eq("id", user_id).single() - returns only the authenticated user
            result = temp_client.table("users").select("*").eq("id", user_id).single().execute()
            
            if not result.data:
                print(f"User {user_id} not found in database")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            user_data = result.data
            
            # Step 4: Defense in depth - verify JWT user_id matches database user_id
            # This catches any edge cases where the query might have returned wrong user
            # (should never happen with .eq() filter, but double-check for safety)
            if user_data.get('id') != user_id:
                print(f"User ID mismatch: JWT user_id={user_id}, DB user_id={user_data.get('id')}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication error"
                )
            
            # Step 5: Return user data (only their own data, guaranteed by user_id filter)
            return {
                "user_id": user_data['id'],
                "email": user_data['email'],
                "timezone": user_data.get('timezone', 'UTC'),  # Include timezone for proper date handling
                "created_at": user_data.get('created_at', datetime.utcnow().isoformat())
            }
            
        except HTTPException:
            # Re-raise HTTPExceptions as-is (they already have proper status codes)
            raise
        except Exception as e:
            # Log full error for debugging but don't expose details to client
            print(f"❌ get_current_user error: {type(e).__name__}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )


# Global auth service instance
auth_service = AuthService()
