# Root Directory Files Guide

## 🎯 Purpose
This document explains which files belong in the root directory and why.

---

## ✅ Files That BELONG in Root

### Core Application Files
- `README.md` - Main project documentation (first file anyone reads)
- `requirements.txt` - Python dependencies (standard location)
- `setup.py` - Package setup (standard location)
- `env.example` - Environment variable template (standard location)
- `.gitignore` - Git ignore patterns (standard location)
- `docker-compose.yml` - Docker configuration (if used)
- `Dockerfile` - Docker image definition (if used)

### Runtime Configuration
- `process_nightly_audio.py` - Production cron job entry point
  - **Why**: Needs to be easily findable for cron jobs
  - **Alternative**: Could go in `scripts/maintenance/` but root is clearer for production

---

## 📁 Files That DON'T Belong in Root

### Documentation → `docs/`
All `*.md` files except `README.md` go in `docs/` organized by topic.

### Utility Scripts → `scripts/`
All `check_*.py`, `analyze_*.py`, `test_*.py`, `verify_*.py`, `cleanup_*.py`, `fix_*.py` scripts go in `scripts/` organized by purpose.

### SQL Files → `scripts/setup/`
All `*.sql` files go in `scripts/setup/` for database setup/migrations.

### Tests → `tests/`
Unit tests go in `tests/` directory (already exists).

---

## 🔍 Quick Reference

| File Type | Location | Reason |
|-----------|----------|--------|
| `README.md` | Root | First file anyone reads |
| `requirements.txt` | Root | Python standard |
| `setup.py` | Root | Python standard |
| `*.md` (docs) | `docs/` | Organized documentation |
| `check_*.py` | `scripts/verification/` | Verification scripts |
| `analyze_*.py` | `scripts/maintenance/` | Analysis tools |
| `test_*.py` (unit) | `tests/` | Unit tests |
| `test_*.py` (one-off) | `scripts/verification/` | Temporary tests |
| `cleanup_*.py` | `scripts/cleanup/` | Cleanup scripts |
| `*.sql` | `scripts/setup/` | Database scripts |
| `*.sh` | `scripts/` | Shell scripts |

---

## 🚫 Files That Should Be DELETED

These are temporary/obsolete and should be removed:
- `COMMIT_FILES.txt` - Temporary commit notes
- `COMMIT_MESSAGE.md` - Temporary commit message
- `cron_configuration.txt` - Temporary config
- `data_integrity_report.json` - Temporary report
- `OPTION_B_CODE_CHANGES.py` - Temporary code
- `server.log` - Should be in `logs/` or gitignored

---

## 📖 See Also

- `FILE_ORGANIZATION_PLAN.md` - Complete organization plan
- `docs/README.md` - Documentation index
- `README.md` - Main project documentation

