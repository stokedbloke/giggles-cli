# Fix Plan: Add Database Check Before OGG Download

## Problem Confirmed
✅ **100% CERTAIN**: OGG files are downloaded BEFORE checking if segments are already processed.

**Current Flow:**
1. `_process_date_range()` calls `get_audio_segments()`
2. `get_audio_segments()` → `_fetch_audio_segments()` downloads OGG file immediately
3. Back in `_process_date_range()`, checks `_segment_already_processed()`
4. If duplicate, deletes OGG file (wasteful!)

## Fix Plan

### Change 1: Add Pre-Download Check in `_process_date_range()`

**Location:** `src/services/scheduler.py`, line ~227 (after `try:`)

**Add:**
```python
# OPTIMIZATION: Check if this time range is already fully processed BEFORE downloading
# This prevents wasteful OGG file downloads for already-processed segments
if await self._is_time_range_processed(user_id, start_time, end_time):
    print(f"⏭️  SKIPPED (already fully processed): Time range {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')} UTC - Already processed, skipping download")
    return 0
```

### Change 2: Fix `_is_time_range_processed()` Overlap Detection

**Location:** `src/services/scheduler.py`, line ~477

**Current (WRONG):** Checks for segments contained within range
```python
.gte("start_time", start_time.isoformat()).lte("end_time", end_time.isoformat())
```

**Fix (CORRECT):** Check for overlapping segments
```python
# Overlap condition: segment_start < our_end AND segment_end > our_start
.lt("start_time", end_time.isoformat()).gt("end_time", start_time.isoformat())
```

**Also add:** Timezone handling
```python
import pytz
if start_time.tzinfo is None:
    start_time = start_time.replace(tzinfo=pytz.UTC)
if end_time.tzinfo is None:
    end_time = end_time.replace(tzinfo=pytz.UTC)
```

## Risks & Mitigation

### Risk 1: False Positives (Skip download when shouldn't)
- **Risk:** Overlap detection might incorrectly skip downloads if segments only partially overlap
- **Mitigation:** 
  - Test with manual cron run after fix
  - Verify logs show correct skip messages
  - Compare before/after segment counts

### Risk 2: False Negatives (Download when shouldn't)
- **Risk:** Overlap detection might miss existing segments, causing duplicate downloads
- **Mitigation:**
  - Existing `_segment_already_processed()` check still runs AFTER download as backup
  - Test with data that has overlapping segments
  - Verify no duplicate OGG files remain after processing

### Risk 3: Timezone Issues
- **Risk:** Timezone mismatch could cause incorrect overlap detection
- **Mitigation:**
  - Added explicit timezone handling in `_is_time_range_processed()`
  - All timestamps normalized to UTC before comparison
  - Test with user in non-UTC timezone

### Risk 4: Performance Impact
- **Risk:** Additional database query before each download
- **Mitigation:**
  - Database query is simple (indexed on user_id, processed, start_time, end_time)
  - Query is much faster than downloading OGG files
  - Net performance improvement (avoids unnecessary downloads)

## Testing Plan

1. **Manual Verification:**
   - Delete all 11/3 data
   - Run manual cron job
   - Verify logs show skip messages for already-processed segments
   - Verify no OGG files downloaded for skipped segments

2. **Edge Cases:**
   - Test with partial overlaps
   - Test with exact matches
   - Test with adjacent segments (no overlap)

3. **Regression:**
   - Verify Update Today button still works
   - Verify Reprocess button still works
   - Verify new segments still download correctly

## Implementation Status

- [ ] Apply Change 1: Pre-download check
- [ ] Apply Change 2: Fix overlap detection  
- [ ] Syntax check
- [ ] Test manual cron run
- [ ] Verify logs
