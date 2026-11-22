-- Réglages par publication (TikTok : visibilité, interactions, divulgation commerciale) et durée des vidéos.
ALTER TABLE post_targets ADD COLUMN IF NOT EXISTS options JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE media ADD COLUMN IF NOT EXISTS duration_s REAL;
