# Detection Logging Improvements

## Summary

Enhanced logging to clearly show:
1. **Total detections from YAMNet** (before duplicate filtering)
2. **Skipped detections** (with reasons)
3. **Stored detections** (after duplicate filtering)

## Changes Made

### 1. Enhanced `_store_laughter_detections` Logging

Now tracks and logs:
- `total_detected`: Total events detected by YAMNet
- `skipped_time_window`: Skipped due to 5-second duplicate window
- `skipped_clip_path`: Skipped due to duplicate clip path
- `skipped_missing_file`: Skipped due to missing clip file
- `stored_count`: Successfully stored in database

### 2. Processing Logs Table

The `processing_logs` table stores **ALL YAMNet detections** (before duplicate filtering):
- `laughter_events_found` field contains the total count from YAMNet
- This is tracked via `enhanced_logger.add_step()` with `metadata={"laughter_count": len(laughter_events)}`
- The enhanced logger aggregates these counts from all processing steps

### 3. Clear Skip Messages

Each skipped detection now logs with:
- ⏭️ SKIPPED prefix
- Reason for skipping
- Timestamp and probability
- What existing detection caused the skip

## Usage

When processing audio, you'll now see:

```
🔥 _store_laughter_detections CALLED: 19 events detected by YAMNet for segment 39890c07
⏭️  SKIPPED (duplicate within 5s): 16:15:43 prob=0.534 - Already exists at 2025-10-29T23:15:42+00:00
✅ STORED: 16:15:42 prob=0.548 clip=20251029_230000-20251030_010000_laughter_942.wav
...
================================================================================
📊 DETECTION SUMMARY for segment 39890c07:
   🎭 Total detected by YAMNet:     19
   ⏭️  Skipped (time window dup):   11
   ⏭️  Skipped (clip path dup):      0
   ⏭️  Skipped (missing file):       0
   ✅ Successfully stored:           8
   📉 Total skipped:                 11
================================================================================
```

## Database Storage

- **`laughter_detections` table**: Only stores non-duplicate detections (what remains after filtering)
- **`processing_logs` table**: Stores ALL YAMNet detections via `laughter_events_found` field

