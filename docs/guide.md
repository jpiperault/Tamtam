# Guide de Tamtam

Tamtam publie un même message sur Instagram, Facebook, X et TikTok, chacun dans son format, et compte les visites
que chaque réseau vous ramène.

## Les mots à connaître

- **Projet** : une appli, un site ou un produit à faire connaître. Chaque projet a ses propres comptes sociaux,
  ses posts et ses statistiques. Le projet actif se choisit en haut de la barre latérale.
- **Compte connecté** : un compte Instagram, une Page Facebook, un compte X ou TikTok que Tamtam a le droit de
  publier pour vous. Vous donnez ce droit sur la page officielle du réseau ; Tamtam ne voit jamais votre mot de passe.
- **Texte commun / texte adapté** : vous écrivez un texte pour tous les réseaux, puis vous pouvez l'adapter pour un
  réseau précis (plus court pour X, plus accrocheur pour TikTok…).
- **Lien suivi** : sur Facebook et X, Tamtam remplace le lien de votre post par un lien court (`/l/…`) qui compte
  les clics, puis renvoie vers votre page avec des paramètres `utm_` (utm_source = le réseau). Vos outils de
  statistiques de site voient ainsi d'où vient chaque visite.

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
- **Campagne** : un mot court (par exemple `lancement-v2`) qui sert à regrouper les visites dans vos statistiques.

### Ce que chaque réseau impose

| Réseau | Texte | Médias | Lien |
|---|---|---|---|
| Instagram | 2 200 caractères | obligatoire : 1 image, 1 vidéo (Reel) ou un carrousel de 10 au plus | pas cliquable : mettez-le dans la bio |
| Facebook | très long | facultatif : jusqu'à 10 images ou 1 vidéo | cliquable, suivi |
| X | 280 caractères (un lien compte pour 23) | facultatif : 4 images ou 1 vidéo | cliquable, suivi |
| TikTok | 2 200 caractères | obligatoire : 1 vidéo, ou des photos (carrousel) | pas cliquable : mettez-le dans la bio |

TikTok : tant que l'application Tamtam n'a pas passé l'audit de TikTok, les posts sont publiés en « Moi
uniquement ». La visibilité voulue se règle sur la carte du compte TikTok (page Comptes).

## Calendrier

La semaine affiche les posts programmés, publiés et les brouillons datés (bord en pointillés). « + Programmer »
ouvre un nouveau post à la date du jour choisi. Cliquer un post programmé permet de le modifier.

## Statistiques

Nombre de clics sur les liens suivis, par réseau, et les posts qui ont ramené le plus de visites. Instagram et TikTok
n'ayant pas de lien cliquable dans les posts, leurs visites se voient dans les statistiques de votre site (lien de
bio avec `utm_source=instagram` par exemple).

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
