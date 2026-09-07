-- 1. Conversations table
CREATE TABLE IF NOT EXISTS public.conversations (
    user_id TEXT PRIMARY KEY,
    user_name TEXT,
    channel_id TEXT,
    channel_type TEXT DEFAULT 'DM',
    profile JSONB DEFAULT '{}'::jsonb,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    total_messages INT DEFAULT 0,
    ai_replies INT DEFAULT 0,
    ai_disabled BOOLEAN DEFAULT FALSE,
    chat_mode TEXT DEFAULT 'human',
    busy_notice_sent BOOLEAN DEFAULT FALSE,
    messages JSONB DEFAULT '[]'::jsonb
);

-- 2. Global Bot State & Settings table
CREATE TABLE IF NOT EXISTS public.bot_state (
    key TEXT PRIMARY KEY,
    value JSONB
);

-- Default state values
INSERT INTO public.bot_state (key, value) VALUES
    ('afk_mode', 'true'::jsonb),
    ('busy_message', '"SAHAL_PRO is busy and working on something"'::jsonb),
    ('rpc_config', '{"enabled": true, "activity_type": "playing", "name": "Writing assignment", "status": "dnd"}'::jsonb),
    ('stats', '{"total_conversations": 0, "total_messages": 0, "total_ai_replies": 0}'::jsonb),
    ('last_sync', 'null'::jsonb),
    ('pending_messages', '[]'::jsonb),
    ('pending_music_commands', '[]'::jsonb),
    ('scan_chats_requested', 'false'::jsonb)
ON CONFLICT (key) DO NOTHING;

-- 3. Storage bucket for deleted images and videos
INSERT INTO storage.buckets (id, name, public) 
VALUES ('media', 'media', true)
ON CONFLICT (id) DO UPDATE SET public = true;

-- Public read access for media
CREATE POLICY "Public media read access" ON storage.objects
FOR SELECT USING (bucket_id = 'media');

-- Insert/Upload access for media
CREATE POLICY "Allow media uploads" ON storage.objects
FOR INSERT WITH CHECK (bucket_id = 'media');

CREATE POLICY "Allow media updates" ON storage.objects
FOR UPDATE USING (bucket_id = 'media');
