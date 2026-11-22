-- 1.5 : statistiques lues sur les réseaux (par post et par réseau) et rapports hebdomadaires rédigés par Claude.

-- Derniers chiffres connus d'un post sur un réseau. NULL = le réseau ne fournit pas ce chiffre.
CREATE TABLE post_metrics (
    post_target_id BIGINT PRIMARY KEY REFERENCES post_targets(id) ON DELETE CASCADE,
    views          BIGINT,
    reach          BIGINT,
    likes          BIGINT,
    comments       BIGINT,
    shares         BIGINT,
    saves          BIGINT,
    error          TEXT NOT NULL DEFAULT '',     -- raison si la lecture a échoué (permission manquante…)
    fetched_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE reports (
    id           BIGSERIAL PRIMARY KEY,
    project_id   BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end   DATE NOT NULL,             -- inclus
    content      JSONB NOT NULL,            -- {resume, points_forts[], a_ameliorer[], idees[]}
    data         JSONB NOT NULL DEFAULT '{}',   -- chiffres envoyés à Claude (pour relire le rapport)
    model        TEXT NOT NULL DEFAULT '',
    created_by   BIGINT REFERENCES users(id) ON DELETE SET NULL,   -- NULL : rapport automatique du lundi
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX reports_project ON reports (project_id, period_end DESC);
