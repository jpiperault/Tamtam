-- 1.8 : page « lien en bio » publique par projet (/b/<slug>), avec comptage des visites et des clics.
CREATE TABLE bio_pages (
    project_id      BIGINT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    slug            TEXT NOT NULL UNIQUE,
    enabled         BOOLEAN NOT NULL DEFAULT false,
    title           TEXT NOT NULL DEFAULT '',
    subtitle        TEXT NOT NULL DEFAULT '',
    avatar_media_id BIGINT REFERENCES media(id) ON DELETE SET NULL,
    links           JSONB NOT NULL DEFAULT '[]',     -- [{id, label, url}]
    show_latest     BOOLEAN NOT NULL DEFAULT true,   -- afficher le dernier post publié
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- source : réseau d'où vient le visiteur (?src=instagram…), « direct » sinon.
CREATE TABLE bio_views (
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source     TEXT NOT NULL,
    day        DATE NOT NULL,
    views      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (project_id, source, day)
);
CREATE TABLE bio_clicks (
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    link_id    TEXT NOT NULL,
    source     TEXT NOT NULL,
    day        DATE NOT NULL,
    clicks     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (project_id, link_id, source, day)
);
