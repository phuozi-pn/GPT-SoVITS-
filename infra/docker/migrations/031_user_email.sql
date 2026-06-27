-- 邮箱登录：users 表增加 email，phone 改为可空（手机号/邮箱二选一）

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS email VARCHAR(255);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL;

ALTER TABLE users
  ALTER COLUMN phone DROP NOT NULL;
