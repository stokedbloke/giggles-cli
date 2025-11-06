# Next Feature Branch: VPS Deployment

## Branch Name
`feature/vps-deployment`

## Overview
Prepare the application for production deployment on a VPS (DigitalOcean, AWS, etc.) with proper process management, web server configuration, SSL/TLS, monitoring, and backup strategies.

## Tasks

### 1. Process Management
- [ ] Create `systemd/giggles.service` file
  - FastAPI app as systemd service
  - Auto-restart on failure
  - Proper logging configuration
- [ ] Configure log rotation (`logrotate` config)
  - Rotate logs daily/weekly
  - Compress old logs
  - Keep 30 days of logs

### 2. Web Server Configuration
- [ ] Create `nginx/giggles.conf` configuration
  - Reverse proxy for FastAPI (port 8000)
  - Static file serving
  - HTTP → HTTPS redirect
  - Security headers
- [ ] SSL/TLS Setup (Let's Encrypt)
  - Certbot installation
  - Auto-renewal configuration
  - Domain/DNS configuration

### 3. Production Environment
- [ ] Create `.env.production.example` template
  - All required environment variables
  - Production-specific settings
  - Security best practices
- [ ] Update `main.py` for production
  - CORS settings for production domain
  - `allowed_hosts` for production domain
  - Debug mode disabled

### 4. Cron Job Configuration
- [ ] Production cron entry
  - Proper paths (absolute paths)
  - Virtual environment activation
  - Log file location and rotation
- [ ] Error notification setup
  - Email alerts on cron failures
  - Log monitoring

### 5. Security Hardening
- [ ] Firewall configuration (UFW)
  - Only allow SSH (22), HTTP (80), HTTPS (443)
  - Block all other ports
- [ ] SSH key-only access
  - Disable password authentication
  - Configure SSH keys
- [ ] Fail2ban setup
  - Protect against brute force attacks
  - Configure jail rules

### 6. Monitoring & Logging
- [ ] Centralized log location
  - `/var/log/giggles/` directory
  - Proper permissions
- [ ] Log aggregation
  - Centralized log collection
  - Error tracking setup
- [ ] Disk space monitoring
  - Script to monitor disk usage
  - Alert on low disk space
- [ ] Health check endpoint
  - Verify `/health` endpoint works
  - Add more detailed health checks

### 7. Backup Strategy
- [ ] Database backup script
  - Supabase data exports
  - Automated daily backups
  - Backup retention policy
- [ ] File backup script
  - User clips and audio files
  - Automated daily backups
  - Backup retention policy
- [ ] Restore procedure documentation
  - Step-by-step restore guide
  - Test restore procedure

### 8. Deployment Documentation
- [ ] Create `DEPLOYMENT.md`
  - Step-by-step VPS setup guide
  - Initial server setup
  - Application deployment process
  - Environment configuration
  - Service configuration
- [ ] Create `TROUBLESHOOTING.md`
  - Common issues and solutions
  - Log file locations
  - Debug procedures
  - Recovery procedures

### 9. Testing
- [ ] Test deployment on staging VPS
  - Full deployment process
  - Verify all services work
  - Test cron job execution
  - Test error scenarios
- [ ] Load testing (optional)
  - Test under load
  - Identify bottlenecks

## Files to Create

```
feature/vps-deployment/
├── systemd/
│   └── giggles.service
├── nginx/
│   └── giggles.conf
├── scripts/
│   ├── backup_database.sh
│   ├── backup_files.sh
│   ├── monitor_disk_space.sh
│   └── setup_ssl.sh
├── DEPLOYMENT.md
└── TROUBLESHOOTING.md
```

## Key Configuration Files

### systemd/giggles.service
```ini
[Unit]
Description=Giggles Laughter Detection API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/laughter-detector
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### nginx/giggles.conf
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy to FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static {
        alias /path/to/laughter-detector/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

## Environment Variables for Production

Create `.env.production.example`:
```bash
# Supabase Configuration
SUPABASE_URL=your_production_supabase_url
SUPABASE_KEY=your_production_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_production_service_role_key

# Security
SECRET_KEY=your_strong_production_secret_key
ENCRYPTION_KEY=your_64_char_hex_encryption_key

# Application
DEBUG=False
HOST=127.0.0.1
PORT=8000
ALLOWED_ORIGINS=https://yourdomain.com

# File Storage
UPLOAD_DIR=/var/lib/giggles/uploads
MAX_FILE_SIZE=104857600

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
```

## Testing Checklist

Before merging to main:
- [ ] All services start correctly
- [ ] Nginx reverse proxy works
- [ ] SSL certificate is valid and auto-renewing
- [ ] Cron job executes successfully
- [ ] Backups run and are restorable
- [ ] Monitoring and alerts work
- [ ] Health checks pass
- [ ] Static files are served correctly
- [ ] All API endpoints work
- [ ] Error handling works correctly

## Estimated Time
- Process Management: 2-3 hours
- Web Server Setup: 2-3 hours
- SSL/TLS: 1-2 hours
- Security Hardening: 2-3 hours
- Monitoring & Logging: 2-3 hours
- Backup Strategy: 3-4 hours
- Documentation: 2-3 hours
- Testing: 3-4 hours

**Total: ~20-25 hours**


