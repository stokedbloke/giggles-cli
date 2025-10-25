"""
Main FastAPI application for the laughter detector system.

This module creates and configures the FastAPI application with all routes,
middleware, and startup/shutdown events.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse

from .config.settings import settings
from .api.routes import router
from .services.cleanup import cleanup_service
from .services.scheduler import scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    
    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("Starting laughter detector application")
    
    # Create necessary directories
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(os.path.join(settings.upload_dir, "clips"), exist_ok=True)
    os.makedirs(os.path.join(settings.upload_dir, "temp"), exist_ok=True)
    
    # Start the scheduler for nightly processing
    # Temporarily disabled to fix page loading issue
    # await scheduler.start()
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down laughter detector application")
    
    # Stop the scheduler
    await scheduler.stop()
    
    # Perform final cleanup
    await cleanup_service.schedule_cleanup()
    
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Giggles API",
    description="Secure audio processing system for laughter detection using YAMNet",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.debug else ["localhost", "127.0.0.1", "yourdomain.com", "*.yourdomain.com"]
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def serve_frontend(request: Request):
    """
    Serve the main frontend application.
    
    Args:
        request: FastAPI request object
        
    Returns:
        HTML response with the main application
    """
    try:
        # Read and return the main HTML template
        with open("templates/index.html", "r") as f:
            html_content = f.read()
        
        return HTMLResponse(content=html_content)
        
    except FileNotFoundError:
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Giggles</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        margin: 0; 
                        padding: 20px; 
                        background: #f5f5f5;
                    }
                    .container { 
                        max-width: 600px; 
                        margin: 0 auto; 
                        background: white; 
                        padding: 20px; 
                        border-radius: 10px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }
                    h1 { color: #333; text-align: center; }
                    .status { 
                        text-align: center; 
                        padding: 20px; 
                        background: #e8f5e8; 
                        border-radius: 5px;
                        margin: 20px 0;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎭 Giggles</h1>
                    <div class="status">
                        <p>Application is running!</p>
                        <p>Frontend template not found. Please check the templates directory.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            status_code=200
        )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors with a custom response."""
    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Page Not Found - Laughter Detector</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background: #f5f5f5;
                    text-align: center;
                }
                .container { 
                    max-width: 600px; 
                    margin: 50px auto; 
                    background: white; 
                    padding: 40px; 
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 { color: #333; }
                p { color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>404 - Page Not Found</h1>
                <p>The page you're looking for doesn't exist.</p>
                <a href="/">← Back to Home</a>
            </div>
        </body>
        </html>
        """,
        status_code=404
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors with a custom response."""
    logger.error(f"Internal server error: {str(exc)}")
    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Server Error - Laughter Detector</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background: #f5f5f5;
                    text-align: center;
                }
                .container { 
                    max-width: 600px; 
                    margin: 50px auto; 
                    background: white; 
                    padding: 40px; 
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 { color: #d32f2f; }
                p { color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>500 - Internal Server Error</h1>
                <p>Something went wrong on our end. Please try again later.</p>
                <a href="/">← Back to Home</a>
            </div>
        </body>
        </html>
        """,
        status_code=500
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
