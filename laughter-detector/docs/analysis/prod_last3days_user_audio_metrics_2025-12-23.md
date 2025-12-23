# Prod: last 3 days per-user audio/YAMNet/laughter metrics (2025-12-23)

This note is **for you** to run in the **Supabase production SQL editor** (read-only).

## What this returns

For **each user** and **each of the last 3 `date` values** (as stored in `processing_logs.date` / `audio_segments.date`), it returns:

- `laughs_detected`: count of rows in `laughter_detections` tied to segments for that day (this is what the UI typically reflects).
- `segments_processed`: count of `audio_segments` with `processed = true` (a practical proxy for “audio that was run through YAMNet end-to-end” in this codebase).
- `processing_log_audio_files_downloaded`: the `processing_logs.audio_files_downloaded` value (Limitless audio files successfully downloaded).
- `processing_log_yamnet_laughter_events_found`: the `processing_logs.laughter_events_found` value (raw YAMNet detections **before** duplicate filtering).
- `processing_log_duplicates_skipped`: the `processing_logs.duplicates_skipped` value (duplicates/missing-file skips tracked by the enhanced logger).

It also includes user `email` and `processing_log_status/trigger_type/updated_at`.

## SQL (paste into Supabase SQL editor)

```sql
WITH user_days AS (
  -- Build the set of (user_id, date) pairs we care about from the last 3 days.
  SELECT DISTINCT user_id, date
  FROM public.processing_logs
  WHERE date >= current_date - 2
  UNION
  SELECT DISTINCT user_id, date
  FROM public.audio_segments
  WHERE date >= current_date - 2
),
latest_processing_logs AS (
  -- If multiple rows exist for the same (user_id, date), keep the most recently updated one.
  SELECT DISTINCT ON (user_id, date)
    user_id,
    date,
    status,
    trigger_type,
    audio_files_downloaded,
    laughter_events_found,
    duplicates_skipped,
    created_at,
    updated_at
  FROM public.processing_logs
  WHERE date >= current_date - 2
  ORDER BY user_id, date, updated_at DESC NULLS LAST, created_at DESC
),
segment_counts AS (
  SELECT
    user_id,
    date,
    COUNT(*) AS segments_total,
    COUNT(*) FILTER (WHERE processed IS TRUE) AS segments_processed
  FROM public.audio_segments
  WHERE date >= current_date - 2
  GROUP BY user_id, date
),
laughter_counts AS (
  -- Group laughter detections by the segment's calendar date (audio_segments.date).
  SELECT
    s.user_id,
    s.date,
    COUNT(d.id) AS laughs_detected,
    COUNT(d.id) FILTER (WHERE s.processed IS TRUE) AS laughs_in_processed_segments
  FROM public.audio_segments AS s
  LEFT JOIN public.laughter_detections AS d
    ON d.audio_segment_id = s.id
  WHERE s.date >= current_date - 2
  GROUP BY s.user_id, s.date
)
SELECT
  ud.date,
  ud.user_id,
  u.email,

  COALESCE(sc.segments_total, 0) AS segments_total,
  COALESCE(sc.segments_processed, 0) AS segments_processed,

  COALESCE(lc.laughs_detected, 0) AS laughs_detected,
  COALESCE(lc.laughs_in_processed_segments, 0) AS laughs_in_processed_segments,

  pl.audio_files_downloaded AS processing_log_audio_files_downloaded,
  pl.laughter_events_found AS processing_log_yamnet_laughter_events_found,
  pl.duplicates_skipped AS processing_log_duplicates_skipped,
  pl.status AS processing_log_status,
  pl.trigger_type AS processing_log_trigger_type,
  pl.updated_at AS processing_log_updated_at
FROM user_days AS ud
LEFT JOIN public.users AS u
  ON u.id = ud.user_id
LEFT JOIN segment_counts AS sc
  ON sc.user_id = ud.user_id AND sc.date = ud.date
LEFT JOIN laughter_counts AS lc
  ON lc.user_id = ud.user_id AND lc.date = ud.date
LEFT JOIN latest_processing_logs AS pl
  ON pl.user_id = ud.user_id AND pl.date = ud.date
ORDER BY ud.date DESC, u.email NULLS LAST, ud.user_id;
```

## Notes / interpretation

- `processing_logs.laughter_events_found` is incremented from YAMNet **before** duplicate filtering; the UI is usually based on stored rows in `laughter_detections` (reported here as `laughs_detected`).
- If you see `segments_processed > 0` but `processing_log_audio_files_downloaded` is `NULL`, it usually means there was no (recent) processing log row for that day, or it was never written/updated.

