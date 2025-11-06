# Changes in ui-mobile-redesign Branch

## New Files Added
- `src/services/enhanced_logger.py` - Complete enhanced processing logger

## Modified Files

### 1. `src/services/scheduler.py`
**Key changes:**
- Added enhanced logger integration throughout
- Removed dead `_create_processing_log` method
- Added cleanup log clarity improvements
- Added API call tracking in `_process_date_range`

**In-line comments added** for:
- Enhanced logger initialization
- Date handling for reprocessing
- Terminology clarification (segments vs clips)
- Duplicate handling logic

### 2. `src/api/audio_routes.py`
**Key changes:**
- Added debug logging for trigger endpoint
- Added enhanced logger initialization

**In-line comments added** for:
- Processing flow
- Timezone usage

### 3. `static/js/app.js`
**Key changes:**
- Delete detection now refreshes home screen
- Enhanced timezone logging
- Reprocess button event delegation

**In-line comments added** for:
- Delete refresh fix
- Timezone detection

### 4. `manual_reprocess_yesterday.py`
**Key changes:**
- Date handling fix
- Enhanced logger integration

**In-line comments added** for:
- Single log per date range behavior

---

## Database Changes Needed

Run these SQL migrations:
1. `enhance_processing_logs.sql` - Adds all new columns
2. `add_duplicates_column.sql` - Adds missing duplicates_skipped
3. `drop_old_columns.sql` - Removes deprecated columns


