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
