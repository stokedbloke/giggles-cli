# Plan: Remove File Path Encryption

## Current Issues
1. File paths are encrypted in database (unnecessary complexity)
2. Decryption fails sometimes → orphaned files
3. Two deletion mechanisms (sync + orphan cleanup)

## Proposed Changes

### 1. Remove Encryption from File Paths
- Change `file_path` and `clip_path` columns to store plaintext paths
- Remove encryption/decryption calls in:
  - `limitless_api.py` (line 88-91)
  - `yamnet_processor.py` (line 347)
  - `scheduler.py` (line 592-600)
  - `data_routes.py` (decryption in endpoints)

### 2. Simplify Deletion
- Remove `cleanup.py` entire file
- Remove cleanup loop from `scheduler.py`
- Keep only sync deletion in `_process_audio_segment`

### 3. Security is Still Strong
- ✅ Limitless API key: encrypted in DB
- ✅ Audio files: deleted after YAMNet processing
- ✅ Access control: RLS policies in Supabase
- ✅ User data isolation: users can only see their own data

## Files to Modify
1. `src/services/limitless_api.py` - remove path encryption
2. `src/services/yamnet_processor.py` - remove path encryption  
3. `src/services/scheduler.py` - remove path decryption, simplify deletion
4. `src/api/data_routes.py` - remove path decryption
5. `src/services/cleanup.py` - DELETE entire file
6. Database migration to remove encryption from existing paths

## Benefits
- Simpler code, easier to debug
- No more decryption failures
- Files deleted reliably after processing
- Security still maintained
