#!/bin/bash
# Safely test retry logic on production for a single day/user
# 
# SAFETY: Only reprocesses ONE day for ONE user - low risk
# 
# Usage:
#   bash scripts/diagnostics/test_single_day_production.sh DATE USER_ID
#
# Example:
#   bash scripts/diagnostics/test_single_day_production.sh 2025-12-20 1b5b22ba-5581-4a83-a774-7d2a667ceaaf

set -e  # Exit on error

DATE=$1
USER_ID=$2

if [ -z "$DATE" ] || [ -z "$USER_ID" ]; then
    echo "Usage: $0 DATE USER_ID"
    echo "Example: $0 2025-12-20 1b5b22ba-5581-4a83-a774-7d2a667ceaaf"
    exit 1
fi

echo "=================================================================================="
echo "SAFE PRODUCTION TEST: Single Day/User"
echo "=================================================================================="
echo "Date: $DATE"
echo "User ID: $USER_ID"
echo ""
echo "⚠️  This will reprocess ONE day for ONE user on PRODUCTION"
echo "⚠️  Make sure retry logic code is deployed first"
echo ""
echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
sleep 5

# Check if we're on production server (has .env.production)
if [ ! -f ".env.production" ]; then
    echo "❌ .env.production not found"
    echo "   This script should be run on production server"
    exit 1
fi

echo ""
echo "📊 Step 1: Recording BEFORE metrics..."
python3 << PYEOF
import sys
from pathlib import Path
import json
from collections import defaultdict
from datetime import datetime, timedelta
import pytz

PROJECT_ROOT = Path("/var/lib/giggles/giggles-cli/laughter-detector")
sys.path.insert(0, str(PROJECT_ROOT))

import os
from dotenv import load_dotenv
load_dotenv(".env.production")

# Fix httpx compatibility issue with supabase-py
from src.utils.httpx_patch import enable_proxy_keyword_compat
enable_proxy_keyword_compat()

from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

DATE = "$DATE"
USER_ID = "$USER_ID"

# Get processing log
logs = supabase.table("processing_logs").select("*").eq("user_id", USER_ID).eq("date", DATE).order("created_at", desc=True).execute()
log = logs.data[0] if logs.data else None

if not log:
    print("❌ No processing log found")
    sys.exit(1)

api_calls = log.get('api_calls', [])
if isinstance(api_calls, str):
    try:
        api_calls = json.loads(api_calls)
    except:
        api_calls = []

status_counts = defaultdict(int)
for call in api_calls:
    status_counts[call.get('status_code', 'unknown')] += 1

print(f"   BEFORE:")
print(f"     500 Errors: {status_counts[500]}")
print(f"     200 Success: {status_counts[200]}")
print(f"     404 No Data: {status_counts[404]}")
print(f"     Laughter Events: {log.get('laughter_events_found', 0)}")
print(f"     Audio Downloaded: {log.get('audio_files_downloaded', 0)}")

PYEOF

echo ""
echo "🔄 Step 2: Reprocessing $DATE for user $USER_ID..."
echo "   (This will take a few minutes)"

cd /var/lib/giggles/giggles-cli/laughter-detector
source venv_linux/bin/activate
python3 scripts/maintenance/manual_reprocess_yesterday.py "$DATE" "$DATE" --user-id "$USER_ID"

echo ""
echo "⏳ Waiting 5 seconds for database to update..."
sleep 5

echo ""
echo "📊 Step 3: Recording AFTER metrics..."
python3 << PYEOF
import sys
from pathlib import Path
import json
from collections import defaultdict
from datetime import datetime, timedelta
import pytz

PROJECT_ROOT = Path("/var/lib/giggles/giggles-cli/laughter-detector")
sys.path.insert(0, str(PROJECT_ROOT))

import os
from dotenv import load_dotenv
load_dotenv(".env.production")

# Fix httpx compatibility issue with supabase-py
from src.utils.httpx_patch import enable_proxy_keyword_compat
enable_proxy_keyword_compat()

from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

DATE = "$DATE"
USER_ID = "$USER_ID"

# Get processing log
logs = supabase.table("processing_logs").select("*").eq("user_id", USER_ID).eq("date", DATE).order("created_at", desc=True).execute()
log = logs.data[0] if logs.data else None

if not log:
    print("❌ No processing log found after reprocessing")
    sys.exit(1)

api_calls = log.get('api_calls', [])
if isinstance(api_calls, str):
    try:
        api_calls = json.loads(api_calls)
    except:
        api_calls = []

status_counts = defaultdict(int)
retry_patterns = 0
for i, call in enumerate(api_calls):
    status = call.get('status_code', 'unknown')
    status_counts[status] += 1
    if i > 0 and api_calls[i-1].get('status_code') == 500 and status == 200:
        retry_patterns += 1

print(f"   AFTER:")
print(f"     500 Errors: {status_counts[500]}")
print(f"     200 Success: {status_counts[200]}")
print(f"     404 No Data: {status_counts[404]}")
print(f"     Retry Patterns (500→200): {retry_patterns}")
print(f"     Laughter Events: {log.get('laughter_events_found', 0)}")
print(f"     Audio Downloaded: {log.get('audio_files_downloaded', 0)}")

PYEOF

echo ""
echo "✅ Test complete!"
echo ""
echo "📋 Review the BEFORE/AFTER metrics above"
echo "   Look for:"
echo "   - 500 errors decreased (retries worked)"
echo "   - 200 success increased (retries recovered audio)"
echo "   - Retry patterns found (500→200 sequences)"
echo "   - Laughter increased (more audio = more laughter)"

