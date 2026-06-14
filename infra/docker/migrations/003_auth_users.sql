-- W1 Auth: users table + dev seed aligned with existing owner_user_id

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(16) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);

INSERT INTO users (id, phone, status) VALUES (
    '00000000-0000-0000-0000-000000000001',
    '13800000001',
    'active'
) ON CONFLICT (phone) DO NOTHING;
