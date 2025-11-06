# Environment Setup Guide

This guide explains how to configure environment variables for production deployment.

## Required Environment Variables

### Supabase Configuration

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
```

**Where to find:**
- Supabase Dashboard → Project Settings → API
- `SUPABASE_URL`: Project URL
- `SUPABASE_KEY`: `anon` `public` key (used by frontend)
- `SUPABASE_SERVICE_ROLE_KEY`: `service_role` `secret` key (used by backend/cron)

**Security:** The service role key has admin access. Keep it secure!

### Security Configuration

```env
SECRET_KEY=your_secret_key_for_jwt_tokens_here
ENCRYPTION_KEY=your_32_byte_encryption_key_here
```

**How to generate:**
```bash
# Generate SECRET_KEY (any random string, 32+ characters recommended)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate ENCRYPTION_KEY (must be exactly 64 hex characters = 32 bytes)
python -c "import secrets; print(secrets.token_hex(32))"
```

**Security:** These keys encrypt user API keys. Never share or commit them!

### Database Configuration

```env
DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres
```

**Where to find:**
- Supabase Dashboard → Project Settings → Database → Connection String
- Use the "URI" format

### Application Configuration

```env
DEBUG=False
HOST=0.0.0.0
PORT=8000
```

**Production values:**
- `DEBUG=False` - Disables debug mode (required for production)
- `HOST=0.0.0.0` - Listen on all interfaces (nginx will proxy)
- `PORT=8000` - Internal port (nginx forwards to this)

### File Storage Configuration

```env
UPLOAD_DIR=/var/lib/giggles/uploads
MAX_FILE_SIZE=104857600  # 100MB
```

**Production values:**
- `UPLOAD_DIR` - Absolute path to upload directory
- `MAX_FILE_SIZE` - Maximum file size in bytes (100MB default)

### Audio Processing Configuration

```env
YAMNET_MODEL_URL=https://tfhub.dev/google/yamnet/1
AUDIO_SAMPLE_RATE=16000
AUDIO_CHANNELS=1
LAUGHTER_THRESHOLD=0.3
CLIP_DURATION=4.0
```

**Default values are usually fine** - only change if you need different detection sensitivity.

## Production Setup Steps

### 1. Create .env File

```bash
# On the VPS, as the giggles user
cd /var/lib/giggles
cp laughter-detector/env.example .env
chmod 600 .env  # Restrict permissions
```

### 2. Edit .env File

```bash
nano .env
```

Fill in all required variables with production values.

### 3. Verify Configuration

```bash
# Test that settings load correctly
cd /var/lib/giggles/laughter-detector
source /var/lib/giggles/venv/bin/activate
python -c "from src.config.settings import settings; print('Config loaded:', settings.supabase_url)"
```

### 4. Security Checklist

- [ ] `.env` file has `chmod 600` (owner read/write only)
- [ ] `.env` file owned by `giggles` user
- [ ] `.env` file is NOT in git (check `.gitignore`)
- [ ] All keys are strong and unique
- [ ] Service role key is kept secret
- [ ] Encryption key is exactly 64 hex characters

## Environment File Location

**Production:** `/var/lib/giggles/.env`

The systemd service file (`systemd/giggles.service`) references this location via:
```ini
EnvironmentFile=/var/lib/giggles/.env
```

## Troubleshooting

### "Encryption key must be exactly 64 hex characters"
- Generate a new key: `python -c "import secrets; print(secrets.token_hex(32))"`
- Ensure it's exactly 64 characters (no spaces, newlines)

### "Supabase connection failed"
- Check `SUPABASE_URL` is correct (no trailing slash)
- Verify `SUPABASE_KEY` matches your project
- Check network connectivity from VPS

### "Permission denied" errors
- Ensure `.env` file is readable by `giggles` user
- Check file permissions: `ls -la /var/lib/giggles/.env`

## Example Production .env

```env
# Supabase Configuration
SUPABASE_URL=https://abcdefghijklmnop.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Security Configuration
SECRET_KEY=your-generated-secret-key-here-min-32-chars
ENCRYPTION_KEY=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef

# Database Configuration
DATABASE_URL=postgresql://postgres:password@db.abcdefghijklmnop.supabase.co:5432/postgres

# Application Configuration
DEBUG=False
HOST=0.0.0.0
PORT=8000

# File Storage Configuration
UPLOAD_DIR=/var/lib/giggles/uploads
MAX_FILE_SIZE=104857600

# Audio Processing Configuration
YAMNET_MODEL_URL=https://tfhub.dev/google/yamnet/1
AUDIO_SAMPLE_RATE=16000
AUDIO_CHANNELS=1
LAUGHTER_THRESHOLD=0.3
CLIP_DURATION=4.0
```

