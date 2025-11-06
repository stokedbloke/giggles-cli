# VPS Deployment Plan - Secure MVP Deployment

## 🎯 Objective
Deploy a secure, production-ready MVP on a VPS with:
- **Security First**: Encrypted storage, secure API key handling, HTTPS/TLS
- **Testability**: Staging environment, easy rollback
- **Maintainability**: Automated backups, monitoring, logging
- **Robustness**: Health checks, auto-restart, error handling

## 📊 Current State vs. Original PRP

### ✅ Already Implemented
- [x] Secure user authentication with Supabase (email/password)
- [x] Encrypted storage of Limitless API keys (AES-256-GCM)
- [x] Nightly audio processing with YAMNet
- [x] Mobile-responsive UI
- [x] Audio clip playback
- [x] Secure data deletion
- [x] Automated cleanup of orphaned files
- [x] Timezone-aware processing
- [x] Duplicate detection (3-layer)
- [x] Enhanced logging and error handling

### ❌ Missing from Original PRP
- [ ] **MFA implementation** - Mentioned but not implemented
- [ ] **Cryptographic file deletion** - Currently using `os.remove()` (simple delete)
- [ ] **Scheduled cleanup tasks** - Cleanup runs ad-hoc, not scheduled
- [ ] **Production deployment configuration** - This is what we're building now

### 🔒 Security Gaps to Address
1. **File Storage Security**: Currently plaintext on disk (acceptable for MVP if files are user-specific)
2. **HTTPS/TLS**: Need SSL certificates for production
3. **Firewall**: Need to restrict access
4. **Backup Encryption**: Need encrypted backups
5. **File Access Control**: Need proper file permissions

---

## 🛠️ Recommended Tools & Services

### Core Infrastructure

#### 1. **VPS Provider: DigitalOcean** ✅ RECOMMENDED
**Why DigitalOcean:**
- Simple, reliable, cost-effective
- Good documentation and community support
- Easy scaling if needed
- Good for first-time VPS deployment

**Cost:** $6-12/month (1-2 vCPU, 1-2GB RAM, 25GB SSD)
- **Recommendation:** $12/month droplet (2 vCPU, 2GB RAM, 50GB SSD)
- **Why:** Better performance for Python/FastAPI, headroom for growth

**Alternative:** Linode ($5/month basic), AWS Lightsail ($10/month)

#### 2. **Reverse Proxy: nginx** ✅ RECOMMENDED
**Why nginx:**
- Industry standard, well-documented
- Excellent performance
- Easy SSL/TLS configuration
- Good for serving static files

**Cost:** Free (open source)

#### 3. **SSL/TLS: Let's Encrypt (Certbot)** ✅ RECOMMENDED
**Why Let's Encrypt:**
- Free SSL certificates
- Auto-renewal via certbot
- Industry standard
- Perfect for MVP

**Cost:** Free

**Alternative:** Cloudflare SSL (free, but requires Cloudflare proxy)

#### 4. **Cloudflare Tunnel** ⚠️ OPTIONAL (Consider Alternatives)
**Why you might want it:**
- Hides origin server IP
- DDoS protection
- Optional: Cloudflare Access (zero-trust)

**Why you might NOT need it:**
- Adds complexity
- Another service to manage
- DigitalOcean has basic DDoS protection
- nginx + Let's Encrypt is sufficient for MVP

**Recommendation:** **SKIP for MVP** - Use nginx + Let's Encrypt directly. Add Cloudflare later if needed.

**Cost:** Free (if used)

#### 5. **Process Manager: systemd** ✅ RECOMMENDED
**Why systemd:**
- Built into Ubuntu/Debian
- Reliable auto-restart
- Easy logging
- No additional cost

**Cost:** Free (built-in)

**Alternative:** PM2 (Node.js style), supervisor (older approach)

#### 6. **Containerization: Docker** ⚠️ OPTIONAL
**Why Docker (optional for MVP):**
- Consistent deployment
- Easy rollback
- Isolation

**Why you might skip it:**
- Adds complexity
- Another layer to debug
- Not necessary for simple Python app
- systemd + virtualenv is sufficient

**Recommendation:** **SKIP for MVP** - Use systemd + virtualenv. Add Docker later if needed.

**Cost:** Free (if used)

#### 7. **Monitoring: UptimeRobot or BetterUptime** ✅ RECOMMENDED
**Why:**
- Monitor uptime
- Alert on downtime
- Simple and free

**Cost:** Free (basic monitoring)

---

## 🏗️ Recommended Architecture (Simple & Secure)

```
Internet
    ↓
[Cloudflare DNS] (optional - use your domain's DNS)
    ↓
[DigitalOcean VPS]
    ↓
[nginx] (reverse proxy, SSL termination)
    ↓
[FastAPI App] (systemd service, port 8000)
    ↓
[Python Virtual Environment]
    ↓
[File Storage: /var/lib/giggles/uploads/]
    ↓
[Supabase] (database, auth - external)
```

**Key Components:**
1. **Domain DNS** → Points to VPS IP
2. **nginx** → Handles HTTPS, reverse proxy, static files
3. **systemd** → Manages FastAPI app (auto-restart)
4. **cron** → Runs nightly processing
5. **Let's Encrypt** → Provides SSL certificates

---

## 📋 Implementation Plan

### Phase 1: VPS Setup & Security Hardening (4-6 hours)

#### Step 1.1: Create DigitalOcean Droplet (30 min)
- [ ] Create Ubuntu 22.04 LTS droplet
- [ ] Choose: 2 vCPU, 2GB RAM, 50GB SSD ($12/month)
- [ ] Add SSH key (NOT password auth)
- [ ] Enable backups ($1.20/month - optional but recommended)
- [ ] Configure firewall rules (allow SSH, HTTP, HTTPS only)

**Cost:** $12-13.20/month

#### Step 1.2: Initial Server Hardening (2 hours)
- [ ] Create non-root user with sudo
- [ ] Disable root login
- [ ] Configure SSH key-only access
- [ ] Install fail2ban (brute force protection)
- [ ] Configure UFW firewall (only 22, 80, 443 open)
- [ ] Set up automatic security updates

**Files to Create:**
- `scripts/initial_server_setup.sh`

#### Step 1.3: Domain & DNS Configuration (30 min)
- [ ] Point domain to VPS IP (A record)
- [ ] Verify DNS propagation
- [ ] Test HTTP access

**Cost:** $0-15/year (if you don't have a domain)

---

### Phase 2: Application Deployment (6-8 hours)

#### Step 2.1: Application Environment Setup (2 hours)
- [ ] Install Python 3.9+ and system dependencies
- [ ] Create application user (`giggles` user)
- [ ] Set up Python virtual environment
- [ ] Install application dependencies
- [ ] Configure environment variables (`.env` file)
- [ ] Set proper file permissions

**Files to Create:**
- `scripts/deploy_application.sh`
- `.env.production.example`

#### Step 2.2: systemd Service Configuration (1 hour)
- [ ] Create systemd service file
- [ ] Configure auto-restart on failure
- [ ] Set up log rotation
- [ ] Test service start/stop/restart

**Files to Create:**
- `systemd/giggles.service`
- `logrotate/giggles`

#### Step 2.3: nginx Configuration (2 hours)
- [ ] Install nginx
- [ ] Configure reverse proxy for FastAPI
- [ ] Configure static file serving
- [ ] Set up HTTP → HTTPS redirect
- [ ] Configure security headers
- [ ] Test configuration

**Files to Create:**
- `nginx/giggles.conf`
- `nginx/giggles-security.conf`

#### Step 2.4: SSL/TLS Setup (1 hour)
- [ ] Install certbot
- [ ] Obtain Let's Encrypt certificate
- [ ] Configure auto-renewal
- [ ] Test HTTPS access
- [ ] Verify certificate auto-renewal

**Files to Create:**
- `scripts/setup_ssl.sh`

#### Step 2.5: Cron Job Configuration (1 hour)
- [ ] Set up cron job for nightly processing
- [ ] Configure log file location
- [ ] Test cron job execution
- [ ] Set up error notification (email)

**Files to Create:**
- `scripts/setup_cron.sh`
- `cron/giggles-nightly`

---

### Phase 3: Backup & Monitoring (3-4 hours)

#### Step 3.1: Backup Strategy (2 hours)
- [ ] Database backup script (Supabase exports)
- [ ] File backup script (user clips/audio)
- [ ] Automated daily backups
- [ ] Encrypted backup storage (optional: Backblaze B2)
- [ ] Test restore procedure

**Files to Create:**
- `scripts/backup_database.sh`
- `scripts/backup_files.sh`
- `scripts/restore_from_backup.sh`

**Cost:** $0-1/month (if using Backblaze B2 for backups)

#### Step 3.2: Monitoring Setup (1-2 hours)
- [ ] Set up UptimeRobot (free monitoring)
- [ ] Configure health check endpoint
- [ ] Set up disk space monitoring
- [ ] Configure email alerts
- [ ] Test monitoring

**Files to Create:**
- `scripts/monitor_disk_space.sh`

**Cost:** Free (UptimeRobot free tier)

---

### Phase 4: Testing & Documentation (2-3 hours)

#### Step 4.1: Deployment Testing (1-2 hours)
- [ ] Test all endpoints
- [ ] Test cron job execution
- [ ] Test file uploads/downloads
- [ ] Test error scenarios
- [ ] Test SSL certificate renewal

#### Step 4.2: Documentation (1 hour)
- [ ] Create `DEPLOYMENT.md` with step-by-step guide
- [ ] Create `TROUBLESHOOTING.md` with common issues
- [ ] Document backup/restore procedures
- [ ] Document monitoring and alerts

**Files to Create:**
- `DEPLOYMENT.md`
- `TROUBLESHOOTING.md`
- `BACKUP_AND_RESTORE.md`

---

## 💰 Cost Breakdown

### Monthly Costs

| Service | Cost | Notes |
|---------|------|-------|
| DigitalOcean Droplet | $12/month | 2 vCPU, 2GB RAM, 50GB SSD |
| DigitalOcean Backups | $1.20/month | Optional but recommended |
| Domain (if needed) | $0-1.25/month | ~$15/year |
| Backblaze B2 (backups) | $0-1/month | ~10GB storage |
| **Total** | **$13.20-15.45/month** | ~$160-185/year |

### One-Time Costs
- Domain registration: $10-15/year (if you don't have one)
- SSL Certificate: Free (Let's Encrypt)

### Cost Optimization
- **MVP Scale (2-5 users):** $12/month is sufficient
- **Future Scale (10+ users):** May need $24/month droplet
- **Backups:** Start with DigitalOcean backups, add Backblaze if needed

---

## ⏱️ Time Estimates

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1: VPS Setup | Droplet, hardening, DNS | 4-6 hours |
| Phase 2: Application Deployment | App setup, systemd, nginx, SSL | 6-8 hours |
| Phase 3: Backup & Monitoring | Backup scripts, monitoring | 3-4 hours |
| Phase 4: Testing & Documentation | Testing, docs | 2-3 hours |
| **Total** | | **15-21 hours** |

**With learning curve (first time):** Add 20-30% buffer → **18-27 hours**

---

## 🔒 Security Considerations

### File Storage Security

**Current State:**
- Files stored in plaintext: `uploads/clips/{user_id}/*.wav`
- Files stored in plaintext: `uploads/audio/{user_id}/*.ogg`

**Recommendations for MVP:**
1. **File Permissions:**
   - Owner: `giggles` user (read/write)
   - Group: `giggles` group (read)
   - Others: No access (chmod 640)
   - Directory: chmod 750

2. **File System Security:**
   - Store files outside web root
   - Use nginx to serve files (not direct file access)
   - Validate file paths (prevent directory traversal)

3. **Access Control:**
   - nginx checks user authentication before serving files
   - FastAPI validates user_id matches file owner
   - RLS policies in Supabase ensure user can only access their files

**Future Enhancement (Post-MVP):**
- Encrypt files at rest (LUKS disk encryption or application-level encryption)
- Use encrypted backup storage

### API Key Security

**Current State:**
- ✅ API keys encrypted with AES-256-GCM
- ✅ Encrypted keys stored in database
- ✅ Decryption key derived from user_id

**Production Recommendations:**
1. **Environment Variables:**
   - Store encryption key in `.env` file (never in code)
   - Restrict file permissions: `chmod 600 .env`
   - Owner: `giggles` user only

2. **Secret Management:**
   - Consider using `python-decouple` or `python-dotenv`
   - Never commit `.env` to git
   - Rotate encryption keys periodically

3. **Database Security:**
   - Supabase RLS policies (already implemented)
   - Use service role key only in cron context
   - Never log API keys

### Network Security

1. **Firewall (UFW):**
   - Only allow: SSH (22), HTTP (80), HTTPS (443)
   - Block all other ports
   - Rate limit SSH connections

2. **HTTPS/TLS:**
   - Force HTTPS (redirect HTTP → HTTPS)
   - Use HSTS header
   - Enable TLS 1.2+ only

3. **Security Headers:**
   - Already implemented in `main.py`
   - Add via nginx as well (defense in depth)

---

## 📝 Deployment Checklist

### Pre-Deployment
- [ ] Review `DEPLOYMENT.md` guide
- [ ] Test deployment on staging (optional but recommended)
- [ ] Verify all environment variables documented
- [ ] Backup current database (if any)
- [ ] Test backup/restore procedure

### Deployment
- [ ] Create DigitalOcean droplet
- [ ] Configure server security
- [ ] Deploy application
- [ ] Configure nginx and SSL
- [ ] Set up cron job
- [ ] Configure backups
- [ ] Set up monitoring

### Post-Deployment
- [ ] Test all endpoints
- [ ] Verify cron job runs
- [ ] Test file uploads/downloads
- [ ] Verify SSL certificate auto-renewal
- [ ] Test backup/restore
- [ ] Monitor for 24-48 hours

---

## 🚀 Quick Start Commands

### Initial Server Setup
```bash
# On your local machine
ssh root@your-vps-ip

# Create deployment user
adduser giggles
usermod -aG sudo giggles
su - giggles

# Clone repository
git clone https://github.com/yourusername/giggles-cli.git
cd giggles-cli/laughter-detector
```

### Application Deployment
```bash
# Install dependencies
sudo apt update
sudo apt install python3-pip python3-venv nginx certbot python3-certbot-nginx

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with production values
chmod 600 .env

# Install systemd service
sudo cp systemd/giggles.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable giggles
sudo systemctl start giggles

# Configure nginx
sudo cp nginx/giggles.conf /etc/nginx/sites-available/giggles
sudo ln -s /etc/nginx/sites-available/giggles /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Setup SSL
sudo certbot --nginx -d yourdomain.com
```

---

## 🔄 Rollback Plan

If deployment fails:
1. **Application Rollback:**
   ```bash
   sudo systemctl stop giggles
   git checkout previous-commit
   sudo systemctl start giggles
   ```

2. **Database Rollback:**
   - Restore from backup (Supabase dashboard or script)

3. **File Rollback:**
   - Restore from backup (if using backup script)

---

## 📚 Next Steps

1. **Review this plan** - Confirm tools and approach
2. **Create deployment branch:** `feature/vps-deployment`
3. **Implement Phase 1** - VPS setup and security
4. **Test on staging** - Use a test domain or subdomain
5. **Deploy to production** - Follow the checklist

---

## ❓ Questions to Consider

1. **Do you have a domain name?** If not, register one (Namecheap, Google Domains, etc.)
2. **Staging environment?** Consider using a subdomain for testing (e.g., `staging.yourdomain.com`)
3. **Backup frequency?** Daily is recommended for MVP
4. **Monitoring alerts?** Email or SMS? (UptimeRobot supports both)

---

## 🎯 Recommended Tools Summary

| Tool | Recommendation | Cost | Time to Set Up |
|------|---------------|------|----------------|
| **VPS** | DigitalOcean | $12/month | 30 min |
| **Reverse Proxy** | nginx | Free | 2 hours |
| **SSL/TLS** | Let's Encrypt | Free | 1 hour |
| **Process Manager** | systemd | Free | 1 hour |
| **Containerization** | Skip (Docker) | - | - |
| **CDN/Proxy** | Skip (Cloudflare) | - | - |
| **Monitoring** | UptimeRobot | Free | 30 min |
| **Backups** | DigitalOcean + Scripts | $1.20/month | 2 hours |

**Total Monthly Cost:** ~$13-15/month  
**Total Setup Time:** 15-21 hours (18-27 hours with learning curve)

---

## ✅ Security Checklist

- [ ] SSH key-only access (no passwords)
- [ ] Firewall configured (UFW)
- [ ] Fail2ban installed
- [ ] Automatic security updates enabled
- [ ] HTTPS/TLS configured
- [ ] Security headers configured
- [ ] File permissions restricted (chmod 640/750)
- [ ] Environment variables secured (.env with chmod 600)
- [ ] Database backups encrypted
- [ ] Monitoring and alerts configured
- [ ] Log rotation configured
- [ ] Health checks configured

---

This plan prioritizes security, simplicity, and maintainability while keeping costs low for your MVP scale.


