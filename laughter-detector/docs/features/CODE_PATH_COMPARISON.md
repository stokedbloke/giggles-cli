# Code Path Comparison: _process_date_range() Calls

## Overview
All three code paths call `_process_date_range()`, but with different context and setup.

## Critical Finding: OGG Download Happens BEFORE Duplicate Check

**Current flow in `_process_date_range()`:**
1. Line 232: `segments = await limitless_api_service.get_audio_segments(...)`
   - This downloads OGG files from Limitless API
   - Files are saved to disk immediately
2. Line 243: `if await self._segment_already_processed(...)`
   - Duplicate check happens AFTER download
   - If duplicate found, OGG file is deleted

**Problem:** OGG files are downloaded even when already processed, then immediately deleted. This is wasteful.

## Code Path 1: Cron Job (`process_nightly_audio.py`)

**Context:**
- Creates its own `enhanced_logger` with `process_date=start_of_yesterday.date()`
- Sets `self.scheduler._trigger_type = 'cron'`
- Calculates "yesterday" in user's timezone, converts to UTC
- Calls `_process_date_range()` directly in a while loop (2-hour chunks)
- Creates its own logger instance, NOT using `_process_user_audio()`
- Saves processing log after all chunks complete

**Key Differences:**
- Does NOT use `_process_user_audio()` method
- Does NOT run orphan cleanup
- Does NOT check for incremental processing (always processes full day)
- Logger is created per user, not per chunk

## Code Path 2: Manual "Update Today" Button (`scheduler.py` → `_process_user_audio()`)

**Context:**
- Uses `_process_user_audio()` method
- Creates `enhanced_logger` with `process_date=date.today()`
- Checks for latest processed timestamp to enable incremental processing
- Calls `_process_date_range()` in a while loop starting from latest processed time
- Runs orphan cleanup after all chunks complete
- Logger is part of the scheduler class

**Key Differences:**
- Uses incremental processing (starts from latest processed timestamp)
- Runs orphan cleanup at end
- Processes from latest timestamp to "now", not full day
- Uses scheduler's logger system

## Code Path 3: Manual Reprocess Button (`manual_reprocess_yesterday.py`)

**Context:**
- Creates `enhanced_logger` per day in date range
- Bypasses `_process_user_audio()` completely
- Calls `_process_date_range()` directly in a while loop
- Clears database records and files before processing
- Does per-day logging

**Key Differences:**
- Clears existing data before processing (reprocess = delete + reprocess)
- Creates separate logger for each day
- Processes date range specified by user
- No orphan cleanup (assumes cleanup happened in clear step)

## Summary

All paths call the same `_process_date_range()` method, but:
1. **Logger setup differs** - cron creates its own, Update Today uses scheduler's, reprocess creates per-day
2. **Incremental processing** - Only Update Today uses it
3. **Orphan cleanup** - Only Update Today runs it
4. **Time range calculation** - All calculate differently (yesterday vs today vs date range)
5. **All share the same bug** - OGG files downloaded before duplicate check

