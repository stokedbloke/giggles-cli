-- Add laughter class information to laughter_detections table
-- This migration adds fields to store YAMNet class information

-- Add new columns to laughter_detections table
ALTER TABLE public.laughter_detections 
ADD COLUMN IF NOT EXISTS class_id INTEGER,
ADD COLUMN IF NOT EXISTS class_name TEXT;

-- Add comment for documentation
COMMENT ON COLUMN public.laughter_detections.class_id IS 'YAMNet class ID for the detected laughter type';
COMMENT ON COLUMN public.laughter_detections.class_name IS 'YAMNet class name for the detected laughter type (e.g., "Laughter", "Giggle", "Belly laugh")';

-- Create index for better performance when filtering by class
CREATE INDEX IF NOT EXISTS idx_laughter_detections_class_id ON public.laughter_detections(class_id);
CREATE INDEX IF NOT EXISTS idx_laughter_detections_class_name ON public.laughter_detections(class_name);
