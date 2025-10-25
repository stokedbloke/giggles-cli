#!/usr/bin/env python3
"""
Data Integrity Monitor for Giggles Application

This script runs the data integrity test and tracks changes over time.
It can be run periodically to monitor cleanup and file management fixes.

SECURITY: This script only READS data - it never modifies anything.
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

def run_integrity_test():
    """Run the data integrity test and return results."""
    try:
        result = subprocess.run([
            sys.executable, 'test_data_integrity.py'
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e)
        }

def load_historical_data():
    """Load historical test results."""
    history_file = Path(__file__).parent / "data_integrity_history.json"
    
    if history_file.exists():
        try:
            with open(history_file, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_historical_data(history):
    """Save historical test results."""
    history_file = Path(__file__).parent / "data_integrity_history.json"
    
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)

def analyze_trends(history):
    """Analyze trends in the data integrity issues."""
    if len(history) < 2:
        return "Not enough data for trend analysis"
    
    print("\n📈 TREND ANALYSIS")
    print("-" * 30)
    
    # Get latest and previous results
    latest = history[-1]
    previous = history[-2]
    
    # Compare issue counts
    latest_issues = latest.get('issues_found', 0)
    previous_issues = previous.get('issues_found', 0)
    
    if latest_issues < previous_issues:
        print(f"✅ IMPROVEMENT: Issues decreased from {previous_issues} to {latest_issues}")
    elif latest_issues > previous_issues:
        print(f"❌ REGRESSION: Issues increased from {previous_issues} to {latest_issues}")
    else:
        print(f"➡️  STABLE: Issues remain at {latest_issues}")
    
    # Compare specific metrics
    latest_db = latest.get('database_counts', {})
    previous_db = previous.get('database_counts', {})
    
    # Audio segments trend
    latest_segments = latest_db.get('audio_segments', 0)
    previous_segments = previous_db.get('audio_segments', 0)
    if latest_segments != previous_segments:
        print(f"📊 Audio segments: {previous_segments} → {latest_segments}")
    
    # Laughter detections trend
    latest_detections = latest_db.get('laughter_detections', 0)
    previous_detections = previous_db.get('laughter_detections', 0)
    if latest_detections != previous_detections:
        print(f"📊 Laughter detections: {previous_detections} → {latest_detections}")
    
    # File counts trend
    latest_fs = latest.get('filesystem_counts', {})
    previous_fs = previous.get('filesystem_counts', {})
    
    latest_audio_files = latest_fs.get('audio_files', 0)
    previous_audio_files = previous_fs.get('audio_files', 0)
    if latest_audio_files != previous_audio_files:
        print(f"📁 Audio files: {previous_audio_files} → {latest_audio_files}")
    
    latest_clips = latest_fs.get('laughter_clips', 0)
    previous_clips = previous_fs.get('laughter_clips', 0)
    if latest_clips != previous_clips:
        print(f"📁 Laughter clips: {previous_clips} → {latest_clips}")

def main():
    """Main monitoring function."""
    print("🔍 Giggles Data Integrity Monitor")
    print("=" * 50)
    print(f"Monitor Time: {datetime.now().isoformat()}")
    print()
    
    # Run the integrity test
    print("Running data integrity test...")
    result = run_integrity_test()
    
    if not result['success']:
        print("❌ Integrity test failed")
        print("STDOUT:", result['stdout'])
        print("STDERR:", result['stderr'])
        sys.exit(1)
    
    # Load historical data
    history = load_historical_data()
    
    # Parse current results
    try:
        report_file = Path(__file__).parent / "data_integrity_report.json"
        with open(report_file, 'r') as f:
            current_data = json.load(f)
    except:
        print("❌ Could not load current test results")
        sys.exit(1)
    
    # Add to history
    history.append(current_data)
    
    # Keep only last 10 results
    if len(history) > 10:
        history = history[-10:]
    
    # Save updated history
    save_historical_data(history)
    
    # Show current status
    print("📊 CURRENT STATUS")
    print("-" * 30)
    print(f"Issues Found: {current_data.get('issues_found', 0)}")
    print(f"Data Consistency: {current_data.get('summary', {}).get('data_consistency', 'UNKNOWN')}")
    
    if current_data.get('issues'):
        print("\nCurrent Issues:")
        for i, issue in enumerate(current_data['issues'], 1):
            print(f"  {i}. {issue}")
    
    # Show trends
    if len(history) > 1:
        analyze_trends(history)
    
    # Show recommendations
    print("\n💡 RECOMMENDATIONS")
    print("-" * 30)
    
    issues = current_data.get('issues', [])
    if not issues:
        print("✅ No issues found - system is healthy!")
    else:
        if any("Audio Segments" in issue for issue in issues):
            print("🔧 Fix file deletion after processing")
        if any("clip ratio" in issue for issue in issues):
            print("🔧 Fix clip over-generation")
        if any("Files still exist" in issue for issue in issues):
            print("🔧 Implement proper cleanup after YAMNet processing")
    
    print(f"\n📄 Full report: {report_file}")
    print(f"📈 History: {Path(__file__).parent / 'data_integrity_history.json'}")
    
    # Exit with appropriate code
    if current_data.get('issues_found', 0) == 0:
        print("\n✅ Monitor completed - system healthy")
        sys.exit(0)
    else:
        print(f"\n⚠️  Monitor completed - {current_data.get('issues_found', 0)} issues found")
        sys.exit(1)

if __name__ == "__main__":
    main()
