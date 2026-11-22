-- 1.7 : validation à deux (un membre propose, un administrateur valide) et boîte de réception des commentaires.

-- status 'review' : en attente de validation (ne part pas).
ALTER TABLE posts ADD COLUMN review_note TEXT NOT NULL DEFAULT '';     -- raison d'un refus
ALTER TABLE posts ADD COLUMN reviewed_by BIGINT REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE posts ADD COLUMN reviewed_at TIMESTAMPTZ;

-- Commentaires reçus sous les posts publiés par Tamtam, et la réponse envoyée.
CREATE TABLE inbox_items (
    id                BIGSERIAL PRIMARY KEY,
    post_target_id    BIGINT NOT NULL REFERENCES post_targets(id) ON DELETE CASCADE,
    platform          TEXT NOT NULL,
    external_id       TEXT NOT NULL,                -- identifiant du commentaire sur le réseau
    extra             JSONB NOT NULL DEFAULT '{}',  -- données utiles pour répondre (Bluesky : uri/cid)
    author_name       TEXT NOT NULL DEFAULT '',
    author_handle     TEXT NOT NULL DEFAULT '',
    author_avatar     TEXT NOT NULL DEFAULT '',
    text              TEXT NOT NULL DEFAULT '',
    commented_at      TIMESTAMPTZ,
    status            TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'replied', 'done')),
    reply_text        TEXT NOT NULL DEFAULT '',
    reply_external_id TEXT NOT NULL DEFAULT '',
    reply_error       TEXT NOT NULL DEFAULT '',
    replied_by        BIGINT REFERENCES users(id) ON DELETE SET NULL,
    replied_at        TIMESTAMPTZ,
    fetched_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (platform, external_id)
);
CREATE INDEX inbox_new ON inbox_items (status, commented_at DESC);
