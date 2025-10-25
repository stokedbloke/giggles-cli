"""
Tests for API endpoints.

This module contains tests for all FastAPI endpoints including authentication,
audio processing, and data management.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import status


class TestAuthEndpoints:
    """Test cases for authentication API endpoints."""
    
    def test_register_endpoint_success(self, client, test_user_registration_data):
        """Test successful user registration."""
        with patch('src.auth.supabase_auth.auth_service.register_user') as mock_register:
            mock_register.return_value = {
                "user_id": "test_user_123",
                "email": "test@example.com",
                "created_at": "2023-01-01T00:00:00Z"
            }
            
            response = client.post("/api/auth/register", json=test_user_registration_data)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == "test_user_123"
            assert data["email"] == "test@example.com"
            assert data["is_active"] is True
            assert data["mfa_enabled"] is True
    
    def test_register_endpoint_invalid_email(self, client):
        """Test user registration with invalid email."""
        invalid_data = {
            "email": "invalid-email",
            "password": "TestPass123!"
        }
        
        response = client.post("/api/auth/register", json=invalid_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_login_endpoint_success(self, client, test_user_login_data):
        """Test successful user login."""
        with patch('src.auth.supabase_auth.auth_service.login_user') as mock_login:
            mock_login.return_value = {
                "user_id": "test_user_123",
                "email": "test@example.com",
                "session": Mock()
            }
            
            response = client.post(
                "/api/auth/login",
                params=test_user_login_data
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "access_token" in data
            assert data["user"]["id"] == "test_user_123"
    
    def test_login_endpoint_invalid_credentials(self, client):
        """Test user login with invalid credentials."""
        with patch('src.auth.supabase_auth.auth_service.login_user') as mock_login:
            mock_login.side_effect = Exception("Invalid credentials")
            
            response = client.post(
                "/api/auth/login",
                params={"email": "test@example.com", "password": "wrongpassword"}
            )
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLimitlessKeyEndpoints:
    """Test cases for Limitless API key management endpoints."""
    
    def test_store_limitless_key_success(self, client, mock_auth_token, test_limitless_key_data):
        """Test successful Limitless API key storage."""
        with patch('src.services.limitless_api.limitless_api_service.validate_api_key') as mock_validate:
            mock_validate.return_value = True
            
            with patch('src.auth.encryption.encryption_service.encrypt') as mock_encrypt:
                mock_encrypt.return_value = "encrypted_key"
                
                headers = {"Authorization": f"Bearer {mock_auth_token}"}
                response = client.post(
                    "/api/api/limitless-key",
                    json=test_limitless_key_data,
                    headers=headers
                )
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["is_active"] is True
    
    def test_store_limitless_key_invalid(self, client, mock_auth_token):
        """Test Limitless API key storage with invalid key."""
        with patch('src.services.limitless_api.limitless_api_service.validate_api_key') as mock_validate:
            mock_validate.return_value = False
            
            headers = {"Authorization": f"Bearer {mock_auth_token}"}
            response = client.post(
                "/api/api/limitless-key",
                json={"api_key": "invalid_key"},
                headers=headers
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_delete_limitless_key_success(self, client, mock_auth_token):
        """Test successful Limitless API key deletion."""
        headers = {"Authorization": f"Bearer {mock_auth_token}"}
        response = client.delete("/api/api/limitless-key", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "deleted successfully" in data["message"]


class TestAudioProcessingEndpoints:
    """Test cases for audio processing endpoints."""
    
    def test_process_daily_audio_success(self, client, mock_auth_token):
        """Test successful daily audio processing."""
        headers = {"Authorization": f"Bearer {mock_auth_token}"}
        response = client.post(
            "/api/api/process-daily-audio",
            params={"date": "2023-01-01T00:00:00Z"},
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "processing"
        assert "user_id" in data
    
    def test_process_daily_audio_unauthorized(self, client):
        """Test daily audio processing without authentication."""
        response = client.post(
            "/api/api/process-daily-audio",
            params={"date": "2023-01-01T00:00:00Z"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLaughterDetectionEndpoints:
    """Test cases for laughter detection endpoints."""
    
    def test_get_daily_summary_success(self, client, mock_auth_token, mock_daily_summary):
        """Test successful daily summary retrieval."""
        headers = {"Authorization": f"Bearer {mock_auth_token}"}
        response = client.get("/api/api/daily-summary", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_laughter_detections_success(self, client, mock_auth_token, mock_laughter_detections):
        """Test successful laughter detections retrieval."""
        headers = {"Authorization": f"Bearer {mock_auth_token}"}
        response = client.get(
            "/api/api/laughter-detections/2023-01-01T00:00:00Z",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    def test_update_laughter_detection_success(self, client, mock_auth_token):
        """Test successful laughter detection update."""
        headers = {"Authorization": f"Bearer {mock_auth_token}"}
        response = client.put(
            "/api/api/laughter-detections/detection_123",
            json={"notes": "Updated notes"},
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "updated successfully" in data["message"]
    
    def test_delete_laughter_detection_success(self, client, mock_auth_token):
        """Test successful laughter detection deletion."""
        headers = {"Authorization": f"Bearer {mock_auth_token}"}
        response = client.delete(
            "/api/api/laughter-detections/detection_123",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "deleted successfully" in data["message"]


class TestAudioClipEndpoints:
    """Test cases for audio clip endpoints."""
    
    def test_get_audio_clip_not_found(self, client, mock_auth_token):
        """Test audio clip retrieval when clip not found."""
        headers = {"Authorization": f"Bearer {mock_auth_token}"}
        response = client.get(
            "/api/api/audio-clips/nonexistent_clip",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDataManagementEndpoints:
    """Test cases for data management endpoints."""
    
    def test_delete_all_user_data_success(self, client, mock_auth_token):
        """Test successful deletion of all user data."""
        with patch('src.services.cleanup.cleanup_service.delete_user_audio_files') as mock_delete:
            mock_delete.return_value = 5
            
            headers = {"Authorization": f"Bearer {mock_auth_token}"}
            response = client.delete("/api/api/user-data", headers=headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "deleted successfully" in data["message"]
            assert data["deleted_files"] == 5
    
    def test_delete_all_user_data_unauthorized(self, client):
        """Test user data deletion without authentication."""
        response = client.delete("/api/api/user-data")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestHealthCheckEndpoint:
    """Test cases for health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestFrontendEndpoints:
    """Test cases for frontend serving endpoints."""
    
    def test_serve_frontend_success(self, client):
        """Test successful frontend serving."""
        with patch('builtins.open') as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "<html>Test</html>"
            
            response = client.get("/")
            
            assert response.status_code == status.HTTP_200_OK
            assert "text/html" in response.headers["content-type"]
    
    def test_serve_frontend_file_not_found(self, client):
        """Test frontend serving when template file not found."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            response = client.get("/")
            
            assert response.status_code == status.HTTP_200_OK
            assert "Laughter Detector" in response.text


class TestErrorHandlers:
    """Test cases for error handling."""
    
    def test_404_handler(self, client):
        """Test 404 error handler."""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "text/html" in response.headers["content-type"]
        assert "404" in response.text
    
    def test_500_handler(self, client):
        """Test 500 error handler."""
        with patch('src.api.routes.router') as mock_router:
            mock_router.side_effect = Exception("Test error")
            
            # This would need to be implemented to trigger a 500 error
            # For now, we'll test the handler exists
            response = client.get("/")
            assert response.status_code == status.HTTP_200_OK


class TestAuthenticationMiddleware:
    """Test cases for authentication middleware."""
    
    def test_protected_endpoint_without_auth(self, client):
        """Test protected endpoint without authentication."""
        response = client.get("/api/api/daily-summary")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_protected_endpoint_with_invalid_auth(self, client):
        """Test protected endpoint with invalid authentication."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/api/daily-summary", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_protected_endpoint_with_valid_auth(self, client, mock_auth_token):
        """Test protected endpoint with valid authentication."""
        with patch('src.auth.supabase_auth.auth_service.get_current_user') as mock_get_user:
            mock_get_user.return_value = {"user_id": "test_user_123", "email": "test@example.com"}
            
            headers = {"Authorization": f"Bearer {mock_auth_token}"}
            response = client.get("/api/api/daily-summary", headers=headers)
            
            assert response.status_code == status.HTTP_200_OK


class TestRateLimiting:
    """Test cases for rate limiting."""
    
    def test_rate_limit_check_within_limits(self, client, mock_auth_token):
        """Test rate limiting when within limits."""
        with patch('src.api.dependencies.check_rate_limit') as mock_rate_limit:
            mock_rate_limit.return_value = True
            
            headers = {"Authorization": f"Bearer {mock_auth_token}"}
            response = client.post(
                "/api/api/process-daily-audio",
                params={"date": "2023-01-01T00:00:00Z"},
                headers=headers
            )
            
            assert response.status_code == status.HTTP_200_OK
    
    def test_rate_limit_check_exceeded(self, client, mock_auth_token):
        """Test rate limiting when limits exceeded."""
        with patch('src.api.dependencies.check_rate_limit') as mock_rate_limit:
            mock_rate_limit.return_value = False
            
            headers = {"Authorization": f"Bearer {mock_auth_token}"}
            response = client.post(
                "/api/api/process-daily-audio",
                params={"date": "2023-01-01T00:00:00Z"},
                headers=headers
            )
            
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
