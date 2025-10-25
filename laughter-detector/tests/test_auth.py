"""
Tests for authentication functionality.

This module contains tests for user registration, login, and authentication
using Supabase Auth.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import status

from src.auth.supabase_auth import AuthService
from src.models.user import UserCreate


class TestAuthService:
    """Test cases for AuthService class."""
    
    def test_validate_email_valid(self):
        """Test email validation with valid email."""
        auth_service = AuthService()
        
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "test+tag@example.org"
        ]
        
        for email in valid_emails:
            assert auth_service.validate_email(email) is True
    
    def test_validate_email_invalid(self):
        """Test email validation with invalid email."""
        auth_service = AuthService()
        
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test.example.com",
            "",
            None
        ]
        
        for email in invalid_emails:
            assert auth_service.validate_email(email) is False
    
    def test_validate_password_strength_valid(self):
        """Test password validation with strong passwords."""
        auth_service = AuthService()
        
        strong_passwords = [
            "StrongPass123!",
            "MySecure@Password1",
            "Test123#Password"
        ]
        
        for password in strong_passwords:
            assert auth_service.validate_password_strength(password) is True
    
    def test_validate_password_strength_invalid(self):
        """Test password validation with weak passwords."""
        auth_service = AuthService()
        
        weak_passwords = [
            "weak",
            "password",
            "12345678",
            "PASSWORD",
            "Password123",
            "Password!",
            "password123!",
            ""
        ]
        
        for password in weak_passwords:
            assert auth_service.validate_password_strength(password) is False
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, mock_supabase_response):
        """Test successful user registration."""
        with patch('src.auth.supabase_auth.create_client') as mock_client:
            mock_supabase = Mock()
            mock_supabase.auth.sign_up.return_value = mock_supabase_response
            mock_client.return_value = mock_supabase
            
            auth_service = AuthService()
            
            result = await auth_service.register_user(
                "test@example.com",
                "TestPass123!"
            )
            
            assert result["user_id"] == "test_user_123"
            assert result["email"] == "test@example.com"
            assert "session" in result
    
    @pytest.mark.asyncio
    async def test_register_user_invalid_email(self):
        """Test user registration with invalid email."""
        auth_service = AuthService()
        
        with pytest.raises(Exception):
            await auth_service.register_user(
                "invalid-email",
                "TestPass123!"
            )
    
    @pytest.mark.asyncio
    async def test_register_user_weak_password(self):
        """Test user registration with weak password."""
        auth_service = AuthService()
        
        with pytest.raises(Exception):
            await auth_service.register_user(
                "test@example.com",
                "weak"
            )
    
    @pytest.mark.asyncio
    async def test_login_user_success(self, mock_supabase_response):
        """Test successful user login."""
        with patch('src.auth.supabase_auth.create_client') as mock_client:
            mock_supabase = Mock()
            mock_supabase.auth.sign_in_with_password.return_value = mock_supabase_response
            mock_client.return_value = mock_supabase
            
            auth_service = AuthService()
            
            result = await auth_service.login_user(
                "test@example.com",
                "TestPass123!"
            )
            
            assert result["user_id"] == "test_user_123"
            assert result["email"] == "test@example.com"
            assert "session" in result
    
    @pytest.mark.asyncio
    async def test_login_user_invalid_credentials(self):
        """Test user login with invalid credentials."""
        with patch('src.auth.supabase_auth.create_client') as mock_client:
            mock_supabase = Mock()
            mock_supabase.auth.sign_in_with_password.return_value = Mock(user=None, session=None)
            mock_client.return_value = mock_supabase
            
            auth_service = AuthService()
            
            with pytest.raises(Exception):
                await auth_service.login_user(
                    "test@example.com",
                    "wrongpassword"
                )
    
    def test_create_access_token(self):
        """Test JWT token creation."""
        auth_service = AuthService()
        
        data = {"sub": "test_user_123", "email": "test@example.com"}
        token = auth_service.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_token_valid(self):
        """Test JWT token verification with valid token."""
        auth_service = AuthService()
        
        data = {"sub": "test_user_123", "email": "test@example.com"}
        token = auth_service.create_access_token(data)
        
        payload = auth_service.verify_token(token)
        assert payload["sub"] == "test_user_123"
        assert payload["email"] == "test@example.com"
    
    def test_verify_token_invalid(self):
        """Test JWT token verification with invalid token."""
        auth_service = AuthService()
        
        with pytest.raises(Exception):
            auth_service.verify_token("invalid_token")


class TestAuthEndpoints:
    """Test cases for authentication API endpoints."""
    
    def test_register_endpoint_success(self, client, test_user_registration_data):
        """Test user registration endpoint with valid data."""
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
    
    def test_register_endpoint_invalid_email(self, client):
        """Test user registration endpoint with invalid email."""
        invalid_data = {
            "email": "invalid-email",
            "password": "TestPass123!"
        }
        
        response = client.post("/api/auth/register", json=invalid_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_register_endpoint_weak_password(self, client):
        """Test user registration endpoint with weak password."""
        invalid_data = {
            "email": "test@example.com",
            "password": "weak"
        }
        
        response = client.post("/api/auth/register", json=invalid_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_login_endpoint_success(self, client, test_user_login_data):
        """Test user login endpoint with valid credentials."""
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
        """Test user login endpoint with invalid credentials."""
        with patch('src.auth.supabase_auth.auth_service.login_user') as mock_login:
            mock_login.side_effect = Exception("Invalid credentials")
            
            response = client.post(
                "/api/auth/login",
                params={"email": "test@example.com", "password": "wrongpassword"}
            )
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUserModels:
    """Test cases for user data models."""
    
    def test_user_create_valid(self):
        """Test UserCreate model with valid data."""
        user_data = UserCreate(
            email="test@example.com",
            password="TestPass123!",
            is_active=True,
            mfa_enabled=False
        )
        
        assert user_data.email == "test@example.com"
        assert user_data.password == "TestPass123!"
        assert user_data.is_active is True
        assert user_data.mfa_enabled is False
    
    def test_user_create_invalid_email(self):
        """Test UserCreate model with invalid email."""
        with pytest.raises(ValueError):
            UserCreate(
                email="invalid-email",
                password="TestPass123!"
            )
    
    def test_user_create_weak_password(self):
        """Test UserCreate model with weak password."""
        with pytest.raises(ValueError):
            UserCreate(
                email="test@example.com",
                password="weak"
            )
    
    def test_limitless_key_create_valid(self):
        """Test LimitlessKeyCreate model with valid data."""
        key_data = LimitlessKeyCreate(api_key="test_api_key_123")
        
        assert key_data.api_key == "test_api_key_123"
    
    def test_limitless_key_create_empty(self):
        """Test LimitlessKeyCreate model with empty API key."""
        with pytest.raises(ValueError):
            LimitlessKeyCreate(api_key="")
    
    def test_limitless_key_create_whitespace(self):
        """Test LimitlessKeyCreate model with whitespace-only API key."""
        with pytest.raises(ValueError):
            LimitlessKeyCreate(api_key="   ")
