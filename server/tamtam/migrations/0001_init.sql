-- Tamtam : schéma initial.

CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    email           TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL DEFAULT '',
    password_hash   TEXT NOT NULL,
    is_admin        BOOLEAN NOT NULL DEFAULT false,
    active          BOOLEAN NOT NULL DEFAULT true,
    session_version INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Un projet = une app, un site ou un produit à faire connaître. Chaque projet a ses propres comptes sociaux.
CREATE TABLE projects (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    url         TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    color       TEXT NOT NULL DEFAULT '#0E6E5C',
    archived    BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX projects_name_uq ON projects (lower(name));

-- Identifiants des applications développeur (Meta, X, TikTok), saisis dans Administration. Secret chiffré.
CREATE TABLE app_credentials (
    provider          TEXT PRIMARY KEY CHECK (provider IN ('meta', 'x', 'tiktok')),
    client_id         TEXT NOT NULL DEFAULT '',
    client_secret_enc TEXT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Connexion en cours (entre le départ vers le réseau et le retour).
CREATE TABLE oauth_states (
    state         TEXT PRIMARY KEY,
    provider      TEXT NOT NULL,
    project_id    BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_verifier TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Comptes trouvés au retour de Meta (plusieurs Pages / comptes Instagram) : l'utilisateur choisit lesquels garder.
CREATE TABLE pending_connections (
    id          TEXT PRIMARY KEY,
    project_id  BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    candidates  TEXT NOT NULL,   -- JSON chiffré (contient des jetons)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE social_accounts (
    id                 BIGSERIAL PRIMARY KEY,
    project_id         BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    platform           TEXT NOT NULL CHECK (platform IN ('instagram', 'facebook', 'x', 'tiktok')),
    external_id        TEXT NOT NULL,
    name               TEXT NOT NULL DEFAULT '',
    handle             TEXT NOT NULL DEFAULT '',
    avatar_url         TEXT NOT NULL DEFAULT '',
    access_token_enc   TEXT,
    refresh_token_enc  TEXT,
    expires_at         TIMESTAMPTZ,
    refresh_expires_at TIMESTAMPTZ,
    meta               JSONB NOT NULL DEFAULT '{}',
    simulated          BOOLEAN NOT NULL DEFAULT false,
    status             TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok', 'expired', 'error')),
    last_error         TEXT NOT NULL DEFAULT '',
    connected_by       BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, platform, external_id)
);

-- Médias envoyés. Le fichier est dans /data/media/<token><ext>, servi publiquement à /m/<token><ext>
-- (Instagram, Facebook et TikTok viennent le chercher eux-mêmes).
CREATE TABLE media (
    id          BIGSERIAL PRIMARY KEY,
    project_id  BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    token       TEXT NOT NULL UNIQUE,
    ext         TEXT NOT NULL,
    filename    TEXT NOT NULL DEFAULT '',
    mime        TEXT NOT NULL,
    kind        TEXT NOT NULL CHECK (kind IN ('image', 'video')),
    size        BIGINT NOT NULL,
    width       INTEGER,
    height      INTEGER,
    created_by  BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- status : draft, scheduled, publishing, done, partial, failed (calculé à partir des cibles).
CREATE TABLE posts (
    id           BIGSERIAL PRIMARY KEY,
    project_id   BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    created_by   BIGINT REFERENCES users(id) ON DELETE SET NULL,
    body         TEXT NOT NULL DEFAULT '',
    link_url     TEXT NOT NULL DEFAULT '',
    campaign     TEXT NOT NULL DEFAULT '',
    scheduled_at TIMESTAMPTZ,
    status       TEXT NOT NULL DEFAULT 'draft',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX posts_project_sched ON posts (project_id, scheduled_at);

CREATE TABLE post_media (
    post_id  BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    media_id BIGINT NOT NULL REFERENCES media(id) ON DELETE RESTRICT,
    position SMALLINT NOT NULL DEFAULT 0,
    PRIMARY KEY (post_id, media_id)
);

-- Une ligne par réseau visé. status : pending, publishing, published, failed.
CREATE TABLE post_targets (
    id                BIGSERIAL PRIMARY KEY,
    post_id           BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    social_account_id BIGINT REFERENCES social_accounts(id) ON DELETE SET NULL,
    platform          TEXT NOT NULL,
    body_override     TEXT,
    status            TEXT NOT NULL DEFAULT 'pending',
    external_id       TEXT NOT NULL DEFAULT '',
    external_url      TEXT NOT NULL DEFAULT '',
    error             TEXT NOT NULL DEFAULT '',
    attempts          INTEGER NOT NULL DEFAULT 0,
    not_before        TIMESTAMPTZ,              -- prochain essai après une erreur passagère
    published_at      TIMESTAMPTZ,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX post_targets_pending ON post_targets (status) WHERE status IN ('pending', 'publishing');

-- Liens courts suivis (/l/<code>) : un par réseau et par post, pour compter les clics réseau par réseau.
CREATE TABLE links (
    id             BIGSERIAL PRIMARY KEY,
    code           TEXT NOT NULL UNIQUE,
    project_id     BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    post_target_id BIGINT REFERENCES post_targets(id) ON DELETE SET NULL,
    platform       TEXT NOT NULL DEFAULT '',
    target_url     TEXT NOT NULL,
    clicks         BIGINT NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE link_clicks (
    link_id BIGINT NOT NULL REFERENCES links(id) ON DELETE CASCADE,
    day     DATE NOT NULL,
    clicks  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (link_id, day)
);
