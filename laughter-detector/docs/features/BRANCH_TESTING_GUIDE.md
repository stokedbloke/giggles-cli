# Testing Guide for ui-mobile-redesign Branch

**Branch:** `ui-mobile-redesign`  
**Date:** 2025-01-31

---

## Overview of Changes

This branch implements **Enhanced Processing Logger** with improved tracking and statistics for audio processing. Key changes:

1. **New Enhanced Logger** (`src/services/enhanced_logger.py`) - comprehensive step-by-step tracking
2. **API Call Tracking** - all Limitless API responses logged (200, 404, 5xx, errors)
3. **Processing Stats Fix** - `audio_files_downloaded` and `laughter_events_found` now accurate
4. **Date Fix** - reprocessing historical dates creates logs with correct dates
5. **Duplicate Skip Stats** - tracks three types of duplicates skipped
6. **UI Bug Fix** - reprocess button no longer stuck in "Processing..." state

---

## Testing Checklist

### ✅ 1. Basic Functionality Tests

#### Test 1.1: Login & Timezone Detection ⚠️ ENHANCED LOGGING
**Steps:**
1. Open app in browser
2. Open browser DevTools (F12) → Console tab
3. Log in with test account
4. Watch console logs for timezone information

**Expected Console Output:**
```
✅ Auth response: {user: {...}}
✅ /auth/me returned full response: { "user": {...} }
✅ User timezone set to: America/Los_Angeles
✅ Extracted from response.user?.timezone: America/Los_Angeles
```

**Alternative Verification (Network Tab):**
1. Open DevTools → Network tab
2. Clear existing requests
3. Refresh page or log in
4. Look for request to `/api/auth/me`
5. Click on request → Response tab
6. Should see JSON with `user.timezone` field

**Expected:**
- Console shows timezone detected
- User object includes `timezone` field (IANA format like "America/Los_Angeles")
- No errors in console

**Risk:** None

**Note:** If you don't see timezone logs, check:
- Browser console is open and not filtered
- User account exists in database with `timezone` field populated
- Server is running and `/auth/me` endpoint working

---

#### Test 1.2: Update Today's Count (Manual Processing)
**Steps:**
1. Navigate to home screen
2. Click "Update Today's Count"
3. Watch server logs
4. Wait for completion

**Expected:**
- Processing starts with enhanced logger initialization
- Server logs show processing steps
- UI shows success message
- Daily summary refreshes

**Database Check:**
```sql
SELECT * FROM processing_logs 
WHERE user_id = '<your-user-id>' 
ORDER BY date DESC LIMIT 1;
```

Should show:
- `date` = today's date
- `trigger_type` = "manual"
- `audio_files_downloaded` = number of successful downloads
- `laughter_events_found` = number of laughter detections
- `processing_steps` = JSONB with step-by-step details
- `api_calls` = JSONB with all API calls

**Risk:** MEDIUM - if enhanced_logger not initialized properly, stats will be 0

---

### ✅ 2. Enhanced Logger Tests

#### Test 2.1: Verify API Call Tracking
**Steps:**
1. Click "Update Today's Count"
2. Wait for processing
3. Check `processing_logs.api_calls` in database

**Expected:**
`api_calls` JSONB contains entries like:
```json
[
  {
    "endpoint": "download-audio",
    "status_code": 200,
    "duration_ms": 1234,
    "response_size_bytes": 512000,
    "params": {"startMs": ..., "endMs": ...}
  },
  {
    "endpoint": "download-audio",
    "status_code": 404,
    "duration_ms": 456,
    "response_size_bytes": 0,
    "error": "No audio data available"
  }
]
```

**Risk:** LOW - if not working, stats just won't populate

---

#### Test 2.2: Verify Processing Steps
**Steps:**
1. Click "Update Today's Count"
2. Check `processing_logs.processing_steps` in database

**Expected:**
Steps include:
- `processing_started`
- `api_key_decrypted`
- `date_range_calculated`
- `chunk_processing_started` (multiple)
- `chunk_processing_completed` (multiple)
- `yamnet_processing_completed`
- `processing_completed`

**Risk:** LOW - logging only, doesn't affect functionality

---

### ✅ 3. Reprocessing Tests

#### Test 3.1: Reprocess Single Day
**Steps:**
1. Go to Settings screen
2. Set start date = yesterday
3. Set end date = yesterday
4. Click "Reprocess Date Range"
5. Confirm

**Expected:**
- Server logs show cleanup deleting old data
- Redownload and reprocess
- One log entry in `processing_logs` with date = yesterday
- Log shows aggregated stats for that day

**Database Check:**
```sql
SELECT date, audio_files_downloaded, laughter_events_found 
FROM processing_logs 
WHERE user_id = '<your-user-id>' 
  AND date = '<yesterday>';
```

**Risk:** MEDIUM - destructive operation, deletes existing data

---

#### Test 3.2: Reprocess Date Range
**Steps:**
1. Go to Settings screen
2. Set start date = 3 days ago
3. Set end date = 2 days ago
4. Click "Reprocess Date Range"
5. Confirm

**Expected:**
- **ONE log entry** with date = start_date (3 days ago)
- Aggregated stats across entire range
- No separate log for end_date

**Database Check:**
```sql
SELECT date, COUNT(*) 
FROM processing_logs 
WHERE user_id = '<your-user-id>' 
  AND date BETWEEN '<start>' AND '<end>';
```

Should return 1 row (for start_date only).

**Risk:** MEDIUM - important to understand this behavior

**Known Issue:** Only one log created for date range, not per-day. This is current design.

---

#### Test 3.3: Reprocess Button State Fix
**Steps:**
1. Navigate to Settings screen
2. Observe reprocess button state
3. Click "Reprocess" without dates
4. Click away, come back to Settings
5. Observe button state again

**Expected:**
- Button shows "Reprocess Date Range" (not "Processing...")
- Button is enabled
- Only ONE confirmation popup per click

**Risk:** LOW - UI fix only

---

### ✅ 4. Statistics Accuracy Tests

#### Test 4.1: Verify audio_files_downloaded
**Steps:**
1. Click "Update Today's Count"
2. Let it complete
3. Check `processing_logs.audio_files_downloaded`

**Expected:**
- Matches number of 200 responses in `api_calls` with `response_size_bytes > 0`
- Represents actual OGG files downloaded from Limitless

**Manual Verification:**
```sql
SELECT 
  audio_files_downloaded,
  (SELECT COUNT(*) FROM jsonb_array_elements(api_calls) 
   WHERE (value->>'status_code')::int = 200 
     AND (value->>'response_size_bytes')::int > 0
  ) as actual_200s
FROM processing_logs 
WHERE user_id = '<your-user-id>' 
ORDER BY date DESC LIMIT 1;
```

Should match.

**Risk:** MEDIUM - previously was always 0, now should be accurate

---

#### Test 4.2: Verify laughter_events_found
**Steps:**
1. Process today's audio
2. Check `processing_logs.laughter_events_found`
3. Check actual `laughter_detections` count

**Expected:**
- `laughter_events_found` = YAMNet detections (raw count)
- Actual stored detections may be lower due to duplicates
- Check console logs for "Laughter Events Found: X"

**Risk:** LOW - should be accurate

---

#### Test 4.3: Verify duplicates_skipped
**Steps:**
1. Reprocess a day with existing data (will create duplicates)
2. Check console logs for "Duplicates Skipped"
3. Check `processing_steps` metadata

**Expected:**
Console shows:
```
⏭️ Duplicates Skipped: 15 (time-window: 10, clip-path: 3, missing-file: 2)
```

**Risk:** LOW - informational only

---

### ✅ 5. Edge Cases

#### Test 5.1: No Audio Data (404s)
**Steps:**
1. Reprocess a day with no Limitless audio
2. Watch server logs
3. Check `processing_logs`

**Expected:**
- Multiple 404 responses logged
- `audio_files_downloaded` = 0
- `laughter_events_found` = 0
- `failed_api_calls` > 0
- Status = "completed" (not error)

**Risk:** LOW - graceful handling

---

#### Test 5.2: Limitless API Gateway Errors
**Steps:**
1. Trigger processing during Limitless downtime
2. Watch server logs

**Expected:**
- 502/503/504 errors logged with warnings
- Chunks skipped
- Processing continues
- Not treated as fatal errors

**Risk:** LOW - MVP graceful degradation

---

#### Test 5.3: Duplicate Processing
**Steps:**
1. Click "Update Today's Count" twice in a row
2. Watch server logs

**Expected:**
- Second run shows "already processed" for all chunks
- OGG files deleted even if skipped
- No duplicate detections created
- Log shows chunks skipped

**Risk:** LOW - duplicate prevention working

---

### ✅ 6. UI Tests

#### Test 6.1: Date Display
**Steps:**
1. Open app
2. Click a day in the summary
3. Verify date in header matches clicked day

**Expected:**
- "Wednesday (X)" header shows correct weekday
- Date matches day clicked, not shifted

**Risk:** LOW - timezone fix already tested

---

#### Test 6.2: Daily Summary Refresh After Processing
**Steps:**
1. Click "Update Today's Count"
2. Wait for "Processing completed!" toast
3. Check if daily summary refreshes automatically

**Expected:**
- Today's card shows updated count
- Card background changes color
- No manual refresh needed

**Risk:** LOW - standard behavior

---

#### Test 6.3: Daily Summary Refresh After Deletion ⚠️ NEW FIX
**Steps:**
1. Navigate to a day with detections (e.g., Monday Nov 3 with 1 detection)
2. Delete one detection
3. Confirm day detail shows "No detections" message
4. Navigate back to home screen
5. Check if count is updated

**Expected:**
- Day detail correctly shows 0 after deletion
- Home screen shows correct count (e.g., Monday shows "No giggles" or removed)
- **No need to logout/login** to see updated count
- Console logs show both day detail AND summary refreshed

**Database Verification:**
```sql
SELECT COUNT(*) FROM laughter_detections 
WHERE user_id = '<your-user-id>' 
  AND DATE(timestamp) = '2025-11-03';
```
Should return 0 (after deletion).

**Risk:** LOW - UI fix only  
**Status:** ✅ FIXED in this branch

---

### ✅ 7. Manual Sanity Checks

#### Check 7.1: Console Logs
After processing, verify console shows:
```
📋 Step: processing_started - INFO: Starting audio processing
🌐 API Call: download-audio - SUCCESS (200) - 1234ms
📊 PROCESSING SESSION SUMMARY
====================================================
⏱️ Duration: 45 seconds
📁 Audio Files Downloaded: 12
🎭 Laughter Events Found: 150
⏭️ Duplicates Skipped: 20
🌐 API Calls: 12 (✅ 12 success, ❌ 0 failed)
```

**Risk:** None

---

#### Check 7.2: Database Integrity
Run queries to verify data consistency:

```sql
-- Total laughter detections should match sum of laughter_events_found (minus duplicates)
SELECT 
  COUNT(*) as total_detections,
  SUM(laughter_events_found) as reported_events
FROM laughter_detections ld
JOIN processing_logs pl ON DATE(ld.timestamp) = pl.date
WHERE ld.user_id = '<your-user-id>';
```

**Risk:** MEDIUM - validates core data accuracy

---

## 🚨 Known Issues / Warnings

### 1. Single Log for Date Ranges
**Issue:** Reprocessing multiple days creates ONE log for start_date only  
**Impact:** Can't see per-day breakdown in logs  
**Workaround:** Use `laughter_detections` table for per-day queries  
**Fix Needed:** Create separate logs per day (future enhancement)

### 2. Legacy Columns Always 0
**Issue:** `processed_segments` and `total_segments` always 0  
**Impact:** None - deprecated  
**Action:** Safe to drop these columns  
**Status:** Documented, not a bug

### 3. Enhanced Logger Only in Processing Context
**Issue:** `get_current_logger()` returns None if called outside processing  
**Impact:** None - gracefully handled  
**Action:** None needed

---

## ⚠️ Risky Code Areas

### 1. `enhanced_logger.py` - New Service
**Risk:** HIGH  
**Reason:** Brand new code, untested  
**Testing:** Thoroughly test all stats accuracy  
**Fallback:** If broken, stats will be 0 but functionality works

---

### 2. `manual_reprocess_yesterday.py` - Date Handling
**Risk:** MEDIUM  
**Reason:** Fixes historical date logging  
**Testing:** Verify logs have correct dates after reprocessing  
**Fallback:** Wrong date in logs, but processing works correctly

---

### 3. `scheduler.py` - Processing Flow Changes
**Risk:** MEDIUM  
**Reason:** Major refactor of logging  
**Testing:** Verify "Update Today's Count" still works  
**Fallback:** Processing fails if enhanced_logger broken

---

### 4. `limitless_api.py` - API Call Tracking
**Risk:** LOW  
**Reason:** Only adds logging, doesn't change core logic  
**Testing:** Verify stats populate  
**Fallback:** Stats stay 0

---

## 🔒 Security Considerations

### Enhanced Logger
- Uses service role key for admin operations (line 166 in `enhanced_logger.py`)
- All user data access via RLS-compliant queries
- No PII logged in processing steps

**Risk:** LOW - only logs data user already has access to

---

## 📊 Performance Impact

**Expected:** Minimal  
**Reason:** Enhanced logging is async and lightweight  
**Monitoring:** Watch for increased processing time  
**Action:** If >10% slower, optimize logging calls

---

## 🧹 Cleanup Tasks

After testing complete:

1. ✅ Drop legacy columns (`processed_segments`, `total_segments`)
2. ✅ Remove debug logs (🔍 DEBUG lines)
3. ✅ Review if all console.logs needed in production
4. ✅ Consider adding `duplicates_skipped` as separate column

---

## 🎯 Success Criteria

Branch is ready to merge if:

- ✅ All basic functionality tests pass
- ✅ Statistics are accurate (<5% variance from expected)
- ✅ No crashes or errors in production scenarios
- ✅ Reprocessing works correctly
- ✅ UI bugs fixed (button state, date display)
- ✅ Database logs populated correctly
- ✅ Performance impact <10%

---

## 🆘 Rollback Plan

If critical issues found:

1. **Immediate:** Revert `enhanced_logger.py` integration in `scheduler.py`
2. **Quick:** Remove `src/services/enhanced_logger.py` entirely
3. **Full:** Reset to main branch, cherry-pick non-logger fixes

**Estimated downtime:** < 5 minutes  
**Data loss:** None

---

## 📝 Notes for PR

- Document that date range reprocessing creates single aggregated log
- Note legacy columns are deprecated but still in DB schema
- Recommend dropping `processed_segments`/`total_segments` in migration
- Consider adding per-day logging for date ranges (future enhancement)

