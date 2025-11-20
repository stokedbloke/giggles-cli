# .env File Migration Guide

## Overview

The `.env` file contains sensitive credentials and configuration. It should **NOT** be committed to Git. This guide shows how to securely copy it from old VPS to new VPS.

---

## Step 1: Backup .env from Old VPS

**On OLD VPS:**
```bash
# SSH into old VPS
ssh giggles@OLD_VPS_IP

# Navigate to project directory
cd /var/lib/giggles/laughter-detector/laughter-detector

# Backup .env file
cp .env ~/env_backup.txt

# Verify backup exists
cat ~/env_backup.txt | head -5
# Should show your environment variables (SUPABASE_URL, etc.)

# Exit VPS
exit
```

---

## Step 2: Copy .env to Your MacBook (Temporary)

**From Your MacBook:**
```bash
# Copy .env from old VPS to your MacBook (temporary location)
scp giggles@OLD_VPS_IP:~/env_backup.txt ~/Downloads/giggles_env_backup.txt

# Verify file copied
cat ~/Downloads/giggles_env_backup.txt | head -5
```

**Security Note:** This file contains secrets. Keep it secure and delete after migration.

---

## Step 3: Copy .env to New VPS

**From Your MacBook:**
```bash
# Copy .env to new VPS
scp ~/Downloads/giggles_env_backup.txt giggles@NEW_VPS_IP:~/env_backup.txt

# SSH into new VPS
ssh giggles@NEW_VPS_IP

# Move .env to correct location
mkdir -p /var/lib/giggles
cp ~/env_backup.txt /var/lib/giggles/.env

# Set correct permissions (important for security)
chmod 600 /var/lib/giggles/.env
chown giggles:giggles /var/lib/giggles/.env

# Verify .env is in place
ls -la /var/lib/giggles/.env
# Should show: -rw------- 1 giggles giggles ... /var/lib/giggles/.env

# Test loading .env
python3 -c "from dotenv import load_dotenv; from pathlib import Path; load_dotenv(Path('/var/lib/giggles/.env')); import os; print('SUPABASE_URL:', os.getenv('SUPABASE_URL')[:30] + '...')"

# Clean up backup file
rm ~/env_backup.txt
```

---

## Step 4: Clean Up MacBook Copy

**On Your MacBook:**
```bash
# Delete temporary backup (contains secrets)
rm ~/Downloads/giggles_env_backup.txt

# Verify deleted
ls ~/Downloads/giggles_env_backup.txt
# Should show: No such file or directory
```

---

## Alternative: Manual Copy-Paste

If `scp` doesn't work, you can manually copy-paste:

**On OLD VPS:**
```bash
# Display .env content
cat /var/lib/giggles/laughter-detector/laughter-detector/.env
```

**Copy the output**, then:

**On NEW VPS:**
```bash
# Create .env file
nano /var/lib/giggles/.env

# Paste content, save (Ctrl+X, Y, Enter)

# Set permissions
chmod 600 /var/lib/giggles/.env
chown giggles:giggles /var/lib/giggles/.env
```

---

## Verify .env Contains Required Variables

**On NEW VPS:**
```bash
# Check required variables exist
python3 << EOF
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv(Path('/var/lib/giggles/.env'))

required = [
    'SUPABASE_URL',
    'SUPABASE_KEY',
    'SUPABASE_SERVICE_ROLE_KEY',
    'SECRET_KEY',
    'ENCRYPTION_KEY',
    'DATABASE_URL'
]

missing = [v for v in required if not os.getenv(v)]
if missing:
    print(f"❌ Missing variables: {missing}")
else:
    print("✅ All required variables present")
EOF
```

---

## Security Best Practices

1. **Never commit .env to Git** ✅ (already in .gitignore)
2. **Use secure transfer** (scp, not email)
3. **Set correct permissions** (600 = owner read/write only)
4. **Delete temporary copies** after migration
5. **Verify .env not in Git history** (if accidentally committed, rotate secrets)

---

## Troubleshooting

### Permission Denied
```bash
# Fix permissions
sudo chown giggles:giggles /var/lib/giggles/.env
chmod 600 /var/lib/giggles/.env
```

### File Not Found
```bash
# Check if .env exists
ls -la /var/lib/giggles/.env

# If missing, verify path
pwd
ls -la /var/lib/giggles/
```

### Variables Not Loading
```bash
# Test loading
python3 -c "from dotenv import load_dotenv; from pathlib import Path; load_dotenv(Path('/var/lib/giggles/.env')); import os; print(os.getenv('SUPABASE_URL'))"

# Check file format (should be KEY=value, no spaces around =)
head -3 /var/lib/giggles/.env
```

