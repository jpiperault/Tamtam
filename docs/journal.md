# Journal

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
