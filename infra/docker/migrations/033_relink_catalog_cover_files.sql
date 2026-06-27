-- 将已落盘的 AI/上传封面 PNG 重新挂回音色馆条目（迁移 029 曾把 URL 重置为默认 SVG）

UPDATE voice_catalog_entries e
SET cover_image_url = '/files/' || e.owner_user_id::text || '/catalog/covers/' || e.id::text || '.png'
WHERE e.id IN (
    '22222222-2222-2222-2222-222222222222',
    '33333333-3333-3333-3333-333333333333',
    '44444444-4444-4444-4444-444444444444',
    '55555555-5555-5555-5555-555555555555'
);
