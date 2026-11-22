"""Boîte de réception : commentaires reçus sous les posts publiés par Tamtam, sur tous les réseaux, au même endroit.

Toutes les 30 minutes (et avec le bouton « Relever » de la page), Tamtam lit les commentaires des posts publiés
depuis moins de 30 jours sur les réseaux qui le permettent, et garde ceux qui ne viennent pas du compte lui-même.
On y répond depuis Tamtam (Claude peut proposer une réponse) ou on les marque comme traités.
"""
from __future__ import annotations

from datetime import datetime

from psycopg.types.json import Jsonb

from . import log, notify, platforms
from .platforms import AuthExpired, PublishError

_log = log.get("inbox")
WINDOW_DAYS = 30


async def collect(app, project_id: int | None = None) -> dict:
    """Relève les commentaires. Renvoie {new, failed, errors: [..]}."""
    from .worker import account_with_token

    s, pool, vault = app.state.settings, app.state.pool, app.state.vault
    pf = "AND p.project_id=%s" if project_id else ""
    async with pool.connection() as conn:
        enabled = await enabled_platforms(conn)
    params: list = [list(platforms.INBOX), WINDOW_DAYS] + ([project_id] if project_id else [])
    async with pool.connection() as conn:
        cur = await conn.execute(f"""
            SELECT t.id, t.platform, t.external_id, t.social_account_id, p.project_id, pr.name AS project, a.simulated
            FROM post_targets t JOIN posts p ON p.id=t.post_id JOIN projects pr ON pr.id=p.project_id
            JOIN social_accounts a ON a.id=t.social_account_id
            WHERE t.status='published' AND t.external_id <> '' AND t.social_account_id IS NOT NULL
              AND t.platform = ANY(%s) AND t.published_at > now() - make_interval(days => %s) {pf}
            ORDER BY t.published_at DESC LIMIT 200""", params)
        targets = await cur.fetchall()
    new = failed = 0
    errors: dict[str, str] = {}
    accounts: dict[int, object] = {}
    for t in targets:
        if t["platform"] not in enabled and not t["simulated"]:   # comptes de démonstration : toujours relevés
            continue
        try:
            aid = t["social_account_id"]
            if aid not in accounts:
                try:
                    accounts[aid] = await account_with_token(pool, vault, aid)
                except PublishError as exc:
                    accounts[aid] = exc
            acc = accounts[aid]
            if isinstance(acc, Exception):
                raise acc
            items = await platforms.comments(t["platform"], acc, t["external_id"], s.graph_version)
        except (AuthExpired, PublishError) as exc:
            failed += 1
            errors.setdefault(t["platform"], str(exc))
            continue
        except Exception as exc:  # noqa: BLE001 - réponse imprévue : on réessaiera
            _log.warning("commentaires du post %s illisibles : %s", t["id"], exc)
            failed += 1
            continue
        added = await store(pool, t["id"], t["platform"], items)
        new += added
        if added:
            notify.fire(app, "inbox", f"💬 Tamtam : {added} nouveau(x) commentaire(s) sur "
                                      f"{platforms.LABELS[t['platform']]} (projet {t['project']}).\n"
                                      f"{s.public_url}/#/boite")
    return {"new": new, "failed": failed, "errors": [f"{platforms.LABELS[p]} : {e}" for p, e in errors.items()]}


async def enabled_platforms(conn) -> list[str]:
    """Réseaux relevés : Bluesky toujours ; les autres si l'option de leur fournisseur est cochée."""
    cur = await conn.execute("SELECT key, value FROM site_settings WHERE key LIKE 'inbox\\_%%'")
    on = {r["key"][6:] for r in await cur.fetchall() if r["value"] == "1"}
    return [p for p in platforms.INBOX if p == "bluesky" or platforms.PROVIDER_OF[p] in on]


async def store(pool, target_id: int, platform: str, items: list[dict]) -> int:
    added = 0
    async with pool.connection() as conn:
        for c in items:
            if c.get("own"):
                continue
            cur = await conn.execute(
                "INSERT INTO inbox_items(post_target_id, platform, external_id, extra, author_name, author_handle, "
                "author_avatar, text, commented_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (platform, external_id) DO UPDATE SET text=EXCLUDED.text, fetched_at=now() "
                "RETURNING (xmax = 0) AS inserted",
                (target_id, platform, str(c["id"]), Jsonb(c.get("extra") or {}), (c.get("author_name") or "")[:200],
                 (c.get("author_handle") or "")[:200], (c.get("author_avatar") or "")[:1000],
                 (c.get("text") or "")[:5000], _when(c.get("created_at"))))
            row = await cur.fetchone()
            added += 1 if row and row["inserted"] else 0
        await conn.commit()
    return added


def _when(v):
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00").replace("+0000", "+00:00"))
    except ValueError:
        return None
