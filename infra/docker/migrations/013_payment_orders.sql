-- Mock payment order ledger (REQ-017 ops visibility; REQ-028 settlement deferred)

CREATE TABLE IF NOT EXISTS payment_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    authorization_id UUID NOT NULL REFERENCES voice_authorizations(id) ON DELETE CASCADE,
    catalog_id UUID NOT NULL,
    buyer_user_id UUID NOT NULL,
    seller_user_id UUID NOT NULL,
    amount_cents INT NOT NULL,
    currency VARCHAR(8) NOT NULL DEFAULT 'CNY',
    status VARCHAR(32) NOT NULL DEFAULT 'paid',
    provider VARCHAR(32) NOT NULL DEFAULT 'mock',
    provider_ref VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payment_orders_buyer ON payment_orders(buyer_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_payment_orders_seller ON payment_orders(seller_user_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_orders_provider_ref ON payment_orders(provider_ref);
