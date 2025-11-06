# Code Changes Summary - Registration Fix

## What Changed

### Method Renamed
- **Old**: `create_user_profile(user_id, email, timezone)` 
- **New**: `update_user_timezone(user_id, timezone, access_token)`

### Why the Change?
1. **Old method tried to INSERT** - blocked by RLS (no INSERT policy)
2. **New method does UPDATE** - allowed by existing RLS policy
3. **More accurate name** - we're updating timezone, not creating profile (trigger does that)

### Impact on Code Flows

**No breaking changes** - `create_user_profile` was only called from:
- `register_user()` method (line 116) - ✅ Updated to call `update_user_timezone()`
- Documentation files (not actual code) - ✅ No impact

**All other code flows:**
- Login flow - ✅ No changes needed
- MFA flow - ✅ No changes needed  
- API routes - ✅ No changes needed
- Frontend - ✅ No changes needed

## Current Flow

```
1. User registers → Supabase Auth creates user
2. Trigger fires → Creates profile with timezone='UTC'
3. Backend calls update_user_timezone() → Updates to detected timezone
```

## If You Want Option B Instead

If you prefer Option B (remove trigger, let backend INSERT):

1. **Delete trigger**:
   ```sql
   DROP TRIGGER on_auth_user_created ON auth.users;
   ```

2. **Add INSERT policy**:
   ```sql
   CREATE POLICY "Users can insert own profile" ON public.users
       FOR INSERT WITH CHECK (auth.uid() = id);
   ```

3. **Revert method** to INSERT:
   ```python
   async def create_user_profile(self, user_id: str, email: str, timezone: str = "UTC"):
       user_client = create_client(settings.supabase_url, settings.supabase_key)
       user_client.postgrest.auth(access_token)
       result = user_client.table("users").insert({
           "id": user_id,
           "email": email,
           "timezone": timezone,
           "is_active": True,
           "mfa_enabled": True
       }).execute()
   ```

4. **Update registration** to call `create_user_profile()` instead of `update_user_timezone()`

