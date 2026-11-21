"""Meta : Pages Facebook et comptes Instagram Professionnels (API Graph).

Une seule application Meta et une seule connexion couvrent Facebook et Instagram : au retour, on liste les Pages
gérées par la personne et le compte Instagram Professionnel relié à chacune. Les jetons de Page obtenus à partir
d'un jeton utilisateur longue durée n'expirent pas (tant que la personne garde ses droits sur la Page).
"""
from __future__ import annotations

import asyncio
from urllib.parse import urlencode

from .base import AuthExpired, Content, PublishError, Result, api_error, client

SCOPES = ["pages_show_list", "pages_read_engagement", "pages_manage_posts", "business_management",
          "instagram_basic", "instagram_content_publish"]


def _graph(version: str) -> str:
    return f"https://graph.facebook.com/{version}"


def authorize_url(client_id: str, redirect_uri: str, state: str, verifier: str | None, version: str) -> str:
    q = {"client_id": client_id, "redirect_uri": redirect_uri, "state": state, "response_type": "code",
         "scope": ",".join(SCOPES)}
    return f"https://www.facebook.com/{version}/dialog/oauth?{urlencode(q)}"


async def exchange(client_id: str, secret: str, redirect_uri: str, code: str, verifier: str | None,
                   version: str) -> list[dict]:
    g = _graph(version)
    async with client() as c:
        r = await c.get(f"{g}/oauth/access_token", params={"client_id": client_id, "client_secret": secret,
                                                          "redirect_uri": redirect_uri, "code": code})
        if r.status_code != 200:
            raise api_error(r, "Meta")
        short = r.json()["access_token"]
        r = await c.get(f"{g}/oauth/access_token", params={"grant_type": "fb_exchange_token", "client_id": client_id,
                                                          "client_secret": secret, "fb_exchange_token": short})
        if r.status_code != 200:
            raise api_error(r, "Meta")
        user_token = r.json()["access_token"]
        fields = "id,name,access_token,picture{url},instagram_business_account{id,username,name,profile_picture_url}"
        pages, url, params = [], f"{g}/me/accounts", {"fields": fields, "limit": 100, "access_token": user_token}
        while url and len(pages) < 500:
            r = await c.get(url, params=params)
            if r.status_code != 200:
                raise api_error(r, "Meta")
            data = r.json()
            pages += data.get("data", [])
            url, params = data.get("paging", {}).get("next"), None
    out = []
    for p in pages:
        token = p.get("access_token")
        if not token:
            continue
        out.append({"platform": "facebook", "external_id": p["id"], "name": p.get("name", ""), "handle": "",
                    "avatar_url": (p.get("picture") or {}).get("data", {}).get("url", ""),
                    "access_token": token, "meta": {"page_id": p["id"]}})
        ig = p.get("instagram_business_account")
        if ig and ig.get("id"):
            out.append({"platform": "instagram", "external_id": ig["id"], "name": ig.get("name") or ig.get("username", ""),
                        "handle": ig.get("username", ""), "avatar_url": ig.get("profile_picture_url", ""),
                        "access_token": token, "meta": {"page_id": p["id"], "page_name": p.get("name", "")}})
    return out


async def _post(c, url: str, data: dict, network: str) -> dict:
    r = await c.post(url, data=data)
    if r.status_code != 200:
        raise api_error(r, network)
    return r.json()


# --- Facebook

async def publish_facebook(account: dict, content: Content, version: str) -> Result:
    g = _graph(version)
    page, token = account["external_id"], account["access_token"]
    images = [m for m in content.media if m.kind == "image"]
    videos = [m for m in content.media if m.kind == "video"]
    async with client(120) as c:
        if videos:
            text = content.text + (f"\n{content.link}" if content.link else "")
            d = await _post(c, f"{g}/{page}/videos", {"file_url": videos[0].url, "description": text,
                                                     "access_token": token}, "Facebook")
            vid = d["id"]
            return Result(vid, f"https://www.facebook.com/{page}/videos/{vid}")
        if len(images) == 1:
            text = content.text + (f"\n{content.link}" if content.link else "")
            d = await _post(c, f"{g}/{page}/photos", {"url": images[0].url, "caption": text,
                                                     "access_token": token}, "Facebook")
            pid = d.get("post_id") or d["id"]
            return Result(pid, f"https://www.facebook.com/{pid}")
        data = {"message": content.text, "access_token": token}
        if images:
            ids = []
            for m in images:
                d = await _post(c, f"{g}/{page}/photos", {"url": m.url, "published": "false",
                                                         "access_token": token}, "Facebook")
                ids.append(d["id"])
            for i, mid in enumerate(ids):
                data[f"attached_media[{i}]"] = '{"media_fbid":"%s"}' % mid
            if content.link:
                data["message"] += f"\n{content.link}"
        elif content.link:
            data["link"] = content.link
        d = await _post(c, f"{g}/{page}/feed", data, "Facebook")
        return Result(d["id"], f"https://www.facebook.com/{d['id']}")


# --- Instagram

async def _wait_container(c, g: str, cid: str, token: str, timeout_s: int = 300) -> None:
    """Les vidéos sont traitées par Instagram avant publication : on attend FINISHED."""
    waited = 0
    while True:
        r = await c.get(f"{g}/{cid}", params={"fields": "status_code,status", "access_token": token})
        if r.status_code != 200:
            raise api_error(r, "Instagram")
        st = r.json().get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise PublishError(f"Instagram : le média a été refusé pendant son traitement ({r.json().get('status', st)}).")
        if waited >= timeout_s:
            raise PublishError("Instagram : traitement de la vidéo trop long, nouvel essai plus tard.", retry=True)
        await asyncio.sleep(5)
        waited += 5


async def publish_instagram(account: dict, content: Content, version: str) -> Result:
    g = _graph(version)
    ig, token = account["external_id"], account["access_token"]
    if not content.media:
        raise PublishError("Instagram : une image ou une vidéo est obligatoire.")
    async with client(120) as c:
        if len(content.media) == 1:
            m = content.media[0]
            data = {"caption": content.text, "access_token": token}
            if m.kind == "video":
                data.update(media_type="REELS", video_url=m.url)
            else:
                data["image_url"] = m.url
            cid = (await _post(c, f"{g}/{ig}/media", data, "Instagram"))["id"]
            if m.kind == "video":
                await _wait_container(c, g, cid, token)
        else:
            children = []
            for m in content.media:
                data = {"is_carousel_item": "true", "access_token": token}
                if m.kind == "video":
                    data.update(media_type="VIDEO", video_url=m.url)
                else:
                    data["image_url"] = m.url
                child = (await _post(c, f"{g}/{ig}/media", data, "Instagram"))["id"]
                if m.kind == "video":
                    await _wait_container(c, g, child, token)
                children.append(child)
            cid = (await _post(c, f"{g}/{ig}/media", {"media_type": "CAROUSEL", "children": ",".join(children),
                                                       "caption": content.text, "access_token": token},
                               "Instagram"))["id"]
            await _wait_container(c, g, cid, token, timeout_s=60)
        mid = (await _post(c, f"{g}/{ig}/media_publish", {"creation_id": cid, "access_token": token},
                           "Instagram"))["id"]
        url = ""
        r = await c.get(f"{g}/{mid}", params={"fields": "permalink", "access_token": token})
        if r.status_code == 200:
            url = r.json().get("permalink", "")
        return Result(mid, url)


async def check_token(account: dict, version: str) -> None:
    async with client() as c:
        r = await c.get(f"{_graph(version)}/me", params={"access_token": account["access_token"]})
    if r.status_code != 200:
        err = api_error(r, "Meta")
        raise AuthExpired(str(err)) if r.status_code in (400, 401) else err
