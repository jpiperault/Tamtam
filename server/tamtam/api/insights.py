"""Statistiques lues sur les réseaux (par post) et rapports hebdomadaires rédigés par Claude."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from .. import metrics, reports
from ..platforms import METRIC_FIELDS
from .common import current_user, fetchall, fetchone, get_conn, project_or_404

router = APIRouter()


@router.get("/insights")
async def insights(project_id: int, days: int = 30, user=Depends(current_user), conn=Depends(get_conn)):
    """Totaux par réseau et chiffres de chaque post publié sur la période."""
    days = max(1, min(days, 365))
    sums = ", ".join(f"sum(m.{c})::bigint AS {c}" for c in METRIC_FIELDS)
    by_platform = await fetchall(conn, f"""
        SELECT t.platform, count(*)::int AS posts, count(m.post_target_id)::int AS measured, {sums},
               max(m.fetched_at) AS fetched_at
        FROM post_targets t JOIN posts p ON p.id=t.post_id LEFT JOIN post_metrics m ON m.post_target_id=t.id
        WHERE p.project_id=%s AND t.status='published' AND t.published_at >= now() - make_interval(days => %s)
        GROUP BY t.platform""", (project_id, days))
    rows = await fetchall(conn, f"""
        SELECT p.id AS post_id, left(p.body, 160) AS body, t.platform, t.external_url, t.published_at,
               {', '.join('m.' + c for c in METRIC_FIELDS)}, m.error, m.fetched_at,
               COALESCE((SELECT sum(clicks) FROM links l WHERE l.post_target_id=t.id), 0)::int AS clicks
        FROM post_targets t JOIN posts p ON p.id=t.post_id LEFT JOIN post_metrics m ON m.post_target_id=t.id
        WHERE p.project_id=%s AND t.status='published' AND t.published_at >= now() - make_interval(days => %s)
        ORDER BY t.published_at DESC LIMIT 300""", (project_id, days))
    posts: dict[int, dict] = {}
    for r in rows:
        p = posts.setdefault(r["post_id"], {"id": r["post_id"], "body": r["body"], "published_at": r["published_at"],
                                            "networks": []})
        p["networks"].append({k: r[k] for k in ("platform", "external_url", "error", "fetched_at", "clicks",
                                                *METRIC_FIELDS)})
    return {"days": days, "by_platform": by_platform, "posts": list(posts.values())}


@router.post("/insights/refresh")
async def refresh(project_id: int, request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    await project_or_404(conn, project_id)
    await conn.commit()
    return await metrics.collect(request.app, project_id, force=True)


def _report_out(r: dict) -> dict:
    return {k: r[k] for k in ("id", "project_id", "period_start", "period_end", "content", "model", "created_at")} | {
        "automatic": r["created_by"] is None}


@router.get("/reports")
async def list_reports(project_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    rows = await fetchall(conn, "SELECT * FROM reports WHERE project_id=%s ORDER BY created_at DESC LIMIT 20",
                          (project_id,))
    return [_report_out(r) for r in rows]


@router.post("/reports", status_code=201)
async def make_report(project_id: int, request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    """Bilan des 7 derniers jours, à la demande."""
    await project_or_404(conn, project_id)
    await conn.commit()
    end = datetime.now(timezone.utc)
    try:
        row = await reports.generate(request.app, project_id, end - timedelta(days=7), end + timedelta(days=1),
                                     user["id"])
    except reports.ReportError as exc:
        raise HTTPException(409 if "configuré" in str(exc) else 502, str(exc)) from exc
    return _report_out(row)


@router.delete("/reports/{report_id}")
async def delete_report(report_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    if not await fetchone(conn, "DELETE FROM reports WHERE id=%s RETURNING id", (report_id,)):
        raise HTTPException(404, "rapport introuvable")
    await conn.commit()
    return {"ok": True}
