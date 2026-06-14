-- Point dev training asset at engine sample (resolved by EngineTrainAdapter)

UPDATE voice_assets
SET storage_uri = 'engine://samples/ref_zh_zero_shot.wav'
WHERE id = '33333333-3333-3333-3333-333333333301';
