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


def authorize_url(client_id: str, redirect_uri: str, state: str, verifier: str | None, version: str,
                  extra: list[str] | None = None) -> str:
    q = {"client_id": client_id, "redirect_uri": redirect_uri, "state": state, "response_type": "code",
         "scope": ",".join(SCOPES + list(extra or []))}
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


# --- Statistiques

def _count(d: dict, edge: str) -> int | None:
    v = d.get(edge)
    if isinstance(v, dict):
        return (v.get("summary") or {}).get("total_count")
    return None


async def _get(c, url: str, params: dict, network: str) -> dict:
    r = await c.get(url, params=params)
    if r.status_code != 200:
        raise api_error(r, network)
    return r.json()


def _insights(d: dict) -> dict:
    out = {}
    for item in d.get("data", []):
        vals = item.get("values") or [{}]
        v = vals[-1].get("value") if vals else None
        if isinstance(v, dict):       # réactions par type : on additionne
            v = sum(x for x in v.values() if isinstance(x, (int, float)))
        if v is None:
            v = item.get("total_value", {}).get("value")
        out[item.get("name")] = v
    return out


async def facebook_metrics(account: dict, post_id: str, version: str) -> dict:
    """J'aime, commentaires, partages (permission déjà accordée) ; vues et portée si read_insights est accordé."""
    g, tok = _graph(version), account["access_token"]
    out = {"views": None, "reach": None, "likes": None, "comments": None, "shares": None, "saves": None}
    async with client(30) as c:
        try:
            d = await _get(c, f"{g}/{post_id}", {"access_token": tok, "fields":
                           "reactions.summary(total_count).limit(0),comments.summary(true).limit(0),shares"}, "Facebook")
            out["shares"] = (d.get("shares") or {}).get("count", 0)
        except PublishError:
            # vidéo : pas de champ « shares » sur l'objet vidéo
            d = await _get(c, f"{g}/{post_id}", {"access_token": tok, "fields":
                           "reactions.summary(total_count).limit(0),comments.summary(true).limit(0)"}, "Facebook")
        out["likes"], out["comments"] = _count(d, "reactions"), _count(d, "comments")
        try:
            ins = _insights(await _get(c, f"{g}/{post_id}/insights", {
                "access_token": tok, "metric": "post_media_view,post_total_media_view_unique"}, "Facebook"))
            out["views"], out["reach"] = ins.get("post_media_view"), ins.get("post_total_media_view_unique")
        except PublishError:
            pass   # read_insights non accordé, ou vidéo : on garde les chiffres d'engagement
    return out


async def instagram_metrics(account: dict, media_id: str, version: str) -> dict:
    """Vues, portée, J'aime, commentaires, partages, enregistrements (instagram_manage_insights) ; sinon J'aime et
    commentaires seulement."""
    g, tok = _graph(version), account["access_token"]
    async with client(30) as c:
        try:
            ins = _insights(await _get(c, f"{g}/{media_id}/insights", {
                "access_token": tok, "metric": "views,reach,likes,comments,shares,saved"}, "Instagram"))
            return {"views": ins.get("views"), "reach": ins.get("reach"), "likes": ins.get("likes"),
                    "comments": ins.get("comments"), "shares": ins.get("shares"), "saves": ins.get("saved")}
        except AuthExpired:
            raise
        except PublishError:
            d = await _get(c, f"{g}/{media_id}", {"access_token": tok, "fields": "like_count,comments_count"},
                           "Instagram")
            return {"views": None, "reach": None, "likes": d.get("like_count"), "comments": d.get("comments_count"),
                    "shares": None, "saves": None}


# --- Commentaires (boîte de réception)

async def facebook_comments(account: dict, post_id: str, version: str) -> list[dict]:
    """Commentaires d'un post de Page, tous niveaux (pages_read_user_content). L'auteur peut manquer : Facebook
    ne le donne que pour les personnes qui l'ont autorisé."""
    g, tok = _graph(version), account["access_token"]
    async with client(30) as c:
        d = await _get(c, f"{g}/{post_id}/comments", {
            "access_token": tok, "fields": "id,message,from{id,name},created_time", "filter": "stream",
            "limit": 100}, "Facebook")
    page = account["external_id"]
    return [{"id": x["id"], "text": x.get("message", ""), "author_name": (x.get("from") or {}).get("name", ""),
             "author_handle": "", "author_avatar": "", "created_at": x.get("created_time"),
             "own": (x.get("from") or {}).get("id") == page} for x in d.get("data", [])]


async def facebook_reply(account: dict, comment_id: str, text: str, version: str) -> str:
    async with client(30) as c:
        d = await _post(c, f"{_graph(version)}/{comment_id}/comments",
                        {"message": text, "access_token": account["access_token"]}, "Facebook")
    return d.get("id", "")


async def instagram_comments(account: dict, media_id: str, version: str) -> list[dict]:
    g, tok = _graph(version), account["access_token"]
    sub = "id,text,timestamp,username,from{id,username}"
    async with client(30) as c:
        d = await _get(c, f"{g}/{media_id}/comments", {
            "access_token": tok, "fields": f"{sub},replies{{{sub}}}", "limit": 50}, "Instagram")
    me = (account.get("handle") or "").lower()
    out = []

    def one(x):
        user = x.get("username") or (x.get("from") or {}).get("username", "")
        return {"id": x["id"], "text": x.get("text", ""), "author_name": user, "author_handle": user,
                "author_avatar": "", "created_at": x.get("timestamp"),
                "own": bool(me) and user.lower() == me or (x.get("from") or {}).get("id") == account["external_id"]}

    for x in d.get("data", []):
        out.append(one(x))
        out += [one(r) for r in (x.get("replies") or {}).get("data", [])]
    return out


async def instagram_reply(account: dict, comment_id: str, text: str, version: str) -> str:
    async with client(30) as c:
        d = await _post(c, f"{_graph(version)}/{comment_id}/replies",
                        {"message": text, "access_token": account["access_token"]}, "Instagram")
    return d.get("id", "")
