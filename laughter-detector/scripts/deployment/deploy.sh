#!/bin/bash
# Application Deployment Script for Giggle Gauge
# Run this script as the 'giggles' user after initial VPS setup
# Usage: bash deploy.sh

set -e  # Exit on error

echo "🚀 Deploying Giggle Gauge application..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as giggles user
if [ "$USER" != "giggles" ]; then
    echo -e "${YELLOW}Warning: Not running as 'giggles' user. Some operations may fail.${NC}"
fi

APP_DIR="/var/lib/giggles/laughter-detector"
VENV_DIR="/var/lib/giggles/venv"

# Navigate to application directory
if [ ! -d "$APP_DIR" ]; then
    echo -e "${RED}Application directory not found: $APP_DIR${NC}"
    echo "Please clone the repository first:"
    echo "  git clone <your-repo-url> $APP_DIR"
    exit 1
fi

cd "$APP_DIR"

# Activate virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    python3.9 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# Pull latest code
echo -e "${GREEN}Pulling latest code...${NC}"
git pull origin main || git pull origin feature/vps-deployment

# Install/update dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Ensure .env file exists
if [ ! -f "/var/lib/giggles/.env" ]; then
    echo -e "${YELLOW}Warning: .env file not found at /var/lib/giggles/.env${NC}"
    echo "Please create it from env.example and configure with production values"
    exit 1
fi

# Set proper permissions
echo -e "${GREEN}Setting file permissions...${NC}"
chmod 600 /var/lib/giggles/.env
chmod 750 /var/lib/giggles/uploads
chmod 640 /var/lib/giggles/uploads/*/* 2>/dev/null || true

# Install systemd service
echo -e "${GREEN}Installing systemd service...${NC}"
sudo cp systemd/giggles.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable giggles

# Restart service
echo -e "${GREEN}Restarting application service...${NC}"
sudo systemctl restart giggles

# Check service status
sleep 2
if sudo systemctl is-active --quiet giggles; then
    echo -e "${GREEN}✅ Application deployed and running!${NC}"
    sudo systemctl status giggles --no-pager -l
else
    echo -e "${RED}❌ Application failed to start. Check logs:${NC}"
    echo "  sudo journalctl -u giggles -n 50"
    exit 1
fi

echo -e "${GREEN}✅ Deployment complete!${NC}"

