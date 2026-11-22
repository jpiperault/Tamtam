# Guide de Tamtam

Tamtam publie un même message sur Instagram, Facebook, X, TikTok, Threads, Bluesky, LinkedIn et YouTube, chacun dans son format, et compte les visites
que chaque réseau vous ramène.

## Les mots à connaître

- **Projet** : une appli, un site ou un produit à faire connaître. Chaque projet a ses propres comptes sociaux,
  ses posts et ses statistiques. Le projet actif se choisit en haut de la barre latérale.
- **Compte connecté** : un compte Instagram, une Page Facebook, un compte X ou TikTok que Tamtam a le droit de
  publier pour vous. Vous donnez ce droit sur la page officielle du réseau ; Tamtam ne voit jamais votre mot de passe.
- **Texte commun / texte adapté** : vous écrivez un texte pour tous les réseaux, puis vous pouvez l'adapter pour un
  réseau précis (plus court pour X, plus accrocheur pour TikTok…).
- **Lien suivi** : sur X, Tamtam remplace le lien de votre post par un lien court (`/l/…`) qui compte les clics,
  puis renvoie vers votre page avec des paramètres `utm_` (utm_source = le réseau). Sur Facebook, c'est une
  **option** à cocher dans chaque post : sans elle, le lien direct vers votre page est publié (avec ses paramètres
  `utm_`, mais sans comptage des clics dans Tamtam). Vos outils de statistiques de site voient d'où vient chaque
  visite dans les deux cas.

## Premiers pas

1. **Projets** → **Nouveau projet** : nom et adresse du site ou de la page de téléchargement.
2. **Comptes** → **Connecter Instagram / Facebook / X / TikTok**. Vous partez sur le réseau, vous acceptez, vous
   revenez sur Tamtam. Pour Meta (Facebook et Instagram), Tamtam affiche les Pages et comptes Instagram trouvés :
   cochez ceux qui appartiennent à ce projet.
3. **Nouveau post** : choisissez les comptes, écrivez, ajoutez une image ou une vidéo, puis **Publier** ou
   **Programmer**.
4. **Publications** : suivez l'envoi réseau par réseau. Un réseau en échec affiche la raison et un bouton
   **Réessayer** (les réseaux déjà publiés ne sont pas republiés).

Si un bouton « Connecter » est grisé, l'application de ce réseau n'est pas encore configurée : voir
« Administration » plus bas.

## Écrire un post

- Les compteurs sous le texte montrent la longueur pour chaque réseau. En rouge : trop long, le bouton de
  publication reste bloqué tant que ce n'est pas corrigé (adaptez le texte dans l'onglet du réseau).
- L'aperçu à droite montre le post tel qu'il apparaîtra sur chaque réseau.
- **Médias** : glissez des fichiers ou cliquez sur « Ajouter ». Les images sont converties en JPEG (2048 px au
  plus). Vidéos acceptées : MP4 et MOV. La **médiathèque** garde tout ce qui a été envoyé pour le projet.
- **Lien à promouvoir** : facultatif et vide par défaut. Sans lien, le post ne contient que votre texte (et vos
  médias). Le bouton « Ajouter l'adresse du projet » remplit le champ avec l'adresse saisie dans la page Projets.
- **Campagne** : un mot court (par exemple `lancement-v2`) qui sert à regrouper les visites dans vos statistiques.
- **Facebook : utiliser aussi le lien court suivi** (case sous le lien, visible quand un compte Facebook est choisi) :
  décochée par défaut, le post Facebook montre votre vrai lien. Cochez-la pour compter les clics Facebook dans Tamtam.
- **Adapter le cadrage des images à chaque réseau** (case sous les médias, décochée par défaut) : au moment de
  publier, Tamtam recadre chaque image au centre au format conseillé du réseau : Instagram 4:5 (portrait),
  TikTok 9:16 (plein écran), X 16:9 (paysage). Facebook garde l'image d'origine. Votre fichier n'est pas modifié ;
  l'aperçu à droite montre le résultat. Même sans la case, une image qu'Instagram refuserait (plus haute que 4:5 ou
  plus large que 1,91:1) est recadrée automatiquement pour Instagram.
- **Quand** : « Maintenant », « Programmer » (date et heure au choix) ou **« Prochain créneau »** : le post prend le
  premier créneau libre du projet (voir ci-dessous), affiché sous les boutons.

### Créneaux de publication

Dans **Projets → Créneaux**, choisissez les jours et heures où vos posts partent, par exemple « mardi 18:30, jeudi
12:00 ». Ensuite, dans « Nouveau post », « Prochain créneau » place le post au premier créneau où aucun autre post du
projet n'est prévu. Pratique pour garder un rythme régulier sans chercher une date à chaque fois. Les heures sont
celles du serveur (heure de Paris par défaut).

### Recycler un post qui a marché

Un post publié peut resservir. Le bouton **Recycler** (dans Publications sur un post publié, et dans Statistiques
à côté des posts qui ont ramené le plus de visites) ouvre un nouveau post avec les mêmes comptes, médias et lien, et
demande à Claude une **nouvelle version** du texte : même message, autre accroche, pour ne pas paraître répété.
Vous relisez, ajustez, puis publiez ou programmez comme d'habitude. Les réglages TikTok sont à choisir à nouveau.

### Rédiger avec Claude

Le bouton **Rédiger avec Claude**, au-dessus du texte, demande une proposition à Claude (l'IA
d'Anthropic) :

1. Choisissez d'abord les comptes : Claude écrit une version pour chacun de leurs réseaux.
2. Dites ce que vous voulez annoncer (« la version 2 sort aujourd'hui, avec le mode sombre »), choisissez un ton,
   puis **Proposer un texte**. Si vous avez déjà écrit un premier jet, Claude l'améliore ou le réécrit.
3. Relisez la proposition : un texte commun et une version par réseau (plus courte pour X, avec hashtags pour
   Instagram et TikTok, renvoi vers le lien en bio quand le lien n'est pas cliquable).
4. **Utiliser ces textes** remplit le texte commun et les onglets des réseaux ; **Texte commun seulement** ne
   touche pas aux onglets. **Recommencer** permet de changer la consigne.

Rien n'est publié tant que vous n'avez pas cliqué sur Publier ou Programmer : relisez toujours, Claude peut se
tromper. Il s'appuie sur la **présentation du projet** (page Projets → Modifier) : plus elle est précise (ce que fait
l'app, pour qui, où la télécharger, le ton de la marque), meilleurs sont les textes. Claude n'invente pas de
fonctionnalité ni de chiffre ; s'il lui manque une information, il le signale au-dessus de la proposition.

**Claude regarde vos médias.** Si le post a des images ou une vidéo, la case « Montrer … à Claude » (cochée par
défaut) lui envoie les images, et pour une vidéo quatre images fixes réparties sur sa durée (Claude ne voit pas la
vidéo elle-même et n'entend pas le son). Il écrit alors un texte qui parle de ce qu'on y voit. Ajoutez donc vos
médias **avant** de cliquer sur « Rédiger avec Claude ». Au-delà de 8 images, les suivantes ne lui sont pas montrées.

Sont envoyés à Anthropic : la consigne, le texte, la présentation du projet, la liste des réseaux et, si la case
est cochée, les images (réduites à 1 568 px) ou les images extraites de la vidéo.

### Ce que chaque réseau impose

| Réseau | Texte | Médias | Lien |
|---|---|---|---|
| Instagram | 2 200 caractères | obligatoire : 1 image, 1 vidéo (Reel) ou un carrousel de 10 au plus | pas cliquable : mettez-le dans la bio |
| Facebook | très long | facultatif : jusqu'à 10 images ou 1 vidéo | cliquable ; suivi si l'option est cochée |
| X | 280 caractères (un lien compte pour 23) | facultatif : 4 images ou 1 vidéo | cliquable, suivi |
| TikTok | 2 200 caractères | obligatoire : 1 vidéo, ou des photos (carrousel) | pas cliquable : mettez-le dans la bio |
| Threads | 500 caractères | facultatif : jusqu'à 20 images et vidéos mélangées (carrousel) | cliquable, suivi |
| Bluesky | 300 caractères (lien compris) | facultatif : 4 images ou 1 vidéo MP4 de 3 minutes au plus | cliquable, suivi |
| LinkedIn | 3 000 caractères | facultatif : jusqu'à 20 images ou 1 vidéo | cliquable, suivi |
| YouTube | titre de 100 caractères + description | obligatoire : 1 vidéo verticale ou carrée de 3 minutes au plus (Short) | dans la description, suivi |

### Réglages YouTube (à chaque post)

Quand une chaîne YouTube est choisie, un bloc **Réglages YouTube** apparaît :

- **Titre** : vide, la première ligne du texte sert de titre et le reste de description. Rempli, tout le texte
  devient la description.
- **Visibilité** : publique, non répertoriée (visible seulement avec le lien) ou privée.
- **Vidéo conçue pour les enfants** : déclaration exigée par YouTube. Laissez décoché si la vidéo ne vise pas les
  enfants.

YouTube en fait un Short si la vidéo est verticale ou carrée et dure 3 minutes au plus. Google limite chaque
projet à 100 envois de vidéos par jour.

### Réglages TikTok (à chaque post)

Quand un compte TikTok est choisi, un bloc **Réglages TikTok** apparaît sous « Quand ». TikTok impose de tout
choisir à chaque post, sans valeur par défaut :

- le compte TikTok qui publiera (nom affiché par TikTok) ;
- **Qui peut voir** la vidéo ou les photos (liste vide au départ ; seules les options permises pour ce compte sont
  proposées) ;
- **Autoriser** : commentaires, et pour une vidéo duo et collage (décochés au départ ; grisés si le compte les a
  désactivés dans TikTok) ;
- **Divulgation du contenu** : à activer si le post fait la promotion de vous-même (**Votre marque** : étiquette
  « Contenu promotionnel ») ou d'un tiers (**Contenu de marque** : étiquette « Partenariat rémunéré », impossible en
  « Moi uniquement »).

La phrase « En publiant, vous acceptez… » au-dessus des boutons renvoie aux règles de TikTok. Une vidéo plus longue
que ce que le compte accepte est signalée avant l'envoi. Après la publication, TikTok peut mettre quelques minutes à
afficher le post sur le profil.

Tant que l'application Tamtam n'a pas passé l'audit de TikTok, les posts restent privés (« Moi uniquement ») et le
compte TikTok doit lui-même être en mode privé au moment de publier.

## Campagne de lancement

Page **Campagne** : décrivez ce que vous lancez (une nouvelle version, une appli, une offre), choisissez le nombre de
posts (2 à 10), le ton et les comptes. Claude rédige une **série** de posts qui se suivent (par exemple teaser,
annonce, un bénéfice par post, rappel), chacun avec son texte commun et ses versions par réseau. Rien n'est publié à
cette étape.

1. Relisez chaque post, corrigez le texte, décochez « Garder » pour écarter un post.
2. Donnez un nom de campagne (pour les statistiques) et choisissez le rythme : **créneaux du projet** (chaque post
   prend le créneau libre suivant) ou **intervalle régulier** (premier post à la date choisie, puis tous les N jours).
3. « Programmer » crée les posts. Ceux qui peuvent partir tels quels sont programmés. Les autres sont créés en
   **brouillons datés** : c'est le cas dès qu'Instagram ou TikTok est choisi (il faut une image ou une vidéo, et
   pour TikTok les réglages du post). Ouvrez-les depuis Publications → Brouillons, ajoutez le média, puis
   programmez-les.

Une campagne compte pour une seule rédaction dans la limite quotidienne de Claude.

## Boîte de réception

Page **Boîte de réception** : les commentaires reçus sous vos posts publiés, tous réseaux confondus, au même endroit.
Tamtam les relève toutes les 30 minutes (posts publiés depuis moins de 30 jours) ; **Relever** le fait tout de suite.
Le nombre de commentaires à traiter s'affiche dans le menu.

Pour chaque commentaire :

- **Proposer avec Claude** : Claude écrit une réponse courte, dans la langue du commentaire, sans rien inventer (s'il
  ne connaît pas la réponse, il propose de revenir vers la personne et vous le signale). Une consigne facultative
  l'oriente (« tutoie », « remercie et propose un code promo »…). Chaque proposition compte pour une rédaction.
- Corrigez si besoin, puis **Répondre** : la réponse est publiée sous le commentaire, sur le réseau.
- **Marquer comme traité** pour les commentaires qui n'appellent pas de réponse (filtre « Traités »).

Réseaux relevés :

| Réseau | Ce qu'il faut |
|---|---|
| Bluesky | rien, toujours relevé |
| Facebook, Instagram | option cochée (Administration → Boîte de réception), permissions `pages_read_user_content`, `pages_manage_engagement`, `instagram_manage_comments` ajoutées à l'app Meta, comptes reconnectés. Facebook ne donne pas toujours le nom de l'auteur. |
| Threads | option cochée, permissions `threads_read_replies` et `threads_manage_replies` ajoutées à l'app Threads, compte reconnecté |
| YouTube | option cochée et chaîne reconnectée. Une réponse coûte 50 unités du quota quotidien (10 000). |
| X | option cochée. X facture chaque commentaire lu, ne remonte que les 7 derniers jours, et refuse souvent les réponses d'une application (seulement si l'auteur vous a mentionné) : répondez alors depuis X. |
| TikTok, LinkedIn | impossible : ces réseaux ne donnent pas accès aux commentaires |

## Validation à deux

Option dans **Administration → Utilisateurs** : les posts des **membres** attendent l'accord d'un administrateur.

- Le membre écrit son post comme d'habitude, choisit « Maintenant », une date ou le prochain créneau, puis
  **Envoyer pour validation**. Le post apparaît dans Publications avec l'état « À valider ».
- Les administrateurs voient le nombre de posts à valider dans le menu (et reçoivent une alerte Telegram si elle
  est cochée). Dans Publications → **À valider** :
  - **Valider** : le post part à l'heure prévue, ou tout de suite si elle est passée ;
  - **Refuser** avec un commentaire : le post redevient un brouillon et l'auteur voit la raison.
- Le membre corrige le brouillon et le renvoie. Un post déjà validé qu'un membre modifie repasse en validation.
- Les posts des administrateurs partent directement. Les campagnes d'un membre passent aussi en validation.

## Calendrier

La semaine affiche les posts programmés, publiés et les brouillons datés (bord en pointillés). « + Programmer »
ouvre un nouveau post à la date du jour choisi. Cliquer un post programmé permet de le modifier.

## Statistiques

### Bilan rédigé par Claude

« **Bilan des 7 derniers jours** » : Claude lit les chiffres de la semaine (posts publiés, vues, J'aime,
commentaires, partages, clics) et les compare à la semaine précédente. Il écrit un résumé, les points forts, ce qui
peut s'améliorer et des idées de posts pour la semaine qui vient. Il ne cite que les chiffres réels ; une cause
supposée est présentée comme une hypothèse. Chaque bilan compte pour une rédaction.

Si l'option est activée (Administration → Statistiques des réseaux), un bilan est rédigé **automatiquement chaque
lundi matin** pour chaque projet qui a publié dans la semaine, et envoyé par Telegram si les alertes sont
configurées.

### Chiffres des réseaux

Pour chaque réseau : nombre de posts et total des vues, J'aime, commentaires et partages sur la période, puis le
détail post par post (avec un bouton **Recycler** pour republier ceux qui ont marché). Tamtam relit ces chiffres
toutes les 6 heures pour les posts publiés depuis moins de 30 jours ; **Actualiser** les relit tout de suite.

Ce que chaque réseau donne :

| Réseau | Sans réglage | Avec la permission en plus |
|---|---|---|
| Facebook | J'aime (réactions), commentaires, partages | + vues et personnes touchées (`read_insights`) |
| Instagram | J'aime, commentaires | + vues, portée, partages, enregistrements (`instagram_manage_insights`) |
| TikTok | rien | vues, J'aime, commentaires, partages (`video.list`) |
| X | vues, J'aime, réponses, reposts, signets | lecture payante chez X : il faut des crédits API |
| Threads | rien | vues, J'aime, réponses, partages (`threads_manage_insights`) |
| Bluesky | J'aime, réponses, partages, signets | (aucune permission à ajouter) |
| LinkedIn | rien | réservé aux apps validées pour la Community Management API |
| YouTube | vues, J'aime, commentaires | (aucune permission à ajouter) |

Un « – » veut dire que le réseau ne fournit pas ce chiffre. Une raison s'affiche sous le tableau quand un réseau
refuse la lecture.

**Ajouter les permissions** (Administration → Statistiques des réseaux) :

1. Ajoutez d'abord la permission à votre application développeur. Pour Meta : dans le cas d'utilisation
   « Gérer tout sur votre Page », ajoutez `read_insights` ; dans « Gérer les messages et le contenu sur Instagram »,
   ajoutez `instagram_manage_insights`. Pour TikTok : ajoutez le produit **Display API** (permission `video.list`).
2. Cochez la case du réseau dans Tamtam.
3. Reconnectez les comptes de ce réseau (page Comptes) pour accepter la nouvelle permission.

Attention : si vous cochez la case sans avoir ajouté la permission à l'application, la connexion au réseau échoue
(« Invalid Scopes » chez Meta). Décochez-la pour revenir en arrière. En mode « développement », les permissions
marchent pour les comptes de test de l'application ; pour d'autres comptes, Meta et TikTok demandent une validation
de l'application.

TikTok ne donne pas de chiffres pour un post privé (« Moi uniquement »), ni tant qu'il est en modération.

### Clics sur les liens

Nombre de clics sur les liens suivis, par réseau, et les posts qui ont ramené le plus de visites. Instagram et TikTok
n'ayant pas de lien cliquable dans les posts, leurs visites se voient dans les statistiques de votre site (lien de
bio avec `utm_source=instagram` par exemple). Il en va de même pour Facebook quand le lien court n'est pas coché :
cherchez `utm_source=facebook` dans les statistiques de votre site.

## Comptes : vérifier, retirer

- **Vérifier** teste que l'autorisation est toujours valable.
- **À reconnecter** : le réseau a retiré l'autorisation (mot de passe changé, droits retirés, délai dépassé).
  Cliquez « Connecter » à nouveau : le compte est mis à jour sans perdre son historique.
- **Retirer** efface le compte et ses jetons de Tamtam. Les posts déjà parus restent en ligne.

## Administration (administrateurs)

### Applications des réseaux

Pour publier, Tamtam a besoin d'une « application développeur » par réseau : Meta (une seule pour Facebook et
Instagram), X et TikTok. La page Administration donne, pour chacune, les étapes et l'**adresse de retour** à
copier dans le portail du réseau. Saisissez ensuite l'identifiant et le secret : ils sont chiffrés en base et ne
réapparaissent jamais en clair. Laisser le champ secret vide garde le secret déjà enregistré.

### Configurer Meta (Facebook et Instagram) pas à pas

Une seule application Meta sert à Facebook et à Instagram. Comptez 15 minutes. Les noms des boutons sont ceux du
site developers.facebook.com en novembre 2026 ; Meta les change parfois.

**Avant de commencer : la forme des comptes à publier**

- **Facebook : une Page, pas un profil.** Meta ne laisse publier par API que sur une Page Facebook, jamais sur un
  profil personnel (même créé pour l'app). Si besoin : Facebook → menu → Pages → **Créer une Page**.
- **Instagram : un compte professionnel relié à la Page.** Dans l'appli Instagram : Paramètres → Type de compte
  et outils → **Passer à un compte professionnel** (Créateur ou Entreprise, gratuit). Puis, sur la Page Facebook :
  Paramètres → **Comptes liés** → Instagram → Connecter le compte.
- **Qui se connecte depuis Tamtam :** une personne administratrice de la Page **et** qui a un rôle sur l'app Meta
  (tant que Meta n'a pas validé l'app). Le plus simple : votre compte Facebook personnel, ajouté comme
  administrateur de la Page (Paramètres de la Page → Accès à la Page). Pour utiliser un compte Facebook dédié à la
  place : dans l'app Meta, **Rôles de l'app** → l'ajouter comme Testeur, puis accepter l'invitation depuis ce compte.

**1. Créer l'app Meta**

Sur developers.facebook.com → **Mes apps** → **Créer une app** : nom et e-mail de contact, puis cochez les cas
d'utilisation **« Gérer tout sur votre Page »** et **« Gérer les messages et le contenu sur Instagram »** (filtre
« Gestion de contenu »). Pas besoin de portefeuille d'entreprise pour l'instant.

Ces deux cas d'utilisation ne se combinent pas avec « Authentifier et demander des données avec Facebook Login ».
Si votre app existante a celui-là (par exemple pour la connexion des joueurs d'un jeu) et que les deux cas sont
grisés, créez une **app à part pour Tamtam**.

**2. Ajouter les autorisations**

Dans la liste des cas d'utilisation, bouton **Personnaliser** de chacun, puis **Ajouter** en face de :

| Cas d'utilisation | Autorisations à ajouter |
|---|---|
| Gérer tout sur votre Page | `pages_manage_posts`, `pages_read_engagement` (`pages_show_list` et `business_management` y sont déjà) |
| Gérer les messages et le contenu sur Instagram | choisir la configuration **« API avec Facebook Login »**, puis `instagram_basic`, `instagram_content_publish` |

Attention aux noms voisins : `instagram_business_basic`, `instagram_business_content_publish`… servent à l'autre
méthode (« Instagram Login »), que Tamtam n'utilise pas. Chaque autorisation ajoutée doit afficher **« Prête pour
le test »**. Inutile d'ajouter les autres.

**3. Déclarer l'adresse de Tamtam**

- **Paramètres de l'app → Général** :
  - **Domaines de l'app** : le domaine seul, par exemple `tamtam.piperault.fr` (sans `https://` ni `/`).
  - Tout en bas : **Ajouter une plateforme** → **Site web**, URL du site `https://tamtam.piperault.fr/`.
  - **Enregistrer les modifications** (barre en bas de l'écran).
- **Facebook Login for Business → Paramètres** (menu de gauche) :
  - **URI de redirection OAuth valides** : collez l'adresse de retour affichée dans Tamtam (Administration), par
    exemple `https://tamtam.piperault.fr/api/v1/connect/meta/callback`, puis **appuyez sur Entrée** : l'adresse
    doit devenir une pastille. Sans Entrée, elle n'est pas gardée.
  - Laissez activés Connexion OAuth cliente, Connexion OAuth Web, Imposer le HTTPS et le mode strict.
  - **Enregistrer les modifications**, puis contrôlez avec le **Validateur d'URI de redirection** en bas de page.

**4. Saisir l'app dans Tamtam**

Paramètres de l'app → Général : copiez l'**Identifiant de l'application** et la **Clé secrète** (bouton
« Afficher », Facebook redemande votre mot de passe). Dans Tamtam → Administration → carte Meta : collez-les, puis
**Enregistrer**. Vérifiez que l'identifiant est bien celui de l'app que vous venez de régler (si vous avez
plusieurs apps Meta, c'est une erreur fréquente).

**5. Connecter les comptes**

Tamtam → **Comptes** → **Connecter Facebook** (ou Instagram, c'est la même connexion). Sur Facebook, cochez la
Page et son compte Instagram, validez. De retour dans Tamtam, cochez les comptes à rattacher au projet.

**Messages de Facebook et solution**

| Message | Cause | Solution |
|---|---|---|
| « Impossible de charger cette URL : le domaine de cette URL n'est pas inscrit… » | Domaine ou adresse de retour non déclarés, ou identifiant d'une autre app dans Tamtam | Étapes 3 et 4 ; vérifier l'identifiant de l'app |
| « Invalid Scopes: pages_manage_posts, instagram_basic… » | Autorisations pas encore ajoutées à l'app | Étape 2 |
| Tamtam affiche « Connexion expirée ou invalide » | Retour sur Tamtam sans connexion valable, par exemple après avoir cliqué « OK » sur un message d'erreur de Facebook, ou plus de 30 minutes passées sur Facebook | Corriger l'erreur Facebook, puis relancer « Connecter » depuis la page Comptes |
| Tamtam affiche « Aucun compte trouvé » | Pas de Page gérée par ce compte Facebook, ou Page non cochée pendant la connexion | Vérifier « Avant de commencer » ; relancer et cocher la Page |
| Le compte Instagram n'apparaît pas | Compte personnel ou non relié à la Page | Passer en compte professionnel et le relier à la Page |

Tant que Meta n'a pas validé l'app (« App Review »), elle reste en mode développement : seules les personnes qui
ont un rôle sur l'app peuvent connecter leurs comptes. Cela suffit pour publier sur vos propres Pages. La
validation n'est nécessaire que pour laisser d'autres personnes connecter leurs comptes.

### Configurer Threads

Threads utilise une application Meta à part (pas celle de Facebook et Instagram).

1. developers.facebook.com → **Créer une app** → cas d'utilisation **« Accéder à l'API Threads »**.
2. Cas d'utilisation → Personnaliser : ajoutez `threads_basic` et `threads_content_publish` (et
   `threads_manage_insights` si vous voulez les statistiques, voir Statistiques des réseaux).
3. Paramètres de Threads : collez l'adresse de retour affichée dans Administration (carte Threads) dans
   « URL de rappel de redirection ».
4. Rôles de l'app → ajoutez votre compte Threads comme **testeur**, puis acceptez l'invitation dans l'appli Threads
   (Réglages → Compte → Autorisations du site web). Tant que l'app n'est pas validée par Meta, seuls les testeurs
   peuvent se connecter.
5. Copiez l'**ID de l'app Threads** et sa **clé secrète** dans la carte Threads d'Administration.

Le jeton dure 60 jours ; Tamtam le renouvelle tout seul une semaine avant l'échéance.

### Configurer Bluesky

Rien à faire dans Administration : sur la page Comptes, **Connecter Bluesky** demande votre pseudo et un **mot de
passe d'application** (Bluesky → Réglages → Confidentialité et sécurité → Mots de passe d'application → Ajouter).
Ce n'est pas votre mot de passe habituel : il ne sert qu'à Tamtam et vous pouvez le supprimer à tout moment pour
couper l'accès. Pour publier des vidéos, l'adresse e-mail du compte Bluesky doit être vérifiée.

### Configurer LinkedIn

1. linkedin.com/developers → **Create app**. LinkedIn demande une Page d'entreprise associée, qui doit valider l'app
   (lien de vérification à envoyer à un administrateur de la Page).
2. Onglet **Products** : ajoutez « Sign In with LinkedIn using OpenID Connect » et « Share on LinkedIn ». C'est
   immédiat.
3. Onglet **Auth** : collez l'adresse de retour de la carte LinkedIn dans « Authorized redirect URLs for your app »,
   puis copiez le **Client ID** et le **Primary Client Secret** dans Administration.

Cela permet de publier sur **votre profil**. Publier sur une **Page d'entreprise** demande en plus la « Community
Management API », que LinkedIn accorde sur dossier (entreprise enregistrée, adresse e-mail professionnelle). Une
fois accordée, cochez **LinkedIn : publier aussi sur les Pages d'entreprise** (Administration → Statistiques des
réseaux) et reconnectez le compte : vos Pages apparaissent à côté du profil.

LinkedIn ne renouvelle pas l'autorisation des applications ordinaires : il faut **reconnecter le compte tous les
60 jours**. La page Comptes affiche la date limite et Tamtam prévient par Telegram une semaine avant. LinkedIn ne
donne pas non plus les statistiques des posts sans la Community Management API.

### Configurer YouTube

1. console.cloud.google.com → créez un projet → API et services → **Bibliothèque** : activez « YouTube Data API
   v3 ».
2. **Écran de consentement OAuth** : type « Externe », ajoutez votre adresse Google comme utilisateur test. Tant que
   l'app reste « en test », Google retire l'autorisation au bout de 7 jours : publiez l'app (bouton « Publier
   l'application ») pour éviter de reconnecter chaque semaine.
3. **Identifiants** → Créer des identifiants → ID client OAuth → Application Web ; collez l'adresse de retour de la
   carte Google (YouTube) dans « URI de redirection autorisés ».
4. Copiez l'**ID client** et le **code secret** dans Administration.

Les vidéos peuvent être publiques dès la connexion (YouTube a levé en novembre 2026 le blocage en privé des apps
non validées).

### Claude (rédaction)

Pour activer « Rédiger avec Claude » : sur **console.anthropic.com**, créez un compte, ajoutez du crédit
(**Billing**), puis **API Keys → Create Key**. Dans Tamtam → Administration → carte **Claude** : collez la clé
(elle commence par `sk-ant-`), choisissez le modèle et le nombre maximal de rédactions par jour, **Enregistrer**,
puis **Tester la clé**. La clé est chiffrée en base et ne réapparaît jamais.

- **Modèle** : Claude Opus 5.5 donne les meilleurs textes (quelques centimes par rédaction) ; Sonnet 5.5 et
  Haiku 5.5 sont plus rapides et moins chers.
- **Rédactions par jour** : limite commune à tous les utilisateurs, pour maîtriser la facture. La carte affiche
  l'usage du jour et du mois.
- **Effacer la clé** désactive le bouton pour tout le monde.

### Pages légales

TikTok, Meta, LinkedIn et Google demandent l'adresse d'une **politique de confidentialité** et de **conditions
d'utilisation** pour valider une application. Tamtam les fournit, en français et en anglais, sans connexion :
`/confidentialite`, `/conditions`, `/privacy`, `/terms`. Dans Administration → **Pages légales**, saisissez le nom
de l'éditeur (vous ou votre société) et une adresse de contact, puis copiez les adresses dans les portails
développeurs.

### Alertes Telegram

Tamtam peut vous prévenir sur Telegram quand un post échoue (après ses nouveaux essais automatiques), quand un compte
doit être reconnecté (vérifié aussi une fois par jour), quand le bilan du lundi est prêt (il est alors envoyé en
entier), quand un membre propose un post à valider, et, si vous le voulez, quand un post est publié ou qu'un
nouveau commentaire arrive.

1. Dans Telegram, ouvrez **@BotFather**, envoyez `/newbot`, choisissez un nom : il vous donne un jeton.
2. Administration → **Alertes Telegram** : collez le jeton, **Enregistrer**.
3. Ouvrez votre bot dans Telegram et envoyez-lui `/start` (ou ajoutez-le à un groupe d'équipe).
4. **Chercher les conversations**, cochez les destinataires, puis **Envoyer un test**.

### Utilisateurs

Ajoutez les personnes qui publient. Tous les utilisateurs voient tous les projets ; seuls les administrateurs
voient cette page. Un mot de passe changé par l'administrateur ferme les sessions ouvertes de la personne.

## En cas de problème

- **« Publication interrompue par un redémarrage »** : Tamtam a redémarré pendant l'envoi. Vérifiez sur le réseau
  si le post est paru avant de cliquer « Réessayer », pour éviter un doublon.
- **« Trop de requêtes » / « le service ne répond pas »** : Tamtam réessaie seul jusqu'à 3 fois (après 5 puis
  10 minutes).
- **Instagram refuse l'image** : vérifiez le format (entre 4:5 et 1.91:1 pour une image seule).
- **Mode simulation** (bandeau orange) : rien n'est publié pour de vrai. Les « comptes de démonstration »
  servent à essayer Tamtam sans application développeur.
