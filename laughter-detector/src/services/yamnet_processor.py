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
                audio_file_path
            )
            
            logger.info(f"Found {len(laughter_events)} laughter events in {audio_file_path}")
            return laughter_events
            
        except Exception as e:
            logger.error(f"Error processing audio file: {str(e)}")
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
            logger.error(f"Error loading audio file: {str(e)}")
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
        
        Args:
            audio_data: Audio data array
            sample_rate: Sample rate of audio
            
        Returns:
            List of YAMNet predictions
        """
        try:
            if self.model is None:
                logger.warning("YAMNet model not loaded, returning empty results")
                return []
            
            # Run YAMNet model
            result = self.model(audio_data)
            scores = result[0]  # Class predictions [num_patches, num_classes]
            
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
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error in model inference: {str(e)}")
            return []
    
    async def _filter_laughter_events(
        self,
        predictions: List[YAMNetPrediction],
        audio_data: np.ndarray,
        sample_rate: int,
        original_file_path: str
    ) -> List[LaughterEvent]:
        """
        Filter predictions for laughter events and create audio clips.
        
        Args:
            predictions: YAMNet predictions
            audio_data: Original audio data
            sample_rate: Sample rate
            original_file_path: Path to original audio file
            
        Returns:
            List of laughter events with audio clips
        """
        laughter_events = []
        
        for prediction in predictions:
            # Check if this is a laughter event
            if (prediction.class_id in self.laughter_class_ids and 
                prediction.probability >= self.config.threshold):
                
                # Create audio clip around the laughter event
                clip_path = await self._create_audio_clip(
                    audio_data,
                    sample_rate,
                    prediction.timestamp,
                    original_file_path
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
        original_file_path: str
    ) -> Optional[str]:
        """
        Create audio clip around laughter timestamp.
        
        Args:
            audio_data: Audio data array
            sample_rate: Sample rate
            timestamp: Laughter timestamp in seconds
            original_file_path: Original file path for naming
            
        Returns:
            Path to created clip file, or None if failed
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
            
            # Create temporary file for clip
            base_name = os.path.splitext(os.path.basename(original_file_path))[0]
            clip_filename = f"{base_name}_laughter_{int(timestamp)}.wav"
            clip_path = os.path.join(settings.upload_dir, "clips", clip_filename)
            
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
