#!/usr/bin/env python3
"""
Setup script for the Laughter Detector application.

This script helps configure the environment and validate the setup.
"""

import os
import secrets
import sys
from pathlib import Path

def generate_secret_key(length=32):
    """Generate a secure random secret key."""
    return secrets.token_urlsafe(length)

def generate_encryption_key(length=32):
    """Generate a secure random encryption key."""
    return secrets.token_hex(length)

def create_env_file():
    """Create .env file with default values."""
    env_file = Path(".env")
    
    if env_file.exists():
        print("⚠️  .env file already exists. Backing up to .env.backup")
        env_file.rename(".env.backup")
    
    # Generate secure keys
    secret_key = generate_secret_key()
    encryption_key = generate_encryption_key()
    
    env_content = f"""# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here

# Security Configuration (GENERATED - KEEP SECURE!)
SECRET_KEY={secret_key}
ENCRYPTION_KEY={encryption_key}

# Database Configuration
DATABASE_URL=postgresql://postgres:your_password@db.your_project.supabase.co:5432/postgres

# Application Configuration
DEBUG=True
HOST=0.0.0.0
PORT=8000

# File Storage Configuration
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=104857600

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# Audio Processing Configuration
YAMNET_MODEL_URL=https://tfhub.dev/google/yamnet/1
AUDIO_SAMPLE_RATE=16000
AUDIO_CHANNELS=1
LAUGHTER_THRESHOLD=0.3
CLIP_DURATION=4.0

# Cleanup Configuration
CLEANUP_INTERVAL=3600
MAX_FILE_AGE=86400
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("✅ Created .env file with secure keys generated")
    print("🔐 IMPORTANT: Keep your .env file secure and never commit it to version control!")
    
    return True

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 9):
        print("❌ Python 3.9 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    
    print(f"✅ Python version: {sys.version}")
    if sys.version_info < (3, 11):
        print("⚠️  Note: Python 3.11+ recommended for best performance")
    return True

def check_pip():
    """Check if pip is available."""
    try:
        import subprocess
        result = subprocess.run([sys.executable, "-m", "pip", "--version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ pip is available: {result.stdout.strip()}")
            return True
    except Exception as e:
        print(f"❌ pip not available: {e}")
        return False
    
    return False

def install_dependencies():
    """Install required dependencies."""
    try:
        import subprocess
        print("📦 Installing dependencies...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
            return True
        else:
            print(f"❌ Failed to install dependencies: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def create_directories():
    """Create necessary directories."""
    directories = ["uploads", "uploads/clips", "uploads/temp", "logs"]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    return True

def validate_structure():
    """Validate project structure."""
    required_files = [
        "src/main.py",
        "requirements.txt",
        "templates/index.html",
        "static/css/style.css",
        "static/js/app.js"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False
    
    print("✅ Project structure is valid")
    return True

def main():
    """Main setup function."""
    print("🎭 Giggles - Setup Script")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check pip
    if not check_pip():
        print("💡 Try installing pip:")
        print("  - On macOS: brew install python")
        print("  - On Ubuntu: sudo apt install python3-pip")
        print("  - On Windows: python -m ensurepip --upgrade")
        sys.exit(1)
    
    # Validate structure
    if not validate_structure():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Create .env file
    create_env_file()
    
    # Install dependencies
    if not install_dependencies():
        print("💡 Try running: python -m pip install --upgrade pip")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Set up your Supabase project:")
    print("   - Go to https://supabase.com")
    print("   - Create a new project")
    print("   - Copy your project URL and API keys")
    print("\n2. Update your .env file with Supabase credentials:")
    print("   - SUPABASE_URL=your_project_url")
    print("   - SUPABASE_KEY=your_anon_key")
    print("   - SUPABASE_SERVICE_ROLE_KEY=your_service_role_key")
    print("   - DATABASE_URL=your_database_url")
    print("\n3. Set up database tables:")
    print("   - Go to Supabase SQL Editor")
    print("   - Run the setup_database.sql script")
    print("\n4. Start the application:")
    print("   - python -m uvicorn src.main:app --reload")
    print("\n5. Open your browser:")
    print("   - http://localhost:8000")

if __name__ == "__main__":
    main()
