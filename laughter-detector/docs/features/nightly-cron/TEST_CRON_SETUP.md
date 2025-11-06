# Testing Cron Job Setup Guide

## Step 1: Delete Data for 11/3 UTC (Today)

Run the cleanup script to delete all data for today:

```bash
cd /Users/neilsethi/git/giggles-cli/laughter-detector
source .venv/bin/activate
python cleanup_date_data.py 2025-11-03
```

When prompted, type `yes` to confirm.

This will delete:
- All laughter_detections from 11/3 UTC
- All audio_segments from 11/3 UTC
- All processing_logs for 11/3
- All OGG files from disk for 11/3
- All WAV clip files from disk for 11/3

## Step 2: Set Up Cron Job

### Option A: Manual Test (Run Now)

Test the cron job manually right now:

```bash
cd /Users/neilsethi/git/giggles-cli/laughter-detector
source .venv/bin/activate
python process_nightly_audio.py
```

This will process "yesterday" (11/2) for all users. Since you deleted 11/3 data, this won't affect your test.

### Option B: Schedule for Tomorrow Morning

Add to crontab to run at 9 AM UTC daily:

```bash
# Edit crontab
crontab -e

# Add this line (replace /path/to with your actual path):
0 9 * * * cd /Users/neilsethi/git/giggles-cli/laughter-detector && source .venv/bin/activate && python process_nightly_audio.py >> /tmp/laughter_cron.log 2>&1
```

### Option C: Schedule for Tonight (Test Run)

To test tonight, schedule it for a few minutes from now:

```bash
# Get current time in UTC
date -u

# Schedule for 5 minutes from now (example: if it's 23:15 UTC, schedule for 23:20)
crontab -e

# Add this line (replace HH:MM with your target time):
MM HH * * * cd /Users/neilsethi/git/giggles-cli/laughter-detector && source .venv/bin/activate && python process_nightly_audio.py >> /tmp/laughter_cron.log 2>&1
```

**Example**: If current UTC time is `23:15`, and you want it to run at `23:20`, add:
```
20 23 * * * cd /Users/neilsethi/git/giggles-cli/laughter-detector && source .venv/bin/activate && python process_nightly_audio.py >> /tmp/laughter_cron.log 2>&1
```

## Step 3: Verify It Works

### Check the logs:

```bash
# View cron log
tail -f /tmp/laughter_cron.log

# Or if using manual test, check the output directly
```

### What to Look For:

✅ **Success indicators:**
- `⏭️ Segment already fully processed for range ... skipping download` - No unnecessary downloads
- `📁 Audio Files Downloaded: X` - Only downloads if needed
- `🎭 Laughter Events Found: X` - Processes audio if segments exist but aren't processed
- `✅ Nightly processing completed successfully`

❌ **Failure indicators:**
- `❌ Error processing user audio`
- Missing logs or empty output
- Still downloading files that already exist

## Step 4: Check Results in Database

After the cron runs, verify:
1. Processing log was created for 11/3
2. Audio segments were downloaded (only if not already processed)
3. Laughter detections were created
4. No duplicate processing occurred

## Quick Commands Reference

```bash
# Delete data for a specific date
python cleanup_date_data.py YYYY-MM-DD

# Run nightly job manually
python process_nightly_audio.py

# View cron jobs
crontab -l

# Edit cron jobs
crontab -e

# View cron logs
tail -f /tmp/laughter_cron.log

# Remove a cron job (edit crontab and delete the line)
crontab -e
```

