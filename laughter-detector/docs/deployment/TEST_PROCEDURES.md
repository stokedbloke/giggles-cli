# Test Procedures for Memory Optimization

## Overview

This document describes how to run tests to verify memory cleanup and multi-user processing before deploying to production.

## Prerequisites

```bash
# Activate virtual environment
source venv_linux/bin/activate

# Verify psutil is installed
pip list | grep psutil
# Should show: psutil>=5.9.0

# Verify test users exist in database
# (Use staging/test users, not production)
```

## Test 1: Simple Memory Test

**Purpose:** Verify basic memory cleanup after TensorFlow operations.

**Script:** `scripts/testing/test_memory_simple.py`

**Run:**
```bash
cd laughter-detector
source venv_linux/bin/activate
python scripts/testing/test_memory_simple.py
```

**Expected Output:**
- ✅ Baseline memory: ~560 MB (after TensorFlow load)
- ✅ Peak memory: < 600 MB
- ✅ Final memory: < 600 MB
- ✅ PASS: Memory stable

**Success Criteria:**
- No memory growth > 150 MB from baseline
- Memory stabilizes after cleanup
- No errors or exceptions

---

## Test 2: Multi-User Memory Test

**Purpose:** Verify memory cleanup between multiple users.

**Script:** `scripts/testing/test_memory_multiple_users.py`

**Run:**
```bash
cd laughter-detector
source venv_linux/bin/activate
python scripts/testing/test_memory_multiple_users.py
```

**Expected Output:**
- ✅ User 1 processes successfully
- ✅ Memory after User 1 cleanup: ~700 MB
- ✅ User 2 processes successfully
- ✅ Memory after User 2 cleanup: ~700 MB
- ✅ No OOM errors

**Success Criteria:**
- Both users complete processing
- Memory cleanup between users (70%+ reduction)
- Final memory < 1 GB
- No AttributeError on 2nd user

---

## Test 3: Real Audio Processing Test

**Purpose:** Verify memory cleanup with actual YAMNet inference.

**Script:** `scripts/testing/test_with_real_processing.py`

**Run:**
```bash
cd laughter-detector
source venv_linux/bin/activate

# Test with specific user IDs
python scripts/testing/test_with_real_processing.py \
  --user-id d26444bc-e441-4f36-91aa-bfee24cb39fb \
  --user-id eb719f30-fe9e-42e4-8bb3-d5b4bb8b3327
```

**Expected Output:**
- ✅ Downloads real audio files
- ✅ Runs YAMNet inference
- ✅ Creates laughter detections
- ✅ Memory cleanup after each user
- ✅ Peak memory: ~2.4 GB (expected for large files)
- ✅ After cleanup: ~700 MB

**Success Criteria:**
- Real audio processing works
- Memory spikes are temporary
- Cleanup reduces memory 70%+
- No OOM errors

---

## Test 4: Production-Like Cron Job Test

**Purpose:** Test the actual cron job script with multiple users.

**Script:** `process_nightly_audio.py`

**Prerequisites:**
```bash
# Clean up test data first (optional)
python scripts/cleanup/cleanup_date_data.py 2025-11-19 USER_ID
```

**Run:**
```bash
cd laughter-detector
source venv_linux/bin/activate

# Test with 2 users
python process_nightly_audio.py \
  --user-id d26444bc-e441-4f36-91aa-bfee24cb39fb \
  --user-id eb719f30-fe9e-42e4-8bb3-d5b4bb8b3327
```

**Expected Output:**
- ✅ User 1: Processing completed successfully
- ✅ Memory after User 1: ~700 MB
- ✅ User 2: Processing completed successfully
- ✅ Memory after User 2: ~700 MB
- ✅ No errors or exceptions

**Success Criteria:**
- Both users process successfully
- Memory cleanup working (logs show cleanup)
- Processing logs created in database
- Laughter detections created
- No OOM errors

**Monitor:**
```bash
# Watch memory during processing
watch -n 1 'free -h'

# Check logs in real-time
tail -f /var/lib/giggles/logs/nightly_processing.log | grep "🧠 Memory"
```

---

## Test 5: Cleanup Verification

**Purpose:** Verify cleanup scripts work correctly.

**Script:** `scripts/cleanup/cleanup_date_data.py`

**Run:**
```bash
cd laughter-detector
source venv_linux/bin/activate

# Clean up test data for a specific date
python scripts/cleanup/cleanup_date_data.py 2025-11-19 USER_ID
```

**Expected Output:**
- ✅ Deletes laughter detections
- ✅ Deletes audio segments
- ✅ Deletes processing logs
- ✅ Deletes files on disk (if they exist)

**Success Criteria:**
- All data for date deleted
- No errors
- Database and disk consistent

---

## Pre-Deployment Checklist

Before deploying to production, verify:

- [ ] **Test 1:** Simple memory test passes
- [ ] **Test 2:** Multi-user test passes
- [ ] **Test 3:** Real audio processing test passes
- [ ] **Test 4:** Production-like cron job test passes
- [ ] **Test 5:** Cleanup verification works

**Memory Verification:**
- [ ] Peak memory < 2.5 GB (for 4GB VPS)
- [ ] Cleanup reduces memory 70%+
- [ ] No OOM errors in any test
- [ ] Memory stabilizes after cleanup

**Functionality Verification:**
- [ ] Both users process successfully
- [ ] No AttributeError on 2nd user
- [ ] Processing logs created correctly
- [ ] Laughter detections created correctly
- [ ] Database and disk consistent

---

## Troubleshooting

### Memory Test Fails

**Symptom:** Memory grows beyond threshold

**Check:**
```bash
# Check if psutil is installed
pip list | grep psutil

# Check Python version
python3 --version  # Should be 3.9+

# Check TensorFlow version
pip list | grep tensorflow
```

**Fix:**
- Install psutil: `pip install psutil>=5.9.0`
- Verify TensorFlow cleanup is working
- Check for memory leaks in code

### AttributeError on 2nd User

**Symptom:** `AttributeError: 'Scheduler' object has no attribute '_service_client'`

**Fix:**
- Verify `process_nightly_audio.py` uses `self.scheduler._service_client = None` (not `delattr()`)
- Check that scheduler's `_get_service_client()` handles `None` correctly

### OOM Error

**Symptom:** Process killed with OOM

**Check:**
- Verify VPS has sufficient RAM (4GB recommended)
- Check swap is enabled: `free -h`
- Monitor memory during processing: `watch -n 1 'free -h'`

**Fix:**
- Upgrade to 4GB VPS
- Enable swap: `sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile`

---

## Production Monitoring

After deployment, monitor:

```bash
# Check memory usage
free -h

# Check cron logs
tail -f /var/lib/giggles/logs/nightly_processing.log | grep "🧠 Memory"

# Check for OOM kills
dmesg | grep -i "out of memory"
journalctl -k | grep -i "killed process"

# Check processing success
grep "✅ User" /var/lib/giggles/logs/nightly_processing.log | tail -10
```

**Alerts:**
- Memory after cleanup > 1 GB (investigate leak)
- OOM kills (upgrade VPS or optimize)
- Processing failures (check logs)

