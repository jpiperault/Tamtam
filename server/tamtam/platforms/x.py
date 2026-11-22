"""X : connexion OAuth 2.0 avec PKCE, envoi des médias par l'API v2, puis publication du post.

Le jeton d'accès dure 2 heures ; le jeton de renouvellement (offline.access) sert une seule fois et est remplacé
à chaque renouvellement.
"""
from __future__ import annotations

import asyncio
from urllib.parse import urlencode

import httpx

from .base import Content, PublishError, Result, api_error, client

API = "https://api.x.com/2"
SCOPES = ["tweet.read", "tweet.write", "users.read", "media.write", "offline.access"]
CHUNK = 4 * 1024 * 1024


def authorize_url(client_id: str, redirect_uri: str, state: str, challenge: str) -> str:
    q = {"response_type": "code", "client_id": client_id, "redirect_uri": redirect_uri, "scope": " ".join(SCOPES),
         "state": state, "code_challenge": challenge, "code_challenge_method": "S256"}
    return f"https://x.com/i/oauth2/authorize?{urlencode(q)}"


def _auth(client_id: str, secret: str | None):
    return httpx.BasicAuth(client_id, secret) if secret else None


async def _token(client_id: str, secret: str | None, data: dict) -> dict:
    if not secret:
        data = {**data, "client_id": client_id}
    async with client() as c:
        r = await c.post(f"{API}/oauth2/token", data=data, auth=_auth(client_id, secret))
    if r.status_code != 200:
        raise api_error(r, "X")
    return r.json()


async def exchange(client_id: str, secret: str | None, redirect_uri: str, code: str, verifier: str) -> list[dict]:
    tok = await _token(client_id, secret, {"grant_type": "authorization_code", "code": code,
                                           "redirect_uri": redirect_uri, "code_verifier": verifier})
    async with client() as c:
        r = await c.get(f"{API}/users/me", params={"user.fields": "profile_image_url"},
                        headers={"Authorization": f"Bearer {tok['access_token']}"})
    if r.status_code != 200:
        raise api_error(r, "X")
    u = r.json()["data"]
    return [{"platform": "x", "external_id": u["id"], "name": u.get("name", ""), "handle": u.get("username", ""),
             "avatar_url": u.get("profile_image_url", ""), "access_token": tok["access_token"],
             "refresh_token": tok.get("refresh_token"), "expires_in": tok.get("expires_in"), "meta": {}}]


async def refresh(client_id: str, secret: str | None, refresh_token: str) -> dict:
    tok = await _token(client_id, secret, {"grant_type": "refresh_token", "refresh_token": refresh_token})
    return {"access_token": tok["access_token"], "refresh_token": tok.get("refresh_token", refresh_token),
            "expires_in": tok.get("expires_in")}


async def _upload(c: httpx.AsyncClient, headers: dict, m) -> str:
    if m.kind == "image" and m.size <= 5 * 1024 * 1024:
        with open(m.path, "rb") as f:
            r = await c.post(f"{API}/media/upload", headers=headers,
                             files={"media": (m.path.name, f.read(), m.mime)},
                             data={"media_category": "tweet_image", "media_type": m.mime})
        if r.status_code not in (200, 201):
            raise api_error(r, "X")
        return r.json()["data"]["id"]
    category = "tweet_video" if m.kind == "video" else "tweet_image"
    r = await c.post(f"{API}/media/upload/initialize", headers=headers,
                     json={"media_type": m.mime, "total_bytes": m.size, "media_category": category})
    if r.status_code not in (200, 201, 202):
        raise api_error(r, "X")
    mid = r.json()["data"]["id"]
    with open(m.path, "rb") as f:
        index = 0
        while chunk := f.read(CHUNK):
            r = await c.post(f"{API}/media/upload/{mid}/append", headers=headers,
                             files={"media": ("chunk", chunk, "application/octet-stream")},
                             data={"segment_index": str(index)})
            if r.status_code not in (200, 201, 202, 204):
                raise api_error(r, "X")
            index += 1
    r = await c.post(f"{API}/media/upload/{mid}/finalize", headers=headers)
    if r.status_code not in (200, 201, 202):
        raise api_error(r, "X")
    info = r.json().get("data", {}).get("processing_info")
    waited = 0
    while info and info.get("state") in ("pending", "in_progress"):
        delay = int(info.get("check_after_secs") or 3)
        if waited > 300:
            raise PublishError("X : traitement de la vidéo trop long, nouvel essai plus tard.", retry=True)
        await asyncio.sleep(delay)
        waited += delay
        r = await c.get(f"{API}/media/upload", headers=headers, params={"command": "STATUS", "media_id": mid})
        if r.status_code != 200:
            raise api_error(r, "X")
        info = r.json().get("data", {}).get("processing_info")
    if info and info.get("state") == "failed":
        raise PublishError(f"X : la vidéo a été refusée ({info.get('error', {}).get('message', 'format non accepté')}).")
    return mid


async def publish(account: dict, content: Content) -> Result:
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    text = content.text + (f"\n{content.link}" if content.link else "")
    async with client(120) as c:
        ids = [await _upload(c, headers, m) for m in content.media]
        body: dict = {"text": text}
        if ids:
            body["media"] = {"media_ids": ids}
        r = await c.post(f"{API}/tweets", headers=headers, json=body)
    if r.status_code not in (200, 201):
        raise api_error(r, "X")
    tid = r.json()["data"]["id"]
    handle = account.get("handle") or "i"
    return Result(tid, f"https://x.com/{handle}/status/{tid}")


async def metrics(account: dict, tweet_id: str) -> dict:
    """Vues, J'aime, réponses, reposts (public_metrics). Lecture payante à l'usage chez X (quelques dixièmes de
    centime par post) : elle échoue si le compte développeur n'a pas de crédit."""
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    async with client(30) as c:
        r = await c.get(f"{API}/tweets", headers=headers, params={"ids": tweet_id, "tweet.fields": "public_metrics"})
    if r.status_code == 402 or (r.status_code == 403 and "credit" in r.text.lower()):
        raise PublishError("X : lecture des statistiques refusée (crédits API X épuisés ou absents)")
    if r.status_code != 200:
        raise api_error(r, "X")
    data = r.json().get("data") or []
    if not data:
        raise PublishError("X : post introuvable (supprimé ?)")
    m = data[0].get("public_metrics") or {}
    shares = None
    if "retweet_count" in m or "quote_count" in m:
        shares = (m.get("retweet_count") or 0) + (m.get("quote_count") or 0)
    return {"views": m.get("impression_count"), "reach": None, "likes": m.get("like_count"),
            "comments": m.get("reply_count"), "shares": shares, "saves": m.get("bookmark_count")}
