# Tamtam

Gestionnaire de réseaux sociaux pour faire connaître des apps, des sites et des produits : un post écrit une fois,
publié sur **Instagram, Facebook, X et TikTok**, chacun dans son format, avec des liens suivis pour savoir quel
réseau ramène des visites.

- **Projets** : un projet par app ou site, avec ses propres comptes sociaux.
- **Connexion des comptes** depuis l'interface (OAuth officiel de chaque réseau, jetons chiffrés en base).
- **Rédaction** : texte commun + adaptation par réseau, compteurs, aperçus, médias (images converties en JPEG,
  vidéos MP4/MOV), publication immédiate ou programmée.
- **Suivi** : état réseau par réseau, raison des échecs, nouvel essai automatique des erreurs passagères.
- **Liens suivis** `/l/<code>` avec paramètres UTM par réseau, statistiques de clics (sur Facebook : option par
  post, lien direct par défaut).
- **Rédaction avec Claude** : texte commun et version par réseau proposés à partir d'une consigne et de la
  présentation du projet (clé API saisie dans Administration).
- **Calendrier** de la semaine, **médiathèque**, **utilisateurs** (administrateurs et membres).
- **Mode simulation** pour tout essayer sans application développeur.

Maquette d'origine : [docs/maquette.html](docs/maquette.html). Guide d'utilisation : [docs/guide.md](docs/guide.md)
(aussi affiché dans la page Aide). Déploiement : [DEPLOY.md](DEPLOY.md). Historique : [docs/journal.md](docs/journal.md).

## Technique

FastAPI + PostgreSQL + React/Vite, un seul conteneur (même recette que Cockpit SE et Sillage).

```
server/tamtam/          API, publication en tâche de fond (worker.py), médias (media.py)
server/tamtam/platforms connecteurs : meta.py (Facebook + Instagram), x.py, tiktok.py
server/tamtam/migrations schéma SQL (appliqué au démarrage)
web/src                 interface React
```

## Essai local (mode simulation)

```bash
mkdir -p .data && chown 10001:10001 .data
docker compose -f docker-compose.local.yml up -d --build
```

Interface sur http://127.0.0.1:8092 (admin@example.test / dev-admin-password), avec deux projets d'exemple et des
comptes de démonstration. Depuis un autre poste : tunnel SSH `ssh -L 8092:127.0.0.1:8092 <serveur>`.

La connexion de vrais comptes demande une adresse publique en HTTPS (les réseaux renvoient vers
`PUBLIC_URL/api/v1/connect/<réseau>/callback` et viennent chercher les médias sur `PUBLIC_URL/m/…`) : à faire sur
Hangar.

## Tests

```bash
cd server && TEST_DATABASE_URL=postgresql://user:mdp@hote:5432/tamtam_test python -m pytest -q tests
```

La base doit se terminer par `_test` (elle est vidée). Les tests tournent en mode simulation : aucun réseau
social n'est contacté. Les appels réels aux API Meta, X et TikTok n'ont pas de test automatique.
