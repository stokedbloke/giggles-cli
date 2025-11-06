# Documentation Index

This directory contains all project documentation organized by topic.

---

## 📁 Directory Structure

```
docs/
├── deployment/        # Deployment guides and checklists
├── security/          # Security documentation and audits
├── features/          # Feature-specific documentation
│   ├── nightly-cron/ # Nightly cron job feature
│   ├── multi-user/   # Multi-user authentication feature
│   └── timezone/     # Timezone handling feature
└── maintenance/       # Maintenance and cleanup guides
```

---

## 🚀 Quick Links

### Deployment
- [VPS Deployment Plan](../docs/deployment/VPS_DEPLOYMENT_PLAN.md)
- [Cron Setup Guide](../docs/deployment/CRON_SETUP_GUIDE.md)
- [Installation Guide](../docs/deployment/INSTALLATION.md)
- [PR and Deployment Checklist](../docs/deployment/PR_AND_DEPLOYMENT_CHECKLIST.md)

### Security
- [Security Audit](../docs/security/SECURITY_AUDIT_FULL.md)
- [Security Priorities](../docs/security/SECURITY_PRIORITIES.md)
- [Security Fix Plan](../docs/security/SECURITY_FIX_PLAN.md)
- [Security Tradeoffs Analysis](../docs/security/SECURITY_TRADEOFFS_ANALYSIS.md)

### Features

#### Nightly Cron
- [Dress Rehearsal Analysis](../docs/features/nightly-cron/DRESS_REHEARSAL_ANALYSIS.md)
- [Nightly Cron TODO](../docs/features/nightly-cron/NIGHTLY_CRON_TODO.md)
- [Test Cron Setup](../docs/features/nightly-cron/TEST_CRON_SETUP.md)
- [True Dress Rehearsal Plan](../docs/features/nightly-cron/TRUE_DRESS_REHEARSAL_PLAN.md)

#### Multi-User
- [Multi-User Testing Guide](../docs/features/multi-user/MULTI_USER_TESTING_GUIDE.md)
- [Registration Flow Explanation](../docs/features/multi-user/REGISTRATION_FLOW_EXPLANATION.md)

#### Timezone
- [Database Schema Timezone](../docs/features/timezone/DATABASE_SCHEMA_TIMEZONE.md)
- [Timezone Analysis Plan](../docs/features/timezone/TIMEZONE_ANALYSIS_PLAN.md)
- [Timezone Implementation Summary](../docs/features/timezone/TIMEZONE_IMPLEMENTATION_SUMMARY.md)
- [Timezone Testing Plan](../docs/features/timezone/TIMEZONE_TESTING_PLAN.md)

### Maintenance
- [Cleanup Plan](../docs/maintenance/CLEANUP_PLAN.md)
- [Remove Orphan Cleanup](../docs/maintenance/REMOVE_ORPHAN_CLEANUP.md)

---

## 📝 Documentation Standards

### File Naming
- Use `UPPERCASE_WITH_UNDERSCORES.md` for main documents
- Use descriptive names that indicate purpose
- Group related files in subdirectories

### Content Standards
- Start with purpose/overview
- Include relevant context
- Use clear headings and structure
- Link to related documents
- Keep up to date

---

## 🔄 Updating Documentation

When adding new documentation:
1. Place in appropriate subdirectory
2. Update this README with link
3. Use descriptive filename
4. Follow content standards
5. Commit with clear message

---

## 📚 See Also

- [Main README](../README.md) - Project overview
- [Root Files Guide](../ROOT_FILES.md) - What belongs in root
- [File Organization Plan](../FILE_ORGANIZATION_PLAN.md) - Complete organization guide

