-- 面向用户：清理测试音色馆条目，上架正式精选（幂等，需已有训练音色）
-- 龙渊 E2E catalog_id 保留：22222222-2222-2222-2222-222222222222
-- 注意：ON CONFLICT / UPDATE 不修改 cover_image_url、demo_audio_url，避免覆盖用户 AI 封面与样音

DELETE FROM voice_authorizations WHERE catalog_id IN (
    'eb042410-e74e-458c-9110-31aa5b52c826',
    '0f7653d8-ef56-4076-a422-86760a087308'
);
DELETE FROM payment_orders WHERE catalog_id IN (
    'eb042410-e74e-458c-9110-31aa5b52c826',
    '0f7653d8-ef56-4076-a422-86760a087308'
);
DELETE FROM voice_complaints WHERE catalog_id IN (
    'eb042410-e74e-458c-9110-31aa5b52c826',
    '0f7653d8-ef56-4076-a422-86760a087308'
);
DELETE FROM voice_catalog_entries WHERE id IN (
    'eb042410-e74e-458c-9110-31aa5b52c826',
    '0f7653d8-ef56-4076-a422-86760a087308'
);

-- 龙渊：绑定真实男播音色（若版本存在）；不覆盖已有封面与样音
UPDATE voice_catalog_entries
SET
    voice_version_id = '55740dc9-99a6-457b-aa33-bdc7620c2b97',
    title = '龙渊 · 沉稳男声',
    description = '适合短剧男主、旁白与解说；声线沉稳厚实，长篇叙事耐听。',
    tags = '["男声", "男主", "旁白", "解说", "沉稳", "磁性", "细腻", "短剧"]'::jsonb,
    featured = TRUE,
    status = 'published',
    price_cents = 9900,
    demo_text = '各位听众，接下来为您讲述这一段故事。'
WHERE id = '22222222-2222-2222-2222-222222222222'
  AND EXISTS (SELECT 1 FROM voice_versions WHERE id = '55740dc9-99a6-457b-aa33-bdc7620c2b97');

INSERT INTO voice_catalog_entries (
    id, voice_version_id, owner_user_id, title, description, tags,
    featured, status, license_type, price_cents, billing_unit, included_chars,
    demo_text, cover_image_url
)
SELECT
    '33333333-3333-3333-3333-333333333333',
    '57b66c19-16bb-4afe-acd9-dc202d533cc8',
    '00000000-0000-0000-0000-000000000001',
    '清岚 · 知性女声',
    '适合女主、旁白与资讯解说；吐字清晰，气质知性自然。',
    '["女声", "女主", "旁白", "解说", "知性", "清亮", "细腻", "短剧"]'::jsonb,
    TRUE, 'published', 'commercial_standard', 6900, 'per_1k_chars', 50000,
    '大家好，欢迎收听本期节目。',
    '/catalog/covers/voice-female-01.svg'
WHERE EXISTS (SELECT 1 FROM voice_versions WHERE id = '57b66c19-16bb-4afe-acd9-dc202d533cc8')
ON CONFLICT (id) DO UPDATE SET
    voice_version_id = EXCLUDED.voice_version_id,
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    tags = EXCLUDED.tags,
    featured = EXCLUDED.featured,
    status = 'published',
    price_cents = EXCLUDED.price_cents,
    demo_text = EXCLUDED.demo_text;

INSERT INTO voice_catalog_entries (
    id, voice_version_id, owner_user_id, title, description, tags,
    featured, status, license_type, price_cents, billing_unit, included_chars,
    demo_text, cover_image_url
)
SELECT
    '44444444-4444-4444-4444-444444444444',
    'eed44932-edec-42bc-aa8a-2adc016c3081',
    '00000000-0000-0000-0000-000000000001',
    '若水 · 温柔女声',
    '适合少女、女配与情感向对白；声线温柔甜美，亲和力强。',
    '["女声", "少女", "女配", "温柔", "甜美", "元气", "短剧"]'::jsonb,
    FALSE, 'published', 'commercial_standard', 4900, 'per_1k_chars', 50000,
    '谢谢你一直陪在我身边。',
    '/catalog/covers/voice-female-01.svg'
WHERE EXISTS (SELECT 1 FROM voice_versions WHERE id = 'eed44932-edec-42bc-aa8a-2adc016c3081')
ON CONFLICT (id) DO UPDATE SET
    voice_version_id = EXCLUDED.voice_version_id,
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    tags = EXCLUDED.tags,
    featured = EXCLUDED.featured,
    status = 'published',
    price_cents = EXCLUDED.price_cents,
    demo_text = EXCLUDED.demo_text;

INSERT INTO voice_catalog_entries (
    id, voice_version_id, owner_user_id, title, description, tags,
    featured, status, license_type, price_cents, billing_unit, included_chars,
    demo_text, cover_image_url
)
SELECT
    '55555555-5555-5555-5555-555555555555',
    'e77debe6-cad8-40a7-b754-4d68a57f4ebc',
    '00000000-0000-0000-0000-000000000001',
    '龙宫 · 磁性男声',
    '适合反派、权谋角色与叙事旁白；声线低沉有张力。',
    '["男声", "反派", "旁白", "磁性", "低沉", "凌厉", "沉稳", "短剧"]'::jsonb,
    TRUE, 'published', 'commercial_standard', 7900, 'per_1k_chars', 50000,
    '这一局，才刚刚开始。',
    '/catalog/covers/voice-male-01.svg'
WHERE EXISTS (SELECT 1 FROM voice_versions WHERE id = 'e77debe6-cad8-40a7-b754-4d68a57f4ebc')
ON CONFLICT (id) DO UPDATE SET
    voice_version_id = EXCLUDED.voice_version_id,
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    tags = EXCLUDED.tags,
    featured = EXCLUDED.featured,
    status = 'published',
    price_cents = EXCLUDED.price_cents,
    demo_text = EXCLUDED.demo_text;

UPDATE voices SET name = '龙渊-男播音' WHERE id = '2155e38f-5816-48cc-8852-39410d8dc27f';
UPDATE voices SET name = '清岚-女播音' WHERE id = '7abeb670-9c7f-4dd7-b1f2-f9bf9c868f58';
UPDATE voices SET name = '若水-温柔女声' WHERE id = '11be5063-af0e-46ac-957d-cfcd28b4370a';
UPDATE voices SET name = '龙宫-磁性男声' WHERE id = '2eed92a9-a9ea-4d6b-9e6c-04bf7d6eb9b5';
