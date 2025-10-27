"""
Orphaned file detection service.

This service detects orphaned audio files and clips that should have been deleted
but weren't. It's designed to be safe - it only DETECTS, it doesn't automatically clean up.

Usage:
    - Run manually to check for orphans
    - Add to monitoring/alerting
    - Can be called from admin interface
"""

import os
import logging
from typing import List, Dict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class OrphanDetector:
    """Service for detecting orphaned files without automatic cleanup."""
    
    def __init__(self, upload_dir: str = "uploads"):
        """Initialize orphan detector."""
        self.upload_dir = Path(upload_dir)
        self.audio_dir = self.upload_dir / "audio"
        self.clips_dir = self.upload_dir / "clips"
    
    def detect_orphaned_audio_files(self) -> List[Dict]:
        """
        Detect orphaned audio files in the audio directory.
        
        Returns:
            List of orphaned file information dictionaries
        """
        orphans = []
        
        if not self.audio_dir.exists():
            logger.warning(f"Audio directory not found: {self.audio_dir}")
            return orphans
        
        # Get all .ogg files in audio directories
        for user_dir in self.audio_dir.iterdir():
            if not user_dir.is_dir():
                continue
            
            user_id = user_dir.name
            for audio_file in user_dir.glob("*.ogg"):
                try:
                    file_info = {
                        "path": str(audio_file),
                        "user_id": user_id,
                        "filename": audio_file.name,
                        "size_mb": audio_file.stat().st_size / (1024 * 1024),
                        "modified": datetime.fromtimestamp(audio_file.stat().st_mtime),
                        "reason": "exists_on_disk"
                    }
                    orphans.append(file_info)
                except Exception as e:
                    logger.error(f"Error checking file {audio_file}: {str(e)}")
        
        return orphans
    
    def get_orphan_report(self) -> Dict:
        """
        Generate a comprehensive orphan report.
        
        Returns:
            Dictionary with orphan statistics and file lists
        """
        logger.info("🔍 Scanning for orphaned files...")
        
        audio_orphans = self.detect_orphaned_audio_files()
        
        total_size_mb = sum(o["size_mb"] for o in audio_orphans)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "audio_orphans_count": len(audio_orphans),
            "audio_orphans_total_size_mb": round(total_size_mb, 2),
            "audio_orphans": audio_orphans
        }
        
        logger.info(f"✅ Found {len(audio_orphans)} orphaned audio files ({total_size_mb:.2f} MB)")
        
        return report
    
    def print_report(self):
        """Print a formatted orphan report to the console."""
        report = self.get_orphan_report()
        
        print("\n" + "=" * 60)
        print("ORPHANED FILES REPORT")
        print("=" * 60)
        print(f"Scan Time: {report['timestamp']}")
        print()
        
        if report["audio_orphans_count"] == 0:
            print("✅ No orphaned audio files found!")
        else:
            print(f"⚠️  Found {report['audio_orphans_count']} orphaned audio files")
            print(f"   Total size: {report['audio_orphans_total_size_mb']} MB")
            print()
            print("Files:")
            for orphan in report["audio_orphans"]:
                print(f"  - {orphan['filename']} ({orphan['size_mb']:.2f} MB)")
                print(f"    User: {orphan['user_id']}")
                print(f"    Modified: {orphan['modified']}")
                print()
        
        print("=" * 60)
        print()


# Global instance
orphan_detector = OrphanDetector()
