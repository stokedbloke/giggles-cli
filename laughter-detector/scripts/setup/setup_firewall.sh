#!/bin/bash
# Firewall Setup Script (UFW)
# Run this script as root
# Usage: sudo bash setup_firewall.sh

set -e  # Exit on error

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

echo -e "${GREEN}Configuring UFW firewall...${NC}"

# Enable UFW
ufw --force enable

# Set defaults
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (critical - don't lock yourself out!)
echo -e "${GREEN}Allowing SSH (port 22)...${NC}"
ufw allow 22/tcp comment 'SSH'

# Allow HTTP
echo -e "${GREEN}Allowing HTTP (port 80)...${NC}"
ufw allow 80/tcp comment 'HTTP'

# Allow HTTPS
echo -e "${GREEN}Allowing HTTPS (port 443)...${NC}"
ufw allow 443/tcp comment 'HTTPS'

# Optional: Rate limit SSH (prevents brute force)
echo -e "${GREEN}Configuring SSH rate limiting...${NC}"
ufw limit 22/tcp comment 'SSH rate limit'

# Show status
echo -e "${GREEN}Firewall status:${NC}"
ufw status verbose

echo -e "${GREEN}✅ Firewall configuration complete!${NC}"
echo -e "${YELLOW}Note: Only SSH (22), HTTP (80), and HTTPS (443) are allowed${NC}"

