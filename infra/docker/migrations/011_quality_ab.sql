-- REQ-006: voice quality reports + blind AB votes

CREATE TABLE IF NOT EXISTS voice_quality_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    voice_version_id UUID NOT NULL UNIQUE,
    owner_user_id UUID NOT NULL,
    similarity_score DOUBLE PRECISION NOT NULL,
    quality_pass BOOLEAN NOT NULL DEFAULT FALSE,
    threshold DOUBLE PRECISION NOT NULL DEFAULT 0.90,
    eval_sentence TEXT NOT NULL DEFAULT '',
    ref_audio_url TEXT,
    synth_audio_url TEXT,
    method VARCHAR(64) NOT NULL DEFAULT 'mock_embedding',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quality_reports_owner ON voice_quality_reports(owner_user_id);

CREATE TABLE IF NOT EXISTS ab_votes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    voice_version_id UUID NOT NULL,
    voter_user_id UUID NOT NULL,
    pick_slot VARCHAR(8) NOT NULL,
    slot_a_kind VARCHAR(8) NOT NULL,
    slot_b_kind VARCHAR(8) NOT NULL,
    picked_kind VARCHAR(8) NOT NULL,
    score INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ab_votes_version ON ab_votes(voice_version_id);
