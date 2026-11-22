"""Statistiques lues sur les réseaux : vues, portée, mentions J'aime, commentaires, partages, enregistrements.

Toutes les 6 heures, le serveur relit les chiffres des posts publiés depuis moins de 30 jours (au-delà, ils ne
bougent presque plus). Un bouton « Actualiser » dans Statistiques lance la même lecture à la demande.
Un réseau qui refuse (permission manquante, offre X sans lecture) : l'erreur est gardée et affichée, sans bloquer.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import log, platforms
from .platforms import METRIC_FIELDS, AuthExpired, PublishError

_log = log.get("metrics")
REFRESH_H = 6
WINDOW_DAYS = 30


async def due_targets(pool, project_id: int | None = None, force: bool = False, limit: int = 300) -> list[dict]:
    pf = "AND p.project_id=%s" if project_id else ""
    stale = "" if force else "AND (m.fetched_at IS NULL OR m.fetched_at < now() - make_interval(hours => %s))"
    params: list = [WINDOW_DAYS]
    if project_id:
        params.append(project_id)
    if not force:
        params.append(REFRESH_H)
    params.append(limit)
    async with pool.connection() as conn:
        cur = await conn.execute(f"""
            SELECT t.id, t.platform, t.external_id, t.social_account_id, t.published_at
            FROM post_targets t JOIN posts p ON p.id=t.post_id LEFT JOIN post_metrics m ON m.post_target_id=t.id
            WHERE t.status='published' AND t.external_id <> '' AND t.social_account_id IS NOT NULL
              AND t.published_at > now() - make_interval(days => %s) {pf} {stale}
            ORDER BY m.fetched_at NULLS FIRST, t.published_at DESC LIMIT %s""", params)
        return await cur.fetchall()


async def save(pool, target_id: int, values: dict, error: str = "") -> None:
    cols = list(METRIC_FIELDS)
    async with pool.connection() as conn:
        if error:
            # on garde les derniers chiffres connus, on note seulement l'erreur
            await conn.execute("INSERT INTO post_metrics(post_target_id, error, fetched_at) VALUES (%s,%s,now()) "
                               "ON CONFLICT (post_target_id) DO UPDATE SET error=EXCLUDED.error, fetched_at=now()",
                               (target_id, error[:500]))
        else:
            await conn.execute(
                f"INSERT INTO post_metrics(post_target_id, {', '.join(cols)}, error, fetched_at) "
                f"VALUES (%s, {', '.join(['%s'] * len(cols))}, '', now()) ON CONFLICT (post_target_id) DO UPDATE SET "
                + ", ".join(f"{c}=EXCLUDED.{c}" for c in cols) + ", error='', fetched_at=now()",
                [target_id] + [values.get(c) for c in cols])
        await conn.commit()


async def collect(app, project_id: int | None = None, force: bool = False) -> dict:
    """Relit les chiffres des posts récents. Renvoie {read, failed}."""
    from .worker import account_with_token

    s, pool, vault = app.state.settings, app.state.pool, app.state.vault
    read = failed = 0
    accounts: dict[int, dict | Exception] = {}
    for t in await due_targets(pool, project_id, force):
        aid = t["social_account_id"]
        try:
            if aid not in accounts:
                try:
                    accounts[aid] = await account_with_token(pool, vault, aid)
                except PublishError as exc:
                    accounts[aid] = exc
            acc = accounts[aid]
            if isinstance(acc, Exception):
                raise acc
            values = await platforms.metrics(t["platform"], acc, t["external_id"], s.graph_version, t["published_at"])
            await save(pool, t["id"], values)
            read += 1
        except AuthExpired as exc:
            await save(pool, t["id"], {}, f"compte à reconnecter : {exc}")
            failed += 1
        except PublishError as exc:
            await save(pool, t["id"], {}, str(exc))
            failed += 1
        except Exception as exc:  # noqa: BLE001 - réponse imprévue d'un réseau : on réessaiera plus tard
            _log.warning("statistiques du post %s illisibles : %s", t["id"], exc)
            await save(pool, t["id"], {}, f"lecture impossible ({type(exc).__name__})")
            failed += 1
    if read or failed:
        _log.info("statistiques relues : %s, échecs : %s", read, failed)
    return {"read": read, "failed": failed}


def week_bounds(now: datetime, tz_name: str) -> tuple[datetime, datetime]:
    """Semaine écoulée (lundi 0 h → lundi 0 h, heure locale) avant `now`, en UTC."""
    from zoneinfo import ZoneInfo

    local = now.astimezone(ZoneInfo(tz_name))
    monday = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    start = monday - timedelta(days=7)
    return start.astimezone(timezone.utc), monday.astimezone(timezone.utc)
