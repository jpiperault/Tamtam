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


def authorize_url(provider: str, client_id: str, redirect_uri: str, state: str, verifier: str,
                  graph_version: str) -> str:
    if provider == "meta":
        return meta.authorize_url(client_id, redirect_uri, state, None, graph_version)
    if provider == "x":
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        return x.authorize_url(client_id, redirect_uri, state, challenge)
    if provider == "tiktok":
        return tiktok.authorize_url(client_id, redirect_uri, state)
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
