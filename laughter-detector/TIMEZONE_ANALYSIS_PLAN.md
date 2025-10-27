# Timezone Handling Analysis & Plan

**Date:** 2024-10-27  
**Branch:** `fix-timezone-handling`  
**Status:** Analysis Phase

---

## 🎯 Problem Statement

Currently, timestamps are stored in the database as `TIMESTAMPTZ` (timezone-aware), but the handling of user timezones is inconsistent. We need to:

1. **Store all timestamps in UTC** (database does this automatically)
2. **Convert to user's timezone for display** (frontend/API)
3. **Use user's timezone for daily boundaries** (scheduler/processing)

---

## 📊 Current State Analysis

### ✅ What Works
- **Database**: All `TIMESTAMPTZ` columns properly store timezone-aware timestamps
- **Timezone column exists**: `users.timezone` field in database
- **Partial implementation**: Scheduler uses `user.get('timezone', 'UTC')`

### ⚠️ What's Broken
1. **Registration** sets timezone to hardcoded 'UTC' instead of detecting user's timezone
2. **No timezone update mechanism** - users can't set their timezone
3. **Frontend** doesn't convert timestamps to user's local time
4. **Scheduler** uses timezone for processing but doesn't handle it consistently
5. **API responses** return UTC timestamps without conversion

---

## 🔍 Is User Timezone Reliable?

**YES** - with caveats:

### ✅ Reliable Sources
1. **Browser's `Intl.DateTimeFormat().resolvedOptions().timeZone`**
   - Returns IANA timezone (e.g., "America/New_York")
   - Works reliably in all modern browsers
   - No user permission required

2. **User Profile Settings**
   - Once set, can be stored in database
   - Persists across sessions
   - User can manually override browser detection

### ⚠️ Considerations
1. **Daylight Saving Time (DST)**: 
   - IANA timezones handle DST automatically
   - Use libraries like `pytz` or `zoneinfo` for server-side

2. **Users Traveling**: 
   - If user travels across timezones, frontend will detect new timezone
   - May want to prompt user to confirm timezone change

3. **Server Timezone**:
   - Should ALWAYS be UTC
   - Only convert for display/processing

---

## 🎨 Design Principles

### 1. Storage Principle
```
All timestamps stored in UTC in database
```

### 2. Conversion Principle
```
Display timestamps in user's local timezone
Process using user's configured timezone
```

### 3. User Experience
```
- Detect user's timezone on registration/login
- Allow user to override timezone preference
- Display all times in user's local timezone
- Process "today" based on user's timezone
```

---

## 📋 Implementation Plan

### Phase 1: Timezone Detection & Storage

#### 1.1 Frontend: Detect User's Timezone
**File:** `static/js/app.js`

```javascript
// Get user's timezone
function getUserTimezone() {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

// Send timezone to backend on registration/login
```

**Action Items:**
- [ ] Add timezone to registration payload
- [ ] Add timezone to login response
- [ ] Store user's timezone in user object

#### 1.2 Backend: Store Timezone
**File:** `src/auth/supabase_auth.py`

```python
async def register(self, email: str, password: str, timezone: str = "UTC"):
    # Store user with timezone
```

**Action Items:**
- [ ] Update registration endpoint to accept `timezone` parameter
- [ ] Default to "UTC" if not provided
- [ ] Store timezone in `users.timezone` column

### Phase 2: Timezone Update Mechanism

#### 2.1 API Endpoint
**File:** `src/api/user_routes.py` (new file)

```python
@router.put("/settings/timezone")
async def update_timezone(
    timezone: str,
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """Update user's timezone preference."""
```

**Action Items:**
- [ ] Create `user_routes.py` for user settings
- [ ] Add endpoint to update timezone
- [ ] Add validation for IANA timezone strings

#### 2.2 UI Component
**File:** `templates/index.html` or new settings page

```html
<select id="timezone-selector">
  <!-- Populated with common timezones -->
</select>
```

**Action Items:**
- [ ] Add timezone selector to UI
- [ ] Send timezone update to API
- [ ] Refresh UI after update

### Phase 3: Timestamp Display Conversion

#### 3.1 Backend: Return Timezone Info
**File:** `src/api/data_routes.py`

```python
# Include user's timezone in responses
user_timezone = user.get('timezone', 'UTC')

# Optionally convert timestamps client-side
```

**Action Items:**
- [ ] Include timezone in API responses
- [ ] Or: Convert timestamps server-side (depends on preference)

#### 3.2 Frontend: Display in User's Timezone
**File:** `static/js/app.js`

```javascript
function formatTimestamp(utcTimestamp, userTimezone) {
    const date = new Date(utcTimestamp);
    return date.toLocaleString('en-US', {
        timeZone: userTimezone,
        dateStyle: 'short',
        timeStyle: 'short'
    });
}
```

**Action Items:**
- [ ] Create utility function to format timestamps
- [ ] Use `toLocaleString()` with user's timezone
- [ ] Update all timestamp displays in UI

### Phase 4: Processing with User Timezone

#### 4.1 Scheduler: Use User Timezone for Daily Boundaries
**File:** `src/services/scheduler.py`

Already partially implemented:
```python
now = datetime.now(pytz.timezone(user.get('timezone', 'UTC')))
```

**Action Items:**
- [ ] Verify timezone is being used correctly
- [ ] Add logging to show timezone in use
- [ ] Test with different timezones

#### 4.2 Daily Summary: Group by User's Local Date
**File:** `src/api/data_routes.py`

```python
# Group laughter detections by date in user's timezone
```

**Action Items:**
- [ ] Convert dates to user's timezone before grouping
- [ ] Ensure "today" means today in user's timezone

---

## 🧪 Testing Plan

### Test Cases

1. **Timezone Detection**
   - [ ] User registers from different timezone
   - [ ] Verify timezone is detected and stored
   - [ ] Verify default to UTC if detection fails

2. **Timezone Conversion**
   - [ ] Display timestamps in user's local time
   - [ ] Verify dates group correctly by local day
   - [ ] Test with timezone that's behind UTC
   - [ ] Test with timezone that's ahead of UTC

3. **Daily Processing**
   - [ ] Process "today" respects user's timezone
   - [ ] Midnight boundaries are in user's timezone
   - [ ] Test edge case: user in timezone when it's tomorrow

4. **DST Handling**
   - [ ] Test during DST transitions
   - [ ] Verify timestamps remain correct

---

## 📚 Resources

### Python Libraries
- `pytz`: Timezone database (already in use)
- `zoneinfo`: Python 3.9+ standard library alternative

### JavaScript APIs
- `Intl.DateTimeFormat().resolvedOptions().timeZone`
- `toLocaleString()` with `timeZone` option

### IANA Timezone Database
- Valid timezone strings: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
- Examples: "America/New_York", "Europe/London", "Asia/Tokyo"

---

## 🎯 Success Criteria

1. ✅ User's timezone is detected on registration
2. ✅ User can update their timezone preference
3. ✅ All timestamps display in user's local timezone
4. ✅ "Today" means today in user's timezone
5. ✅ Processing scheduler respects user's timezone
6. ✅ No timezone-related bugs in testing

---

## 🚨 Potential Issues

### Issue 1: Old Users with UTC Timezone
**Problem:** Existing users will have timezone = 'UTC'  
**Solution:** Prompt users to set their timezone on first login after update

### Issue 2: Mobile Browser Detection
**Problem:** Mobile browsers may not always detect timezone correctly  
**Solution:** Allow manual override, provide timezone picker

### Issue 3: Server Deployment Timezone
**Problem:** Production server must be in UTC  
**Solution:** Verify server timezone in deployment

---

## 📝 Next Steps

1. **Start with Phase 1**: Detect timezone on registration
2. **Add timezone update endpoint** (Phase 2)
3. **Update frontend to display local time** (Phase 3)
4. **Test thoroughly** with different timezones
5. **Deploy incrementally** and monitor for issues

---

## 💡 Recommendation

**Start Small**: Implement Phase 1 only (detect and store timezone). Then gradually add features:
- First: Just store timezone
- Second: Use it for daily boundaries in scheduler
- Third: Add timezone update mechanism
- Fourth: Convert display timestamps

This incremental approach reduces risk and makes debugging easier.
