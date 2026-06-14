-- MVP+1 slice: platform catalog + cross-user VoiceGrant

CREATE TABLE IF NOT EXISTS voice_catalog_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    voice_version_id UUID NOT NULL,
    owner_user_id UUID NOT NULL,
    title VARCHAR(128) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    featured BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(32) NOT NULL DEFAULT 'published',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_catalog_status ON voice_catalog_entries(status);
CREATE INDEX IF NOT EXISTS idx_catalog_featured ON voice_catalog_entries(featured) WHERE featured = TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS idx_catalog_voice_version ON voice_catalog_entries(voice_version_id);

CREATE TABLE IF NOT EXISTS voice_grants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    voice_id UUID NOT NULL,
    granter_user_id UUID NOT NULL,
    grantee_user_id UUID NOT NULL,
    scope VARCHAR(32) NOT NULL DEFAULT 'synthesize',
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_voice_grants_grantee ON voice_grants(grantee_user_id);
CREATE INDEX IF NOT EXISTS idx_voice_grants_voice ON voice_grants(voice_id);
