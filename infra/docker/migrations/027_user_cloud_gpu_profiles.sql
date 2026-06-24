-- Per-user cloud GPU SSH credentials (AutoDL / rented server)

CREATE TABLE IF NOT EXISTS user_cloud_gpu_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    ssh_host VARCHAR(255) NOT NULL,
    ssh_port INT NOT NULL DEFAULT 22,
    ssh_user VARCHAR(64) NOT NULL DEFAULT 'root',
    auth_type VARCHAR(16) NOT NULL DEFAULT 'password',
    credential_enc TEXT NOT NULL,
    remote_engine_root VARCHAR(512) NOT NULL DEFAULT '/root/GPT-SoVITS',
    remote_platform_root VARCHAR(512) NOT NULL DEFAULT '/root/GPT',
    remote_work_dir VARCHAR(512) NOT NULL DEFAULT '/root/cloud_train_jobs',
    last_tested_at TIMESTAMPTZ,
    last_test_ok BOOLEAN,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
