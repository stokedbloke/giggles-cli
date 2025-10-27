#!/bin/bash
# Cleanup script for PR - removes temporary files and documentation clutter

echo "🧹 Cleaning up codebase for PR..."
echo ""

cd "$(dirname "$0")"

# Count files before cleanup
FILES_BEFORE=$(find . -name "*.md" -o -name "test_*.py" | wc -l | tr -d ' ')

# Delete temporary markdown documentation
echo "📄 Removing temporary documentation..."
rm -f AWS_DEPLOYMENT_PLAN.md
rm -f DIGITALOCEAN_DEPLOYMENT_PLAN.md
rm -f VERCEL_DEPLOYMENT_PLAN.md
rm -f DUPLICATE_PREVENTION_SUMMARY.md
rm -f FINAL_AUDIT_REPORT.md
rm -f PRODUCTION_SCHEDULER_ANALYSIS.md
rm -f TASK_LIST_AND_FIXES.md
rm -f TEST_RESULTS.md

# Delete old test files (keep only the security fix test)
echo "🧪 Removing old test files..."
rm -f test_app.py
rm -f test_complete_duplicate_prevention.py
rm -f test_core_functionality.py
rm -f test_correct_duplicate_prevention.py
rm -f test_current_day_processing.py
rm -f test_data_integrity.py
rm -f test_duplicate_prevention.py
rm -f test_duplicate_prevention_simple.py
rm -f test_manual_processing.py
rm -f test_page_refresh.py
rm -f test_security_fix_get_current_user.py
rm -f test_structure.py

# Note: Keep test_security_fix_unit.py (the passing one)

# Delete temporary security docs (after review)
echo "🔒 Removing temporary security docs..."
# Note: CHANGES_SUMMARY.md and SECURITY_FIX_PR_SUMMARY.md 
# should be kept for PR review, then deleted after merge

# Count files after cleanup
FILES_AFTER=$(find . -name "*.md" -o -name "test_*.py" | wc -l | tr -d ' ')

echo ""
echo "✅ Cleanup complete!"
echo "   Files before: $FILES_BEFORE"
echo "   Files after: $FILES_AFTER"
echo "   Removed: $((FILES_BEFORE - FILES_AFTER)) files"
echo ""
echo "📋 Remaining documentation:"
find . -name "*.md" | sort
echo ""
echo "📋 Remaining tests:"
find . -name "test_*.py" | sort
