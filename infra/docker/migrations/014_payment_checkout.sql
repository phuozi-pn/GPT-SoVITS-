-- Async checkout: pending orders + webhook idempotency

ALTER TABLE payment_orders
    ALTER COLUMN authorization_id DROP NOT NULL;

ALTER TABLE payment_orders
    ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS payment_webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(32) NOT NULL,
    provider_ref VARCHAR(128) NOT NULL,
    order_id UUID REFERENCES payment_orders(id) ON DELETE SET NULL,
    payload_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider, provider_ref)
);

CREATE INDEX IF NOT EXISTS idx_payment_orders_status ON payment_orders(status, created_at DESC);
