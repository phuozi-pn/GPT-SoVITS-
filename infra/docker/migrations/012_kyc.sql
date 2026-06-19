-- REQ-002 KYC: user verification + append-only audit log

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS verified BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS id_number_hash VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_users_verified ON users(verified);

CREATE TABLE IF NOT EXISTS kyc_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    provider VARCHAR(64) NOT NULL DEFAULT 'mock',
    message TEXT,
    real_name_masked VARCHAR(64),
    id_number_last4 VARCHAR(4),
    id_number_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kyc_audit_user ON kyc_audit_logs(user_id, created_at DESC);
