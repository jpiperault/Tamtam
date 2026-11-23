"""Nouvelles versions : sources suivies par projet (dépôt GitHub, appli App Store) et brouillons d'annonce."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .. import releases
from .common import current_user, fetchall, fetchone, get_conn, project_or_404

router = APIRouter()
COLS = ("id", "project_id", "kind", "ref", "country", "label", "instructions", "enabled", "last_version",
        "last_seen_at", "last_checked_at", "last_error", "last_post_id", "created_at")


def _out(r: dict) -> dict:
    url = (f"https://github.com/{r['ref']}/releases" if r["kind"] == "github"
           else f"https://apps.apple.com/{r['country']}/app/id{r['ref']}" if r["ref"].isdigit() else "")
    return {**{k: r[k] for k in COLS}, "has_token": bool(r.get("token_enc")), "url": url}


async def _source(conn, source_id: int) -> dict:
    row = await fetchone(conn, "SELECT * FROM release_sources WHERE id=%s", (source_id,))
    if not row:
        raise HTTPException(404, "source introuvable")
    return row


@router.get("/projects/{project_id}/releases")
async def list_sources(project_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    await project_or_404(conn, project_id)
    return [_out(r) for r in await fetchall(conn, "SELECT * FROM release_sources WHERE project_id=%s ORDER BY id",
                                            (project_id,))]


class SourceIn(BaseModel):
    kind: str = Field(pattern="^(github|appstore)$")
    ref: str = Field(min_length=1, max_length=300)
    country: str = Field(default="fr", pattern="^[a-zA-Z]{2}$")
    token: str = Field(default="", max_length=300)
    instructions: str = Field(default="", max_length=1000)


@router.post("/projects/{project_id}/releases", status_code=201)
async def add_source(project_id: int, body: SourceIn, request: Request, user=Depends(current_user),
                     conn=Depends(get_conn)):
    """Ajoute une source après l'avoir lue une fois : sa version actuelle sert de point de départ."""
    await project_or_404(conn, project_id)
    try:
        ref = releases.normalize(body.kind, body.ref)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    country = body.country.lower()
    if await fetchone(conn, "SELECT 1 FROM release_sources WHERE project_id=%s AND kind=%s AND ref=%s",
                      (project_id, body.kind, ref)):
        raise HTTPException(409, "cette source est déjà suivie pour ce projet")
    token = body.token.strip() if body.kind == "github" else ""
    await conn.commit()
    try:
        rel = (await releases.fetch_github(ref, token or None) if body.kind == "github"
               else await releases.fetch_appstore(ref, country))
    except releases.ReleaseError as exc:
        raise HTTPException(422, str(exc)) from exc
    vault = request.app.state.vault
    row = await fetchone(conn, """
        INSERT INTO release_sources(project_id, kind, ref, country, token_enc, label, instructions, last_version,
                                    last_seen_at, last_checked_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,now()) RETURNING *""",
                         (project_id, body.kind, ref, country, vault.seal(token) if token else None,
                          rel.name if body.kind == "appstore" else ref, body.instructions.strip(), rel.version,
                          rel.published_at))
    await conn.commit()
    return _out(row)


class SourcePatch(BaseModel):
    enabled: bool | None = None
    instructions: str | None = Field(default=None, max_length=1000)
    country: str | None = Field(default=None, pattern="^[a-zA-Z]{2}$")
    token: str | None = Field(default=None, max_length=300)   # None = garder ; "" = effacer


@router.patch("/releases/{source_id}")
async def patch_source(source_id: int, body: SourcePatch, request: Request, user=Depends(current_user),
                       conn=Depends(get_conn)):
    src = await _source(conn, source_id)
    if body.enabled is not None:
        await conn.execute("UPDATE release_sources SET enabled=%s WHERE id=%s", (body.enabled, source_id))
    if body.instructions is not None:
        await conn.execute("UPDATE release_sources SET instructions=%s WHERE id=%s",
                           (body.instructions.strip(), source_id))
    if body.country is not None and src["kind"] == "appstore":
        await conn.execute("UPDATE release_sources SET country=%s WHERE id=%s", (body.country.lower(), source_id))
    if body.token is not None and src["kind"] == "github":
        t = body.token.strip()
        await conn.execute("UPDATE release_sources SET token_enc=%s WHERE id=%s",
                           (request.app.state.vault.seal(t) if t else None, source_id))
    await conn.commit()
    return _out(await _source(conn, source_id))


@router.delete("/releases/{source_id}")
async def delete_source(source_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    if not await fetchone(conn, "DELETE FROM release_sources WHERE id=%s RETURNING id", (source_id,)):
        raise HTTPException(404, "source introuvable")
    await conn.commit()
    return {"ok": True}


@router.post("/releases/{source_id}/check")
async def check_source(source_id: int, request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    """Vérifie tout de suite. Une version nouvelle donne un brouillon, comme la vérification automatique."""
    src = await _source(conn, source_id)
    await conn.commit()
    try:
        r = await releases.check_one(request.app, src)
    except releases.ReleaseError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {**r, "source": _out(await _source(conn, source_id))}


@router.post("/releases/{source_id}/draft")
async def draft_now(source_id: int, request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    """Brouillon d'annonce pour la version actuelle (par exemple juste après avoir ajouté la source)."""
    src = await _source(conn, source_id)
    await conn.commit()
    try:
        rel = await releases.fetch(src, request.app.state.vault)
        post_id = await releases.make_draft(request.app, src, rel, user["id"])
    except releases.ReleaseError as exc:
        raise HTTPException(502 if "configuré" not in str(exc) else 409, str(exc)) from exc
    return {"post_id": post_id, "version": rel.version, "source": _out(await _source(conn, source_id))}
