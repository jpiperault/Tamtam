-- 1.6 : Threads, Bluesky, LinkedIn, YouTube. La liste des réseaux est désormais vérifiée par le serveur (code),
-- plus par la base, pour pouvoir en ajouter sans migration.
ALTER TABLE app_credentials DROP CONSTRAINT IF EXISTS app_credentials_provider_check;
ALTER TABLE social_accounts DROP CONSTRAINT IF EXISTS social_accounts_platform_check;
