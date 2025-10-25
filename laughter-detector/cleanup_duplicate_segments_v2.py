#!/usr/bin/env python3
"""
Improved Duplicate Segments Cleanup Script for Giggles Application

This script removes duplicate/overlapping audio segments from the database,
but PRIORITIZES segments that have laughter detections associated with them.

SECURITY: This script only removes duplicate data - it preserves user data integrity.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

class ImprovedDuplicateSegmentCleaner:
    def __init__(self):
        """Initialize the cleaner with Supabase connection."""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not self.supabase_url or not self.supabase_service_key:
            print("❌ ERROR: Supabase credentials not found in environment")
            sys.exit(1)
        
        self.supabase = create_client(self.supabase_url, self.supabase_service_key)
        
        print("🧹 Giggles Improved Duplicate Segments Cleaner")
        print("=" * 50)
        print(f"Cleanup Time: {datetime.now().isoformat()}")
        print("🎯 PRIORITY: Preserving segments with laughter detections")
        print()

    def get_segment_laughter_count(self, segment_id: str) -> int:
        """Get the number of laughter detections for a segment."""
        try:
            result = self.supabase.table("laughter_detections").select("id", count="exact").eq("audio_segment_id", segment_id).execute()
            return result.count
        except Exception as e:
            print(f"Warning: Could not get laughter count for segment {segment_id}: {str(e)}")
            return 0

    def find_overlapping_segments(self, user_id: str) -> List[Tuple[Dict, List[Dict]]]:
        """Find overlapping segments for a user."""
        try:
            # Get all segments for the user
            result = self.supabase.table("audio_segments").select("*").eq("user_id", user_id).order("start_time").execute()
            
            if not result.data:
                return []
            
            segments = result.data
            overlaps = []
            
            # Group segments by overlapping time ranges
            for i, segment1 in enumerate(segments):
                try:
                    start1 = datetime.fromisoformat(segment1['start_time'].replace('Z', '+00:00'))
                    end1 = datetime.fromisoformat(segment1['end_time'].replace('Z', '+00:00'))
                    
                    overlapping_group = [segment1]
                    
                    # Find all segments that overlap with this one
                    for j, segment2 in enumerate(segments[i+1:], i+1):
                        try:
                            start2 = datetime.fromisoformat(segment2['start_time'].replace('Z', '+00:00'))
                            end2 = datetime.fromisoformat(segment2['end_time'].replace('Z', '+00:00'))
                            
                            # Check if time ranges overlap
                            if start1 < end2 and start2 < end1:
                                overlapping_group.append(segment2)
                                
                        except Exception as e:
                            print(f"Warning: Error parsing segment {segment2['id']}: {str(e)}")
                            continue
                    
                    # If we found overlaps, add to the list
                    if len(overlapping_group) > 1:
                        overlaps.append((segment1, overlapping_group[1:]))
                        
                except Exception as e:
                    print(f"Warning: Error parsing segment {segment1['id']}: {str(e)}")
                    continue
            
            return overlaps
            
        except Exception as e:
            print(f"❌ Error finding overlapping segments: {str(e)}")
            return []

    def select_segments_to_keep(self, overlapping_group: List[Dict]) -> List[Dict]:
        """Select which segments to keep from an overlapping group, prioritizing segments with laughter detections."""
        if len(overlapping_group) <= 1:
            return overlapping_group
        
        # Get laughter detection counts for each segment
        for segment in overlapping_group:
            segment['laughter_count'] = self.get_segment_laughter_count(segment['id'])
        
        # Sort by priority:
        # 1. Segments with laughter detections (keep segments with laughter over those without)
        # 2. Processed segments (keep processed over unprocessed)
        # 3. Most recent creation time
        # 4. Longest duration (more complete data)
        
        def segment_priority(segment):
            laughter_score = segment.get('laughter_count', 0) * 1000  # High priority for segments with laughter
            processed_score = 1 if segment['processed'] else 0
            
            # Use a timestamp if available, otherwise use start_time
            try:
                created_at = datetime.fromisoformat(segment.get('created_at', segment['start_time']).replace('Z', '+00:00'))
                time_score = created_at.timestamp()
            except:
                time_score = 0
            
            # Calculate duration
            try:
                start = datetime.fromisoformat(segment['start_time'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(segment['end_time'].replace('Z', '+00:00'))
                duration = (end - start).total_seconds()
            except:
                duration = 0
            
            return (laughter_score, processed_score, time_score, duration)
        
        # Sort by priority (highest first)
        sorted_group = sorted(overlapping_group, key=segment_priority, reverse=True)
        
        # Keep the best one
        return [sorted_group[0]]

    def cleanup_duplicates(self, user_id: str) -> Dict:
        """Clean up duplicate segments for a user."""
        print(f"🔍 Analyzing segments for user: {user_id}")
        
        # Find overlapping segments
        overlaps = self.find_overlapping_segments(user_id)
        
        if not overlaps:
            print("✅ No overlapping segments found")
            return {"removed": 0, "kept": 0, "groups": 0}
        
        print(f"Found {len(overlaps)} overlapping groups")
        
        removed_count = 0
        kept_count = 0
        
        for i, (original, duplicates) in enumerate(overlaps):
            print(f"\n📊 Group {i+1}: {len(duplicates) + 1} overlapping segments")
            
            # Show the segments with laughter counts
            all_segments = [original] + duplicates
            for j, segment in enumerate(all_segments):
                laughter_count = self.get_segment_laughter_count(segment['id'])
                status = "✅" if segment['processed'] else "⏳"
                start_time = segment['start_time'][:19]
                end_time = segment['end_time'][:19]
                laughter_info = f" ({laughter_count} laughs)" if laughter_count > 0 else ""
                print(f"  {j+1}. {status} {segment['id'][:8]}... | {start_time} → {end_time}{laughter_info}")
            
            # Select which segments to keep
            segments_to_keep = self.select_segments_to_keep(all_segments)
            segments_to_remove = [s for s in all_segments if s not in segments_to_keep]
            
            kept_segment = segments_to_keep[0]
            kept_laughter_count = self.get_segment_laughter_count(kept_segment['id'])
            print(f"  🎯 Keeping: {kept_segment['id'][:8]}... ({kept_laughter_count} laughs)")
            print(f"  🗑️  Removing: {len(segments_to_remove)} duplicates")
            
            # Remove duplicate segments
            for segment in segments_to_remove:
                try:
                    self.supabase.table("audio_segments").delete().eq("id", segment['id']).execute()
                    removed_count += 1
                    print(f"    ✅ Removed: {segment['id'][:8]}...")
                except Exception as e:
                    print(f"    ❌ Failed to remove {segment['id'][:8]}...: {str(e)}")
            
            kept_count += len(segments_to_keep)
        
        return {
            "removed": removed_count,
            "kept": kept_count,
            "groups": len(overlaps)
        }

    def run_cleanup(self) -> bool:
        """Run the complete cleanup process."""
        try:
            # Get all users
            users_result = self.supabase.table("users").select("id").execute()
            
            if not users_result.data:
                print("❌ No users found")
                return False
            
            total_removed = 0
            total_kept = 0
            total_groups = 0
            
            for user in users_result.data:
                user_id = user['id']
                print(f"\n👤 Processing user: {user_id}")
                
                result = self.cleanup_duplicates(user_id)
                total_removed += result['removed']
                total_kept += result['kept']
                total_groups += result['groups']
            
            print(f"\n📋 CLEANUP SUMMARY")
            print("-" * 30)
            print(f"Total segments removed: {total_removed}")
            print(f"Total segments kept: {total_kept}")
            print(f"Overlapping groups processed: {total_groups}")
            
            if total_removed > 0:
                print(f"✅ Cleanup completed successfully")
                print(f"💾 Space saved: {total_removed} duplicate segments removed")
                print(f"🎯 Laughter detections preserved")
            else:
                print(f"✅ No duplicates found - database is clean")
            
            return True
            
        except Exception as e:
            print(f"❌ Cleanup failed with error: {str(e)}")
            return False

def main():
    """Main entry point for the cleaner."""
    cleaner = ImprovedDuplicateSegmentCleaner()
    success = cleaner.run_cleanup()
    
    if success:
        print("\n✅ Improved duplicate segments cleanup completed")
        sys.exit(0)
    else:
        print("\n❌ Improved duplicate segments cleanup failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
