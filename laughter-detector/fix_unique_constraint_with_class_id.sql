-- Fix unique constraint to include class_id
-- This allows different laughter types (e.g., class_id 13 and 15) at the same timestamp
-- to be stored as separate detections
--
-- BACKGROUND: YAMNet can detect multiple laughter classes at the same timestamp
-- (e.g., "Laughter" class_id=13 and "Giggle" class_id=15). The old constraint
-- (user_id, timestamp) prevented storing both, causing valid detections to be skipped.
--
-- NEW BEHAVIOR: Same user_id + timestamp is only a duplicate if class_id is also the same.
-- Different class_ids at the same timestamp are treated as unique detections.
--
-- TRIGGER: This constraint is checked during scheduler._store_laughter_detections()
-- when inserting into laughter_detections table. Violations are caught and handled
-- gracefully (see scheduler.py line 619-623).

-- Drop the old constraint that only checked (user_id, timestamp)
ALTER TABLE public.laughter_detections 
DROP CONSTRAINT IF EXISTS unique_laughter_timestamp_user;

-- Add new constraint that includes class_id
-- This allows same timestamp + user_id if class_id is different
-- CONSTRAINT NAME: unique_laughter_timestamp_user_class
-- FIELDS: (user_id, timestamp, class_id) - all three must match for a duplicate
ALTER TABLE public.laughter_detections 
ADD CONSTRAINT unique_laughter_timestamp_user_class 
UNIQUE (user_id, timestamp, class_id);

-- Add comment for documentation
COMMENT ON CONSTRAINT unique_laughter_timestamp_user_class ON public.laughter_detections IS 
'Prevents duplicate laughter detections for the same user at the same timestamp with the same class_id. Allows different class_ids (e.g., Laughter vs Giggle) at the same timestamp.';
