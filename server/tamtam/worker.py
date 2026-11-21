"""Publication en tâche de fond : toutes les 10 secondes, envoie les posts dont l'heure est venue.

Chaque réseau visé est traité à part : un échec sur l'un ne bloque pas les autres. Les erreurs passagères
(service indisponible, trop de requêtes) sont réessayées 3 fois, à 5 puis 10 minutes d'intervalle.
"""
from __future__ import annotations

import asyncio
import json
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from . import log, media as media_mod, platforms
from .platforms import AuthExpired, Content, MediaFile, PublishError

_log = log.get("worker")
MAX_ATTEMPTS = 3
TICK_S = 10
PUBLISH_TIMEOUT_S = 20 * 60


def with_utm(url: str, platform: str, campaign: str, post_id: int) -> str:
    parts = urlsplit(url)
    q = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not k.startswith("utm_")]
    q += [("utm_source", platform), ("utm_medium", "social"), ("utm_campaign", campaign or "tamtam"),
          ("utm_content", f"post-{post_id}")]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))


async def recompute_status(conn, post_id: int) -> str:
    # Verrou sur le post d'abord : deux réseaux qui finissent en même temps attendent leur tour, et le second
    # relit alors l'état des cibles après l'enregistrement du premier.
    cur = await conn.execute("SELECT status FROM posts WHERE id=%s FOR UPDATE", (post_id,))
    row = await cur.fetchone()
    cur = await conn.execute("SELECT status FROM post_targets WHERE post_id=%s", (post_id,))
    sts = [r["status"] for r in await cur.fetchall()]
    if not row or row["status"] == "draft":
        return row["status"] if row else ""
    if not sts:
        new = "failed"
    elif all(s == "published" for s in sts):
        new = "done"
    elif any(s in ("pending", "publishing") for s in sts):
        new = "publishing" if any(s != "pending" for s in sts) else "scheduled"
    elif any(s == "published" for s in sts):
        new = "partial"
    else:
        new = "failed"
    await conn.execute("UPDATE posts SET status=%s, updated_at=now() WHERE id=%s", (new, post_id))
    return new


async def credentials(conn, vault, provider: str) -> tuple[str, str | None]:
    cur = await conn.execute("SELECT client_id, client_secret_enc FROM app_credentials WHERE provider=%s", (provider,))
    row = await cur.fetchone()
    if not row or not row["client_id"]:
        raise PublishError(f"l'application {platforms.PROVIDER_LABELS[provider]} n'est pas configurée "
                           "(Administration → Applications des réseaux)")
    return row["client_id"], vault.open(row["client_secret_enc"])


async def account_with_token(pool, vault, account_id: int, force_refresh: bool = False) -> dict:
    """Compte avec son jeton en clair ; renouvelle le jeton X / TikTok s'il expire dans moins de 5 minutes."""
    async with pool.connection() as conn:
        async with conn.transaction():
            cur = await conn.execute("SELECT * FROM social_accounts WHERE id=%s FOR UPDATE", (account_id,))
            acc = await cur.fetchone()
            if not acc:
                raise PublishError("compte social déconnecté entre-temps")
            acc["access_token"] = vault.open(acc["access_token_enc"])
            if acc["simulated"]:
                return acc
            if acc["access_token"] is None:
                raise AuthExpired("jeton illisible (TOKEN_KEY a changé ?) : reconnectez le compte")
            soon = datetime.now(timezone.utc) + timedelta(minutes=5)
            needs = acc["platform"] in ("x", "tiktok") and (force_refresh or (acc["expires_at"] and acc["expires_at"] < soon))
            if needs:
                rt = vault.open(acc["refresh_token_enc"])
                if not rt:
                    raise AuthExpired(f"{platforms.LABELS[acc['platform']]} : autorisation expirée, reconnectez le compte")
                cid, secret = await credentials(conn, vault, platforms.PROVIDER_OF[acc["platform"]])
                try:
                    tok = await platforms.refresh(acc["platform"], cid, secret, rt)
                except PublishError as exc:
                    if exc.retry:
                        raise
                    raise AuthExpired(f"{platforms.LABELS[acc['platform']]} : renouvellement refusé, reconnectez "
                                      f"le compte ({exc})") from exc
                now = datetime.now(timezone.utc)
                exp = now + timedelta(seconds=int(tok["expires_in"])) if tok.get("expires_in") else None
                rexp = (now + timedelta(seconds=int(tok["refresh_expires_in"]))
                        if tok.get("refresh_expires_in") else acc["refresh_expires_at"])
                await conn.execute(
                    "UPDATE social_accounts SET access_token_enc=%s, refresh_token_enc=%s, expires_at=%s, "
                    "refresh_expires_at=%s, status='ok', last_error='', updated_at=now() WHERE id=%s",
                    (vault.seal(tok["access_token"]), vault.seal(tok.get("refresh_token") or rt), exp, rexp, acc["id"]))
                acc["access_token"] = tok["access_token"]
            return acc


async def _make_link(conn, post: dict, target: dict, public_url: str) -> str:
    if not post["link_url"]:
        return ""
    cur = await conn.execute("SELECT code FROM links WHERE post_target_id=%s", (target["id"],))
    row = await cur.fetchone()
    if row:
        return f"{public_url}/l/{row['code']}"
    code = secrets.token_urlsafe(5).replace("-", "a").replace("_", "b")
    dest = with_utm(post["link_url"], target["platform"], post["campaign"], post["id"])
    await conn.execute("INSERT INTO links(code, project_id, post_target_id, platform, target_url) "
                       "VALUES (%s,%s,%s,%s,%s)", (code, post["project_id"], target["id"], target["platform"], dest))
    return f"{public_url}/l/{code}"


async def publish_target(app, target_id: int) -> None:
    s = app.state.settings
    pool, vault = app.state.pool, app.state.vault
    async with pool.connection() as conn:
        cur = await conn.execute("SELECT * FROM post_targets WHERE id=%s", (target_id,))
        target = await cur.fetchone()
        cur = await conn.execute("SELECT * FROM posts WHERE id=%s", (target["post_id"],))
        post = await cur.fetchone()
        cur = await conn.execute("SELECT m.* FROM post_media pm JOIN media m ON m.id=pm.media_id "
                                 "WHERE pm.post_id=%s ORDER BY pm.position", (post["id"],))
        files = [MediaFile(kind=m["kind"], path=media_mod.path_for(s.data_dir, m["token"], m["ext"]),
                           url=f"{s.public_url}/m/{m['token']}{m['ext']}", mime=m["mime"], size=m["size"])
                 for m in await cur.fetchall()]
        link = ""
        if platforms.RULES[target["platform"]]["link_in_text"]:
            link = await _make_link(conn, post, target, s.public_url)
        await conn.commit()
    text = target["body_override"] if target["body_override"] is not None else post["body"]
    status, err, ext_id, ext_url, retry_at = "published", "", "", "", None
    try:
        if target["social_account_id"] is None:
            raise PublishError("compte social déconnecté : reconnectez-le puis réessayez")
        acc = await account_with_token(pool, vault, target["social_account_id"])
        content = Content(text=text, link=link, media=files)
        try:
            res = await asyncio.wait_for(platforms.publish(target["platform"], acc, content, s.graph_version),
                                         PUBLISH_TIMEOUT_S)
        except AuthExpired:
            if target["platform"] not in ("x", "tiktok"):
                raise
            acc = await account_with_token(pool, vault, target["social_account_id"], force_refresh=True)
            res = await asyncio.wait_for(platforms.publish(target["platform"], acc, content, s.graph_version),
                                         PUBLISH_TIMEOUT_S)
        ext_id, ext_url = res.external_id, res.url
    except AuthExpired as exc:
        status, err = "failed", str(exc)
        async with pool.connection() as conn:
            await conn.execute("UPDATE social_accounts SET status='expired', last_error=%s, updated_at=now() "
                               "WHERE id=%s", (err[:500], target["social_account_id"]))
            await conn.commit()
    except PublishError as exc:
        err = str(exc)
        if exc.retry and target["attempts"] < MAX_ATTEMPTS:
            status = "pending"
            retry_at = datetime.now(timezone.utc) + timedelta(minutes=5 * target["attempts"])
        else:
            status = "failed"
    except asyncio.TimeoutError:
        status, err = "failed", "délai dépassé : vérifiez sur le réseau si le post est paru avant de réessayer"
    except Exception as exc:  # erreur inattendue (réseau coupé, réponse imprévue…)
        _log.exception("publication %s : erreur inattendue", target_id)
        err = f"erreur inattendue : {type(exc).__name__}"
        if target["attempts"] < MAX_ATTEMPTS:
            status, retry_at = "pending", datetime.now(timezone.utc) + timedelta(minutes=5 * target["attempts"])
        else:
            status = "failed"
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE post_targets SET status=%s, error=%s, external_id=%s, external_url=%s, not_before=%s, "
            "published_at=CASE WHEN %s='published' THEN now() ELSE published_at END, updated_at=now() WHERE id=%s",
            (status, err[:1000], ext_id, ext_url, retry_at, status, target_id))
        await recompute_status(conn, post["id"])
        await conn.commit()
    _log.info("post %s → %s : %s%s", post["id"], target["platform"], status, f" ({err})" if err else "")


async def claim(pool, limit: int = 4) -> list[int]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "UPDATE post_targets SET status='publishing', attempts=attempts+1, updated_at=now() WHERE id IN ("
            " SELECT t.id FROM post_targets t JOIN posts p ON p.id=t.post_id"
            " WHERE t.status='pending' AND p.status <> 'draft' AND p.scheduled_at <= now()"
            " AND (t.not_before IS NULL OR t.not_before <= now())"
            " ORDER BY p.scheduled_at, t.id LIMIT %s FOR UPDATE OF t SKIP LOCKED) RETURNING id, post_id",
            (limit,))
        rows = await cur.fetchall()
        for pid in {r["post_id"] for r in rows}:
            await recompute_status(conn, pid)
        await conn.commit()
        return [r["id"] for r in rows]


async def reset_interrupted(pool) -> None:
    """Au démarrage : une publication coupée en plein envoi est marquée en échec (pas de double post automatique)."""
    async with pool.connection() as conn:
        cur = await conn.execute(
            "UPDATE post_targets SET status='failed', error='publication interrompue par un redémarrage : vérifiez "
            "sur le réseau si le post est paru avant de réessayer', updated_at=now() WHERE status='publishing' "
            "RETURNING post_id")
        pids = {r["post_id"] for r in await cur.fetchall()}
        cur = await conn.execute("SELECT id FROM posts WHERE status='publishing'")
        pids |= {r["id"] for r in await cur.fetchall()}
        for pid in pids:
            await recompute_status(conn, pid)
        await conn.commit()


async def run(app, stop: asyncio.Event) -> None:
    sem = asyncio.Semaphore(3)
    running: set[asyncio.Task] = set()

    async def one(tid: int):
        async with sem:
            await publish_target(app, tid)

    while not stop.is_set():
        try:
            if len(running) < 6:
                for tid in await claim(app.state.pool, 6 - len(running)):
                    t = asyncio.create_task(one(tid))
                    running.add(t)
                    t.add_done_callback(running.discard)
        except Exception as exc:
            _log.warning("boucle de publication : %s", exc)
        try:
            await asyncio.wait_for(stop.wait(), TICK_S)
        except asyncio.TimeoutError:
            pass
    for t in running:
        t.cancel()


