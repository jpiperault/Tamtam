"""Projets (apps, sites, produits) et médias."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from psycopg.types.json import Jsonb

from .. import media as media_mod, slots as slots_mod
from .common import current_user, fetchall, fetchone, get_conn, project_or_404, update_row

router = APIRouter()


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    url: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=3000)
    color: str = Field(default="#0E6E5C", pattern=r"^#[0-9A-Fa-f]{6}$")


class ProjectPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    url: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=3000)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    archived: bool | None = None
    slots: list[dict] | None = Field(default=None, max_length=50)   # [{day: 0-6, time: "HH:MM"}]


def _check_url(url: str | None) -> None:
    if url and not url.startswith(("https://", "http://")):
        raise HTTPException(422, "l'adresse doit commencer par https://")


@router.get("/projects")
async def list_projects(user=Depends(current_user), conn=Depends(get_conn)):
    return await fetchall(conn, """
        SELECT p.*, (SELECT count(*) FROM social_accounts a WHERE a.project_id=p.id) AS accounts,
               (SELECT count(*) FROM posts q WHERE q.project_id=p.id AND q.status IN ('scheduled','publishing')) AS upcoming
        FROM projects p ORDER BY p.archived, lower(p.name)""")


@router.post("/projects", status_code=201)
async def create_project(body: ProjectIn, user=Depends(current_user), conn=Depends(get_conn)):
    _check_url(body.url)
    if await fetchone(conn, "SELECT 1 FROM projects WHERE lower(name)=lower(%s)", (body.name.strip(),)):
        raise HTTPException(409, "un projet porte déjà ce nom")
    row = await fetchone(conn, "INSERT INTO projects(name, url, description, color) VALUES (%s,%s,%s,%s) RETURNING *",
                         (body.name.strip(), body.url.strip(), body.description.strip(), body.color))
    await conn.commit()
    return row


@router.patch("/projects/{project_id}")
async def patch_project(project_id: int, body: ProjectPatch, user=Depends(current_user), conn=Depends(get_conn)):
    await project_or_404(conn, project_id)
    data = body.model_dump(exclude_unset=True)
    _check_url(data.get("url"))
    if "name" in data:
        data["name"] = data["name"].strip()
        if await fetchone(conn, "SELECT 1 FROM projects WHERE lower(name)=lower(%s) AND id<>%s", (data["name"], project_id)):
            raise HTTPException(409, "un projet porte déjà ce nom")
    if "slots" in data:
        try:
            data["slots"] = Jsonb(slots_mod.clean(data["slots"] or []))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    await update_row(conn, "projects", project_id, data, {"name", "url", "description", "color", "archived", "slots"})
    await conn.commit()
    return await project_or_404(conn, project_id)


@router.get("/projects/{project_id}/slots/next")
async def next_slots(project_id: int, request: Request, count: int = 1, user=Depends(current_user),
                     conn=Depends(get_conn)):
    """Prochains créneaux libres du projet (pour l'écran de rédaction et les campagnes)."""
    from datetime import datetime, timezone

    project = await project_or_404(conn, project_id)
    found = slots_mod.upcoming(project["slots"], request.app.state.settings.timezone,
                               await slots_mod.taken(conn, project_id), datetime.now(timezone.utc),
                               max(1, min(count, 30)))
    return {"slots": project["slots"], "next": found}


# --- Médias

MEDIA_COLS = "id, project_id, token, ext, filename, mime, kind, size, width, height, duration_s, created_at"


def media_out(m: dict) -> dict:
    return {**{k: m[k] for k in ("id", "project_id", "filename", "mime", "kind", "size", "width", "height",
                                 "duration_s", "created_at")}, "url": f"/m/{m['token']}{m['ext']}"}


@router.get("/projects/{project_id}/media")
async def list_media(project_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    rows = await fetchall(conn, f"SELECT {MEDIA_COLS} FROM media WHERE project_id=%s ORDER BY created_at DESC LIMIT 200",
                          (project_id,))
    return [media_out(m) for m in rows]


@router.post("/projects/{project_id}/media", status_code=201)
async def upload_media(project_id: int, request: Request, file: UploadFile = File(...), user=Depends(current_user),
                       conn=Depends(get_conn)):
    await project_or_404(conn, project_id)
    s = request.app.state.settings
    limit = s.max_upload_mb * 1024 * 1024
    fd, tmp = tempfile.mkstemp(prefix="tamtam-up-")
    try:
        size = 0
        with os.fdopen(fd, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    raise HTTPException(413, f"fichier trop volumineux ({s.max_upload_mb} Mo au plus)")
                out.write(chunk)
        if size == 0:
            raise HTTPException(422, "fichier vide")
        import asyncio
        try:
            info = await asyncio.to_thread(media_mod.store, Path(tmp), s.data_dir)
        except media_mod.MediaError as exc:
            raise HTTPException(422, str(exc)) from exc
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
    row = await fetchone(conn, f"INSERT INTO media(project_id, token, ext, filename, mime, kind, size, width, height, "
                               f"duration_s, created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING {MEDIA_COLS}",
                         (project_id, info["token"], info["ext"], (file.filename or "")[:200], info["mime"],
                          info["kind"], info["size"], info["width"], info["height"], info.get("duration_s"),
                          user["id"]))
    await conn.commit()
    return media_out(row)


@router.delete("/media/{media_id}")
async def delete_media(media_id: int, request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    m = await fetchone(conn, "SELECT * FROM media WHERE id=%s", (media_id,))
    if not m:
        raise HTTPException(404, "média introuvable")
    used = await fetchone(conn, "SELECT 1 FROM post_media pm JOIN posts p ON p.id=pm.post_id WHERE pm.media_id=%s "
                                "AND p.status IN ('draft','scheduled','publishing')", (media_id,))
    if used:
        raise HTTPException(409, "ce média est utilisé par un post pas encore publié")
    await conn.execute("DELETE FROM post_media WHERE media_id=%s", (media_id,))
    await conn.execute("DELETE FROM media WHERE id=%s", (media_id,))
    await conn.commit()
    media_mod.remove(request.app.state.settings.data_dir, m["token"], m["ext"])
    return {"ok": True}
