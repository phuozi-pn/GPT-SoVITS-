-- Per-user monthly quota overrides (NULL = use platform default from env)

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS quota_monthly_char_limit INTEGER NULL,
    ADD COLUMN IF NOT EXISTS quota_monthly_train_limit INTEGER NULL;

COMMENT ON COLUMN users.quota_monthly_char_limit IS 'Override monthly synthesis char limit; NULL uses QUOTA_MONTHLY_CHAR_LIMIT';
COMMENT ON COLUMN users.quota_monthly_train_limit IS 'Override monthly training job limit; NULL uses QUOTA_MONTHLY_TRAIN_LIMIT';
