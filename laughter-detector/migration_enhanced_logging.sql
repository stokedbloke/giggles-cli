-- Enhanced Processing Logs Schema Changes
-- Run this on your production database to add enhanced logging capabilities
--
-- PURPOSE: Replaces the old processed_segments/total_segments fields with direct
-- counters that accurately track what actually happened during processing.
-- These fields are populated by EnhancedProcessingLogger.save_to_database() which
-- is called after each processing session completes (manual trigger, scheduled, or cron).
--
-- TRIGGERS:
-- - save_to_database() is called from scheduler._process_user_audio() after processing completes
-- - Also called from manual_reprocess_yesterday.py after reprocessing date ranges
-- - Creates or updates ONE row per (user_id, date) combination per processing session

-- Add new columns to processing_logs table for detailed tracking
ALTER TABLE public.processing_logs
ADD COLUMN IF NOT EXISTS processing_steps JSONB DEFAULT '[]'::jsonb,  -- DEPRECATED: No longer populated, kept for backward compatibility
ADD COLUMN IF NOT EXISTS api_calls JSONB DEFAULT '[]'::jsonb,  -- Array of Limitless API calls (populated by enhanced_logger.add_api_call())
ADD COLUMN IF NOT EXISTS error_details JSONB DEFAULT '{}'::jsonb,  -- Error information (populated by enhanced_logger.add_error())
ADD COLUMN IF NOT EXISTS trigger_type TEXT DEFAULT 'manual' CHECK (trigger_type IN ('manual', 'scheduled', 'cron')),  -- How processing was triggered
ADD COLUMN IF NOT EXISTS processing_duration_seconds INTEGER DEFAULT 0,  -- Total time in seconds (calculated from logger start_time to save_to_database() call)
ADD COLUMN IF NOT EXISTS audio_files_downloaded INTEGER DEFAULT 0,  -- Count of OGG files downloaded from Limitless API (incremented by limitless_api._fetch_audio_segments())
ADD COLUMN IF NOT EXISTS laughter_events_found INTEGER DEFAULT 0,  -- Total laughter events detected by YAMNet (set by scheduler._store_laughter_detections())
ADD COLUMN IF NOT EXISTS duplicates_skipped INTEGER DEFAULT 0;  -- Total duplicates prevented (sum of time_window + clip_path + missing_file skips)

-- Add comments for documentation
COMMENT ON COLUMN public.processing_logs.processing_steps IS 'Array of processing steps with timestamps and status';
COMMENT ON COLUMN public.processing_logs.api_calls IS 'Array of Limitless API calls with response codes and details';
COMMENT ON COLUMN public.processing_logs.error_details IS 'Detailed error information including stack traces';
COMMENT ON COLUMN public.processing_logs.trigger_type IS 'How the processing was triggered (manual, scheduled, cron)';
COMMENT ON COLUMN public.processing_logs.processing_duration_seconds IS 'Total processing time in seconds';
COMMENT ON COLUMN public.processing_logs.audio_files_downloaded IS 'Number of audio files successfully downloaded';
COMMENT ON COLUMN public.processing_logs.laughter_events_found IS 'Number of laughter events detected';
COMMENT ON COLUMN public.processing_logs.duplicates_skipped IS 'Number of duplicates prevented (time-window + clip-path + missing-file)';

-- Create indexes on processing_steps for better querying
CREATE INDEX IF NOT EXISTS idx_processing_logs_steps ON public.processing_logs USING GIN (processing_steps);
CREATE INDEX IF NOT EXISTS idx_processing_logs_api_calls ON public.processing_logs USING GIN (api_calls);
CREATE INDEX IF NOT EXISTS idx_processing_logs_trigger_type ON public.processing_logs (trigger_type);

-- Now drop the deprecated columns (processed_segments and total_segments were confusing and inaccurate)
-- These were replaced by audio_files_downloaded and laughter_events_found for clarity
ALTER TABLE public.processing_logs 
DROP COLUMN IF EXISTS processed_segments,
DROP COLUMN IF EXISTS total_segments;
