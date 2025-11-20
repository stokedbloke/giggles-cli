#!/usr/bin/env python3
"""
Test Memory Cleanup Between Multiple Users

This test verifies that memory is properly released after each user
completes processing, preventing memory accumulation across users.
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


async def test_multiple_users_cleanup():
    """
    Test that memory resets between users.
    
    This simulates the cron job processing multiple users sequentially
    and verifies memory doesn't accumulate.
    """
    print("=" * 60)
    print("Multiple Users Memory Cleanup Test")
    print("=" * 60)
    
    # Import and initialize TensorFlow BEFORE measuring baseline
    from process_nightly_audio import NightlyAudioProcessor
    from src.services.supabase_client import get_service_role_client
    
    print("\nLoading TensorFlow model (this takes ~400-500MB)...")
    supabase = get_service_role_client()
    
    # Get multiple users for testing
    result = supabase.table("limitless_keys").select("user_id, users!inner(email)").eq("is_active", True).limit(3).execute()
    
    if not result.data or len(result.data) < 2:
        print("⚠️ Need at least 2 active users for this test")
        print("   Test will simulate with available users")
        if result.data:
            user_ids = [row["user_id"] for row in result.data]
        else:
            print("❌ No active users found")
            return False
    else:
        user_ids = [row["user_id"] for row in result.data[:3]]  # Test with up to 3 users
    
    print(f"\nTesting with {len(user_ids)} user(s)")
    
    # Initialize processor
    processor = NightlyAudioProcessor(include_user_ids=user_ids)
    
    # Measure baseline AFTER TensorFlow loads
    baseline = get_memory_mb()
    print(f"Baseline memory (after TensorFlow load): {baseline:.1f} MB\n")
    
    memory_after_each_user = []
    max_memory_during_test = baseline
    
    # Process each user (simulating cron job)
    for user_idx, user_id in enumerate(user_ids, 1):
        print(f"\n{'='*60}")
        print(f"Processing User {user_idx}/{len(user_ids)}: {user_id[:8]}...")
        print(f"{'='*60}")
        
        # Memory before user
        memory_before_user = get_memory_mb()
        print(f"Memory before user {user_idx}: {memory_before_user:.1f} MB")
        
        try:
            # Get user info
            user_result = supabase.table("users").select("email, timezone").eq("id", user_id).execute()
            if user_result.data:
                user_info = {
                    "user_id": user_id,
                    "email": user_result.data[0].get("email", "unknown"),
                    "timezone": user_result.data[0].get("timezone", "UTC")
                }
            else:
                print(f"⚠️ User {user_id} not found, skipping")
                continue
            
            # Process user (this will trigger cleanup in finally block)
            await processor._process_user_yesterday(user_info)
            
            # Memory after user (cleanup should have run)
            memory_after_user = get_memory_mb()
            memory_after_each_user.append(memory_after_user)
            max_memory_during_test = max(max_memory_during_test, memory_after_user)
            
            growth_from_baseline = memory_after_user - baseline
            print(f"Memory after user {user_idx}: {memory_after_user:.1f} MB (+{growth_from_baseline:+.1f} MB from baseline)")
            
            # Check if memory reset between users
            if user_idx > 1:
                previous_memory = memory_after_each_user[user_idx - 2]
                memory_change = memory_after_user - previous_memory
                
                if abs(memory_change) > 200:
                    print(f"⚠️ WARNING: Memory changed significantly between users: {memory_change:+.1f} MB")
                    if memory_change > 200:
                        print(f"   ⚠️ Memory grew between users (possible leak)")
                    else:
                        print(f"   ✅ Memory decreased between users (cleanup working)")
            
            # Check if memory exceeds threshold
            if memory_after_user > baseline + 300:
                print(f"❌ FAIL: Memory exceeded threshold: {memory_after_user:.1f} MB (baseline: {baseline:.1f} MB)")
                return False
            
        except Exception as e:
            print(f"❌ Error processing user {user_idx}: {e}")
            import traceback
            traceback.print_exc()
            # Still check memory after error
            memory_after_user = get_memory_mb()
            memory_after_each_user.append(memory_after_user)
    
    # Final analysis
    final_memory = get_memory_mb()
    final_growth = final_memory - baseline
    
    print(f"\n{'='*60}")
    print("TEST RESULTS")
    print(f"{'='*60}")
    print(f"Baseline memory: {baseline:.1f} MB")
    print(f"Peak memory: {max_memory_during_test:.1f} MB")
    print(f"Final memory: {final_memory:.1f} MB")
    print(f"Final growth: {final_growth:+.1f} MB")
    
    if len(memory_after_each_user) >= 2:
        print(f"\nMemory after each user:")
        for idx, mem in enumerate(memory_after_each_user, 1):
            growth = mem - baseline
            print(f"  User {idx}: {mem:.1f} MB (+{growth:+.1f} MB)")
        
        # Check for memory accumulation
        first_user_memory = memory_after_each_user[0]
        last_user_memory = memory_after_each_user[-1]
        accumulation = last_user_memory - first_user_memory
        
        print(f"\nMemory accumulation analysis:")
        print(f"  First user: {first_user_memory:.1f} MB")
        print(f"  Last user: {last_user_memory:.1f} MB")
        print(f"  Accumulation: {accumulation:+.1f} MB")
        
        if accumulation > 150:
            print(f"\n❌ FAIL: Memory accumulating between users ({accumulation:.1f} MB)")
            return False
        elif accumulation > 50:
            print(f"\n⚠️ WARNING: Some memory accumulation ({accumulation:.1f} MB)")
        else:
            print(f"\n✅ PASS: Memory stable between users")
    
    # Final success criteria
    if final_growth < 200:
        print(f"\n✅ TEST PASSED: Memory cleanup working correctly")
        print(f"   - Final growth: {final_growth:.1f} MB (acceptable)")
        return True
    else:
        print(f"\n❌ TEST FAILED: Memory didn't return to baseline")
        print(f"   - Final growth: {final_growth:.1f} MB (too high)")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_multiple_users_cleanup())
    sys.exit(0 if success else 1)

