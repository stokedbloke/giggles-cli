"""
Limitless API integration service for audio data retrieval.

This module handles secure communication with the Limitless AI API,
including rate limiting, error handling, and incremental data retrieval.
"""

import asyncio
import aiohttp
import os
import tempfile
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, status
import pytz

from ..config.settings import settings
from ..auth.encryption import encryption_service
from ..models.audio import AudioSegment, AudioSegmentCreate



class LimitlessAPIService:
    """Service for interacting with the Limitless AI API."""
    
    def __init__(self):
        """Initialize the Limitless API service."""
        self.base_url = "https://api.limitless.ai"
        self.rate_limit_requests = settings.rate_limit_requests
        self.rate_limit_window = settings.rate_limit_window
        self.max_audio_minutes = 120  # Maximum minutes per request
    
    async def get_audio_segments(
        self, 
        api_key: str, 
        start_date: datetime, 
        end_date: datetime,
        user_id: str
    ) -> List[AudioSegmentCreate]:
        """
        Retrieve audio segments from Limitless API for a date range.
        
        Args:
            api_key: Limitless API key
            start_date: Start date for audio retrieval
            end_date: End date for audio retrieval
            user_id: User ID for tracking
            
        Returns:
            List of audio segments
            
        Raises:
            HTTPException: If API request fails or rate limit exceeded
        """
        try:
            # Check rate limits
            if await self._check_rate_limit(api_key):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="API rate limit exceeded. Please try again later."
                )
            
            # Ensure both dates are timezone-aware
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=pytz.UTC)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=pytz.UTC)
            
            # Calculate time range in minutes
            time_diff = end_date - start_date
            total_minutes = int(time_diff.total_seconds() / 60)
            
            if total_minutes > self.max_audio_minutes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Date range too large. Maximum {self.max_audio_minutes} minutes per request."
                )
            
            # Make API request
            segments = await self._fetch_audio_segments(api_key, start_date, end_date, user_id)
            
            # Process audio segments for laughter detection
            processed_segments = []
            for segment_data in segments:
                # Store plaintext file path (no encryption needed)
                segment = AudioSegmentCreate(
                    date=segment_data['date'],
                    start_time=segment_data['start_time'],
                    end_time=segment_data['end_time'],
                    file_path=segment_data['file_path']  # Store plaintext file path
                )
                processed_segments.append(segment)
            
            return processed_segments
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Error retrieving audio segments: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve audio segments"
            )
    
    async def _fetch_audio_segments(
        self, 
        api_key: str, 
        start_date: datetime, 
        end_date: datetime,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch audio segments from Limitless API.
        
        This method downloads OGG audio files from the Limitless API for a specific time range.
        The API returns binary audio data which is saved to disk in user-specific folders.
        
        API Endpoint:
            GET /v1/download-audio
            Query params: startMs, endMs (milliseconds since epoch)
            Headers: X-API-Key (API key)
        
        Response Handling:
            - 200: Success - binary OGG file data
            - 404: No audio data available (expected for time ranges with no audio)
            - 401: Invalid API key
            - 429: Rate limit exceeded
            - 502/503/504: Gateway errors (skipped, logged)
        
        File Storage:
            - Location: uploads/audio/{user_id}/{timestamp_start}-{timestamp_end}.ogg
            - Filename format: YYYYMMDD_HHMMSS-YYYYMMDD_HHMMSS.ogg
        
        Args:
            api_key: Limitless API key (decrypted)
            start_date: Start date/time (UTC, timezone-aware)
            end_date: End date/time (UTC, timezone-aware)
            user_id: User ID for folder structure and enhanced logger tracking
            
        Returns:
            List of segment data dictionaries with date, start_time, end_time, file_path
            
        Database Operations:
            - Increments enhanced_logger.audio_files_downloaded counter
            - Logs API call details (endpoint, status, duration, response size)
        """
        try:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Convert dates to ISO format for API
            start_iso = start_date.isoformat()
            end_iso = end_date.isoformat()
            
            # Use the download-audio endpoint to get audio files
            params = {
                "startMs": int(start_date.timestamp() * 1000),
                "endMs": int(end_date.timestamp() * 1000)
            }
            
            # Track API call start time and get enhanced logger
            # FIX: Added API call tracking to populate audio_files_downloaded stat
            # Previously limitless_api never called add_api_call, causing stats to be 0
            import time
            api_call_start = time.time()
            from .enhanced_logger import get_current_logger
            enhanced_logger = get_current_logger()  # May be None if not in processing context
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/v1/download-audio",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout
                ) as response:
                    # Calculate API call duration and record it
                    api_call_duration = int((time.time() - api_call_start) * 1000)  # milliseconds
                    
                    if response.status == 401:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid Limitless API key"
                        )
                    elif response.status == 429:
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Limitless API rate limit exceeded"
                        )
                    elif response.status == 404:
                        # No audio data for this time range - skip this chunk
                        # This is expected when Limitless has no audio for that window, not an error
                        print(f"⚠️ No audio data available for time range: {start_iso} to {end_iso}")
                        # Record the 404 API call for tracking (counts as failed_api_call in stats)
                        if enhanced_logger:
                            enhanced_logger.add_api_call(
                                endpoint="download-audio",
                                status_code=404,
                                duration_ms=api_call_duration,
                                response_size_bytes=0,
                                params={"startMs": params["startMs"], "endMs": params["endMs"]},
                                error="No audio data available"
                            )
                        return []
                    elif response.status in [502, 503, 504]:
                        # Gateway errors - log and skip this chunk (MVP behavior)
                        # These indicate transient Limitless API issues, not application errors
                        print(f"⚠️ Limitless API returned {response.status} for {start_iso} to {end_iso} - skipping this chunk")
                        # Record the gateway error for audit trail
                        if enhanced_logger:
                            enhanced_logger.add_api_call(
                                endpoint="download-audio",
                                status_code=response.status,
                                duration_ms=api_call_duration,
                                response_size_bytes=0,
                                params={"startMs": params["startMs"], "endMs": params["endMs"]},
                                error=f"Gateway error: {response.status}"
                            )
                        return []
                    elif response.status != 200:
                        print(f"❌ Limitless API returned status {response.status}")
                        # Record the error
                        if enhanced_logger:
                            enhanced_logger.add_api_call(
                                endpoint="download-audio",
                                status_code=response.status,
                                duration_ms=api_call_duration,
                                response_size_bytes=0,
                                params={"startMs": params["startMs"], "endMs": params["endMs"]},
                                error=f"Unexpected error: {response.status}"
                            )
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to fetch audio segments from Limitless API"
                        )
                    
                    # The response should be binary audio data (.ogg file)
                    audio_data = await response.read()
                    
                    # Record successful API call (for debugging) and increment counter
                    if enhanced_logger:
                        enhanced_logger.add_api_call(
                            endpoint="download-audio",
                            status_code=200,
                            duration_ms=api_call_duration,
                            response_size_bytes=len(audio_data) if audio_data else 0,  # OGG file size
                            params={"startMs": params["startMs"], "endMs": params["endMs"]}
                        )
                        # Increment audio files downloaded counter
                        if audio_data:  # Only count if we actually got data
                            enhanced_logger.increment_audio_files()
                    
                    # Generate filename for the audio file
                    start_ms = int(start_date.timestamp() * 1000)
                    end_ms = int(end_date.timestamp() * 1000)
                    filename = f"{start_date.strftime('%Y%m%d_%H%M%S')}-{end_date.strftime('%Y%m%d_%H%M%S')}.ogg"
                    
                    print(f"  ✅ : {len(audio_data)} bytes for {start_date.strftime('%H:%M')} to {end_date.strftime('%H:%M')}")
                    
                    # Store the audio file
                    audio_file_path = await self._store_audio_file(audio_data, user_id, filename)
                    
                    segments = []
                    if audio_file_path:
                        import uuid
                        segments.append({
                            'id': str(uuid.uuid4()),
                            'date': start_date.strftime('%Y-%m-%d'),
                            'start_time': start_date.isoformat(),
                            'end_time': end_date.isoformat(),
                            'file_path': audio_file_path
                        })
                    
                    print(f"  📁 Stored OGG: {filename}")
                    return segments
                    
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Error fetching audio segments from Limitless API: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve audio segments"
            )
        
        # Real implementation would be:
        # headers = {
        #     "Authorization": f"Bearer {api_key}",
        #     "Content-Type": "application/json"
        # }
        # 
        # params = {
        #     "start_time": start_date.isoformat(),
        #     "end_time": end_date.isoformat(),
        #     "format": "wav",
        #     "sample_rate": settings.audio_sample_rate,
        #     "channels": settings.audio_channels
        # }
        # 
        # async with aiohttp.ClientSession() as session:
        #     async with session.get(
        #         f"{self.base_url}/audio/segments",
        #         headers=headers,
        #         params=params,
        #         timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout
        #     ) as response:
        #         if response.status == 401:
        #             raise HTTPException(
        #                 status_code=status.HTTP_401_UNAUTHORIZED,
        #                 detail="Invalid API key"
        #             )
        #         elif response.status == 429:
        #             raise HTTPException(
        #                 status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        #                 detail="API rate limit exceeded"
        #             )
        #         elif response.status != 200:
        #             raise HTTPException(
        #                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #                 detail="Failed to fetch audio segments"
        #             )
        #         
        #         data = await response.json()
        #         return data.get('segments', [])
    
    async def _check_rate_limit(self, api_key: str) -> bool:
        """
        Check if API key has exceeded rate limits.
        
        Args:
            api_key: Limitless API key
            
        Returns:
            True if rate limit exceeded, False otherwise
        """
        # In a real implementation, this would check against a database
        # or cache to track API usage per key
        # For now, we'll implement a simple in-memory cache
        # TODO: Implement proper rate limiting with database storage
        return False
    
    async def validate_api_key(self, api_key: str) -> bool:
        """
        Validate Limitless API key by making a test request.
        
        Args:
            api_key: Limitless API key to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/v1/lifelogs",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return True
                    elif response.status == 401:
                        print(f"⚠️ Invalid Limitless API key provided")
                        return False
                    elif response.status == 403:
                        print(f"⚠️ Limitless API key access forbidden")
                        return False
                    else:
                        print(f"⚠️ Unexpected response from Limitless API: {response.status}")
                        return False
                    
        except aiohttp.ClientError as e:
            print(f"❌ Network error validating Limitless API key: {str(e)}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error validating Limitless API key: {str(e)}")
            return False
    
    async def get_processing_status(self, api_key: str) -> Dict[str, Any]:
        """
        Get current processing status from Limitless API.
        
        Args:
            api_key: Limitless API key
            
        Returns:
            Processing status information
        """
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/processing/status",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"status": "unknown", "message": "Unable to get status"}
                        
        except Exception as e:
            print(f"❌ Error getting processing status: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _store_audio_file(self, audio_data: bytes, user_id: str, filename: str) -> Optional[str]:
        """
        Store audio file data to local storage.
        
        Args:
            audio_data: Binary audio data (.ogg file)
            user_id: User ID for directory structure
            filename: Filename for the audio file
            
        Returns:
            Local file path if successful, None if failed
        """
        try:
            # Create user-specific directory
            user_dir = os.path.join(settings.upload_dir, "audio", user_id)
            os.makedirs(user_dir, exist_ok=True)
            
            # Generate file path
            local_path = os.path.join(user_dir, filename)
            
            # Write the audio data to file
            with open(local_path, 'wb') as f:
                f.write(audio_data)
            
            return local_path
            
        except Exception as e:
            print(f"❌ Error storing audio file: {str(e)}")
            return None

    async def _download_audio_file(self, file_url: str, user_id: str, segment_id: str) -> Optional[str]:
        """
        Download audio file from URL to local storage.
        
        Args:
            file_url: URL of the audio file to download
            user_id: User ID for directory structure
            segment_id: Segment ID for filename
            
        Returns:
            Local file path if successful, None if failed
        """
        try:
            # Create user-specific directory
            user_dir = os.path.join(settings.upload_dir, "audio", user_id)
            os.makedirs(user_dir, exist_ok=True)
            
            # Generate filename
            filename = f"{segment_id}.wav"
            local_path = os.path.join(user_dir, filename)
            
            # Download the file
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url, timeout=aiohttp.ClientTimeout(total=300)) as response:
                    if response.status == 200:
                        with open(local_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        
                        print(f"Downloaded audio file: {local_path}")
                        return local_path
                    else:
                        print(f"❌ Failed to download audio file: HTTP {response.status}")
                        return None
                        
        except Exception as e:
            print(f"❌ Error downloading audio file: {str(e)}")
            return None


# Global service instance
limitless_api_service = LimitlessAPIService()
