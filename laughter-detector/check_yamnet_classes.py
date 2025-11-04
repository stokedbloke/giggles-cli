#!/usr/bin/env python3
"""
Check YAMNet class names for laughter-related classes.
"""

def check_yamnet_classes():
    """Check what the actual YAMNet class names are."""
    
    # YAMNet class IDs for laughter (from the code)
    laughter_class_ids = [13, 14, 15, 17, 18]
    
    print("🎭 YAMNet Laughter Classes:")
    print("=" * 30)
    
    # These are the typical YAMNet class names (from the YAMNet paper/dataset)
    yamnet_classes = {
        13: "Laughter",
        14: "Baby laughter, baby giggling",
        15: "Giggle", 
        17: "Belly laugh",
        18: "Chuckle, chortle"
    }
    
    for class_id in laughter_class_ids:
        class_name = yamnet_classes.get(class_id, f"Unknown class {class_id}")
        print(f"Class {class_id:2d}: {class_name}")
    
    print()
    print("🔍 Analysis:")
    print("- All your detections are Class 13 (Laughter)")
    print("- This suggests YAMNet is only detecting general 'Laughter'")
    print("- Other laughter types (giggle, chuckle, belly laugh) may not be present in your audio")
    print("- Or the threshold (0.3) may be filtering them out")
    
    print()
    print("💡 Possible reasons:")
    print("1. Your audio only contains general laughter, not specific types")
    print("2. Threshold too high - try lowering it to 0.2 or 0.1")
    print("3. YAMNet model may not be detecting subtle differences")
    print("4. Audio quality or duration may affect detection")

if __name__ == "__main__":
    check_yamnet_classes()
