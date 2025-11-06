#!/usr/bin/env python3
"""
Cleanup Existing Duplicates Script
===================================

This script identifies and removes duplicate laughter detections and audio clips
that were created before the duplicate prevention system was implemented.

Usage:
    python3 cleanup_existing_duplicates.py [--dry-run] [--aggressive]

Options:
    --dry-run     Show what would be deleted without actually deleting
    --aggressive  Remove more potential duplicates (use with caution)
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from dotenv import load_dotenv
from supabase import create_client, Client
import shutil
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DuplicateCleanup:
    def __init__(self, dry_run: bool = False, aggressive: bool = False):
        self.dry_run = dry_run
        self.aggressive = aggressive
        
        # Load environment variables
        load_dotenv()
        
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise Exception("Supabase credentials not found")
        
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        self.uploads_dir = Path("/Users/neilsethi/git/giggles-cli/laughter-detector/uploads")
        
        logger.info(f"🔧 Duplicate Cleanup initialized (dry_run={dry_run}, aggressive={aggressive})")
    
    def find_duplicate_laughter_detections(self) -> List[Dict]:
        """Find duplicate laughter detections."""
        logger.info("🔍 Scanning for duplicate laughter detections...")
        
        # Get all laughter detections grouped by user and time window
        result = self.supabase.table("laughter_detections").select("*").order("user_id").order("timestamp").execute()
        
        if not result.data:
            logger.info("✅ No laughter detections found")
            return []
        
        duplicates = []
        current_user = None
        current_window = None
        window_detections = []
        
        for detection in result.data:
            user_id = detection["user_id"]
            timestamp = datetime.fromisoformat(detection["timestamp"].replace('Z', '+00:00'))
            
            # New user or time window
            if current_user != user_id or not current_window or (timestamp - current_window).total_seconds() > 5:
                # Process previous window if it had duplicates
                if len(window_detections) > 1:
                    duplicates.extend(self._process_window_duplicates(window_detections))
                
                # Start new window
                current_user = user_id
                current_window = timestamp
                window_detections = [detection]
            else:
                window_detections.append(detection)
        
        # Process final window
        if len(window_detections) > 1:
            duplicates.extend(self._process_window_duplicates(window_detections))
        
        logger.info(f"🔍 Found {len(duplicates)} duplicate laughter detections")
        return duplicates
    
    def _process_window_duplicates(self, detections: List[Dict]) -> List[Dict]:
        """Process a window of detections to find duplicates."""
        if len(detections) <= 1:
            return []
        
        # Sort by probability (descending) and created_at (ascending)
        detections.sort(key=lambda x: (-x["probability"], x.get("created_at", "")))
        
        # Keep the first (highest probability, earliest created)
        keep = detections[0]
        duplicates = []
        
        for detection in detections[1:]:
            # Check if it's really a duplicate
            time_diff = abs((datetime.fromisoformat(detection["timestamp"].replace('Z', '+00:00')) - 
                           datetime.fromisoformat(keep["timestamp"].replace('Z', '+00:00'))).total_seconds())
            prob_diff = abs(detection["probability"] - keep["probability"])
            
            # Consider it a duplicate if within 5 seconds and probability within 20%
            if time_diff <= 5 and prob_diff <= 0.2:
                duplicates.append({
                    "id": detection["id"],
                    "user_id": detection["user_id"],
                    "timestamp": detection["timestamp"],
                    "probability": detection["probability"],
                    "clip_path": detection.get("clip_path"),
                    "reason": f"Duplicate of {keep['id']} (time_diff: {time_diff:.1f}s, prob_diff: {prob_diff:.3f})"
                })
        
        return duplicates
    
    def find_duplicate_clip_files(self) -> List[Dict]:
        """Find duplicate clip files on filesystem."""
        logger.info("🔍 Scanning for duplicate clip files...")
        
        if not self.uploads_dir.exists():
            logger.info("✅ No uploads directory found")
            return []
        
        clip_files = []
        for user_dir in self.uploads_dir.iterdir():
            if user_dir.is_dir():
                laughter_dir = user_dir / "laughter_clips"
                if laughter_dir.exists():
                    for clip_file in laughter_dir.glob("*.wav"):
                        clip_files.append({
                            "path": str(clip_file),
                            "size": clip_file.stat().st_size,
                            "mtime": clip_file.stat().st_mtime,
                            "user_id": user_dir.name
                        })
        
        # Group by size and find duplicates
        size_groups = {}
        for clip in clip_files:
            size = clip["size"]
            if size not in size_groups:
                size_groups[size] = []
            size_groups[size].append(clip)
        
        duplicates = []
        for size, clips in size_groups.items():
            if len(clips) > 1:
                # Sort by modification time (keep newest)
                clips.sort(key=lambda x: x["mtime"], reverse=True)
                keep = clips[0]
                
                for clip in clips[1:]:
                    # Check if files are identical (basic check)
                    if self._files_identical(keep["path"], clip["path"]):
                        duplicates.append({
                            "path": clip["path"],
                            "user_id": clip["user_id"],
                            "reason": f"Duplicate of {keep['path']} (same size: {size} bytes)"
                        })
        
        logger.info(f"🔍 Found {len(duplicates)} duplicate clip files")
        return duplicates
    
    def _files_identical(self, path1: str, path2: str) -> bool:
        """Check if two files are identical (basic implementation)."""
        try:
            with open(path1, 'rb') as f1, open(path2, 'rb') as f2:
                # Read first 1KB to compare
                chunk1 = f1.read(1024)
                chunk2 = f2.read(1024)
                return chunk1 == chunk2
        except Exception:
            return False
    
    def cleanup_duplicate_laughter_detections(self, duplicates: List[Dict]) -> int:
        """Remove duplicate laughter detections from database."""
        if not duplicates:
            logger.info("✅ No duplicate laughter detections to clean up")
            return 0
        
        logger.info(f"🧹 Cleaning up {len(duplicates)} duplicate laughter detections...")
        
        deleted_count = 0
        for duplicate in duplicates:
            try:
                if self.dry_run:
                    logger.info(f"🔍 [DRY RUN] Would delete laughter detection: {duplicate['id']} - {duplicate['reason']}")
                else:
                    self.supabase.table("laughter_detections").delete().eq("id", duplicate["id"]).execute()
                    logger.info(f"🗑️  Deleted laughter detection: {duplicate['id']} - {duplicate['reason']}")
                deleted_count += 1
            except Exception as e:
                logger.error(f"❌ Error deleting laughter detection {duplicate['id']}: {str(e)}")
        
        return deleted_count
    
    def cleanup_duplicate_clip_files(self, duplicates: List[Dict]) -> int:
        """Remove duplicate clip files from filesystem."""
        if not duplicates:
            logger.info("✅ No duplicate clip files to clean up")
            return 0
        
        logger.info(f"🧹 Cleaning up {len(duplicates)} duplicate clip files...")
        
        deleted_count = 0
        for duplicate in duplicates:
            try:
                if self.dry_run:
                    logger.info(f"🔍 [DRY RUN] Would delete clip file: {duplicate['path']} - {duplicate['reason']}")
                else:
                    Path(duplicate["path"]).unlink()
                    logger.info(f"🗑️  Deleted clip file: {duplicate['path']} - {duplicate['reason']}")
                deleted_count += 1
            except Exception as e:
                logger.error(f"❌ Error deleting clip file {duplicate['path']}: {str(e)}")
        
        return deleted_count
    
    def run_cleanup(self):
        """Run the complete cleanup process."""
        logger.info("🚀 Starting duplicate cleanup process...")
        
        # Step 1: Find and clean up duplicate laughter detections
        laughter_duplicates = self.find_duplicate_laughter_detections()
        laughter_deleted = self.cleanup_duplicate_laughter_detections(laughter_duplicates)
        
        # Step 2: Find and clean up duplicate clip files
        clip_duplicates = self.find_duplicate_clip_files()
        clip_deleted = self.cleanup_duplicate_clip_files(clip_duplicates)
        
        # Summary
        logger.info("📊 Cleanup Summary:")
        logger.info(f"   Laughter detections: {len(laughter_duplicates)} found, {laughter_deleted} {'would be ' if self.dry_run else ''}deleted")
        logger.info(f"   Clip files: {len(clip_duplicates)} found, {clip_deleted} {'would be ' if self.dry_run else ''}deleted")
        
        if self.dry_run:
            logger.info("🔍 This was a dry run - no actual changes were made")
        else:
            logger.info("✅ Cleanup completed successfully")
        
        return laughter_deleted + clip_deleted

def main():
    parser = argparse.ArgumentParser(description="Clean up duplicate laughter detections and clip files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    parser.add_argument("--aggressive", action="store_true", help="Remove more potential duplicates (use with caution)")
    
    args = parser.parse_args()
    
    try:
        cleanup = DuplicateCleanup(dry_run=args.dry_run, aggressive=args.aggressive)
        deleted_count = cleanup.run_cleanup()
        
        if args.dry_run:
            print(f"\n🔍 Dry run completed - {deleted_count} items would be deleted")
            print("Run without --dry-run to perform actual cleanup")
        else:
            print(f"\n✅ Cleanup completed - {deleted_count} items deleted")
            
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
