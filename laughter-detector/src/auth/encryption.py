"""
Secure encryption and decryption utilities for API keys and sensitive data.

This module provides AES-256-GCM encryption for storing sensitive data like
Limitless API keys with proper key derivation and secure deletion.
"""

import os
import base64
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

from ..config.settings import settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption service.
        
        Args:
            encryption_key: Hex encoded encryption key. If None, uses settings.
        """
        if encryption_key:
            # Handle hex string (64 characters = 32 bytes)
            if len(encryption_key) == 64:
                self.key = bytes.fromhex(encryption_key)
            else:
                self.key = encryption_key.encode('utf-8')
        else:
            self.key = bytes.fromhex(settings.encryption_key)
        
        if len(self.key) != 32:
            raise ValueError("Encryption key must be 32 bytes")
    
    def encrypt(self, plaintext: str, associated_data: Optional[bytes] = None) -> str:
        """
        Encrypt plaintext using AES-256-GCM.
        
        Args:
            plaintext: Text to encrypt
            associated_data: Optional associated data for authentication
            
        Returns:
            Base64 encoded encrypted data with nonce
        """
        if not plaintext:
            raise ValueError("Plaintext cannot be empty")
        
        # Generate random nonce
        nonce = os.urandom(12)
        
        # Create AESGCM cipher
        aesgcm = AESGCM(self.key)
        
        # Encrypt the data
        ciphertext = aesgcm.encrypt(
            nonce, 
            plaintext.encode('utf-8'), 
            associated_data
        )
        
        # Combine nonce and ciphertext
        encrypted_data = nonce + ciphertext
        
        # Return base64 encoded result
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt(self, encrypted_data: str, associated_data: Optional[bytes] = None) -> str:
        """
        Decrypt encrypted data using AES-256-GCM.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            associated_data: Optional associated data for authentication
            
        Returns:
            Decrypted plaintext
            
        Raises:
            ValueError: If decryption fails or data is invalid
        """
        if not encrypted_data:
            raise ValueError("Encrypted data cannot be empty")
        
        try:
            # Decode base64
            encrypted_bytes = base64.b64decode(encrypted_data)
            
            # Extract nonce and ciphertext
            nonce = encrypted_bytes[:12]
            ciphertext = encrypted_bytes[12:]
            
            # Create AESGCM cipher
            aesgcm = AESGCM(self.key)
            
            # Decrypt the data
            plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, associated_data)
            
            return plaintext_bytes.decode('utf-8')
            
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def derive_key_from_password(self, password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password using PBKDF2.
        
        Args:
            password: User password
            salt: Random salt bytes
            
        Returns:
            Derived key bytes
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(password.encode('utf-8'))
    
    def secure_delete_file(self, file_path: str) -> bool:
        """
        Securely delete a file by overwriting it with random data.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                return True
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Overwrite with random data multiple times
            with open(file_path, 'r+b') as f:
                for _ in range(3):  # Overwrite 3 times
                    f.seek(0)
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            
            # Delete the file
            os.remove(file_path)
            return True
            
        except Exception:
            return False


# Global encryption service instance
encryption_service = EncryptionService()
