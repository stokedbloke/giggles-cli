# Troubleshooting Guide

Common issues and solutions for Giggle Gauge deployment.

## Service Won't Start

### Check Service Status
```bash
sudo systemctl status giggles
```

### View Error Logs
```bash
sudo journalctl -u giggles -n 100
```

### Common Causes

**1. Missing .env file**
```bash
# Solution: Create .env file
cd /var/lib/giggles
cp laughter-detector/env.example .env
chmod 600 .env
nano .env  # Fill in values
```

**2. Invalid environment variables**
```bash
# Test configuration loading
cd /var/lib/giggles/laughter-detector
source /var/lib/giggles/venv/bin/activate
python -c "from src.config.settings import settings; print(settings.supabase_url)"
```

**3. Wrong Python version**
```bash
# Check Python version (needs 3.9+)
python3.9 --version

# Recreate venv if needed
rm -rf /var/lib/giggles/venv
python3.9 -m venv /var/lib/giggles/venv
```

**4. Missing dependencies**
```bash
source /var/lib/giggles/venv/bin/activate
pip install -r requirements.txt
```

**5. Permission issues**
```bash
# Fix ownership
sudo chown -R giggles:giggles /var/lib/giggles
sudo chmod 600 /var/lib/giggles/.env
```

## nginx Issues

### Test Configuration
```bash
sudo nginx -t
```

### Common Errors

**1. "502 Bad Gateway"**
- Application not running: `sudo systemctl status giggles`
- Wrong port: Check nginx config points to `127.0.0.1:8000`
- Firewall blocking: Check `sudo ufw status`

**2. "Connection refused"**
- Application not listening: Check `sudo netstat -tlnp | grep 8000`
- Wrong host: Application should listen on `127.0.0.1`, not `0.0.0.0` (nginx handles external)

**3. "SSL certificate error"**
- Certificate expired: `sudo certbot renew`
- Wrong domain: Check nginx config `server_name` matches certificate
- DNS not propagated: Wait or check DNS with `dig yourdomain.com`

### Reload nginx
```bash
sudo systemctl reload nginx
```

## SSL Certificate Issues

### Certificate Expired
```bash
# Renew certificate
sudo certbot renew

# Test auto-renewal
sudo certbot renew --dry-run
```

### Certificate Not Found
```bash
# Re-run SSL setup
sudo bash /var/lib/giggles/laughter-detector/scripts/setup/setup_ssl.sh yourdomain.com
```

### Wrong Domain
```bash
# Update nginx config
sudo nano /etc/nginx/sites-available/giggles
# Update server_name and certificate paths
sudo nginx -t
sudo systemctl reload nginx
```

## Database Connection Issues

### Supabase Connection Failed

**Check credentials:**
```bash
# Verify .env file has correct values
cat /var/lib/giggles/.env | grep SUPABASE
```

**Test connection:**
```bash
cd /var/lib/giggles/laughter-detector
source /var/lib/giggles/venv/bin/activate
python -c "from supabase import create_client; import os; from dotenv import load_dotenv; load_dotenv('/var/lib/giggles/.env'); client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')); print('✅ Connected')"
```

**Common issues:**
- Wrong URL (should be `https://xxx.supabase.co`, no trailing slash)
- Wrong key (anon key vs service role key)
- Network firewall blocking Supabase

## File Permission Issues

### "Permission denied" errors

**Fix ownership:**
```bash
sudo chown -R giggles:giggles /var/lib/giggles
```

**Fix permissions:**
```bash
# .env file
sudo chmod 600 /var/lib/giggles/.env

# Upload directories
sudo chmod 750 /var/lib/giggles/uploads
sudo find /var/lib/giggles/uploads -type f -exec chmod 640 {} \;
sudo find /var/lib/giggles/uploads -type d -exec chmod 750 {} \;
```

## Cron Job Issues

### Cron Not Running

**Check cron file:**
```bash
cat /etc/cron.d/giggles-nightly
```

**Check cron logs:**
```bash
tail -f /var/lib/giggles/logs/nightly_processing.log
```

**Test manually:**
```bash
cd /var/lib/giggles/laughter-detector
source /var/lib/giggles/venv/bin/activate
python process_nightly_audio.py
```

**Common issues:**
- Wrong Python path in cron (use full path: `/var/lib/giggles/venv/bin/python`)
- Missing environment variables (cron doesn't load .env automatically)
- Permission issues (cron runs as root, but files owned by giggles)

## Firewall Issues

### Can't Access Application

**Check firewall status:**
```bash
sudo ufw status
```

**Allow required ports:**
```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
```

**Check if port is listening:**
```bash
sudo netstat -tlnp | grep :8000
```

## Disk Space Issues

### Out of Disk Space

**Check disk usage:**
```bash
df -h
du -sh /var/lib/giggles/*
```

**Clean up:**
```bash
# Remove old logs
sudo journalctl --vacuum-time=7d

# Remove old uploads (if needed)
# Be careful - this deletes user data!
```

## Application Errors

### Import Errors

**Reinstall dependencies:**
```bash
source /var/lib/giggles/venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Encryption Key Errors

**"Encryption key must be exactly 64 hex characters"**
```bash
# Generate new key
python -c "import secrets; print(secrets.token_hex(32))"
# Update .env file
nano /var/lib/giggles/.env
```

### Audio Processing Errors

**Check YAMNet model:**
```bash
# Model downloads on first use
# Check internet connectivity
ping tfhub.dev
```

**Check audio file permissions:**
```bash
ls -la /var/lib/giggles/uploads/audio/
```

## Network Issues

### Can't Reach Application

**Check if service is running:**
```bash
sudo systemctl status giggles
curl http://localhost:8000/health
```

**Check nginx:**
```bash
sudo systemctl status nginx
curl http://localhost/health
```

**Check DNS:**
```bash
dig yourdomain.com
nslookup yourdomain.com
```

## Quick Diagnostic Commands

```bash
# Service status
sudo systemctl status giggles nginx

# Recent logs
sudo journalctl -u giggles -n 50
sudo tail -n 50 /var/log/nginx/giggles-error.log

# Network connectivity
curl http://localhost:8000/health
curl https://yourdomain.com/health

# Disk space
df -h
du -sh /var/lib/giggles/*

# Process status
ps aux | grep uvicorn
ps aux | grep nginx

# Port status
sudo netstat -tlnp | grep -E ':(80|443|8000)'
```

## Getting Help

If issues persist:

1. **Check logs:** All logs are in `/var/lib/giggles/logs/` and `journalctl`
2. **Verify configuration:** Run diagnostic commands above
3. **Check documentation:** Review `DEPLOYMENT_GUIDE.md` and `ENVIRONMENT_SETUP.md`
4. **Test components:** Test each component individually (service, nginx, SSL, database)

## Common Solutions Summary

| Issue | Solution |
|-------|----------|
| Service won't start | Check logs: `sudo journalctl -u giggles -n 100` |
| 502 Bad Gateway | Check service: `sudo systemctl status giggles` |
| SSL error | Renew cert: `sudo certbot renew` |
| Permission denied | Fix ownership: `sudo chown -R giggles:giggles /var/lib/giggles` |
| Can't connect to DB | Verify .env credentials |
| Cron not running | Check cron file and test manually |
| Out of space | Clean logs: `sudo journalctl --vacuum-time=7d` |

