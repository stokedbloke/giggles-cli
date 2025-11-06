#!/bin/bash
echo "=== Cron Job Status Check ==="
echo ""

# Check if cron is scheduled
echo "1. Cron Schedule:"
crontab -l | grep "process_nightly_audio" || echo "   ❌ Not scheduled"
echo ""

# Check log file
echo "2. Log File:"
if [ -f "logs/nightly_processing.log" ]; then
    echo "   ✅ Log file exists"
    echo "   Last modified: $(stat -f "%Sm" logs/nightly_processing.log)"
    echo ""
    echo "   Last 20 lines:"
    echo "   ----------------------------------------"
    tail -20 logs/nightly_processing.log | sed 's/^/   /'
else
    echo "   ❌ Log file doesn't exist (cron hasn't run yet or failed silently)"
fi
echo ""

# Check database (requires Python)
echo "3. Database Check (cron entries):"
cd /Users/neilsethi/git/giggles-cli/laughter-detector
/Users/neilsethi/git/giggles-cli/.venv/bin/python3 << 'PYEOF'
import os
import sys
sys.path.append('.')
from dotenv import load_dotenv
from supabase import create_client

try:
    load_dotenv()
    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    
    result = supabase.table("processing_logs").select("*").eq("trigger_type", "cron").order("created_at", desc=True).limit(3).execute()
    
    if result.data:
        print("   ✅ Found cron job entries:")
        for log in result.data:
            print(f"   - {log.get('created_at')} | Events: {log.get('laughter_events_found', 0)}")
    else:
        print("   ❌ No cron job entries found")
except Exception as e:
    print(f"   ⚠️  Could not check database: {e}")
PYEOF

echo ""
echo "=== To manually test the cron job: ==="
echo "cd /Users/neilsethi/git/giggles-cli/laughter-detector"
echo "/Users/neilsethi/git/giggles-cli/.venv/bin/python3 process_nightly_audio.py"
