#!/usr/bin/env python3
from __future__ import annotations

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

import argparse
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
from src.services.scheduler import (
    Scheduler,
    generate_time_chunks,
    DEFAULT_CHUNK_MINUTES,
)
from src.services.limitless_keys import (
    LimitlessKeyError,
    fetch_decrypted_limitless_key,
)
from src.services.supabase_client import get_service_role_client

# Load environment variables - check multiple locations (VPS uses /var/lib/giggles/.env)
env_paths = [
    Path(__file__).parent / ".env",
    Path("/var/lib/giggles/.env"),
    Path.home() / ".env",
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        print(f"📄 Loaded .env from: {env_path}")
        break
else:
    load_dotenv()  # Fallback to default behavior


class NightlyAudioProcessor:
    """
    Processes audio for all users during nightly runs.

    Features:
    - Processes "yesterday" for each user based on their timezone
    - Uses scheduler's existing methods (no code duplication)
    - Sequential processing for reliability
    """

    def __init__(
        self,
        *,
        include_user_emails: List[str] | None = None,
        include_user_ids: List[str] | None = None,
    ):
        """Initialize the processor with Supabase connection."""
        try:
            self.supabase: Client = get_service_role_client()
        except Exception as exc:
            raise RuntimeError(f"Failed to create Supabase client: {exc}") from exc

        # Initialize scheduler
        self.scheduler = Scheduler()
        self.include_user_ids = include_user_ids or []
        self.include_user_emails = include_user_emails or []
        self.email_priority = {
            email.lower(): idx for idx, email in enumerate(self.include_user_emails)
        }
        self.user_id_priority = {
            user_id: idx for idx, user_id in enumerate(self.include_user_ids)
        }

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
                finally:
                    # ========================================================================
                    # AGGRESSIVE MEMORY CLEANUP BETWEEN USERS
                    # ========================================================================
                    # Purpose: Prevent memory accumulation when processing multiple users
                    #          in a single cron job run. Without this cleanup, memory can
                    #          grow from ~700 MB to 2+ GB, causing OOM kills on 2GB VPS.
                    #
                    # Strategy: Multi-layer cleanup approach:
                    #   1. Clear TensorFlow session/graph (releases TF internal state)
                    #   2. Clear NumPy error handlers (may hold references)
                    #   3. Clear cached Supabase client (releases HTTP connections)
                    #   4. Aggressive Python GC (10x to force collection)
                    #   5. OS-level memory release (malloc_trim on Linux/macOS)
                    #
                    # Test Results: Reduces memory from ~2.4 GB peak to ~700 MB after cleanup
                    #              (70%+ reduction). Verified on multi-user test runs.
                    # ========================================================================
                    try:
                        import gc
                        import tensorflow as tf
                        import numpy as np
                        
                        # Clear TensorFlow computational graph and session state
                        # Reason: TensorFlow maintains internal state (graph, variables, buffers)
                        #         that can accumulate between users. Clearing releases this memory.
                        tf.keras.backend.clear_session()
                        tf.compat.v1.reset_default_graph()
                        
                        # Suppress NumPy warnings during cleanup
                        # Reason: NumPy may emit warnings when arrays are deleted, which
                        #         can clutter logs. Suppressing during cleanup is safe.
                        try:
                            np.seterr(all='ignore')
                        except:
                            pass  # NumPy may not be available in all environments
                        
                        # Clear scheduler's cached Supabase service client
                        # Reason: HTTP clients can hold connection pools and buffers.
                        #         Setting to None (not deleting) allows lazy re-initialization
                        #         on next access, preventing AttributeError.
                        # Fix: Changed from delattr() to = None to preserve attribute existence
                        #      for scheduler's lazy initialization pattern.
                        if hasattr(self.scheduler, '_service_client'):
                            self.scheduler._service_client = None
                        
                        # Aggressive Python garbage collection
                        # Reason: Python's GC may not run immediately. Multiple passes ensure
                        #         circular references and large objects are collected.
                        # Note: 10 passes is aggressive but necessary for TensorFlow/NumPy
                        #       objects which can have complex reference cycles.
                        for _ in range(10):
                            gc.collect()
                        
                        # Force OS-level memory release (Linux/macOS only)
                        # Reason: Python's memory allocator may not return freed memory to OS
                        #         immediately. malloc_trim() forces release back to OS.
                        # Note: This is a best-effort operation - failures are non-critical.
                        try:
                            import ctypes
                            libc = ctypes.CDLL("libc.dylib")  # macOS
                            libc.malloc_trim(0)
                        except:
                            try:
                                import ctypes
                                libc = ctypes.CDLL("libc.so.6")  # Linux
                                libc.malloc_trim(0)
                            except:
                                pass  # Not available on all systems (Windows, etc.)
                        
                        # Log memory usage after cleanup for monitoring
                        # Reason: Track effectiveness of cleanup and detect memory leaks.
                        #         Logs are used for production monitoring and debugging.
                        try:
                            import psutil
                            import os
                            process = psutil.Process(os.getpid())
                            mem_mb = process.memory_info().rss / 1024 / 1024
                            print(f"🧠 Memory after user cleanup: {mem_mb:.1f} MB")
                        except ImportError:
                            # psutil may not be installed in all environments
                            print("🧠 Memory cleanup complete (psutil not available)")
                    except Exception as cleanup_err:
                        # Non-fatal: Log error but don't fail the entire job
                        # Reason: Memory cleanup failures shouldn't prevent user processing.
                        #         Log for debugging but continue execution.
                        print(f"⚠️ Memory cleanup failed: {cleanup_err}")
                        import traceback
                        traceback.print_exc()
                    
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

            users: List[Dict[str, Any]] = []
            if result.data:
                users = [
                    {
                        "user_id": row["user_id"],
                        "email": row["users"]["email"],
                        "timezone": row["users"].get("timezone", "UTC"),
                    }
                    for row in result.data
                ]

            if self.include_user_ids:
                allowed_ids = set(self.include_user_ids)
                users = [user for user in users if user["user_id"] in allowed_ids]
            if self.include_user_emails:
                allowed_emails = set(
                    email.lower() for email in self.include_user_emails
                )
                users = [
                    user
                    for user in users
                    if user.get("email", "").lower() in allowed_emails
                ]
            if self.email_priority:
                users.sort(
                    key=lambda user: self.email_priority.get(
                        user.get("email", "").lower(), len(self.email_priority)
                    )
                )
            elif self.user_id_priority:
                users.sort(
                    key=lambda user: self.user_id_priority.get(
                        user["user_id"], len(self.user_id_priority)
                    )
                )
            else:
                users.sort(key=lambda user: user.get("email", "").lower())

            return users

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
            all_stored_clip_paths = set()  # Track clip paths created in this processing session

            for chunk_count, (chunk_start, chunk_end) in enumerate(
                generate_time_chunks(
                    start_of_yesterday_utc,
                    end_of_yesterday_utc,
                    chunk_minutes=DEFAULT_CHUNK_MINUTES,
                ),
                start=1,
            ):
                print(
                    f"📦 Processing chunk {chunk_count}: {chunk_start.strftime('%H:%M')} UTC to {chunk_end.strftime('%H:%M')} UTC"
                )
                segments_processed, chunk_clip_paths = await self.scheduler._process_date_range(
                    user_id, api_key, chunk_start, chunk_end
                )
                total_segments_processed += segments_processed
                # Accumulate clip paths created in this processing session
                # These will be excluded from orphan cleanup to prevent race condition
                all_stored_clip_paths.update(chunk_clip_paths)

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
        finally:
            # ALWAYS run orphan cleanup, even if processing failed
            # This ensures no orphaned files remain from crashed/failed processing
            try:
                now_utc = datetime.utcnow()
                start_window = now_utc - timedelta(days=2)
                # Get clip paths created in this session to exclude from cleanup
                # CRITICAL FIX: Prevents race condition where cleanup deletes files
                # that were just created but aren't visible in database query yet
                session_clip_paths = all_stored_clip_paths if 'all_stored_clip_paths' in locals() else set()
                await self.scheduler._cleanup_orphaned_files(
                    user_id, start_window, now_utc, exclude_clip_paths=session_clip_paths
                )
                print("🧹 Orphan cleanup completed")
            except Exception as cleanup_err:
                print(f"⚠️ Orphan cleanup failed (non-fatal): {str(cleanup_err)}")


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Process yesterday's audio for Giggle Gauge users."
    )
    parser.add_argument(
        "--user-email",
        action="append",
        dest="user_emails",
        default=[],
        help="Email of a user to process (can be passed multiple times to define order).",
    )
    parser.add_argument(
        "--user-id",
        action="append",
        dest="user_ids",
        default=[],
        help="User ID to process (can be passed multiple times to define order).",
    )
    return parser.parse_args()


async def main():
    """Main entry point for the nightly processing script."""
    try:
        print("🌙 Starting nightly audio processing...")
        print("=" * 60)

        args = _parse_args()
        processor = NightlyAudioProcessor(
            include_user_emails=args.user_emails, include_user_ids=args.user_ids
        )
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
