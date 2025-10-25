"""
Main routes module for the laughter detector application.

This module imports and includes all route modules to create the complete API.
"""

from fastapi import APIRouter

from .auth_routes import router as auth_router
from .key_routes import router as key_router
from .audio_routes import router as audio_router
from .data_routes import router as data_router
from .health_routes import router as health_router
# from .current_day_routes import router as current_day_router  # Temporarily disabled

# Create main router
router = APIRouter()

# Include all route modules
router.include_router(auth_router)
router.include_router(key_router)
router.include_router(audio_router)
router.include_router(data_router)
router.include_router(health_router)
# router.include_router(current_day_router)  # Temporarily disabled