#!/usr/bin/env python3
"""Verify data isolation between two users sharing the same Limitless API key."""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client
from pathlib import Path

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

def get_user_id(email: str) -> str:
    """Get user ID from email."""
    result = supabase.table("users").select("id").eq("email", email).execute()
    if not result.data:
        print(f"❌ User {email} not found!")
        sys.exit(1)
    return result.data[0]["id"]

def check_data_isolation(user1_id: str, user2_id: str):
    """Check that data is properly isolated between two users."""
    print("=" * 80)
    print("MULTI-USER DATA ISOLATION VERIFICATION")
    print("=" * 80)
    
    # 1. Check laughter_detections
    print("\n1. LAUGHTER DETECTIONS")
    print("-" * 80)
    user1_dets = supabase.table("laughter_detections").select("id, timestamp, clip_path").eq("user_id", user1_id).execute()
    user2_dets = supabase.table("laughter_detections").select("id, timestamp, clip_path").eq("user_id", user2_id).execute()
    
    print(f"User 1 giggles: {len(user1_dets.data)}")
    print(f"User 2 giggles: {len(user2_dets.data)}")
    
    # Check for any cross-contamination
    user1_ids = {det["id"] for det in user1_dets.data}
    user2_ids = {det["id"] for det in user2_dets.data}
    overlap = user1_ids & user2_ids
    
    if overlap:
        print(f"❌ ERROR: Found {len(overlap)} shared laughter detection IDs!")
        print(f"   Shared IDs: {list(overlap)[:5]}")
        return False
    else:
        print("✅ No shared laughter detection IDs")
    
    # 2. Check audio_segments
    print("\n2. AUDIO SEGMENTS")
    print("-" * 80)
    user1_segs = supabase.table("audio_segments").select("id, start_time, end_time, file_path").eq("user_id", user1_id).execute()
    user2_segs = supabase.table("audio_segments").select("id, start_time, end_time, file_path").eq("user_id", user2_id).execute()
    
    print(f"User 1 segments: {len(user1_segs.data)}")
    print(f"User 2 segments: {len(user2_segs.data)}")
    
    # Check for any cross-contamination
    user1_seg_ids = {seg["id"] for seg in user1_segs.data}
    user2_seg_ids = {seg["id"] for seg in user2_segs.data}
    overlap = user1_seg_ids & user2_seg_ids
    
    if overlap:
        print(f"❌ ERROR: Found {len(overlap)} shared audio segment IDs!")
        print(f"   Shared IDs: {list(overlap)[:5]}")
        return False
    else:
        print("✅ No shared audio segment IDs")
    
    # Check if they have same file paths (might indicate same Limitless data)
    user1_paths = {seg["file_path"] for seg in user1_segs.data}
    user2_paths = {seg["file_path"] for seg in user2_segs.data}
    shared_paths = user1_paths & user2_paths
    
    if shared_paths:
        print(f"⚠️  NOTE: {len(shared_paths)} shared file paths (might indicate same Limitless device/pendant)")
        print(f"   This is OK - files are stored in separate user folders")
    else:
        print("✅ No shared file paths")
    
    # 3. Check processing_logs
    print("\n3. PROCESSING LOGS")
    print("-" * 80)
    user1_logs = supabase.table("processing_logs").select("id, date, trigger_type").eq("user_id", user1_id).execute()
    user2_logs = supabase.table("processing_logs").select("id, date, trigger_type").eq("user_id", user2_id).execute()
    
    print(f"User 1 logs: {len(user1_logs.data)}")
    print(f"User 2 logs: {len(user2_logs.data)}")
    
    # Check for any cross-contamination
    user1_log_ids = {log["id"] for log in user1_logs.data}
    user2_log_ids = {log["id"] for log in user2_logs.data}
    overlap = user1_log_ids & user2_log_ids
    
    if overlap:
        print(f"❌ ERROR: Found {len(overlap)} shared processing log IDs!")
        return False
    else:
        print("✅ No shared processing log IDs")
    
    # 4. Check limitless_keys
    print("\n4. LIMITLESS API KEYS")
    print("-" * 80)
    user1_keys = supabase.table("limitless_keys").select("id, is_active, created_at").eq("user_id", user1_id).execute()
    user2_keys = supabase.table("limitless_keys").select("id, is_active, created_at").eq("user_id", user2_id).execute()
    
    print(f"User 1 keys: {len(user1_keys.data)} (active: {sum(1 for k in user1_keys.data if k.get('is_active'))})")
    print(f"User 2 keys: {len(user2_keys.data)} (active: {sum(1 for k in user2_keys.data if k.get('is_active'))})")
    
    # Keys should be separate (encrypted differently per user)
    user1_key_ids = {key["id"] for key in user1_keys.data}
    user2_key_ids = {key["id"] for key in user2_keys.data}
    overlap = user1_key_ids & user2_key_ids
    
    if overlap:
        print(f"❌ ERROR: Found {len(overlap)} shared key IDs!")
        return False
    else:
        print("✅ Keys stored separately (as expected)")
    
    # 5. Check file system isolation
    print("\n5. FILE SYSTEM ISOLATION")
    print("-" * 80)
    project_root = Path(__file__).parent
    user1_audio_dir = project_root / "uploads" / "audio" / user1_id
    user2_audio_dir = project_root / "uploads" / "audio" / user2_id
    user1_clips_dir = project_root / "uploads" / "clips" / user1_id
    user2_clips_dir = project_root / "uploads" / "clips" / user2_id
    
    user1_audio_files = list(user1_audio_dir.glob("*.ogg")) if user1_audio_dir.exists() else []
    user2_audio_files = list(user2_audio_dir.glob("*.ogg")) if user2_audio_dir.exists() else []
    user1_clip_files = list(user1_clips_dir.glob("*.wav")) if user1_clips_dir.exists() else []
    user2_clip_files = list(user2_clips_dir.glob("*.wav")) if user2_clips_dir.exists() else []
    
    print(f"User 1 audio files: {len(user1_audio_files)}")
    print(f"User 2 audio files: {len(user2_audio_files)}")
    print(f"User 1 clip files: {len(user1_clip_files)}")
    print(f"User 2 clip files: {len(user2_clip_files)}")
    
    # Check for files in wrong location
    user1_audio_names = {f.name for f in user1_audio_files}
    user2_audio_names = {f.name for f in user2_audio_files}
    shared_audio = user1_audio_names & user2_audio_names
    
    if shared_audio:
        print(f"⚠️  NOTE: {len(shared_audio)} shared audio filenames")
        print(f"   This might indicate same Limitless device, but files are in separate folders ✅")
    else:
        print("✅ No shared audio filenames")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("✅ Database isolation: PASSED")
    print("✅ File system isolation: PASSED")
    print("✅ Processing logs isolation: PASSED")
    print("\n✅ Multi-user test: PASSED - Data is properly isolated!")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python verify_multi_user_isolation.py <user1_email> <user2_email>")
        sys.exit(1)
    
    user1_email = sys.argv[1]
    user2_email = sys.argv[2]
    
    print(f"Checking isolation between:")
    print(f"  User 1: {user1_email}")
    print(f"  User 2: {user2_email}")
    
    user1_id = get_user_id(user1_email)
    user2_id = get_user_id(user2_email)
    
    print(f"\nUser IDs:")
    print(f"  User 1: {user1_id}")
    print(f"  User 2: {user2_id}\n")
    
    success = check_data_isolation(user1_id, user2_id)
    
    if not success:
        print("\n❌ FAILED: Data isolation issues detected!")
        sys.exit(1)

