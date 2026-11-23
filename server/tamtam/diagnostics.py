"""État des connexions : tout ce qui doit être en place pour publier en vrai, vérifié en un clic.

- Adresse publique : en HTTPS et joignable (Meta, Instagram, Threads et TikTok viennent y chercher les médias).
- Applications des réseaux : identifiants saisis.
- Chaque compte : autorisation encore acceptée par le réseau, date d'expiration, permissions accordées comparées à
  celles dont Tamtam a besoin avec les options choisies (statistiques, boîte de réception, Pages LinkedIn).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from . import log, platforms
from .platforms import AuthExpired, PublishError
from .platforms.base import client

_log = log.get("diagnostics")
YT = "https://www.googleapis.com/auth/"

# Permissions indispensables pour publier.
BASE_SCOPES = {
    "facebook": ["pages_manage_posts", "pages_read_engagement"],
    "instagram": ["instagram_basic", "instagram_content_publish"],
    "x": ["tweet.read", "tweet.write", "users.read", "media.write", "offline.access"],
    "tiktok": ["user.info.basic", "video.publish", "video.upload"],
    "threads": ["threads_basic", "threads_content_publish"],
    "linkedin": ["w_member_social"],
    "youtube": [YT + "youtube.upload"],
    "bluesky": [],
}
# Permissions en plus, selon les options cochées dans Administration.
OPTION_SCOPES = {
    ("facebook", "stats_scopes_meta"): ["read_insights"],
    ("instagram", "stats_scopes_meta"): ["instagram_manage_insights"],
    ("tiktok", "stats_scopes_tiktok"): ["video.list"],
    ("threads", "stats_scopes_threads"): ["threads_manage_insights"],
    ("facebook", "inbox_meta"): ["pages_read_user_content", "pages_manage_engagement"],
    ("instagram", "inbox_meta"): ["instagram_manage_comments"],
    ("threads", "inbox_threads"): ["threads_read_replies", "threads_manage_replies"],
    ("youtube", "inbox_google"): [YT + "youtube.force-ssl"],
}


def expected(platform: str, options: dict, kind: str = "") -> list[str]:
    out = list(BASE_SCOPES.get(platform, []))
    for (p, key), scopes in OPTION_SCOPES.items():
        if p == platform and options.get(key) == "1":
            out += scopes
    if platform == "linkedin" and kind == "page":
        out = ["w_organization_social"]
    return out


def missing(platform: str, granted: list[str] | None, wanted: list[str]) -> list[str]:
    if granted is None:
        return []
    g = set(granted)
    if platform == "youtube" and YT + "youtube.force-ssl" in g:
        g.add(YT + "youtube.upload")   # force-ssl couvre l'envoi
    return [s for s in wanted if s not in g]


async def check_public(public_url: str) -> dict:
    out = {"url": public_url, "https": public_url.startswith("https://"), "reachable": None, "detail": ""}
    try:
        async with client(10) as c:
            r = await c.get(f"{public_url}/health")
        out["reachable"] = r.status_code == 200
        if r.status_code != 200:
            out["detail"] = f"réponse {r.status_code}"
    except Exception as exc:  # noqa: BLE001 - on veut juste savoir si l'adresse répond
        out["reachable"] = False
        out["detail"] = type(exc).__name__
    return out


async def _granted(acc: dict, creds: dict, version: str) -> tuple[list[str] | None, str]:
    """(permissions accordées ou None si inconnues, source)."""
    p = acc["platform"]
    if acc.get("simulated"):
        return None, ""
    if p in ("facebook", "instagram") and creds.get("meta"):
        cid, secret = creds["meta"]
        if cid and secret:
            return await platforms.meta.granted_scopes(acc, cid, secret, version), "lu en direct"
    if p == "youtube":
        return await platforms.youtube.granted_scopes(acc), "lu en direct"
    stored = (acc.get("meta") or {}).get("scopes")
    if stored:
        return list(stored), "à la connexion"
    return None, ""


async def check_account(app, a: dict, options: dict, creds: dict) -> dict:
    from .worker import account_with_token

    s = app.state.settings
    out = {"id": a["id"], "platform": a["platform"], "name": a["name"] or a["handle"], "project": a["project"],
           "simulated": a["simulated"], "expires_at": a["expires_at"], "ok": True, "problem": "", "scopes": None,
           "scopes_source": "", "missing": []}
    try:
        acc = await account_with_token(app.state.pool, app.state.vault, a["id"])
        out["expires_at"] = acc.get("expires_at")
        await asyncio.wait_for(platforms.check_token(a["platform"], acc, s.graph_version), 20)
        try:
            out["scopes"], out["scopes_source"] = await asyncio.wait_for(_granted(acc, creds, s.graph_version), 20)
        except PublishError as exc:
            out["scopes_source"] = f"illisibles ({exc})"
        wanted = expected(a["platform"], options, (acc.get("meta") or {}).get("kind", ""))
        out["missing"] = missing(a["platform"], out["scopes"], wanted)
        if out["missing"]:
            out["ok"] = False
            out["problem"] = ("permissions manquantes : ajoutez-les à l'application du réseau puis reconnectez le "
                              "compte")
    except AuthExpired as exc:
        out.update(ok=False, problem=f"à reconnecter : {exc}")
    except (PublishError, asyncio.TimeoutError) as exc:
        out.update(ok=False, problem=str(exc) or "le réseau ne répond pas")
    except Exception as exc:  # noqa: BLE001
        _log.warning("diagnostic du compte %s : %s", a["id"], exc)
        out.update(ok=False, problem=f"vérification impossible ({type(exc).__name__})")
    exp = out["expires_at"]
    if out["ok"] and exp and a["platform"] == "linkedin" and (exp - datetime.now(timezone.utc)).days < 7:
        out["problem"] = f"autorisation à renouveler avant le {exp:%d/%m} (reconnecter le compte)"
    return out


async def run(app) -> dict:
    s, pool, vault = app.state.settings, app.state.pool, app.state.vault
    async with pool.connection() as conn:
        cur = await conn.execute("SELECT key, value FROM site_settings")
        options = {r["key"]: r["value"] for r in await cur.fetchall()}
        cur = await conn.execute("SELECT provider, client_id, client_secret_enc FROM app_credentials")
        rows = await cur.fetchall()
        cur = await conn.execute("SELECT a.id, a.platform, a.name, a.handle, a.simulated, a.expires_at, "
                                 "p.name AS project FROM social_accounts a JOIN projects p ON p.id=a.project_id "
                                 "WHERE NOT p.archived ORDER BY p.name, a.platform, a.name")
        accounts = await cur.fetchall()
    creds = {r["provider"]: (r["client_id"], vault.open(r["client_secret_enc"])) for r in rows}
    apps = []
    for p in platforms.PROVIDERS:
        if p in platforms.NO_APP:
            continue
        cid, secret = creds.get(p, ("", None))
        apps.append({"provider": p, "label": platforms.PROVIDER_LABELS[p], "configured": bool(cid and secret),
                     "accounts": sum(1 for a in accounts if platforms.PROVIDER_OF[a["platform"]] == p)})
    sem = asyncio.Semaphore(4)

    async def one(a):
        async with sem:
            return await check_account(app, a, options, creds)

    results = await asyncio.gather(check_public(s.public_url), *(one(a) for a in accounts))
    return {"public": results[0], "apps": apps, "accounts": list(results[1:]),
            "checked_at": datetime.now(timezone.utc), "simulation": s.simulation}
