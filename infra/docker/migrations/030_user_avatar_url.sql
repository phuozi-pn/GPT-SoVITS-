-- 创作者主页头像 URL（支持 AI 生图落盘）
ALTER TABLE user_profiles
  ADD COLUMN IF NOT EXISTS avatar_url TEXT;
