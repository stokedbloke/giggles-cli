# Timezone Implementation: Testing & Migration Plan

**Key Questions Answered:**
1. When will detection happen? **On registration, login fallback**
2. Need new account? **No - can update existing users**
3. Need DB changes? **No - timezone column already exists**

---

## ✅ Database Status

**Good News:** The database is already set up!

```sql
-- From setup_database.sql line 12
timezone TEXT DEFAULT 'UTC',
```

The `users` table already has:
- ✅ `timezone` column exists
- ✅ Defaults to 'UTC'
- ✅ No migration needed

**Existing users:** Already have `timezone = 'UTC'`, which will be updated on first login.

---

## 🔄 Detection Timeline

### Option A: Registration + Login Fallback (Recommended)

**Detection happens in 2 places:**

1. **During Registration:**
   ```javascript
   // Frontend detects timezone
   const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
   
   // Sends to backend during registration
   POST /auth/register { email, password, timezone }
   ```

2. **During Login (Fallback for existing users):**
   ```javascript
   // If user timezone is 'UTC' (old user), detect on login
   if (user.timezone === 'UTC') {
       const detectedTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
       await updateTimezone(detectedTimezone);
   }
   ```

**Benefits:**
- ✅ Existing users automatically get timezone on next login
- ✅ New users get timezone on registration
- ✅ No need to create new account to test
- ✅ One-time detection, stored in database

---

## 🧪 Testing Scenarios

### Scenario 1: New User Registration
1. User registers via UI
2. Frontend detects timezone (browser)
3. Backend stores timezone in database
4. User profile has timezone set

### Scenario 2: Existing User Login
1. User logs in
2. Frontend checks if timezone is 'UTC' (default)
3. If yes, detect and update timezone
4. Store in database for future logins

### Scenario 3: Manual Timezone Update (Phase 2)
1. User goes to settings
2. User selects timezone from dropdown
3. Backend updates `users.timezone` column
4. UI refreshes with new timezone

---

## 🔧 Implementation Details

### Frontend Changes

**File:** `static/js/app.js`

```javascript
// Detection function
function detectTimezone() {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

// During registration
async function register(email, password) {
    const timezone = detectTimezone(); // e.g., "America/Los_Angeles"
    const response = await fetch('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, timezone })
    });
}

// During login (fallback for existing users)
async function handleLogin(user) {
    if (user.timezone === 'UTC') {
        const detectedTimezone = detectTimezone();
        await updateUserTimezone(detectedTimezone);
    }
}
```

### Backend Changes

**File:** `src/auth/supabase_auth.py`

```python
async def register_user(self, email: str, password: str, timezone: str = "UTC"):
    """Register new user with timezone."""
    # ... existing registration logic ...
    
    # Create user profile with detected timezone
    await self.create_user_profile(
        user_id=response.user.id, 
        email=response.user.email,
        timezone=timezone  # <-- NEW parameter
    )

async def create_user_profile(self, user_id: str, email: str, timezone: str = "UTC"):
    """Create user profile with timezone."""
    result = self.supabase.table("users").insert({
        "id": user_id,
        "email": email,
        "timezone": timezone,  # <-- Store detected timezone
        "is_active": True,
        "mfa_enabled": True
    }).execute()
```

---

## 📋 Migration Path for Existing Users

### Automatic Migration (Recommended)

**On login, check and update:**

```javascript
// Frontend: static/js/app.js
async function handleLogin(response) {
    const user = response.user;
    
    // If old user (timezone = 'UTC'), update it
    if (user.timezone === 'UTC') {
        const detectedTimezone = detectTimezone();
        await updateTimezone(detectedTimezone);
        console.log(`Updated timezone from UTC to ${detectedTimezone}`);
    }
}

async function updateTimezone(timezone) {
    await fetch('/api/settings/timezone', {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${authToken}` },
        body: JSON.stringify({ timezone })
    });
}
```

**Alternative: One-time manual update**

You can also manually update your existing account:

```sql
-- Run in Supabase SQL Editor
UPDATE public.users 
SET timezone = 'America/Los_Angeles'  -- Your timezone
WHERE email = 'your@email.com';
```

---

## 🎯 Testing Without New Account

**You can test with your existing account:**

1. **Manual DB Update (Fastest for testing):**
   ```sql
   UPDATE public.users 
   SET timezone = 'America/Los_Angeles'
   WHERE email = 'your@email.com';
   ```

2. **Wait for Login Detection:**
   - Implement timezone detection on login
   - Login to your account
   - Timezone will be auto-detected and updated

3. **Use Settings Page (Phase 2):**
   - Add timezone selector to UI
   - Manually select your timezone
   - Save to database

---

## ✅ Summary

**Database:** ✅ Already has `timezone` column  
**New account:** ❌ Not needed - can update existing account  
**Migration:** ✅ Automatic on login, or manual SQL update  
**Testing:** Can test immediately by updating your existing user

**Next Steps:**
1. Implement timezone detection on frontend
2. Update registration to accept timezone parameter
3. Add login fallback to detect timezone for existing users
4. Test with your existing account (or update manually first)
