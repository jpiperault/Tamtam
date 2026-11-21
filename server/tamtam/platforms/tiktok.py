"""TikTok : Login Kit (OAuth 2.0) et Content Posting API (publication directe).

Vidéos : envoyées par morceaux (FILE_UPLOAD). Photos : TikTok vient les chercher à l'adresse publique (PULL_FROM_URL),
ce qui exige que le domaine de PUBLIC_URL soit vérifié dans le portail développeur TikTok.
Tant que l'application n'a pas passé l'audit TikTok, seule la visibilité « Moi uniquement » (SELF_ONLY) est permise.
"""
from __future__ import annotations

import asyncio
from urllib.parse import urlencode

from .base import Content, PublishError, Result, api_error, client

API = "https://open.tiktokapis.com/v2"
SCOPES = ["user.info.basic", "video.publish", "video.upload"]
MIN_CHUNK, MAX_CHUNK = 5 * 1024 * 1024, 64 * 1024 * 1024
CHUNK = 10 * 1024 * 1024


def authorize_url(client_key: str, redirect_uri: str, state: str) -> str:
    q = {"client_key": client_key, "scope": ",".join(SCOPES), "response_type": "code",
         "redirect_uri": redirect_uri, "state": state}
    return f"https://www.tiktok.com/v2/auth/authorize/?{urlencode(q)}"


def _check(r, network: str = "TikTok") -> dict:
    try:
        data = r.json()
    except ValueError:
        raise api_error(r, network)
    err = data.get("error")
    if r.status_code != 200 or (isinstance(err, dict) and err.get("code") not in (None, "ok")):
        if isinstance(err, dict) and err.get("code") in ("access_token_invalid", "scope_not_authorized"):
            from .base import AuthExpired
            raise AuthExpired(f"TikTok : autorisation expirée ou insuffisante, reconnectez le compte ({err.get('message', '')}).")
        if isinstance(err, dict) and err.get("code") == "rate_limit_exceeded":
            raise PublishError("TikTok : trop de requêtes, nouvel essai plus tard.", retry=True)
        if isinstance(err, dict) and err.get("message"):
            raise PublishError(f"TikTok : {err['message']} ({err.get('code')})")
        raise api_error(r, network)
    return data


async def _token(data: dict) -> dict:
    async with client() as c:
        r = await c.post(f"{API}/oauth/token/", data=data,
                         headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        d = r.json()
    except ValueError:
        raise api_error(r, "TikTok")
    if r.status_code != 200 or "access_token" not in d:
        raise PublishError(f"TikTok : {d.get('error_description') or d.get('error') or r.text[:200]}")
    return d


async def exchange(client_key: str, secret: str, redirect_uri: str, code: str) -> list[dict]:
    tok = await _token({"client_key": client_key, "client_secret": secret, "code": code,
                        "grant_type": "authorization_code", "redirect_uri": redirect_uri})
    async with client() as c:
        r = await c.get(f"{API}/user/info/", params={"fields": "open_id,display_name,avatar_url"},
                        headers={"Authorization": f"Bearer {tok['access_token']}"})
    u = _check(r)["data"]["user"]
    return [{"platform": "tiktok", "external_id": tok.get("open_id") or u.get("open_id"),
             "name": u.get("display_name", ""), "handle": u.get("display_name", ""),
             "avatar_url": u.get("avatar_url", ""), "access_token": tok["access_token"],
             "refresh_token": tok.get("refresh_token"), "expires_in": tok.get("expires_in"),
             "refresh_expires_in": tok.get("refresh_expires_in"), "meta": {}}]


async def refresh(client_key: str, secret: str, refresh_token: str) -> dict:
    tok = await _token({"client_key": client_key, "client_secret": secret, "grant_type": "refresh_token",
                        "refresh_token": refresh_token})
    return {"access_token": tok["access_token"], "refresh_token": tok.get("refresh_token", refresh_token),
            "expires_in": tok.get("expires_in"), "refresh_expires_in": tok.get("refresh_expires_in")}


async def creator_info(access_token: str) -> dict:
    async with client() as c:
        r = await c.post(f"{API}/post/publish/creator_info/query/", json={},
                         headers={"Authorization": f"Bearer {access_token}",
                                  "Content-Type": "application/json; charset=UTF-8"})
    return _check(r)["data"]


def _chunks(size: int) -> tuple[int, int]:
    if size <= MAX_CHUNK:
        return size, 1
    return CHUNK, size // CHUNK  # le dernier morceau absorbe le reste (jusqu'à 128 Mo permis)


async def publish(account: dict, content: Content) -> Result:
    token = account["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}
    info = await creator_info(token)
    options = info.get("privacy_level_options") or ["SELF_ONLY"]
    wanted = (account.get("meta") or {}).get("privacy") or "PUBLIC_TO_EVERYONE"
    privacy = wanted if wanted in options else ("SELF_ONLY" if "SELF_ONLY" in options else options[0])
    videos = [m for m in content.media if m.kind == "video"]
    images = [m for m in content.media if m.kind == "image"]
    async with client(300) as c:
        if videos:
            v = videos[0]
            chunk, count = _chunks(v.size)
            body = {"post_info": {"title": content.text[:2200], "privacy_level": privacy, "disable_comment": False,
                                  "disable_duet": False, "disable_stitch": False},
                    "source_info": {"source": "FILE_UPLOAD", "video_size": v.size, "chunk_size": chunk,
                                    "total_chunk_count": count}}
            d = _check(await c.post(f"{API}/post/publish/video/init/", headers=headers, json=body))["data"]
            publish_id, upload_url = d["publish_id"], d["upload_url"]
            with open(v.path, "rb") as f:
                for i in range(count):
                    start = i * chunk
                    length = v.size - start if i == count - 1 else chunk
                    f.seek(start)
                    data = f.read(length)
                    r = await c.put(upload_url, content=data, headers={
                        "Content-Type": v.mime, "Content-Length": str(len(data)),
                        "Content-Range": f"bytes {start}-{start + len(data) - 1}/{v.size}"})
                    if r.status_code not in (200, 201, 206):
                        raise PublishError(f"TikTok : envoi de la vidéo refusé (HTTP {r.status_code}).", retry=True)
        elif images:
            body = {"post_info": {"title": content.text[:90], "description": content.text[:4000],
                                  "privacy_level": privacy, "disable_comment": False, "auto_add_music": True},
                    "source_info": {"source": "PULL_FROM_URL", "photo_cover_index": 0,
                                    "photo_images": [m.url for m in images]},
                    "post_mode": "DIRECT_POST", "media_type": "PHOTO"}
            publish_id = _check(await c.post(f"{API}/post/publish/content/init/", headers=headers,
                                             json=body))["data"]["publish_id"]
        else:
            raise PublishError("TikTok : une vidéo ou des photos sont obligatoires.")
        waited = 0
        while True:
            d = _check(await c.post(f"{API}/post/publish/status/fetch/", headers=headers,
                                    json={"publish_id": publish_id}))["data"]
            st = d.get("status")
            if st == "PUBLISH_COMPLETE":
                ids = d.get("publicaly_available_post_id") or d.get("publicly_available_post_id") or []
                post_id = str(ids[0]) if ids else publish_id
                return Result(post_id, f"https://www.tiktok.com/@{account.get('handle')}/video/{post_id}"
                              if ids and account.get("handle") else "")
            if st == "FAILED":
                raise PublishError(f"TikTok : publication refusée ({d.get('fail_reason', 'raison inconnue')}).")
            if waited > 600:
                raise PublishError("TikTok : traitement trop long. Vérifiez le compte TikTok avant de réessayer.")
            await asyncio.sleep(5)
            waited += 5
