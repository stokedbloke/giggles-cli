#!/bin/bash
# Data Integrity Monitor Runner
# Run this script periodically to track data consistency

echo "🔍 Running Giggles Data Integrity Monitor..."
echo "Time: $(date)"
echo ""

# Run the monitor
python3 monitor_data_integrity.py

# Show exit status
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Monitor completed successfully"
else
    echo ""
    echo "⚠️  Monitor found issues - check the report"
fi
