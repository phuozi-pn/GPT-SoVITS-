-- User TTS Token wallet (mock purchase; distinct from seller_wallets CNY)

CREATE TABLE IF NOT EXISTS user_wallets (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    token_balance BIGINT NOT NULL DEFAULT 0,
    total_purchased_tokens BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_wallet_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind VARCHAR(32) NOT NULL,
    token_delta BIGINT NOT NULL,
    balance_after BIGINT NOT NULL DEFAULT 0,
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    package_sku VARCHAR(64),
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_wallet_ledger_user ON user_wallet_ledger(user_id, created_at DESC);
