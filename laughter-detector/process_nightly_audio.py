#!/usr/bin/env python3
"""
Nightly Audio Processing Script for Laughter Detection

This script runs as a cron job to process audio for all users.
It processes "yesterday" for each user based on their timezone.

Usage:
    python process_nightly_audio.py

Cron Configuration:
    # Run at 9:00 AM UTC daily (1:00 AM PST, 4:00 AM EST)
    # This ensures all US timezones have completed their previous day:
    # - PST (UTC-8): 1:00 AM = previous day is complete
    # - EST (UTC-5): 4:00 AM = previous day is complete
    # - UTC users: 9:00 AM = previous day is complete
    0 9 * * * cd /path/to/laughter-detector && source .venv/bin/activate && python process_nightly_audio.py >> /var/log/laughter_processing.log 2>&1
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Dict, Any
import pytz

# Add the src directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from supabase import Client

# Import our services
from src.services.scheduler import Scheduler, generate_time_chunks
from src.services.limitless_keys import (
    LimitlessKeyError,
    fetch_decrypted_limitless_key,
)
from src.services.supabase_client import get_service_role_client

# Load environment variables
load_dotenv()


class NightlyAudioProcessor:
    """
    Processes audio for all users during nightly runs.

    Features:
    - Processes "yesterday" for each user based on their timezone
    - Uses scheduler's existing methods (no code duplication)
    - Sequential processing for reliability
    """

    def __init__(self):
        """Initialize the processor with Supabase connection."""
        try:
            self.supabase: Client = get_service_role_client()
        except Exception as exc:
            raise RuntimeError(f"Failed to create Supabase client: {exc}") from exc

        # Initialize scheduler
        self.scheduler = Scheduler()

        print("🎭 Nightly Audio Processor initialized")
        print(f"📅 Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    async def process_all_users(self):
        """Process audio for all active users."""
        try:
            # Get all users with active Limitless API keys
            active_users = await self._get_active_users()

            if not active_users:
                print("ℹ️ No active users found with Limitless API keys")
                return

            print(f"👥 Found {len(active_users)} active users")

            total_users_processed = 0
            total_users_failed = 0

            # Process each user sequentially for reliability
            for user in active_users:
                user_email = user.get("email", "unknown")
                user_id = user["user_id"]
                print(f"\n🎯 Processing user: {user_email} ({user_id[:8]}...)")

                try:
                    await self._process_user_yesterday(user)
                    total_users_processed += 1
                    print(f"✅ User {user_email}: Processing completed successfully")

                except Exception as e:
                    total_users_failed += 1
                    print(f"❌ Error processing user {user_email}: {str(e)}")
                    import traceback

                    print(f"❌ Traceback: {traceback.format_exc()}")
                    continue

            print(f"\n🎉 Nightly processing complete!")
            print(
                f"📊 Total: {total_users_processed} users processed successfully, {total_users_failed} failed"
            )

        except Exception as e:
            print(f"❌ Fatal error in nightly processing: {str(e)}")
            import traceback

            print(f"❌ Traceback: {traceback.format_exc()}")
            raise

    async def _get_active_users(self) -> List[Dict[str, Any]]:
        """
        Get all users with active Limitless API keys.

        SECURITY: Uses service role key to bypass RLS for background job.
        This is standard practice for cron jobs that need to process all users.

        Safety measures:
        - Explicitly queries only active keys with user info
        - Only reads data, never writes user data directly
        - User data is processed through scheduler which validates user_id
        """
        try:
            result = (
                self.supabase.table("limitless_keys")
                .select("user_id, users!inner(email, timezone)")
                .eq("is_active", True)
                .execute()
            )

            if result.data:
                return [
                    {
                        "user_id": row["user_id"],
                        "email": row["users"]["email"],
                        "timezone": row["users"].get("timezone", "UTC"),
                    }
                    for row in result.data
                ]

            return []

        except Exception as e:
            print(f"❌ Error getting active users: {str(e)}")
            return []

    async def _process_user_yesterday(self, user: Dict[str, Any]):
        """
        Process "yesterday" for a specific user based on their timezone.

        This method calculates "yesterday" in the user's local timezone, then converts to UTC
        for API calls and database queries. This ensures each user's "yesterday" is correctly
        interpreted regardless of when the cron job runs.

        Example:
            Cron runs at 9 AM UTC (1 AM PST)
            User in PST (UTC-8):
            - UTC time: 9:00 AM Jan 15
            - PST time: 1:00 AM Jan 15
            - "Yesterday" for user: Jan 14, 2025 PST (00:00 → 23:59 PST)
            - UTC range: Jan 14 08:00 UTC → Jan 15 08:00 UTC

        Args:
            user: User information including user_id, email, timezone

        Database Operations:
            - Creates processing_logs entry with trigger_type='cron'
            - Stores audio_segments and laughter_detections via scheduler._process_date_range()

        Called by:
            - process_all_users() - iterates through all active users
        """
        user_id = user["user_id"]
        user_timezone = user.get("timezone", "UTC")

        # TIMEZONE-AWARE PROCESSING: Calculate "yesterday" in user's timezone
        # Example: If cron runs at 9 AM UTC and user is in PST (UTC-8):
        # - UTC time: 9:00 AM Jan 15
        # - PST time: 1:00 AM Jan 15 (previous day completed at midnight PST)
        # - "Yesterday" for user: Jan 14, 2025 PST (00:00 → 23:59 PST)
        user_tz = pytz.timezone(user_timezone)
        now_in_user_tz = datetime.now(user_tz)
        yesterday_in_user_tz = now_in_user_tz - timedelta(days=1)

        # Calculate day boundaries in user's timezone
        start_of_yesterday = yesterday_in_user_tz.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_of_yesterday = start_of_yesterday + timedelta(days=1)

        # Convert to UTC for API calls (Limitless API uses UTC, database stores UTC)
        start_of_yesterday_utc = start_of_yesterday.astimezone(pytz.UTC)
        end_of_yesterday_utc = end_of_yesterday.astimezone(pytz.UTC)

        print(f"📅 Processing yesterday for user in {user_timezone}:")
        print(f"   Local date: {start_of_yesterday.strftime('%Y-%m-%d')}")
        print(
            f"   Local range: {start_of_yesterday.strftime('%H:%M')} → {end_of_yesterday.strftime('%H:%M')}"
        )
        print(
            f"   UTC range: {start_of_yesterday_utc.strftime('%Y-%m-%d %H:%M')} → {end_of_yesterday_utc.strftime('%Y-%m-%d %H:%M')}"
        )

        # REUSE EXISTING CODE: Call scheduler's _process_date_range directly
        # This reuses all the chunking logic, enhanced logger, duplicate detection, and error handling
        # Set trigger_type to 'cron' for database constraint compliance (saves to processing_logs.trigger_type)
        # The scheduler's _process_date_range() handles:
        # - Pre-download duplicate checks (prevents wasteful OGG downloads)
        # - OGG file download from Limitless API
        # - YAMNet processing for laughter detection
        # - Three-layer duplicate prevention
        # - Enhanced logging for database tracking
        self.scheduler._trigger_type = "cron"

        try:
            try:
                api_key = fetch_decrypted_limitless_key(user_id, supabase=self.supabase)
            except LimitlessKeyError:
                print(f"⚠️ No Limitless API key found for user {user_id}")
                return
            except Exception as exc:
                print(f"❌ Failed to load Limitless API key for {user_id}: {exc}")
                return

            # Initialize enhanced logger for yesterday's date
            from src.services.enhanced_logger import get_enhanced_logger

            enhanced_logger = get_enhanced_logger(
                user_id, "cron", process_date=start_of_yesterday.date()
            )

            chunk_count = 0
            total_segments_processed = 0

            for chunk_count, (chunk_start, chunk_end) in enumerate(
                generate_time_chunks(
                    start_of_yesterday_utc, end_of_yesterday_utc, chunk_minutes=30
                ),
                start=1,
            ):
                print(
                    f"📦 Processing chunk {chunk_count}: {chunk_start.strftime('%H:%M')} UTC to {chunk_end.strftime('%H:%M')} UTC"
                )
                segments_processed = await self.scheduler._process_date_range(
                    user_id, api_key, chunk_start, chunk_end
                )
                total_segments_processed += segments_processed

            # Save processing log
            await enhanced_logger.save_to_database(
                "completed",
                f"Nightly processing completed for {start_of_yesterday.date().isoformat()}",
            )
            enhanced_logger.log_processing_summary()

            print(
                f"✅ Processed {total_segments_processed} segment(s) in {chunk_count} chunk(s)"
            )

        except Exception as e:
            print(f"❌ Error processing user audio: {str(e)}")
            import traceback

            print(f"❌ Traceback: {traceback.format_exc()}")
            raise


async def main():
    """Main entry point for the nightly processing script."""
    try:
        print("🌙 Starting nightly audio processing...")
        print("=" * 60)

        processor = NightlyAudioProcessor()
        await processor.process_all_users()

        print("=" * 60)
        print("✅ Nightly processing completed successfully")

    except Exception as e:
        print(f"❌ Fatal error in nightly processing: {str(e)}")
        import traceback

        print(f"❌ Traceback: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
