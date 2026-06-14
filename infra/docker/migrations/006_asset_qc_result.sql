-- W2 Module C: QC report JSON on voice_assets

ALTER TABLE voice_assets ADD COLUMN IF NOT EXISTS qc_result JSONB;
