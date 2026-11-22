"""Point d'entrée unique vers les réseaux : connexion, renouvellement des jetons, publication.

En mode simulation (SIMULATION=true), les comptes « de démonstration » ne contactent aucun réseau.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import secrets

from . import meta, tiktok, x
from .base import (LABELS, PLATFORMS, PROVIDER_OF, RULES, AuthExpired, Content, MediaFile, PublishError, Result,
                   check, text_length)

PROVIDERS = ("meta", "x", "tiktok")
PROVIDER_LABELS = {"meta": "Meta (Facebook et Instagram)", "x": "X", "tiktok": "TikTok"}

__all__ = ["LABELS", "PLATFORMS", "PROVIDERS", "PROVIDER_OF", "RULES", "AuthExpired", "Content", "MediaFile",
           "PublishError", "Result", "check", "text_length"]


def pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return verifier, challenge


# Permissions de lecture des statistiques, demandées seulement si l'administrateur l'a choisi (Administration →
# Statistiques) : un réseau refuse toute la connexion si l'application développeur ne les a pas ajoutées.
STATS_SCOPES = {"meta": ["read_insights", "instagram_manage_insights"], "tiktok": ["video.list"]}


def authorize_url(provider: str, client_id: str, redirect_uri: str, state: str, verifier: str,
                  graph_version: str, stats: bool = False) -> str:
    extra = STATS_SCOPES.get(provider, []) if stats else []
    if provider == "meta":
        return meta.authorize_url(client_id, redirect_uri, state, None, graph_version, extra)
    if provider == "x":
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        return x.authorize_url(client_id, redirect_uri, state, challenge)
    if provider == "tiktok":
        return tiktok.authorize_url(client_id, redirect_uri, state, extra)
    raise ValueError(provider)


async def exchange(provider: str, client_id: str, secret: str | None, redirect_uri: str, code: str,
                   verifier: str | None, graph_version: str) -> list[dict]:
    if provider == "meta":
        return await meta.exchange(client_id, secret or "", redirect_uri, code, None, graph_version)
    if provider == "x":
        return await x.exchange(client_id, secret, redirect_uri, code, verifier or "")
    if provider == "tiktok":
        return await tiktok.exchange(client_id, secret or "", redirect_uri, code)
    raise ValueError(provider)


async def refresh(platform: str, client_id: str, secret: str | None, refresh_token: str) -> dict:
    if platform == "x":
        return await x.refresh(client_id, secret, refresh_token)
    if platform == "tiktok":
        return await tiktok.refresh(client_id, secret or "", refresh_token)
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
    raise PublishError(f"réseau inconnu : {platform}")
