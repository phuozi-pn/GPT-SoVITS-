-- 音色馆封面图（创作者上传或 AI 生图 URL）
ALTER TABLE voice_catalog_entries
  ADD COLUMN IF NOT EXISTS cover_image_url TEXT;

-- 演示条目：正式对外文案 + 默认封面
UPDATE voice_catalog_entries
SET
  title = '龙渊 · 沉稳男声',
  description = '适合短剧男主、旁白与解说；声线沉稳厚实，长篇叙事耐听。',
  cover_image_url = '/catalog/covers/voice-male-01.svg',
  tags = '["男声", "男主", "旁白", "解说", "沉稳", "磁性", "细腻", "短剧"]'::jsonb
WHERE id = '22222222-2222-2222-2222-222222222222';
