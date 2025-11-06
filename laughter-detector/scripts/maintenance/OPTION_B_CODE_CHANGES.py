# Option B: Code Changes
# Replace update_user_timezone() with create_user_profile()

# In src/auth/supabase_auth.py, replace the update_user_timezone method with:

async def create_user_profile(self, user_id: str, email: str, timezone: str, access_token: str) -> None:
    """
    Create user profile in our custom users table.
    
    SECURITY: Uses user's session token (RLS enforced) - no service role key needed.
    The INSERT RLS policy "Users can insert own profile" enforces auth.uid() = id.
    
    Args:
        user_id: User ID from Supabase auth
        email: User email address
        timezone: User's timezone (IANA format, e.g., 'America/Los_Angeles')
        access_token: User's access token from registration session
    """
    try:
        # Create client with user's session token (RLS will enforce user can only insert own profile)
        from supabase import create_client
        user_client = create_client(settings.supabase_url, settings.supabase_key)
        user_client.postgrest.auth(access_token)
        
        # Insert user profile with timezone - RLS policy "Users can insert own profile" will allow this
        result = user_client.table("users").insert({
            "id": user_id,
            "email": email,
            "is_active": True,
            "mfa_enabled": True,
            "timezone": timezone  # Set timezone correctly from the start
        }).execute()
        
        if not result.data:
            raise Exception("Failed to create user profile")
                
    except Exception as e:
        print(f"Error creating user profile: {str(e)}")
        raise

# In register_user(), change line 118 from:
#   await self.update_user_timezone(response.user.id, timezone, response.session.access_token)
# To:
#   await self.create_user_profile(response.user.id, response.user.email, timezone, response.session.access_token)

