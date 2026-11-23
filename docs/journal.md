# Journal

## 1.10.0 — 23 novembre 2026

- **Visuels d'annonce** (« Créer un visuel » dans Médias) : modèles Annonce, Clair et Citation ; formats carré,
  portrait 4:5, story 9:16 et paysage 16:9 ; titre, accroche, étiquette, capture d'écran, couleur du projet ; aperçu
  en direct ; enregistré en JPEG dans la médiathèque et ajouté au post. Police Inter incluse (licence SIL OFL).
- **Traduction par Claude** : langue de publication par compte (Comptes) ; dans « Nouveau post », un bouton traduit
  le texte commun pour chaque compte dans une autre langue, en respectant la longueur maximale du réseau.
- **Bibliothèque du projet** : groupes de hashtags, signatures et textes réutilisables, insérés en un clic dans le
  texte.

Vérifié : tests d'API (bibliothèque, langue des comptes, traduction simulée et avec un faux Claude, rendu de chaque
modèle dans chaque format, aperçu et enregistrement d'un visuel) ; dans le navigateur, langue d'un compte,
traduction, insertion depuis la bibliothèque, création d'un visuel avec capture, en mode simulation.
**Pas encore vérifié** : traduction par le vrai Claude.

## 1.9.0 — 23 novembre 2026

- **Nouvelles versions** (nouvelle page) : Tamtam suit la fiche App Store ou le dépôt GitHub d'une appli (jeton
  facultatif, chiffré, pour un dépôt privé) et vérifie toutes les heures. À chaque nouvelle version, Claude rédige un
  brouillon d'annonce à partir des notes de version, sur tous les comptes du projet, avec le lien de la fiche (App
  Store) ou du projet, et la première capture d'écran de la fiche. Rien n'est publié tout seul. Bouton pour créer
  tout de suite le brouillon de la version actuelle. Alerte Telegram « nouvelle version » (option). Google Play non
  pris en charge (pas d'interface publique fiable).
- **Meilleurs moments pour publier** (Statistiques) : jours et heures où les posts marchent le mieux, chaque post
  étant comparé à la moyenne de son réseau (vues et réactions), sur 90 jours, par réseau ou tous ensemble ; bouton
  « Ajouter aux créneaux ».
- Les brouillons créés automatiquement affichent d'où ils viennent et la remarque de Claude.

Vérifié : tests d'API (lecture GitHub et App Store simulée, point de départ sans brouillon, brouillon à la version
suivante, capture d'écran jointe, calcul des meilleurs moments) ; dans le navigateur, ajout d'une vraie fiche App
Store et d'un vrai dépôt GitHub public, brouillon (texte simulé) ouvert dans l'éditeur. **Pas encore vérifié** :
brouillon rédigé par le vrai Claude, dépôt privé avec jeton.

## 1.8.0 — 22 novembre 2026

- **État des connexions** (administrateurs) : vérification en direct de l'adresse publique (HTTPS, joignable), des
  applications des réseaux et de chaque compte (autorisation, expiration, permissions accordées comparées à celles
  qu'exigent les options choisies, avec la liste des manquantes).
- **Lien en bio** : page publique par projet (`/b/<adresse>`), boutons, image, accroche, dernier post publié ;
  une adresse par réseau (`?src=instagram`…) pour savoir d'où viennent les visites ; clics comptés et redirigés avec
  UTM ; statistiques visites / clics ; aperçu dans Tamtam.
- Les permissions accordées sont désormais gardées à la connexion (X, TikTok, LinkedIn, YouTube).

Vérifié : tests d'API (diagnostic, page publique, échappement, comptage par source, redirection UTM, adresse
déjà prise), écrans dans le navigateur et page publique sur mobile en mode simulation. **Pas encore vérifié** :
lecture réelle des permissions chez Meta et Google.

## 1.7.0 — 22 novembre 2026

- **Boîte de réception** (nouvelle page) : commentaires reçus sous les posts publiés sur Facebook, Instagram,
  Threads, Bluesky, YouTube et X, relevés toutes les 30 minutes ; réponse depuis Tamtam, proposée par Claude au
  besoin (avec une consigne facultative) ; « Marquer comme traité ». Permissions de lecture et de réponse à
  activer par réseau dans Administration (Bluesky : aucune). TikTok et LinkedIn ne le permettent pas.
- **Validation à deux** (option) : les posts des membres passent par l'état « À valider » ; un administrateur
  valide (le post part à l'heure prévue) ou refuse avec un commentaire (retour en brouillon).
- Alertes Telegram : post à valider, nouveau commentaire (option).
- Pages légales : commentaires reçus et données envoyées à Claude pour proposer une réponse.

Vérifié : tests d'API (relève sans doublon, proposition avec un faux Claude, réponse, permissions demandées,
lecture et réponse simulées sur Bluesky, Facebook, YouTube et X, validation à deux de bout en bout), écrans dans le
navigateur en mode simulation. **Pas encore vérifié** : relève et réponse réelles sur chaque réseau.

## 1.6.0 — 22 novembre 2026

- **Quatre nouveaux réseaux** :
  - **Threads** : texte, image, vidéo ou carrousel de 20 médias ; application Threads à part ; jeton de 60 jours
    renouvelé automatiquement.
  - **Bluesky** : connexion avec un mot de passe d'application (pas d'application développeur), liens et hashtags
    cliquables, 4 images ou une vidéo (service vidéo de Bluesky).
  - **LinkedIn** : profil personnel (Share on LinkedIn) et, en option, Pages d'entreprise (Community Management
    API) ; images, carrousel d'images, vidéo ; rappel une semaine avant l'expiration de l'autorisation (60 jours).
  - **YouTube Shorts** : envoi reprenable, réglages par post (titre, visibilité, déclaration « pour les enfants »).
- Statistiques lues sur Threads (option), Bluesky et YouTube. Claude connaît le style de chaque nouveau réseau
  (le titre YouTube sur la première ligne).
- La liste des réseaux n'est plus figée dans la base (ajout possible sans migration).

Vérifié : tests d'API (publication en démonstration sur les quatre réseaux, réglages YouTube, échanges simulés avec
les API Bluesky, LinkedIn, YouTube et Threads), écrans dans le navigateur en mode simulation. **Pas encore
vérifié** : connexion et publication réelles sur Threads, Bluesky, LinkedIn et YouTube.

## 1.5.0 — 22 novembre 2026

- **Chiffres des réseaux** dans Statistiques : vues, J'aime, commentaires, partages (et portée, enregistrements
  quand le réseau les donne), par réseau et post par post. Relus toutes les 6 heures pour les posts de moins de
  30 jours, bouton « Actualiser ».
- **Bilan rédigé par Claude** : à la demande (7 derniers jours) ou automatiquement chaque lundi matin (option dans
  Administration), avec comparaison à la semaine précédente, points forts, points à améliorer et idées. Envoyé par
  Telegram si les alertes sont configurées.
- Administration → **Statistiques des réseaux** : demander à la connexion les permissions de lecture des
  statistiques (Meta `read_insights` + `instagram_manage_insights`, TikTok `video.list`), désactivées par défaut
  pour ne pas casser la connexion des applications qui ne les ont pas.
- Pages légales mises à jour (statistiques lues, chiffres envoyés à Claude pour le bilan).

Vérifié : tests d'API (lecture des chiffres en simulation, bilan avec un faux Claude, permissions demandées à la
connexion, découpage des semaines), écrans dans le navigateur en mode simulation. **Pas encore vérifié** : lecture
réelle sur Facebook, Instagram, TikTok et X (formats de réponse tirés de la documentation officielle), vrai bilan
rédigé par Claude.

## 1.4.0 — 22 novembre 2026

- **Campagne de lancement** (nouvelle page) : Claude rédige une série de 2 à 10 posts à partir d'une seule consigne ;
  relecture et correction de chaque post, puis programmation sur les créneaux du projet ou à intervalle régulier.
  Les posts qui ne peuvent pas partir tels quels (média manquant, réglages TikTok) sont créés en brouillons datés.
- **Créneaux de publication** par projet (Projets → Créneaux) et option « Prochain créneau » dans Nouveau post.
- **Recadrage par réseau** : case « Adapter le cadrage » (Instagram 4:5, TikTok 9:16, X 16:9), aperçu fidèle ; une
  image qu'Instagram refuserait est toujours recadrée. Les fichiers recadrés sont gardés à côté de l'original et
  supprimés avec lui.
- **Recycler** un post publié (Publications, Statistiques) : nouveau post pré-rempli, Claude propose une nouvelle
  formulation. Le post garde la trace de l'original.
- Les réglages TikTok ne sont plus repris quand on duplique un post (TikTok interdit de les pré-remplir).

Vérifié : tests d'API (créneaux et file d'attente, recadrage, campagne avec un faux Claude, recyclage), écrans dans
le navigateur en mode simulation. **Pas encore vérifié** : une vraie campagne rédigée par Claude, un vrai post
Instagram recadré.

## 1.3.0 — 22 novembre 2026

- **TikTok, écran conforme à l'audit** : réglages choisis à chaque post (compte affiché, « Qui peut voir » sans
  valeur par défaut et limité aux options permises, commentaires / duo / collage décochés et grisés si le compte les
  désactive, divulgation du contenu « Votre marque » / « Contenu de marque » avec l'étiquette correspondante, phrase
  d'acceptation des règles de TikTok, durée maximale de vidéo vérifiée, message de traitement après l'envoi).
  Le réglage de visibilité par compte (page Comptes) est supprimé.
- **Pages légales publiques** (français et anglais) : `/confidentialite`, `/conditions`, `/privacy`, `/terms`, avec
  éditeur et contact saisis dans Administration ; liens sur la page de connexion.
- **Alertes Telegram** : post en échec, compte à reconnecter (vérification quotidienne des comptes), post publié en
  option ; configuration guidée dans Administration (bot, recherche des conversations, message de test).
- Durée des vidéos enregistrée à l'envoi. Bouton « Rédiger avec Claude » déplacé au-dessus des onglets de texte.

Vérifié : tests d'API (réglages TikTok, pages légales, alertes avec un faux Telegram), écran TikTok dans le
navigateur en mode simulation. **Pas encore vérifié** : un vrai envoi TikTok avec ces réglages, un vrai bot Telegram.

## 1.2.0 — 21 novembre 2026

- **Claude regarde les médias** du post avant de rédiger : les images, et pour une vidéo 4 images fixes réparties
  sur sa durée (extraites avec PyAV). Case « Montrer les médias à Claude », cochée par défaut ; 8 images au plus par
  demande ; un média illisible est signalé sans bloquer la rédaction.
- Consigne de Claude : coller à ce que montrent les médias, ne rien inventer de ce qui n'est pas visible.

Vérifié : test d'API avec un faux client Claude (une image + une vraie vidéo MP4 générée : 5 images envoyées,
JPEG de 1 568 px au plus ; vidéo illisible signalée). **Pas encore vérifié** : un vrai appel à Claude avec images.

## 1.1.1 — 21 novembre 2026

- Rédaction : le **lien à promouvoir** n'est plus prérempli avec l'adresse du projet ; il est facultatif, et un
  bouton « Ajouter l'adresse du projet » le remplit à la demande.

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
