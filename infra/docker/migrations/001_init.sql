-- W1 Core initial schema + dev seed (zero-shot voice)
-- Idempotent: safe to re-run on startup

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS voice_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    voice_id UUID NOT NULL,
    owner_user_id UUID NOT NULL,
    version INT NOT NULL DEFAULT 1,
    model_tag VARCHAR(64) NOT NULL,
    checkpoint_uri VARCHAR(512),
    ref_audio_uri VARCHAR(512),
    ref_text TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    trace_id VARCHAR(64) NOT NULL,
    job_schema_version VARCHAR(16) NOT NULL,
    payload JSONB NOT NULL,
    result JSONB,
    error_message TEXT,
    owner_user_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_owner ON jobs(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_type_status ON jobs(job_type, status);

-- Dev seed: default user + zero-shot voice (see infra/engine/samples)
INSERT INTO voice_versions (
    id,
    voice_id,
    owner_user_id,
    version,
    model_tag,
    ref_text,
    metadata
) VALUES (
    '11111111-1111-1111-1111-111111111101',
    '11111111-1111-1111-1111-111111111100',
    '00000000-0000-0000-0000-000000000001',
    1,
    'gsv-v2pro-20250606',
    '大家好，我是测试用户，今天我们来测试一下语音合成功能。',
    '{"engine_ref_audio_path": "/workspace/GPT-SoVITS/samples/ref_zh_zero_shot.wav", "prompt_lang": "zh", "text_lang": "zh"}'::jsonb
) ON CONFLICT (id) DO NOTHING;
