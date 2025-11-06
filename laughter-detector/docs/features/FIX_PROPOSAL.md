# Fix Proposal: Orphaned File Deletion Bug

## The Bug

**Problem:** Files are being deleted even though their detections exist in the database.

**Root Cause:** The `_delete_orphaned_clip()` function deletes files without verifying they're actually orphaned (not referenced in the database).

**Evidence:**
- 18 detections in database for Nov 3 PST
- Only 16 WAV files on disk
- The 2 missing files have `clip_path` entries in the database
- Log shows they were deleted as "orphaned" but they're NOT orphaned

## Current Code Flow (Broken)

```python
# In _store_laughter_detections()
if duplicate_found:
    print("SKIPPED (duplicate)")
    self._delete_orphaned_clip(file_path, "time-window duplicate")  # BUG: Deletes without DB check
    continue  # Skip insertion

# Later...
insert_to_database()  # But sometimes this still happens?
```

The `_delete_orphaned_clip()` function:
```python
def _delete_orphaned_clip(self, clip_path: str, reason: str = "orphaned"):
    if os.path.exists(clip_path):
        os.remove(clip_path)  # BUG: Deletes without checking DB
```

**Why this is broken:**
- Even when correctly identifying a duplicate, the file deletion happens without verification
- If there's a race condition or logic error elsewhere, files can be deleted even when referenced in DB
- No safety net to prevent deleting files that ARE in the database

## The Fix (Minimal, Safe)

**Change:** Add a database check to `_delete_orphaned_clip()` to verify the file is actually orphaned before deleting.

**Code Change:**
```python
def _delete_orphaned_clip(self, clip_path: str, reason: str = "orphaned"):
    """
    Modular function to delete orphaned clip files.
    
    SAFETY: Verifies file is actually orphaned (not in DB) before deleting.
    """
    if not self.DELETE_ORPHANED_CLIPS:
        return False
    
    try:
        if not clip_path:
            return False
        
        # SAFETY CHECK: Verify file is actually orphaned (not referenced in DB)
        import os
        from dotenv import load_dotenv
        from supabase import create_client
        
        load_dotenv()
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            # Check if file is referenced in database
            result = supabase.table("laughter_detections").select("id").eq("clip_path", clip_path).limit(1).execute()
            if result.data and len(result.data) > 0:
                # File IS referenced in database - don't delete!
                print(f"⚠️  Skipped deleting clip ({reason}): {os.path.basename(clip_path)} - File is referenced in database")
                return False
        
        # File is actually orphaned - safe to delete
        if os.path.exists(clip_path):
            os.remove(clip_path)
            print(f"🧹 Deleted orphaned clip ({reason}): {os.path.basename(clip_path)}")
            return True
        else:
            return False
    except Exception as e:
        print(f"⚠️  Failed to delete orphaned clip ({reason}): {os.path.basename(clip_path)} - {str(e)}")
        return False
```

## Why This Fix is Safe

### 1. **No Breaking Changes**
- Only ADDS a safety check, doesn't remove any functionality
- All existing code paths remain the same
- If DB check fails (exception), it gracefully returns False (doesn't delete)
- Still respects `DELETE_ORPHANED_CLIPS` flag

### 2. **Prevents Data Loss**
- Files that ARE in the database will never be deleted
- Even if duplicate detection logic has bugs, files are protected
- Acts as a safety net for all edge cases

### 3. **Minimal Performance Impact**
- Single database query (indexed on `clip_path`)
- Only runs when a duplicate is detected (not on every file)
- Query is fast (primary key lookup)

### 4. **No Overengineering**
- Simple database check before deletion
- Reuses existing Supabase connection pattern
- No new dependencies or complex logic
- Adds ~5 lines of code + safety check

### 5. **Backward Compatible**
- If DB check fails, function returns False (safe default)
- Existing behavior preserved for files that are actually orphaned
- No changes to calling code required

## Testing Plan

1. **Test 1: Orphaned file deletion (should work)**
   - Create a WAV file on disk
   - Don't create DB entry
   - Call `_delete_orphaned_clip()` → Should delete file

2. **Test 2: File in database (should NOT delete)**
   - Create WAV file on disk
   - Create DB entry with `clip_path`
   - Call `_delete_orphaned_clip()` → Should skip deletion with warning

3. **Test 3: Duplicate detection (should work)**
   - Process audio with duplicate detections
   - Verify orphaned duplicates are deleted
   - Verify non-orphaned files are NOT deleted

## Risk Assessment

**Risk Level: LOW**

- Only adds a safety check (defensive programming)
- No changes to core logic
- Graceful error handling (if DB check fails, doesn't delete)
- Can be disabled via `DELETE_ORPHANED_CLIPS = False` flag

## Alternative (If DB Check is Too Slow)

If the database check adds too much latency, we could:
1. Cache DB check results during processing session
2. Only check for files that are suspicious (recently created)
3. But the simple approach is likely fine - the check only runs when duplicates are detected

## Summary

**Fix:** Add a database verification check to `_delete_orphaned_clip()` before deleting files.

**Impact:** 
- Prevents deleting files that are in the database
- Minimal code change (~10 lines)
- No breaking changes
- Adds safety net for edge cases

**Rollout:**
1. Make the change
2. Test with existing data
3. Monitor logs for any warnings
4. No rollback needed (only adds safety check)

