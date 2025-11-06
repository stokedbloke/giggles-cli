#!/bin/bash
# SSL/TLS Setup Script using Let's Encrypt
# Run this script as root after nginx is configured
# Usage: sudo bash setup_ssl.sh yourdomain.com

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

# Check domain argument
if [ -z "$1" ]; then
    echo -e "${RED}Usage: sudo bash setup_ssl.sh yourdomain.com${NC}"
    exit 1
fi

DOMAIN=$1

echo -e "${GREEN}Setting up SSL certificate for $DOMAIN...${NC}"

# Ensure nginx is installed and running
if ! command -v nginx &> /dev/null; then
    echo -e "${RED}nginx is not installed. Please install it first.${NC}"
    exit 1
fi

# Ensure certbot is installed
if ! command -v certbot &> /dev/null; then
    echo -e "${GREEN}Installing certbot...${NC}"
    apt update
    apt install -y certbot python3-certbot-nginx
fi

# Check if nginx config exists
NGINX_CONFIG="/etc/nginx/sites-available/giggles"
if [ ! -f "$NGINX_CONFIG" ]; then
    echo -e "${YELLOW}Warning: nginx config not found at $NGINX_CONFIG${NC}"
    echo "Please copy nginx/giggles.conf to $NGINX_CONFIG first"
    echo "And update the server_name directive with your domain"
    exit 1
fi

# Update nginx config with domain name
sed -i "s/server_name _;/server_name $DOMAIN;/g" "$NGINX_CONFIG"
sed -i "s/YOUR_DOMAIN/$DOMAIN/g" "$NGINX_CONFIG"

# Test nginx configuration
echo -e "${GREEN}Testing nginx configuration...${NC}"
nginx -t

# Restart nginx
systemctl restart nginx

# Obtain certificate
echo -e "${GREEN}Obtaining SSL certificate from Let's Encrypt...${NC}"
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email admin@"$DOMAIN" --redirect

# Test auto-renewal
echo -e "${GREEN}Testing certificate auto-renewal...${NC}"
certbot renew --dry-run

# Setup auto-renewal cron (certbot usually does this automatically, but verify)
if ! grep -q "certbot renew" /etc/cron.d/certbot 2>/dev/null; then
    echo "0 0,12 * * * root certbot renew --quiet" >> /etc/cron.d/certbot
fi

echo -e "${GREEN}✅ SSL certificate setup complete!${NC}"
echo -e "${YELLOW}Your site should now be accessible at https://$DOMAIN${NC}"

