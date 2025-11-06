#!/bin/bash
# File Organization Script
# Moves files to organized directories using 'git mv' to preserve history

set -e  # Exit on error

echo "📁 Starting file organization..."

# Documentation files - organized by topic
echo "📚 Moving documentation files..."

# Deployment docs
git mv DOCUMENTATION_AND_DEPLOYMENT_PLAN.md docs/deployment/ 2>/dev/null || true
git mv CRON_SETUP_GUIDE.md docs/deployment/ 2>/dev/null || true
git mv INSTALLATION.md docs/deployment/ 2>/dev/null || true
git mv PR_AND_DEPLOYMENT_CHECKLIST.md docs/deployment/ 2>/dev/null || true
git mv PR_CHECKLIST.md docs/deployment/ 2>/dev/null || true
git mv VPS_DEPLOYMENT_PLAN.md docs/deployment/ 2>/dev/null || true

# Security docs
git mv CRON_SECURITY_BEST_PRACTICES.md docs/security/ 2>/dev/null || true
git mv SECURITY_AUDIT_FULL.md docs/security/ 2>/dev/null || true
git mv SECURITY_FIX_PLAN.md docs/security/ 2>/dev/null || true
git mv SECURITY_FIX_PR_SUMMARY.md docs/security/ 2>/dev/null || true
git mv SECURITY_PRIORITIES.md docs/security/ 2>/dev/null || true
git mv SECURITY_TRADEOFFS_ANALYSIS.md docs/security/ 2>/dev/null || true

# Feature docs - Nightly Cron
git mv DRESS_REHEARSAL_ANALYSIS.md docs/features/nightly-cron/ 2>/dev/null || true
git mv NIGHTLY_CRON_TODO.md docs/features/nightly-cron/ 2>/dev/null || true
git mv TEST_CRON_SETUP.md docs/features/nightly-cron/ 2>/dev/null || true
git mv TRUE_DRESS_REHEARSAL_PLAN.md docs/features/nightly-cron/ 2>/dev/null || true

# Feature docs - Multi-User
git mv MULTI_USER_TESTING_GUIDE.md docs/features/multi-user/ 2>/dev/null || true
git mv REGISTRATION_FLOW_EXPLANATION.md docs/features/multi-user/ 2>/dev/null || true

# Feature docs - Timezone
git mv DATABASE_SCHEMA_TIMEZONE.md docs/features/timezone/ 2>/dev/null || true
git mv TIMEZONE_ANALYSIS_PLAN.md docs/features/timezone/ 2>/dev/null || true
git mv TIMEZONE_CRON_ANALYSIS.md docs/features/timezone/ 2>/dev/null || true
git mv TIMEZONE_IMPLEMENTATION_PRIORITY.md docs/features/timezone/ 2>/dev/null || true
git mv TIMEZONE_IMPLEMENTATION_SUMMARY.md docs/features/timezone/ 2>/dev/null || true
git mv TIMEZONE_TEST_PLAN.md docs/features/timezone/ 2>/dev/null || true
git mv TIMEZONE_TEST.md docs/features/timezone/ 2>/dev/null || true
git mv TIMEZONE_TESTING_PLAN.md docs/features/timezone/ 2>/dev/null || true
git mv QUICK_TIMEZONE_UPDATE.md docs/features/timezone/ 2>/dev/null || true

# Feature docs - General
git mv BACKLOG.md docs/features/ 2>/dev/null || true
git mv BRANCH_CHANGES_SUMMARY.md docs/features/ 2>/dev/null || true
git mv BRANCH_TESTING_GUIDE.md docs/features/ 2>/dev/null || true
git mv CHANGES_SUMMARY.md docs/features/ 2>/dev/null || true
git mv CHANGES_THIS_BRANCH.md docs/features/ 2>/dev/null || true
git mv CODE_CHANGES_SUMMARY.md docs/features/ 2>/dev/null || true
git mv COMPLETE_CHANGES_SUMMARY.md docs/features/ 2>/dev/null || true
git mv DEBUGGING_ANALYSIS.md docs/features/ 2>/dev/null || true
git mv DEFINITIVE_ANALYSIS.md docs/features/ 2>/dev/null || true
git mv DEFINITIVE_TEST_PLAN.md docs/features/ 2>/dev/null || true
git mv DETECTION_LOGGING_IMPROVEMENTS.md docs/features/ 2>/dev/null || true
git mv DETECTION_TRACKING_ANALYSIS.md docs/features/ 2>/dev/null || true
git mv FIXES_APPLIED.md docs/features/ 2>/dev/null || true
git mv FIX_PLAN_PRE_DOWNLOAD_CHECK.md docs/features/ 2>/dev/null || true
git mv FIX_PROPOSAL.md docs/features/ 2>/dev/null || true
git mv FIX_VERIFICATION.md docs/features/ 2>/dev/null || true
git mv NEXT_FEATURE_BRANCH.md docs/features/ 2>/dev/null || true
git mv PR_DESCRIPTION.md docs/features/ 2>/dev/null || true
git mv PR_README.md docs/features/ 2>/dev/null || true
git mv RECOMMENDATION_OPTION_B.md docs/features/ 2>/dev/null || true
git mv REMOVE_PATH_ENCRYPTION_PLAN.md docs/features/ 2>/dev/null || true
git mv REPROCESS_DUPLICATE_ANALYSIS.md docs/features/ 2>/dev/null || true
git mv SIMPLIFIED_LOGGING.md docs/features/ 2>/dev/null || true
git mv TEST_COMPARISON_ANALYSIS.md docs/features/ 2>/dev/null || true
git mv UI_REPROCESS_FEATURE.md docs/features/ 2>/dev/null || true

# Maintenance docs
git mv CLEANUP_PLAN.md docs/maintenance/ 2>/dev/null || true
git mv REMOVE_ORPHAN_CLEANUP.md docs/maintenance/ 2>/dev/null || true

echo "✅ Documentation files moved"

# Utility scripts
echo "🔧 Moving utility scripts..."

# Verification scripts
git mv check_clip_duplicates.py scripts/verification/ 2>/dev/null || true
git mv check_clip_issue.py scripts/verification/ 2>/dev/null || true
git mv check_cron_status.sh scripts/verification/ 2>/dev/null || true
git mv check_db_status.py scripts/verification/ 2>/dev/null || true
git mv check_earlier_processing.py scripts/verification/ 2>/dev/null || true
git mv check_file_paths.py scripts/verification/ 2>/dev/null || true
git mv check_files.py scripts/verification/ 2>/dev/null || true
git mv check_laughter_classes.py scripts/verification/ 2>/dev/null || true
git mv check_limitless_timestamp_issue.py scripts/verification/ 2>/dev/null || true
git mv check_orphaned_file.py scripts/verification/ 2>/dev/null || true
git mv check_orphans.py scripts/verification/ 2>/dev/null || true
git mv check_processing_logs.py scripts/verification/ 2>/dev/null || true
git mv check_reprocess_results.py scripts/verification/ 2>/dev/null || true
git mv check_timezone_issue.py scripts/verification/ 2>/dev/null || true
git mv check_yamnet_classes.py scripts/verification/ 2>/dev/null || true
git mv compare_runs.py scripts/verification/ 2>/dev/null || true
git mv verify_11_5_giggles.py scripts/verification/ 2>/dev/null || true
git mv verify_cleanup.py scripts/verification/ 2>/dev/null || true
git mv verify_cron_results.py scripts/verification/ 2>/dev/null || true
git mv verify_dress_rehearsal.py scripts/verification/ 2>/dev/null || true
git mv verify_multi_user_isolation.py scripts/verification/ 2>/dev/null || true
git mv test_deletion_direct.py scripts/verification/ 2>/dev/null || true
git mv test_processing_flow.py scripts/verification/ 2>/dev/null || true

# Cleanup scripts
git mv cleanup_date_data.py scripts/cleanup/ 2>/dev/null || true
git mv cleanup_duplicate_segments_v2.py scripts/cleanup/ 2>/dev/null || true
git mv cleanup_duplicate_segments.py scripts/cleanup/ 2>/dev/null || true
git mv cleanup_existing_duplicates.py scripts/cleanup/ 2>/dev/null || true
git mv cleanup_orphaned_audio.py scripts/cleanup/ 2>/dev/null || true
git mv cleanup_orphaned_files.py scripts/cleanup/ 2>/dev/null || true
git mv cleanup_today_data.py scripts/cleanup/ 2>/dev/null || true

# Maintenance scripts
git mv analyze_duplicates.py scripts/maintenance/ 2>/dev/null || true
git mv analyze_timestamp_offset.py scripts/maintenance/ 2>/dev/null || true
git mv delete_test_user.py scripts/maintenance/ 2>/dev/null || true
git mv fix_data_integrity.py scripts/maintenance/ 2>/dev/null || true
git mv fix_encrypted_paths.py scripts/maintenance/ 2>/dev/null || true
git mv fix_missing_detections_simple.py scripts/maintenance/ 2>/dev/null || true
git mv fix_missing_detections.py scripts/maintenance/ 2>/dev/null || true
git mv fix_timestamps_properly.py scripts/maintenance/ 2>/dev/null || true
git mv manual_reprocess_yesterday.py scripts/maintenance/ 2>/dev/null || true
git mv monitor_data_integrity.py scripts/maintenance/ 2>/dev/null || true
git mv monitor_duplicates.py scripts/maintenance/ 2>/dev/null || true
git mv reprocess_date.py scripts/maintenance/ 2>/dev/null || true
git mv run_monitor.sh scripts/maintenance/ 2>/dev/null || true
git mv start_scheduler.py scripts/maintenance/ 2>/dev/null || true
git mv cleanup_for_pr.sh scripts/maintenance/ 2>/dev/null || true

# Setup scripts
git mv apply_laughter_classes_migration.py scripts/setup/ 2>/dev/null || true
git mv deploy_duplicate_prevention.sh scripts/setup/ 2>/dev/null || true
git mv start_fresh_script.py scripts/setup/ 2>/dev/null || true

# SQL files
echo "💾 Moving SQL files..."
git mv add_laughter_classes.sql scripts/setup/ 2>/dev/null || true
git mv fix_duplicate_prevention_correct.sql scripts/setup/ 2>/dev/null || true
git mv fix_duplicate_prevention.sql scripts/setup/ 2>/dev/null || true
git mv fix_unique_constraint_with_class_id.sql scripts/setup/ 2>/dev/null || true
git mv migration_enhanced_logging.sql scripts/setup/ 2>/dev/null || true
git mv REGISTRATION_FIX_FINAL.sql scripts/setup/ 2>/dev/null || true
git mv setup_database.sql scripts/setup/ 2>/dev/null || true

echo "✅ Files organized successfully!"
echo ""
echo "📋 Summary:"
echo "  - Documentation → docs/"
echo "  - Utility scripts → scripts/"
echo "  - SQL files → scripts/setup/"
echo ""
echo "💡 Next step: Review changes with 'git status', then commit"

