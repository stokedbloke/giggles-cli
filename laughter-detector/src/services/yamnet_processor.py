"""
YAMNet audio processing service for laughter detection.

This module handles audio processing using TensorFlow Hub's YAMNet model
to detect laughter events with timestamps and probability scores.
"""

import os
import tempfile
import asyncio
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
import librosa
import soundfile as sf
import logging

from ..config.settings import settings
from ..models.laughter import (
    LaughterEvent, 
    YAMNetPrediction, 
    LaughterDetectionConfig,
    LaughterClass
)
from ..auth.encryption import encryption_service

logger = logging.getLogger(__name__)


class YAMNetProcessor:
    """Service for processing audio with YAMNet model."""
    
    def __init__(self):
        """Initialize YAMNet model and processing configuration."""
        self.model_url = settings.yamnet_model_url
        self.model = None
        self.config = LaughterDetectionConfig(
            threshold=settings.laughter_threshold,
            clip_duration_before=settings.clip_duration / 2,
            clip_duration_after=settings.clip_duration / 2,
            sample_rate=settings.audio_sample_rate,
            channels=settings.audio_channels
        )
        self._load_model()
    
    def _load_model(self):
        """Load YAMNet model from TensorFlow Hub."""
        try:
            # Limit TensorFlow memory growth to prevent OOM kills on small VPS
            # Only allocate GPU memory as needed
            gpus = tf.config.experimental.list_physical_devices('GPU')
            if gpus:
                try:
                    for gpu in gpus:
                        tf.config.experimental.set_memory_growth(gpu, True)
                except RuntimeError as e:
                    print(f"⚠️ Error setting GPU memory growth: {e}")
            
            # For CPU, limit thread pool size to reduce memory usage
            # This helps on 2GB VPS systems by using fewer threads
            # Note: TensorFlow doesn't support memory limits for CPU, so we rely on:
            # 1. Thread limits (reduces parallel memory usage)
            # 2. Explicit garbage collection after each file
            # 3. Clearing TensorFlow sessions between files
            tf.config.threading.set_intra_op_parallelism_threads(1)
            tf.config.threading.set_inter_op_parallelism_threads(1)
            
            # Load YAMNet model from TensorFlow Hub
            self.model = hub.load(self.model_url)
            
            # Load class names from YAMNet repository
            import requests
            class_map_url = 'https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv'
            response = requests.get(class_map_url)
            
            if response.status_code == 200:
                lines = response.text.strip().split('\n')
                self.class_names = []
                for line in lines[1:]:  # Skip header
                    parts = line.split(',')
                    if len(parts) >= 3:
                        self.class_names.append(parts[2].strip('"'))
                
                # Define laughter-related class IDs based on YAMNet class map
                self.laughter_class_ids = [13, 14, 15, 17, 18]  # Laughter, Baby laughter, Giggle, Belly laugh, Chuckle
                
                logger.info(f"YAMNet model loaded successfully with {len(self.class_names)} classes")
                logger.info(f"Found {len(self.laughter_class_ids)} laughter-related classes: {[self.class_names[i] for i in self.laughter_class_ids]}")
            else:
                raise Exception("Failed to load class names")
            
        except Exception as e:
            logger.error(f"Failed to load YAMNet model: {str(e)}")
            # For now, create a mock model to avoid crashes
            logger.warning("Using mock YAMNet model - install TensorFlow Hub to enable real laughter detection")
            self.model = None
            self.class_names = []
            self.laughter_class_ids = []
    
    async def process_audio_file(
        self, 
        audio_file_path: str, 
        user_id: str
    ) -> List[LaughterEvent]:
        """
        Process audio file to detect laughter events.
        
        Args:
            audio_file_path: Path to audio file (encrypted)
            user_id: User ID for file path decryption
            
        Returns:
            List of detected laughter events
        """
        try:
            logger.info(f"🎭 Starting YAMNet processing for user {user_id}")
            
            # Use plaintext file path (no decryption needed)
            if not os.path.exists(audio_file_path):
                logger.error(f"Audio file not found: {audio_file_path}")
                return []
            
            logger.info(f"📁 Loading audio file: {os.path.basename(audio_file_path)}")
            
            # Load and preprocess audio
            audio_data, sample_rate = await self._load_audio(audio_file_path)
            logger.info(f"🎵 Audio loaded: {len(audio_data)} samples at {sample_rate}Hz")
            
            # Run YAMNet inference
            logger.info("🧠 Running YAMNet inference...")
            predictions = await self._run_inference(audio_data, sample_rate)
            
                        # Filter for laughter events
            laughter_events = await self._filter_laughter_events(
                predictions, 
                audio_data, 
                sample_rate, 
                audio_file_path,
                user_id  # Pass user_id for user-specific folder structure
            )
            
            logger.info(f"Found {len(laughter_events)} laughter events in {audio_file_path}")
            
            # AGGRESSIVE memory cleanup after processing each file
            # This is critical on 2GB VPS to prevent OOM kills
            # Delete large arrays AFTER all processing is complete
            import gc
            
            # Delete large audio data arrays explicitly (now safe - all processing done)
            del audio_data
            del predictions
            
            # Force garbage collection multiple times
            for _ in range(3):
                gc.collect()
            
            return laughter_events
            
        except Exception as e:
            import traceback
            error_msg = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
            print(f"❌ Error processing audio file: {error_msg}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            
            # Clear memory even on error
            try:
                import gc
                gc.collect()
            except:
                pass
            
            return []
    
    async def _load_audio(self, file_path: str) -> Tuple[np.ndarray, int]:
        """
        Load audio file and convert to required format.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Tuple of (audio_data, sample_rate)
        """
        try:
            # Load audio with librosa
            audio_data, sample_rate = librosa.load(
                file_path,
                sr=self.config.sample_rate,
                mono=True
            )
            
            # Ensure audio is in the correct format
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            return audio_data, sample_rate
            
        except Exception as e:
            import traceback
            error_msg = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
            print(f"❌ Error loading audio file: {error_msg}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            raise
    
    async def _run_inference(
        self, 
        audio_data: np.ndarray, 
        sample_rate: int
    ) -> List[YAMNetPrediction]:
        """
        Run YAMNet inference on audio data.
        
        Args:
            audio_data: Audio data array
            sample_rate: Sample rate of audio
            
        Returns:
            List of YAMNet predictions
        """
        try:
            # Run inference in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            predictions = await loop.run_in_executor(
                None, 
                self._run_model_inference, 
                audio_data, 
                sample_rate
            )
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error running inference: {str(e)}")
            return []
    
    def _run_model_inference(
        self, 
        audio_data: np.ndarray, 
        sample_rate: int
    ) -> List[YAMNetPrediction]:
        """
        Run YAMNet model inference (synchronous).
        
        YAMNet processes audio in patches of 0.48 seconds (patch_duration). Each patch
        produces probability scores for 521 audio classes. We filter for laughter-related
        classes (class_ids: 13, 14, 15, 17, 18) that exceed the threshold.
        
        Laughter Classes:
            - 13: Laughter
            - 14: Baby laughter
            - 15: Giggle
            - 17: Belly laugh
            - 18: Chuckle
        
        Args:
            audio_data: Audio data array (mono, 16kHz sample rate)
            sample_rate: Sample rate (must be 16000 Hz for YAMNet)
            
        Returns:
            List of YAMNetPrediction objects with timestamp, probability, class_id, class_name
            
        Note: This runs synchronously in a thread pool executor to avoid blocking the event loop
        """
        try:
            if self.model is None:
                logger.warning("YAMNet model not loaded, returning empty results")
                return []
            
            # Limit audio length to prevent OOM (max 2 hours = 7200 seconds at 16kHz = 115,200,000 samples)
            # Process in chunks if audio is too long
            max_samples = 115200000  # 2 hours max
            if len(audio_data) > max_samples:
                logger.warning(f"Audio file too long ({len(audio_data)} samples), truncating to {max_samples} samples")
                audio_data = audio_data[:max_samples]
            
            # Run YAMNet model
            result = self.model(audio_data)
            scores = result[0]  # Class predictions [num_patches, num_classes]
            
            # CRITICAL: Delete audio_data immediately after inference to free memory
            # The audio_data array can be 400-500MB, so delete it ASAP
            del audio_data
            import gc
            gc.collect()
            
            predictions = []
            patch_duration = 0.48  # YAMNet patch hop duration in seconds
            
            for patch_idx in range(scores.shape[0]):
                patch_scores = scores[patch_idx]
                
                # Check each laughter class
                for class_id in self.laughter_class_ids:
                    # Convert tensor to float for comparison
                    score = float(patch_scores[class_id])
                    if score > self.config.threshold:
                        predictions.append(YAMNetPrediction(
                            timestamp=float(patch_idx * patch_duration),
                            probability=score,
                            class_id=class_id,
                            class_name=self.class_names[class_id] if class_id < len(self.class_names) else f"Class_{class_id}"
                        ))
            
            # Delete scores tensor to free memory
            del scores
            del result
            gc.collect()
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error in model inference: {str(e)}")
            return []
    
    async def _filter_laughter_events(
        self,
        predictions: List[YAMNetPrediction],
        audio_data: np.ndarray,
        sample_rate: int,
        original_file_path: str,
        user_id: str
    ) -> List[LaughterEvent]:
        """
        Filter predictions for laughter events and create audio clips.
        
        Args:
            predictions: YAMNet predictions
            audio_data: Original audio data
            sample_rate: Sample rate
            original_file_path: Path to original audio file
            user_id: User ID for user-specific folder structure
            
        Returns:
            List of laughter events with audio clips
        """
        laughter_events = []
        
        for prediction in predictions:
            # Check if this is a laughter event
            if (prediction.class_id in self.laughter_class_ids and 
                prediction.probability >= self.config.threshold):
                
                # Create audio clip around the laughter event
                # CRITICAL: Pass class_id to ensure unique filenames for same timestamp but different classes
                # (e.g., Laughter class_id=13 and Giggle class_id=15 at same timestamp need different filenames)
                clip_path = await self._create_audio_clip(
                    audio_data,
                    sample_rate,
                    prediction.timestamp,
                    prediction.class_id,  # Include class_id for unique filenames
                    original_file_path,
                    user_id  # Pass user_id for user-specific folder structure
                )
                
                if clip_path:
                    # Calculate clip timing
                    clip_start_time = prediction.timestamp - self.config.clip_duration_before
                    clip_end_time = prediction.timestamp + self.config.clip_duration_after
                    
                    # Create laughter event
                    event = LaughterEvent(
                        timestamp=prediction.timestamp,  # Keep as float (seconds from audio start)
                        probability=prediction.probability,
                        class_id=prediction.class_id,
                        class_name=prediction.class_name,
                        clip_start_time=clip_start_time,  # Keep as float
                        clip_end_time=clip_end_time,  # Keep as float
                        clip_path=clip_path
                    )
                    
                    laughter_events.append(event)
        
        return laughter_events
    
    async def _create_audio_clip(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        timestamp: float,
        class_id: int,
        original_file_path: str,
        user_id: str
    ) -> Optional[str]:
        """
        Create audio clip around laughter timestamp.
        
        This method extracts a 4-second clip (2 seconds before + 2 seconds after) around the
        detected laughter timestamp. The filename includes the class_id to ensure uniqueness
        when multiple laughter types are detected at the same timestamp.
        
        Filename Format:
            {base_name}_laughter_{timestamp_str}_{class_id}.wav
            Example: 20251024_130000-20251024_150000_laughter_2708-64_13.wav
            - base_name: Original OGG filename (without .ogg extension)
            - timestamp_str: Timestamp in seconds, formatted as "2708-64" (replaces . with -)
            - class_id: YAMNet class ID (13=Laughter, 15=Giggle, etc.)
        
        File Location:
            uploads/clips/{user_id}/filename.wav (user-specific folder structure)
        
        Args:
            audio_data: Full audio data array from OGG file
            sample_rate: Sample rate (16000 Hz for YAMNet)
            timestamp: Laughter timestamp in seconds (relative to audio start)
            class_id: YAMNet class ID for this detection (ensures unique filenames)
            original_file_path: Original OGG file path (used for base filename)
            user_id: User ID for folder structure
            
        Returns:
            Path to created clip file (relative to project root), or None if failed
            
        Called by:
            - _filter_laughter_events() - for each detected laughter event
        """
        try:
            # Calculate clip boundaries
            start_sample = int((timestamp - self.config.clip_duration_before) * sample_rate)
            end_sample = int((timestamp + self.config.clip_duration_after) * sample_rate)
            
            # Ensure boundaries are within audio data
            start_sample = max(0, start_sample)
            end_sample = min(len(audio_data), end_sample)
            
            if start_sample >= end_sample:
                return None
            
            # Extract clip
            clip_data = audio_data[start_sample:end_sample]
            
            # Create filename with class_id to ensure uniqueness
            # CRITICAL FIX: Include class_id in filename to prevent collisions when multiple
            # laughter types are detected at the same timestamp (e.g., Laughter class_id=13
            # and Giggle class_id=15). Without this, int(timestamp) causes filename collisions.
            # Format: {base_name}_laughter_{timestamp_str}_{class_id}.wav
            # Example: 20251024_130000-20251024_150000_laughter_2708-64_13.wav
            base_name = os.path.splitext(os.path.basename(original_file_path))[0]
            # Use timestamp with 2 decimal places (YAMNet patch_duration=0.48s, so .2f is sufficient)
            # Replace decimal point with hyphen to avoid filesystem issues
            timestamp_str = f"{timestamp:.2f}".replace(".", "-")
            # Include class_id as suffix to ensure uniqueness
            clip_filename = f"{base_name}_laughter_{timestamp_str}_{class_id}.wav"
            
            # FOLDER STRUCTURE: Store clips in user-specific folders (consistent with audio files)
            # This ensures clips are organized per-user for easier cleanup and management
            # Format: uploads/clips/{user_id}/filename.wav (matches uploads/audio/{user_id}/filename.ogg)
            clip_path = os.path.join(settings.upload_dir, "clips", user_id, clip_filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(clip_path), exist_ok=True)
            
            # Save clip
            sf.write(clip_path, clip_data, sample_rate)
            
            # Return plaintext clip path (no encryption needed)
            return clip_path
            
        except Exception as e:
            logger.error(f"Error creating audio clip: {str(e)}")
            return None


# Global processor instance
yamnet_processor = YAMNetProcessor()
