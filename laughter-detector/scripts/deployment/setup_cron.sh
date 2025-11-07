#!/bin/bash
# Cron Job Setup Script for Nightly Audio Processing
# Run this script as root
# Usage: sudo bash setup_cron.sh

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

APP_DIR="/var/lib/giggles/laughter-detector/laughter-detector"
VENV_DIR="/var/lib/giggles/venv"
LOG_DIR="/var/lib/giggles/logs"
CRON_SCRIPT="$APP_DIR/process_nightly_audio.py"

echo -e "${GREEN}Setting up cron job for nightly audio processing...${NC}"

# Verify files exist
if [ ! -f "$CRON_SCRIPT" ]; then
    echo -e "${RED}Cron script not found: $CRON_SCRIPT${NC}"
    exit 1
fi

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"
chown giggles:giggles "$LOG_DIR"

# Create cron job entry
# Runs daily at 2:00 AM (adjust timezone as needed)
CRON_ENTRY="0 2 * * * cd $APP_DIR && $VENV_DIR/bin/python $CRON_SCRIPT >> $LOG_DIR/nightly_processing.log 2>&1"

# Check if cron job already exists
CRON_FILE="/etc/cron.d/giggles-nightly"
if [ -f "$CRON_FILE" ]; then
    echo -e "${YELLOW}Cron file already exists. Updating...${NC}"
else
    echo -e "${GREEN}Creating cron file...${NC}"
fi

# Write cron job
cat > "$CRON_FILE" << EOF
# Giggle Gauge Nightly Audio Processing
# Runs daily at 2:00 AM
$CRON_ENTRY
EOF

# Set proper permissions
chmod 644 "$CRON_FILE"
chown root:root "$CRON_FILE"

# Verify cron syntax (if available)
if command -v crontab &> /dev/null; then
    echo -e "${GREEN}Verifying cron syntax...${NC}"
    # Note: We can't directly test /etc/cron.d files, but we can check the format
fi

echo -e "${GREEN}✅ Cron job configured!${NC}"
echo -e "${YELLOW}Cron job will run daily at 2:00 AM${NC}"
echo -e "${YELLOW}Logs will be written to: $LOG_DIR/nightly_processing.log${NC}"
echo ""
echo -e "${GREEN}To view cron logs:${NC}"
echo "  tail -f $LOG_DIR/nightly_processing.log"
echo ""
echo -e "${GREEN}To test the cron job manually:${NC}"
echo "  cd $APP_DIR && $VENV_DIR/bin/python $CRON_SCRIPT"

