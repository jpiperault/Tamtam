# Journal

## 1.1.0 — 21 novembre 2026

- **Rédiger avec Claude** dans « Nouveau post » : à partir d'une consigne, d'un ton et de la présentation du
  projet, Claude propose un texte commun et une version adaptée à chaque réseau choisi (longueur, hashtags, lien en
  bio). On applique tout, ou seulement le texte commun ; rien n'est publié sans validation.
- Administration : carte **Claude** (clé API chiffrée, modèle, limite de rédactions par jour, test de la clé, usage
  du jour et du mois).
- Projets : la description devient la **présentation** (3 000 caractères), utilisée par Claude.
- Mode simulation sans clé : propositions factices pour essayer l'écran.

Vérifié : tests d'API avec un faux client Claude (format de la demande, limite quotidienne, erreurs de clé et
refus), écran essayé dans le navigateur en mode simulation. **Pas encore vérifié** : un vrai appel à Claude (pas de
clé Anthropic sur le serveur de développement).

## 1.0.3 — 21 novembre 2026

- Facebook : le lien court suivi (`/l/…`) devient une option par post, **décochée par défaut**. Sans elle, le post
  Facebook montre le lien direct vers votre page (avec ses paramètres UTM) et ses clics ne sont pas comptés dans
  Tamtam. X garde le lien court. Les posts déjà enregistrés passent au lien direct.

## 1.0.2 — 21 novembre 2026

- Aide : nouvelle section « Configurer Meta (Facebook et Instagram) pas à pas », écrite pendant la première vraie
  connexion : forme des comptes (Page, Instagram professionnel relié), création de l'app, autorisations, domaine,
  adresse de retour, et tableau des messages d'erreur de Facebook avec leur solution.
- Administration : étapes Meta corrigées (plateforme Site web, Entrée dans le champ des adresses de retour,
  autorisations exactes, app à part si l'app a déjà « Facebook Login »).
- Aide : les tableaux s'affichent enfin comme des tableaux (ils apparaissaient en texte brut avec des `|`).
- Retour de connexion : l'erreur renvoyée par le réseau est affichée même quand l'état de connexion manque, et la
  raison d'un retour refusé est écrite dans les journaux.

## 1.0.1 — 21 novembre 2026

- Correction : « Enregistrer » dans Administration → Applications des réseaux et l'enregistrement d'un post modifié
  échouaient (« Z.put is not a function »).
- Administration : étapes de création de l'application Meta mises à jour pour l'interface actuelle de Meta
  (cas d'utilisation au lieu des « types d'app » et « produits »).

## 1.0.0 — 21 novembre 2026

Première version, construite à partir de la maquette validée ([maquette.html](maquette.html)). Appelée « Relais »
pendant la construction, renommée **Tamtam** avant la mise en ligne.

- Projets, utilisateurs (administrateurs et membres), connexion par e-mail et mot de passe.
- Connexion des comptes depuis l'interface : Meta (Pages Facebook et comptes Instagram Professionnels reliés,
  choix des comptes au retour), X (OAuth 2.0 avec PKCE, jeton renouvelé automatiquement), TikTok (Login Kit,
  jeton renouvelé automatiquement, visibilité réglable).
- Identifiants des applications développeur saisis dans Administration, chiffrés avec `TOKEN_KEY`.
- Rédaction : texte commun et textes adaptés par réseau, compteurs, règles de chaque réseau vérifiées avant envoi,
  aperçus, médias (conversion JPEG, vidéos MP4/MOV), médiathèque, brouillons, publication immédiate ou programmée.
- Publication en tâche de fond, réseau par réseau, 3 essais pour les erreurs passagères, nouvel essai manuel.
- Liens suivis `/l/<code>` avec UTM par réseau ; statistiques de clics.
- Calendrier de la semaine.
- Mode simulation et données de démonstration pour essayer sans application développeur.

Vérifié : 16 tests d'API sur PostgreSQL (mode simulation), parcours complet dans un navigateur sans interface
(connexion d'un compte démo, envoi d'image, texte adapté pour X, publication sur 4 réseaux).
**Pas encore vérifié** : les appels réels aux API Meta, X et TikTok (il faut les applications développeur et
l'adresse publique sur Hangar).
