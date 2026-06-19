-- MVP+1: license policy, mock purchase authorizations, infringement complaints

ALTER TABLE voice_catalog_entries
    ADD COLUMN IF NOT EXISTS license_type VARCHAR(32) NOT NULL DEFAULT 'personal_non_commercial',
    ADD COLUMN IF NOT EXISTS price_cents INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS billing_unit VARCHAR(32) NOT NULL DEFAULT 'per_1k_chars',
    ADD COLUMN IF NOT EXISTS included_chars INT NOT NULL DEFAULT 50000,
    ADD COLUMN IF NOT EXISTS prohibited_domains JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS policy_version INT NOT NULL DEFAULT 1;

CREATE TABLE IF NOT EXISTS voice_authorizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    catalog_id UUID NOT NULL,
    voice_version_id UUID NOT NULL,
    voice_id UUID NOT NULL,
    seller_user_id UUID NOT NULL,
    buyer_user_id UUID NOT NULL,
    license_type VARCHAR(32) NOT NULL,
    billing_unit VARCHAR(32) NOT NULL DEFAULT 'per_1k_chars',
    char_quota_total INT NOT NULL DEFAULT 0,
    char_quota_used INT NOT NULL DEFAULT 0,
    price_paid_cents INT NOT NULL DEFAULT 0,
    payment_ref VARCHAR(128) NOT NULL DEFAULT '',
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_voice_auth_buyer ON voice_authorizations(buyer_user_id);
CREATE INDEX IF NOT EXISTS idx_voice_auth_seller ON voice_authorizations(seller_user_id);
CREATE INDEX IF NOT EXISTS idx_voice_auth_catalog ON voice_authorizations(catalog_id);

CREATE TABLE IF NOT EXISTS voice_complaints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    catalog_id UUID,
    voice_version_id UUID,
    reporter_user_id UUID NOT NULL,
    target_url TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL,
    evidence_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    resolution_note TEXT,
    resolved_by UUID,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_complaints_status ON voice_complaints(status);
