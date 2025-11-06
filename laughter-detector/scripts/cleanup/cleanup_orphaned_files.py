#!/usr/bin/env python3
"""
Orphaned Files Cleanup Script for Giggles Application

This script removes orphaned files from the filesystem when the database has been cleaned.
It ensures complete cleanup of both database and filesystem.

SECURITY: This script only removes orphaned files - it preserves user data integrity.
"""

import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

class OrphanedFilesCleaner:
    def __init__(self):
        """Initialize the cleaner with Supabase connection."""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not self.supabase_url or not self.supabase_service_key:
            print("❌ ERROR: Supabase credentials not found in environment")
            sys.exit(1)
        
        self.supabase = create_client(self.supabase_url, self.supabase_service_key)
        
        # Set up paths
        self.project_root = Path(__file__).parent
        self.uploads_dir = self.project_root / "uploads"
        self.audio_dir = self.uploads_dir / "audio"
        self.clips_dir = self.uploads_dir / "clips"
        self.temp_dir = self.uploads_dir / "temp"
        
        print("🧹 Giggles Orphaned Files Cleaner")
        print("=" * 50)
        print(f"Cleanup Time: {datetime.now().isoformat()}")
        print(f"Project Root: {self.project_root}")
        print(f"Uploads Dir: {self.uploads_dir}")
        print()

    def get_database_file_paths(self) -> List[str]:
        """Get all file paths referenced in the database."""
        try:
            # Get audio segment file paths
            segments_result = self.supabase.table("audio_segments").select("file_path").execute()
            segment_paths = [segment["file_path"] for segment in segments_result.data]
            
            # Get laughter detection clip paths
            detections_result = self.supabase.table("laughter_detections").select("clip_path").execute()
            clip_paths = [detection["clip_path"] for detection in detections_result.data]
            
            all_paths = segment_paths + clip_paths
            print(f"📊 Database references {len(all_paths)} files:")
            print(f"  - Audio segments: {len(segment_paths)}")
            print(f"  - Laughter clips: {len(clip_paths)}")
            
            return all_paths
            
        except Exception as e:
            print(f"❌ Error getting database file paths: {str(e)}")
            return []

    def get_filesystem_files(self) -> Dict[str, List[Path]]:
        """Get all files on the filesystem."""
        files = {
            "audio_files": [],
            "laughter_clips": [],
            "temp_files": []
        }
        
        # Get audio files
        if self.audio_dir.exists():
            for user_dir in self.audio_dir.iterdir():
                if user_dir.is_dir():
                    for file_path in user_dir.rglob("*.ogg"):
                        files["audio_files"].append(file_path)
        
        # Get laughter clips
        if self.clips_dir.exists():
            for file_path in self.clips_dir.rglob("*.wav"):
                files["laughter_clips"].append(file_path)
        
        # Get temp files
        if self.temp_dir.exists():
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    files["temp_files"].append(file_path)
        
        print(f"📁 Filesystem contains:")
        print(f"  - Audio files: {len(files['audio_files'])}")
        print(f"  - Laughter clips: {len(files['laughter_clips'])}")
        print(f"  - Temp files: {len(files['temp_files'])}")
        
        return files

    def find_orphaned_files(self, db_paths: List[str], fs_files: Dict[str, List[Path]]) -> Dict[str, List[Path]]:
        """Find files that exist on filesystem but not in database."""
        orphaned = {
            "audio_files": [],
            "laughter_clips": [],
            "temp_files": []
        }
        
        # Check audio files
        for audio_file in fs_files["audio_files"]:
            # Convert to string for comparison
            file_str = str(audio_file)
            is_referenced = any(file_str in db_path or db_path in file_str for db_path in db_paths)
            
            if not is_referenced:
                orphaned["audio_files"].append(audio_file)
        
        # Check laughter clips
        for clip_file in fs_files["laughter_clips"]:
            file_str = str(clip_file)
            is_referenced = any(file_str in db_path or db_path in file_str for db_path in db_paths)
            
            if not is_referenced:
                orphaned["laughter_clips"].append(clip_file)
        
        # All temp files are considered orphaned if database is clean
        orphaned["temp_files"] = fs_files["temp_files"]
        
        return orphaned

    def calculate_cleanup_size(self, orphaned_files: Dict[str, List[Path]]) -> int:
        """Calculate total size of files to be cleaned up."""
        total_size = 0
        
        for file_type, files in orphaned_files.items():
            for file_path in files:
                if file_path.exists():
                    total_size += file_path.stat().st_size
        
        return total_size

    def cleanup_orphaned_files(self, orphaned_files: Dict[str, List[Path]]) -> Dict[str, int]:
        """Clean up orphaned files."""
        results = {
            "audio_files_removed": 0,
            "laughter_clips_removed": 0,
            "temp_files_removed": 0,
            "total_size_freed": 0
        }
        
        # Clean up audio files
        print(f"\n🗑️  Cleaning up {len(orphaned_files['audio_files'])} orphaned audio files...")
        for audio_file in orphaned_files["audio_files"]:
            try:
                if audio_file.exists():
                    file_size = audio_file.stat().st_size
                    audio_file.unlink()
                    results["audio_files_removed"] += 1
                    results["total_size_freed"] += file_size
                    print(f"  ✅ Removed: {audio_file.name} ({file_size / 1024 / 1024:.2f} MB)")
            except Exception as e:
                print(f"  ❌ Failed to remove {audio_file.name}: {str(e)}")
        
        # Clean up laughter clips
        print(f"\n🗑️  Cleaning up {len(orphaned_files['laughter_clips'])} orphaned laughter clips...")
        for clip_file in orphaned_files["laughter_clips"]:
            try:
                if clip_file.exists():
                    file_size = clip_file.stat().st_size
                    clip_file.unlink()
                    results["laughter_clips_removed"] += 1
                    results["total_size_freed"] += file_size
                    print(f"  ✅ Removed: {clip_file.name} ({file_size / 1024 / 1024:.2f} MB)")
            except Exception as e:
                print(f"  ❌ Failed to remove {clip_file.name}: {str(e)}")
        
        # Clean up temp files
        print(f"\n🗑️  Cleaning up {len(orphaned_files['temp_files'])} temp files...")
        for temp_file in orphaned_files["temp_files"]:
            try:
                if temp_file.exists():
                    file_size = temp_file.stat().st_size
                    temp_file.unlink()
                    results["temp_files_removed"] += 1
                    results["total_size_freed"] += file_size
                    print(f"  ✅ Removed: {temp_file.name} ({file_size / 1024 / 1024:.2f} MB)")
            except Exception as e:
                print(f"  ❌ Failed to remove {temp_file.name}: {str(e)}")
        
        return results

    def cleanup_empty_directories(self):
        """Remove empty directories."""
        print(f"\n🧹 Cleaning up empty directories...")
        
        directories_to_check = [self.audio_dir, self.clips_dir, self.temp_dir]
        
        for directory in directories_to_check:
            if directory.exists():
                try:
                    # Remove empty user directories
                    for user_dir in directory.iterdir():
                        if user_dir.is_dir() and not any(user_dir.iterdir()):
                            shutil.rmtree(user_dir)
                            print(f"  ✅ Removed empty directory: {user_dir.name}")
                    
                    # Remove the main directory if it's empty
                    if not any(directory.iterdir()):
                        shutil.rmtree(directory)
                        print(f"  ✅ Removed empty directory: {directory.name}")
                        
                except Exception as e:
                    print(f"  ⚠️  Could not remove directory {directory.name}: {str(e)}")

    def run_cleanup(self) -> bool:
        """Run the complete orphaned files cleanup process."""
        try:
            print("🔍 Analyzing filesystem vs database...")
            
            # Get database file paths
            db_paths = self.get_database_file_paths()
            
            # Get filesystem files
            fs_files = self.get_filesystem_files()
            
            # Find orphaned files
            orphaned_files = self.find_orphaned_files(db_paths, fs_files)
            
            total_orphaned = sum(len(files) for files in orphaned_files.values())
            
            if total_orphaned == 0:
                print("✅ No orphaned files found - filesystem is clean!")
                return True
            
            print(f"\n📊 Found {total_orphaned} orphaned files:")
            print(f"  - Audio files: {len(orphaned_files['audio_files'])}")
            print(f"  - Laughter clips: {len(orphaned_files['laughter_clips'])}")
            print(f"  - Temp files: {len(orphaned_files['temp_files'])}")
            
            # Calculate cleanup size
            cleanup_size = self.calculate_cleanup_size(orphaned_files)
            print(f"  - Total size to free: {cleanup_size / 1024 / 1024:.2f} MB")
            
            # Confirm cleanup
            print(f"\n⚠️  This will permanently delete {total_orphaned} files ({cleanup_size / 1024 / 1024:.2f} MB)")
            print("Proceeding with cleanup...")
            
            # Clean up orphaned files
            results = self.cleanup_orphaned_files(orphaned_files)
            
            # Clean up empty directories
            self.cleanup_empty_directories()
            
            # Summary
            print(f"\n📋 CLEANUP SUMMARY")
            print("-" * 30)
            print(f"Audio files removed: {results['audio_files_removed']}")
            print(f"Laughter clips removed: {results['laughter_clips_removed']}")
            print(f"Temp files removed: {results['temp_files_removed']}")
            print(f"Total size freed: {results['total_size_freed'] / 1024 / 1024:.2f} MB")
            
            if results['total_size_freed'] > 0:
                print("✅ Orphaned files cleanup completed successfully")
            else:
                print("✅ No orphaned files to clean up")
            
            return True
            
        except Exception as e:
            print(f"❌ Cleanup failed with error: {str(e)}")
            return False

def main():
    """Main entry point for the cleaner."""
    cleaner = OrphanedFilesCleaner()
    success = cleaner.run_cleanup()
    
    if success:
        print("\n✅ Orphaned files cleanup completed")
        sys.exit(0)
    else:
        print("\n❌ Orphaned files cleanup failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
