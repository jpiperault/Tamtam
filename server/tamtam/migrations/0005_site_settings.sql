-- Réglages simples du site (éditeur et contact des pages légales, alertes Telegram…), saisis dans Administration.
CREATE TABLE IF NOT EXISTS site_settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
