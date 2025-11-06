# Reprocess Duplicate Analysis

## Answer: **NO DUPLICATES** - Records are DELETED first, then new ones inserted

## Reprocess Flow:

### 1. **DELETION PHASE** (Before Processing):
```
clear_database_records() is called FIRST:
  ✅ Deletes ALL laughter_detections in date range
  ✅ Deletes ALL audio_segments in date range  
  ✅ Deletes ALL processing_logs in date range
```

### 2. **CLEANUP PHASE**:
```
clear_disk_files() is called:
  ✅ Deletes OGG files in date range
  ✅ Deletes WAV clip files in date range
```

### 3. **REPROCESSING PHASE** (After Cleanup):
```
Fresh download from Limitless API
Fresh YAMNet processing
New records inserted into EMPTY database (for that date range)
```

## Database Safety Nets:

### Unique Constraints (Database Level):
1. **`unique_laughter_timestamp_user`** - UNIQUE (user_id, timestamp)
   - Prevents exact same timestamp for same user
   - Database will REJECT duplicate inserts

2. **`unique_laughter_clip_path`** - UNIQUE (clip_path)
   - Prevents same clip file being referenced twice
   - Database will REJECT duplicate inserts

### Application-Level Prevention (Code Level):
1. **5-second window check** - Checks for existing detections within 5 seconds
2. **Clip path check** - Checks if clip path already exists
3. **Missing file check** - Won't insert if clip file doesn't exist

## Conclusion:

✅ **Records are NOT overwritten - they are DELETED then RE-INSERTED**

✅ **No duplicates will occur because:**
   - Old records deleted first (for the date range)
   - Database constraints prevent duplicates at DB level
   - Application code prevents duplicates at app level

✅ **If somehow a duplicate gets through:**
   - Database constraint will REJECT it (return error, not create duplicate)
   - Code catches this and logs: "⏭️ SKIPPED (database constraint)"

## Example Flow:

```
Before reprocess:
  - Date range has 20 laughter_detections
  - Date range has 10 audio_segments

During reprocess:
  Step 1: DELETE all 20 laughter_detections
  Step 2: DELETE all 10 audio_segments
  Step 3: DELETE disk files
  Step 4: Download fresh from Limitless
  Step 5: Process with YAMNet (finds 19 events)
  Step 6: INSERT new records (8 stored after duplicate filtering)

After reprocess:
  - Date range has 8 laughter_detections (fresh data)
  - Date range has new audio_segments (fresh data)
```

**No duplicates possible** - old records are gone before new ones are created.

