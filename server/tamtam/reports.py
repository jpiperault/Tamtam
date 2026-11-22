"""Rapport hebdomadaire rédigé par Claude : chiffres de la semaine écoulée, points forts, idées pour la suivante.

Automatique chaque lundi à partir de 8 h (heure du serveur) si l'option est activée dans Administration, pour
chaque projet qui a publié pendant la semaine ; envoyé aussi par Telegram si les alertes sont configurées.
Un bouton « Rapport de la semaine » le génère à la demande dans Statistiques.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from psycopg.types.json import Jsonb

from . import ai, log, metrics, notify
from .platforms import LABELS, METRIC_FIELDS

_log = log.get("reports")
AUTO_HOUR = 8


class ReportError(Exception):
    pass


async def gather(conn, project_id: int, start: datetime, end: datetime) -> dict:
    """Chiffres envoyés à Claude (et gardés avec le rapport)."""
    cur = await conn.execute("""
        SELECT p.id, p.campaign, left(p.body, 280) AS body, min(t.published_at) AS published_at,
               (SELECT count(*) FROM post_media pm WHERE pm.post_id=p.id)::int AS medias, p.link_url <> '' AS has_link
        FROM posts p JOIN post_targets t ON t.post_id=p.id
        WHERE p.project_id=%s AND t.status='published' AND t.published_at >= %s AND t.published_at < %s
        GROUP BY p.id ORDER BY min(t.published_at)""", (project_id, start, end))
    posts = await cur.fetchall()
    out_posts = []
    for p in posts:
        cur = await conn.execute(f"""
            SELECT t.platform, t.body_override, {', '.join('m.' + c for c in METRIC_FIELDS)}, m.error,
                   COALESCE((SELECT sum(clicks) FROM links l WHERE l.post_target_id=t.id), 0)::int AS clics_lien
            FROM post_targets t LEFT JOIN post_metrics m ON m.post_target_id=t.id
            WHERE t.post_id=%s AND t.status='published' ORDER BY t.platform""", (p["id"],))
        nets = []
        for r in await cur.fetchall():
            item = {"reseau": LABELS.get(r["platform"], r["platform"]), "clics_lien": r["clics_lien"]}
            item.update({c: r[c] for c in METRIC_FIELDS})
            if r["error"]:
                item["chiffres_indisponibles"] = r["error"]
            if r["body_override"]:
                item["texte_adapte"] = r["body_override"][:280]
            nets.append(item)
        out_posts.append({"date": p["published_at"].date().isoformat(), "texte": p["body"], "campagne": p["campaign"],
                          "medias": p["medias"], "lien": p["has_link"], "reseaux": nets})

    async def totals(a: datetime, b: datetime) -> dict:
        cur = await conn.execute(f"""
            SELECT t.platform, count(*)::int AS posts, {', '.join(f'sum(m.{c})::bigint AS {c}' for c in METRIC_FIELDS)}
            FROM post_targets t JOIN posts p ON p.id=t.post_id LEFT JOIN post_metrics m ON m.post_target_id=t.id
            WHERE p.project_id=%s AND t.status='published' AND t.published_at >= %s AND t.published_at < %s
            GROUP BY t.platform""", (project_id, a, b))
        return {LABELS.get(r["platform"], r["platform"]): {k: v for k, v in r.items() if k != "platform"}
                for r in await cur.fetchall()}

    cur = await conn.execute("""
        SELECT COALESCE(sum(c.clicks), 0)::int AS n FROM link_clicks c JOIN links l ON l.id=c.link_id
        WHERE l.project_id=%s AND c.day >= %s::date AND c.day < %s::date""", (project_id, start, end))
    clicks = (await cur.fetchone())["n"]
    cur = await conn.execute("SELECT count(*)::int AS n FROM posts WHERE project_id=%s AND status='scheduled' "
                             "AND scheduled_at >= %s AND scheduled_at < %s + interval '7 days'", (project_id, end, end))
    upcoming = (await cur.fetchone())["n"]
    return {"semaine": {"du": start.date().isoformat(), "au": (end - timedelta(days=1)).date().isoformat()},
            "posts": out_posts, "totaux_par_reseau": await totals(start, end),
            "totaux_semaine_precedente": await totals(start - timedelta(days=7), start),
            "clics_sur_liens_suivis": clicks, "posts_programmes_semaine_suivante": upcoming}


async def _ai_settings(conn) -> dict | None:
    cur = await conn.execute("SELECT * FROM ai_settings WHERE id=1")
    return await cur.fetchone()


async def generate(app, project_id: int, start: datetime, end: datetime, user_id: int | None = None) -> dict:
    """Relit les chiffres, rédige et enregistre le rapport. Lève ReportError si impossible."""
    pool, vault, s = app.state.pool, app.state.vault, app.state.settings
    await metrics.collect(app, project_id)
    async with pool.connection() as conn:
        cur = await conn.execute("SELECT * FROM projects WHERE id=%s", (project_id,))
        project = await cur.fetchone()
        if not project:
            raise ReportError("projet introuvable")
        data = await gather(conn, project_id, start, end)
        conf = await _ai_settings(conn)
        await conn.commit()
    if not conf or not conf["api_key_enc"]:
        if not s.simulation:
            raise ReportError("Claude n'est pas configuré : un administrateur doit saisir la clé API dans Administration")
        content, model, tin, tout = ai.simulated_report(data), "simulation", 0, 0
    else:
        async with pool.connection() as conn:
            cur = await conn.execute("SELECT count(*)::int AS n FROM ai_calls WHERE ok AND "
                                     "created_at >= date_trunc('day', now())")
            if (await cur.fetchone())["n"] >= conf["daily_limit"]:
                raise ReportError(f"limite de {conf['daily_limit']} rédactions par jour atteinte")
        try:
            content, model, tin, tout = await ai.weekly_report(vault.open(conf["api_key_enc"]), conf["model"],
                                                               project, data)
        except ai.AIError as exc:
            async with pool.connection() as conn:
                await conn.execute("INSERT INTO ai_calls(user_id, project_id, model, ok) VALUES (%s,%s,%s,false)",
                                   (user_id, project_id, conf["model"]))
                await conn.commit()
            raise ReportError(str(exc)) from exc
        async with pool.connection() as conn:
            await conn.execute("INSERT INTO ai_calls(user_id, project_id, model, input_tokens, output_tokens) "
                               "VALUES (%s,%s,%s,%s,%s)", (user_id, project_id, model, tin, tout))
            await conn.commit()
    async with pool.connection() as conn:
        cur = await conn.execute(
            "INSERT INTO reports(project_id, period_start, period_end, content, data, model, created_by) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *",
            (project_id, start.date(), (end - timedelta(days=1)).date(), Jsonb(content),
             Jsonb(_jsonable(data)), model, user_id))
        row = await cur.fetchone()
        await conn.commit()
    return row


def _jsonable(data: dict) -> dict:
    import json
    return json.loads(json.dumps(data, default=str))


def telegram_text(public_url: str, project: str, report: dict) -> str:
    c = report["content"]
    parts = [f"📊 Tamtam : bilan de la semaine pour {project} ({report['period_start']:%d/%m} au "
             f"{report['period_end']:%d/%m})", "", c["resume"]]
    for key, title in (("points_forts", "Points forts"), ("a_ameliorer", "À améliorer"), ("idees", "Idées")):
        if c.get(key):
            parts += ["", title + " :"] + [f"• {x}" for x in c[key]]
    parts += ["", f"{public_url}/#/stats"]
    return "\n".join(parts)


async def auto_weekly(app) -> int:
    """Rapports automatiques du lundi (option « rapport hebdomadaire » dans Administration)."""
    from zoneinfo import ZoneInfo

    s, pool = app.state.settings, app.state.pool
    now = datetime.now(timezone.utc)
    local = now.astimezone(ZoneInfo(s.timezone))
    if local.weekday() != 0 or local.hour < AUTO_HOUR:
        return 0
    start, end = metrics.week_bounds(now, s.timezone)
    async with pool.connection() as conn:
        cur = await conn.execute("SELECT value FROM site_settings WHERE key='report_weekly'")
        row = await cur.fetchone()
        if not row or row["value"] != "1":
            return 0
        cur = await conn.execute("""
            SELECT DISTINCT p.id, p.name FROM projects p JOIN posts q ON q.project_id=p.id
            JOIN post_targets t ON t.post_id=q.id
            WHERE NOT p.archived AND t.status='published' AND t.published_at >= %s AND t.published_at < %s
              AND NOT EXISTS (SELECT 1 FROM reports r WHERE r.project_id=p.id AND r.period_start=%s::date
                              AND r.created_by IS NULL)""", (start, end, start))
        projects = await cur.fetchall()
    done = 0
    for p in projects:
        try:
            rep = await generate(app, p["id"], start, end)
        except ReportError as exc:
            _log.warning("rapport hebdomadaire du projet %s impossible : %s", p["id"], exc)
            continue
        done += 1
        notify.fire(app, "report", telegram_text(s.public_url, p["name"], rep))
    return done
