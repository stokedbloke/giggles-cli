#!/bin/bash
# VPS Initial Setup Script for Giggle Gauge
# Run this script as root on a fresh Ubuntu 22.04 server
# Usage: sudo bash setup_vps.sh

set -e  # Exit on error

echo "🚀 Starting VPS setup for Giggle Gauge..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Update system
echo -e "${GREEN}Updating system packages...${NC}"
apt update && apt upgrade -y

# Install essential packages
echo -e "${GREEN}Installing essential packages...${NC}"
apt install -y \
    python3.9 \
    python3.9-venv \
    python3-pip \
    nginx \
    certbot \
    python3-certbot-nginx \
    ufw \
    fail2ban \
    git \
    curl \
    wget \
    unzip \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev

# Create application user
echo -e "${GREEN}Creating application user...${NC}"
if ! id "giggles" &>/dev/null; then
    useradd -m -s /bin/bash giggles
    usermod -aG sudo giggles
    echo -e "${GREEN}User 'giggles' created${NC}"
else
    echo -e "${YELLOW}User 'giggles' already exists${NC}"
fi

# Create application directories
echo -e "${GREEN}Creating application directories...${NC}"
mkdir -p /var/lib/giggles/{uploads/{clips,audio,temp},logs,static}
chown -R giggles:giggles /var/lib/giggles
chmod 750 /var/lib/giggles
chmod 640 /var/lib/giggles/uploads/* 2>/dev/null || true

# Setup firewall
echo -e "${GREEN}Configuring firewall...${NC}"
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw status

# Configure fail2ban
echo -e "${GREEN}Configuring fail2ban...${NC}"
systemctl enable fail2ban
systemctl start fail2ban

# Setup automatic security updates
echo -e "${GREEN}Configuring automatic security updates...${NC}"
apt install -y unattended-upgrades
echo 'Unattended-Upgrade::Automatic-Reboot "false";' >> /etc/apt/apt.conf.d/50unattended-upgrades

echo -e "${GREEN}✅ VPS setup complete!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Clone your repository to /var/lib/giggles/laughter-detector"
echo "2. Create virtual environment: python3.9 -m venv /var/lib/giggles/venv"
echo "3. Install dependencies: /var/lib/giggles/venv/bin/pip install -r requirements.txt"
echo "4. Configure .env file: cp env.example /var/lib/giggles/.env"
echo "5. Run deployment script: ./scripts/deployment/deploy.sh"

