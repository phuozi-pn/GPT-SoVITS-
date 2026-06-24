-- REQ-015: invite-only catalog publish + waitlist

CREATE TABLE IF NOT EXISTS marketplace_invite_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(32) NOT NULL UNIQUE,
    max_uses INT NOT NULL DEFAULT 1,
    used_count INT NOT NULL DEFAULT 0,
    created_by UUID,
    note TEXT NOT NULL DEFAULT '',
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_marketplace_invite_codes_active
    ON marketplace_invite_codes(code)
    WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS marketplace_invite_redemptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invite_code_id UUID NOT NULL REFERENCES marketplace_invite_codes(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    redeemed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_marketplace_invite_redemption_user UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_marketplace_invite_redemptions_user
    ON marketplace_invite_redemptions(user_id);

CREATE TABLE IF NOT EXISTS marketplace_waitlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    contact VARCHAR(128) NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Dev seed: shared creator invite (redeem once per user)
INSERT INTO marketplace_invite_codes (code, max_uses, note)
VALUES ('PHONIA-CREATOR', 999, 'Dev seed invite for MVP+1 catalog publish')
ON CONFLICT (code) DO NOTHING;

-- REQ-024: consent review metadata
ALTER TABLE consents ADD COLUMN IF NOT EXISTS reject_reason TEXT;
ALTER TABLE consents ADD COLUMN IF NOT EXISTS reviewed_by UUID;
ALTER TABLE consents ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;
