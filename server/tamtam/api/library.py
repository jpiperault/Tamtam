"""Bibliothèque du projet : groupes de hashtags, signatures et textes réutilisables, insérés dans un post en un clic."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .common import current_user, fetchall, fetchone, get_conn, project_or_404

router = APIRouter()
MAX_PER_PROJECT = 200


class SnippetIn(BaseModel):
    kind: str = Field(pattern="^(hashtags|signature|text)$")
    name: str = Field(min_length=1, max_length=80)
    body: str = Field(min_length=1, max_length=5000)


def _clean(body: SnippetIn) -> tuple[str, str]:
    text = body.body.strip()
    if body.kind == "hashtags":
        # « appli, #ios android » → « #appli #ios #android »
        tags = [t.strip().lstrip("#") for t in text.replace(",", " ").split()]
        tags = [t for t in dict.fromkeys(tags) if t]
        if not tags:
            raise HTTPException(422, "indiquez au moins un hashtag")
        text = " ".join("#" + t for t in tags)
    if not text:
        raise HTTPException(422, "le texte est vide")
    return body.name.strip(), text


@router.get("/projects/{project_id}/snippets")
async def list_snippets(project_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    await project_or_404(conn, project_id)
    return await fetchall(conn, "SELECT * FROM snippets WHERE project_id=%s ORDER BY kind, lower(name)", (project_id,))


@router.post("/projects/{project_id}/snippets", status_code=201)
async def add_snippet(project_id: int, body: SnippetIn, user=Depends(current_user), conn=Depends(get_conn)):
    await project_or_404(conn, project_id)
    n = await fetchone(conn, "SELECT count(*)::int AS n FROM snippets WHERE project_id=%s", (project_id,))
    if n["n"] >= MAX_PER_PROJECT:
        raise HTTPException(422, f"{MAX_PER_PROJECT} éléments au plus par projet")
    name, text = _clean(body)
    row = await fetchone(conn, "INSERT INTO snippets(project_id, kind, name, body) VALUES (%s,%s,%s,%s) RETURNING *",
                         (project_id, body.kind, name, text))
    await conn.commit()
    return row


@router.put("/snippets/{snippet_id}")
async def update_snippet(snippet_id: int, body: SnippetIn, user=Depends(current_user), conn=Depends(get_conn)):
    name, text = _clean(body)
    row = await fetchone(conn, "UPDATE snippets SET kind=%s, name=%s, body=%s, updated_at=now() WHERE id=%s "
                               "RETURNING *", (body.kind, name, text, snippet_id))
    if not row:
        raise HTTPException(404, "élément introuvable")
    await conn.commit()
    return row


@router.delete("/snippets/{snippet_id}")
async def delete_snippet(snippet_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    if not await fetchone(conn, "DELETE FROM snippets WHERE id=%s RETURNING id", (snippet_id,)):
        raise HTTPException(404, "élément introuvable")
    await conn.commit()
    return {"ok": True}
