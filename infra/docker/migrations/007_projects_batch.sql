-- Projects, role bindings, batch synthesis support

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID NOT NULL,
    name VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    role_name VARCHAR(64) NOT NULL,
    voice_version_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, role_name)
);

CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_project_roles_project ON project_roles(project_id);
