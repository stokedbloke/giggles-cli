# UI Reprocess Date Range Feature

## Summary

Added a UI button in the Settings screen to reprocess date ranges, eliminating the need for a separate manual script. This provides a unified interface and ensures consistency.

## Changes Made

### 1. **API Endpoint** (`src/api/data_routes.py`)
- Added `/api/reprocess-date-range` POST endpoint
- Accepts `ReprocessDateRangeRequest` with `start_date` and `end_date`
- Reuses `manual_reprocess_yesterday.reprocess_date_range()` function
- Properly authenticated and validated

### 2. **Frontend UI** (`templates/index.html`)
- Added "Reprocess Data" section in Settings screen
- Two date input fields (start and end)
- Reprocess button with status display area
- Help text explaining the feature

### 3. **Frontend Handler** (`static/js/app.js`)
- Added `handleReprocessDateRange()` method
- Validates dates (not empty, start < end)
- Shows confirmation dialog
- Displays progress and status
- Refreshes daily summary after completion

### 4. **Styling** (`static/css/style.css`)
- Added styles for reprocess form
- Status message styling (info, success, error)
- Consistent with existing settings UI

### 5. **Data Model** (`src/models/audio.py`)
- Added `ReprocessDateRangeRequest` Pydantic model
- Validates date format (YYYY-MM-DD)

## Benefits

✅ **Single code path** - Both UI and script use same `reprocess_date_range()` function  
✅ **Better UX** - No need to SSH or run commands manually  
✅ **Consistent** - Same authentication and validation as other endpoints  
✅ **Maintainable** - One function to maintain instead of two separate implementations  
✅ **Safe** - Confirmation dialog prevents accidental reprocessing  

## Usage

1. Navigate to Settings screen
2. Scroll to "Reprocess Data" section
3. Select start and end dates
4. Click "Reprocess Date Range"
5. Confirm the action
6. Wait for completion (may take several minutes)
7. Daily summary refreshes automatically

## Note

The `manual_reprocess_yesterday.py` script can still be used for command-line access if needed, but the UI provides the same functionality with better user experience.

