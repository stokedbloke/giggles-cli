# Security Priorities for Giggles Application

**Date:** December 2024  
**Status:** Pre-Production  
**Risk Level:** HIGH 🔴

---

## 🚨 CRITICAL - Fix Before Production (Week 1)

### 1. Fix `get_current_user` Authentication Bypass
**Severity:** CRITICAL  
**File:** `src/auth/supabase_auth.py:261-283`  
**Effort:** 2 hours

**Issue:** The current implementation queries the users table without a WHERE clause, potentially returning the wrong user.

```python
# Current (INSECURE):
result = temp_client.table("users").select("id, email, created_at").limit(1).execute()

# This returns the FIRST user alphabetically, not necessarily the user from the JWT
```

**Fix:**
```python
async def get_current_user(self, token: str) -> Dict[str, Any]:
    try:
        # Decode JWT to extract user_id (without full verification first)
        from jose import jwt
        unverified_payload = jwt.get_unverified_claims(token)
        user_id = unverified_payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Now query with the user_id from JWT
        temp_client = create_client(settings.supabase_url, settings.supabase_key)
        temp_client.postgrest.auth(token)
        
        result = temp_client.table("users").select("*").eq("id", user_id).single().execute()
        
        if not result.data:
            raise HTTPException(status_code=401, detail="User not found")
        
        return {
            "user_id": result.data['id'],
            "email": result.data['email'],
            "created_at": result.data.get('created_at', datetime.utcnow().isoformat())
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(status_code=401, detail="Could not validate credentials")
```

---

### 2. Add Input Validation to All Endpoints
**Severity:** CRITICAL  
**Files:** `src/api/data_routes.py`, `src/api/audio_routes.py`, `src/api/key_routes.py`  
**Effort:** 4 hours

**Issue:** No validation on user inputs, allowing potential SQL injection, DoS, or data corruption.

**Fix Examples:**

```python
# In data_routes.py:
@router.get("/laughter-detections/{date}")
async def get_laughter_detections(
    date: str,
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    # Validate date format
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")
    
    # Rest of function...
```

```python
# In models/audio.py:
from pydantic import Field, validator

class LaughterDetectionUpdate(BaseModel):
    notes: Optional[str] = Field(None, max_length=1000)
    probability: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    @validator('notes')
    def validate_notes(cls, v):
        if v and len(v) > 1000:
            raise ValueError("Notes must be less than 1000 characters")
        return v
```

---

### 3. Add CSRF Protection
**Severity:** CRITICAL  
**File:** `src/main.py`  
**Effort:** 3 hours

**Issue:** No CSRF protection allows cross-site request forgery attacks.

**Fix:**
```python
# Add to requirements.txt:
# fastapi-csrf-protect==0.1.1

# In main.py:
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError

@CsrfProtect.load_config
def get_csrf_config():
    return CsrfConfig(secret_key=settings.secret_key)

@app.exception_handler(CsrfProtectError)
def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )
```

---

### 4. Add Security Headers
**Severity:** CRITICAL  
**File:** `src/main.py`  
**Effort:** 1 hour

**Issue:** Missing security headers allow XSS, clickjacking, and MIME sniffing attacks.

**Fix:**
```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Content Security Policy (adjust for your needs)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'"
    )
    
    # Remove server header (if possible)
    response.headers.pop("Server", None)
    
    return response
```

---

### 5. Fix CORS Configuration
**Severity:** CRITICAL  
**File:** `src/main.py:78`  
**Effort:** 30 minutes

**Issue:** CORS allows all origins in debug mode, which could accidentally expose API to all domains in production.

**Fix:**
```python
# In settings.py, add:
allowed_origins: str = "http://localhost:8000"

# In main.py:
import os

ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:8000').split(',')

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Never allow all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

---

## ⚠️ HIGH - Fix Soon (Week 2)

### 6. Add File Size Validation
**Severity:** HIGH  
**File:** `src/services/yamnet_processor.py`  
**Effort:** 2 hours

**Issue:** No file size limit allows DoS via extremely large audio files.

**Fix:**
```python
import os

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

async def process_audio_file(self, file_path: str, user_id: str):
    file_size = os.path.getsize(file_path)
    
    if file_size > MAX_FILE_SIZE:
        logger.error(f"File too large: {file_size} bytes")
        raise ValueError(f"Audio file exceeds maximum size of {MAX_FILE_SIZE} bytes")
    
    # Rest of processing...
```

---

### 7. Add JWT Secret Validation
**Severity:** HIGH  
**File:** `src/config/settings.py`  
**Effort:** 1 hour

**Issue:** No validation that JWT secret key is strong enough.

**Fix:**
```python
@validator("secret_key")
def validate_secret_key(cls, v):
    if len(v) < 32:
        raise ValueError("Secret key must be at least 32 characters")
    
    # Check entropy (at least 10 unique characters)
    unique_chars = len(set(v))
    if unique_chars < 10:
        raise ValueError("Secret key must have sufficient entropy (at least 10 unique characters)")
    
    return v
```

---

### 8. Sanitize Frontend User Content
**Severity:** HIGH  
**File:** `static/js/app.js`  
**Effort:** 2 hours

**Issue:** User notes displayed without sanitization, allowing XSS.

**Fix:**
```javascript
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return String(unsafe)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// In createDetectionRow:
row.innerHTML = `
    <td>${escapeHtml(time)}</td>
    <td>${escapeHtml(detection.class_name || 'Unknown')}</td>
    <td>${escapeHtml(detection.notes || '')}</td>
`;
```

---

### 9. Add Timeout to External API Calls
**Severity:** HIGH  
**File:** `src/services/limitless_api.py`  
**Effort:** 1 hour

**Issue:** No timeout on Limitless API calls allows resource exhaustion.

**Fix:**
```python
import asyncio
from aiohttp import ClientTimeout

async def get_audio_segments(self, api_key: str, start_time: datetime, end_time: datetime, user_id: str):
    timeout = ClientTimeout(total=30)  # 30 second timeout
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # API call with timeout
            async with session.get(url, headers=headers) as response:
                # Process response
                pass
    except asyncio.TimeoutError:
        logger.error(f"Timeout calling Limitless API")
        raise HTTPException(504, "External API timeout")
```

---

### 10. Implement Application-Level Audit Logging
**Severity:** HIGH  
**Files:** All route handlers  
**Effort:** 4 hours

**Issue:** No logging of security-sensitive actions.

**Fix:**
```python
import logging

audit_logger = logging.getLogger('audit')
audit_logger.setLevel(logging.WARNING)

@router.delete("/laughter-detections/{detection_id}")
async def delete_laughter_detection(
    detection_id: str,
    user: dict,
    request: Request,
    ...
):
    audit_logger.warning(
        f"USER_DELETE: user_id={user['user_id']}, "
        f"detection_id={detection_id}, "
        f"ip={request.client.host}, "
        f"timestamp={datetime.utcnow().isoformat()}"
    )
    
    # Rest of function...
```

---

## 📋 MEDIUM - Nice to Have (Week 3-4)

### 11. Add Resource Limits to YAMNet Processing
**File:** `src/services/yamnet_processor.py`  
**Effort:** 2 hours

**Fix:**
```python
import resource

def set_memory_limit(gb=2):
    """Set memory limit for the process."""
    memory_limit = gb * 1024 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory_limit, -1))
```

---

### 12. Check Python Dependencies for Vulnerabilities
**Effort:** 1 hour

```bash
pip install safety
safety check
```

---

### 13. Verify RLS Policies are Working
**Effort:** 4 hours

- Test with different user tokens
- Verify each user can only see their own data
- Document expected behavior

---

### 14. Add Health Check Endpoint
**File:** `src/api/health_routes.py`  
**Effort:** 30 minutes

```python
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }
```

---

## 🔒 LOW - Future Enhancements

### 15. Implement Key Rotation Mechanism
### 16. Add Rate Limiting (Defense in Depth)
### 17. Add Data Retention Policies
### 18. Encrypt Files at Rest
### 19. Security Testing Automation (OWASP ZAP)
### 20. Third-Party Security Audit

---

## Summary

**Must Fix Before Production (Week 1):**
1. ✅ Fix `get_current_user` (CRITICAL)
2. ✅ Add input validation (CRITICAL)
3. ✅ Add CSRF protection (CRITICAL)
4. ✅ Add security headers (CRITICAL)
5. ✅ Fix CORS configuration (CRITICAL)

**Should Fix Soon (Week 2):**
6. ✅ File size validation (HIGH)
7. ✅ JWT secret validation (HIGH)
8. ✅ Sanitize frontend content (HIGH)
9. ✅ Add API timeouts (HIGH)
10. ✅ Audit logging (HIGH)

**Estimated Total Time:** ~20 hours of development work

**Recommended Approach:**
- Monday-Tuesday: Fix all CRITICAL items
- Wednesday-Thursday: Fix all HIGH items
- Friday: Testing and verification
- Deploy only after all CRITICAL and HIGH items are fixed

