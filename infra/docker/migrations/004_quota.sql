-- W1 Quota: usage_records (audit + idempotent per job_id)

CREATE TABLE IF NOT EXISTS usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    job_id UUID NOT NULL UNIQUE,
    record_type VARCHAR(16) NOT NULL,
    amount BIGINT NOT NULL DEFAULT 1,
    billing_month CHAR(7) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT usage_records_type_check CHECK (record_type IN ('chars', 'train'))
);

CREATE INDEX IF NOT EXISTS idx_usage_records_user_month
    ON usage_records(user_id, billing_month);

CREATE INDEX IF NOT EXISTS idx_usage_records_user_month_type
    ON usage_records(user_id, billing_month, record_type);
