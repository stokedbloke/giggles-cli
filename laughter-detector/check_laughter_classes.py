#!/usr/bin/env python3
"""
Check current laughter detections and their class information.
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def check_laughter_detections():
    """Check current laughter detections and their class information."""
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials in .env file")
        return
    
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        
        print("🔍 Checking laughter detections...")
        
        # Get recent detections
        result = supabase.table("laughter_detections").select("*").order("created_at", desc=True).limit(10).execute()
        
        if result.data:
            print(f"Found {len(result.data)} recent detections:")
            print()
            
            for i, detection in enumerate(result.data, 1):
                class_id = detection.get('class_id')
                class_name = detection.get('class_name')
                prob = detection.get('probability', 0)
                timestamp = detection.get('timestamp', '')
                
                print(f"{i}. ID: {detection['id'][:8]}...")
                print(f"   Class ID: {class_id}")
                print(f"   Class Name: {class_name}")
                print(f"   Probability: {prob:.3f}")
                print(f"   Timestamp: {timestamp}")
                print()
        else:
            print("No laughter detections found")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    check_laughter_detections()
