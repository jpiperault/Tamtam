-- 1.9 : veille des nouvelles versions (GitHub, App Store) → brouillon rédigé par Claude.
CREATE TABLE IF NOT EXISTS release_sources (
    id              BIGSERIAL PRIMARY KEY,
    project_id      BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL CHECK (kind IN ('github', 'appstore')),
    ref             TEXT NOT NULL,                 -- « propriétaire/dépôt » ou identifiant App Store
    country         TEXT NOT NULL DEFAULT 'fr',    -- App Store : boutique du pays
    token_enc       TEXT,                          -- GitHub : jeton facultatif (dépôt privé), chiffré
    label           TEXT NOT NULL DEFAULT '',      -- nom de l'appli ou du dépôt, lu à l'ajout
    instructions    TEXT NOT NULL DEFAULT '',      -- consigne en plus pour Claude
    enabled         BOOLEAN NOT NULL DEFAULT true,
    last_version    TEXT NOT NULL DEFAULT '',
    last_seen_at    TIMESTAMPTZ,
    last_checked_at TIMESTAMPTZ,
    last_error      TEXT NOT NULL DEFAULT '',
    last_post_id    BIGINT REFERENCES posts(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, kind, ref)
);

-- Brouillon créé automatiquement : d'où il vient et la remarque de Claude, affichées dans la liste des posts.
ALTER TABLE posts ADD COLUMN IF NOT EXISTS auto_note TEXT NOT NULL DEFAULT '';
