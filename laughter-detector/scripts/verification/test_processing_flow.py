#!/usr/bin/env python3
"""
Test the actual processing flow to see where the deletion fails.
"""

import os
import asyncio
from dotenv import load_dotenv
from src.services.scheduler import scheduler

load_dotenv()

async def test_processing_flow():
    """Test the actual processing flow that the web interface uses."""
    print("🧪 Testing the actual processing flow...")
    
    user_id = "d223fee9-b279-4dc7-8cd1-188dc09ccdd1"
    
    # Simulate the user object that the web interface passes
    user = {
        "user_id": user_id,
        "email": "test@example.com",
        "timezone": "America/Los_Angeles"
    }
    
    print(f"👤 Testing with user: {user_id}")
    
    try:
        print("🔍 Calling _process_user_audio method...")
        await scheduler._process_user_audio(user)
        print("✅ Processing completed")
        
    except Exception as e:
        print(f"❌ Exception during processing: {str(e)}")
        import traceback
        print(f"🔍 Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_processing_flow())
