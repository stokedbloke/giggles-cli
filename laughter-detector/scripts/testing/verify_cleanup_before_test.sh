#!/bin/bash
# Quick script to verify cleanup before re-running tests

echo "============================================================"
echo "Verifying Cleanup Before Test"
echo "============================================================"

cd /Users/neilsethi/git/giggles-cli/laughter-detector
source venv_linux/bin/activate

USER1_ID="d26444bc-e441-4f36-91aa-bfee24cb39fb"
USER2_ID="eb719f30-fe9e-42e4-8bb3-d5b4bb8b3327"

echo ""
echo "Checking User 1 detections for Nov 19..."
python -c "
from src.services.supabase_client import get_service_role_client
from datetime import datetime
import pytz

supabase = get_service_role_client()
user_id = '$USER1_ID'
tz = pytz.timezone('America/Los_Angeles')
nov_19_start = tz.localize(datetime(2025, 11, 19, 0, 0, 0))
nov_19_end = tz.localize(datetime(2025, 11, 20, 0, 0, 0))
start_utc = nov_19_start.astimezone(pytz.UTC).isoformat()
end_utc = nov_19_end.astimezone(pytz.UTC).isoformat()

result = supabase.table('laughter_detections').select('id').eq('user_id', user_id).gte('timestamp', start_utc).lt('timestamp', end_utc).execute()
print(f'  User 1 detections: {len(result.data)}')

result = supabase.table('audio_segments').select('id').eq('user_id', user_id).gte('start_time', start_utc).lt('start_time', end_utc).execute()
print(f'  User 1 segments: {len(result.data)}')

result = supabase.table('processing_logs').select('id').eq('user_id', user_id).eq('date', '2025-11-19').execute()
print(f'  User 1 logs: {len(result.data)}')
"

echo ""
echo "Checking User 2 detections for Nov 19..."
python -c "
from src.services.supabase_client import get_service_role_client
from datetime import datetime
import pytz

supabase = get_service_role_client()
user_id = '$USER2_ID'
tz = pytz.timezone('America/Los_Angeles')
nov_19_start = tz.localize(datetime(2025, 11, 19, 0, 0, 0))
nov_19_end = tz.localize(datetime(2025, 11, 20, 0, 0, 0))
start_utc = nov_19_start.astimezone(pytz.UTC).isoformat()
end_utc = nov_19_end.astimezone(pytz.UTC).isoformat()

result = supabase.table('laughter_detections').select('id').eq('user_id', user_id).gte('timestamp', start_utc).lt('timestamp', end_utc).execute()
print(f'  User 2 detections: {len(result.data)}')

result = supabase.table('audio_segments').select('id').eq('user_id', user_id).gte('start_time', start_utc).lt('start_time', end_utc).execute()
print(f'  User 2 segments: {len(result.data)}')

result = supabase.table('processing_logs').select('id').eq('user_id', user_id).eq('date', '2025-11-19').execute()
print(f'  User 2 logs: {len(result.data)}')
"

echo ""
echo "============================================================"
echo "If counts are > 0, run cleanup:"
echo "  python scripts/cleanup/cleanup_date_data.py 2025-11-19 USER_ID"
echo "============================================================"

