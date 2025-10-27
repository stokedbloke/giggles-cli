"""
User data models for authentication and profile management.

This module defines Pydantic models for user-related data validation
and SQLAlchemy models for database operations.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class UserBase(BaseModel):
    """Base user model with common fields."""
    email: EmailStr
    is_active: bool = True
    mfa_enabled: bool = False


class UserCreate(UserBase):
    """User creation model with password."""
    password: str
    timezone: Optional[str] = "UTC"  # User's timezone (IANA format)
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Check for uppercase, lowercase, digit, and special character
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
        
        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError(
                'Password must contain uppercase, lowercase, digit, and special character'
            )
        
        return v


class UserLogin(BaseModel):
    """User login model."""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """User response model without sensitive data."""
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserUpdate(BaseModel):
    """User update model for profile changes."""
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    mfa_enabled: Optional[bool] = None


class LimitlessKeyCreate(BaseModel):
    """Model for creating Limitless API key."""
    api_key: str
    
    @validator('api_key')
    def validate_api_key(cls, v):
        """Validate API key format."""
        if not v or len(v.strip()) == 0:
            raise ValueError('API key cannot be empty')
        return v.strip()


class LimitlessKeyResponse(BaseModel):
    """Model for Limitless API key response (without actual key)."""
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool = True


# SQLAlchemy Models
class User(Base):
    """SQLAlchemy model for users table."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    mfa_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class LimitlessKey(Base):
    """SQLAlchemy model for Limitless API keys table."""
    __tablename__ = "limitless_keys"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    encrypted_api_key = Column(Text, nullable=False)  # Encrypted API key
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
