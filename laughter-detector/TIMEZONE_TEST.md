# Timezone Testing Guide

## Quick Test Steps

### 1. Check Your Timezone in Database
In Supabase, your timezone should be set to: `America/Los_Angeles`

### 2. Test Timezone Detection (Console)
After logging in, open browser console (F12) and run:

```javascript
// Check if timezone is detected
console.log('My timezone:', window.app.userTimezone);

// Check what browser detects
console.log('Browser detects:', Intl.DateTimeFormat().resolvedOptions().timeZone);
```

**Expected Output:**
- `My timezone: America/Los_Angeles` (or whatever you set in database)
- `Browser detects: America/Los_Angeles` (should match)

### 3. Test Timestamp Display (UI)

1. Click on a day with laughter detections
2. Look at the timestamps displayed (e.g., "05:05:08 PM")
3. Compare with what you expect in PST

**What Changed:**
- Before: Timestamps were in UTC
- After: Timestamps are converted to your local timezone (PST)

**Example:**
- If timestamp in DB is: `2025-10-26T00:05:08+00:00` (UTC midnight)
- You should see: `05:05:08 PM` (PST time on Oct 25th)

### 4. Test Daily Boundaries (Processing)

1. Click "Update Today's Count" button
2. Check server logs (terminal)
3. Should see timezone-aware processing:

```
Processing chunk 1: 2025-10-27 00:00:00-07:00 to 2025-10-27 02:00:00-07:00
```

**What Changed:**
- Before: Processed based on UTC day boundaries
- After: Processes based on PST day boundaries
- This fixes "33 laughs on wrong day" issue

### 5. Quick Console Test Commands

Open browser console and run these:

```javascript
// Test 1: Check timezone storage
console.log('User timezone:', window.app.userTimezone);

// Test 2: Check timezone detection
console.log('Detected timezone:', window.app.detectTimezone());

// Test 3: Test timestamp formatting
const testDate = new Date('2025-10-27T12:00:00Z'); // Noon UTC
const formatted = window.app.formatTimestampToTimezone(
    testDate.toISOString(), 
    'America/Los_Angeles'
);
console.log('Formatted timestamp:', formatted); // Should show 05:00 AM (PST is UTC-7)
```

## What Was Implemented

### Phase 1: ✅ Detection & Storage
- Detects timezone on registration/login
- Stores in database
- Retrieves on login

### Phase 3: ✅ Timestamp Display
- All timestamps converted to user's timezone
- Uses `formatTimestampToTimezone()` method

### Phase 4: ✅ Daily Boundaries
- Scheduler uses user's timezone for "today"
- Converts to UTC for API calls
- Stores everything in UTC

## Troubleshooting

### No console logs?
- Check browser console filter settings
- Try hard refresh (Cmd+Shift+R)

### Timezone still showing UTC?
- Check Supabase database
- Make sure you updated the `timezone` field
- Log out and log back in

### Timestamps still wrong?
- Check that timezone is set correctly in DB
- Hard refresh the page (Cmd+Shift+R)
- Check console for errors
