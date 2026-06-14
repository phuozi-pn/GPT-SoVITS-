-- W1 Train Job: voices, assets, consents + dev seed for POST /voices/{id}/train

CREATE TABLE IF NOT EXISTS voices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID NOT NULL,
    name VARCHAR(128) NOT NULL DEFAULT 'dev-voice',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID NOT NULL,
    voice_id UUID NOT NULL REFERENCES voices(id),
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    approved_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS voice_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    voice_id UUID NOT NULL REFERENCES voices(id),
    owner_user_id UUID NOT NULL,
    storage_uri VARCHAR(512) NOT NULL,
    locked BOOLEAN NOT NULL DEFAULT FALSE,
    qc_passed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_voices_owner ON voices(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_consents_voice ON consents(voice_id);
CREATE INDEX IF NOT EXISTS idx_voice_assets_voice ON voice_assets(voice_id);

-- Dev seed (aligns with voice_versions seed in 001)
INSERT INTO voices (id, owner_user_id, name) VALUES (
    '11111111-1111-1111-1111-111111111100',
    '00000000-0000-0000-0000-000000000001',
    'dev-zero-shot-voice'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO consents (id, owner_user_id, voice_id, status, approved_at) VALUES (
    '22222222-2222-2222-2222-222222222201',
    '00000000-0000-0000-0000-000000000001',
    '11111111-1111-1111-1111-111111111100',
    'approved',
    NOW()
) ON CONFLICT (id) DO NOTHING;

INSERT INTO voice_assets (id, voice_id, owner_user_id, storage_uri, locked, qc_passed) VALUES (
    '33333333-3333-3333-3333-333333333301',
    '11111111-1111-1111-1111-111111111100',
    '00000000-0000-0000-0000-000000000001',
    'local://dev/training/sample.wav',
    TRUE,
    TRUE
) ON CONFLICT (id) DO NOTHING;
