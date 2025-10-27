# Recommendation: Remove Orphan Cleanup Code

## Current State
- **Sync deletion** (in `_process_audio_segment`) - ✅ This works and is sufficient
- **Orphan cleanup** (in `cleanup.py` and `scheduler._run_cleanup_tasks`) - ❌ Redundant and incomplete

## Recommendation
Remove:
1. `src/services/cleanup.py` (the entire file)
2. The cleanup loop in `scheduler.py` (`_run_cleanup_tasks`, `_cleanup_loop`)
3. Orphan cleanup scripts

Keep:
1. Sync deletion in `_process_audio_segment` after YAMNet
2. User-initiated deletion (`delete_user_data`)

## Why?
- The **single deletion** after YAMNet is the only mechanism needed
- If it fails, orphan cleanup won't work either (same decryption issue)
- Simpler code, fewer moving parts, easier to debug
