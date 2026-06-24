-- REQ-025: persistent audio fingerprints for export traceability

CREATE TABLE IF NOT EXISTS audio_fingerprints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    voice_id UUID,
    storage_url TEXT,
    digest VARCHAR(64) NOT NULL,
    hashes_json JSONB NOT NULL DEFAULT '[]',
    hash_count INT NOT NULL DEFAULT 0,
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audio_fingerprints_job ON audio_fingerprints(job_id);
CREATE INDEX IF NOT EXISTS idx_audio_fingerprints_user ON audio_fingerprints(user_id, enrolled_at DESC);
CREATE INDEX IF NOT EXISTS idx_audio_fingerprints_digest ON audio_fingerprints(digest);
