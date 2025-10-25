name: "Laughter Detector and Counter - Secure Audio Processing System"
description: |
  A secure web application that processes audio from Limitless AI pendant to detect and count laughter using YAMNet, with encrypted storage and mobile-responsive UI.

## Purpose
Template optimized for AI agents to implement a secure laughter detection system with proper authentication, audio processing, and data privacy controls.

## Core Principles
1. **Security First**: All user data and API keys must be encrypted in transit and at rest
2. **Privacy by Design**: Audio data is processed and deleted immediately after analysis
3. **Mobile-First**: Dead simple responsive design for maximum compatibility
4. **Minimal State**: Avoid complex state management, keep UI simple
5. **Progressive Enhancement**: Start with core functionality, add features incrementally

---

## Goal
Build a secure web application that:
- Authenticates users via Supabase (email/password + MFA)
- Securely stores and manages Limitless API keys (encrypted)
- Processes daily audio segments from Limitless API using YAMNet
- Detects laughter with timestamps and probability scores
- Provides mobile-responsive UI showing daily laugh counts
- Allows users to play audio clips and manage their data
- Implements secure data deletion and cleanup

## Why
- **User Value**: Track daily laughter patterns for wellness/mental health insights
- **Privacy**: Users control their own audio data with secure deletion options
- **Security**: Encrypted storage and transmission of sensitive API keys and audio
- **Simplicity**: Easy-to-use interface for non-technical users

## What

### Success Criteria
- [ ] Secure user authentication with Supabase (email/password + MFA)
- [ ] Encrypted storage of Limitless API keys
- [ ] Nightly audio processing with YAMNet laughter detection
- [ ] Mobile-responsive UI showing daily laugh counts
- [ ] Audio clip playback with timestamp and probability display
- [ ] Secure data deletion (individual clips and full account data)
- [ ] Automated cleanup of orphaned audio files
- [ ] Error handling for API failures and missing data

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://www.limitless.ai/developers
  why: Official Limitless API documentation for audio retrieval
  
- url: https://www.tensorflow.org/hub/tutorials/yamnet
  why: YAMNet model documentation and usage examples
  
- url: https://supabase.com/docs
  why: Authentication, database, and security implementation
  
- url: https://fastapi.tiangolo.com/
  why: Python web framework for secure API development
  
- url: https://docs.pydantic.dev/
  why: Data validation and serialization for security
  
- url: https://docs.sqlalchemy.org/
  why: Database ORM for secure data management
```

### Current Codebase tree
```bash
/Users/neilsethi/git/context-engineering-intro/
├── CLAUDE.md                    # Project guardrails
├── INITIAL.md                   # Feature specification
├── PRPs/
│   ├── templates/
│   │   └── prp_base.md         # PRP template
│   └── laughter-detector.md    # This PRP
├── use-cases/                   # Example implementations
│   ├── agent-factory-with-subagents/
│   ├── mcp-server/
│   └── pydantic-ai/
└── examples/                    # Sample files (empty)
```

### Desired Codebase tree with files to be added
```bash
laughter-detector/
├── src/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entry point
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # Environment configuration
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── supabase_auth.py     # Supabase authentication
│   │   └── encryption.py        # API key encryption/decryption
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py             # User data models
│   │   ├── audio.py            # Audio processing models
│   │   └── laughter.py         # Laughter detection models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── limitless_api.py    # Limitless API integration
│   │   ├── yamnet_processor.py # YAMNet audio processing
│   │   └── cleanup.py          # Audio cleanup service
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py           # API endpoints
│   │   └── dependencies.py     # FastAPI dependencies
│   └── utils/
│       ├── __init__.py
│       ├── audio_utils.py      # Audio format conversion
│       └── security.py         # Security utilities
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_audio_processing.py
│   └── test_api.py
├── static/
│   ├── css/
│   │   └── style.css           # Mobile-responsive CSS
│   └── js/
│       └── app.js              # Frontend JavaScript
├── templates/
│   └── index.html              # Main UI template
├── requirements.txt
├── .env.example
├── README.md
└── docker-compose.yml          # Local development setup
```

### Known Gotchas & Security Requirements
```python
# CRITICAL: Limitless API has rate limits (60-120 minutes max per request)
# CRITICAL: Audio files must be deleted immediately after processing
# CRITICAL: API keys must be encrypted with AES-256-GCM
# CRITICAL: Supabase RLS policies must be configured for user data isolation
# CRITICAL: YAMNet requires specific audio format (16kHz, mono, WAV)
# CRITICAL: Mobile UI must work without JavaScript for maximum compatibility
# CRITICAL: All database queries must use parameterized statements
# CRITICAL: File uploads must be validated and sanitized
```

## Implementation Blueprint

### Data models and structure

Create secure data models with proper validation and encryption:

```python
# src/models/user.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    mfa_enabled: bool = False

class UserCreate(UserBase):
    password: str  # Will be hashed by Supabase

class UserResponse(UserBase):
    id: str
    created_at: datetime
    
class LimitlessKeyCreate(BaseModel):
    api_key: str  # Will be encrypted before storage

class LimitlessKeyResponse(BaseModel):
    id: str
    created_at: datetime
    # Never return the actual key

# src/models/audio.py
class AudioSegment(BaseModel):
    id: str
    user_id: str
    date: datetime
    start_time: datetime
    end_time: datetime
    file_path: str
    processed: bool = False

class LaughterDetection(BaseModel):
    id: str
    audio_segment_id: str
    timestamp: datetime
    probability: float
    clip_path: str
    notes: Optional[str] = None
```

### Implementation Tasks

```yaml
Task 1: Project Setup
CREATE laughter-detector/:
  - SETUP: Python virtual environment with FastAPI, Supabase, TensorFlow
  - CONFIGURE: Environment variables for secrets
  - INITIALIZE: Git repository with .gitignore for sensitive files

Task 2: Authentication System
CREATE src/auth/supabase_auth.py:
  - IMPLEMENT: Supabase client initialization
  - IMPLEMENT: User registration with email/password
  - IMPLEMENT: User login with session management
  - IMPLEMENT: MFA setup and verification
  - SECURITY: Password hashing and validation

CREATE src/auth/encryption.py:
  - IMPLEMENT: AES-256-GCM encryption for API keys
  - IMPLEMENT: Secure key derivation from user password
  - IMPLEMENT: Key rotation and secure deletion

Task 3: Database Models and Security
CREATE src/models/:
  - IMPLEMENT: Pydantic models for data validation
  - IMPLEMENT: SQLAlchemy models for database
  - IMPLEMENT: Supabase RLS policies for user data isolation
  - SECURITY: Input validation and sanitization

Task 4: Limitless API Integration
CREATE src/services/limitless_api.py:
  - IMPLEMENT: Secure API key storage and retrieval
  - IMPLEMENT: Audio segment download with rate limiting
  - IMPLEMENT: Date range processing (previous day + current day)
  - IMPLEMENT: Incremental processing (only new audio)
  - SECURITY: Encrypted API key transmission

Task 5: YAMNet Audio Processing
CREATE src/services/yamnet_processor.py:
  - IMPLEMENT: Audio format conversion (Limitless → YAMNet format)
  - IMPLEMENT: YAMNet model loading and inference
  - IMPLEMENT: Laughter detection with timestamps and probabilities
  - IMPLEMENT: Audio clip extraction (2 seconds before/after)
  - OPTIMIZATION: Minimize file conversions

Task 6: Cleanup and Security
CREATE src/services/cleanup.py:
  - IMPLEMENT: Secure deletion of original audio files
  - IMPLEMENT: Orphaned file detection and removal
  - IMPLEMENT: Scheduled cleanup tasks
  - SECURITY: Cryptographic file deletion

Task 7: API Endpoints
CREATE src/api/routes.py:
  - IMPLEMENT: User authentication endpoints
  - IMPLEMENT: Limitless key management endpoints
  - IMPLEMENT: Daily laugh count retrieval
  - IMPLEMENT: Audio clip playback endpoints
  - IMPLEMENT: Data deletion endpoints
  - SECURITY: Rate limiting and input validation

Task 8: Mobile-Responsive UI
CREATE templates/index.html:
  - IMPLEMENT: Dead simple mobile-first design
  - IMPLEMENT: Daily laugh count cards
  - IMPLEMENT: Audio clip playback interface
  - IMPLEMENT: Data management controls
  - COMPATIBILITY: Works without JavaScript

CREATE static/css/style.css:
  - IMPLEMENT: Mobile-responsive CSS Grid/Flexbox
  - IMPLEMENT: Bright, accessible color scheme
  - IMPLEMENT: Touch-friendly interface elements

Task 9: Background Processing
CREATE src/services/scheduler.py:
  - IMPLEMENT: Nightly audio processing job
  - IMPLEMENT: Timezone-aware scheduling
  - IMPLEMENT: Error handling and retry logic
  - IMPLEMENT: Processing status tracking

Task 10: Testing and Security
CREATE tests/:
  - IMPLEMENT: Unit tests for all services
  - IMPLEMENT: Integration tests for API endpoints
  - IMPLEMENT: Security tests for encryption/decryption
  - IMPLEMENT: Audio processing accuracy tests
```

### Per task pseudocode

```python
# Task 2: Authentication
async def register_user(email: str, password: str) -> UserResponse:
    # SECURITY: Validate email format and password strength
    validated_email = validate_email(email)
    validated_password = validate_password_strength(password)
    
    # SECURITY: Use Supabase for secure user creation
    user = await supabase.auth.sign_up({
        "email": validated_email,
        "password": validated_password
    })
    
    # SECURITY: Enable MFA by default
    await enable_mfa(user.id)
    
    return UserResponse.from_supabase_user(user)

# Task 4: Limitless API Integration
async def process_daily_audio(user_id: str, date: datetime) -> List[AudioSegment]:
    # SECURITY: Retrieve encrypted API key
    encrypted_key = await get_user_limitless_key(user_id)
    api_key = decrypt_key(encrypted_key, user_id)
    
    # RATE LIMIT: Check API limits (60-120 minutes max)
    if await check_rate_limit(api_key):
        raise RateLimitError("API rate limit exceeded")
    
    # PROCESSING: Get audio segments for date range
    segments = await limitless_api.get_audio_segments(
        api_key=api_key,
        start_date=date,
        end_date=date + timedelta(days=1)
    )
    
    # SECURITY: Store segments with encrypted file paths
    for segment in segments:
        encrypted_path = encrypt_file_path(segment.file_path)
        await store_audio_segment(user_id, segment, encrypted_path)
    
    return segments

# Task 5: YAMNet Processing
async def detect_laughter(audio_segment: AudioSegment) -> List[LaughterDetection]:
    # FORMAT: Convert to YAMNet required format (16kHz, mono, WAV)
    converted_audio = await convert_audio_format(
        audio_segment.file_path,
        target_format="wav",
        sample_rate=16000,
        channels=1
    )
    
    # INFERENCE: Run YAMNet model
    predictions = yamnet_model.predict(converted_audio)
    
    # FILTER: Extract laughter predictions (class_id for laughter)
    laughter_events = []
    for timestamp, probability, class_id in predictions:
        if class_id == LAUGHTER_CLASS_ID and probability > LAUGHTER_THRESHOLD:
            # EXTRACT: Create 2-second clip around detection
            clip_path = await extract_audio_clip(
                converted_audio,
                timestamp - 2.0,
                timestamp + 2.0
            )
            
            laughter_events.append(LaughterDetection(
                timestamp=timestamp,
                probability=probability,
                clip_path=clip_path
            ))
    
    return laughter_events

# Task 7: Secure Data Deletion
async def delete_user_data(user_id: str) -> bool:
    # SECURITY: Delete all user audio files
    audio_files = await get_user_audio_files(user_id)
    for file_path in audio_files:
        await secure_delete_file(file_path)  # Cryptographic deletion
    
    # SECURITY: Delete database records
    await delete_user_laughter_detections(user_id)
    await delete_user_audio_segments(user_id)
    
    # SECURITY: Delete encrypted API key
    await delete_user_limitless_key(user_id)
    
    return True
```

### Integration Points
```yaml
DATABASE:
  - provider: "Supabase PostgreSQL"
  - tables: "users, limitless_keys, audio_segments, laughter_detections"
  - security: "Row Level Security (RLS) policies for user data isolation"
  - encryption: "API keys encrypted with AES-256-GCM"
  
AUTHENTICATION:
  - provider: "Supabase Auth"
  - methods: "Email/password + MFA"
  - security: "JWT tokens with secure session management"
  
STORAGE:
  - audio_files: "Encrypted local storage with secure deletion"
  - cleanup: "Scheduled cleanup of orphaned files"
  
API_SECURITY:
  - rate_limiting: "Per-user rate limits for API endpoints"
  - validation: "Pydantic models for all input validation"
  - encryption: "All sensitive data encrypted in transit and at rest"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
cd laughter-detector
python -m ruff check src/ --fix  # Auto-fix what's possible
python -m mypy src/            # Type checking
python -m black src/           # Code formatting

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests
```python
# CREATE comprehensive test suite
def test_user_registration():
    """User can register with valid email/password"""
    response = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "SecurePass123!"
    })
    assert response.status_code == 201
    assert "user_id" in response.json()

def test_api_key_encryption():
    """API keys are properly encrypted"""
    key = "test_api_key_123"
    encrypted = encrypt_api_key(key, "user_id")
    decrypted = decrypt_api_key(encrypted, "user_id")
    assert decrypted == key
    assert encrypted != key

def test_audio_processing():
    """YAMNet correctly detects laughter in test audio"""
    test_audio = load_test_audio("sample_laughter.wav")
    detections = process_audio_with_yamnet(test_audio)
    assert len(detections) > 0
    assert all(d.probability > 0.5 for d in detections)

def test_secure_deletion():
    """Files are securely deleted"""
    test_file = create_test_file("test_audio.wav")
    secure_delete_file(test_file)
    assert not os.path.exists(test_file)
```

```bash
# Run and iterate until passing:
cd laughter-detector
python -m pytest tests/ -v
# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test
```bash
# Start the service
cd laughter-detector
python -m uvicorn src.main:app --reload

# Test authentication
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "SecurePass123!"}'

# Test API key storage
curl -X POST http://localhost:8000/api/limitless-key \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"api_key": "test_key_123"}'

# Expected: {"status": "success", "message": "API key stored securely"}
# If error: Check logs for stack trace
```

## Final validation Checklist
- [ ] All tests pass: `python -m pytest tests/ -v`
- [ ] No linting errors: `python -m ruff check src/`
- [ ] No type errors: `python -m mypy src/`
- [ ] Security scan passes: `bandit -r src/`
- [ ] Manual test successful: User can register, add API key, view daily counts
- [ ] Audio processing works: YAMNet detects laughter in test files
- [ ] Mobile UI responsive: Test on mobile device or browser dev tools
- [ ] Secure deletion works: Files are cryptographically deleted
- [ ] Error cases handled gracefully: API failures, invalid keys, missing data
- [ ] Documentation updated: README.md with setup and security notes

---

## Anti-Patterns to Avoid
- ❌ Don't store API keys in plain text
- ❌ Don't leave audio files on disk after processing
- ❌ Don't use synchronous functions in async context
- ❌ Don't skip input validation on API endpoints
- ❌ Don't hardcode secrets in configuration
- ❌ Don't ignore rate limits on external APIs
- ❌ Don't create complex state management in frontend
- ❌ Don't skip mobile responsiveness testing
- ❌ Don't forget to implement secure deletion
- ❌ Don't skip MFA implementation for security
