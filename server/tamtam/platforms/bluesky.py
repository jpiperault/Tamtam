"""Bluesky (AT Protocol) : connexion avec le pseudo et un « mot de passe d'application », puis publication.

Pas d'application développeur à créer : l'utilisateur crée un mot de passe d'application dans Bluesky
(Réglages → Confidentialité et sécurité → Mots de passe d'application) et le saisit une fois dans Tamtam. Tamtam ne
garde pas ce mot de passe : seulement les jetons de session (chiffrés), renouvelés automatiquement.
"""
from __future__ import annotations

import base64
import io
import json
import re
from datetime import datetime, timezone

from .base import AuthExpired, Content, PublishError, Result, api_error, client

DEFAULT_PDS = "https://bsky.social"
APPVIEW = "https://public.api.bsky.app"
VIDEO = "https://video.bsky.app"
IMAGE_MAX_BYTES = 950_000          # limite Bluesky : environ 1 Mo par image
URL_RE = re.compile(r"https?://[^\s<>\"']+[^\s<>\"'.,;:!?)\]]")
TAG_RE = re.compile(r"(?:^|\s)(#[^\d\s#][^\s#]*)")


def _exp_seconds(jwt: str) -> int | None:
    """Durée de validité restante d'un jeton JWT (lecture du champ exp, sans vérification)."""
    try:
        payload = jwt.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        exp = json.loads(base64.urlsafe_b64decode(payload))["exp"]
        return max(60, int(exp - datetime.now(timezone.utc).timestamp()))
    except (IndexError, KeyError, ValueError):
        return None


def _pds_of(session: dict) -> str:
    for s in (session.get("didDoc") or {}).get("service", []):
        if s.get("id", "").endswith("#atproto_pds") and s.get("serviceEndpoint"):
            return s["serviceEndpoint"].rstrip("/")
    return DEFAULT_PDS


def _check(r, what: str = "Bluesky") -> dict:
    if r.status_code == 200:
        return r.json()
    try:
        d = r.json()
    except ValueError:
        d = {}
    err, msg = d.get("error", ""), d.get("message", "")
    if err in ("ExpiredToken", "InvalidToken") or r.status_code == 401:
        raise AuthExpired(f"{what} : session expirée, reconnectez le compte ({msg or err}).")
    if err == "AuthFactorTokenRequired":
        raise PublishError(f"{what} : ce compte demande un code reçu par e-mail ; utilisez un mot de passe "
                           "d'application (Réglages → Confidentialité et sécurité → Mots de passe d'application).")
    if r.status_code == 429:
        raise PublishError(f"{what} : trop de requêtes, nouvel essai plus tard.", retry=True)
    if r.status_code >= 500:
        raise PublishError(f"{what} : le service ne répond pas correctement ({msg or r.status_code}).", retry=True)
    if msg or err:
        raise PublishError(f"{what} : {msg or err}")
    raise api_error(r, what)


async def login(identifier: str, app_password: str) -> dict:
    """Ouvre une session ; renvoie le compte à rattacher (format des candidats de connexion)."""
    ident = identifier.strip().lstrip("@")
    async with client() as c:
        r = await c.post(f"{DEFAULT_PDS}/xrpc/com.atproto.server.createSession",
                         json={"identifier": ident, "password": app_password.strip()})
        if r.status_code == 401:
            raise PublishError("Bluesky : pseudo ou mot de passe d'application incorrect.")
        s = _check(r)
        pds = _pds_of(s)
        if pds != DEFAULT_PDS:   # compte hébergé ailleurs : on rouvre la session sur son propre serveur
            s = _check(await c.post(f"{pds}/xrpc/com.atproto.server.createSession",
                                    json={"identifier": ident, "password": app_password.strip()}))
        prof = {}
        r = await c.get(f"{APPVIEW}/xrpc/app.bsky.actor.getProfile", params={"actor": s["did"]})
        if r.status_code == 200:
            prof = r.json()
    return {"platform": "bluesky", "external_id": s["did"], "name": prof.get("displayName") or s.get("handle", ""),
            "handle": s.get("handle", ""), "avatar_url": prof.get("avatar", ""), "access_token": s["accessJwt"],
            "refresh_token": s["refreshJwt"], "expires_in": _exp_seconds(s["accessJwt"]),
            "refresh_expires_in": _exp_seconds(s["refreshJwt"]), "meta": {"pds": pds}}


async def refresh(refresh_token: str, meta: dict | None = None) -> dict:
    pds = (meta or {}).get("pds") or DEFAULT_PDS
    async with client() as c:
        r = await c.post(f"{pds}/xrpc/com.atproto.server.refreshSession",
                         headers={"Authorization": f"Bearer {refresh_token}"})
    s = _check(r)
    return {"access_token": s["accessJwt"], "refresh_token": s["refreshJwt"],
            "expires_in": _exp_seconds(s["accessJwt"]), "refresh_expires_in": _exp_seconds(s["refreshJwt"])}


def facets(text: str) -> list[dict]:
    """Liens et hashtags rendus cliquables (positions en octets UTF-8, comme l'exige Bluesky)."""
    out = []

    def span(start: int, end: int) -> dict:
        return {"byteStart": len(text[:start].encode()), "byteEnd": len(text[:end].encode())}

    for m in URL_RE.finditer(text):
        out.append({"index": span(m.start(), m.end()),
                    "features": [{"$type": "app.bsky.richtext.facet#link", "uri": m.group(0)}]})
    for m in TAG_RE.finditer(text):
        tag = m.group(1)
        start = m.start(1)
        if len(tag) > 1 and not any(f["index"]["byteStart"] <= len(text[:start].encode()) < f["index"]["byteEnd"]
                                    for f in out):
            out.append({"index": span(start, start + len(tag)),
                        "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": tag[1:][:64]}]})
    return out


def _shrink(path) -> tuple[bytes, int, int]:
    """Image JPEG sous la limite de taille de Bluesky (réduite si besoin)."""
    from PIL import Image

    with Image.open(path) as im:
        im = im.convert("RGB")
        w, h = im.size
        data = path.read_bytes()
        quality, side = 85, max(w, h)
        while len(data) > IMAGE_MAX_BYTES:
            side = int(side * 0.85)
            cur = im.copy()
            cur.thumbnail((side, side))
            buf = io.BytesIO()
            cur.save(buf, "JPEG", quality=quality, optimize=True)
            data, (w, h) = buf.getvalue(), cur.size
            quality = max(70, quality - 5)
    return data, w, h


async def publish(account: dict, content: Content) -> Result:
    pds = (account.get("meta") or {}).get("pds") or DEFAULT_PDS
    did = account["external_id"]
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    text = content.text + (f"\n{content.link}" if content.link else "")
    record: dict = {"$type": "app.bsky.feed.post", "text": text,
                    "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    f = facets(text)
    if f:
        record["facets"] = f
    async with client(180) as c:
        images = [m for m in content.media if m.kind == "image"]
        videos = [m for m in content.media if m.kind == "video"]
        if images:
            items = []
            for m in images[:4]:
                data, w, h = _shrink(m.path)
                blob = _check(await c.post(f"{pds}/xrpc/com.atproto.repo.uploadBlob", content=data,
                                           headers={**headers, "Content-Type": "image/jpeg"}))["blob"]
                items.append({"image": blob, "alt": "", "aspectRatio": {"width": w, "height": h}})
            record["embed"] = {"$type": "app.bsky.embed.images", "images": items}
        elif videos:
            record["embed"] = await _video_embed(c, pds, did, headers, videos[0])
        r = await c.post(f"{pds}/xrpc/com.atproto.repo.createRecord", headers=headers,
                         json={"repo": did, "collection": "app.bsky.feed.post", "record": record})
    d = _check(r)
    uri = d["uri"]
    rkey = uri.rsplit("/", 1)[-1]
    return Result(uri, f"https://bsky.app/profile/{account.get('handle') or did}/post/{rkey}")


async def _video_embed(c, pds: str, did: str, headers: dict, m) -> dict:
    """Vidéo : envoi au service vidéo de Bluesky (avec un jeton de service), puis attente du traitement."""
    import asyncio
    from urllib.parse import urlsplit

    if m.mime != "video/mp4":
        raise PublishError("Bluesky : seules les vidéos MP4 sont acceptées.")
    if m.duration_s and m.duration_s > 180:
        raise PublishError(f"Bluesky : la vidéo dure {round(m.duration_s)} s, 3 minutes au plus.")
    host = urlsplit(pds).hostname
    exp = int(datetime.now(timezone.utc).timestamp()) + 1800
    svc = _check(await c.get(f"{pds}/xrpc/com.atproto.server.getServiceAuth", headers=headers,
                             params={"aud": f"did:web:{host}", "lxm": "com.atproto.repo.uploadBlob", "exp": exp}))
    vh = {"Authorization": f"Bearer {svc['token']}"}
    lim = await c.get(f"{VIDEO}/xrpc/app.bsky.video.getUploadLimits", headers=vh)
    if lim.status_code == 200 and lim.json().get("canUpload") is False:
        raise PublishError(f"Bluesky : envoi de vidéo impossible pour ce compte "
                           f"({lim.json().get('message') or 'limite du jour atteinte ou e-mail non vérifié'}).")
    r = await c.post(f"{VIDEO}/xrpc/app.bsky.video.uploadVideo", params={"did": did, "name": m.path.name},
                     content=m.path.read_bytes(), headers={**vh, "Content-Type": "video/mp4"})
    d = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    job = d.get("jobStatus") or d
    if r.status_code != 200 and job.get("error") != "already_exists" and not job.get("jobId"):
        _check(r)
    waited = 0
    while not job.get("blob"):
        if job.get("state") == "JOB_STATE_FAILED":
            raise PublishError(f"Bluesky : vidéo refusée ({job.get('error') or job.get('message') or 'traitement'}).")
        if waited > 600:
            raise PublishError("Bluesky : traitement de la vidéo trop long. Vérifiez le compte avant de réessayer.")
        await asyncio.sleep(4)
        waited += 4
        s = await c.get(f"{VIDEO}/xrpc/app.bsky.video.getJobStatus", params={"jobId": job["jobId"]}, headers=vh)
        job = _check(s).get("jobStatus") or {}
    return {"$type": "app.bsky.embed.video", "video": job["blob"]}


async def metrics(account: dict, uri: str) -> dict:
    async with client(30) as c:
        r = await c.get(f"{APPVIEW}/xrpc/app.bsky.feed.getPosts", params={"uris": uri})
    posts = _check(r).get("posts") or []
    if not posts:
        raise PublishError("Bluesky : post introuvable (supprimé ?)")
    p = posts[0]
    return {"views": None, "reach": None, "likes": p.get("likeCount"), "comments": p.get("replyCount"),
            "shares": (p.get("repostCount") or 0) + (p.get("quoteCount") or 0), "saves": p.get("bookmarkCount")}


async def metrics_ready(account: dict) -> None:
    """Vérification du compte : la session est-elle encore acceptée ?"""
    pds = (account.get("meta") or {}).get("pds") or DEFAULT_PDS
    async with client() as c:
        r = await c.get(f"{pds}/xrpc/com.atproto.server.getSession",
                        headers={"Authorization": f"Bearer {account['access_token']}"})
    _check(r)
