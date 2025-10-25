"""
Audio utility functions for format conversion and processing.

This module provides utilities for converting audio between different formats
required by the Limitless API and YAMNet model.
"""

import os
import tempfile
import logging
from typing import Optional, Tuple
import librosa
import soundfile as sf
import numpy as np

logger = logging.getLogger(__name__)


class AudioUtils:
    """Utility class for audio format conversion and processing."""
    
    @staticmethod
    def convert_to_yamnet_format(
        input_path: str, 
        output_path: Optional[str] = None,
        target_sample_rate: int = 16000,
        target_channels: int = 1
    ) -> str:
        """
        Convert audio file to YAMNet required format.
        
        Args:
            input_path: Path to input audio file
            output_path: Path for output file (optional, creates temp file if None)
            target_sample_rate: Target sample rate (default: 16000 Hz)
            target_channels: Target number of channels (default: 1 for mono)
            
        Returns:
            Path to converted audio file
            
        Raises:
            ValueError: If conversion fails
        """
        try:
            if output_path is None:
                # Create temporary file
                temp_fd, output_path = tempfile.mkstemp(
                    suffix='.wav',
                    prefix='yamnet_'
                )
                os.close(temp_fd)
            
            # Load audio with librosa
            audio_data, sample_rate = librosa.load(
                input_path,
                sr=target_sample_rate,
                mono=(target_channels == 1)
            )
            
            # Ensure correct number of channels
            if target_channels == 1 and len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            elif target_channels > 1 and len(audio_data.shape) == 1:
                audio_data = np.stack([audio_data] * target_channels, axis=1)
            
            # Save as WAV file
            sf.write(output_path, audio_data, target_sample_rate)
            
            logger.info(f"Audio converted successfully: {input_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Audio conversion failed: {str(e)}")
            raise ValueError(f"Failed to convert audio: {str(e)}")
    
    @staticmethod
    def validate_audio_file(file_path: str) -> bool:
        """
        Validate that audio file is in a supported format.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            True if file is valid, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                return False
            
            # Try to load the file with librosa
            audio_data, sample_rate = librosa.load(file_path, sr=None, mono=False)
            
            # Check if we got valid audio data
            if audio_data.size == 0:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Audio validation failed: {str(e)}")
            return False
    
    @staticmethod
    def get_audio_info(file_path: str) -> dict:
        """
        Get audio file information.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary with audio information
            
        Raises:
            ValueError: If file cannot be read
        """
        try:
            audio_data, sample_rate = librosa.load(file_path, sr=None, mono=False)
            
            duration = len(audio_data) / sample_rate
            channels = 1 if len(audio_data.shape) == 1 else audio_data.shape[0]
            
            return {
                'duration': duration,
                'sample_rate': sample_rate,
                'channels': channels,
                'samples': len(audio_data) if channels == 1 else audio_data.shape[1]
            }
            
        except Exception as e:
            logger.error(f"Failed to get audio info: {str(e)}")
            raise ValueError(f"Could not read audio file: {str(e)}")
    
    @staticmethod
    def extract_audio_clip(
        input_path: str,
        start_time: float,
        end_time: float,
        output_path: Optional[str] = None
    ) -> str:
        """
        Extract audio clip from a larger audio file.
        
        Args:
            input_path: Path to input audio file
            start_time: Start time in seconds
            end_time: End time in seconds
            output_path: Path for output clip (optional)
            
        Returns:
            Path to extracted audio clip
            
        Raises:
            ValueError: If extraction fails
        """
        try:
            if output_path is None:
                temp_fd, output_path = tempfile.mkstemp(
                    suffix='.wav',
                    prefix='clip_'
                )
                os.close(temp_fd)
            
            # Load audio
            audio_data, sample_rate = librosa.load(input_path, sr=None, mono=False)
            
            # Calculate sample indices
            start_sample = int(start_time * sample_rate)
            end_sample = int(end_time * sample_rate)
            
            # Ensure indices are within bounds
            start_sample = max(0, start_sample)
            end_sample = min(len(audio_data) if len(audio_data.shape) == 1 else audio_data.shape[1], end_sample)
            
            if start_sample >= end_sample:
                raise ValueError("Invalid time range for clip extraction")
            
            # Extract clip
            if len(audio_data.shape) == 1:
                clip_data = audio_data[start_sample:end_sample]
            else:
                clip_data = audio_data[:, start_sample:end_sample]
            
            # Save clip
            sf.write(output_path, clip_data, sample_rate)
            
            logger.info(f"Audio clip extracted: {start_time}s-{end_time}s -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Audio clip extraction failed: {str(e)}")
            raise ValueError(f"Failed to extract audio clip: {str(e)}")
    
    @staticmethod
    def normalize_audio(audio_data: np.ndarray) -> np.ndarray:
        """
        Normalize audio data to prevent clipping.
        
        Args:
            audio_data: Audio data array
            
        Returns:
            Normalized audio data
        """
        try:
            # Calculate maximum absolute value
            max_val = np.max(np.abs(audio_data))
            
            if max_val == 0:
                return audio_data
            
            # Normalize to prevent clipping
            normalized = audio_data / max_val * 0.95
            
            return normalized
            
        except Exception as e:
            logger.error(f"Audio normalization failed: {str(e)}")
            return audio_data
    
    @staticmethod
    def remove_silence(
        audio_data: np.ndarray, 
        sample_rate: int,
        threshold: float = 0.01,
        min_duration: float = 0.1
    ) -> np.ndarray:
        """
        Remove silence from audio data.
        
        Args:
            audio_data: Audio data array
            sample_rate: Sample rate of audio
            threshold: Silence threshold (default: 0.01)
            min_duration: Minimum duration of non-silent segments (default: 0.1s)
            
        Returns:
            Audio data with silence removed
        """
        try:
            # Calculate frame length for minimum duration
            frame_length = int(min_duration * sample_rate)
            
            # Find non-silent frames
            non_silent_frames = np.abs(audio_data) > threshold
            
            # Find segments longer than minimum duration
            segments = []
            start = None
            
            for i, is_non_silent in enumerate(non_silent_frames):
                if is_non_silent and start is None:
                    start = i
                elif not is_non_silent and start is not None:
                    if i - start >= frame_length:
                        segments.append((start, i))
                    start = None
            
            # Handle case where audio ends with non-silent segment
            if start is not None and len(audio_data) - start >= frame_length:
                segments.append((start, len(audio_data)))
            
            if not segments:
                # Return original audio if no non-silent segments found
                return audio_data
            
            # Concatenate non-silent segments
            result_segments = [audio_data[start:end] for start, end in segments]
            
            if len(result_segments) == 1:
                return result_segments[0]
            else:
                return np.concatenate(result_segments)
            
        except Exception as e:
            logger.error(f"Silence removal failed: {str(e)}")
            return audio_data
