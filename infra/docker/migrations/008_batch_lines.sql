-- BatchJob 行级状态跟踪
-- 每行独立持久化，支持实时进度查询、失败行重试、Worker 崩溃恢复

CREATE TABLE IF NOT EXISTS batch_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    line_index INT NOT NULL,
    role VARCHAR(128) NOT NULL,
    text TEXT NOT NULL,
    voice_version_id UUID NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'queued',  -- queued | running | succeeded | failed
    audio_url TEXT,
    duration_sec FLOAT,
    export_compliant BOOLEAN DEFAULT false,
    label_type VARCHAR(32),
    labeled_at TIMESTAMPTZ,
    error_code VARCHAR(64),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (job_id, line_index)
);

CREATE INDEX IF NOT EXISTS idx_batch_lines_job ON batch_lines(job_id);
CREATE INDEX IF NOT EXISTS idx_batch_lines_job_status ON batch_lines(job_id, status);
