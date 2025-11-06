# Definitive Analysis: Option B vs Option C

## Critical Facts

### 1. What `get_current_user` Requires
```python
result = temp_client.table("users").select("*").eq("id", user_id).single().execute()
if not result.data:
    raise HTTPException(401, "User not found")
```
**Fact**: User profile MUST exist in `public.users` table or authentication fails.

### 2. Current Problem with Option C
- Trigger creates profile with `timezone='UTC'`
- Backend UPDATEs timezone
- **If UPDATE fails**: User has wrong timezone but can still log in
- **This is a partial failure state** - BAD

### 3. What Happens with Option B
- Backend INSERTs profile with correct timezone
- **If INSERT fails**: Registration fails completely, user can't log in
- **This is correct behavior** - registration should fail if profile creation fails

## The Real Question

**Why does the trigger exist?**

Looking at the trigger:
```sql
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

**Original purpose**: Ensure profile exists even if backend code fails.

**But this creates problems**:
1. Trigger can't receive timezone parameter
2. Creates split-brain (trigger vs backend)
3. If both run, duplicate key error
4. Partial failure states (wrong timezone)

## Industry Best Practice

**Supabase recommendation**: Use RLS policies for security, application code for business logic.

**User profile creation is business logic** (needs timezone from frontend), not data integrity.

**Triggers should be used for**:
- Audit logs
- Automatic timestamps
- Data integrity constraints
- NOT for business logic that requires application parameters

## Definitive Answer: Option B

### Why Option B is Correct

1. **Single source of truth**: Backend controls profile creation
2. **Correct from start**: Timezone set immediately
3. **Clean failure**: If INSERT fails, registration fails (correct)
4. **No split-brain**: One system, one operation
5. **Follows best practices**: Application code handles business logic

### Why Option C is Wrong

1. **Split-brain**: Two systems trying to manage same data
2. **Partial failures**: Wrong timezone but user can log in
3. **Complexity**: Two operations instead of one
4. **Against best practices**: Trigger doing business logic

## What Happens If Option B Fails?

**Scenario**: Backend INSERT fails during registration

**Result**:
- User exists in `auth.users` (Supabase Auth)
- No profile in `public.users`
- User tries to log in → `get_current_user` fails → "User not found"
- **This is CORRECT** - registration should fail completely if profile creation fails

**With Option C**:
- User exists in `auth.users`
- Profile exists in `public.users` (from trigger) with wrong timezone
- User can log in with wrong timezone
- **This is WRONG** - partial success state

## Final Recommendation

**Option B is definitively correct.**

The trigger was a workaround for missing INSERT policy. Now that we're adding the INSERT policy, the trigger is unnecessary and harmful.

## SQL to Run (Definitive)

```sql
-- Step 1: Add INSERT RLS policy (REQUIRED)
CREATE POLICY "Users can insert own profile" ON public.users
    FOR INSERT WITH CHECK (auth.uid() = id);

-- Step 2: Remove trigger (REQUIRED - prevents duplicate key errors)
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Step 3: Drop the function (optional, but clean)
DROP FUNCTION IF EXISTS public.handle_new_user();
```

## Code Changes (Definitive)

Replace `update_user_timezone()` with `create_user_profile()` that does INSERT.

See `OPTION_B_CODE_CHANGES.py` for exact code.

