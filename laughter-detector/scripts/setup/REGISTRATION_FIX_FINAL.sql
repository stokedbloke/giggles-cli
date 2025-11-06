-- FINAL SQL: Run this in Supabase SQL Editor
-- This fixes the registration RLS issue by adding INSERT policy and removing trigger

-- Step 1: Add INSERT RLS policy (allows users to insert their own profile)
CREATE POLICY "Users can insert own profile" ON public.users
    FOR INSERT WITH CHECK (auth.uid() = id);

-- Step 2: Remove trigger (prevents duplicate key errors when backend also inserts)
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Step 3: Drop the function (optional cleanup, but recommended)
DROP FUNCTION IF EXISTS public.handle_new_user();

