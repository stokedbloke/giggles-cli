#!/usr/bin/env python3
"""
Script to start the background scheduler for testing.
This runs the automated nightly processing scheduler.
"""

import asyncio
import logging
import signal
import sys
from src.services.scheduler import scheduler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to start the scheduler."""
    logger.info("🚀 Starting Giggles Background Scheduler...")
    
    try:
        # Start the scheduler
        await scheduler.start()
        
    except KeyboardInterrupt:
        logger.info("🛑 Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"❌ Scheduler error: {str(e)}")
    finally:
        await scheduler.stop()
        logger.info("✅ Scheduler stopped")

def signal_handler(signum, frame):
    """Handle interrupt signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the scheduler
    asyncio.run(main())
