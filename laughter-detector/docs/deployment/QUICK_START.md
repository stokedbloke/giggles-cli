# Quick Start - VPS Deployment

**TL;DR:** Get your app running on DigitalOcean in ~2 hours.

## Prerequisites Checklist

- [ ] DigitalOcean account (free to create)
- [ ] Domain name (optional - can use IP initially)
- [ ] SSH key pair (`ssh-keygen` if you don't have one)
- [ ] Supabase project with credentials ready

## Step-by-Step (30 minutes setup + 1.5 hours deployment)

### 1. Create DigitalOcean Droplet (10 min)

1. Go to DigitalOcean → Create → Droplets
2. Choose: Ubuntu 22.04, $12/month plan, add SSH key
3. Create droplet
4. Note the IP address

### 2. Initial Server Setup (20 min)

```bash
# SSH into your droplet
ssh root@YOUR_DROPLET_IP

# Clone repo and run setup
cd /tmp
git clone https://github.com/YOUR_USERNAME/giggles-cli.git
cd giggles-cli/laughter-detector
chmod +x scripts/deployment/setup_vps.sh
sudo bash scripts/deployment/setup_vps.sh
```

### 3. Clone & Configure (15 min)

```bash
# Switch to giggles user
su - giggles

# Clone repository
cd /var/lib/giggles
git clone https://github.com/YOUR_USERNAME/giggles-cli.git
mv giggles-cli/laughter-detector laughter-detector
cd laughter-detector

# Create venv and install
python3.9 -m venv /var/lib/giggles/venv
source /var/lib/giggles/venv/bin/activate
pip install -r requirements.txt

# Create .env file
cp env.example /var/lib/giggles/.env
chmod 600 /var/lib/giggles/.env
nano /var/lib/giggles/.env  # Fill in your values
```

### 4. Deploy Application (20 min)

```bash
# Install systemd service
sudo cp systemd/giggles.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable giggles

# Deploy
bash scripts/deployment/deploy.sh
```

### 5. Configure nginx (15 min)

```bash
# As root
sudo cp /var/lib/giggles/laughter-detector/nginx/giggles.conf /etc/nginx/sites-available/giggles
sudo nano /etc/nginx/sites-available/giggles  # Update server_name if using domain
sudo ln -s /etc/nginx/sites-available/giggles /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Setup SSL (If using domain) (10 min)

```bash
# Configure DNS first (A record pointing to droplet IP)
# Then run:
sudo bash /var/lib/giggles/laughter-detector/scripts/setup/setup_ssl.sh yourdomain.com
```

### 7. Setup Cron (5 min)

```bash
sudo bash /var/lib/giggles/laughter-detector/scripts/deployment/setup_cron.sh
```

## Verify It Works

```bash
# Check service
sudo systemctl status giggles

# Test locally
curl http://localhost:8000

# Test via nginx (if using domain)
curl https://yourdomain.com
```

## What You Get

✅ Application running on VPS  
✅ HTTPS/SSL (if using domain)  
✅ Auto-restart on failure (systemd)  
✅ Nightly audio processing (cron)  
✅ Firewall configured  
✅ Security hardened  

## Next Steps

- Set up monitoring (UptimeRobot - free)
- Configure backups
- Test full user flow
- Monitor logs for first 24 hours

## Need Help?

- **Full guide:** `docs/deployment/DEPLOYMENT_GUIDE.md`
- **Troubleshooting:** `docs/deployment/TROUBLESHOOTING.md`
- **Environment setup:** `docs/deployment/ENVIRONMENT_SETUP.md`

## Cost

- **VPS:** $12/month
- **Domain:** $0-15/year (optional)
- **SSL:** Free (Let's Encrypt)
- **Total:** ~$13-15/month

---

**Time estimate:** 2-3 hours for first deployment (including learning curve)

