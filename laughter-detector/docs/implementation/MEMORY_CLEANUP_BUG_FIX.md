# Memory Cleanup Bug Fix

## Problem

**Symptom:** Second user in multi-user cron job fails with:
```
AttributeError: 'Scheduler' object has no attribute '_service_client'
```

**Root Cause:**
- Aggressive cleanup in `process_nightly_audio.py` was **deleting** `_service_client` attribute
- Used `delattr(self.scheduler, '_service_client')` 
- Scheduler's `_get_service_client()` checks `if self._service_client is None:`
- This check fails with `AttributeError` if attribute doesn't exist

**Impact:**
- First user: ✅ Works (attribute exists initially)
- Second user: ❌ Fails (attribute was deleted after first user)

## Fix

**Changed:**
```python
# OLD (BROKEN):
if hasattr(self.scheduler, '_service_client'):
    delattr(self.scheduler, '_service_client')

# NEW (FIXED):
if hasattr(self.scheduler, '_service_client'):
    self.scheduler._service_client = None
```

**Why This Works:**
- Setting to `None` preserves the attribute
- `if self._service_client is None:` check works correctly
- Scheduler recreates client when needed
- Still releases memory (client object is garbage collected)

## Testing

**Before Fix:**
- User 1: ✅ Processes successfully
- User 2: ❌ Fails with AttributeError

**After Fix:**
- User 1: ✅ Processes successfully  
- User 2: ✅ Processes successfully

## Lesson Learned

**Never delete attributes that are checked with `if attr is None:`**
- Use `obj.attr = None` instead of `delattr(obj, 'attr')`
- This preserves the attribute while clearing its value
- Allows lazy initialization patterns to work correctly

