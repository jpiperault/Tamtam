"""Threads (Meta) : connexion OAuth avec l'application Threads (identifiants distincts de l'app Facebook) et
publication par « conteneurs » (texte, image, vidéo ou carrousel), comme Instagram.

Jeton longue durée : 60 jours, renouvelé par Tamtam (vérification quotidienne des comptes) dès qu'il lui reste
moins de 7 jours. Les médias sont récupérés par Threads à l'adresse publique de Tamtam.
"""
from __future__ import annotations

import asyncio
from urllib.parse import urlencode

from .base import AuthExpired, Content, PublishError, Result, api_error, client

GRAPH = "https://graph.threads.com"
API = f"{GRAPH}/v1.0"
SCOPES = ["threads_basic", "threads_content_publish"]
STATS_SCOPES = ["threads_manage_insights"]


def authorize_url(client_id: str, redirect_uri: str, state: str, extra: list[str] | None = None) -> str:
    q = {"client_id": client_id, "redirect_uri": redirect_uri, "state": state, "response_type": "code",
         "scope": ",".join(SCOPES + list(extra or []))}
    return f"https://threads.com/oauth/authorize?{urlencode(q)}"


async def _json(r, what: str = "Threads") -> dict:
    if r.status_code != 200:
        raise api_error(r, what)
    return r.json()


async def exchange(client_id: str, secret: str, redirect_uri: str, code: str) -> list[dict]:
    async with client() as c:
        short = await _json(await c.post(f"{GRAPH}/oauth/access_token", data={
            "client_id": client_id, "client_secret": secret, "code": code, "grant_type": "authorization_code",
            "redirect_uri": redirect_uri}))
        long = await _json(await c.get(f"{GRAPH}/access_token", params={
            "grant_type": "th_exchange_token", "client_secret": secret, "access_token": short["access_token"]}))
        me = await _json(await c.get(f"{API}/me", params={
            "fields": "id,username,name,threads_profile_picture_url", "access_token": long["access_token"]}))
    return [{"platform": "threads", "external_id": str(me["id"]), "name": me.get("name") or me.get("username", ""),
             "handle": me.get("username", ""), "avatar_url": me.get("threads_profile_picture_url", ""),
             "access_token": long["access_token"], "refresh_token": long["access_token"],
             "expires_in": long.get("expires_in"), "meta": {}}]


async def refresh(token: str) -> dict:
    """Renouvelle le jeton longue durée (il doit avoir plus de 24 h et ne pas être expiré)."""
    async with client() as c:
        r = await c.get(f"{GRAPH}/refresh_access_token", params={"grant_type": "th_refresh_token",
                                                                 "access_token": token})
    d = await _json(r)
    return {"access_token": d["access_token"], "refresh_token": d["access_token"], "expires_in": d.get("expires_in")}


async def _create(c, uid: str, token: str, data: dict) -> str:
    r = await c.post(f"{API}/{uid}/threads", data={**data, "access_token": token})
    return (await _json(r))["id"]


async def _wait(c, cid: str, token: str, timeout_s: int = 300) -> None:
    waited = 0
    while True:
        d = await _json(await c.get(f"{API}/{cid}", params={"fields": "status,error_message", "access_token": token}))
        st = d.get("status")
        if st in ("FINISHED", "PUBLISHED"):
            return
        if st in ("ERROR", "EXPIRED"):
            raise PublishError(f"Threads : média refusé ({d.get('error_message') or st}).")
        if waited >= timeout_s:
            raise PublishError("Threads : traitement du média trop long. Vérifiez le compte avant de réessayer.")
        await asyncio.sleep(5)
        waited += 5


async def publish(account: dict, content: Content) -> Result:
    uid, token = account["external_id"], account["access_token"]
    text = content.text + (f"\n{content.link}" if content.link else "")
    media = content.media
    async with client(60) as c:
        if not media:
            cid = await _create(c, uid, token, {"media_type": "TEXT", "text": text})
        elif len(media) == 1:
            m = media[0]
            kind = {"media_type": "VIDEO", "video_url": m.url} if m.kind == "video" else \
                {"media_type": "IMAGE", "image_url": m.url}
            cid = await _create(c, uid, token, {**kind, "text": text})
            await _wait(c, cid, token)
        else:
            children = []
            for m in media[:20]:
                kind = {"media_type": "VIDEO", "video_url": m.url} if m.kind == "video" else \
                    {"media_type": "IMAGE", "image_url": m.url}
                children.append(await _create(c, uid, token, {**kind, "is_carousel_item": "true"}))
            for ch in children:
                await _wait(c, ch, token)
            cid = await _create(c, uid, token, {"media_type": "CAROUSEL", "children": ",".join(children), "text": text})
            await _wait(c, cid, token, 120)
        mid = (await _json(await c.post(f"{API}/{uid}/threads_publish",
                                        data={"creation_id": cid, "access_token": token})))["id"]
        url = ""
        r = await c.get(f"{API}/{mid}", params={"fields": "permalink", "access_token": token})
        if r.status_code == 200:
            url = r.json().get("permalink", "")
    return Result(str(mid), url)


async def check_token(account: dict) -> None:
    async with client() as c:
        r = await c.get(f"{API}/me", params={"fields": "id", "access_token": account["access_token"]})
    if r.status_code != 200:
        err = api_error(r, "Threads")
        raise AuthExpired(str(err)) if r.status_code in (400, 401) else err


async def metrics(account: dict, media_id: str) -> dict:
    async with client(30) as c:
        r = await c.get(f"{API}/{media_id}/insights", params={
            "metric": "views,likes,replies,reposts,quotes,shares", "access_token": account["access_token"]})
    if r.status_code != 200:
        err = api_error(r, "Threads")
        if isinstance(err, AuthExpired):
            raise err
        raise PublishError("Threads : lecture des statistiques refusée. Cochez la permission dans Administration → "
                           "Statistiques des réseaux puis reconnectez le compte")
    vals = {}
    for item in r.json().get("data", []):
        v = item.get("values") or []
        vals[item.get("name")] = v[-1].get("value") if v else (item.get("total_value") or {}).get("value")
    shares = None
    if vals.get("reposts") is not None or vals.get("quotes") is not None or vals.get("shares") is not None:
        shares = sum(vals.get(k) or 0 for k in ("reposts", "quotes", "shares"))
    return {"views": vals.get("views"), "reach": None, "likes": vals.get("likes"), "comments": vals.get("replies"),
            "shares": shares, "saves": None}


# --- Réponses (boîte de réception)

async def comments(account: dict, media_id: str) -> list[dict]:
    """Toutes les réponses sous le post (threads_read_replies)."""
    async with client(30) as c:
        d = await _json(await c.get(f"{API}/{media_id}/conversation", params={
            "fields": "id,text,username,timestamp,is_reply_owned_by_me,profile_picture_url", "reverse": "false",
            "access_token": account["access_token"]}))
    return [{"id": x["id"], "text": x.get("text", ""), "author_name": x.get("username", ""),
             "author_handle": x.get("username", ""), "author_avatar": x.get("profile_picture_url", ""),
             "created_at": x.get("timestamp"), "own": bool(x.get("is_reply_owned_by_me"))}
            for x in d.get("data", [])]


async def reply(account: dict, reply_to: str, text: str) -> str:
    """Réponse publiée sous un commentaire (threads_manage_replies)."""
    uid, token = account["external_id"], account["access_token"]
    async with client(60) as c:
        cid = await _create(c, uid, token, {"media_type": "TEXT", "text": text, "reply_to_id": reply_to})
        await _wait(c, cid, token, 120)
        d = await _json(await c.post(f"{API}/{uid}/threads_publish", data={"creation_id": cid, "access_token": token}))
    return str(d.get("id", ""))
