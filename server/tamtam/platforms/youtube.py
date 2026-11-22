"""YouTube (Shorts) : connexion OAuth Google et envoi de la vidéo par l'API YouTube Data v3 (envoi reprenable).

Un Short est une vidéo verticale ou carrée de 3 minutes au plus. Titre : réglage du post, ou première ligne du texte
(100 caractères au plus) ; description : le reste du texte et le lien. Quota Google : 100 envois par jour et par
projet Google Cloud.
"""
from __future__ import annotations

import json
from urllib.parse import urlencode

from .base import AuthExpired, Content, PublishError, Result, api_error, client

AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]
CHUNK = 8 * 1024 * 1024   # multiple de 256 Kio, comme l'exige Google
PRIVACY = ("public", "unlisted", "private")


def authorize_url(client_id: str, redirect_uri: str, state: str) -> str:
    q = {"client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code", "scope": " ".join(SCOPES),
         "state": state, "access_type": "offline", "prompt": "consent", "include_granted_scopes": "true"}
    return f"{AUTH}?{urlencode(q)}"


async def _token(data: dict) -> dict:
    async with client() as c:
        r = await c.post(TOKEN, data=data)
    if r.status_code != 200:
        try:
            err = r.json()
        except ValueError:
            err = {}
        if err.get("error") == "invalid_grant":
            raise AuthExpired("YouTube : autorisation retirée ou expirée, reconnectez le compte.")
        raise api_error(r, "YouTube")
    return r.json()


async def exchange(client_id: str, secret: str, redirect_uri: str, code: str) -> list[dict]:
    tok = await _token({"code": code, "client_id": client_id, "client_secret": secret, "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code"})
    async with client() as c:
        r = await c.get(f"{API}/channels", params={"part": "snippet", "mine": "true"},
                        headers={"Authorization": f"Bearer {tok['access_token']}"})
    if r.status_code != 200:
        raise api_error(r, "YouTube")
    out = []
    for ch in r.json().get("items", []):
        sn = ch.get("snippet", {})
        thumb = (sn.get("thumbnails", {}).get("default") or {}).get("url", "")
        out.append({"platform": "youtube", "external_id": ch["id"], "name": sn.get("title", ""),
                    "handle": (sn.get("customUrl") or "").lstrip("@"), "avatar_url": thumb,
                    "access_token": tok["access_token"], "refresh_token": tok.get("refresh_token"),
                    "expires_in": tok.get("expires_in"), "meta": {}})
    if not out:
        raise PublishError("YouTube : ce compte Google n'a pas de chaîne YouTube. Créez-la sur youtube.com.")
    return out


async def refresh(client_id: str, secret: str, refresh_token: str) -> dict:
    t = await _token({"client_id": client_id, "client_secret": secret, "refresh_token": refresh_token,
                      "grant_type": "refresh_token"})
    return {"access_token": t["access_token"], "refresh_token": t.get("refresh_token", refresh_token),
            "expires_in": t.get("expires_in")}


def metadata(text: str, link: str, options: dict) -> dict:
    lines = text.strip().splitlines()
    first = lines[0].strip() if lines else ""
    title = (options.get("title") or "").strip() or first or "Nouvelle vidéo"
    title = title.replace("<", "").replace(">", "")[:100]
    rest = "\n".join(lines[1:]).strip() if not (options.get("title") or "").strip() else text.strip()
    desc = (rest + (f"\n\n{link}" if link else "")).replace("<", "").replace(">", "").strip()
    while len(desc.encode()) > 5000:
        desc = desc[:-50]
    privacy = options.get("privacy") if options.get("privacy") in PRIVACY else "public"
    return {"snippet": {"title": title, "description": desc, "categoryId": "22"},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": bool(options.get("made_for_kids"))}}


async def publish(account: dict, content: Content) -> Result:
    videos = [m for m in content.media if m.kind == "video"]
    if not videos:
        raise PublishError("YouTube : une vidéo est obligatoire.")
    m = videos[0]
    if m.duration_s and m.duration_s > 180:
        raise PublishError(f"YouTube : la vidéo dure {round(m.duration_s)} s ; un Short dure 3 minutes au plus.")
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    meta = metadata(content.text, content.link, content.options)
    async with client(300) as c:
        r = await c.post(UPLOAD, params={"uploadType": "resumable", "part": "snippet,status"},
                         headers={**headers, "Content-Type": "application/json; charset=UTF-8",
                                  "X-Upload-Content-Length": str(m.size), "X-Upload-Content-Type": m.mime},
                         content=json.dumps(meta))
        if r.status_code != 200:
            _quota(r)
            raise api_error(r, "YouTube")
        session = r.headers["Location"]
        sent, done = 0, None
        with open(m.path, "rb") as f:
            while sent < m.size:
                data = f.read(CHUNK)
                end = sent + len(data) - 1
                up = await c.put(session, content=data, headers={
                    **headers, "Content-Length": str(len(data)), "Content-Range": f"bytes {sent}-{end}/{m.size}"})
                if up.status_code in (200, 201):
                    done = up.json()
                    break
                if up.status_code != 308:
                    _quota(up)
                    raise api_error(up, "YouTube")
                rng = up.headers.get("Range", "")
                sent = int(rng.rsplit("-", 1)[-1]) + 1 if rng else 0
                f.seek(sent)
    if not done:
        raise PublishError("YouTube : envoi interrompu. Vérifiez la chaîne avant de réessayer.")
    vid = done["id"]
    return Result(vid, f"https://www.youtube.com/shorts/{vid}")


def _quota(r) -> None:
    if r.status_code == 403 and "quota" in r.text.lower():
        raise PublishError("YouTube : quota d'envois du jour atteint pour votre projet Google (100 vidéos par jour). "
                           "Réessayez demain (bouton Réessayer).")


async def check_token(account: dict) -> None:
    async with client() as c:
        r = await c.get(f"{API}/channels", params={"part": "id", "mine": "true"},
                        headers={"Authorization": f"Bearer {account['access_token']}"})
    if r.status_code != 200:
        err = api_error(r, "YouTube")
        raise AuthExpired(str(err)) if r.status_code == 401 else err


async def metrics(account: dict, video_id: str) -> dict:
    async with client(30) as c:
        r = await c.get(f"{API}/videos", params={"part": "statistics", "id": video_id},
                        headers={"Authorization": f"Bearer {account['access_token']}"})
    if r.status_code != 200:
        raise api_error(r, "YouTube")
    items = r.json().get("items") or []
    if not items:
        raise PublishError("YouTube : vidéo introuvable (supprimée ?)")
    s = items[0].get("statistics", {})
    num = lambda k: int(s[k]) if k in s else None  # noqa: E731
    return {"views": num("viewCount"), "reach": None, "likes": num("likeCount"), "comments": num("commentCount"),
            "shares": None, "saves": None}
