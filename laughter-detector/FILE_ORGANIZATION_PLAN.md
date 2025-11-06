# File Organization Plan

## 🎯 Goal
Clean, maintainable repository structure where it's immediately clear:
- What's mainline code vs feature-specific
- What files belong to which feature/branch
- What's temporary vs permanent

---

## 📁 Proposed Directory Structure

```
laughter-detector/
├── src/                    # Core application code (mainline)
├── static/                 # Static assets (mainline)
├── templates/              # HTML templates (mainline)
├── tests/                  # Unit tests (mainline)
├── uploads/                # User uploads (runtime)
├── logs/                   # Log files (runtime)
│
├── docs/                   # ALL documentation
│   ├── deployment/         # Deployment guides
│   ├── security/           # Security documentation
│   ├── features/           # Feature-specific docs
│   │   ├── nightly-cron/   # Nightly cron feature docs
│   │   ├── multi-user/     # Multi-user feature docs
│   │   └── timezone/       # Timezone feature docs
│   └── README.md           # Documentation index
│
├── scripts/                # Utility scripts (not mainline code)
│   ├── maintenance/        # Maintenance/debugging scripts
│   ├── verification/       # Verification/test scripts
│   ├── cleanup/            # Cleanup scripts
│   └── setup/              # Setup/installation scripts
│
├── .gitignore              # Git ignore patterns
├── README.md               # Main project README
├── requirements.txt        # Python dependencies
├── setup.py                # Package setup
├── env.example             # Environment template
├── docker-compose.yml      # Docker config (if used)
└── ROOT_FILES.md           # Explains what belongs in root

```

---

## 🔄 File Categories

### MAINLINE CODE (Stay in current locations)
- `src/` - All application code
- `static/` - Frontend assets
- `templates/` - HTML templates
- `tests/` - Unit tests
- `requirements.txt` - Dependencies
- `setup.py` - Package setup
- `README.md` - Main documentation

### DOCUMENTATION (Move to `docs/`)
- All `*.md` files except `README.md`
- Organized by feature/topic

### UTILITY SCRIPTS (Move to `scripts/`)
- `check_*.py` - Verification scripts
- `analyze_*.py` - Analysis scripts
- `test_*.py` - One-off test scripts (not unit tests)
- `verify_*.py` - Verification scripts
- `cleanup_*.py` - Cleanup scripts
- `fix_*.py` - One-off fix scripts
- `*.sh` - Shell scripts

### SQL FILES (Move to `scripts/setup/`)
- `*.sql` - Database setup/migration scripts

### TEMPORARY/DEBUG FILES (Should be deleted or gitignored)
- `*_ANALYSIS.md` - Temporary analysis docs
- `*_PLAN.md` - Temporary planning docs (unless feature-specific)
- `COMMIT_*.txt`, `COMMIT_*.md` - Temporary commit notes
- `*.log` - Log files (should be in `logs/` or gitignored)
- `data_integrity_report.json` - Temporary reports

---

## 📋 File Mapping

### Documentation Files
```
BACKLOG.md                          → docs/features/BACKLOG.md
BRANCH_CHANGES_SUMMARY.md           → docs/features/BRANCH_CHANGES_SUMMARY.md
BRANCH_TESTING_GUIDE.md             → docs/features/BRANCH_TESTING_GUIDE.md
CHANGES_SUMMARY.md                  → docs/features/CHANGES_SUMMARY.md
CHANGES_THIS_BRANCH.md              → docs/features/CHANGES_THIS_BRANCH.md
CLEANUP_PLAN.md                     → docs/maintenance/CLEANUP_PLAN.md
CODE_CHANGES_SUMMARY.md             → docs/features/CODE_CHANGES_SUMMARY.md
CRON_SECURITY_BEST_PRACTICES.md     → docs/security/CRON_SECURITY_BEST_PRACTICES.md
CRON_SETUP_GUIDE.md                 → docs/deployment/CRON_SETUP_GUIDE.md
DATABASE_SCHEMA_TIMEZONE.md         → docs/features/timezone/DATABASE_SCHEMA_TIMEZONE.md
DEBUGGING_ANALYSIS.md               → docs/features/DEBUGGING_ANALYSIS.md
DEFINITIVE_ANALYSIS.md              → docs/features/DEFINITIVE_ANALYSIS.md
DEFINITIVE_TEST_PLAN.md             → docs/features/DEFINITIVE_TEST_PLAN.md
DETECTION_LOGGING_IMPROVEMENTS.md   → docs/features/DETECTION_LOGGING_IMPROVEMENTS.md
DETECTION_TRACKING_ANALYSIS.md      → docs/features/DETECTION_TRACKING_ANALYSIS.md
DOCUMENTATION_AND_DEPLOYMENT_PLAN.md → docs/deployment/DOCUMENTATION_AND_DEPLOYMENT_PLAN.md
DRESS_REHEARSAL_ANALYSIS.md         → docs/features/nightly-cron/DRESS_REHEARSAL_ANALYSIS.md
FIXES_APPLIED.md                    → docs/features/FIXES_APPLIED.md
FIX_PLAN_PRE_DOWNLOAD_CHECK.md      → docs/features/FIX_PLAN_PRE_DOWNLOAD_CHECK.md
FIX_PROPOSAL.md                     → docs/features/FIX_PROPOSAL.md
FIX_VERIFICATION.md                 → docs/features/FIX_VERIFICATION.md
INSTALLATION.md                     → docs/deployment/INSTALLATION.md
MULTI_USER_TESTING_GUIDE.md         → docs/features/multi-user/MULTI_USER_TESTING_GUIDE.md
NEXT_FEATURE_BRANCH.md              → docs/features/NEXT_FEATURE_BRANCH.md
NIGHTLY_CRON_TODO.md                → docs/features/nightly-cron/NIGHTLY_CRON_TODO.md
PR_AND_DEPLOYMENT_CHECKLIST.md      → docs/deployment/PR_AND_DEPLOYMENT_CHECKLIST.md
PR_CHECKLIST.md                     → docs/deployment/PR_CHECKLIST.md
PR_DESCRIPTION.md                   → docs/features/PR_DESCRIPTION.md
PR_README.md                        → docs/features/PR_README.md
QUICK_TIMEZONE_UPDATE.md            → docs/features/timezone/QUICK_TIMEZONE_UPDATE.md
RECOMMENDATION_OPTION_B.md          → docs/features/RECOMMENDATION_OPTION_B.md
REGISTRATION_FLOW_EXPLANATION.md    → docs/features/multi-user/REGISTRATION_FLOW_EXPLANATION.md
REMOVE_ORPHAN_CLEANUP.md            → docs/maintenance/REMOVE_ORPHAN_CLEANUP.md
REMOVE_PATH_ENCRYPTION_PLAN.md      → docs/features/REMOVE_PATH_ENCRYPTION_PLAN.md
REPROCESS_DUPLICATE_ANALYSIS.md     → docs/features/REPROCESS_DUPLICATE_ANALYSIS.md
SECURITY_AUDIT_FULL.md              → docs/security/SECURITY_AUDIT_FULL.md
SECURITY_FIX_PLAN.md                → docs/security/SECURITY_FIX_PLAN.md
SECURITY_FIX_PR_SUMMARY.md          → docs/security/SECURITY_FIX_PR_SUMMARY.md
SECURITY_PRIORITIES.md              → docs/security/SECURITY_PRIORITIES.md
SECURITY_TRADEOFFS_ANALYSIS.md      → docs/security/SECURITY_TRADEOFFS_ANALYSIS.md
SIMPLIFIED_LOGGING.md               → docs/features/SIMPLIFIED_LOGGING.md
TEST_COMPARISON_ANALYSIS.md         → docs/features/TEST_COMPARISON_ANALYSIS.md
TEST_CRON_SETUP.md                  → docs/features/nightly-cron/TEST_CRON_SETUP.md
TIMEZONE_ANALYSIS_PLAN.md           → docs/features/timezone/TIMEZONE_ANALYSIS_PLAN.md
TIMEZONE_CRON_ANALYSIS.md           → docs/features/timezone/TIMEZONE_CRON_ANALYSIS.md
TIMEZONE_IMPLEMENTATION_PRIORITY.md → docs/features/timezone/TIMEZONE_IMPLEMENTATION_PRIORITY.md
TIMEZONE_IMPLEMENTATION_SUMMARY.md  → docs/features/timezone/TIMEZONE_IMPLEMENTATION_SUMMARY.md
TIMEZONE_TEST_PLAN.md               → docs/features/timezone/TIMEZONE_TEST_PLAN.md
TIMEZONE_TEST.md                    → docs/features/timezone/TIMEZONE_TEST.md
TIMEZONE_TESTING_PLAN.md            → docs/features/timezone/TIMEZONE_TESTING_PLAN.md
TRUE_DRESS_REHEARSAL_PLAN.md        → docs/features/nightly-cron/TRUE_DRESS_REHEARSAL_PLAN.md
UI_REPROCESS_FEATURE.md             → docs/features/UI_REPROCESS_FEATURE.md
VPS_DEPLOYMENT_PLAN.md              → docs/deployment/VPS_DEPLOYMENT_PLAN.md
```

### Utility Scripts
```
analyze_duplicates.py               → scripts/maintenance/analyze_duplicates.py
analyze_timestamp_offset.py         → scripts/maintenance/analyze_timestamp_offset.py
apply_laughter_classes_migration.py → scripts/setup/apply_laughter_classes_migration.py
check_clip_duplicates.py            → scripts/verification/check_clip_duplicates.py
check_clip_issue.py                 → scripts/verification/check_clip_issue.py
check_cron_status.sh                → scripts/verification/check_cron_status.sh
check_db_status.py                  → scripts/verification/check_db_status.py
check_earlier_processing.py         → scripts/verification/check_earlier_processing.py
check_file_paths.py                 → scripts/verification/check_file_paths.py
check_files.py                      → scripts/verification/check_files.py
check_laughter_classes.py           → scripts/verification/check_laughter_classes.py
check_limitless_timestamp_issue.py  → scripts/verification/check_limitless_timestamp_issue.py
check_orphaned_file.py              → scripts/verification/check_orphaned_file.py
check_orphans.py                    → scripts/verification/check_orphans.py
check_processing_logs.py            → scripts/verification/check_processing_logs.py
check_reprocess_results.py          → scripts/verification/check_reprocess_results.py
check_timezone_issue.py             → scripts/verification/check_timezone_issue.py
check_yamnet_classes.py             → scripts/verification/check_yamnet_classes.py
cleanup_date_data.py                → scripts/cleanup/cleanup_date_data.py
cleanup_duplicate_segments_v2.py    → scripts/cleanup/cleanup_duplicate_segments_v2.py
cleanup_duplicate_segments.py       → scripts/cleanup/cleanup_duplicate_segments.py
cleanup_existing_duplicates.py      → scripts/cleanup/cleanup_existing_duplicates.py
cleanup_for_pr.sh                   → scripts/maintenance/cleanup_for_pr.sh
cleanup_orphaned_audio.py           → scripts/cleanup/cleanup_orphaned_audio.py
cleanup_orphaned_files.py           → scripts/cleanup/cleanup_orphaned_files.py
cleanup_today_data.py               → scripts/cleanup/cleanup_today_data.py
compare_runs.py                     → scripts/verification/compare_runs.py
delete_test_user.py                 → scripts/maintenance/delete_test_user.py
deploy_duplicate_prevention.sh      → scripts/setup/deploy_duplicate_prevention.sh
fix_data_integrity.py               → scripts/maintenance/fix_data_integrity.py
fix_encrypted_paths.py              → scripts/maintenance/fix_encrypted_paths.py
fix_missing_detections_simple.py    → scripts/maintenance/fix_missing_detections_simple.py
fix_missing_detections.py           → scripts/maintenance/fix_missing_detections.py
fix_timestamps_properly.py          → scripts/maintenance/fix_timestamps_properly.py
manual_reprocess_yesterday.py       → scripts/maintenance/manual_reprocess_yesterday.py
monitor_data_integrity.py           → scripts/maintenance/monitor_data_integrity.py
monitor_duplicates.py               → scripts/maintenance/monitor_duplicates.py
process_nightly_audio.py            → scripts/maintenance/process_nightly_audio.py (or keep in root?)
reprocess_date.py                   → scripts/maintenance/reprocess_date.py
run_monitor.sh                      → scripts/maintenance/run_monitor.sh
start_fresh_script.py               → scripts/setup/start_fresh_script.py
start_scheduler.py                  → scripts/maintenance/start_scheduler.py
test_deletion_direct.py             → scripts/verification/test_deletion_direct.py
test_processing_flow.py             → scripts/verification/test_processing_flow.py
verify_11_5_giggles.py              → scripts/verification/verify_11_5_giggles.py
verify_cleanup.py                   → scripts/verification/verify_cleanup.py
verify_cron_results.py              → scripts/verification/verify_cron_results.py
verify_dress_rehearsal.py           → scripts/verification/verify_dress_rehearsal.py
verify_multi_user_isolation.py      → scripts/verification/verify_multi_user_isolation.py
```

### SQL Files
```
add_laughter_classes.sql                → scripts/setup/add_laughter_classes.sql
fix_duplicate_prevention_correct.sql    → scripts/setup/fix_duplicate_prevention_correct.sql
fix_duplicate_prevention.sql            → scripts/setup/fix_duplicate_prevention.sql
fix_unique_constraint_with_class_id.sql → scripts/setup/fix_unique_constraint_with_class_id.sql
migration_enhanced_logging.sql          → scripts/setup/migration_enhanced_logging.sql
REGISTRATION_FIX_FINAL.sql              → scripts/setup/REGISTRATION_FIX_FINAL.sql
setup_database.sql                      → scripts/setup/setup_database.sql
```

### Files to DELETE (temporary/obsolete)
```
COMMIT_FILES.txt
COMMIT_MESSAGE.md
cron_configuration.txt
data_integrity_report.json
OPTION_B_CODE_CHANGES.py
REGISTRATION_FIX_STEPS.md (merge into REGISTRATION_FLOW_EXPLANATION.md)
SECURITY_AUDIT_CRITIQUE.md.backup
server.log (should be in logs/ or gitignored)
```

---

## 🚀 Execution Strategy

### Phase 1: Create Directory Structure (Safe - No File Moves)
1. Create `docs/` subdirectories
2. Create `scripts/` subdirectories
3. Update `.gitignore` for temporary files

### Phase 2: Move Documentation (Preserves Git History)
1. Use `git mv` for all `.md` files
2. Commit on current branch

### Phase 3: Move Scripts (Preserves Git History)
1. Use `git mv` for all utility scripts
2. Commit on current branch

### Phase 4: Clean Up Temporary Files
1. Delete obsolete files
2. Update any references to moved files

### Phase 5: Update Documentation
1. Create `ROOT_FILES.md` explaining structure
2. Create `docs/README.md` as documentation index
3. Update main `README.md` with new structure

---

## ⚠️ Safety Measures

1. **Use `git mv`** - Preserves file history
2. **Commit on feature branch** - Don't affect main until merged
3. **Test after moves** - Verify scripts still work
4. **Keep backups** - Git history is the backup
5. **Update imports/references** - Fix any broken paths

---

## 📝 Git Operations Guide

### Safe Workflow

1. **Current State**: On `feature/multi-user-authentication-fix` branch
2. **Make Changes**: Organize files (this cleanup)
3. **Commit**: `git commit -m "refactor: organize files into docs/ and scripts/"`
4. **Test**: Verify everything still works
5. **Merge Strategy**: 
   - Option A: Merge this branch to main first, then merge other branches
   - Option B: Rebase other branches on top of organized structure

### Understanding Git Operations

- **Commit**: Saves changes to current branch (safe, local only)
- **Push**: Uploads branch to remote (safe, creates backup)
- **Merge**: Combines branches (can be undone if needed)
- **Publish Branch**: Same as push (creates remote copy)

### What's Safe to Do Now

✅ **SAFE:**
- Create directories
- Move files with `git mv`
- Commit changes
- Push branch (creates backup)
- Test locally

⚠️ **BE CAREFUL:**
- Merging to main (but can be undone)
- Force push (only if you know what you're doing)

---

## 🎯 Success Criteria

After cleanup:
- ✅ Root directory has < 15 files
- ✅ All docs in `docs/` with clear organization
- ✅ All utility scripts in `scripts/` with clear organization
- ✅ Easy to find feature-specific files
- ✅ Clear separation between mainline code and utilities
- ✅ Git history preserved for all moved files

