"""Connexion, déconnexion, profil et gestion des utilisateurs (administrateur)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from .. import security
from .common import admin_user, current_user, fetchall, fetchone, get_conn, update_row

router = APIRouter()


class LoginIn(BaseModel):
    email: str = Field(max_length=200)
    password: str = Field(max_length=200)


@router.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response, conn=Depends(get_conn)):
    ip = security.client_ip(request)
    if not request.app.state.limiter.allow(ip):
        raise HTTPException(429, "trop de tentatives, réessayez dans quelques minutes")
    user = await fetchone(conn, "SELECT id, password_hash, active, session_version FROM users WHERE email=%s",
                          (body.email.strip().lower(),))
    valid = security.check_password_constant_time(body.password, user["password_hash"] if user else None)
    if not valid or not user["active"]:
        raise HTTPException(401, "adresse ou mot de passe incorrect")
    security.set_session_cookie(response, request, user["id"], user["session_version"],
                                request.app.state.settings.session_secret)
    return {"ok": True}


@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(security.COOKIE_NAME, path="/")
    return {"ok": True}


@router.post("/auth/logout-all")
async def logout_all(response: Response, user=Depends(current_user), conn=Depends(get_conn)):
    """Invalide toutes les sessions de l'utilisateur (tous appareils), y compris celle-ci."""
    await conn.execute("UPDATE users SET session_version=session_version+1 WHERE id=%s", (user["id"],))
    await conn.commit()
    response.delete_cookie(security.COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/auth/me")
async def me(user=Depends(current_user)):
    return user


class ProfileIn(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    current_password: str | None = Field(default=None, max_length=200)
    new_password: str | None = Field(default=None, max_length=200)


@router.patch("/auth/me")
async def update_me(body: ProfileIn, request: Request, response: Response, user=Depends(current_user),
                    conn=Depends(get_conn)):
    data = body.model_dump(exclude_unset=True)
    if body.new_password is not None:
        row = await fetchone(conn, "SELECT password_hash FROM users WHERE id=%s", (user["id"],))
        if not body.current_password or not security.check_password(body.current_password, row["password_hash"]):
            raise HTTPException(422, "mot de passe actuel incorrect")
        if len(body.new_password) < security.MIN_PASSWORD:
            raise HTTPException(422, f"le mot de passe doit faire au moins {security.MIN_PASSWORD} caractères")
        data["password_hash"] = security.hash_password(body.new_password)
    await update_row(conn, "users", user["id"], data, {"name", "password_hash"})
    if "password_hash" in data:  # les autres appareils sont déconnectés, celui-ci reçoit un nouveau cookie
        row = await fetchone(conn, "UPDATE users SET session_version=session_version+1 WHERE id=%s "
                                   "RETURNING session_version", (user["id"],))
        security.set_session_cookie(response, request, user["id"], row["session_version"],
                                    request.app.state.settings.session_secret)
    await conn.commit()
    return await fetchone(conn, "SELECT id, email, name, is_admin, active FROM users WHERE id=%s",
                          (user["id"],))


@router.get("/users")
async def list_users(user=Depends(current_user), conn=Depends(get_conn)):
    """Liste courte pour les menus « attribuer à » (utilisateurs actifs)."""
    return await fetchall(conn, "SELECT id, name, email FROM users WHERE active ORDER BY name, email")


# --- Administration des utilisateurs

class UserIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    name: str = Field(default="", max_length=120)
    password: str = Field(max_length=200)
    is_admin: bool = False


class UserPatch(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    is_admin: bool | None = None
    active: bool | None = None
    password: str | None = Field(default=None, max_length=200)


@router.get("/admin/users")
async def admin_list_users(admin=Depends(admin_user), conn=Depends(get_conn)):
    return await fetchall(conn, "SELECT id, email, name, is_admin, active, created_at "
                                "FROM users ORDER BY active DESC, name, email")


@router.post("/admin/users", status_code=201)
async def admin_create_user(body: UserIn, admin=Depends(admin_user), conn=Depends(get_conn)):
    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(422, "adresse e-mail invalide")
    if len(body.password) < security.MIN_PASSWORD:
        raise HTTPException(422, f"le mot de passe doit faire au moins {security.MIN_PASSWORD} caractères")
    if await fetchone(conn, "SELECT 1 FROM users WHERE email=%s", (email,)):
        raise HTTPException(409, "un utilisateur existe déjà avec cette adresse")
    row = await fetchone(conn, "INSERT INTO users(email, name, password_hash, is_admin) VALUES (%s,%s,%s,%s) "
                               "RETURNING id, email, name, is_admin, active",
                         (email, body.name.strip(), security.hash_password(body.password), body.is_admin))
    await conn.commit()
    return row


@router.patch("/admin/users/{user_id}")
async def admin_update_user(user_id: int, body: UserPatch, request: Request, admin=Depends(admin_user),
                            conn=Depends(get_conn)):
    target = await fetchone(conn, "SELECT id, email FROM users WHERE id=%s", (user_id,))
    if not target:
        raise HTTPException(404, "utilisateur introuvable")
    data = body.model_dump(exclude_unset=True)
    if target["email"] == request.app.state.settings.admin_email and (
            data.get("is_admin") is False or data.get("active") is False):
        raise HTTPException(422, "le compte administrateur principal ne peut pas être désactivé ni rétrogradé")
    if user_id == admin["id"] and (data.get("is_admin") is False or data.get("active") is False):
        raise HTTPException(422, "vous ne pouvez pas retirer vos propres droits")
    if "password" in data:
        if len(data["password"] or "") < security.MIN_PASSWORD:
            raise HTTPException(422, f"le mot de passe doit faire au moins {security.MIN_PASSWORD} caractères")
        data["password_hash"] = security.hash_password(data.pop("password"))
    await update_row(conn, "users", user_id, data, {"name", "is_admin", "active", "password_hash"})
    if "password_hash" in data or data.get("active") is False:  # coupe les sessions ouvertes de cette personne
        await conn.execute("UPDATE users SET session_version=session_version+1 WHERE id=%s", (user_id,))
    await conn.commit()
    return await fetchone(conn, "SELECT id, email, name, is_admin, active FROM users WHERE id=%s",
                          (user_id,))
