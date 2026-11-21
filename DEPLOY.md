# Déployer Tamtam sur Hangar

Un seul conteneur Docker (port 8080, HTTP simple : le HTTPS est géré par Cloudflare et Caddy). Les données sont
dans PostgreSQL ; `/data` contient la documentation (recréée à chaque démarrage) et **les médias envoyés**
(`/data/media`).

## 1. Nouvelle application dans Hangar

| Champ | Valeur |
|---|---|
| Type | Appli web |
| Nom | Tamtam |
| Identifiant | `tamtam` |
| Adresse | Sous-domaine `tamtam` → https://tamtam.piperault.fr/ |
| Source | Image Docker `ghcr.io/jpiperault/tamtam` |
| Version | le tag publié, par exemple `1.0.0` (jamais `latest`) |
| Port interne | `8080` |
| Adresse de santé | `/health` |
| RAM max (Mo) | `512` (envoi de vidéos) |
| Base PostgreSQL | oui (Hangar fournit `DATABASE_URL`) |

L'adresse doit être **publique** : Instagram, Facebook et TikTok téléchargent les médias à
`https://tamtam.piperault.fr/m/…`, et les réseaux renvoient l'utilisateur vers
`https://tamtam.piperault.fr/api/v1/connect/<réseau>/callback` après autorisation. Ne pas mettre l'appli derrière
une protection d'accès qui bloquerait `/m/`, `/l/` ou `/api/v1/connect/*/callback`.

## 2. Variables d'environnement

Les vraies valeurs se saisissent seulement dans la console Hangar, jamais dans le dépôt.

| Variable | Obligatoire | Rôle | Comment l'obtenir |
|---|---|---|---|
| `DATABASE_URL` | oui | Connexion à la base | Fournie par Hangar |
| `SESSION_SECRET` | oui | Signe les sessions (cookie de 30 jours). La changer déconnecte tout le monde. | `openssl rand -hex 32` |
| `TOKEN_KEY` | oui | Chiffre en base les jetons des réseaux et les secrets des applications développeur. **La perdre ou la changer oblige à reconnecter tous les comptes et à ressaisir les secrets.** À sauvegarder à part. | `python3 -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"` |
| `PUBLIC_URL` | oui | Adresse publique complète, sans `/` final | `https://tamtam.piperault.fr` |
| `ADMIN_EMAIL` | oui | Administrateur principal (ne peut être ni désactivé ni rétrogradé) | Votre adresse |
| `ADMIN_PASSWORD` | 1er démarrage | Crée le compte administrateur s'il n'existe pas ; ignorée ensuite | `openssl rand -base64 24` |
| `APP_TIMEZONE` | non | Fuseau horaire. Défaut `Europe/Paris` | — |
| `MAX_UPLOAD_MB` | non | Taille maximale d'un média envoyé. Défaut `250` | — |
| `META_GRAPH_VERSION` | non | Version de l'API Graph de Meta. Défaut `v24.0` | Voir developers.facebook.com/docs/graph-api/changelog |
| `SIMULATION` | non | `true` permet les comptes de démonstration (publication factice). **Ne pas activer en production.** | — |
| `DEMO_DATA` | non | `true` ajoute des projets fictifs si la base est vide. **Ne pas activer en production.** | — |

Si une variable obligatoire manque ou est invalide, le conteneur s'arrête aussitôt (code 2) avec un message qui la
nomme ; Hangar remet alors la version précédente.

## 3. Applications développeur des réseaux

Elles se configurent **dans l'interface** : Administration → Applications des réseaux. La page donne, pour Meta, X et
TikTok, les étapes et l'adresse de retour à copier. Points à prévoir :

- **Meta** (Facebook + Instagram) : marche à suivre complète, avec les messages d'erreur rencontrés et leur
  solution, dans [docs/guide.md](docs/guide.md) → « Configurer Meta (Facebook et Instagram) pas à pas » (aussi dans
  la page Aide). En bref : app à part avec les cas d'utilisation « Gérer tout sur votre Page » et « Gérer les
  messages et le contenu sur Instagram » (configuration avec Facebook Login), autorisations `pages_manage_posts`,
  `pages_read_engagement`, `instagram_basic`, `instagram_content_publish`, domaine + plateforme Site web, adresse
  de retour dans Facebook Login for Business. Publication seulement sur une **Page** et un Instagram
  **professionnel relié** à cette Page. Tant que l'App Review n'est pas validée, seules les personnes ayant un rôle
  sur l'app peuvent connecter leurs comptes (ce qui suffit pour vos propres Pages).
- **X** : l'écriture par API dépend de l'offre d'accès de votre compte développeur (payante ou limitée).
- **TikTok** : sans audit, les posts sont publiés en privé. Pour les carrousels photo, vérifier le domaine
  `tamtam.piperault.fr` dans le portail TikTok (« URL properties »).

### Claude (rédaction des posts)

Facultatif. La clé API Anthropic se saisit **dans l'interface** (Administration → carte Claude), chiffrée avec
`TOKEN_KEY` comme les secrets des réseaux : aucune variable d'environnement à ajouter. Le conteneur doit pouvoir
joindre `https://api.anthropic.com`. Sont envoyés à Anthropic : la consigne, le texte du post, le nom, l'adresse et
la présentation du projet et, si l'utilisateur laisse la case cochée, les images du post (réduites à 1 568 px) ou
4 images extraites de la vidéo (bibliothèque PyAV, incluse dans l'image Docker) ; jamais les jetons ni les comptes. Chaque appel est noté dans la table
`ai_calls` (utilisateur, projet, jetons) pour la limite quotidienne et le suivi du coût.

## 4. Mettre à jour

```bash
git tag v1.0.1 && git push --tags
```

L'Action GitHub « Image Docker » lance les tests sur PostgreSQL, construit l'image `linux/amd64` et publie
`ghcr.io/jpiperault/tamtam:1.0.1`. Ensuite, dans Hangar : bloc **Version**, saisir `1.0.1`, **Déployer**.

Les migrations de base s'appliquent seules au démarrage (ajouts uniquement).

## 5. Fonctionnement, santé, journaux

- `GET /health` : `200 ok` en moins d'une seconde, `503` si la base est inaccessible.
- La publication tourne dans le même processus : toutes les 10 secondes, envoi des posts dont l'heure est venue
  (3 en parallèle au plus). Un redémarrage pendant un envoi marque ce réseau en échec (« vérifiez sur le réseau
  avant de réessayer ») plutôt que de risquer un doublon.
- Routes publiques sans connexion : `/m/<fichier>` (médias, noms aléatoires impossibles à deviner), `/l/<code>`
  (liens suivis), `/api/v1/connect/<réseau>/callback` (retour OAuth, protégé par un état à usage unique de
  30 minutes).
- Journaux sur la sortie standard, sans jeton ni secret.

## 6. Sauvegardes

Hangar sauvegarde chaque nuit la base et `/data`.

- **Base** : utilisateurs, projets, comptes (jetons chiffrés), posts, liens, clics.
- **`/data/media`** : les images et vidéos envoyées. Sans elles, les posts programmés qui les utilisent échouent.
- **`TOKEN_KEY`** n'est dans aucune des deux : la conserver dans votre gestionnaire de mots de passe.
