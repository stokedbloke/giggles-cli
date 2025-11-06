# Dress Rehearsal Analysis - Nov 3, 2025

## Questions Answered

### 1. Why did the segment 20:00-22:00 UTC exist in the DB? Why wasn't it "fully processed"? When was the prior interrupted run? Why didn't cleanup delete it?

**Answer:** This is a **BUG in the cleanup script** - it failed to delete the segment.

**Timeline:**
- **08:58 AM (16:58 UTC)**: Cleanup script ran, **claimed to delete** Nov 3 PST data
- **09:00 AM (17:00 UTC)**: Manual cron job triggered
- **17:00:27 UTC**: Cron job found segment 20:00-22:00 UTC still existed in DB
- **Log shows**: "Segment exists but not fully processed for range 20:00 - 22:00 UTC"

**The Problem:**
- The cleanup script's database deletion query (`clear_database_records`) **failed to delete the audio_segment** for 20:00-22:00 UTC
- This segment had `processed=False` (either it was never fully processed, or the cleanup partially failed)
- When the cron job ran, it found this "existing but not fully processed" segment and reprocessed it

**Why it wasn't "fully processed":**
- The segment existed with `processed=False`
- The `_is_segment_fully_processed()` function checks both `processed=True` OR existence of laughter detections
- If neither condition was met, it would report as "not fully processed"

**Root Cause:** The cleanup script's `clear_database_records` function has a bug in its query logic that fails to delete some `audio_segments` entries even when they fall within the specified UTC range.

---

### 2. When did the WAV files become orphaned?

**Answer:** The WAV files became orphaned **during the cron job run**, but this was caused by the cleanup script bug.

**Cascade of Events:**
1. **16:58 UTC**: Cleanup script ran, **failed to delete segment 20:00-22:00 UTC** (Bug #1)
2. **17:00 UTC**: Cron job started
3. **17:00:27 UTC**: Cron job found the segment still existed, reprocessed it
4. **17:00:27-17:00:58**: YAMNet processed audio, detected 2 laughter events
5. **17:00:27-17:00:58**: WAV files were created on disk:
   - `20251103_200000-20251103_220000_laughter_681-60_13.wav`
   - `20251103_200000-20251103_220000_laughter_3226-56_13.wav`
6. **17:00:27-17:00:58**: Duplicate check ran and found detections at these timestamps **within 5 seconds** of existing detections (possibly from chunks 1-6 that were processed earlier in the same run)
7. **17:00:27-17:00:58**: System logged "SKIPPED (duplicate within 5s)" and called `_delete_orphaned_clip()`
8. **17:00:27-17:00:58**: Files were deleted as "orphaned"

**However**, the detections **WERE still stored in the database** (created_at: 17:00:58). This means:
- The duplicate check found duplicates
- The code logged "SKIPPED" and deleted files
- **BUT** the detections were inserted anyway (either the duplicate check failed to prevent insertion, or they were inserted from a different code path)

**This is a CASCADE from Bug #1**: If the cleanup script had worked correctly, the segment wouldn't have existed, and this reprocessing wouldn't have happened.

---

### 3. There are 18 laughs detected but only 16 on disk. Explain.

**Answer:** This is also a **CASCADE from the cleanup script bug**.

**What happened:**
1. **18 detections stored in DB** for Nov 3 PST (confirmed by query)
2. **16 WAV files on disk** (confirmed by file count)
3. **2 missing files** are the ones deleted during the cascade:
   - `20251103_200000-20251103_220000_laughter_681-60_13.wav`
   - `20251103_200000-20251103_220000_laughter_3226-56_13.wav`

**The Cascade:**
1. Cleanup script bug → Segment 20:00-22:00 UTC not deleted
2. Cron job reprocessed segment → YAMNet detected laughter
3. Duplicate check found duplicates (within 5-second window)
4. Code logged "SKIPPED" and deleted files
5. **BUT** detections were still inserted into database (bug in duplicate prevention or race condition)
6. Result: Database has 18 detections, but 2 files are missing

**Root Cause Analysis:**
- **Primary bug**: Cleanup script failed to delete the segment
- **Secondary issue**: Duplicate detection logic may have a race condition where:
  - Duplicate check runs and finds duplicates
  - Code attempts to skip insertion
  - But insertion happens anyway (possibly due to exception handling or code flow)
  - Files get deleted, but DB entries remain

**Evidence:**
- Both "missing" detections exist in DB with `created_at: 2025-11-04T17:00:58`
- Their `clip_path` values reference the deleted files
- The log shows they were "SKIPPED (duplicate within 5s)" but they were still stored
- No other detections at those exact timestamps (so database unique constraint didn't block them)

---

## Is This a Bug in the Code or Execution?

**This is a CASCADE of bugs, starting with the cleanup script.**

**Bug Sequence:**
1. **Cleanup script bug** (primary): Failed to delete segment 20:00-22:00 UTC
2. **Cascade effect**: Cron job reprocessed segment, causing duplicate detection issues
3. **Duplicate detection/insertion bug** (secondary): Detections were logged as "SKIPPED" but still inserted, and files were deleted

**Fix Priority:**
1. ✅ **Fix cleanup script** - COMPLETED: Changed query to use proper overlap detection (`start_time < cleanup_end AND end_time > cleanup_start`)
2. ✅ **Fix duplicate detection logic** - COMPLETED: Added DB verification to `_delete_orphaned_clip()` to prevent deleting files referenced in database
3. ⚠️ **Fix insertion logic** - STILL INVESTIGATING: Why detections marked as "SKIPPED" are still being inserted

**Status:**
- ✅ Cleanup script fixed with proper overlap detection
- ✅ Orphan cleanup now has safety check (won't delete files referenced in DB)
- ⚠️ Still need to investigate why "SKIPPED" detections end up in database

**Next Steps:**
- Monitor logs for "Skipped deleting clip - File is referenced in database" warnings
- Investigate why detections are inserted despite being marked as duplicates
- May need to add transaction-level locking or more detailed logging to trace the code path
