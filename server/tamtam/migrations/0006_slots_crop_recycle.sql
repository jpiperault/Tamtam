-- 1.4 : créneaux de publication par projet, recadrage automatique par réseau, posts recyclés.

-- Créneaux : [{"day": 0-6 (lundi = 0), "time": "HH:MM"}], heure locale du serveur (TZ).
ALTER TABLE projects ADD COLUMN slots JSONB NOT NULL DEFAULT '[]';

-- Recadrer les images au format conseillé de chaque réseau (Instagram 4:5, TikTok 9:16, X 16:9).
ALTER TABLE posts ADD COLUMN auto_crop BOOLEAN NOT NULL DEFAULT false;

-- Post d'origine quand un post est une nouvelle version d'un ancien (recyclage).
ALTER TABLE posts ADD COLUMN recycled_from BIGINT REFERENCES posts(id) ON DELETE SET NULL;
