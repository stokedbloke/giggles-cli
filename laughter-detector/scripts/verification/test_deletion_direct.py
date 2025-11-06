#!/usr/bin/env python3
"""
Direct test of the audio deletion method to isolate the bug.
"""

import os
import asyncio
from dotenv import load_dotenv
from src.services.scheduler import scheduler

load_dotenv()

async def test_deletion():
    """Test the deletion method directly."""
    print("🧪 Testing audio deletion method directly...")
    
    # Get the first audio file
    audio_dir = "uploads/audio/d223fee9-b279-4dc7-8cd1-188dc09ccdd1"
    files = [f for f in os.listdir(audio_dir) if f.endswith('.ogg')]
    
    if not files:
        print("❌ No audio files found to test")
        return
    
    test_file = os.path.join(audio_dir, files[0])
    print(f"🎯 Testing deletion of: {test_file}")
    print(f"📁 File exists: {os.path.exists(test_file)}")
    
    if os.path.exists(test_file):
        file_size = os.path.getsize(test_file)
        print(f"📊 File size: {file_size} bytes")
    
    # Test the deletion method directly
    user_id = "d223fee9-b279-4dc7-8cd1-188dc09ccdd1"
    
    try:
        print("🔍 Calling _delete_audio_file method...")
        await scheduler._delete_audio_file(test_file, user_id)
        print("✅ Deletion method completed")
        
        # Check if file still exists
        if os.path.exists(test_file):
            print("❌ File still exists after deletion attempt")
        else:
            print("✅ File successfully deleted!")
            
    except Exception as e:
        print(f"❌ Exception during deletion: {str(e)}")
        import traceback
        print(f"🔍 Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_deletion())
