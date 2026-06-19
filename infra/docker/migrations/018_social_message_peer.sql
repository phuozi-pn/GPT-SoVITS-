-- Attach system notices to a human conversation (MVP+1 social)

ALTER TABLE user_messages
    ADD COLUMN IF NOT EXISTS conversation_peer_user_id UUID REFERENCES users(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_user_messages_recipient_peer_created
    ON user_messages (recipient_user_id, conversation_peer_user_id, created_at DESC);

