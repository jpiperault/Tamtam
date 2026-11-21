"""Outils partagés par les routes : connexion, utilisateur courant, requêtes."""
from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request

from .. import security


async def get_conn(request: Request):
    async with request.app.state.pool.connection() as conn:
        yield conn


async def current_user(request: Request, conn=Depends(get_conn)) -> dict:
    token = request.cookies.get(security.COOKIE_NAME)
    parsed = security.read_token(token, request.app.state.settings.session_secret) if token else None
    if parsed is None:
        raise HTTPException(401, "connexion requise")
    uid, version = parsed
    cur = await conn.execute("SELECT id, email, name, is_admin, active, session_version FROM users WHERE id=%s", (uid,))
    user = await cur.fetchone()
    if not user or not user["active"] or user["session_version"] != version:
        raise HTTPException(401, "connexion requise")
    del user["session_version"]
    return user


async def admin_user(user: dict = Depends(current_user)) -> dict:
    if not user["is_admin"]:
        raise HTTPException(403, "réservé aux administrateurs")
    return user


async def fetchall(conn, sql: str, params: Any = ()) -> list[dict]:
    cur = await conn.execute(sql, params)
    return await cur.fetchall()


async def fetchone(conn, sql: str, params: Any = ()) -> dict | None:
    cur = await conn.execute(sql, params)
    return await cur.fetchone()


async def update_row(conn, table: str, row_id: int, data: dict, allowed: set[str]) -> None:
    """UPDATE partiel limité aux colonnes autorisées (les noms ne viennent jamais du client)."""
    cols = [k for k in data if k in allowed]
    if not cols:
        return
    sets = ", ".join(f"{c}=%s" for c in cols)
    await conn.execute(f"UPDATE {table} SET {sets} WHERE id=%s", [data[c] for c in cols] + [row_id])


async def project_or_404(conn, project_id: int) -> dict:
    row = await fetchone(conn, "SELECT * FROM projects WHERE id=%s", (project_id,))
    if not row:
        raise HTTPException(404, "projet introuvable")
    return row
