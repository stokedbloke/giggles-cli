# Multi-User Testing Guide

## Overview
Testing multiple users with the same Limitless API key to verify data isolation and multi-user functionality.

## ✅ What Should Work (Based on Code Analysis)

### 1. **Data Isolation**
- ✅ Files stored per-user: `uploads/audio/{user_id}/` and `uploads/clips/{user_id}/`
- ✅ Database queries filter by `user_id` in all tables
- ✅ Row Level Security (RLS) policies enforce user isolation
- ✅ No file path collisions (different user_id folders)

### 2. **API Key Storage**
- ✅ Keys stored separately per user in `limitless_keys` table
- ✅ Keys encrypted with user-specific associated data
- ✅ No database constraint preventing same API key for multiple users

### 3. **Processing Isolation**
- ✅ Each user's processing runs independently
- ✅ Processing logs stored per user_id
- ✅ Audio segments and laughter detections isolated by user_id

## ⚠️ Potential Issues to Watch For

### 1. **Limitless API Behavior**
**Question**: Does Limitless API return user-specific data or device-specific data?

- If **device-specific**: Sharing a key might return the same audio for both users (if they're using the same device/pendant)
- If **user-specific**: Each user should get their own audio data
- **Test**: Check if both users see the same or different audio segments after processing

### 2. **Concurrent Processing**
**Scenario**: Both users trigger processing at the same time

- ✅ Should be safe - each user processes independently
- ⚠️ Watch for: Resource contention (CPU, memory) if processing large files simultaneously
- ⚠️ Watch for: Database connection limits if many users process concurrently

### 3. **Database Constraints**
**Check**: Verify no unique constraints that would prevent this

- ✅ `limitless_keys` table: No unique constraint on encrypted_api_key
- ✅ All tables use `user_id` for isolation
- ✅ Unique constraints are per-user (e.g., `unique_laughter_timestamp_user` includes user_id)

### 4. **File Storage Verification**
**Verify**: Files are truly isolated

- ✅ OGG files: `uploads/audio/{user_id}/filename.ogg`
- ✅ WAV clips: `uploads/clips/{user_id}/filename.wav`
- ✅ No shared directories that could cause collisions

## 🧪 Testing Checklist

### Pre-Test Setup
- [ ] Create second user account (different email)
- [ ] Log in as second user
- [ ] Add same Limitless API key to second user
- [ ] Verify key is stored (check `/api/limitless-key/status`)

### Test 1: Data Isolation
- [ ] Process audio for User 1
- [ ] Process audio for User 2 (same date/time range)
- [ ] Verify User 1 only sees their own giggles
- [ ] Verify User 2 only sees their own giggles
- [ ] Check database: Query `laughter_detections` for both users - should be separate

### Test 2: File Storage
- [ ] Check `uploads/audio/{user1_id}/` - should only have User 1's files
- [ ] Check `uploads/audio/{user2_id}/` - should only have User 2's files
- [ ] Check `uploads/clips/{user1_id}/` - should only have User 1's clips
- [ ] Check `uploads/clips/{user2_id}/` - should only have User 2's clips
- [ ] Verify no files in wrong user folder

### Test 3: Limitless API Data
- [ ] Compare audio segments between users
- [ ] **If same audio**: Limitless API returns device-specific data (expected if same pendant)
- [ ] **If different audio**: Limitless API returns user-specific data
- [ ] Document findings for future reference

### Test 4: Concurrent Processing
- [ ] Trigger processing for both users simultaneously
- [ ] Monitor logs for errors
- [ ] Verify both complete successfully
- [ ] Check processing_logs table - should have separate entries per user

### Test 5: Database Queries
- [ ] Query `audio_segments` filtered by user_id - should only return that user's data
- [ ] Query `laughter_detections` filtered by user_id - should only return that user's data
- [ ] Query `processing_logs` filtered by user_id - should only return that user's logs
- [ ] Verify RLS policies prevent cross-user access

### Test 6: Nightly Cron Job
- [ ] Wait for nightly cron to run
- [ ] Verify both users' data processed separately
- [ ] Check `nightly_processing.log` for both users
- [ ] Verify processing_logs created for both users

## 🔍 Verification Scripts

### Quick Database Check
```python
# Check both users' data isolation
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

user1_id = "user1_id_here"
user2_id = "user2_id_here"

# Check laughter detections
user1_dets = supabase.table("laughter_detections").select("id").eq("user_id", user1_id).execute()
user2_dets = supabase.table("laughter_detections").select("id").eq("user_id", user2_id).execute()

print(f"User 1 giggles: {len(user1_dets.data)}")
print(f"User 2 giggles: {len(user2_dets.data)}")

# Check audio segments
user1_segs = supabase.table("audio_segments").select("id").eq("user_id", user1_id).execute()
user2_segs = supabase.table("audio_segments").select("id").eq("user_id", user2_id).execute()

print(f"User 1 segments: {len(user1_segs.data)}")
print(f"User 2 segments: {len(user2_segs.data)}")
```

### File System Check
```bash
# Check file isolation
ls -la uploads/audio/
ls -la uploads/clips/

# Should see separate folders for each user_id
```

## 📝 Expected Behaviors

### ✅ Should Work
1. Both users can store the same API key
2. Both users process independently
3. Data is completely isolated (database + files)
4. Each user only sees their own data in UI
5. Processing logs are separate per user

### ⚠️ May Vary
1. **Limitless API data**: If same device/pendant, both users might get same audio segments
   - This is a Limitless API behavior, not a system bug
   - Each user's processing of that audio is still isolated
2. **Processing times**: Concurrent processing might be slower due to resource sharing

### ❌ Should NOT Happen
1. User 1 seeing User 2's giggles (or vice versa)
2. Files in wrong user folder
3. Database records with wrong user_id
4. Processing errors due to user conflicts

## 🐛 If Issues Found

### Issue: Users see each other's data
- **Check**: RLS policies in database
- **Check**: `user_id` filtering in API queries
- **Check**: Authentication token handling

### Issue: File collisions
- **Check**: File paths include user_id
- **Check**: Directory structure is per-user

### Issue: Processing conflicts
- **Check**: Resource limits (CPU, memory, database connections)
- **Check**: Concurrent processing logic

## 📊 Success Criteria

✅ **Test passes if:**
- Both users can use same API key
- Data is completely isolated (database + files)
- No cross-user data leakage
- Both users can process independently
- No file collisions or conflicts
- Processing logs are separate

## 🔐 Security Notes

- RLS policies should prevent users from accessing each other's data even if they try
- API keys are encrypted per-user (different associated data)
- File system isolation provides additional security layer

