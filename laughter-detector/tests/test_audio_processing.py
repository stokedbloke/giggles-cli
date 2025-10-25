"""
Tests for audio processing functionality.

This module contains tests for YAMNet audio processing, laughter detection,
and audio format conversion.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import os

from src.services.yamnet_processor import YAMNetProcessor
from src.services.limitless_api import LimitlessAPIService
from src.utils.audio_utils import AudioUtils
from src.models.laughter import LaughterDetectionConfig, YAMNetPrediction


class TestYAMNetProcessor:
    """Test cases for YAMNet audio processing."""
    
    @pytest.fixture
    def yamnet_processor(self):
        """Create YAMNet processor instance for testing."""
        with patch('src.services.yamnet_processor.hub.load') as mock_load:
            mock_model = Mock()
            mock_model.class_names.numpy.return_value = [
                b'Speech', b'Laughter', b'Music', b'Silence'
            ]
            mock_load.return_value = mock_model
            
            processor = YAMNetProcessor()
            processor.model = mock_model
            return processor
    
    def test_init(self, yamnet_processor):
        """Test YAMNet processor initialization."""
        assert yamnet_processor.config.threshold == 0.3
        assert yamnet_processor.config.sample_rate == 16000
        assert yamnet_processor.config.channels == 1
        assert yamnet_processor.model is not None
    
    @pytest.mark.asyncio
    async def test_process_audio_file_success(self, yamnet_processor, mock_audio_file):
        """Test successful audio file processing."""
        with patch('src.auth.encryption.encryption_service.decrypt') as mock_decrypt:
            mock_decrypt.return_value = mock_audio_file
            
            # Mock librosa.load
            with patch('src.services.yamnet_processor.librosa.load') as mock_load:
                mock_load.return_value = (np.random.rand(16000), 16000)
                
                # Mock model inference
                with patch.object(yamnet_processor, '_run_inference') as mock_inference:
                    mock_predictions = [
                        YAMNetPrediction(
                            timestamp=1.0,
                            probability=0.85,
                            class_id=139,  # Laughter
                            class_name="Laughter"
                        )
                    ]
                    mock_inference.return_value = mock_predictions
                    
                    # Mock clip creation
                    with patch.object(yamnet_processor, '_create_audio_clip') as mock_clip:
                        mock_clip.return_value = "encrypted_clip_path"
                        
                        result = await yamnet_processor.process_audio_file(
                            "encrypted_file_path",
                            "user_id"
                        )
                        
                        assert len(result) == 1
                        assert result[0].probability == 0.85
                        assert result[0].class_id == 139
    
    @pytest.mark.asyncio
    async def test_process_audio_file_not_found(self, yamnet_processor):
        """Test audio file processing with non-existent file."""
        with patch('src.auth.encryption.encryption_service.decrypt') as mock_decrypt:
            mock_decrypt.return_value = "/nonexistent/file.wav"
            
            result = await yamnet_processor.process_audio_file(
                "encrypted_file_path",
                "user_id"
            )
            
            assert result == []
    
    def test_run_model_inference(self, yamnet_processor):
        """Test YAMNet model inference."""
        # Mock audio data
        audio_data = np.random.rand(16000)
        sample_rate = 16000
        
        # Mock model call
        mock_scores = np.array([[0.1, 0.85, 0.05], [0.2, 0.72, 0.08]])
        mock_embeddings = np.random.rand(2, 1024)
        mock_spectrogram = np.random.rand(2, 64)
        
        yamnet_processor.model.return_value = (mock_scores, mock_embeddings, mock_spectrogram)
        
        result = yamnet_processor._run_model_inference(audio_data, sample_rate)
        
        assert len(result) == 2
        assert all(isinstance(pred, YAMNetPrediction) for pred in result)
    
    def test_filter_laughter_events(self, yamnet_processor):
        """Test filtering predictions for laughter events."""
        predictions = [
            YAMNetPrediction(
                timestamp=1.0,
                probability=0.85,
                class_id=139,  # Laughter
                class_name="Laughter"
            ),
            YAMNetPrediction(
                timestamp=2.0,
                probability=0.25,
                class_id=140,  # Chuckle
                class_name="Chuckle"
            ),
            YAMNetPrediction(
                timestamp=3.0,
                probability=0.15,
                class_id=0,  # Speech
                class_name="Speech"
            )
        ]
        
        audio_data = np.random.rand(16000)
        sample_rate = 16000
        file_path = "/test/path.wav"
        
        with patch.object(yamnet_processor, '_create_audio_clip') as mock_clip:
            mock_clip.return_value = "encrypted_clip_path"
            
            result = yamnet_processor._filter_laughter_events(
                predictions, audio_data, sample_rate, file_path
            )
            
            # Should only include laughter events above threshold
            assert len(result) == 1
            assert result[0].probability == 0.85


class TestLimitlessAPIService:
    """Test cases for Limitless API integration."""
    
    @pytest.fixture
    def limitless_service(self):
        """Create Limitless API service instance for testing."""
        return LimitlessAPIService()
    
    @pytest.mark.asyncio
    async def test_validate_api_key_valid(self, limitless_service):
        """Test API key validation with valid key."""
        with patch('src.services.limitless_api.aiohttp.ClientSession') as mock_session:
            mock_response = Mock()
            mock_response.status = 200
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            result = await limitless_service.validate_api_key("valid_api_key")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_api_key_invalid(self, limitless_service):
        """Test API key validation with invalid key."""
        with patch('src.services.limitless_api.aiohttp.ClientSession') as mock_session:
            mock_response = Mock()
            mock_response.status = 401
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            result = await limitless_service.validate_api_key("invalid_api_key")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_audio_segments_success(self, limitless_service):
        """Test successful audio segments retrieval."""
        with patch.object(limitless_service, '_check_rate_limit') as mock_rate_limit:
            mock_rate_limit.return_value = False
            
            with patch.object(limitless_service, '_fetch_audio_segments') as mock_fetch:
                mock_fetch.return_value = [
                    {
                        'date': '2023-01-01T00:00:00Z',
                        'start_time': '2023-01-01T00:00:00Z',
                        'end_time': '2023-01-01T01:00:00Z',
                        'file_path': '/path/to/segment.wav'
                    }
                ]
                
                with patch('src.auth.encryption.encryption_service.encrypt') as mock_encrypt:
                    mock_encrypt.return_value = "encrypted_path"
                    
                    result = await limitless_service.get_audio_segments(
                        "api_key",
                        "2023-01-01T00:00:00Z",
                        "2023-01-01T01:00:00Z",
                        "user_id"
                    )
                    
                    assert len(result) == 1
                    assert result[0].file_path == "encrypted_path"
    
    @pytest.mark.asyncio
    async def test_get_audio_segments_rate_limit_exceeded(self, limitless_service):
        """Test audio segments retrieval with rate limit exceeded."""
        with patch.object(limitless_service, '_check_rate_limit') as mock_rate_limit:
            mock_rate_limit.return_value = True
            
            with pytest.raises(Exception):
                await limitless_service.get_audio_segments(
                    "api_key",
                    "2023-01-01T00:00:00Z",
                    "2023-01-01T01:00:00Z",
                    "user_id"
                )


class TestAudioUtils:
    """Test cases for audio utility functions."""
    
    def test_convert_to_yamnet_format(self, mock_audio_file):
        """Test audio format conversion to YAMNet format."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            with patch('src.utils.audio_utils.librosa.load') as mock_load:
                mock_load.return_value = (np.random.rand(16000), 16000)
                
                with patch('src.utils.audio_utils.sf.write') as mock_write:
                    result = AudioUtils.convert_to_yamnet_format(
                        mock_audio_file,
                        temp_path
                    )
                    
                    assert result == temp_path
                    mock_write.assert_called_once()
                    
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_validate_audio_file_valid(self, mock_audio_file):
        """Test audio file validation with valid file."""
        with patch('src.utils.audio_utils.librosa.load') as mock_load:
            mock_load.return_value = (np.random.rand(16000), 16000)
            
            result = AudioUtils.validate_audio_file(mock_audio_file)
            assert result is True
    
    def test_validate_audio_file_invalid(self):
        """Test audio file validation with invalid file."""
        with patch('src.utils.audio_utils.librosa.load') as mock_load:
            mock_load.side_effect = Exception("Invalid file")
            
            result = AudioUtils.validate_audio_file("/invalid/path.wav")
            assert result is False
    
    def test_get_audio_info(self, mock_audio_file):
        """Test getting audio file information."""
        with patch('src.utils.audio_utils.librosa.load') as mock_load:
            mock_audio_data = np.random.rand(16000)
            mock_load.return_value = (mock_audio_data, 16000)
            
            result = AudioUtils.get_audio_info(mock_audio_file)
            
            assert result['duration'] == 1.0  # 16000 samples / 16000 Hz
            assert result['sample_rate'] == 16000
            assert result['channels'] == 1
            assert result['samples'] == 16000
    
    def test_extract_audio_clip(self, mock_audio_file):
        """Test audio clip extraction."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            with patch('src.utils.audio_utils.librosa.load') as mock_load:
                mock_audio_data = np.random.rand(32000)  # 2 seconds at 16kHz
                mock_load.return_value = (mock_audio_data, 16000)
                
                with patch('src.utils.audio_utils.sf.write') as mock_write:
                    result = AudioUtils.extract_audio_clip(
                        mock_audio_file,
                        0.5,  # Start at 0.5 seconds
                        1.5,  # End at 1.5 seconds
                        temp_path
                    )
                    
                    assert result == temp_path
                    mock_write.assert_called_once()
                    
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_normalize_audio(self):
        """Test audio normalization."""
        # Test with audio data that needs normalization
        audio_data = np.array([0.5, -0.8, 1.0, -1.0])
        normalized = AudioUtils.normalize_audio(audio_data)
        
        # Check that maximum absolute value is approximately 0.95
        assert np.max(np.abs(normalized)) <= 0.95
        assert np.max(np.abs(normalized)) > 0.9
    
    def test_remove_silence(self):
        """Test silence removal from audio data."""
        # Create audio data with silence and sound
        audio_data = np.concatenate([
            np.zeros(1000),  # Silence
            np.ones(2000) * 0.5,  # Sound
            np.zeros(1000),  # Silence
            np.ones(2000) * 0.5   # Sound
        ])
        
        result = AudioUtils.remove_silence(audio_data, 16000, threshold=0.1)
        
        # Should remove silence and keep only sound segments
        assert len(result) < len(audio_data)
        assert np.all(np.abs(result) > 0.1)


class TestLaughterDetectionConfig:
    """Test cases for laughter detection configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = LaughterDetectionConfig()
        
        assert config.threshold == 0.3
        assert config.clip_duration_before == 2.0
        assert config.clip_duration_after == 2.0
        assert config.sample_rate == 16000
        assert config.channels == 1
        assert 139 in config.laughter_classes  # Laughter
        assert 140 in config.laughter_classes  # Chuckle
        assert 141 in config.laughter_classes  # Giggle
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = LaughterDetectionConfig(
            threshold=0.5,
            clip_duration_before=1.0,
            clip_duration_after=1.0,
            sample_rate=22050,
            channels=2,
            laughter_classes=[139, 140]
        )
        
        assert config.threshold == 0.5
        assert config.clip_duration_before == 1.0
        assert config.clip_duration_after == 1.0
        assert config.sample_rate == 22050
        assert config.channels == 2
        assert config.laughter_classes == [139, 140]
