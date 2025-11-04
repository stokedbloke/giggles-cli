"""
Audio processing data models for laughter detection.

This module defines Pydantic models for audio segments and laughter detection
results with proper validation and type safety.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, validator, Field
from sqlalchemy import Column, String, DateTime, Float, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class AudioSegmentBase(BaseModel):
    """Base model for audio segments."""
    date: datetime
    start_time: datetime
    end_time: datetime
    processed: bool = False


class AudioSegmentCreate(AudioSegmentBase):
    """Model for creating audio segments."""
    file_path: str
    
    @validator('end_time')
    def validate_time_range(cls, v, values):
        """Validate that end_time is after start_time."""
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v


class AudioSegmentResponse(AudioSegmentBase):
    """Model for audio segment responses."""
    id: str
    user_id: str
    file_path: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class LaughterDetectionBase(BaseModel):
    """Base model for laughter detection results."""
    timestamp: datetime
    probability: float
    notes: Optional[str] = None


class LaughterDetectionCreate(LaughterDetectionBase):
    """Model for creating laughter detection records."""
    audio_segment_id: str
    clip_path: str
    class_id: Optional[int] = None
    class_name: Optional[str] = None
    
    @validator('probability')
    def validate_probability(cls, v):
        """Validate probability is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError('Probability must be between 0 and 1')
        return v


class LaughterDetectionResponse(LaughterDetectionBase):
    """Model for laughter detection responses."""
    id: str
    audio_segment_id: str
    clip_path: str
    class_id: Optional[int] = None
    class_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class LaughterDetectionUpdate(BaseModel):
    """Model for updating laughter detection records."""
    notes: Optional[str] = Field(None, max_length=1000, description="User notes about the laughter detection")
    
    @validator('notes')
    def validate_notes(cls, v):
        """
        Validate notes field.
        
        Args:
            v: Notes value
            
        Returns:
            str: Validated notes
            
        Raises:
            ValueError: If notes exceed maximum length
        """
        if v is not None and len(v) > 1000:
            raise ValueError("Notes must be less than 1000 characters")
        return v


class DailyLaughterSummary(BaseModel):
    """Model for daily laughter summary."""
    date: str
    total_laughter_events: int
    average_probability: float
    audio_segments_processed: int


class AudioProcessingStatus(BaseModel):
    """Model for audio processing status."""
    status: str  # "processing", "completed", "failed"
    message: Optional[str] = None
    processed_segments: int = 0
    total_segments: int = 0
    last_processed: Optional[datetime] = None


class ReprocessDateRangeRequest(BaseModel):
    """Model for reprocess date range request."""
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    
    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        """Validate date format is YYYY-MM-DD."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')


# SQLAlchemy Models
class AudioSegment(Base):
    """SQLAlchemy model for audio segments table."""
    __tablename__ = "audio_segments"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    file_path = Column(String, nullable=False)  # Encrypted file path
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class LaughterDetection(Base):
    """SQLAlchemy model for laughter detection results table."""
    __tablename__ = "laughter_detections"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    audio_segment_id = Column(String, ForeignKey("audio_segments.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    probability = Column(Float, nullable=False)
    clip_path = Column(String, nullable=False)  # Encrypted file path
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
