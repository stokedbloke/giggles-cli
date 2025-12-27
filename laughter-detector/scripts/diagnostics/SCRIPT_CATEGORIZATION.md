# Diagnostic Scripts Categorization Guide

## 🟢 SAFE FOR PRODUCTION (Read-Only)

### 1. `analyze_production_500s_readonly.py`
**Purpose:** Find days with 500 errors in production (read-only analysis)  
**Safety:** ✅ ZERO RISK - Only reads data  
**When to use:** Before testing - find best test days  
**Usage:**
```bash
# On MacBook
python scripts/diagnostics/analyze_production_500s_readonly.py --days 60
```
**Output:** List of days with 500 errors, best test candidates

---

### 2. `analyze_500_errors.py`
**Purpose:** Analyze 500 errors for a specific day (read-only)  
**Safety:** ✅ ZERO RISK - Only reads data  
**When to use:** Investigate a specific day with 500 errors  
**Usage:**
```bash
# On MacBook or Production
python scripts/diagnostics/analyze_500_errors.py 2025-12-20
```
**Output:** Per-user breakdown of 500 errors, API calls, laughter counts

---

### 3. `analyze_last_5_days.py`
**Purpose:** Analyze last 5 days of processing (read-only)  
**Safety:** ✅ ZERO RISK - Only reads data  
**When to use:** Quick overview of recent processing  
**Usage:**
```bash
# On Production Server
python scripts/diagnostics/analyze_last_5_days.py
```
**Output:** Daily metrics for all users (laughs, segments, API calls)

---

### 4. `quick_user_stats.py`
**Purpose:** Quick user statistics (read-only)  
**Safety:** ✅ ZERO RISK - Only reads data  
**When to use:** Get quick overview of user activity  
**Usage:**
```bash
# On Production Server
python scripts/diagnostics/quick_user_stats.py
```
**Output:** Days on platform, laughter stats per user

---

### 5. `check_user_processing_status_fixed.py`
**Purpose:** Check user processing status (read-only)  
**Safety:** ✅ ZERO RISK - Only reads data  
**When to use:** Debug specific user/date processing issues  
**Usage:**
```bash
python scripts/diagnostics/check_user_processing_status_fixed.py USER_ID DATE
```

---

### 6. `check_user_day.sh`
**Purpose:** Quick check for user on specific day (read-only)  
**Safety:** ✅ ZERO RISK - Only reads data  
**When to use:** Quick status check  
**Usage:**
```bash
bash scripts/diagnostics/check_user_day.sh 2025-12-20 USER_ID
```

---

### 7. `find_days_with_500_errors.py`
**Purpose:** Find all days with 500 errors (read-only)  
**Safety:** ✅ ZERO RISK - Only reads data  
**When to use:** Find test candidates  
**Usage:**
```bash
python scripts/diagnostics/find_days_with_500_errors.py --days 60
```

---

## 🟡 SAFE FOR PRODUCTION (Reprocesses Single Days)

### 8. `test_single_day_production.sh`
**Purpose:** Test retry logic on ONE day for ONE user  
**Safety:** ✅ LOW RISK - Only reprocesses one day, can reprocess again  
**When to use:** Test retry logic on production after deployment  
**Usage:**
```bash
# On Production Server
bash scripts/diagnostics/test_single_day_production.sh 2025-12-20 USER_ID
```
**What it does:**
1. Records BEFORE metrics
2. Reprocesses the day
3. Records AFTER metrics
4. Shows comparison

---

### 9. `reprocess_user_day.sh`
**Purpose:** Reprocess a specific day for a user  
**Safety:** ✅ LOW RISK - Just reprocessing, no permanent changes  
**When to use:** Manual reprocessing of a specific day  
**Usage:**
```bash
bash scripts/diagnostics/reprocess_user_day.sh 2025-12-20 USER_ID
```

---

## 🟠 STAGING ONLY (Not for Production)

### 10. `test_retry_methodical.py`
**Purpose:** Methodical test of retry logic (tests multiple days)  
**Safety:** ⚠️ STAGING ONLY - Tests multiple days  
**When to use:** Comprehensive testing on staging before production  
**Usage:**
```bash
# On MacBook (staging)
python scripts/diagnostics/test_retry_methodical.py --days 60 --min-500-errors 1 --limit 5
```
**Why staging only:** Tests multiple days, better to test on staging first

---

### 11. `test_retry_definitive.sh`
**Purpose:** Test retry logic on staging (tries multiple dates)  
**Safety:** ⚠️ STAGING ONLY - Tests multiple dates  
**When to use:** Test retry logic on staging  
**Usage:**
```bash
# On MacBook (staging)
bash scripts/diagnostics/test_retry_definitive.sh
```

---

### 12. `test_all_500_days.sh`
**Purpose:** Test all days with 500 errors in staging  
**Safety:** ⚠️ STAGING ONLY - Tests all days  
**When to use:** Comprehensive staging test  
**Usage:**
```bash
# On MacBook (staging)
bash scripts/diagnostics/test_all_500_days.sh
```

---

### 13. `test_retry_comprehensive.sh`
**Purpose:** Comprehensive retry test (finds best cases)  
**Safety:** ⚠️ STAGING ONLY - Tests multiple days  
**When to use:** Find and test best test cases on staging  
**Usage:**
```bash
# On MacBook (staging)
bash scripts/diagnostics/test_retry_comprehensive.sh
```

---

### 14. `quick_test.sh`
**Purpose:** Quick test script (edit TEST_CASES array)  
**Safety:** ⚠️ STAGING ONLY - Tests multiple days  
**When to use:** Quick testing of specific days on staging  
**Usage:**
```bash
# On MacBook (staging)
# Edit TEST_CASES array in script first
bash scripts/diagnostics/quick_test.sh
```

---

## 🔴 DEBUGGING ONLY (Not for Production Testing)

### 15. `verify_retry_logic.py`
**Purpose:** Verify retry logic was triggered  
**Safety:** ✅ Read-only, but debugging tool  
**When to use:** Debug why retry logic didn't work  
**Usage:**
```bash
python scripts/diagnostics/verify_retry_logic.py DATE USER_ID
```

---

### 16. `verify_retry_with_certainty.py`
**Purpose:** Verify retry logic with certainty  
**Safety:** ✅ Read-only, but debugging tool  
**When to use:** Debug retry logic issues  
**Usage:**
```bash
python scripts/diagnostics/verify_retry_with_certainty.py DATE USER_ID
```

---

### 17. `investigate_laughter_decrease.py`
**Purpose:** Investigate why laughter decreased  
**Safety:** ✅ Read-only, but debugging tool  
**When to use:** Debug laughter decrease issues  
**Usage:**
```bash
python scripts/diagnostics/investigate_laughter_decrease.py DATE USER_ID
```

---

### 18. `investigate_laughter_decrease_detailed.py`
**Purpose:** Detailed investigation of laughter decrease  
**Safety:** ✅ Read-only, but debugging tool  
**When to use:** Deep dive into laughter decrease  
**Usage:**
```bash
python scripts/diagnostics/investigate_laughter_decrease_detailed.py DATE USER_ID
```

---

### 19. `investigate_mismatch_29_vs_23.py`
**Purpose:** Investigate mismatch between expected and actual detections  
**Safety:** ✅ Read-only, but debugging tool  
**When to use:** Debug counting mismatches  
**Usage:**
```bash
python scripts/diagnostics/investigate_mismatch_29_vs_23.py DATE USER_ID
```

---

## 📋 RECOMMENDED PRODUCTION TESTING WORKFLOW

### Step 1: Find Test Days (Read-Only)
```bash
# On MacBook
python scripts/diagnostics/analyze_production_500s_readonly.py --days 60
```
**Output:** Best test candidates

### Step 2: Test Single Day (Safe)
```bash
# On Production Server
bash scripts/diagnostics/test_single_day_production.sh DATE USER_ID
```
**Output:** Before/after comparison

### Step 3: Analyze Results (Read-Only)
```bash
# On MacBook or Production
python scripts/diagnostics/analyze_500_errors.py DATE
```
**Output:** Detailed breakdown

---

## 🚫 DO NOT USE ON PRODUCTION

These test multiple days automatically - use on staging only:
- `test_retry_methodical.py` (unless limited to 1-2 days)
- `test_retry_definitive.sh`
- `test_all_500_days.sh`
- `test_retry_comprehensive.sh`
- `quick_test.sh`

---

## 📊 Quick Reference

| Script | Safety | Use Case | Production? |
|--------|--------|----------|------------|
| `analyze_production_500s_readonly.py` | ✅ Zero risk | Find test days | ✅ Yes |
| `test_single_day_production.sh` | ✅ Low risk | Test one day | ✅ Yes |
| `analyze_500_errors.py` | ✅ Zero risk | Analyze specific day | ✅ Yes |
| `test_retry_methodical.py` | ⚠️ Multiple days | Comprehensive test | ❌ Staging only |
| `quick_test.sh` | ⚠️ Multiple days | Quick test | ❌ Staging only |

---

## 🎯 For Your Current Goal (Test Retry Logic on Production)

**Recommended workflow:**

1. **Find test days (read-only):**
   ```bash
   python scripts/diagnostics/analyze_production_500s_readonly.py --days 60
   ```

2. **Test ONE day (safe):**
   ```bash
   bash scripts/diagnostics/test_single_day_production.sh DATE USER_ID
   ```

3. **Review results (read-only):**
   ```bash
   python scripts/diagnostics/analyze_500_errors.py DATE
   ```

**That's it!** Safe, methodical, and gives you the evidence you need.

