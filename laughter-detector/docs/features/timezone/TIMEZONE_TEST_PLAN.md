# Timezone Implementation Test Plan

**Date:** 2024-10-27  
**Branch:** `fix-timezone-handling`  
**Status:** Ready for Testing

---

## 🎯 What Was Fixed

### Backend Changes
1. ✅ **`src/services/scheduler.py`** - Fixed `AudioSegmentCreate.id` bug (lines 174-176)
2. ✅ **`src/api/data_routes.py`** - Timezone-aware daily boundaries (lines 170-189)
3. ✅ **`src/api/data_routes.py`** - Timezone-aware daily summary grouping (lines 85-130)
4. ✅ **`src/auth/supabase_auth.py`** - Timezone storage on registration

### Frontend Changes
1. ✅ **`static/js/app.js`** - Timezone detection on registration (line 190)
2. ✅ **`static/js/app.js`** - Timestamp formatting utility (lines 392-409)
3. ✅ **`static/js/app.js`** - Use formatted timestamps in display (line 416)
4. ✅ **`static/js/app.js`** - Fixed date header parsing (line 607)

---

## 🧪 Test Plan

### Test 1: Verify Timezone Detection (Registration)

**Steps:**
1. Delete all your data and logout
2. Register a new account
3. Check browser console for timezone logs

**Expected Console Output:**
```
🌍 Browser detected timezone: America/Los_Angeles
✅ Timezone sent to backend: America/Los_Angeles
```

**Verification:**
- Run in browser console: `console.log('My timezone:', window.app.userTimezone)`
- Should see: `My timezone: America/Los_Angeles`

**What Success Looks Like:**
- ✅ User account created with timezone stored
- ✅ No errors in console

---

### Test 2: Verify Daily Summary Date Grouping

**Steps:**
1. After "Delete All Data" and "Update Today's Count"
2. Look at the home screen daily summary
3. Check that dates match your local calendar

**What to Look For:**
- Click "Delete All Data" button
- Click "Update Today's Count" 
- Look at the date cards on home screen
- Dates should match your local calendar (not UTC)

**Expected Behavior:**
```
Example (if today is Oct 27, 2025 in PST):
❌ BEFORE: Shows "Oct 28, 2025" (UTC time)
✅ AFTER:  Shows "Oct 27, 2025" (PST time)
```

**Verification:**
- Dates on summary cards should match your calendar
- No laughter events on "wrong day"

---

### Test 3: Verify Timestamp Display (Day Detail View)

**Steps:**
1. Click on a day with laughter detections
2. Look at individual timestamps
3. Verify they're in PST, not UTC

**What to Look For:**
- Open a day with laughter (e.g., "Thursday Oct 27")
- Look at the time for each laughter event
- Times should be in your local timezone

**Expected Behavior:**
If a laughter event occurred at 5:00 PM your local time:
```
❌ BEFORE: Shows "00:00:00" (UTC midnight)
✅ AFTER:  Shows "17:00:00" (PST 5 PM)
```

**Verification:**
- Timestamps should be in 12-hour format with AM/PM
- Times should match when laughter actually happened

---

### Test 4: Verify Date Header in Detail View

**Steps:**
1. Click on a day card
2. Check the date header at the top of the detail view
3. Verify it shows the correct day name and date

**What to Look For:**
- After clicking "Monday (4)" should show "Monday, October 27, 2025"
- Not "Tuesday, October 28, 2025"

**Expected Behavior:**
```
❌ BEFORE: Clicking "Monday" shows "Tuesday" (timezone shift)
✅ AFTER:  Clicking "Monday" shows "Monday"
```

**Verification:**
- Day name in header matches day clicked
- Date matches your calendar

---

### Test 5: Verify Scheduler Bug Fix (File Deletion)

**Steps:**
1. Delete all data
2. Click "Update Today's Count"
3. Let processing complete
4. Check for OGG files on disk

**What to Look For:**
- After processing completes
- Navigate to `uploads/audio/[user-id]/` folder
- Should be empty (no .ogg files)

**Expected Behavior:**
```
BEFORE: 7 OGG files remain on disk (bug)
AFTER:  0 OGG files (cleanup working)
```

**Verification:**
- Run: `ls -la /Users/neilsethi/git/giggles-cli/laughter-detector/uploads/audio/`
- Should show empty or only old files from before fix

---

## 🔧 How to Run Tests

### Quick Test Script

Open browser console (F12) and run:

```javascript
// Test 1: Timezone detection
console.log('Detected timezone:', Intl.DateTimeFormat().resolvedOptions().timeZone);
console.log('User timezone:', window.app.userTimezone);

// Test 2: Test timestamp formatting
const testDate = new Date('2025-10-27T12:00:00Z'); // Noon UTC
const formatted = window.app.formatTimestampToTimezone(
    testDate.toISOString(), 
    'America/Los_Angeles'
);
console.log('Formatted timestamp:', formatted); // Should show 05:00 AM (PST is UTC-7)

// Test 3: Check daily summary
console.log('Current date:', this.currentDate);
```

### Server Log Monitoring

Watch server logs for timezone processing:

```bash
tail -f /tmp/uvicorn.log | grep -E "(timezone|Processing chunk|deleted)"
```

**Expected Output:**
```
Processing chunk 1: 2025-10-27 00:00:00-07:00 to 2025-10-27 02:00:00-07:00
✅ Deleted audio file: /path/to/file.ogg
```

---

## ❌ What NOT to Test Yet

**Skip these for now (future features):**
- Timezone update on login (not implemented)
- Manual timezone changes (not implemented)
- Traveling across timezones (not implemented)

---

## 📊 Success Criteria

✅ **All 5 tests pass**
✅ **No console errors**
✅ **Dates match local calendar**
✅ **Timestamps in PST**
✅ **Files deleted after processing**
✅ **No "wrong day" grouping**

---

## 🚨 Known Issues (Acceptable for MVP)

1. **Timezone updates** - Users can't manually change timezone yet (Phase 2 feature)
2. **Auto-timezone on login** - Not implemented yet (user gets timezone on registration only)
3. **DST handling** - Should work automatically via IANA timezone, but not explicitly tested

---

## 📝 Next Steps After Testing

1. **If all tests pass:**
   - Commit timezone fixes
   - Merge to main
   - Proceed to next feature branch (UI updates & cron)

2. **If any test fails:**
   - Document specific failure
   - Re-evaluate approach
   - Fix and re-test

