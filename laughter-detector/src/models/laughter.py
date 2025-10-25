"""
Laughter detection specific models and constants.

This module defines models specific to laughter detection processing
and YAMNet model integration.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum


class LaughterClass(Enum):
    """YAMNet class IDs for laughter detection."""
    LAUGHTER = 139  # YAMNet class ID for laughter
    CHUCKLE = 140   # YAMNet class ID for chuckle
    GIGGLE = 141    # YAMNet class ID for giggle


class ProcessingStatus(Enum):
    """Audio processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class YAMNetPrediction(BaseModel):
    """Model for YAMNet prediction results."""
    timestamp: float
    probability: float
    class_id: int
    class_name: str


class LaughterEvent(BaseModel):
    """Model for detected laughter events."""
    timestamp: float  # Seconds from audio start
    probability: float
    class_id: int
    class_name: str
    clip_start_time: float  # Seconds from audio start
    clip_end_time: float  # Seconds from audio start
    clip_path: str


class AudioClipInfo(BaseModel):
    """Model for audio clip information."""
    clip_path: str
    start_time: datetime
    end_time: datetime
    duration: float
    sample_rate: int
    channels: int


class LaughterDetectionConfig(BaseModel):
    """Configuration for laughter detection processing."""
    threshold: float = 0.3
    clip_duration_before: float = 2.0  # seconds before laughter
    clip_duration_after: float = 2.0   # seconds after laughter
    sample_rate: int = 16000
    channels: int = 1
    laughter_classes: List[int] = [139, 140, 141]  # YAMNet laughter class IDs


class ProcessingResult(BaseModel):
    """Model for audio processing results."""
    audio_segment_id: str
    status: ProcessingStatus
    laughter_events: List[LaughterEvent]
    processing_time: float
    error_message: Optional[str] = None


class DailyProcessingSummary(BaseModel):
    """Model for daily processing summary."""
    date: datetime
    total_segments: int
    processed_segments: int
    total_laughter_events: int
    processing_time: float
    errors: List[str]
