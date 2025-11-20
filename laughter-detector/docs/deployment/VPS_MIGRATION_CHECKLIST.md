# VPS Migration Checklist

## Pre-Migration (Old VPS)

- [ ] Backup `.env` file: `cp /var/lib/giggles/.env ~/env_backup.txt`
- [ ] Backup cron: `crontab -l > ~/crontab_backup.txt`
- [ ] Backup nginx config: `sudo cp /etc/nginx/sites-available/giggles ~/nginx_backup.conf`
- [ ] Note current memory usage: `free -h`
- [ ] Note disk usage: `df -h /var/lib/giggles`

## New VPS Setup

### Initial Setup
- [ ] Create base directory: `sudo mkdir -p /var/lib/giggles && sudo chown giggles:giggles /var/lib/giggles`
- [ ] Create upload directories: `mkdir -p /var/lib/giggles/uploads/{audio,clips,temp}`
- [ ] Create logs directory: `mkdir -p /var/lib/giggles/logs`
- [ ] Set permissions: `chmod -R 755 /var/lib/giggles/uploads && chmod 755 /var/lib/giggles/logs`

### Install Dependencies
- [ ] Update system: `sudo apt update`
- [ ] Install Python packages: `sudo apt install -y python3 python3-pip python3-venv git build-essential`
- [ ] Install audio libraries: `sudo apt install -y libsndfile1 libsndfile1-dev ffmpeg python3-dev`

### Code Deployment
- [ ] Clone repository: `cd /var/lib/giggles && git clone https://github.com/YOUR_USERNAME/giggles-cli.git`
- [ ] Navigate to project: `cd giggles-cli/laughter-detector`
- [ ] Create venv: `python3 -m venv venv_linux`
- [ ] Activate venv: `source venv_linux/bin/activate`
- [ ] Upgrade pip: `pip install --upgrade pip`
- [ ] Install requirements: `pip install -r requirements.txt`
- [ ] Verify psutil: `pip list | grep psutil` (should show psutil>=5.9.0)

### Environment Configuration
- [ ] Copy `.env` from old VPS or recreate from backup
- [ ] Place `.env` at: `/var/lib/giggles/.env`
- [ ] Verify `.env` loading: `python3 -c "from dotenv import load_dotenv; from pathlib import Path; load_dotenv(Path('/var/lib/giggles/.env')); import os; print('SUPABASE_URL:', os.getenv('SUPABASE_URL')[:20] + '...')"`

### Test Installation
- [ ] Test database connection: `python3 -c "from src.services.supabase_client import get_service_role_client; client = get_service_role_client(); print('✅ Database connection OK')"`
- [ ] Test memory logging: `python3 -c "import psutil; import os; p = psutil.Process(os.getpid()); print(f'✅ Memory logging OK: {p.memory_info().rss / 1024 / 1024:.1f} MB')"`

### Cron Setup
- [ ] Edit crontab: `crontab -e`
- [ ] Add cron entry:
  ```
  0 2 * * * cd /var/lib/giggles/laughter-detector/laughter-detector && /var/lib/giggles/laughter-detector/venv_linux/bin/python3 process_nightly_audio.py >> /var/lib/giggles/logs/nightly_processing.log 2>&1
  ```
- [ ] Verify cron: `crontab -l`

### Manual Test Run
- [ ] Run test with one user: `python3 process_nightly_audio.py --user-id TEST_USER_ID`
- [ ] Check logs: `tail -f /var/lib/giggles/logs/nightly_processing.log`
- [ ] Verify memory cleanup: `grep "🧠 Memory" /var/lib/giggles/logs/nightly_processing.log | tail -10`
- [ ] Verify detections in database (check Supabase dashboard)

## Post-Migration Verification

### First Cron Run
- [ ] Wait for first cron execution (or trigger manually)
- [ ] Check logs: `tail -100 /var/lib/giggles/logs/nightly_processing.log`
- [ ] Verify no errors: `grep -i "error\|exception\|traceback" /var/lib/giggles/logs/nightly_processing.log`
- [ ] Verify memory cleanup: `grep "🧠 Memory after user cleanup" /var/lib/giggles/logs/nightly_processing.log | tail -5`

### System Health
- [ ] Check memory usage: `free -h` (should show adequate free memory)
- [ ] Check disk space: `df -h /var/lib/giggles` (should have space for uploads)
- [ ] Check process: `ps aux | grep process_nightly_audio` (should not be stuck)

### Database Verification
- [ ] Check processing_logs table for new entries
- [ ] Verify laughter_detections are being created
- [ ] Verify audio_segments are being stored
- [ ] Check for orphaned files: `find /var/lib/giggles/uploads -type f -mtime +1 | wc -l`

## Rollback Plan (If Needed)

- [ ] Keep old VPS running for 1 week
- [ ] If issues occur, revert DNS/load balancer to old VPS
- [ ] Restore cron on old VPS: `crontab ~/crontab_backup.txt`
- [ ] Investigate issues on new VPS before retrying

## Success Criteria

✅ All checklist items completed  
✅ Test run processes successfully  
✅ Memory cleanup working (logs show cleanup)  
✅ First cron run completes without errors  
✅ Database shows new detections  
✅ No OOM errors in logs  

**If all criteria met:** ✅ **Migration successful!**

