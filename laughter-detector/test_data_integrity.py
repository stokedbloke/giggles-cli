#!/usr/bin/env python3
"""
Data Integrity Test for Giggles Application

This script validates data consistency between database and filesystem.
It tracks mismatches to help identify cleanup and file management bugs.

SECURITY: This script only READS data - it never modifies anything.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

class DataIntegrityTest:
    def __init__(self):
        """Initialize the test with Supabase connection."""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not self.supabase_url or not self.supabase_service_key:
            print("❌ ERROR: Supabase credentials not found in environment")
            sys.exit(1)
        
        self.supabase = create_client(self.supabase_url, self.supabase_service_key)
        self.project_root = Path(__file__).parent
        self.uploads_dir = self.project_root / "uploads"
        
        print("🔍 Giggles Data Integrity Test")
        print("=" * 50)
        print(f"Test Time: {datetime.now().isoformat()}")
        print(f"Project Root: {self.project_root}")
        print(f"Uploads Dir: {self.uploads_dir}")
        print()

    def test_database_counts(self) -> Dict[str, int]:
        """Count records in each database table."""
        print("📊 DATABASE COUNTS")
        print("-" * 30)
        
        counts = {}
        
        try:
            # Count users
            users_result = self.supabase.table("users").select("id", count="exact").execute()
            counts['users'] = users_result.count
            print(f"Users: {counts['users']}")
            
            # Count limitless_keys
            keys_result = self.supabase.table("limitless_keys").select("id", count="exact").execute()
            counts['limitless_keys'] = keys_result.count
            print(f"Limitless Keys: {counts['limitless_keys']}")
            
            # Count audio_segments
            segments_result = self.supabase.table("audio_segments").select("id", count="exact").execute()
            counts['audio_segments'] = segments_result.count
            print(f"Audio Segments: {counts['audio_segments']}")
            
            # Count processed vs unprocessed segments
            processed_result = self.supabase.table("audio_segments").select("id", count="exact").eq("processed", True).execute()
            counts['processed_segments'] = processed_result.count
            print(f"  └─ Processed: {counts['processed_segments']}")
            print(f"  └─ Unprocessed: {counts['audio_segments'] - counts['processed_segments']}")
            
            # Count laughter_detections
            detections_result = self.supabase.table("laughter_detections").select("id", count="exact").execute()
            counts['laughter_detections'] = detections_result.count
            print(f"Laughter Detections: {counts['laughter_detections']}")
            
            # Count by date
            if counts['laughter_detections'] > 0:
                detections_by_date = self.supabase.table("laughter_detections").select("timestamp").execute()
                dates = {}
                for detection in detections_by_date.data:
                    if detection['timestamp']:
                        date_str = detection['timestamp'][:10]  # Extract YYYY-MM-DD
                        dates[date_str] = dates.get(date_str, 0) + 1
                
                print(f"  └─ By Date:")
                for date, count in sorted(dates.items()):
                    print(f"      {date}: {count}")
            
        except Exception as e:
            print(f"❌ Database query failed: {str(e)}")
            return {}
        
        print()
        return counts

    def test_filesystem_counts(self) -> Dict[str, int]:
        """Count files in each directory."""
        print("📁 FILESYSTEM COUNTS")
        print("-" * 30)
        
        counts = {}
        
        try:
            # Count audio files (original downloads)
            audio_dir = self.uploads_dir / "audio"
            if audio_dir.exists():
                audio_files = list(audio_dir.rglob("*.ogg")) + list(audio_dir.rglob("*.wav")) + list(audio_dir.rglob("*.mp3"))
                counts['audio_files'] = len(audio_files)
                print(f"Audio Files: {counts['audio_files']}")
                
                # Show file details
                if audio_files:
                    print(f"  └─ File types:")
                    ogg_count = len([f for f in audio_files if f.suffix == '.ogg'])
                    wav_count = len([f for f in audio_files if f.suffix == '.wav'])
                    mp3_count = len([f for f in audio_files if f.suffix == '.mp3'])
                    if ogg_count > 0: print(f"      .ogg: {ogg_count}")
                    if wav_count > 0: print(f"      .wav: {wav_count}")
                    if mp3_count > 0: print(f"      .mp3: {mp3_count}")
                    
                    # Show file sizes
                    total_size = sum(f.stat().st_size for f in audio_files)
                    print(f"  └─ Total size: {total_size / (1024*1024):.2f} MB")
            else:
                counts['audio_files'] = 0
                print(f"Audio Files: 0 (directory doesn't exist)")
            
            # Count laughter clips
            clips_dir = self.uploads_dir / "clips"
            if clips_dir.exists():
                clip_files = list(clips_dir.rglob("*.wav")) + list(clips_dir.rglob("*.mp3"))
                counts['laughter_clips'] = len(clip_files)
                print(f"Laughter Clips: {counts['laughter_clips']}")
                
                if clip_files:
                    # Show clip details
                    print(f"  └─ File types:")
                    wav_count = len([f for f in clip_files if f.suffix == '.wav'])
                    mp3_count = len([f for f in clip_files if f.suffix == '.mp3'])
                    if wav_count > 0: print(f"      .wav: {wav_count}")
                    if mp3_count > 0: print(f"      .mp3: {mp3_count}")
                    
                    # Show file sizes
                    total_size = sum(f.stat().st_size for f in clip_files)
                    print(f"  └─ Total size: {total_size / (1024*1024):.2f} MB")
                    
                    # Show sample filenames
                    print(f"  └─ Sample files:")
                    for i, file in enumerate(sorted(clip_files)[:3]):
                        print(f"      {file.name}")
                    if len(clip_files) > 3:
                        print(f"      ... and {len(clip_files) - 3} more")
            else:
                counts['laughter_clips'] = 0
                print(f"Laughter Clips: 0 (directory doesn't exist)")
            
            # Count temp files
            temp_dir = self.uploads_dir / "temp"
            if temp_dir.exists():
                temp_files = list(temp_dir.rglob("*"))
                counts['temp_files'] = len(temp_files)
                print(f"Temp Files: {counts['temp_files']}")
            else:
                counts['temp_files'] = 0
                print(f"Temp Files: 0 (directory doesn't exist)")
                
        except Exception as e:
            print(f"❌ Filesystem scan failed: {str(e)}")
            return {}
        
        print()
        return counts

    def analyze_inconsistencies(self, db_counts: Dict[str, int], fs_counts: Dict[str, int]) -> List[str]:
        """Analyze data inconsistencies and return issues found."""
        print("🔍 INCONSISTENCY ANALYSIS")
        print("-" * 30)
        
        issues = []
        
        # Check 1: Audio segments vs audio files
        total_segments = db_counts.get('audio_segments', 0)
        processed_segments = db_counts.get('processed_segments', 0)
        unprocessed_segments = total_segments - processed_segments
        actual_audio_files = fs_counts.get('audio_files', 0)
        
        # Only unprocessed segments should have corresponding files
        if unprocessed_segments != actual_audio_files:
            issue = f"Unprocessed Segments ({unprocessed_segments}) ≠ Audio Files ({actual_audio_files})"
            issues.append(issue)
            print(f"❌ {issue}")
            
            # Debug: Check if files were deleted but segments not updated
            if actual_audio_files < unprocessed_segments:
                print(f"   └─ DEBUG: {unprocessed_segments - actual_audio_files} files missing - possible deletion bug")
            else:
                print(f"   └─ DEBUG: {actual_audio_files - unprocessed_segments} extra files - possible duplicate processing")
        else:
            print(f"✅ Unprocessed Segments ({unprocessed_segments}) = Audio Files ({actual_audio_files})")
        
        # Check if processed segments have files (they shouldn't)
        if processed_segments > 0 and actual_audio_files > 0:
            if actual_audio_files > unprocessed_segments:
                issue = f"Files still exist ({actual_audio_files}) but {processed_segments} segments marked processed"
                issues.append(issue)
                print(f"❌ {issue}")
                print(f"   └─ DEBUG: File deletion after processing may be failing")
            else:
                print(f"✅ File cleanup working: {actual_audio_files} files for {unprocessed_segments} unprocessed segments")
        
        # Check 2: Laughter detections vs clips ratio
        detections = db_counts.get('laughter_detections', 0)
        clips = fs_counts.get('laughter_clips', 0)
        
        if detections > 0 and clips > 0:
            ratio = clips / detections
            if ratio > 5:  # More than 5 clips per detection is suspicious
                issue = f"High clip ratio: {clips} clips for {detections} detections (ratio: {ratio:.1f})"
                issues.append(issue)
                print(f"❌ {issue}")
                print(f"   └─ DEBUG: Possible over-generation of clips")
            else:
                print(f"✅ Clip ratio reasonable: {clips} clips for {detections} detections (ratio: {ratio:.1f})")
        elif detections > 0 and clips == 0:
            issue = f"Laughter detections ({detections}) but no clips generated"
            issues.append(issue)
            print(f"❌ {issue}")
            print(f"   └─ DEBUG: Clip generation may be failing")
        elif detections == 0 and clips > 0:
            issue = f"No laughter detections but {clips} clips exist"
            issues.append(issue)
            print(f"❌ {issue}")
            print(f"   └─ DEBUG: Clips may be from old data or orphaned")
        else:
            print(f"✅ No laughter data yet (detections: {detections}, clips: {clips})")
        
        # Check 3: Processed segments vs remaining files
        processed = db_counts.get('processed_segments', 0)
        unprocessed = db_counts.get('audio_segments', 0) - processed
        
        if processed > 0 and actual_audio_files > 0:
            if actual_audio_files > unprocessed:
                issue = f"Files still exist ({actual_audio_files}) but {processed} segments marked processed"
                issues.append(issue)
                print(f"❌ {issue}")
                print(f"   └─ DEBUG: File deletion after processing may be failing")
            else:
                print(f"✅ File cleanup working: {actual_audio_files} files for {unprocessed} unprocessed segments")
        
        # Check 4: Temp files cleanup
        temp_files = fs_counts.get('temp_files', 0)
        if temp_files > 0:
            issue = f"Temp files not cleaned up: {temp_files} files"
            issues.append(issue)
            print(f"❌ {issue}")
            print(f"   └─ DEBUG: Temp cleanup may be failing")
        else:
            print(f"✅ No temp files (cleanup working)")
        
        print()
        return issues

    def generate_report(self, db_counts: Dict[str, int], fs_counts: Dict[str, int], issues: List[str]) -> str:
        """Generate a comprehensive test report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "database_counts": db_counts,
            "filesystem_counts": fs_counts,
            "issues_found": len(issues),
            "issues": issues,
            "summary": {
                "total_issues": len(issues),
                "critical_issues": len([i for i in issues if "❌" in i]),
                "data_consistency": "GOOD" if len(issues) == 0 else "NEEDS_ATTENTION"
            }
        }
        
        return json.dumps(report, indent=2)

    def run_test(self) -> bool:
        """Run the complete data integrity test."""
        try:
            # Test database
            db_counts = self.test_database_counts()
            if not db_counts:
                print("❌ Database test failed")
                return False
            
            # Test filesystem
            fs_counts = self.test_filesystem_counts()
            if not fs_counts:
                print("❌ Filesystem test failed")
                return False
            
            # Analyze inconsistencies
            issues = self.analyze_inconsistencies(db_counts, fs_counts)
            
            # Generate report
            report = self.generate_report(db_counts, fs_counts, issues)
            
            # Save report
            report_file = self.project_root / "data_integrity_report.json"
            with open(report_file, 'w') as f:
                f.write(report)
            
            # Print summary
            print("📋 TEST SUMMARY")
            print("-" * 30)
            print(f"Issues Found: {len(issues)}")
            if issues:
                print("Issues:")
                for i, issue in enumerate(issues, 1):
                    print(f"  {i}. {issue}")
            else:
                print("✅ No issues found - data integrity is good!")
            
            print(f"\n📄 Full report saved to: {report_file}")
            
            return len(issues) == 0
            
        except Exception as e:
            print(f"❌ Test failed with error: {str(e)}")
            return False

def main():
    """Main entry point for the test."""
    test = DataIntegrityTest()
    success = test.run_test()
    
    if success:
        print("\n✅ Data integrity test PASSED")
        sys.exit(0)
    else:
        print("\n❌ Data integrity test FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
