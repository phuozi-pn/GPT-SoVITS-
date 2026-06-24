-- REQ-015: waitlist fulfillment tracking for operator invite issuance

ALTER TABLE marketplace_waitlist
    ADD COLUMN IF NOT EXISTS fulfilled_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS issued_invite_code_id UUID REFERENCES marketplace_invite_codes(id);

CREATE INDEX IF NOT EXISTS idx_marketplace_waitlist_pending
    ON marketplace_waitlist(created_at)
    WHERE fulfilled_at IS NULL;
