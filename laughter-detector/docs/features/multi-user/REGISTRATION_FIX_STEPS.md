# Registration Fix - Final Steps

## Step 1: Run SQL (ONE FILE)

**File**: `REGISTRATION_FIX_FINAL.sql`

Run this in Supabase SQL Editor:
```sql
-- Add INSERT RLS policy
CREATE POLICY "Users can insert own profile" ON public.users
    FOR INSERT WITH CHECK (auth.uid() = id);

-- Remove trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Drop function (cleanup)
DROP FUNCTION IF EXISTS public.handle_new_user();
```

## Step 2: Update Code

**File**: `src/auth/supabase_auth.py`

1. **Replace `update_user_timezone()` method** (lines 171-208) with:

```python
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
        from supabase import create_client
        user_client = create_client(settings.supabase_url, settings.supabase_key)
        user_client.postgrest.auth(access_token)
        
        result = user_client.table("users").insert({
            "id": user_id,
            "email": email,
            "is_active": True,
            "mfa_enabled": True,
            "timezone": timezone
        }).execute()
        
        if not result.data:
            raise Exception("Failed to create user profile")
                
    except Exception as e:
        print(f"Error creating user profile: {str(e)}")
        raise
```

2. **Update `register_user()` method** (line 118):

Change from:
```python
await self.update_user_timezone(response.user.id, timezone, response.session.access_token)
```

To:
```python
await self.create_user_profile(response.user.id, response.user.email, timezone, response.session.access_token)
```

## Step 3: Test

1. Try registering a new user
2. Verify timezone is set correctly
3. Verify user can log in

## Files to Ignore/Delete

- `OPTION_B_IMPLEMENTATION.sql` (old, has commented code)
- `fix_user_insert_policy.sql` (old, incomplete)
- Use only: `REGISTRATION_FIX_FINAL.sql`

