-- ==================================================
-- DUPLICATE PREVENTION FIXES FOR GIGGLES SYSTEM
-- ==================================================
-- This script implements robust duplicate prevention
-- for laughter detections and audio clips at the database level

-- 1. ADD UNIQUE CONSTRAINTS FOR LAUGHTER DETECTIONS
-- ==================================================

-- Add unique constraint on timestamp + user_id (prevents exact timestamp duplicates)
ALTER TABLE public.laughter_detections 
ADD CONSTRAINT unique_laughter_timestamp_user 
UNIQUE (user_id, timestamp);

-- Add unique constraint on clip_path (prevents duplicate clip files)
ALTER TABLE public.laughter_detections 
ADD CONSTRAINT unique_laughter_clip_path 
UNIQUE (clip_path);

-- 2. ADD INDEXES FOR PERFORMANCE
-- ==================================================

-- Index for time-based duplicate detection queries
CREATE INDEX IF NOT EXISTS idx_laughter_detections_user_timestamp 
ON public.laughter_detections (user_id, timestamp);

-- Index for clip path uniqueness checks
CREATE INDEX IF NOT EXISTS idx_laughter_detections_clip_path 
ON public.laughter_detections (clip_path);

-- Index for overlapping segment detection
CREATE INDEX IF NOT EXISTS idx_audio_segments_user_time 
ON public.audio_segments (user_id, start_time, end_time);

-- 3. ADD COMPOSITE INDEXES FOR COMPLEX QUERIES
-- ==================================================

-- Index for time window duplicate detection
CREATE INDEX IF NOT EXISTS idx_laughter_detections_user_time_window 
ON public.laughter_detections (user_id, timestamp, probability);

-- Index for segment overlap detection
CREATE INDEX IF NOT EXISTS idx_audio_segments_overlap_detection 
ON public.audio_segments (user_id, start_time, end_time, processed);

-- 4. ADD TRIGGERS FOR AUTOMATIC DUPLICATE PREVENTION
-- ==================================================

-- Function to prevent duplicate laughter detections
CREATE OR REPLACE FUNCTION prevent_duplicate_laughter()
RETURNS TRIGGER AS $$
BEGIN
    -- Check for existing laughter detection within 5-second window
    IF EXISTS (
        SELECT 1 FROM public.laughter_detections 
        WHERE user_id = NEW.user_id 
        AND ABS(EXTRACT(EPOCH FROM (timestamp - NEW.timestamp))) <= 5
        AND probability >= NEW.probability * 0.9  -- Allow 10% variance in probability
    ) THEN
        -- If duplicate found, keep the one with higher probability
        IF EXISTS (
            SELECT 1 FROM public.laughter_detections 
            WHERE user_id = NEW.user_id 
            AND ABS(EXTRACT(EPOCH FROM (timestamp - NEW.timestamp))) <= 5
            AND probability > NEW.probability
        ) THEN
            -- Delete the new record (lower probability)
            RETURN NULL;
        ELSE
            -- Delete the existing record (lower probability)
            DELETE FROM public.laughter_detections 
            WHERE user_id = NEW.user_id 
            AND ABS(EXTRACT(EPOCH FROM (timestamp - NEW.timestamp))) <= 5
            AND probability < NEW.probability;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for duplicate prevention
DROP TRIGGER IF EXISTS prevent_duplicate_laughter_trigger ON public.laughter_detections;
CREATE TRIGGER prevent_duplicate_laughter_trigger
    BEFORE INSERT ON public.laughter_detections
    FOR EACH ROW
    EXECUTE FUNCTION prevent_duplicate_laughter();

-- 5. ADD CLEANUP FUNCTIONS
-- ==================================================

-- Function to clean up existing duplicates
CREATE OR REPLACE FUNCTION cleanup_duplicate_laughter()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
BEGIN
    -- Delete duplicate laughter detections (keep highest probability)
    WITH duplicates AS (
        SELECT id, 
               ROW_NUMBER() OVER (
                   PARTITION BY user_id, 
                   DATE_TRUNC('second', timestamp), 
                   ROUND(probability::numeric, 2)
                   ORDER BY probability DESC, created_at ASC
               ) as rn
        FROM public.laughter_detections
    )
    DELETE FROM public.laughter_detections 
    WHERE id IN (
        SELECT id FROM duplicates WHERE rn > 1
    );
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 6. ADD MONITORING FUNCTIONS
-- ==================================================

-- Function to detect potential duplicates
CREATE OR REPLACE FUNCTION detect_potential_duplicates()
RETURNS TABLE (
    user_id UUID,
    duplicate_count BIGINT,
    time_range TEXT,
    avg_probability NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ld.user_id,
        COUNT(*) as duplicate_count,
        CONCAT(
            MIN(ld.timestamp)::text, ' to ', 
            MAX(ld.timestamp)::text
        ) as time_range,
        AVG(ld.probability) as avg_probability
    FROM public.laughter_detections ld
    WHERE ld.timestamp IN (
        SELECT timestamp 
        FROM public.laughter_detections 
        GROUP BY user_id, timestamp 
        HAVING COUNT(*) > 1
    )
    GROUP BY ld.user_id, DATE_TRUNC('minute', ld.timestamp)
    HAVING COUNT(*) > 1
    ORDER BY duplicate_count DESC;
END;
$$ LANGUAGE plpgsql;

-- 7. ADD RLS POLICIES FOR NEW CONSTRAINTS
-- ==================================================

-- Update RLS policies to work with new constraints
DROP POLICY IF EXISTS "Users can insert own laughter detections" ON public.laughter_detections;
CREATE POLICY "Users can insert own laughter detections" ON public.laughter_detections
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- 8. ADD PERFORMANCE MONITORING
-- ==================================================

-- Create view for duplicate monitoring
CREATE OR REPLACE VIEW duplicate_monitoring AS
SELECT 
    user_id,
    COUNT(*) as total_detections,
    COUNT(DISTINCT timestamp) as unique_timestamps,
    COUNT(*) - COUNT(DISTINCT timestamp) as potential_duplicates,
    ROUND(
        (COUNT(*) - COUNT(DISTINCT timestamp))::numeric / COUNT(*) * 100, 
        2
    ) as duplicate_percentage
FROM public.laughter_detections
GROUP BY user_id
HAVING COUNT(*) > COUNT(DISTINCT timestamp);

-- 9. GRANT PERMISSIONS
-- ==================================================

-- Grant necessary permissions for new functions
GRANT EXECUTE ON FUNCTION prevent_duplicate_laughter() TO authenticated;
GRANT EXECUTE ON FUNCTION cleanup_duplicate_laughter() TO authenticated;
GRANT EXECUTE ON FUNCTION detect_potential_duplicates() TO authenticated;
GRANT SELECT ON duplicate_monitoring TO authenticated;

-- 10. ADD COMMENTS FOR DOCUMENTATION
-- ==================================================

COMMENT ON CONSTRAINT unique_laughter_timestamp_user ON public.laughter_detections IS 
'Prevents duplicate laughter detections for the same user at the same timestamp';

COMMENT ON CONSTRAINT unique_laughter_clip_path ON public.laughter_detections IS 
'Prevents duplicate audio clip files';

COMMENT ON FUNCTION prevent_duplicate_laughter() IS 
'Automatically prevents duplicate laughter detections within 5-second windows';

COMMENT ON FUNCTION cleanup_duplicate_laughter() IS 
'Cleans up existing duplicate laughter detections, keeping highest probability';

COMMENT ON FUNCTION detect_potential_duplicates() IS 
'Detects potential duplicate laughter detections for monitoring';

COMMENT ON VIEW duplicate_monitoring IS 
'Monitoring view for duplicate laughter detection analysis';
