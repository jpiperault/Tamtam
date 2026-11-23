"""Réglages de la page « lien en bio » d'un projet et ses statistiques."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from .. import bio
from ..platforms import PLATFORMS
from .common import current_user, fetchall, fetchone, get_conn, project_or_404

router = APIRouter()


async def _free_slug(conn, base: str, project_id: int) -> str:
    slug, n = base, 2
    while slug in bio.RESERVED or await fetchone(conn, "SELECT 1 FROM bio_pages WHERE slug=%s AND project_id<>%s",
                                                (slug, project_id)):
        slug = f"{base[:36]}-{n}"
        n += 1
    return slug


def _out(row: dict, public_url: str, avatar: dict | None) -> dict:
    url = f"{public_url}/b/{row['slug']}"
    return {"slug": row["slug"], "enabled": row["enabled"], "title": row["title"], "subtitle": row["subtitle"],
            "links": row["links"], "show_latest": row["show_latest"], "avatar_media_id": row["avatar_media_id"],
            "avatar_url": f"/m/{avatar['token']}{avatar['ext']}" if avatar else "",
            "url": url, "per_network": {p: f"{url}?src={p}" for p in PLATFORMS}}


@router.get("/projects/{project_id}/bio")
async def get_bio(project_id: int, request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    project = await project_or_404(conn, project_id)
    row = await fetchone(conn, "SELECT * FROM bio_pages WHERE project_id=%s", (project_id,))
    if not row:   # première ouverture : page préparée (désactivée) avec l'adresse du projet
        links = [{"id": "", "label": "Découvrir " + project["name"], "url": project["url"]}] if project["url"] else []
        row = {"slug": await _free_slug(conn, bio.slugify(project["name"]), project_id), "enabled": False,
               "title": project["name"], "subtitle": "", "links": bio.clean_links(links), "show_latest": True,
               "avatar_media_id": None}
    avatar = await fetchone(conn, "SELECT token, ext FROM media WHERE id=%s", (row["avatar_media_id"],)) \
        if row["avatar_media_id"] else None
    return _out(row, request.app.state.settings.public_url, avatar)


class BioIn(BaseModel):
    slug: str = Field(min_length=1, max_length=40)
    enabled: bool = False
    title: str = Field(default="", max_length=80)
    subtitle: str = Field(default="", max_length=200)
    links: list[dict] = Field(default_factory=list, max_length=20)
    show_latest: bool = True
    avatar_media_id: int | None = None


@router.put("/projects/{project_id}/bio")
async def save_bio(project_id: int, body: BioIn, request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    await project_or_404(conn, project_id)
    slug = body.slug.strip().lower()
    if not bio.SLUG_RE.match(slug) or slug in bio.RESERVED:
        raise HTTPException(422, "adresse invalide : lettres minuscules, chiffres et tirets (2 à 40 caractères)")
    if await fetchone(conn, "SELECT 1 FROM bio_pages WHERE slug=%s AND project_id<>%s", (slug, project_id)):
        raise HTTPException(409, "cette adresse est déjà prise par un autre projet")
    try:
        links = bio.clean_links(body.links)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if body.enabled and not links:
        raise HTTPException(422, "ajoutez au moins un lien avant d'activer la page")
    if body.avatar_media_id and not await fetchone(conn, "SELECT 1 FROM media WHERE id=%s AND project_id=%s "
                                                         "AND kind='image'", (body.avatar_media_id, project_id)):
        raise HTTPException(422, "l'image choisie n'appartient pas à ce projet")
    await conn.execute(
        "INSERT INTO bio_pages(project_id, slug, enabled, title, subtitle, links, show_latest, avatar_media_id) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (project_id) DO UPDATE SET slug=EXCLUDED.slug, "
        "enabled=EXCLUDED.enabled, title=EXCLUDED.title, subtitle=EXCLUDED.subtitle, links=EXCLUDED.links, "
        "show_latest=EXCLUDED.show_latest, avatar_media_id=EXCLUDED.avatar_media_id, updated_at=now()",
        (project_id, slug, body.enabled, body.title.strip(), body.subtitle.strip(), Jsonb(links), body.show_latest,
         body.avatar_media_id))
    await conn.commit()
    return await get_bio(project_id, request, user, conn)


@router.get("/projects/{project_id}/bio/stats")
async def bio_stats(project_id: int, days: int = 30, user=Depends(current_user), conn=Depends(get_conn)):
    days = max(1, min(days, 365))
    views = await fetchall(conn, "SELECT source, sum(views)::int AS n FROM bio_views WHERE project_id=%s "
                                 "AND day >= current_date - %s::int GROUP BY source ORDER BY n DESC", (project_id, days))
    clicks = await fetchall(conn, "SELECT link_id, sum(clicks)::int AS n FROM bio_clicks WHERE project_id=%s "
                                  "AND day >= current_date - %s::int GROUP BY link_id ORDER BY n DESC", (project_id, days))
    by_source = await fetchall(conn, "SELECT source, sum(clicks)::int AS n FROM bio_clicks WHERE project_id=%s "
                                     "AND day >= current_date - %s::int GROUP BY source ORDER BY n DESC",
                               (project_id, days))
    return {"days": days, "views": views, "clicks": clicks, "clicks_by_source": by_source}
