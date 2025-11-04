"""
Security utility functions for the laughter detector application.

This module provides security-related utilities including input validation,
sanitization, and security checks.
"""

import re
import hashlib
import secrets
from typing import Optional, List
from urllib.parse import urlparse



class SecurityUtils:
    """Utility class for security-related functions."""
    
    # Regex patterns for validation
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    SAFE_FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')
    SQL_INJECTION_PATTERNS = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
        r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',
        r'(\'|\"|;|\-\-)',
    ]
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email address format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not email or len(email) > 254:
            return False
        
        return bool(SecurityUtils.EMAIL_PATTERN.match(email))
    
    @staticmethod
    def validate_password_strength(password: str) -> bool:
        """
        Validate password strength requirements.
        
        Args:
            password: Password to validate
            
        Returns:
            True if strong enough, False otherwise
        """
        if not password or len(password) < 8:
            return False
        
        # Check for required character types
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        return has_upper and has_lower and has_digit and has_special
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal attacks.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        if not filename:
            return "unnamed_file"
        
        # Remove path components
        filename = filename.split('/')[-1].split('\\')[-1]
        
        # Remove dangerous characters
        filename = re.sub(r'[^\w\-_\.]', '_', filename)
        
        # Ensure filename is not empty
        if not filename or filename.startswith('.'):
            filename = f"file_{filename}"
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:250] + (f'.{ext}' if ext else '')
        
        return filename
    
    @staticmethod
    def validate_filename(filename: str) -> bool:
        """
        Validate filename for security.
        
        Args:
            filename: Filename to validate
            
        Returns:
            True if safe, False otherwise
        """
        if not filename:
            return False
        
        # Check for path traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            return False
        
        # Check for dangerous characters
        if not SecurityUtils.SAFE_FILENAME_PATTERN.match(filename):
            return False
        
        # Check length
        if len(filename) > 255:
            return False
        
        return True
    
    @staticmethod
    def sanitize_input(input_string: str) -> str:
        """
        Sanitize user input to prevent XSS and injection attacks.
        
        Args:
            input_string: Input string to sanitize
            
        Returns:
            Sanitized string
        """
        if not input_string:
            return ""
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', input_string)
        
        # Limit length
        if len(sanitized) > 1000:
            sanitized = sanitized[:1000]
        
        return sanitized.strip()
    
    @staticmethod
    def check_sql_injection(input_string: str) -> bool:
        """
        Check for potential SQL injection patterns.
        
        Args:
            input_string: String to check
            
        Returns:
            True if potential SQL injection detected, False otherwise
        """
        if not input_string:
            return False
        
        input_lower = input_string.lower()
        
        for pattern in SecurityUtils.SQL_INJECTION_PATTERNS:
            if re.search(pattern, input_lower, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def validate_url(url: str, allowed_domains: Optional[List[str]] = None) -> bool:
        """
        Validate URL for security.
        
        Args:
            url: URL to validate
            allowed_domains: List of allowed domains (optional)
            
        Returns:
            True if valid and safe, False otherwise
        """
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check domain if allowed_domains specified
            if allowed_domains:
                if parsed.netloc not in allowed_domains:
                    return False
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        Generate a cryptographically secure random token.
        
        Args:
            length: Length of token in bytes
            
        Returns:
            Base64 encoded token
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple:
        """
        Hash password with salt using PBKDF2.
        
        Args:
            password: Password to hash
            salt: Optional salt (generates new one if None)
            
        Returns:
            Tuple of (hashed_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(32)
        
        # Use PBKDF2 with SHA-256
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )
        
        return hashed.hex(), salt
    
    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            password: Password to verify
            hashed_password: Stored hash
            salt: Salt used for hashing
            
        Returns:
            True if password matches, False otherwise
        """
        computed_hash, _ = SecurityUtils.hash_password(password, salt)
        return computed_hash == hashed_password
    
    @staticmethod
    def check_file_type(file_path: str, allowed_extensions: List[str]) -> bool:
        """
        Check if file has allowed extension.
        
        Args:
            file_path: Path to file
            allowed_extensions: List of allowed extensions
            
        Returns:
            True if file type is allowed, False otherwise
        """
        if not file_path:
            return False
        
        file_ext = file_path.lower().split('.')[-1]
        return file_ext in [ext.lower() for ext in allowed_extensions]
    
    @staticmethod
    def validate_json_input(data: dict, required_fields: List[str]) -> bool:
        """
        Validate JSON input data.
        
        Args:
            data: JSON data to validate
            required_fields: List of required field names
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(data, dict):
            return False
        
        for field in required_fields:
            if field not in data or data[field] is None:
                return False
        
        return True
    
    @staticmethod
    def rate_limit_check(user_id: str, endpoint: str, limit: int, window: int) -> bool:
        """
        Check if user has exceeded rate limit for endpoint.
        
        Args:
            user_id: User ID
            endpoint: API endpoint
            limit: Request limit
            window: Time window in seconds
            
        Returns:
            True if within limits, False if exceeded
        """
        # In a real implementation, this would check against a database or cache
        # For now, return True (no rate limiting)
        return True
