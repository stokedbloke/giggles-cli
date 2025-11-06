# Nightly Cron Job Implementation Plan

## Current Status
- ✅ Branch created: `feature/nightly-cron-job`
- ✅ `process_nightly_audio.py` exists but needs updates
- ✅ Scheduler has `_process_user_audio()` method ready to use
- ⚠️ Script still uses `logger` instead of `print()`
- ⚠️ Script may have outdated patterns from `enhanced_logger`

## Tasks

### 1. Update `process_nightly_audio.py`
- [ ] Replace all `logger` calls with `print()`
- [ ] Remove `logging` module imports
- [ ] Update to use scheduler's `_process_user_audio()` directly
- [ ] Ensure enhanced_logger is initialized with `trigger_type='scheduled'`
- [ ] Test script runs successfully standalone

### 2. Test Locally
- [ ] Run script manually to verify it works
- [ ] Verify it processes users correctly
- [ ] Verify logs are created in database
- [ ] Test with 0 users, 1 user, multiple users

### 3. Cron Setup Documentation
- [ ] Update `CRON_SETUP_GUIDE.md` with current paths
- [ ] Provide clear macOS local testing instructions
- [ ] Provide DigitalOcean VPS instructions
- [ ] Include troubleshooting section

### 4. Cron Configuration
- [ ] Create example crontab entry
- [ ] Set default time (e.g., 2:00 AM daily)
- [ ] Configure log file location
- [ ] Test cron job locally on macOS

### 5. Integration
- [ ] Verify script works with existing scheduler code
- [ ] Ensure no conflicts with manual "Update Today" button
- [ ] Test incremental processing (should skip already-processed chunks)

## Files to Modify
1. `process_nightly_audio.py` - Main cron script
2. `CRON_SETUP_GUIDE.md` - Documentation
3. `cron_configuration.txt` - Example cron entries

## Testing Strategy
1. Run script manually first
2. Add to crontab with `* * * * *` (every minute) for testing
3. Verify it runs and processes correctly
4. Change to `0 2 * * *` (2 AM daily) for production

