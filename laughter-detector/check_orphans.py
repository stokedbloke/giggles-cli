#!/usr/bin/env python3
"""
Orphaned Files Checker

This script checks for orphaned audio files that should have been deleted
but weren't. It's safe to run - it only detects, doesn't delete.

Usage:
    python check_orphans.py

Output:
    - Prints a report of orphaned files
    - Exits with code 0 if no orphans found
    - Exits with code 1 if orphans are found (for monitoring/alerting)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.services.orphan_detector import orphan_detector


def main():
    """Main entry point for orphan checker."""
    print("🔍 Checking for orphaned files...")
    print()
    
    # Get orphan report
    report = orphan_detector.get_orphan_report()
    
    # Print formatted report
    orphan_detector.print_report()
    
    # Exit with appropriate code
    if report["audio_orphans_count"] > 0:
        print(f"⚠️  WARNING: {report['audio_orphans_count']} orphaned files found!")
        print(f"   Total size: {report['audio_orphans_total_size_mb']} MB")
        print()
        print("💡 Recommendation: Review these files and delete manually if needed.")
        sys.exit(1)
    else:
        print("✅ No orphaned files found - all good!")
        sys.exit(0)


if __name__ == "__main__":
    main()
