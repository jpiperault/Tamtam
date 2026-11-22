"""Point d'entrée unique vers les réseaux : connexion, renouvellement des jetons, publication.

En mode simulation (SIMULATION=true), les comptes « de démonstration » ne contactent aucun réseau.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import secrets

from . import bluesky, linkedin, meta, threads, tiktok, x, youtube
from .base import (LABELS, PLATFORMS, PROVIDER_OF, RULES, AuthExpired, Content, MediaFile, PublishError, Result,
                   check, text_length)

PROVIDERS = ("meta", "x", "tiktok", "threads", "linkedin", "google", "bluesky")
PROVIDER_LABELS = {"meta": "Meta (Facebook et Instagram)", "x": "X", "tiktok": "TikTok", "threads": "Threads",
                   "linkedin": "LinkedIn", "google": "Google (YouTube)", "bluesky": "Bluesky"}
# Bluesky : pas d'application développeur, connexion avec le pseudo et un « mot de passe d'application ».
NO_APP = ("bluesky",)
# Réseaux dont le jeton d'accès est court et se renouvelle avec un jeton de renouvellement.
REFRESHABLE = ("x", "tiktok", "threads", "bluesky", "linkedin", "youtube")

__all__ = ["LABELS", "PLATFORMS", "PROVIDERS", "PROVIDER_OF", "RULES", "AuthExpired", "Content", "MediaFile",
           "PublishError", "Result", "check", "text_length"]


def pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return verifier, challenge


# Permissions de lecture des statistiques, demandées seulement si l'administrateur l'a choisi (Administration →
# Statistiques) : un réseau refuse toute la connexion si l'application développeur ne les a pas ajoutées.
STATS_SCOPES = {"meta": ["read_insights", "instagram_manage_insights"], "tiktok": ["video.list"],
                "threads": threads.STATS_SCOPES}
# Boîte de réception : permissions de lecture et de réponse aux commentaires (option dans Administration).
INBOX_SCOPES = {"meta": ["pages_read_user_content", "pages_manage_engagement", "instagram_manage_comments"],
                "threads": ["threads_read_replies", "threads_manage_replies"],
                "google": ["https://www.googleapis.com/auth/youtube.force-ssl"],
                "x": []}
# Réseaux dont Tamtam sait lire les commentaires ; Bluesky toujours, les autres si l'option est cochée.
INBOX = ("facebook", "instagram", "threads", "bluesky", "youtube", "x")


def authorize_url(provider: str, client_id: str, redirect_uri: str, state: str, verifier: str,
                  graph_version: str, stats: bool = False, pages: bool = False, inbox: bool = False) -> str:
    extra = (STATS_SCOPES.get(provider, []) if stats else []) + (INBOX_SCOPES.get(provider, []) if inbox else [])
    if provider == "meta":
        return meta.authorize_url(client_id, redirect_uri, state, None, graph_version, extra)
    if provider == "x":
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        return x.authorize_url(client_id, redirect_uri, state, challenge)
    if provider == "tiktok":
        return tiktok.authorize_url(client_id, redirect_uri, state, extra)
    if provider == "threads":
        return threads.authorize_url(client_id, redirect_uri, state, extra)
    if provider == "linkedin":
        return linkedin.authorize_url(client_id, redirect_uri, state, linkedin.PAGE_SCOPES if pages else [])
    if provider == "google":
        return youtube.authorize_url(client_id, redirect_uri, state, extra)
    raise ValueError(provider)


async def exchange(provider: str, client_id: str, secret: str | None, redirect_uri: str, code: str,
                   verifier: str | None, graph_version: str) -> list[dict]:
    if provider == "meta":
        return await meta.exchange(client_id, secret or "", redirect_uri, code, None, graph_version)
    if provider == "x":
        return await x.exchange(client_id, secret, redirect_uri, code, verifier or "")
    if provider == "tiktok":
        return await tiktok.exchange(client_id, secret or "", redirect_uri, code)
    if provider == "threads":
        return await threads.exchange(client_id, secret or "", redirect_uri, code)
    if provider == "linkedin":
        return await linkedin.exchange(client_id, secret or "", redirect_uri, code)
    if provider == "google":
        return await youtube.exchange(client_id, secret or "", redirect_uri, code)
    raise ValueError(provider)


async def refresh(platform: str, client_id: str, secret: str | None, refresh_token: str,
                  meta_info: dict | None = None) -> dict:
    if platform == "x":
        return await x.refresh(client_id, secret, refresh_token)
    if platform == "tiktok":
        return await tiktok.refresh(client_id, secret or "", refresh_token)
    if platform == "threads":
        return await threads.refresh(refresh_token)
    if platform == "bluesky":
        return await bluesky.refresh(refresh_token, meta_info)
    if platform == "linkedin":
        return await linkedin.refresh(client_id, secret or "", refresh_token)
    if platform == "youtube":
        return await youtube.refresh(client_id, secret or "", refresh_token)
    raise PublishError("ce réseau ne renouvelle pas ses jetons")


def demo_candidates(provider: str) -> list[dict]:
    tag = secrets.token_hex(3)
    def one(platform, name, handle):
        return {"platform": platform, "external_id": f"demo-{platform}-{tag}", "name": name, "handle": handle,
                "avatar_url": "", "access_token": "demo", "meta": {}, "simulated": True}
    if provider == "meta":
        return [one("facebook", "Page de démonstration", ""), one("instagram", "Compte démo", "compte.demo")]
    if provider == "x":
        return [one("x", "Compte démo", "compte_demo")]
    if provider == "threads":
        return [one("threads", "Compte démo", "compte.demo")]
    if provider == "bluesky":
        return [one("bluesky", "Compte démo", "compte-demo.bsky.social")]
    if provider == "linkedin":
        page = one("linkedin", "Page de démonstration", "")
        page["external_id"] += "-page"
        page["meta"] = {"kind": "page", "page_name": "Page de démonstration"}
        return [one("linkedin", "Profil de démonstration", ""), page]
    if provider == "google":
        return [one("youtube", "Chaîne de démonstration", "chaine-demo")]
    return [one("tiktok", "Compte démo", "compte.demo")]


async def publish(platform: str, account: dict, content: Content, graph_version: str) -> Result:
    if account.get("simulated"):
        await asyncio.sleep(1.0)
        return Result(f"demo-{secrets.token_hex(4)}", "")
    if platform == "facebook":
        return await meta.publish_facebook(account, content, graph_version)
    if platform == "instagram":
        return await meta.publish_instagram(account, content, graph_version)
    if platform == "x":
        return await x.publish(account, content)
    if platform == "tiktok":
        return await tiktok.publish(account, content)
    if platform == "threads":
        return await threads.publish(account, content)
    if platform == "bluesky":
        return await bluesky.publish(account, content)
    if platform == "linkedin":
        return await linkedin.publish(account, content)
    if platform == "youtube":
        return await youtube.publish(account, content)
    raise PublishError(f"réseau inconnu : {platform}")


METRIC_FIELDS = ("views", "reach", "likes", "comments", "shares", "saves")


def simulated_metrics(external_id: str, published_at) -> dict:
    """Chiffres factices mais stables (mode simulation) : ils grandissent avec l'âge du post."""
    import hashlib
    from datetime import datetime, timezone

    seed = int(hashlib.sha256(external_id.encode()).hexdigest()[:8], 16)
    hours = max(1.0, (datetime.now(timezone.utc) - published_at).total_seconds() / 3600) if published_at else 1.0
    growth = min(1.0, hours / 72) ** 0.5
    views = int((300 + seed % 4700) * growth)
    return {"views": views, "reach": int(views * 0.8), "likes": int(views * (0.02 + seed % 7 / 100)),
            "comments": int(views * 0.004), "shares": int(views * 0.003), "saves": int(views * 0.002)}


async def metrics(platform: str, account: dict, external_id: str, graph_version: str, published_at=None) -> dict:
    """Chiffres d'un post publié : {views, reach, likes, comments, shares, saves} (None si non fourni)."""
    if account.get("simulated"):
        return simulated_metrics(external_id, published_at)
    if platform == "facebook":
        return await meta.facebook_metrics(account, external_id, graph_version)
    if platform == "instagram":
        return await meta.instagram_metrics(account, external_id, graph_version)
    if platform == "x":
        return await x.metrics(account, external_id)
    if platform == "tiktok":
        return await tiktok.metrics(account, external_id)
    if platform == "threads":
        return await threads.metrics(account, external_id)
    if platform == "bluesky":
        return await bluesky.metrics(account, external_id)
    if platform == "linkedin":
        return await linkedin.metrics(account, external_id)
    if platform == "youtube":
        return await youtube.metrics(account, external_id)
    raise PublishError(f"réseau inconnu : {platform}")


async def check_token(platform: str, account: dict, graph_version: str) -> None:
    """Vérifie que le réseau accepte encore le jeton (AuthExpired sinon)."""
    if account.get("simulated"):
        return
    if platform in ("facebook", "instagram"):
        await meta.check_token(account, graph_version)
    elif platform == "tiktok":
        await tiktok.creator_info(account["access_token"])
    elif platform == "threads":
        await threads.check_token(account)
    elif platform == "linkedin":
        await linkedin.check_token(account)
    elif platform == "youtube":
        await youtube.check_token(account)
    elif platform == "bluesky":
        await bluesky.metrics_ready(account)


def simulated_comments(external_id: str) -> list[dict]:
    """Commentaires factices et stables (mode simulation)."""
    import hashlib

    n = int(hashlib.sha256(external_id.encode()).hexdigest()[:2], 16) % 3
    samples = [("Julie", "julie.m", "Trop bien ! Elle est disponible sur Android ?"),
               ("Marc", "marc_dev", "Je l'utilise depuis une semaine, le mode sombre est top."),
               ("Sofia", "sofia", "Combien ça coûte ?")]
    return [{"id": f"{external_id}-c{i}", "text": t, "author_name": a, "author_handle": h, "author_avatar": "",
             "created_at": None, "own": False} for i, (a, h, t) in enumerate(samples[:n + 1])]


async def comments(platform: str, account: dict, external_id: str, graph_version: str) -> list[dict]:
    """Commentaires sous un post publié : [{id, text, author_name, author_handle, author_avatar, created_at, own,
    extra}]."""
    if account.get("simulated"):
        return simulated_comments(external_id)
    if platform == "facebook":
        return await meta.facebook_comments(account, external_id, graph_version)
    if platform == "instagram":
        return await meta.instagram_comments(account, external_id, graph_version)
    if platform == "threads":
        return await threads.comments(account, external_id)
    if platform == "bluesky":
        return await bluesky.comments(account, external_id)
    if platform == "youtube":
        return await youtube.comments(account, external_id)
    if platform == "x":
        return await x.comments(account, external_id)
    raise PublishError(f"{LABELS.get(platform, platform)} ne permet pas de lire les commentaires")


async def reply(platform: str, account: dict, item: dict, text: str, graph_version: str) -> str:
    """Répond au commentaire `item` (ligne de inbox_items) ; renvoie l'identifiant de la réponse."""
    if account.get("simulated"):
        await asyncio.sleep(0.3)
        return f"demo-reply-{secrets.token_hex(4)}"
    cid, extra = item["external_id"], item.get("extra") or {}
    if platform == "facebook":
        return await meta.facebook_reply(account, cid, text, graph_version)
    if platform == "instagram":
        return await meta.instagram_reply(account, cid, text, graph_version)
    if platform == "threads":
        return await threads.reply(account, cid, text)
    if platform == "bluesky":
        return await bluesky.reply(account, extra, text)
    if platform == "youtube":
        return await youtube.reply(account, extra, cid, text)
    if platform == "x":
        return await x.reply(account, cid, text)
    raise PublishError(f"{LABELS.get(platform, platform)} ne permet pas de répondre depuis Tamtam")
