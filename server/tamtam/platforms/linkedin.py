"""LinkedIn : connexion OAuth (produits « Sign In with OpenID Connect » et « Share on LinkedIn ») et publication
avec l'API Posts (texte, images, une vidéo).

- Profil personnel : permission w_member_social, en libre-service.
- Pages d'entreprise (option dans Administration) : w_organization_social + r_organization_admin, réservées aux
  applications validées pour la « Community Management API ».
Le jeton dure 60 jours et LinkedIn ne donne pas de jeton de renouvellement aux applications ordinaires : il faut
reconnecter le compte avant l'échéance (Tamtam prévient 7 jours avant).
"""
from __future__ import annotations

import asyncio
import re
from urllib.parse import quote, urlencode

from .base import AuthExpired, Content, PublishError, Result, api_error, client, scope_list

AUTH = "https://www.linkedin.com/oauth/v2"
API = "https://api.linkedin.com"
VERSION = "202611"
SCOPES = ["openid", "profile", "w_member_social"]
PAGE_SCOPES = ["w_organization_social", "r_organization_admin"]
_ESCAPE = re.compile(r"([|{}@\[\]()<>#\\*_~])")
_URL = re.compile(r"https?://\S+")
_TAG = re.compile(r"(?<![\w#])#(\w[\w-]*)")


def authorize_url(client_id: str, redirect_uri: str, state: str, extra: list[str] | None = None) -> str:
    q = {"response_type": "code", "client_id": client_id, "redirect_uri": redirect_uri, "state": state,
         "scope": " ".join(SCOPES + list(extra or []))}
    return f"{AUTH}/authorization?{urlencode(q)}"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Linkedin-Version": VERSION, "X-Restli-Protocol-Version": "2.0.0"}


def commentary(text: str) -> str:
    """Texte au format « little text » de LinkedIn : caractères réservés échappés, sauf dans les adresses web ;
    les hashtags restent cliquables."""
    out, pos = [], 0
    for m in _URL.finditer(text):
        out.append(_escape_plain(text[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(_escape_plain(text[pos:]))
    return "".join(out)


def _escape_plain(t: str) -> str:
    parts, pos = [], 0
    for m in _TAG.finditer(t):
        parts.append(_ESCAPE.sub(r"\\\1", t[pos:m.start()]))
        parts.append("#" + m.group(1).replace("_", "\\_"))
        pos = m.end()
    parts.append(_ESCAPE.sub(r"\\\1", t[pos:]))
    return "".join(parts)


async def exchange(client_id: str, secret: str, redirect_uri: str, code: str) -> list[dict]:
    async with client() as c:
        r = await c.post(f"{AUTH}/accessToken", data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
            "client_id": client_id, "client_secret": secret})
        if r.status_code != 200:
            raise api_error(r, "LinkedIn")
        tok = r.json()
        token = tok["access_token"]
        r = await c.get(f"{API}/v2/userinfo", headers={"Authorization": f"Bearer {token}"})
        if r.status_code != 200:
            raise api_error(r, "LinkedIn")
        me = r.json()
        common = {"access_token": token, "scope": tok.get("scope"), "refresh_token": tok.get("refresh_token"),
                  "expires_in": tok.get("expires_in"), "refresh_expires_in": tok.get("refresh_token_expires_in")}
        out = [{"platform": "linkedin", "external_id": f"person:{me['sub']}", "name": me.get("name", ""),
                "handle": "", "avatar_url": me.get("picture", ""), "meta": {"author": f"urn:li:person:{me['sub']}", "scopes": scope_list(tok.get("scope")),
                                                                           "kind": "profil"}, **common}]
        if "r_organization_admin" in (tok.get("scope") or ""):
            out += await _pages(c, token, common)
    return out


async def _pages(c, token: str, common: dict) -> list[dict]:
    """Pages d'entreprise dont l'utilisateur est administrateur (si la permission a été accordée)."""
    r = await c.get(f"{API}/rest/organizationAcls", headers=_headers(token),
                    params={"q": "roleAssignee", "role": "ADMINISTRATOR", "state": "APPROVED"})
    if r.status_code != 200:
        return []
    out = []
    for el in r.json().get("elements", [])[:20]:
        urn = el.get("organization", "")
        oid = urn.rsplit(":", 1)[-1]
        if not oid.isdigit():
            continue
        name, vanity = f"Page {oid}", ""
        o = await c.get(f"{API}/rest/organizations/{oid}", headers=_headers(token))
        if o.status_code == 200:
            name, vanity = o.json().get("localizedName") or name, o.json().get("vanityName", "")
        out.append({"platform": "linkedin", "external_id": f"organization:{oid}", "name": name, "handle": vanity,
                    "avatar_url": "", "meta": {"author": urn, "kind": "page", "page_name": name,
                                               "scopes": scope_list(common.get("scope"))}, **common})
    return out


async def refresh(client_id: str, secret: str, refresh_token: str) -> dict:
    async with client() as c:
        r = await c.post(f"{AUTH}/accessToken", data={"grant_type": "refresh_token", "refresh_token": refresh_token,
                                                      "client_id": client_id, "client_secret": secret})
    if r.status_code != 200:
        raise api_error(r, "LinkedIn")
    t = r.json()
    return {"access_token": t["access_token"], "refresh_token": t.get("refresh_token", refresh_token),
            "expires_in": t.get("expires_in"), "refresh_expires_in": t.get("refresh_token_expires_in")}


async def _check(r, ok=(200, 201)) -> None:
    if r.status_code not in ok:
        raise api_error(r, "LinkedIn")


async def _image(c, token: str, owner: str, m) -> str:
    r = await c.post(f"{API}/rest/images?action=initializeUpload", headers=_headers(token),
                     json={"initializeUploadRequest": {"owner": owner}})
    await _check(r)
    v = r.json()["value"]
    up = await c.put(v["uploadUrl"], content=m.path.read_bytes(), headers={"Authorization": f"Bearer {token}"})
    await _check(up)
    return v["image"]


async def _video(c, token: str, owner: str, m) -> str:
    r = await c.post(f"{API}/rest/videos?action=initializeUpload", headers=_headers(token),
                     json={"initializeUploadRequest": {"owner": owner, "fileSizeBytes": m.size,
                                                       "uploadCaptions": False, "uploadThumbnail": False}})
    await _check(r)
    v = r.json()["value"]
    etags = []
    with open(m.path, "rb") as f:
        for part in v["uploadInstructions"]:
            f.seek(part["firstByte"])
            data = f.read(part["lastByte"] - part["firstByte"] + 1)
            up = await c.put(part["uploadUrl"], content=data, headers={"Content-Type": "application/octet-stream"})
            await _check(up)
            etags.append(up.headers.get("etag", "").strip('"') or up.headers.get("ETag", ""))
    r = await c.post(f"{API}/rest/videos?action=finalizeUpload", headers=_headers(token),
                     json={"finalizeUploadRequest": {"video": v["video"], "uploadToken": v.get("uploadToken", ""),
                                                     "uploadedPartIds": etags}})
    await _check(r)
    waited = 0
    while True:
        s = await c.get(f"{API}/rest/videos/{quote(v['video'], safe='')}", headers=_headers(token))
        await _check(s)
        st = s.json().get("status")
        if st == "AVAILABLE":
            return v["video"]
        if st == "PROCESSING_FAILED":
            raise PublishError("LinkedIn : la vidéo a été refusée pendant son traitement.")
        if waited > 600:
            raise PublishError("LinkedIn : traitement de la vidéo trop long. Vérifiez le compte avant de réessayer.")
        await asyncio.sleep(5)
        waited += 5


async def publish(account: dict, content: Content) -> Result:
    token = account["access_token"]
    author = (account.get("meta") or {}).get("author") or f"urn:li:{account['external_id']}"
    text = content.text + (f"\n{content.link}" if content.link else "")
    body: dict = {"author": author, "commentary": commentary(text), "visibility": "PUBLIC",
                  "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [],
                                   "thirdPartyDistributionChannels": []},
                  "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False}
    async with client(180) as c:
        images = [m for m in content.media if m.kind == "image"]
        videos = [m for m in content.media if m.kind == "video"]
        if videos:
            body["content"] = {"media": {"id": await _video(c, token, author, videos[0])}}
        elif len(images) == 1:
            body["content"] = {"media": {"id": await _image(c, token, author, images[0])}}
        elif images:
            ids = [await _image(c, token, author, m) for m in images[:20]]
            body["content"] = {"multiImage": {"images": [{"id": i} for i in ids]}}
        r = await c.post(f"{API}/rest/posts", headers=_headers(token), json=body)
    await _check(r)
    urn = r.headers.get("x-restli-id", "")
    return Result(urn, f"https://www.linkedin.com/feed/update/{urn}/" if urn else "")


async def check_token(account: dict) -> None:
    async with client() as c:
        r = await c.get(f"{API}/v2/userinfo", headers={"Authorization": f"Bearer {account['access_token']}"})
    if r.status_code != 200:
        err = api_error(r, "LinkedIn")
        raise AuthExpired(str(err)) if r.status_code in (401, 403) else err


async def metrics(account: dict, urn: str) -> dict:
    raise PublishError("LinkedIn ne fournit les statistiques des posts qu'aux applications validées pour la "
                       "Community Management API : consultez-les sur LinkedIn")
