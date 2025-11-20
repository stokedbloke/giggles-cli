#!/usr/bin/env python3
"""
Test Memory Cleanup with Real Audio Processing

This test processes real audio segments to verify memory cleanup
works correctly during actual YAMNet inference.
"""

import sys
import os
import asyncio
import psutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment
env_paths = [
    Path(__file__).parent.parent.parent / ".env",
    Path.home() / ".env",
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break


def get_memory_mb():
    """Get current memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


async def test_real_processing():
    """
    Test memory cleanup with real audio processing.
    
    This will process actual audio segments and verify memory
    cleanup works during YAMNet inference.
    """
    print("=" * 60)
    print("Real Audio Processing Memory Test")
    print("=" * 60)
    
    from process_nightly_audio import NightlyAudioProcessor
    from src.services.supabase_client import get_service_role_client
    
    print("\nLoading TensorFlow model (this takes ~400-500MB)...")
    supabase = get_service_role_client()
    
    # Allow specific user IDs from command line
    if len(sys.argv) > 1:
        user_ids = sys.argv[1:]
        print(f"\nUsing specified user IDs: {user_ids}")
        # Verify users exist and have active keys
        result = supabase.table("limitless_keys").select("user_id, users!inner(email)").eq("is_active", True).in_("user_id", user_ids).execute()
        if not result.data:
            print("❌ None of the specified users have active keys")
            return False
        user_ids = [row["user_id"] for row in result.data]
    else:
        # Get users with active keys
        result = supabase.table("limitless_keys").select("user_id, users!inner(email)").eq("is_active", True).limit(2).execute()
        
        if not result.data:
            print("❌ No active users found")
            return False
        
        user_ids = [row["user_id"] for row in result.data]
    
    print(f"\nTesting with {len(user_ids)} user(s):")
    for user_id in user_ids:
        user_result = supabase.table("users").select("email").eq("id", user_id).execute()
        email = user_result.data[0]["email"] if user_result.data else "unknown"
        print(f"  - {email} ({user_id[:8]}...)")
    
    # Initialize processor
    processor = NightlyAudioProcessor(include_user_ids=user_ids)
    
    # Measure baseline AFTER TensorFlow loads
    baseline = get_memory_mb()
    print(f"\nBaseline memory (after TensorFlow load): {baseline:.1f} MB")
    print(f"\n{'='*60}")
    print("Starting processing...")
    print(f"{'='*60}\n")
    
    memory_samples = []
    max_memory = baseline
    
    # Process each user
    for user_idx, user_id in enumerate(user_ids, 1):
        print(f"\n{'='*60}")
        print(f"User {user_idx}/{len(user_ids)}")
        print(f"{'='*60}")
        
        memory_before = get_memory_mb()
        print(f"Memory before user {user_idx}: {memory_before:.1f} MB")
        
        try:
            # Get user info
            user_result = supabase.table("users").select("email, timezone").eq("id", user_id).execute()
            if not user_result.data:
                print(f"⚠️ User {user_id} not found, skipping")
                continue
            
            user_info = {
                "user_id": user_id,
                "email": user_result.data[0].get("email", "unknown"),
                "timezone": user_result.data[0].get("timezone", "UTC")
            }
            
            # Process user (this will do real processing if segments exist)
            await processor._process_user_yesterday(user_info)
            
            # Memory after user (cleanup should have run)
            memory_after = get_memory_mb()
            memory_samples.append(memory_after)
            max_memory = max(max_memory, memory_after)
            
            growth = memory_after - baseline
            print(f"Memory after user {user_idx}: {memory_after:.1f} MB (+{growth:+.1f} MB from baseline)")
            
            # Check threshold
            if memory_after > baseline + 300:
                print(f"⚠️ WARNING: Memory exceeded threshold: {memory_after:.1f} MB")
            
        except Exception as e:
            print(f"❌ Error processing user {user_idx}: {e}")
            import traceback
            traceback.print_exc()
            memory_after = get_memory_mb()
            memory_samples.append(memory_after)
    
    # Final analysis
    final_memory = get_memory_mb()
    final_growth = final_memory - baseline
    
    print(f"\n{'='*60}")
    print("TEST RESULTS")
    print(f"{'='*60}")
    print(f"Baseline memory: {baseline:.1f} MB")
    print(f"Peak memory: {max_memory:.1f} MB")
    print(f"Final memory: {final_memory:.1f} MB")
    print(f"Final growth: {final_growth:+.1f} MB")
    
    if len(memory_samples) >= 2:
        print(f"\nMemory after each user:")
        for idx, mem in enumerate(memory_samples, 1):
            growth = mem - baseline
            print(f"  User {idx}: {mem:.1f} MB (+{growth:+.1f} MB)")
        
        # Check accumulation
        if len(memory_samples) >= 2:
            accumulation = memory_samples[-1] - memory_samples[0]
            print(f"\nMemory accumulation: {accumulation:+.1f} MB")
            
            if accumulation > 150:
                print(f"❌ FAIL: Memory accumulating ({accumulation:.1f} MB)")
                return False
            elif accumulation > 50:
                print(f"⚠️ WARNING: Some accumulation ({accumulation:.1f} MB)")
            else:
                print(f"✅ PASS: Memory stable between users")
    
    # Success criteria
    if final_growth < 200 and max_memory < baseline + 400:
        print(f"\n✅ TEST PASSED: Memory cleanup working correctly")
        print(f"   - Peak memory: {max_memory:.1f} MB (acceptable)")
        print(f"   - Final growth: {final_growth:.1f} MB (acceptable)")
        return True
    else:
        print(f"\n❌ TEST FAILED")
        if final_growth >= 200:
            print(f"   - Final growth too high: {final_growth:.1f} MB")
        if max_memory >= baseline + 400:
            print(f"   - Peak memory too high: {max_memory:.1f} MB")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_real_processing())
    sys.exit(0 if success else 1)

