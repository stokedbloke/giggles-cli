#!/usr/bin/env python3
"""
Diagnostic script to identify what's holding memory.

This will help us verify if YAMNet model reload is the right fix.
"""

import sys
import os
import gc
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


def analyze_memory_objects():
    """Analyze what Python objects are holding memory."""
    try:
        import tracemalloc
        tracemalloc.start()
        
        # Get current memory
        current, peak = tracemalloc.get_traced_memory()
        print(f"Current memory: {current / 1024 / 1024:.1f} MB")
        print(f"Peak memory: {peak / 1024 / 1024:.1f} MB")
        
        # Get top memory consumers
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        print("\nTop 10 memory consumers:")
        for index, stat in enumerate(top_stats[:10], 1):
            print(f"{index}. {stat}")
        
        tracemalloc.stop()
    except ImportError:
        print("⚠️ tracemalloc not available, using gc.get_objects()")
        
        # Fallback: count objects by type
        objects = gc.get_objects()
        type_counts = {}
        for obj in objects:
            obj_type = type(obj).__name__
            type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
        
        print("\nTop object types by count:")
        for obj_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
            print(f"  {obj_type}: {count}")


def check_yamnet_model():
    """Check if YAMNet model is loaded and its memory footprint."""
    try:
        from src.services.yamnet_processor import yamnet_processor
        
        print("\n" + "="*60)
        print("YAMNet Model Status")
        print("="*60)
        
        if yamnet_processor.model is None:
            print("❌ Model not loaded")
            return
        
        print("✅ Model is loaded")
        print(f"Model type: {type(yamnet_processor.model)}")
        print(f"Model URL: {yamnet_processor.model_url}")
        
        # Try to get model size (may not work for all model types)
        try:
            import sys
            model_size = sys.getsizeof(yamnet_processor.model)
            print(f"Model object size: {model_size / 1024 / 1024:.2f} MB")
        except:
            print("⚠️ Could not determine model size")
        
        # Check TensorFlow graph
        try:
            import tensorflow as tf
            print(f"TensorFlow default graph: {tf.get_default_graph()}")
            print(f"Active sessions: {len(tf.compat.v1.get_default_session() or [])}")
        except:
            print("⚠️ Could not check TensorFlow state")
            
    except Exception as e:
        print(f"❌ Error checking YAMNet model: {e}")
        import traceback
        traceback.print_exc()


def test_model_reload():
    """Test if reloading model releases memory."""
    print("\n" + "="*60)
    print("Testing Model Reload")
    print("="*60)
    
    baseline = get_memory_mb()
    print(f"Baseline memory: {baseline:.1f} MB")
    
    try:
        from src.services.yamnet_processor import yamnet_processor
        import tensorflow as tf
        import gc
        
        # Check memory with model loaded
        with_model = get_memory_mb()
        print(f"Memory with model: {with_model:.1f} MB")
        print(f"Model overhead: {with_model - baseline:.1f} MB")
        
        # Delete model
        print("\nDeleting model...")
        if yamnet_processor.model is not None:
            del yamnet_processor.model
            yamnet_processor.model = None
        
        # Clear TensorFlow
        tf.keras.backend.clear_session()
        tf.compat.v1.reset_default_graph()
        
        # Aggressive GC
        for _ in range(10):
            gc.collect()
        
        after_delete = get_memory_mb()
        print(f"Memory after delete: {after_delete:.1f} MB")
        print(f"Memory released: {with_model - after_delete:.1f} MB")
        
        # Reload model
        print("\nReloading model...")
        yamnet_processor._load_model()
        
        after_reload = get_memory_mb()
        print(f"Memory after reload: {after_reload:.1f} MB")
        print(f"Memory difference: {after_reload - after_delete:.1f} MB")
        
        if abs(after_reload - with_model) < 50:
            print("✅ Model reload releases memory correctly")
        else:
            print("⚠️ Model reload may not fully release memory")
            
    except Exception as e:
        print(f"❌ Error testing model reload: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("="*60)
    print("Memory Diagnostic Tool")
    print("="*60)
    
    print(f"\nCurrent memory: {get_memory_mb():.1f} MB")
    
    # Check YAMNet model
    check_yamnet_model()
    
    # Analyze memory objects
    print("\n" + "="*60)
    print("Memory Object Analysis")
    print("="*60)
    analyze_memory_objects()
    
    # Test model reload
    test_model_reload()
    
    print("\n" + "="*60)
    print("Diagnostic Complete")
    print("="*60)

