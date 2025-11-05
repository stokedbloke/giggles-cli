-- Giggles Database Setup Script
-- Run this in your Supabase SQL Editor

-- Note: JWT secret is managed by Supabase automatically

-- Create users table (extends Supabase auth.users)
CREATE TABLE IF NOT EXISTS public.users (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    timezone TEXT DEFAULT 'UTC',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create limitless_keys table
CREATE TABLE IF NOT EXISTS public.limitless_keys (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
    encrypted_api_key TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create audio_segments table
-- TIMEZONE NOTE: The 'date' field is a calendar date interpreted in the user's timezone
-- The start_time and end_time fields are UTC timestamps
CREATE TABLE IF NOT EXISTS public.audio_segments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
    date DATE NOT NULL, -- Calendar date in user's timezone (see TIMEZONE NOTE above)
    start_time TIMESTAMPTZ NOT NULL, -- UTC timestamp
    end_time TIMESTAMPTZ NOT NULL, -- UTC timestamp
    file_path TEXT NOT NULL, -- Encrypted file path
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(), -- UTC timestamp
    updated_at TIMESTAMPTZ DEFAULT NOW() -- UTC timestamp
);

-- Create laughter_detections table
CREATE TABLE IF NOT EXISTS public.laughter_detections (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
    audio_segment_id UUID REFERENCES public.audio_segments(id) ON DELETE CASCADE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    probability DECIMAL(5,4) NOT NULL CHECK (probability >= 0 AND probability <= 1),
    clip_path TEXT NOT NULL, -- Encrypted file path
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create processing_logs table for tracking
-- TIMEZONE NOTE: The 'date' field is a calendar date interpreted in the user's timezone
-- For example, processing "Nov 3 PST" (which spans Nov 3 08:00 UTC to Nov 4 08:00 UTC) 
-- will have date = '2025-11-03' (Nov 3 in user's timezone)
CREATE TABLE IF NOT EXISTS public.processing_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
    date DATE NOT NULL, -- Calendar date in user's timezone (see TIMEZONE NOTE above)
    status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    message TEXT,
    processed_segments INTEGER DEFAULT 0,
    total_segments INTEGER DEFAULT 0,
    last_processed TIMESTAMPTZ, -- UTC timestamp
    created_at TIMESTAMPTZ DEFAULT NOW(), -- UTC timestamp
    updated_at TIMESTAMPTZ DEFAULT NOW() -- UTC timestamp
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_limitless_keys_user_id ON public.limitless_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_audio_segments_user_id ON public.audio_segments(user_id);
CREATE INDEX IF NOT EXISTS idx_audio_segments_date ON public.audio_segments(date);
CREATE INDEX IF NOT EXISTS idx_laughter_detections_user_id ON public.laughter_detections(user_id);
CREATE INDEX IF NOT EXISTS idx_laughter_detections_timestamp ON public.laughter_detections(timestamp);
CREATE INDEX IF NOT EXISTS idx_processing_logs_user_id ON public.processing_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_date ON public.processing_logs(date);

-- Enable Row Level Security (RLS) on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.limitless_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audio_segments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.laughter_detections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.processing_logs ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for users table
CREATE POLICY "Users can view own profile" ON public.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.users
    FOR UPDATE USING (auth.uid() = id);

-- Create RLS policies for limitless_keys table
CREATE POLICY "Users can view own API keys" ON public.limitless_keys
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own API keys" ON public.limitless_keys
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own API keys" ON public.limitless_keys
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own API keys" ON public.limitless_keys
    FOR DELETE USING (auth.uid() = user_id);

-- Create RLS policies for audio_segments table
CREATE POLICY "Users can view own audio segments" ON public.audio_segments
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own audio segments" ON public.audio_segments
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own audio segments" ON public.audio_segments
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own audio segments" ON public.audio_segments
    FOR DELETE USING (auth.uid() = user_id);

-- Create RLS policies for laughter_detections table
CREATE POLICY "Users can view own laughter detections" ON public.laughter_detections
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own laughter detections" ON public.laughter_detections
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own laughter detections" ON public.laughter_detections
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own laughter detections" ON public.laughter_detections
    FOR DELETE USING (auth.uid() = user_id);

-- Create RLS policies for processing_logs table
CREATE POLICY "Users can view own processing logs" ON public.processing_logs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own processing logs" ON public.processing_logs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own processing logs" ON public.processing_logs
    FOR UPDATE USING (auth.uid() = user_id);

-- Create function to automatically create user profile
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, email, is_active, mfa_enabled)
    VALUES (NEW.id, NEW.email, TRUE, TRUE);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger to automatically create user profile on signup
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_limitless_keys_updated_at
    BEFORE UPDATE ON public.limitless_keys
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_audio_segments_updated_at
    BEFORE UPDATE ON public.audio_segments
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_laughter_detections_updated_at
    BEFORE UPDATE ON public.laughter_detections
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_processing_logs_updated_at
    BEFORE UPDATE ON public.processing_logs
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;
