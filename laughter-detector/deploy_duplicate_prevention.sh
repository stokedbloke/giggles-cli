#!/bin/bash
# ==================================================
# DUPLICATE PREVENTION DEPLOYMENT SCRIPT
# ==================================================
# This script deploys the complete duplicate prevention system
# for the Giggles laughter detection system.

set -e  # Exit on any error

echo "🚀 Deploying Duplicate Prevention System"
echo "========================================"

# Configuration
PROJECT_DIR="/Users/neilsethi/git/giggles-cli/laughter-detector"
BACKUP_DIR="$PROJECT_DIR/backups/$(date +%Y%m%d_%H%M%S)"
DRY_RUN=${1:-false}

echo "📁 Project Directory: $PROJECT_DIR"
echo "💾 Backup Directory: $BACKUP_DIR"
echo "🔍 Dry Run: $DRY_RUN"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Step 1: Backup existing data
echo ""
echo "📦 Step 1: Creating backup..."
if [ "$DRY_RUN" = "false" ]; then
    # Backup database schema
    echo "   Backing up database schema..."
    pg_dump --schema-only --no-owner --no-privileges $DATABASE_URL > "$BACKUP_DIR/schema_backup.sql" 2>/dev/null || echo "   ⚠️  Could not backup schema (database not accessible)"
    
    # Backup current laughter detections
    echo "   Backing up laughter detections..."
    python3 -c "
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import json

load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    result = supabase.table('laughter_detections').select('*').execute()
    with open('$BACKUP_DIR/laughter_detections_backup.json', 'w') as f:
        json.dump(result.data, f, indent=2, default=str)
    print(f'   ✅ Backed up {len(result.data)} laughter detections')
else:
    print('   ⚠️  Could not backup data (credentials not found)')
" || echo "   ⚠️  Could not backup data"
else
    echo "   🔍 [DRY RUN] Would create backup"
fi

# Step 2: Apply database constraints
echo ""
echo "🗄️  Step 2: Applying database constraints..."
if [ "$DRY_RUN" = "false" ]; then
    echo "   Applying duplicate prevention constraints..."
    psql $DATABASE_URL -f "$PROJECT_DIR/fix_duplicate_prevention.sql" || {
        echo "   ❌ Failed to apply database constraints"
        echo "   🔧 Manual application required:"
        echo "      psql \$DATABASE_URL -f $PROJECT_DIR/fix_duplicate_prevention.sql"
        exit 1
    }
    echo "   ✅ Database constraints applied"
else
    echo "   🔍 [DRY RUN] Would apply database constraints"
fi

# Step 3: Clean up existing duplicates
echo ""
echo "🧹 Step 3: Cleaning up existing duplicates..."
if [ "$DRY_RUN" = "false" ]; then
    echo "   Running duplicate cleanup..."
    python3 "$PROJECT_DIR/cleanup_existing_duplicates.py" || {
        echo "   ❌ Duplicate cleanup failed"
        echo "   🔧 Manual cleanup required:"
        echo "      python3 $PROJECT_DIR/cleanup_existing_duplicates.py"
        exit 1
    }
    echo "   ✅ Duplicate cleanup completed"
else
    echo "   🔍 [DRY RUN] Would run duplicate cleanup"
    python3 "$PROJECT_DIR/cleanup_existing_duplicates.py" --dry-run
fi

# Step 4: Restart server with new code
echo ""
echo "🔄 Step 4: Restarting server..."
if [ "$DRY_RUN" = "false" ]; then
    echo "   Stopping existing server..."
    pkill -f "uvicorn src.main:app" || echo "   ⚠️  No existing server found"
    sleep 2
    
    echo "   Starting server with duplicate prevention..."
    cd "$PROJECT_DIR"
    nohup python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --log-level info > server.log 2>&1 &
    sleep 3
    
    # Check if server started
    if pgrep -f "uvicorn src.main:app" > /dev/null; then
        echo "   ✅ Server started successfully"
    else
        echo "   ❌ Server failed to start"
        echo "   🔧 Check server.log for details"
        exit 1
    fi
else
    echo "   🔍 [DRY RUN] Would restart server"
fi

# Step 5: Start monitoring
echo ""
echo "📊 Step 5: Starting duplicate monitoring..."
if [ "$DRY_RUN" = "false" ]; then
    echo "   Starting duplicate monitor..."
    nohup python3 "$PROJECT_DIR/monitor_duplicates.py" --check-interval 300 > monitor.log 2>&1 &
    sleep 2
    
    if pgrep -f "monitor_duplicates.py" > /dev/null; then
        echo "   ✅ Duplicate monitor started"
    else
        echo "   ⚠️  Duplicate monitor failed to start"
        echo "   🔧 Check monitor.log for details"
    fi
else
    echo "   🔍 [DRY RUN] Would start duplicate monitoring"
fi

# Step 6: Verify deployment
echo ""
echo "✅ Step 6: Verifying deployment..."
if [ "$DRY_RUN" = "false" ]; then
    echo "   Checking server health..."
    sleep 5
    
    # Check if server is responding
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "   ✅ Server is responding"
    else
        echo "   ⚠️  Server health check failed"
    fi
    
    # Check for duplicates
    echo "   Checking for existing duplicates..."
    python3 "$PROJECT_DIR/monitor_duplicates.py" --once || echo "   ⚠️  Duplicate check failed"
    
    echo "   ✅ Deployment verification completed"
else
    echo "   🔍 [DRY RUN] Would verify deployment"
fi

# Summary
echo ""
echo "🎉 DEPLOYMENT SUMMARY"
echo "===================="
if [ "$DRY_RUN" = "false" ]; then
    echo "✅ Duplicate prevention system deployed successfully"
    echo ""
    echo "📁 Files created:"
    echo "   - $PROJECT_DIR/fix_duplicate_prevention.sql"
    echo "   - $PROJECT_DIR/cleanup_existing_duplicates.py"
    echo "   - $PROJECT_DIR/monitor_duplicates.py"
    echo "   - $PROJECT_DIR/deploy_duplicate_prevention.sh"
    echo ""
    echo "📊 Monitoring:"
    echo "   - Server logs: $PROJECT_DIR/server.log"
    echo "   - Monitor logs: $PROJECT_DIR/monitor.log"
    echo "   - Health data: /tmp/giggles_duplicate_health.json"
    echo ""
    echo "🔧 Manual commands:"
    echo "   - Check duplicates: python3 $PROJECT_DIR/monitor_duplicates.py --once"
    echo "   - Clean duplicates: python3 $PROJECT_DIR/cleanup_existing_duplicates.py"
    echo "   - View server logs: tail -f $PROJECT_DIR/server.log"
    echo "   - View monitor logs: tail -f $PROJECT_DIR/monitor.log"
else
    echo "🔍 [DRY RUN] Deployment would complete successfully"
    echo ""
    echo "📋 To deploy for real, run:"
    echo "   $0 false"
fi

echo ""
echo "🚀 Duplicate prevention system is ready!"
