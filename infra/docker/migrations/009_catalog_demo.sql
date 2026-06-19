-- MVP+1: pre-generated catalog demo audio

ALTER TABLE voice_catalog_entries
    ADD COLUMN IF NOT EXISTS demo_text TEXT NOT NULL DEFAULT '';

ALTER TABLE voice_catalog_entries
    ADD COLUMN IF NOT EXISTS demo_audio_url TEXT;

ALTER TABLE voice_catalog_entries
    ADD COLUMN IF NOT EXISTS demo_job_id UUID;
