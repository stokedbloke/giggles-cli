# Deployment Guide - Step-by-Step Instructions

This guide walks you through deploying Giggle Gauge to a DigitalOcean VPS.

## Prerequisites

- [ ] DigitalOcean account created
- [ ] Domain name (optional but recommended)
- [ ] SSH key pair generated
- [ ] Supabase project configured
- [ ] Code repository accessible

## Phase 1: Create DigitalOcean Droplet

### Step 1.1: Create Droplet

1. Log into DigitalOcean
2. Click "Create" → "Droplets"
3. Choose:
   - **Image:** Ubuntu 22.04 LTS
   - **Plan:** Basic ($12/month - 2 vCPU, 2GB RAM, 50GB SSD)
   - **Region:** Choose closest to your users
   - **Authentication:** SSH keys (add your public key)
   - **Hostname:** `giggles-production` (or your choice)
4. Click "Create Droplet"

### Step 1.2: Initial SSH Access

```bash
# From your local machine
ssh root@YOUR_DROPLET_IP

# You should be logged in now
```

### Step 1.3: Add SSH Key to Droplet

If you didn't add your SSH key during creation:

```bash
# On your local machine, copy your public key
cat ~/.ssh/id_rsa.pub

# On the droplet, add it to authorized_keys
mkdir -p ~/.ssh
echo "YOUR_PUBLIC_KEY" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

## Phase 2: Initial VPS Setup

### Step 2.1: Run Initial Setup Script

```bash
# On the droplet, as root
cd /tmp
git clone https://github.com/YOUR_USERNAME/giggles-cli.git
cd giggles-cli/laughter-detector
chmod +x scripts/deployment/setup_vps.sh
sudo bash scripts/deployment/setup_vps.sh
```

This script will:
- Update system packages
- Install Python, nginx, certbot, and other dependencies
- Create the `giggles` user
- Set up directories
- Configure firewall

### Step 2.2: Clone Repository

```bash
# Switch to giggles user
su - giggles

# Clone repository
cd /var/lib/giggles
git clone https://github.com/YOUR_USERNAME/giggles-cli.git
mv giggles-cli/laughter-detector laughter-detector
cd laughter-detector
```

### Step 2.3: Create Virtual Environment

```bash
# Still as giggles user
python3.9 -m venv /var/lib/giggles/venv
source /var/lib/giggles/venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Phase 3: Configure Environment

### Step 3.1: Create .env File

```bash
# As giggles user
cd /var/lib/giggles
cp laughter-detector/env.example .env
chmod 600 .env
nano .env
```

Fill in all required values (see `docs/deployment/ENVIRONMENT_SETUP.md` for details).

**Required values:**
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SECRET_KEY` (generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- `ENCRYPTION_KEY` (generate: `python -c "import secrets; print(secrets.token_hex(32))"`)
- `DATABASE_URL`
- `DEBUG=False`

### Step 3.2: Verify Configuration

```bash
source /var/lib/giggles/venv/bin/activate
cd /var/lib/giggles/laughter-detector
python -c "from src.config.settings import settings; print('✅ Config loaded')"
```

## Phase 4: Configure nginx

### Step 4.1: Copy nginx Configuration

```bash
# As root
sudo cp /var/lib/giggles/laughter-detector/nginx/giggles.conf /etc/nginx/sites-available/giggles
```

### Step 4.2: Edit nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/giggles
```

Update:
- Replace `server_name _;` with your domain name (or keep `_` for IP access)
- If using domain, replace `YOUR_DOMAIN` with your actual domain

### Step 4.3: Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/giggles /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

## Phase 5: Setup SSL (If Using Domain)

### Step 5.1: Configure DNS

Point your domain to the droplet IP:
- **A Record:** `@` → `YOUR_DROPLET_IP`
- **A Record:** `www` → `YOUR_DROPLET_IP` (optional)

Wait for DNS propagation (5-60 minutes).

### Step 5.2: Run SSL Setup Script

```bash
# As root
sudo bash /var/lib/giggles/laughter-detector/scripts/setup/setup_ssl.sh yourdomain.com
```

This will:
- Install certbot
- Obtain Let's Encrypt certificate
- Configure auto-renewal
- Update nginx config

## Phase 6: Deploy Application

### Step 6.1: Install Systemd Service

```bash
# As root
sudo cp /var/lib/giggles/laughter-detector/systemd/giggles.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable giggles
```

### Step 6.2: Run Deployment Script

```bash
# As giggles user
cd /var/lib/giggles/laughter-detector
bash scripts/deployment/deploy.sh
```

This will:
- Pull latest code
- Install dependencies
- Set permissions
- Start the service

### Step 6.3: Verify Service

```bash
# Check service status
sudo systemctl status giggles

# Check logs
sudo journalctl -u giggles -n 50

# Test endpoint
curl http://localhost:8000/health  # Should return 200
```

## Phase 7: Setup Cron Job

### Step 7.1: Configure Cron

```bash
# As root
sudo bash /var/lib/giggles/laughter-detector/scripts/deployment/setup_cron.sh
```

This creates a cron job that runs nightly audio processing at 2:00 AM.

### Step 7.2: Test Cron Job

```bash
# As giggles user
cd /var/lib/giggles/laughter-detector
source /var/lib/giggles/venv/bin/activate
python process_nightly_audio.py
```

## Phase 8: Final Verification

### Step 8.1: Test Application

1. **Health Check:**
   ```bash
   curl https://yourdomain.com/health
   ```

2. **Access Web UI:**
   - Open `https://yourdomain.com` in browser
   - Should see login page

3. **Test Authentication:**
   - Register a new account
   - Login
   - Upload audio file

### Step 8.2: Check Logs

```bash
# Application logs
sudo journalctl -u giggles -f

# Cron logs
tail -f /var/lib/giggles/logs/nightly_processing.log

# nginx logs
sudo tail -f /var/log/nginx/giggles-access.log
sudo tail -f /var/log/nginx/giggles-error.log
```

### Step 8.3: Security Verification

- [ ] Firewall configured (only 22, 80, 443 open)
- [ ] HTTPS working (SSL certificate valid)
- [ ] File permissions correct (`chmod 600 .env`, `chmod 640 uploads`)
- [ ] Service running as `giggles` user (not root)
- [ ] Fail2ban active

## Post-Deployment

### Monitoring

- Set up UptimeRobot (free) to monitor `https://yourdomain.com/health`
- Check logs regularly for errors
- Monitor disk space: `df -h`

### Backups

- DigitalOcean automatic backups (optional, $1.20/month)
- Manual database backups via Supabase dashboard
- File backups (if needed): `tar -czf backup.tar.gz /var/lib/giggles/uploads`

### Updates

To deploy updates:

```bash
# As giggles user
cd /var/lib/giggles/laughter-detector
bash scripts/deployment/deploy.sh
```

## Troubleshooting

See `docs/deployment/TROUBLESHOOTING.md` for common issues and solutions.

## Quick Reference

**Service Management:**
```bash
sudo systemctl start giggles
sudo systemctl stop giggles
sudo systemctl restart giggles
sudo systemctl status giggles
```

**View Logs:**
```bash
sudo journalctl -u giggles -n 100 -f
```

**Test nginx Config:**
```bash
sudo nginx -t
sudo systemctl reload nginx
```

**Check Firewall:**
```bash
sudo ufw status
```

**Test SSL Renewal:**
```bash
sudo certbot renew --dry-run
```

