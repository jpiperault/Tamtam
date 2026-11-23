-- 1.10 : bibliothèque par projet, langue par compte.
CREATE TABLE IF NOT EXISTS snippets (
    id         BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    kind       TEXT NOT NULL CHECK (kind IN ('hashtags', 'signature', 'text')),
    name       TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS snippets_project ON snippets (project_id, kind);

-- Langue de publication du compte ('' = celle du texte du post). Claude traduit pour les comptes dans une autre langue.
ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS language TEXT NOT NULL DEFAULT '';
