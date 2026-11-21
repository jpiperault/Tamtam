-- Lien court suivi sur Facebook : désormais une option par post (désactivée par défaut).
ALTER TABLE posts ADD COLUMN IF NOT EXISTS facebook_short_link boolean NOT NULL DEFAULT false;
