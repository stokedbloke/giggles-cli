#!/usr/bin/env python3
"""
Duplicate Monitoring Script
===========================

This script monitors the system for duplicate laughter detections and clips,
providing alerts and statistics for production environments.

Usage:
    python3 monitor_duplicates.py [--alert-threshold 10] [--check-interval 300]

Options:
    --alert-threshold    Number of duplicates to trigger alert (default: 10)
    --check-interval     Seconds between checks (default: 300)
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from dotenv import load_dotenv
from supabase import create_client, Client
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DuplicateMonitor:
    def __init__(self, alert_threshold: int = 10):
        self.alert_threshold = alert_threshold
        
        # Load environment variables
        load_dotenv()
        
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise Exception("Supabase credentials not found")
        
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        
        logger.info(f"🔍 Duplicate Monitor initialized (alert_threshold={alert_threshold})")
    
    def check_duplicate_laughter_detections(self) -> Dict:
        """Check for duplicate laughter detections."""
        try:
            # Use the database function to detect duplicates
            result = self.supabase.rpc("detect_potential_duplicates").execute()
            
            if not result.data:
                return {"count": 0, "duplicates": []}
            
            duplicates = []
            for row in result.data:
                duplicates.append({
                    "user_id": row["user_id"],
                    "duplicate_count": row["duplicate_count"],
                    "time_range": row["time_range"],
                    "avg_probability": float(row["avg_probability"])
                })
            
            return {
                "count": len(duplicates),
                "duplicates": duplicates,
                "total_duplicate_events": sum(d["duplicate_count"] for d in duplicates)
            }
            
        except Exception as e:
            logger.error(f"Error checking duplicate laughter detections: {str(e)}")
            return {"count": 0, "duplicates": [], "error": str(e)}
    
    def check_duplicate_clip_files(self) -> Dict:
        """Check for duplicate clip files."""
        try:
            # Get all clip paths
            result = self.supabase.table("laughter_detections").select("clip_path").not_.is_("clip_path", "null").execute()
            
            if not result.data:
                return {"count": 0, "duplicates": []}
            
            # Count occurrences of each clip path
            clip_counts = {}
            for row in result.data:
                clip_path = row["clip_path"]
                if clip_path:
                    clip_counts[clip_path] = clip_counts.get(clip_path, 0) + 1
            
            # Find duplicates
            duplicates = []
            for clip_path, count in clip_counts.items():
                if count > 1:
                    duplicates.append({
                        "clip_path": clip_path,
                        "count": count
                    })
            
            return {
                "count": len(duplicates),
                "duplicates": duplicates,
                "total_duplicate_files": sum(d["count"] for d in duplicates)
            }
            
        except Exception as e:
            logger.error(f"Error checking duplicate clip files: {str(e)}")
            return {"count": 0, "duplicates": [], "error": str(e)}
    
    def check_system_health(self) -> Dict:
        """Check overall system health for duplicates."""
        logger.info("🔍 Checking system health for duplicates...")
        
        # Check laughter detection duplicates
        laughter_duplicates = self.check_duplicate_laughter_detections()
        
        # Check clip file duplicates
        clip_duplicates = self.check_duplicate_clip_files()
        
        # Calculate health score
        total_duplicates = laughter_duplicates.get("count", 0) + clip_duplicates.get("count", 0)
        health_score = max(0, 100 - (total_duplicates * 5))  # 5 points per duplicate
        
        health_status = "healthy"
        if total_duplicates > self.alert_threshold:
            health_status = "critical"
        elif total_duplicates > self.alert_threshold // 2:
            health_status = "warning"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "health_status": health_status,
            "health_score": health_score,
            "total_duplicates": total_duplicates,
            "laughter_duplicates": laughter_duplicates,
            "clip_duplicates": clip_duplicates,
            "alert_threshold": self.alert_threshold
        }
    
    def send_alert(self, health_data: Dict):
        """Send alert if duplicates exceed threshold."""
        if health_data["health_status"] == "critical":
            logger.error(f"🚨 CRITICAL: {health_data['total_duplicates']} duplicates detected (threshold: {self.alert_threshold})")
            
            # Log detailed information
            if health_data["laughter_duplicates"]["count"] > 0:
                logger.error(f"   Laughter detection duplicates: {health_data['laughter_duplicates']['count']}")
                for dup in health_data["laughter_duplicates"]["duplicates"][:5]:  # Show first 5
                    logger.error(f"     User {dup['user_id']}: {dup['duplicate_count']} duplicates in {dup['time_range']}")
            
            if health_data["clip_duplicates"]["count"] > 0:
                logger.error(f"   Clip file duplicates: {health_data['clip_duplicates']['count']}")
                for dup in health_data["clip_duplicates"]["duplicates"][:5]:  # Show first 5
                    logger.error(f"     {dup['clip_path']}: {dup['count']} occurrences")
        
        elif health_data["health_status"] == "warning":
            logger.warning(f"⚠️  WARNING: {health_data['total_duplicates']} duplicates detected (threshold: {self.alert_threshold})")
    
    def run_monitoring_cycle(self):
        """Run one monitoring cycle."""
        try:
            health_data = self.check_system_health()
            
            # Log health status
            logger.info(f"📊 System Health: {health_data['health_status'].upper()} (Score: {health_data['health_score']}/100)")
            logger.info(f"   Total duplicates: {health_data['total_duplicates']}")
            logger.info(f"   Laughter duplicates: {health_data['laughter_duplicates']['count']}")
            logger.info(f"   Clip duplicates: {health_data['clip_duplicates']['count']}")
            
            # Send alerts if needed
            self.send_alert(health_data)
            
            # Save health data to file for external monitoring
            health_file = "/tmp/giggles_duplicate_health.json"
            with open(health_file, "w") as f:
                json.dump(health_data, f, indent=2)
            
            return health_data
            
        except Exception as e:
            logger.error(f"❌ Monitoring cycle failed: {str(e)}")
            return None
    
    def run_continuous_monitoring(self, check_interval: int = 300):
        """Run continuous monitoring."""
        logger.info(f"🔄 Starting continuous monitoring (interval: {check_interval}s)")
        
        while True:
            try:
                self.run_monitoring_cycle()
                time.sleep(check_interval)
            except KeyboardInterrupt:
                logger.info("🛑 Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Monitoring error: {str(e)}")
                time.sleep(check_interval)

def main():
    parser = argparse.ArgumentParser(description="Monitor for duplicate laughter detections and clips")
    parser.add_argument("--alert-threshold", type=int, default=10, help="Number of duplicates to trigger alert")
    parser.add_argument("--check-interval", type=int, default=300, help="Seconds between checks")
    parser.add_argument("--once", action="store_true", help="Run once instead of continuously")
    
    args = parser.parse_args()
    
    try:
        monitor = DuplicateMonitor(alert_threshold=args.alert_threshold)
        
        if args.once:
            monitor.run_monitoring_cycle()
        else:
            monitor.run_continuous_monitoring(args.check_interval)
            
    except Exception as e:
        logger.error(f"❌ Monitor failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
