# Backlog

## Known Issues & Future Enhancements

### Limitless API 504 Gateway Timeout Errors

**Status**: Accepted (MVP behavior)

**Issue**: Limitless API intermittently returns 504 Gateway Timeout errors when fetching audio chunks. This occurred on 2025-10-29 for the 04:00-06:00 PST time window.

**Current Behavior** (MVP):
- 504/502/503 errors are logged as warnings
- The problematic chunk is skipped
- Processing continues with remaining chunks
- User is not notified of skipped chunks

**Logs**: Check `processing_logs` table for specific occurrences

**Future Enhancement Options**:
1. **Retry Logic**: Implement exponential backoff retry (2-3 attempts with 2s, 4s delays)
   - **Pros**: Recovers from transient network issues
   - **Cons**: Longer processing time, more complex code
   - **Recommendation**: Implement if 504 errors are frequent (>10% of requests)

2. **Manual Replay**: Allow users to manually trigger processing for specific time windows
   - **Pros**: User control, audit trail
   - **Cons**: Requires UI work, user education
   - **Recommendation**: Post-MVP feature

3. **Alert User**: Notify user when chunks are skipped
   - **Pros**: Transparency
   - **Cons**: May confuse users if it's rare
   - **Recommendation**: Implement if skipping becomes noticeable pattern

4. **Scheduled Retry**: Next nightly run attempts to fill gaps from previous run
   - **Pros**: Automatic recovery
   - **Cons**: Database tracking needed
   - **Recommendation**: Implement after retry logic

**Decision**: Keep simple for MVP. Monitor frequency via logs. Add retry logic if 504 errors are occurring frequently (>10% of chunks).

### Missing WAV Clip Files (404 Errors)

**Status**: Fixed (defensive check added)

**Issue**: Some laughter detections in the database reference WAV clip files that don't exist on disk, causing 404 errors when users try to play clips.

**Root Cause**: YAMNet detects laughter and creates a database entry, but the WAV clip file creation can fail silently (e.g., file write error). The database entry is still created with the clip_path, even though the file doesn't exist.

**Fixed**: Added a defensive check before inserting laughter detections - only insert if the clip file actually exists on disk. This prevents 404 errors from being stored in the database.

**Future Enhancement**: 
- Investigate why `_create_audio_clip` fails (disk space, permissions, concurrent writes?)
- Add retry logic for clip creation
- Consider storing laughter detections without clips as "detected but no audio available"

**Logs**: Look for "Skipping laughter event - clip file not found" warnings

### Pages Running Together / Overlapping Views

**Status**: Fixed

**Issue**: Settings page intermittently showed content from the home/summary page (e.g., "8 giggles" card appearing on Settings screen).

**Root Cause**: **Duplicate HTML structure** - the old desktop layout's `.app-header` (lines 15-19 in HTML) was never removed when the mobile redesign was implemented. This old header existed at the page root level, separate from the `#app-section` container that JavaScript shows/hides. The result was:
1. Two headers on the page (old desktop one + new mobile one)
2. Old header was never hidden by JavaScript
3. Content could render in both layouts simultaneously
4. Intermittent overlap depending on CSS specificity and rendering order

**Fixed**: Removed the old `.app-header` from the HTML root. Now only one header exists (the `.mobile-header` inside `#app-section`), which is properly hidden/shown by JavaScript.

**Lesson**: When refactoring layouts, completely remove old HTML structure rather than leaving it hidden. Redundant DOM elements create unpredictable rendering behavior.

### Missing WAV Clips - Duplicate Detection Deletion

**Status**: Being debugged

**Issue**: WAV clips are being deleted by cleanup process, but they appear to be legitimate files that should be kept.

**Root Cause Hypothesis**: Duplicate detection logic may be too aggressive and deleting clips that aren't actual duplicates. The flow is:
1. YAMNet detects laughter and creates clip on disk
2. Duplicate check (5-second window OR exact clip path) finds a match
3. Clip is deleted from disk
4. Database insertion is skipped
5. Later, cleanup process finds clip on disk without DB record and deletes it (this is correct behavior)

**Problem**: If duplicate detection is incorrectly identifying clips as duplicates, legitimate clips are being deleted.

**Debugging Added**:
- Enhanced logging in YAMNet clip creation to track creation attempts
- Logging before database insertion to confirm file existence
- Enhanced cleanup logging to show which clips are deleted

**Future Fix**: Review duplicate detection logic - may need to adjust 5-second window or clip path comparison logic.

**Root Cause Identified**: The file path was relative (`./uploads/clips/...`) instead of absolute, causing `os.path.exists()` to fail when the current working directory changed. This allowed database inserts without files on disk.

**Fixes Applied**:
1. Converted clip paths to absolute using `os.path.abspath()` in YAMNet processor
2. Added enhanced logging to track clip creation and file existence
3. Fixed timezone naive/aware handling in duplicate detection

### Missing Favicon

**Status**: Backlog

**Issue**: Browser requests `/favicon.ico` which returns 404, cluttering logs with: `GET /favicon.ico HTTP/1.1 404 Not Found`

**Future Enhancement**: Create a favicon.ico file or add a route handler that returns a simple icon to prevent 404 errors in logs.

