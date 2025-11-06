# True Dress Rehearsal Test Plan

## Objective

Perform a complete, verifiable dress rehearsal that exactly mirrors the scheduled cron job execution, with full logging and verification at each step.

---

## Prerequisites

1. **Clean State:** All data for the test date must be deleted from:
   - Database (processing_logs, laughter_detections, audio_segments)
   - Disk (OGG files in `/uploads/audio/{user_id}/`, WAV clips in `/uploads/clips/{user_id}/`)

2. **Test Date Selection:**
   - Choose a date that:
     - Has audio data available from Limitless API
     - Is NOT today (to test "yesterday" processing)
     - Example: If today is Nov 4, use Nov 3

3. **Verification Tools Ready:**
   - Database query scripts
   - File system verification scripts
   - Log file monitoring

---

## Test Steps

### Step 0: Baseline Verification (BEFORE cleanup)

**Purpose:** Document the current state before starting

**Actions:**
1. Query database for test date:
   ```sql
   -- Processing logs
   SELECT * FROM processing_logs WHERE user_id = '{user_id}' AND date = '{test_date}';
   
   -- Laughter detections
   SELECT COUNT(*) FROM laughter_detections 
   WHERE user_id = '{user_id}' 
   AND timestamp >= '{test_date}T00:00:00Z' 
   AND timestamp < '{test_date+1day}T00:00:00Z';
   
   -- Audio segments
   SELECT COUNT(*) FROM audio_segments 
   WHERE user_id = '{user_id}' 
   AND start_time >= '{test_date}T00:00:00Z' 
   AND end_time < '{test_date+1day}T00:00:00Z';
   ```

2. Count files on disk:
   ```bash
   # OGG files
   find uploads/audio/{user_id}/ -name "*{test_date}*.ogg" | wc -l
   
   # WAV clips
   find uploads/clips/{user_id}/ -name "*{test_date}*.wav" | wc -l
   ```

3. **Record baseline counts** in verification log

**Expected:** May have existing data from previous tests

---

### Step 1: Cleanup Verification

**Purpose:** Ensure test date is completely clean before starting

**Actions:**
1. Run cleanup script:
   ```bash
   python3 cleanup_date_data.py {test_date}
   ```

2. Verify cleanup:
   ```sql
   -- All should return 0
   SELECT COUNT(*) FROM processing_logs WHERE user_id = '{user_id}' AND date = '{test_date}';
   SELECT COUNT(*) FROM laughter_detections WHERE user_id = '{user_id}' AND timestamp >= '{start_utc}' AND timestamp < '{end_utc}';
   SELECT COUNT(*) FROM audio_segments WHERE user_id = '{user_id}' AND start_time >= '{start_utc}' AND end_time < '{end_utc}';
   ```

3. Verify files deleted:
   ```bash
   # Should return 0
   find uploads/audio/{user_id}/ -name "*{test_date}*.ogg" | wc -l
   find uploads/clips/{user_id}/ -name "*{test_date}*.wav" | wc -l
   ```

**Pass Criteria:**
- ✅ All database counts = 0
- ✅ All file counts = 0
- ✅ Cleanup script exits with success

**If FAIL:** Investigate and fix cleanup script before proceeding

---

### Step 2: Manual Cron Job Execution

**Purpose:** Run the cron job script manually with full logging

**Actions:**
1. **Clear log file:**
   ```bash
   > logs/nightly_processing.log
   ```

2. **Run cron job script:**
   ```bash
   python3 process_nightly_audio.py >> logs/nightly_processing.log 2>&1
   ```

3. **Wait for completion** (check process is finished)

4. **Capture full terminal output:**
   ```bash
   # Save terminal output
   python3 process_nightly_audio.py > logs/manual_cron_run_{timestamp}.log 2>&1
   ```

**Critical:** Do NOT skip this step - we need to see all output

---

### Step 3: Log Analysis

**Purpose:** Verify the cron job executed correctly by analyzing logs

**Checkpoints:**

1. **Processing Started:**
   - [ ] Log shows "Starting nightly audio processing"
   - [ ] Log shows correct user timezone
   - [ ] Log shows correct date range (yesterday in user's timezone)

2. **Chunk Processing:**
   - [ ] Log shows 12 chunks attempted (or expected number for full day)
   - [ ] Each chunk shows either:
     - "SUCCESS" with file size
     - "ERROR" with status code and reason
     - "already fully processed" (should NOT happen on clean state)

3. **API Calls:**
   - [ ] Count successful API calls (should be 12 for full day, or less if some failed)
   - [ ] Document any errors (503, 404, etc.) with timestamps

4. **YAMNet Processing:**
   - [ ] Log shows detection summaries for each segment
   - [ ] Log shows total laughter events found
   - [ ] Log shows duplicates skipped

5. **Completion:**
   - [ ] Log shows "Processing completed successfully"
   - [ ] Log shows final summary with counts

**Pass Criteria:**
- ✅ All 12 chunks attempted
- ✅ No unexpected errors (404/503 errors are acceptable if logged)
- ✅ Processing completed successfully
- ✅ Summary shows consistent counts

**If FAIL:** Document specific errors and investigate root cause

---

### Step 4: Database Verification

**Purpose:** Verify database state matches expectations

**Queries:**

1. **Processing Log:**
   ```sql
   SELECT * FROM processing_logs 
   WHERE user_id = '{user_id}' AND date = '{test_date}'
   ORDER BY created_at DESC LIMIT 1;
   ```
   
   **Verify:**
   - [ ] Exactly 1 row exists
   - [ ] `trigger_type` = 'cron'
   - [ ] `status` = 'completed'
   - [ ] `audio_files_downloaded` matches expected count
   - [ ] `laughter_events_found` > 0 (if audio had laughter)
   - [ ] `created_at` is recent (just now)

2. **Audio Segments:**
   ```sql
   SELECT start_time, end_time, file_path, processed, created_at
   FROM audio_segments 
   WHERE user_id = '{user_id}' 
   AND start_time >= '{start_utc}' AND end_time < '{end_utc}'
   ORDER BY start_time;
   ```
   
   **Verify:**
   - [ ] Count matches `audio_files_downloaded` from processing_log
   - [ ] All segments have `processed` = true
   - [ ] Time ranges cover full day (no gaps, no overlaps)
   - [ ] All `file_path` values are valid
   - [ ] `created_at` timestamps are recent

3. **Laughter Detections:**
   ```sql
   SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
   FROM laughter_detections 
   WHERE user_id = '{user_id}' 
   AND timestamp >= '{start_utc}' AND timestamp < '{end_utc}';
   ```
   
   **Verify:**
   - [ ] Count matches `laughter_events_found` from processing_log
   - [ ] All timestamps are within expected range
   - [ ] All have valid `clip_path` values

**Pass Criteria:**
- ✅ Database counts match log summary
- ✅ All segments marked as processed
- ✅ No missing or orphaned references
- ✅ All timestamps are recent (from this run)

**If FAIL:** Compare with log output to identify discrepancies

---

### Step 5: File System Verification

**Purpose:** Verify files on disk match database records

**Checks:**

1. **OGG Files:**
   ```bash
   # List all OGG files for test date
   find uploads/audio/{user_id}/ -name "*{test_date}*.ogg" -type f
   
   # Count files
   find uploads/audio/{user_id}/ -name "*{test_date}*.ogg" -type f | wc -l
   ```
   
   **Verify:**
   - [ ] Count matches `audio_files_downloaded` from processing_log
   - [ ] All files exist (no missing files)
   - [ ] All files have non-zero size
   - [ ] File paths match database `audio_segments.file_path`

2. **WAV Clip Files:**
   ```bash
   # List all WAV files for test date
   find uploads/clips/{user_id}/ -name "*{test_date}*.wav" -type f
   
   # Count files
   find uploads/clips/{user_id}/ -name "*{test_date}*.wav" -type f | wc -l
   ```
   
   **Verify:**
   - [ ] Count matches `laughter_events_found - duplicates_skipped` (actual stored)
   - [ ] All files exist (no missing files)
   - [ ] All files have non-zero size
   - [ ] File paths match database `laughter_detections.clip_path`

3. **Cross-Reference:**
   ```python
   # For each database record, verify file exists
   # For each file on disk, verify database record exists
   ```

**Pass Criteria:**
- ✅ OGG file count = database `audio_segments` count
- ✅ WAV file count = database `laughter_detections` count (after deduplication)
- ✅ All database file paths point to existing files
- ✅ No orphaned files on disk (files without DB records)

**If FAIL:** Document which files are missing/extra and investigate

---

### Step 6: Consistency Check

**Purpose:** Verify consistency across all systems

**Checks:**

1. **Processing Log vs Database:**
   - [ ] `audio_files_downloaded` = `audio_segments` count
   - [ ] `laughter_events_found` = sum of all detections (including skipped)
   - [ ] `duplicates_skipped` = sum of skipped detections

2. **Database vs Disk:**
   - [ ] All `audio_segments.file_path` exist on disk
   - [ ] All `laughter_detections.clip_path` exist on disk
   - [ ] No files on disk without corresponding DB records

3. **Log vs Reality:**
   - [ ] Log chunk count matches actual segments processed
   - [ ] Log error messages match actual missing files (if any)
   - [ ] Log summary matches database counts

**Pass Criteria:**
- ✅ All counts are consistent
- ✅ No discrepancies between systems
- ✅ Log accurately reflects reality

**If FAIL:** Identify the source of discrepancy and root cause

---

### Step 7: UI Verification

**Purpose:** Verify data appears correctly in UI

**Actions:**
1. Start server (if not running)
2. Navigate to test date in UI
3. Verify:
   - [ ] Date shows correct laughter count
   - [ ] All audio clips are playable (no "Audio file not available")
   - [ ] Clips are in chronological order
   - [ ] All clips have correct metadata (class, probability, timestamp)

**Pass Criteria:**
- ✅ UI shows correct count
- ✅ All clips are accessible
- ✅ Display is correct

**If FAIL:** Check API endpoints and file serving

---

## Success Criteria

**The dress rehearsal PASSES if:**

1. ✅ Cleanup completely removed all test date data
2. ✅ Cron job executed without errors (except expected API errors like 503)
3. ✅ Log shows 12 chunks attempted (or expected number)
4. ✅ Processing log created with correct trigger_type='cron'
5. ✅ Database counts match log summary exactly
6. ✅ All files on disk match database records
7. ✅ No orphaned files or missing files
8. ✅ UI displays data correctly

**Any failure at any step = FAILURE** - must investigate and fix before considering complete

---

## Failure Investigation

If any step fails:

1. **Document failure:**
   - Which step failed
   - What was expected
   - What actually happened
   - Relevant log excerpts

2. **Root cause analysis:**
   - Compare with successful steps
   - Check for patterns (timezone issues, file path issues, etc.)
   - Verify code logic matches expected behavior

3. **Fix and retest:**
   - Fix identified issue
   - Repeat from Step 1 (clean state)

---

## Test Date: ________________

**User ID:** ________________  
**User Timezone:** ________________  
**Test Date (local):** ________________  
**Test Date (UTC range):** ________________ to ________________

**Baseline (Step 0):**
- Processing logs: _____
- Laughter detections: _____
- Audio segments: _____
- OGG files: _____
- WAV files: _____

**After Cleanup (Step 1):**
- Processing logs: _____
- Laughter detections: _____
- Audio segments: _____
- OGG files: _____
- WAV files: _____

**After Cron Job (Steps 2-5):**
- Processing logs: _____
- Laughter detections: _____
- Audio segments: _____
- OGG files: _____
- WAV files: _____

**Final Status:** ✅ PASS / ❌ FAIL

**Notes:**
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

