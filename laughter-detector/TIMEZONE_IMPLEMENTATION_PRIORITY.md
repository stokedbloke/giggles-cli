# Timezone Implementation Priority

**Based on your specific issue analysis**  
**Branch:** `fix-timezone-handling`

---

## 🎯 Immediate Problem

You're seeing **date allocation errors**:
- Oct 25th clips show times: 9am → 5pm → 7pm → **12pm** (out of order)
- Home screen shows "33 laughs on Sunday Oct 26" when those should be Oct 25th
- This happens because system uses **UTC day boundaries** but you're in **PST (UTC-7)**

---

## ✅ MVP Approach: Simple & Reliable

### 1. Storing Timezone on Registration
**YES - This makes sense for MVP**

**Why it works:**
- Most users don't travel frequently
- If they travel, they can manually update timezone (Phase 2)
- Registration timezone = "home timezone" is a reasonable default
- Can add auto-detection on login later if needed

**Store:**
- IANA timezone string: `"America/Los_Angeles"` (for PST)
- Default to UTC if detection fails

### 2. Files on Disk & Database
**YES - Everything in UTC**

**Database timestamps:**
- All `TIMESTAMPTZ` columns store UTC
- PostgreSQL does this automatically
- ✅ Already correct in your schema

**Files on disk:**
- Filenames should use UTC timestamps
- Example: `2025-10-27_19-30-00.ogg` (UTC)
- This ensures consistency if files are moved

**Client-side rendering:**
- Frontend converts UTC → user's local timezone for display
- Groups into "days" based on user's local timezone boundaries
- ✅ This is the key fix for your issue

---

## 🔧 Your Specific PST Issue

### The Problem
```
Your time: 11:55 PM PST on Oct 25th
UTC time:  06:55 AM on Oct 26th (PST = UTC-7)

Current system:
- Uses UTC day boundaries
- Considers "today" = Oct 26th in UTC
- Pulls audio for Oct 26th UTC
- Displays as "Oct 26th" with 33 laughs
```

### The Solution (With Your +7h Example)
```
Your time: 11:55 PM PST on Oct 25th
User timezone: PST (UTC-7)

System should:
1. Detect you're in PST
2. Define "today" as Oct 25th (in PST)
3. Calculate UTC range for Oct 25th PST:
   - Start: 00:00 PST Oct 25 = 07:00 UTC Oct 25
   - End:   23:59 PST Oct 25 = 06:59 UTC Oct 26
4. Pull audio from Limitless using UTC range
5. Process and store in UTC
6. Display grouped by local days
```

**This fixes:**
- Clips correctly allocated to Oct 25th
- No more "33 laughs on wrong day"
- Timestamps display in order

---

## 📋 Implementation Order

### Phase 1: Detect & Store (Foundation)
1. Detect timezone in browser during registration
2. Send to backend, store in `users.timezone`
3. Default to UTC if detection fails

**Files to modify:**
- `static/js/app.js` - detect timezone
- `src/auth/supabase_auth.py` - accept and store timezone

### Phase 4: Use for Daily Boundaries (Critical Fix)
1. When user clicks "Update Today's Count"
2. Get user's timezone from database
3. Calculate "today" in user's timezone
4. Convert to UTC range for API queries
5. Pull audio, process, store in UTC
6. Display grouped by local days

**Files to modify:**
- `src/services/scheduler.py` - use timezone for date ranges
- `src/api/audio_routes.py` - manual trigger respects timezone

### Phase 3: Convert Display (UI Fix)
1. All timestamps displayed in user's local time
2. Days grouped by local timezone boundaries
3. Fix the "7pm → 12pm" ordering issue

**Files to modify:**
- `static/js/app.js` - format timestamps for display
- `src/api/data_routes.py` - include timezone in responses

### Phase 2: Update Mechanism (Nice to Have)
Add timezone selector in settings (can wait)

---

## 🎯 Simplified Approach for Your Case

Since you're in **PST (UTC-7)**, the logic is:

```python
# 1. Get user's timezone
timezone = user.get('timezone', 'UTC')  # e.g., 'America/Los_Angeles'

# 2. Define "today" in user's timezone
user_tz = pytz.timezone(timezone)
now_local = datetime.now(user_tz)
today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
today_end = now_local.replace(hour=23, minute=59, second=59, microsecond=999999)

# 3. Convert to UTC for API
today_start_utc = today_start.astimezone(pytz.UTC)
today_end_utc = today_end.astimezone(pytz.UTC)

# 4. Pull audio for UTC range
# Limitless API called with UTC timestamps
# Results stored with UTC timestamps
# Display converts back to PST
```

**Result:**
- ✅ "Today" means "today in PST"
- ✅ Audio pulled for correct time range
- ✅ Everything stored in UTC
- ✅ Displayed in PST
- ✅ Days group correctly

---

## 🚀 Next Step

Let's start with **Phase 1 + Phase 4** together:

1. Detect timezone on registration
2. Store it
3. Use it immediately for "Update Today's Count"

This fixes your immediate issue without waiting for the full 4-phase rollout.

Ready to implement?
