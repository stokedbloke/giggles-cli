# Database Schema: Timezone Behavior

**Last Updated:** 2025-11-04

## Overview

This document explains how timezones are handled for all database fields. The general principle is:
- **All timestamps are stored in UTC** (using `TIMESTAMPTZ` type)
- **Date fields are calendar dates** (interpreted in the user's timezone)
- **Display/processing converts UTC timestamps to user's timezone**

---

## Timestamp Fields (TIMESTAMPTZ - UTC)

All timestamp fields are stored in UTC and automatically converted by PostgreSQL:

### `users` table
- `created_at` (TIMESTAMPTZ) - **UTC**
- `updated_at` (TIMESTAMPTZ) - **UTC**

### `limitless_keys` table
- `created_at` (TIMESTAMPTZ) - **UTC**
- `updated_at` (TIMESTAMPTZ) - **UTC**

### `audio_segments` table
- `start_time` (TIMESTAMPTZ) - **UTC** - Start time of audio segment
- `end_time` (TIMESTAMPTZ) - **UTC** - End time of audio segment
- `created_at` (TIMESTAMPTZ) - **UTC**
- `updated_at` (TIMESTAMPTZ) - **UTC**

### `laughter_detections` table
- `timestamp` (TIMESTAMPTZ) - **UTC** - Exact time when laughter was detected
- `created_at` (TIMESTAMPTZ) - **UTC**
- `updated_at` (TIMESTAMPTZ) - **UTC**

### `processing_logs` table
- `last_processed` (TIMESTAMPTZ) - **UTC** - Last processed timestamp
- `created_at` (TIMESTAMPTZ) - **UTC**
- `updated_at` (TIMESTAMPTZ) - **UTC**

---

## Date Fields (DATE - User Timezone)

Date fields store calendar dates without time information. **These dates are interpreted in the user's timezone**, not UTC.

### `audio_segments` table
- `date` (DATE) - **User Timezone** - Calendar date of the audio segment
  - Example: For a user in PST, audio from Nov 3 08:00-10:00 UTC is stored with `date = '2025-11-03'` (Nov 3 PST)

### `processing_logs` table
- `date` (DATE) - **User Timezone** - Calendar date being processed
  - **CRITICAL:** The `date` field indicates which calendar date was processed (interpreted in the user's timezone)
  - Example: If processing "Nov 3 PST" (which spans Nov 3 08:00 UTC to Nov 4 08:00 UTC), the `date` field will be `'2025-11-03'` (Nov 3 in user's timezone)

---

## Non-Timezone Fields

### `users` table
- `timezone` (TEXT) - IANA timezone string (e.g., "America/Los_Angeles")
  - Used to interpret `date` fields and convert timestamps for display/processing
  - Default: 'UTC'

---

## Examples

### Example 1: Processing Nov 3 PST
**User timezone:** America/Los_Angeles (PST, UTC-8)

**Processing range:**
- Local: Nov 3 00:00 PST to Nov 3 23:59 PST
- UTC: Nov 3 08:00 UTC to Nov 4 08:00 UTC

**Database entries:**
- `audio_segments.date` = `'2025-11-03'` (Nov 3 in user's timezone)
- `audio_segments.start_time` = `'2025-11-03 08:00:00+00:00'` (UTC)
- `audio_segments.end_time` = `'2025-11-04 08:00:00+00:00'` (UTC)
- `processing_logs.date` = `'2025-11-03'` (Nov 3 in user's timezone)
- `processing_logs.last_processed` = `'2025-11-04 08:00:00+00:00'` (UTC)

### Example 2: Laughter Detection
**Laughter detected at:** Nov 3 18:00 PST

**Database entry:**
- `laughter_detections.timestamp` = `'2025-11-04 02:00:00+00:00'` (UTC)
- Display in UI: Converted to `'2025-11-03 18:00:00-08:00'` (PST)

---

## Key Takeaways

1. **All TIMESTAMPTZ fields are UTC** - PostgreSQL automatically stores and converts these
2. **All DATE fields are user timezone** - They represent calendar dates in the user's local timezone
3. **Always convert TIMESTAMPTZ to user timezone** when displaying to users
4. **Always convert user timezone dates to UTC** when querying TIMESTAMPTZ fields
5. **The `processing_logs.date` field indicates which calendar date was processed (interpreted in the user's timezone)**

