# DNS and Database Changes for VPS Migration

## Quick Answer

**Database:** ✅ **NO CHANGES NEEDED** - Same Supabase database  
**DNS/GoDaddy:** ⚠️ **ONLY IF CHANGING DOMAIN/IP** - Otherwise no changes

---

## Database Changes

### ✅ **NO CHANGES REQUIRED**

**Why:**
- Both VPS instances use the **same Supabase database**
- Database connection is configured via `.env` file (`SUPABASE_URL`, `DATABASE_URL`)
- New VPS will use same credentials → connects to same database
- No migration needed

**What to Verify:**
```bash
# On NEW VPS, test database connection
python3 -c "
from src.services.supabase_client import get_service_role_client
client = get_service_role_client()
print('✅ Database connection successful')
"
```

**Action:** ✅ None - Just copy `.env` file (see `ENV_FILE_MIGRATION.md`)

---

## DNS/GoDaddy Changes

### ⚠️ **ONLY IF CHANGING IP ADDRESS OR DOMAIN**

**Scenario 1: Same IP Address (IP Transfer)**
- **Action:** ✅ **NO DNS CHANGES NEEDED**
- **Why:** DNS already points to correct IP
- **Note:** This is rare - usually VPS migration involves new IP

**Scenario 2: New IP Address (New VPS)**
- **Action:** ⚠️ **UPDATE DNS RECORDS**
- **Steps:**
  1. Get new VPS IP address
  2. Log into GoDaddy DNS management
  3. Update A record to point to new IP
  4. Wait for DNS propagation (5 minutes - 48 hours, usually < 1 hour)

**Scenario 3: New Domain**
- **Action:** ⚠️ **UPDATE DNS RECORDS + SSL CERTIFICATE**
- **Steps:**
  1. Update DNS A record
  2. Update SSL certificate (Let's Encrypt)
  3. Update nginx configuration
  4. Update CORS settings in `.env` (if applicable)

---

## DNS Update Steps (If Needed)

### Step 1: Get New VPS IP Address

**On NEW VPS:**
```bash
# Get public IP
curl ifconfig.me
# Or
hostname -I
```

### Step 2: Update GoDaddy DNS

1. **Log into GoDaddy:**
   - Go to https://dcc.godaddy.com/
   - Navigate to DNS Management

2. **Find Your Domain:**
   - Select your domain (e.g., `giggles.com`)

3. **Update A Record:**
   - Find A record (usually `@` or domain name)
   - Change IP address to new VPS IP
   - Save changes

4. **Update Subdomain (if applicable):**
   - If using `api.giggles.com`, update that A record too
   - Save changes

### Step 3: Verify DNS Propagation

**From Your MacBook:**
```bash
# Check DNS propagation
dig YOUR_DOMAIN.com +short
# Should show new IP address

# Or use nslookup
nslookup YOUR_DOMAIN.com
# Should show new IP address
```

**Wait Time:**
- Usually: 5 minutes - 1 hour
- Maximum: 48 hours (rare)
- Check every 15 minutes until updated

### Step 4: Update SSL Certificate (If Domain Changed)

**On NEW VPS:**
```bash
# If using Let's Encrypt
sudo certbot --nginx -d YOUR_DOMAIN.com

# Verify SSL
curl -I https://YOUR_DOMAIN.com
# Should show: HTTP/2 200
```

---

## What If You're NOT Changing Domain/IP?

### ✅ **NO DNS CHANGES NEEDED**

**If:**
- Using same domain
- Same IP address (unlikely with new VPS)
- Or testing on new VPS before switching DNS

**Action:** ✅ None - Just copy `.env` and deploy code

---

## Checklist

### Database
- [ ] Copy `.env` file (contains database credentials)
- [ ] Test database connection on new VPS
- [ ] Verify same Supabase project URL
- [ ] ✅ **NO DATABASE MIGRATION NEEDED**

### DNS (Only if changing IP/domain)
- [ ] Get new VPS IP address
- [ ] Update GoDaddy A record
- [ ] Wait for DNS propagation
- [ ] Verify DNS updated (`dig` or `nslookup`)
- [ ] Update SSL certificate (if domain changed)

### Testing Before DNS Switch
- [ ] Test new VPS with direct IP access
- [ ] Verify cron job works
- [ ] Verify API endpoints work
- [ ] Then switch DNS

---

## Recommended Migration Strategy

### Phase 1: Deploy to New VPS (No DNS Change)
1. Deploy code to new VPS
2. Copy `.env` file
3. Test with direct IP: `http://NEW_VPS_IP:8000`
4. Verify cron job works
5. Monitor for 24-48 hours

### Phase 2: Switch DNS (After Verification)
1. Update GoDaddy DNS to new IP
2. Wait for propagation
3. Verify domain works: `https://YOUR_DOMAIN.com`
4. Monitor for issues
5. Keep old VPS running for 1 week (rollback)

### Phase 3: Decommission Old VPS (After 1 Week)
1. Verify no issues on new VPS
2. Stop services on old VPS
3. Delete old VPS (after 1 week of success)

---

## Summary

**Database:** ✅ **NO CHANGES** - Same Supabase, just copy `.env`  
**DNS:** ⚠️ **ONLY IF NEW IP** - Update GoDaddy A record  
**SSL:** ⚠️ **ONLY IF DOMAIN CHANGED** - Update Let's Encrypt certificate

**Most Common Scenario:**
- New VPS = New IP → Update DNS A record
- Same database → Just copy `.env`
- Same domain → Update SSL after DNS

