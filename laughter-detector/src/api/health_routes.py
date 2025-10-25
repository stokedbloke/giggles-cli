"""
Health check routes for the laughter detector application.

This module handles health checks and system status endpoints.
"""

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        System health status
    """
    return {
        "status": "healthy",
        "message": "Giggles API is running",
        "timestamp": "2024-12-19T00:00:00Z"
    }
