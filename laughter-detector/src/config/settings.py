"""
Application settings and configuration management.

This module handles environment variable loading and configuration validation
using Pydantic settings for type safety and validation.
"""

import os
from typing import Optional
from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation and environment variable support."""
    
    # Supabase Configuration
    supabase_url: str
    supabase_key: str
    supabase_service_role_key: str
    
    # Security Configuration
    secret_key: str
    encryption_key: str
    
    # Database Configuration
    database_url: str
    
    # Application Configuration
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: str = "http://localhost:8000"
    allowed_hosts: Optional[str] = "localhost,127.0.0.1"
    
    # File Storage Configuration
    upload_dir: str = "./uploads"
    max_file_size: int = 104857600  # 100MB
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hour
    
    # Audio Processing Configuration
    yamnet_model_url: str = "https://tfhub.dev/google/yamnet/1"
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    laughter_threshold: float = 0.1
    clip_duration: float = 4.0  # 2 seconds before and after
    
    # Cleanup Configuration
    cleanup_interval: int = 3600  # 1 hour
    max_file_age: int = 86400  # 24 hours
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = False
    
    @validator("encryption_key")
    def validate_encryption_key(cls, v):
        """Validate encryption key is 32 bytes for AES-256."""
        if len(v) != 64:  # Hex string is 64 characters for 32 bytes
            raise ValueError("Encryption key must be exactly 64 hex characters (32 bytes)")
        return v
    
    @validator("secret_key")
    def validate_secret_key(cls, v):
        """
        Validate secret key is strong enough.
        
        Args:
            v: Secret key value
            
        Returns:
            str: Validated secret key
            
        Raises:
            ValueError: If secret key is too weak
        """
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters")
        
        # Check entropy (at least 10 unique characters)
        unique_chars = len(set(v))
        if unique_chars < 10:
            raise ValueError("Secret key must have sufficient entropy (at least 10 unique characters)")
        
        return v
    
    @validator("laughter_threshold")
    def validate_laughter_threshold(cls, v):
        """Validate laughter threshold is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Laughter threshold must be between 0 and 1")
        return v
    
    @validator("upload_dir")
    def validate_upload_dir(cls, v):
        """Ensure upload directory exists."""
        os.makedirs(v, exist_ok=True)
        return v


# Global settings instance
settings = Settings()
