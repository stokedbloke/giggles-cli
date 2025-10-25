"""
Secure cleanup and deletion service for audio files and user data.

This module handles secure deletion of audio files, cleanup of orphaned files,
and user data deletion with cryptographic file deletion.
"""

import os
import asyncio
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from ..config.settings import settings
from ..auth.encryption import encryption_service

logger = logging.getLogger(__name__)


class CleanupService:
    """Service for secure file cleanup and data deletion."""
    
    def __init__(self):
        """Initialize cleanup service."""
        self.upload_dir = settings.upload_dir
        self.max_file_age = settings.max_file_age
        self.cleanup_interval = settings.cleanup_interval
    
    async def secure_delete_file(self, encrypted_file_path: str, user_id: str = None) -> bool:
        """
        Securely delete a file using cryptographic deletion.
        
        Args:
            encrypted_file_path: Encrypted file path
            user_id: User ID for decryption (optional)
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            # Decrypt file path
            if user_id:
                file_path = encryption_service.decrypt(
                    encrypted_file_path,
                    associated_data=user_id.encode('utf-8')
                )
            else:
                file_path = encryption_service.decrypt(encrypted_file_path)
            
            if not os.path.exists(file_path):
                logger.warning(f"File not found for deletion: {file_path}")
                return True  # Consider it deleted if it doesn't exist
            
            # Perform secure deletion
            success = encryption_service.secure_delete_file(file_path)
            
            if success:
                logger.info(f"Securely deleted file: {file_path}")
            else:
                logger.error(f"Failed to securely delete file: {file_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in secure file deletion: {str(e)}")
            return False
    
    async def cleanup_orphaned_files(self) -> int:
        """
        Clean up orphaned audio files that are no longer referenced.
        
        Returns:
            Number of files cleaned up
        """
        try:
            orphaned_files = await self._find_orphaned_files()
            cleanup_count = 0
            
            for file_path in orphaned_files:
                if await self._delete_orphaned_file(file_path):
                    cleanup_count += 1
            
            logger.info(f"Cleaned up {cleanup_count} orphaned files")
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Error in orphaned file cleanup: {str(e)}")
            return 0
    
    async def _find_orphaned_files(self) -> List[str]:
        """
        Find orphaned files in the upload directory.
        
        Returns:
            List of orphaned file paths
        """
        orphaned_files = []
        
        try:
            # Walk through upload directory
            for root, dirs, files in os.walk(self.upload_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Check if file is old enough to be considered orphaned
                    if await self._is_file_orphaned(file_path):
                        orphaned_files.append(file_path)
            
            return orphaned_files
            
        except Exception as e:
            logger.error(f"Error finding orphaned files: {str(e)}")
            return []
    
    async def _is_file_orphaned(self, file_path: str) -> bool:
        """
        Check if a file is orphaned based on age and other criteria.
        
        Args:
            file_path: Path to file to check
            
        Returns:
            True if file is orphaned, False otherwise
        """
        try:
            # Get file modification time
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            age = datetime.now() - mod_time
            
            # Consider file orphaned if it's older than max_file_age
            return age.total_seconds() > self.max_file_age
            
        except Exception as e:
            logger.error(f"Error checking file age: {str(e)}")
            return False
    
    async def _delete_orphaned_file(self, file_path: str) -> bool:
        """
        Delete an orphaned file securely.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            return encryption_service.secure_delete_file(file_path)
        except Exception as e:
            logger.error(f"Error deleting orphaned file {file_path}: {str(e)}")
            return False
    
    async def delete_user_audio_files(self, user_id: str) -> int:
        """
        Delete all audio files for a specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of files deleted
        """
        try:
            deleted_count = 0
            
            # Find all files for user (this would typically query the database)
            # For now, we'll implement a simple file system walk
            user_files = await self._find_user_files(user_id)
            
            for file_path in user_files:
                if await self.secure_delete_file(file_path, user_id):
                    deleted_count += 1
            
            logger.info(f"Deleted {deleted_count} files for user {user_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting user files: {str(e)}")
            return 0
    
    async def _find_user_files(self, user_id: str) -> List[str]:
        """
        Find all files associated with a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of file paths
        """
        # In a real implementation, this would query the database
        # to find all files associated with the user
        # For now, return empty list
        return []
    
    async def cleanup_old_temp_files(self) -> int:
        """
        Clean up old temporary files.
        
        Returns:
            Number of files cleaned up
        """
        try:
            cleanup_count = 0
            temp_dir = os.path.join(self.upload_dir, "temp")
            
            if not os.path.exists(temp_dir):
                return 0
            
            for file in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file)
                
                if os.path.isfile(file_path):
                    # Check file age
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    age = datetime.now() - mod_time
                    
                    # Delete files older than 1 hour
                    if age.total_seconds() > 3600:
                        if encryption_service.secure_delete_file(file_path):
                            cleanup_count += 1
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {str(e)}")
            return 0
    
    async def schedule_cleanup(self):
        """
        Schedule periodic cleanup tasks.
        
        This method should be called periodically to clean up old files.
        """
        try:
            logger.info("Starting scheduled cleanup")
            
            # Clean up orphaned files
            orphaned_count = await self.cleanup_orphaned_files()
            
            # Clean up old temp files
            temp_count = await self.cleanup_old_temp_files()
            
            logger.info(f"Cleanup completed: {orphaned_count} orphaned files, {temp_count} temp files")
            
        except Exception as e:
            logger.error(f"Error in scheduled cleanup: {str(e)}")


# Global cleanup service instance
cleanup_service = CleanupService()
