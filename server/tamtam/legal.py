"""Pages publiques « Politique de confidentialité » et « Conditions d'utilisation » (français et anglais).

Les portails développeurs (TikTok, Meta, LinkedIn, Google…) exigent leurs adresses lors de la validation d'une
application. Le nom de l'éditeur et l'adresse de contact se saisissent dans Administration (table site_settings).
Le texte décrit ce que fait réellement Tamtam : à tenir à jour si le traitement des données change.
"""
from __future__ import annotations

import html
import re

UPDATED = {"fr": "22 novembre 2026", "en": "November 22, 2026"}

PRIVACY_FR = """# Politique de confidentialité

Dernière mise à jour : {updated}

{app} est un outil de publication sur les réseaux sociaux utilisé par {operator} pour faire connaître ses propres
applications, sites et produits. Cette page explique quelles données il traite et pourquoi.

## Responsable du traitement

{operator} — contact : {contact}

## Données traitées

- **Comptes des utilisateurs de {app}** : nom, adresse e-mail, mot de passe (stocké sous forme chiffrée irréversible).
- **Comptes de réseaux sociaux connectés** (Facebook, Instagram, X, TikTok, Threads, Bluesky, LinkedIn, YouTube) :
  identifiant du compte, nom affiché, photo de profil et jetons d'accès délivrés par le réseau. Les jetons sont
  chiffrés en base. {app} ne connaît jamais vos mots de passe de réseaux sociaux (pour Bluesky, un « mot de passe
  d'application » sert une seule fois à ouvrir la session ; il n'est pas conservé).
- **Contenus publiés** : textes, images et vidéos préparés dans {app}, réglages de publication, et l'adresse des
  posts une fois publiés.
- **Statistiques des posts** lues sur les réseaux : nombres de vues, de mentions J'aime, de commentaires, de partages
  et d'enregistrements de chaque post publié par {app} (jamais l'identité des personnes).
- **Clics sur les liens courts** : uniquement un nombre de clics par jour. Ni adresse IP, ni cookie, ni profil des
  personnes qui cliquent ne sont conservés.

## Utilisation

Ces données servent uniquement à publier les contenus choisis par les utilisateurs de {app} sur les comptes qu'ils
ont connectés, à afficher l'état et les statistiques de ces publications, et à assurer la sécurité du service.
Elles ne sont ni vendues, ni utilisées à des fins publicitaires, ni partagées avec d'autres tiers que ceux-ci :

- **les réseaux sociaux** sur lesquels un utilisateur demande à publier, qui reçoivent le contenu du post ;
- **Anthropic** (assistant de rédaction Claude), seulement quand un utilisateur demande une proposition de texte :
  la consigne, le texte, la présentation du projet et, si l'utilisateur l'accepte, les images du post ; pour le
  bilan hebdomadaire, les textes des posts de la semaine et leurs chiffres (vues, mentions J'aime, commentaires…).

## Données TikTok

Pour TikTok, {app} utilise les informations de base du compte (nom affiché, photo) et l'autorisation de publier
(Content Posting API) et, si l'option est activée, les nombres de vues, de J'aime, de commentaires et de partages des
vidéos qu'il a publiées (video.list). Il ne lit pas les messages, les abonnés ni les contenus d'autres comptes.

## Conservation et suppression

Les données sont conservées tant que le compte de réseau social reste connecté. **Retirer** un compte dans {app}
efface ses jetons. Vous pouvez aussi retirer l'accès à tout moment depuis les réglages de sécurité du réseau social
(applications autorisées). Pour toute demande d'accès, de rectification ou de suppression : {contact}.

## Sécurité

Accès réservé aux utilisateurs autorisés, connexion chiffrée (HTTPS), jetons et secrets chiffrés en base,
sauvegardes quotidiennes.
"""

TERMS_FR = """# Conditions d'utilisation

Dernière mise à jour : {updated}

{app} est un outil interne de {operator} servant à préparer et publier des contenus sur les réseaux sociaux de
ses propres applications, sites et produits. Il n'est pas ouvert au public : seules les personnes invitées par un
administrateur peuvent s'y connecter.

## Utilisation

- Chaque utilisateur est responsable des contenus qu'il publie et doit respecter les règles de chaque réseau social
  (notamment celles de TikTok, Meta, X, LinkedIn et YouTube) ainsi que le droit applicable.
- Les contenus commerciaux doivent être signalés comme tels lorsque le réseau le demande.
- Les textes proposés par l'assistant de rédaction doivent être relus avant publication.

## Comptes de réseaux sociaux

En connectant un compte, l'utilisateur autorise {app} à publier en son nom les contenus qu'il valide. Cette
autorisation peut être retirée à tout moment dans {app} ou dans les réglages du réseau social.

## Responsabilité

{app} est fourni tel quel. {operator} ne garantit pas l'absence d'interruption et ne peut être tenu responsable
des décisions des réseaux sociaux (refus, retrait ou visibilité des contenus).

## Contact

{contact}
"""

PRIVACY_EN = """# Privacy Policy

Last updated: {updated}

{app} is a social media publishing tool used by {operator} to promote its own apps, websites and products. This
page explains which data it processes and why.

## Data controller

{operator} — contact: {contact}

## Data we process

- **{app} user accounts**: name, email address, password (stored as an irreversible hash).
- **Connected social media accounts** (Facebook, Instagram, X, TikTok, Threads, Bluesky, LinkedIn, YouTube): account
  ID, display name, profile picture and the access tokens issued by the network. Tokens are encrypted at rest.
  {app} never sees your social media passwords (for Bluesky, an "app password" is used once to open a session and
  is not stored).
- **Published content**: texts, images and videos prepared in {app}, posting settings, and the address of each post
  once published.
- **Post statistics** read from the networks: number of views, likes, comments, shares and saves of each post
  published by {app} (never who these people are).
- **Short link clicks**: only a daily click count. No IP address, cookie or profile of the people who click is kept.

## How we use it

This data is used only to publish the content chosen by {app} users to the accounts they connected, to show the
status and statistics of these posts, and to keep the service secure. It is not sold, not used for advertising, and
shared only with:

- **the social networks** a user asks to publish to, which receive the post content;
- **Anthropic** (Claude writing assistant), only when a user asks for a text suggestion: the instructions, the text,
  the project description and, if the user agrees, the post's images; for the weekly report, the week's post texts
  and their figures (views, likes, comments…).

## TikTok data

For TikTok, {app} uses basic account information (display name, avatar) and the permission to publish (Content
Posting API), and, if enabled, the view, like, comment and share counts of the videos it published (video.list). It
does not read messages, followers or other accounts' content.

## Retention and deletion

Data is kept while the social media account stays connected. **Removing** an account in {app} deletes its tokens.
You can also revoke access at any time in the social network's security settings (authorized apps). For any access,
correction or deletion request: {contact}.

## Security

Access limited to authorized users, encrypted connections (HTTPS), tokens and secrets encrypted at rest, daily
backups.
"""

TERMS_EN = """# Terms of Service

Last updated: {updated}

{app} is an internal tool of {operator} used to prepare and publish content on the social media accounts of its own
apps, websites and products. It is not open to the public: only people invited by an administrator can sign in.

## Use

- Each user is responsible for the content they publish and must follow each social network's rules (including
  TikTok, Meta, X, LinkedIn and YouTube) and applicable law.
- Commercial content must be disclosed as such when the network requires it.
- Texts suggested by the writing assistant must be reviewed before publishing.

## Social media accounts

By connecting an account, the user authorizes {app} to publish on their behalf the content they approve. This
authorization can be revoked at any time in {app} or in the social network's settings.

## Liability

{app} is provided as is. {operator} does not guarantee uninterrupted service and is not responsible for the social
networks' decisions (rejection, removal or visibility of content).

## Contact

{contact}
"""

PAGES = {
    "confidentialite": ("fr", PRIVACY_FR, "Politique de confidentialité", "privacy"),
    "conditions": ("fr", TERMS_FR, "Conditions d'utilisation", "terms"),
    "privacy": ("en", PRIVACY_EN, "Privacy Policy", "confidentialite"),
    "terms": ("en", TERMS_EN, "Terms of Service", "conditions"),
}


def _inline(text: str) -> str:
    t = html.escape(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    return re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', t)


def to_html(md: str) -> str:
    out, para, items = [], [], []

    def flush():
        nonlocal para, items
        if para:
            out.append(f"<p>{_inline(' '.join(para))}</p>")
        if items:
            out.append("<ul>" + "".join(f"<li>{_inline(i)}</li>" for i in items) + "</ul>")
        para, items = [], []

    for line in md.splitlines():
        if not line.strip():
            flush()
        elif line.startswith("#"):
            flush()
            level = min(len(line) - len(line.lstrip("#")), 2)
            out.append(f"<h{level}>{_inline(line.lstrip('#').strip())}</h{level}>")
        elif line.startswith("- "):
            if para:
                flush()
            items.append(line[2:].strip())
        elif line.startswith("  ") and items:
            items[-1] += " " + line.strip()
        else:
            para.append(line.strip())
    flush()
    return "\n".join(out)


def render(page: str, operator: str, contact: str) -> str | None:
    if page not in PAGES:
        return None
    lang, template, title, other = PAGES[page]
    missing = "[à compléter dans Administration]" if lang == "fr" else "[to be completed]"
    md = template.format(app="Tamtam", operator=operator.strip() or missing, contact=contact.strip() or missing,
                         updated=UPDATED[lang])
    switch = ('<a href="/{0}">English version</a>' if lang == "fr" else '<a href="/{0}">Version française</a>').format(other)
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — Tamtam</title><link rel="icon" href="/favicon.svg">
<style>
body {{ font: 16px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif; color: #1b2421; background: #f3f5f4; margin: 0; }}
main {{ max-width: 760px; margin: 0 auto; padding: 32px 16px 64px; }}
h1 {{ font-size: 28px; line-height: 1.2; }} h2 {{ font-size: 19px; margin-top: 28px; }}
a {{ color: #0e6e5c; }} nav {{ font-size: 14px; }}
@media (prefers-color-scheme: dark) {{ body {{ background: #0f1513; color: #e4ebe8; }} a {{ color: #5fc4ad; }} }}
</style></head><body><main><nav>{switch}</nav>
{to_html(md)}
</main></body></html>"""
