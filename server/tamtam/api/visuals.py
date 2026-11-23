"""Visuels d'annonce : aperçu (image renvoyée directement) et enregistrement dans la médiathèque du projet."""
from __future__ import annotations

import asyncio
import io
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from .. import media as media_mod, visuals
from .common import current_user, fetchone, get_conn, project_or_404
from .projects import MEDIA_COLS, media_out

router = APIRouter()


class VisualIn(BaseModel):
    template: str = Field(default="annonce", pattern="^(annonce|clair|citation)$")
    format: str = Field(default="carre", pattern="^(carre|portrait|story|paysage)$")
    title: str = Field(default="", max_length=200)
    subtitle: str = Field(default="", max_length=300)
    badge: str = Field(default="", max_length=30)
    footer: str = Field(default="", max_length=60)
    color: str = Field(default="", pattern=r"^(|#[0-9A-Fa-f]{6})$")   # vide = couleur du projet
    media_id: int | None = None                                      # capture d'écran (image de la médiathèque)


async def _render(conn, request: Request, project_id: int, body: VisualIn):
    project = await project_or_404(conn, project_id)
    shot = None
    if body.media_id:
        m = await fetchone(conn, "SELECT token, ext, kind FROM media WHERE id=%s AND project_id=%s",
                           (body.media_id, project_id))
        if not m or m["kind"] != "image":
            raise HTTPException(422, "la capture doit être une image de la médiathèque du projet")
        shot = media_mod.path_for(request.app.state.settings.data_dir, m["token"], m["ext"])
    spec = visuals.Spec(template=body.template, format=body.format, title=body.title, subtitle=body.subtitle,
                        badge=body.badge, footer=body.footer, color=body.color or project["color"], screenshot=shot)
    try:
        return await asyncio.to_thread(visuals.render, spec)
    except visuals.VisualError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/projects/{project_id}/visuals/preview")
async def preview(project_id: int, body: VisualIn, request: Request, user=Depends(current_user),
                  conn=Depends(get_conn)):
    img = await _render(conn, request, project_id, body)
    buf = io.BytesIO()
    await asyncio.to_thread(lambda: visuals.preview(img).save(buf, "JPEG", quality=85))
    return Response(buf.getvalue(), media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.post("/projects/{project_id}/visuals", status_code=201)
async def create(project_id: int, body: VisualIn, request: Request, user=Depends(current_user),
                 conn=Depends(get_conn)):
    img = await _render(conn, request, project_id, body)
    fd, tmp = tempfile.mkstemp(prefix="tamtam-visuel-", suffix=".png")
    os.close(fd)
    try:
        # PNG sans perte : la médiathèque le convertit une seule fois en JPEG (format exigé par Instagram)
        await asyncio.to_thread(img.save, tmp, "PNG")
        info = await asyncio.to_thread(media_mod.store, Path(tmp), request.app.state.settings.data_dir)
    except media_mod.MediaError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        Path(tmp).unlink(missing_ok=True)
    name = f"visuel-{body.template}-{body.format}.jpg"
    row = await fetchone(conn, f"INSERT INTO media(project_id, token, ext, filename, mime, kind, size, width, height, "
                               f"created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING {MEDIA_COLS}",
                         (project_id, info["token"], info["ext"], name, info["mime"], info["kind"], info["size"],
                          info["width"], info["height"], user["id"]))
    await conn.commit()
    return media_out(row)
