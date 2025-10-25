"""
Pytest configuration and fixtures for the laughter detector test suite.

This module provides common test fixtures and configuration for all tests.
"""

import pytest
import asyncio
import tempfile
import os
from typing import AsyncGenerator
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from src.main import app
from src.config.settings import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> TestClient:
    """
    Create a test client for the FastAPI application.
    
    Returns:
        TestClient instance
    """
    return TestClient(app)


@pytest.fixture
def temp_dir():
    """
    Create a temporary directory for test files.
    
    Returns:
        Path to temporary directory
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_auth_token():
    """
    Mock authentication token for testing.
    
    Returns:
        Mock JWT token
    """
    return "mock_jwt_token_12345"


@pytest.fixture
def mock_user_data():
    """
    Mock user data for testing.
    
    Returns:
        Dictionary with mock user data
    """
    return {
        "user_id": "test_user_123",
        "email": "test@example.com",
        "created_at": "2023-01-01T00:00:00Z"
    }


@pytest.fixture
def mock_limitless_api_key():
    """
    Mock Limitless API key for testing.
    
    Returns:
        Mock API key string
    """
    return "mock_limitless_api_key_12345"


@pytest.fixture
def mock_audio_file(temp_dir):
    """
    Create a mock audio file for testing.
    
    Args:
        temp_dir: Temporary directory fixture
        
    Returns:
        Path to mock audio file
    """
    audio_file_path = os.path.join(temp_dir, "test_audio.wav")
    
    # Create a simple mock audio file
    with open(audio_file_path, "wb") as f:
        # Write minimal WAV header + some data
        f.write(b'RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x08\x00\x00')
        f.write(b'\x00' * 2048)  # Some audio data
    
    return audio_file_path


@pytest.fixture
def mock_yamnet_predictions():
    """
    Mock YAMNet predictions for testing.
    
    Returns:
        List of mock prediction dictionaries
    """
    return [
        {
            "timestamp": 1.0,
            "probability": 0.85,
            "class_id": 139,  # Laughter class
            "class_name": "Laughter"
        },
        {
            "timestamp": 3.5,
            "probability": 0.72,
            "class_id": 140,  # Chuckle class
            "class_name": "Chuckle"
        },
        {
            "timestamp": 5.2,
            "probability": 0.45,
            "class_id": 141,  # Giggle class
            "class_name": "Giggle"
        }
    ]


@pytest.fixture
def mock_laughter_detections():
    """
    Mock laughter detection results for testing.
    
    Returns:
        List of mock detection dictionaries
    """
    return [
        {
            "id": "detection_1",
            "audio_segment_id": "segment_1",
            "timestamp": "2023-01-01T12:00:01Z",
            "probability": 0.85,
            "clip_path": "/encrypted/clip/path/1",
            "notes": "Test laughter detection"
        },
        {
            "id": "detection_2",
            "audio_segment_id": "segment_1",
            "timestamp": "2023-01-01T12:00:03Z",
            "probability": 0.72,
            "clip_path": "/encrypted/clip/path/2",
            "notes": None
        }
    ]


@pytest.fixture
def mock_daily_summary():
    """
    Mock daily summary data for testing.
    
    Returns:
        List of mock daily summary dictionaries
    """
    return [
        {
            "date": "2023-01-01T00:00:00Z",
            "total_laughs": 5,
            "laughter_detections": [
                {
                    "id": "detection_1",
                    "timestamp": "2023-01-01T12:00:01Z",
                    "probability": 0.85,
                    "notes": "Test laughter"
                }
            ]
        },
        {
            "date": "2023-01-02T00:00:00Z",
            "total_laughs": 3,
            "laughter_detections": []
        }
    ]


@pytest.fixture
def mock_encrypted_data():
    """
    Mock encrypted data for testing.
    
    Returns:
        Dictionary with mock encrypted data
    """
    return {
        "encrypted_api_key": "encrypted_key_data_12345",
        "encrypted_file_path": "encrypted_file_path_67890"
    }


@pytest.fixture
def mock_supabase_response():
    """
    Mock Supabase authentication response.
    
    Returns:
        Mock response object
    """
    mock_response = Mock()
    mock_response.user = Mock()
    mock_response.user.id = "test_user_123"
    mock_response.user.email = "test@example.com"
    mock_response.user.created_at = "2023-01-01T00:00:00Z"
    mock_response.session = Mock()
    mock_response.session.access_token = "mock_access_token"
    return mock_response


@pytest.fixture
def mock_limitless_api_response():
    """
    Mock Limitless API response.
    
    Returns:
        Mock response data
    """
    return {
        "segments": [
            {
                "date": "2023-01-01T00:00:00Z",
                "start_time": "2023-01-01T00:00:00Z",
                "end_time": "2023-01-01T01:00:00Z",
                "file_path": "/path/to/audio/segment1.wav"
            },
            {
                "date": "2023-01-01T01:00:00Z",
                "start_time": "2023-01-01T01:00:00Z",
                "end_time": "2023-01-01T02:00:00Z",
                "file_path": "/path/to/audio/segment2.wav"
            }
        ]
    }


@pytest.fixture
def mock_yamnet_model():
    """
    Mock YAMNet model for testing.
    
    Returns:
        Mock YAMNet model
    """
    mock_model = Mock()
    
    # Mock the model call
    def mock_model_call(audio_data):
        # Return mock predictions
        scores = [[0.1, 0.85, 0.05], [0.2, 0.72, 0.08], [0.15, 0.45, 0.4]]
        embeddings = [[0.1] * 1024, [0.2] * 1024, [0.3] * 1024]
        spectrogram = [[0.1] * 64, [0.2] * 64, [0.3] * 64]
        
        return scores, embeddings, spectrogram
    
    mock_model.__call__ = mock_model_call
    
    # Mock class names
    mock_model.class_names = Mock()
    mock_model.class_names.numpy.return_value = [
        b'Speech', b'Laughter', b'Music'
    ]
    
    return mock_model


@pytest.fixture
def mock_cleanup_service():
    """
    Mock cleanup service for testing.
    
    Returns:
        Mock cleanup service
    """
    mock_service = Mock()
    mock_service.secure_delete_file.return_value = True
    mock_service.cleanup_orphaned_files.return_value = 5
    mock_service.delete_user_audio_files.return_value = 10
    return mock_service


@pytest.fixture
def mock_encryption_service():
    """
    Mock encryption service for testing.
    
    Returns:
        Mock encryption service
    """
    mock_service = Mock()
    mock_service.encrypt.return_value = "encrypted_data_12345"
    mock_service.decrypt.return_value = "decrypted_data_67890"
    mock_service.secure_delete_file.return_value = True
    return mock_service


@pytest.fixture
def mock_settings():
    """
    Mock settings for testing.
    
    Returns:
        Mock settings object
    """
    mock_settings = Mock()
    mock_settings.supabase_url = "https://test.supabase.co"
    mock_settings.supabase_key = "test_supabase_key"
    mock_settings.encryption_key = "test_encryption_key_32_bytes_long"
    mock_settings.upload_dir = "/tmp/test_uploads"
    mock_settings.laughter_threshold = 0.3
    mock_settings.audio_sample_rate = 16000
    mock_settings.debug = True
    return mock_settings


# Async fixtures for testing async functions
@pytest.fixture
async def async_client():
    """
    Create an async test client for testing async endpoints.
    
    Returns:
        Async test client
    """
    from httpx import AsyncClient
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def mock_async_limitless_api():
    """
    Mock async Limitless API service for testing.
    
    Returns:
        Mock async API service
    """
    mock_service = Mock()
    mock_service.validate_api_key.return_value = True
    mock_service.get_audio_segments.return_value = []
    mock_service.get_processing_status.return_value = {"status": "active"}
    return mock_service


@pytest.fixture
async def mock_async_yamnet_processor():
    """
    Mock async YAMNet processor for testing.
    
    Returns:
        Mock async processor
    """
    mock_processor = Mock()
    mock_processor.process_audio_file.return_value = []
    return mock_processor


# Test data fixtures
@pytest.fixture
def test_user_registration_data():
    """
    Test data for user registration.
    
    Returns:
        Dictionary with test registration data
    """
    return {
        "email": "test@example.com",
        "password": "TestPass123!",
        "is_active": True,
        "mfa_enabled": False
    }


@pytest.fixture
def test_user_login_data():
    """
    Test data for user login.
    
    Returns:
        Dictionary with test login data
    """
    return {
        "email": "test@example.com",
        "password": "TestPass123!"
    }


@pytest.fixture
def test_limitless_key_data():
    """
    Test data for Limitless API key.
    
    Returns:
        Dictionary with test API key data
    """
    return {
        "api_key": "test_limitless_api_key_12345"
    }


@pytest.fixture
def test_audio_segment_data():
    """
    Test data for audio segment.
    
    Returns:
        Dictionary with test audio segment data
    """
    return {
        "date": "2023-01-01T00:00:00Z",
        "start_time": "2023-01-01T00:00:00Z",
        "end_time": "2023-01-01T01:00:00Z",
        "file_path": "/path/to/test/audio.wav",
        "processed": False
    }
