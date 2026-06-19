-- REQ-028 seller wallet, ledger, payout requests (GA skeleton)

CREATE TABLE IF NOT EXISTS seller_wallets (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    balance_cents BIGINT NOT NULL DEFAULT 0,
    pending_payout_cents BIGINT NOT NULL DEFAULT 0,
    total_earned_cents BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS seller_ledger_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seller_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    payment_order_id UUID REFERENCES payment_orders(id) ON DELETE SET NULL,
    kind VARCHAR(32) NOT NULL,
    gross_cents INT NOT NULL DEFAULT 0,
    fee_cents INT NOT NULL DEFAULT 0,
    net_cents INT NOT NULL DEFAULT 0,
    balance_after_cents BIGINT NOT NULL DEFAULT 0,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_seller_ledger_user ON seller_ledger_entries(seller_user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS payout_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seller_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount_cents INT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    note TEXT,
    processed_by UUID,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payout_requests_status ON payout_requests(status, created_at DESC);
