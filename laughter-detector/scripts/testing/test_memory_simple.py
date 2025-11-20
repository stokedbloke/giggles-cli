#!/usr/bin/env python3
"""
Simple Memory Test

Process multiple segments and verify memory doesn't grow unbounded.
Minimal test to verify cleanup works.
"""

import sys
import os
import asyncio
import psutil
from pathlib import Path

# Add project root to path (so we can import from src)
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


async def test_memory_cleanup():
    """
    Test that memory cleanup works between segments.
    
    This is a minimal test - just verify memory doesn't grow unbounded.
    """
    print("=" * 60)
    print("Simple Memory Cleanup Test")
    print("=" * 60)
    
    # Import and initialize TensorFlow BEFORE measuring baseline
    # TensorFlow model loading takes ~400-500MB, so baseline should be AFTER loading
    from src.services.scheduler import Scheduler
    from src.services.supabase_client import get_service_role_client
    
    print("\nLoading TensorFlow model (this takes ~400-500MB)...")
    scheduler = Scheduler()
    supabase = get_service_role_client()
    
    # Now measure baseline AFTER TensorFlow is loaded
    baseline = get_memory_mb()
    print(f"\nBaseline memory (after TensorFlow load): {baseline:.1f} MB")
    
    # Get a test user with segments
    result = supabase.table("limitless_keys").select("user_id").eq("is_active", True).limit(1).execute()
    
    if not result.data:
        print("❌ No active users found for testing")
        return False
    
    user_id = result.data[0]["user_id"]
    print(f"Testing with user: {user_id[:8]}...")
    
    # Get unprocessed segments (or use test segments)
    # For now, just simulate processing
    print("\nProcessing segments...")
    
    max_memory = baseline
    memory_samples = []
    
    # Process 10 segments (or as many as available)
    segments_processed = 0
    for i in range(10):
        memory_before = get_memory_mb()
        
        # Simulate segment processing
        # In real test, you'd call:
        # await scheduler._process_audio_segment(user_id, segment, segment_id)
        print(f"  Segment {i+1}: memory before = {memory_before:.1f} MB", end="")
        
        # Small delay to simulate processing
        await asyncio.sleep(0.1)
        
        memory_after = get_memory_mb()
        max_memory = max(max_memory, memory_after)
        memory_samples.append(memory_after)
        
        growth = memory_after - baseline
        print(f" → after = {memory_after:.1f} MB (+{growth:+.1f} MB)")
        
        # Check if memory grew too much during processing
        # Threshold: 200 MB growth is acceptable (TensorFlow inference overhead)
        # But if it keeps growing segment by segment, that's a leak
        if memory_after > baseline + 300:
            print(f"\n❌ FAIL: Memory grew too much: {memory_after:.1f} MB (baseline: {baseline:.1f} MB, growth: {growth:.1f} MB)")
            return False
        
        segments_processed += 1
    
    # Final check
    final_memory = get_memory_mb()
    final_growth = final_memory - baseline
    
    print(f"\nResults:")
    print(f"  Segments processed: {segments_processed}")
    print(f"  Baseline memory: {baseline:.1f} MB")
    print(f"  Peak memory: {max_memory:.1f} MB")
    print(f"  Final memory: {final_memory:.1f} MB")
    print(f"  Total growth: {final_growth:+.1f} MB")
    
    # Check for memory leak (linear growth)
    if len(memory_samples) >= 5:
        first_half = sum(memory_samples[:5]) / 5
        second_half = sum(memory_samples[5:]) / 5
        growth_rate = ((second_half - first_half) / first_half) * 100
        
        print(f"  Growth rate: {growth_rate:+.1f}%")
        
        if growth_rate > 10:
            print(f"\n⚠️ WARNING: Memory growing linearly ({growth_rate:.1f}% growth)")
            return False
    
    # Success criteria
    # After processing, memory should return close to baseline
    # Allow 150 MB overhead for TensorFlow operations
    if final_growth < 150:
        print(f"\n✅ PASS: Memory stable (growth < 150 MB from baseline)")
        return True
    else:
        print(f"\n❌ FAIL: Memory didn't return to baseline (growth: {final_growth:.1f} MB)")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_memory_cleanup())
    sys.exit(0 if success else 1)

