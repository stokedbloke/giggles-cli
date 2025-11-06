# Registration Flow - What Actually Happens

## Step-by-Step Flow

### 1. User Submits Registration Form
- Frontend calls `/auth/register` with email, password, timezone

### 2. Backend Calls Supabase Auth
```python
response = self.supabase.auth.sign_up({
    "email": email,
    "password": password
})
```
- This creates a user in `auth.users` table (Supabase's auth system)
- Returns user object with `user.id` and `session.access_token`

### 3. Database Trigger Fires (AUTOMATIC)
- **Trigger**: `on_auth_user_created` runs AFTER INSERT on `auth.users`
- **Function**: `handle_new_user()` executes
- **What it does**: 
  ```sql
  INSERT INTO public.users (id, email, is_active, mfa_enabled)
  VALUES (NEW.id, NEW.email, TRUE, TRUE);
  ```
- **Timezone**: NOT set, defaults to `'UTC'` (from table default)
- **RLS**: Bypassed because function uses `SECURITY DEFINER`
- **Timing**: Runs SYNCHRONOUSLY - completes before backend code continues

### 4. Backend Code Continues
- MFA is enabled (uses service role key - appropriate for admin operation)
- **Original code tried**: INSERT user profile again (FAILED - RLS violation)
- **New code does**: UPDATE timezone (WORKS - RLS allows UPDATE of own profile)

## The Original Problem

### What Was Happening:
1. Trigger creates user profile with `timezone='UTC'`
2. Backend code tries to INSERT user profile again
3. **Error**: RLS violation - no INSERT policy exists
4. Registration fails even though user was created in auth.users

### Why It Failed:
- `users` table has RLS enabled
- RLS policies exist for SELECT and UPDATE, but NOT for INSERT
- Backend code used regular client (not service role), so RLS was enforced
- INSERT was blocked

## The Fix

### What Changed:
1. **Removed**: INSERT/UPSERT attempt (which was blocked)
2. **Added**: UPDATE timezone using user's session token
3. **Why it works**: UPDATE policy exists: `auth.uid() = id` allows users to update own profile

### What About "Race Condition"?
**There is NO race condition.** I was wrong to mention it.
- Database triggers run SYNCHRONOUSLY
- Trigger completes before backend code continues
- The retry logic I added is unnecessary

### What About "User Already Exists"?
**This is NOT about duplicate email registration.**
- If user tries to register with existing email, Supabase Auth returns an error BEFORE step 2
- The "user already exists" I mentioned was about the trigger creating the profile, then backend trying to create it again
- This is now fixed - we UPDATE instead of INSERT

## Timezone Issue - Fixed or Not?

### Original Issue:
- Trigger creates user with `timezone='UTC'` (default)
- Backend wanted to set detected timezone
- Backend INSERT failed, so timezone stayed UTC

### Current Fix:
- Trigger still creates user with `timezone='UTC'`
- Backend UPDATEs timezone to detected value
- **This works** because UPDATE policy allows it

### Is This The Best Solution?
**Current implementation is Option C.** Here are the alternatives:

1. **Option A**: Update trigger to accept timezone
   - **Why it doesn't work**: Database triggers can't receive parameters from application code
   - **Would require**: Passing timezone through Supabase Auth metadata (complex, not standard)

2. **Option B**: Remove trigger, let backend create profile
   - **What it means**: Delete the `on_auth_user_created` trigger, backend does INSERT
   - **Requires**: Adding INSERT RLS policy: `CREATE POLICY "Users can insert own profile" ON public.users FOR INSERT WITH CHECK (auth.uid() = id);`
   - **Pros**: Single operation (INSERT with timezone), simpler flow
   - **Cons**: If backend code fails, no profile created (trigger is more reliable)
   - **Security**: Still secure - INSERT policy enforces `auth.uid() = id`

3. **Option C**: Current approach - trigger creates, backend updates
   - **What it means**: Keep trigger (creates with UTC), backend UPDATEs timezone
   - **Pros**: More reliable (trigger always runs), defense in depth
   - **Cons**: Two operations (INSERT then UPDATE), slightly more complex
   - **Security**: Secure - UPDATE policy enforces `auth.uid() = id`

**Why I chose C (current implementation):**
- Trigger provides automatic fallback if backend code fails
- No need to add new RLS policy
- Works with existing database setup
- Timezone update is non-fatal (graceful degradation)

## Security Analysis

### Service Role Key Usage:
- **enable_mfa()**: Uses service role key ✅ (admin operation, appropriate)
- **update_user_timezone()**: Uses user session token ✅ (user operation, RLS enforced)

### RLS Enforcement:
- User profile creation: Trigger (bypasses RLS via SECURITY DEFINER) ✅
- Timezone update: User session (RLS enforced: `auth.uid() = id`) ✅

## Recommendations

1. **Remove unnecessary retry logic** - triggers are synchronous
2. **Consider adding INSERT policy** - would allow backend to create profile if trigger fails
3. **Keep current approach** - it works and is secure

