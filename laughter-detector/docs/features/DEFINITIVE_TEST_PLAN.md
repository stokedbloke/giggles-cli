# DEFINITIVE TEST PLAN - Cleanup & Cron Job Verification

## ✅ REPROCESSING STATUS: PERFECT
- **18 detections** - All files exist on disk
- **12 segments** - All processed
- **1 processing log** - Correctly created
- **0 missing files** - Perfect state

---

## 🎯 TEST OBJECTIVE
Verify that the manual cleanup and cron job scripts work identically to the reprocess button functionality.

---

## 📊 BASELINE STATE (Before Test)

**11/3 Data:**
- Processing logs: 1 entry
- Laughter detections: 18
- Audio segments: 12 (all processed)
- WAV files on disk: 18/18 (100%)

---

## 🧪 TEST STEPS

### Step 1: Manual Cleanup Test
**Script:** `cleanup_date_data.py`  
**Command:** `python cleanup_date_data.py 2025-11-03`

**Expected Result:**
- All 11/3 database records deleted:
  - processing_logs: 0 entries for 11/3
  - laughter_detections: 0 entries for 11/3
  - audio_segments: 0 entries for 11/3
- All 11/3 files deleted from disk:
  - WAV files: 0 files in clips folder for 11/3
  - OGG files: 0 files in audio folder for 11/3

**Verification Query:**
```python
# Should return 0 for all counts
```

---

### Step 2: Manual Cron Job Test
**Script:** `process_nightly_audio.py`  
**Command:** `python process_nightly_audio.py`

**Expected Result:**
- Processing log created for 11/3
- Laughter detections: 18 (same as before)
- Audio segments: 12 (same as before)
- WAV files on disk: 18/18 (all exist)

**Verification:**
- Should match the reprocessing results exactly
- All files should exist on disk
- Processing log should show correct counts

---

## ✅ PASS/FAIL CRITERIA

### Cleanup Test PASSES if:
- ✅ All 11/3 database records deleted
- ✅ All 11/3 files deleted from disk
- ✅ No orphaned files remain

### Cron Job Test PASSES if:
- ✅ Results match reprocessing exactly:
  - Same number of detections (18)
  - Same number of segments (12)
  - All files exist on disk (18/18)
  - Processing log created with correct counts

### OVERALL TEST PASSES if:
- ✅ Both cleanup and cron job work identically to reprocess button
- ✅ No missing files
- ✅ No orphaned files
- ✅ Database state matches disk state

---

## 🔍 VERIFICATION QUERIES

After each step, run these queries to verify state:

```python
# Check 11/3 data
- processing_logs for date='2025-11-03'
- laughter_detections for timestamp in 11/3 UTC range
- audio_segments for start_time/end_time in 11/3 UTC range
- Files on disk matching 11/3 date patterns
```

