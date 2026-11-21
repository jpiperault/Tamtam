-- Rédaction avec Claude : réglages (une seule ligne) et journal des appels (limite quotidienne, suivi du coût).
CREATE TABLE IF NOT EXISTS ai_settings (
    id          INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    api_key_enc TEXT,
    model       TEXT NOT NULL DEFAULT 'claude-opus-5-5',
    daily_limit INT NOT NULL DEFAULT 50,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS ai_calls (
    id            BIGSERIAL PRIMARY KEY,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_id       BIGINT REFERENCES users(id) ON DELETE SET NULL,
    project_id    BIGINT REFERENCES projects(id) ON DELETE SET NULL,
    model         TEXT NOT NULL DEFAULT '',
    input_tokens  INT NOT NULL DEFAULT 0,
    output_tokens INT NOT NULL DEFAULT 0,
    ok            BOOLEAN NOT NULL DEFAULT true
);
CREATE INDEX IF NOT EXISTS ai_calls_day ON ai_calls (created_at);
