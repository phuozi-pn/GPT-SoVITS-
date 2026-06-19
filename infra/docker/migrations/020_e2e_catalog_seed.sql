-- E2E / demo: one published paid catalog voice for golden-path tests
INSERT INTO voice_catalog_entries (
    id,
    voice_version_id,
    owner_user_id,
    title,
    description,
    tags,
    featured,
    status,
    license_type,
    price_cents,
    billing_unit,
    included_chars,
    demo_text
) VALUES (
    '22222222-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111101',
    '00000000-0000-0000-0000-000000000001',
    'E2E 演示音色',
    'Playwright 金路径用公开音色，含 mock 购买流程',
    '["短剧", "男声", "演示"]'::jsonb,
    TRUE,
    'published',
    'commercial_standard',
    9900,
    'per_1k_chars',
    50000,
    '方源，你给我出来！'
) ON CONFLICT (id) DO UPDATE SET
    status = EXCLUDED.status,
    price_cents = EXCLUDED.price_cents,
    title = EXCLUDED.title,
    featured = EXCLUDED.featured;
