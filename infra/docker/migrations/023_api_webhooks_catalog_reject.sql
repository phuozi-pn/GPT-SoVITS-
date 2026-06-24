-- REQ-030 Open API job webhooks + catalog reject reason

ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS webhook_url TEXT;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS webhook_secret VARCHAR(128);

ALTER TABLE voice_catalog_entries ADD COLUMN IF NOT EXISTS reject_reason TEXT;
