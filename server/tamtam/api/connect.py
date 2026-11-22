"""Connexion des comptes sociaux (OAuth) et gestion des comptes connectés."""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb

from .. import log, platforms, worker
from ..platforms import AuthExpired, PublishError
from .common import current_user, fetchall, fetchone, get_conn, project_or_404

router = APIRouter()
_log = log.get("connect")
ACCOUNT_COLS = ("id, project_id, platform, external_id, name, handle, avatar_url, expires_at, meta, simulated, "
                "status, last_error, created_at")


def redirect_uri(request: Request, provider: str) -> str:
    return f"{request.app.state.settings.public_url}/api/v1/connect/{provider}/callback"


def _back(message: str = "", ok: bool = True, choose: str = "") -> RedirectResponse:
    """Retour vers la page Comptes de l'interface, avec un message."""
    frag = "#/comptes"
    params = []
    if message:
        params.append(("ok" if ok else "err") + "=" + quote(message))
    if choose:
        params.append("choose=" + choose)
    if params:
        frag += "?" + "&".join(params)
    return RedirectResponse("/" + frag, status_code=303)


@router.get("/connect/providers")
async def providers(request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    rows = {r["provider"]: r for r in await fetchall(conn, "SELECT provider, client_id FROM app_credentials")}
    return {"simulation": request.app.state.settings.simulation,
            "providers": {p: {"label": platforms.PROVIDER_LABELS[p], "configured": bool(rows.get(p, {}).get("client_id"))}
                          for p in platforms.PROVIDERS}}


class StartIn(BaseModel):
    project_id: int
    demo: bool = False


@router.post("/connect/{provider}/start")
async def start(provider: str, body: StartIn, request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    if provider not in platforms.PROVIDERS:
        raise HTTPException(404, "réseau inconnu")
    await project_or_404(conn, body.project_id)
    s = request.app.state.settings
    if body.demo:
        if not s.simulation:
            raise HTTPException(422, "les comptes de démonstration ne sont permis qu'en mode simulation")
        pid = await _save_pending(conn, request, body.project_id, user["id"], platforms.demo_candidates(provider))
        await conn.commit()
        return {"choose": pid}
    creds = await fetchone(conn, "SELECT client_id FROM app_credentials WHERE provider=%s", (provider,))
    if not creds or not creds["client_id"]:
        raise HTTPException(422, f"l'application {platforms.PROVIDER_LABELS[provider]} n'est pas encore configurée : "
                                 "un administrateur doit saisir ses identifiants dans Administration")
    state = secrets.token_urlsafe(24)
    verifier, _ = platforms.pkce()
    await conn.execute("DELETE FROM oauth_states WHERE created_at < now() - interval '30 minutes'")
    await conn.execute("INSERT INTO oauth_states(state, provider, project_id, user_id, code_verifier) "
                       "VALUES (%s,%s,%s,%s,%s)", (state, provider, body.project_id, user["id"], verifier))
    await conn.commit()
    stats = await fetchone(conn, "SELECT value FROM site_settings WHERE key=%s", (f"stats_scopes_{provider}",))
    url = platforms.authorize_url(provider, creds["client_id"], redirect_uri(request, provider), state, verifier,
                                  s.graph_version, bool(stats and stats["value"] == "1"))
    return {"url": url}


async def _save_pending(conn, request, project_id: int, user_id: int, candidates: list[dict]) -> str:
    pid = secrets.token_urlsafe(16)
    await conn.execute("DELETE FROM pending_connections WHERE created_at < now() - interval '1 hour'")
    await conn.execute("INSERT INTO pending_connections(id, project_id, user_id, candidates) VALUES (%s,%s,%s,%s)",
                       (pid, project_id, user_id, request.app.state.vault.seal(json.dumps(candidates))))
    return pid


@router.get("/connect/{provider}/callback")
async def callback(provider: str, request: Request, conn=Depends(get_conn)):
    """Retour du réseau après autorisation (navigation du navigateur, pas un appel de l'interface)."""
    q = request.query_params
    state = q.get("state", "")
    row = await fetchone(conn, "DELETE FROM oauth_states WHERE state=%s AND provider=%s "
                               "AND created_at > now() - interval '30 minutes' RETURNING *", (state, provider))
    await conn.commit()
    if q.get("error"):
        reason = q.get("error_description") or q.get("error_reason") or q.get("error")
        _log.info("connexion %s : le réseau a renvoyé une erreur (%s)", provider, reason)
        return _back(f"Connexion annulée sur {platforms.PROVIDER_LABELS[provider]} ({reason}).", ok=False)
    if not row:
        why = "sans état" if not state else "état inconnu, déjà utilisé ou de plus de 30 minutes"
        _log.warning("connexion %s : retour refusé (%s, code %s)", provider, why, "présent" if q.get("code") else "absent")
        return _back("Connexion expirée ou invalide, recommencez depuis la page Comptes.", ok=False)
    code = q.get("code")
    if not code:
        return _back("Le réseau n'a pas renvoyé d'autorisation.", ok=False)
    creds = await fetchone(conn, "SELECT client_id, client_secret_enc FROM app_credentials WHERE provider=%s",
                           (provider,))
    vault = request.app.state.vault
    try:
        cands = await platforms.exchange(provider, creds["client_id"], vault.open(creds["client_secret_enc"]),
                                         redirect_uri(request, provider), code, row["code_verifier"],
                                         request.app.state.settings.graph_version)
    except PublishError as exc:
        _log.warning("connexion %s refusée : %s", provider, exc)
        return _back(f"Connexion refusée : {exc}", ok=False)
    except Exception as exc:
        _log.exception("connexion %s : erreur inattendue", provider)
        return _back(f"Connexion impossible ({type(exc).__name__}). Réessayez dans un instant.", ok=False)
    if not cands:
        hint = (" Vérifiez que vous gérez au moins une Page Facebook et que le compte Instagram est Professionnel et "
                "relié à cette Page." if provider == "meta" else "")
        return _back("Aucun compte trouvé." + hint, ok=False)
    pid = await _save_pending(conn, request, row["project_id"], row["user_id"], cands)
    await conn.commit()
    return _back(choose=pid)


def _public(c: dict, i: int) -> dict:
    return {"key": i, "platform": c["platform"], "name": c["name"], "handle": c.get("handle", ""),
            "avatar_url": c.get("avatar_url", ""), "detail": c.get("meta", {}).get("page_name", ""),
            "simulated": bool(c.get("simulated"))}


async def _load_pending(conn, request, pid: str, user: dict) -> tuple[dict, list[dict]]:
    row = await fetchone(conn, "SELECT * FROM pending_connections WHERE id=%s AND user_id=%s "
                               "AND created_at > now() - interval '1 hour'", (pid, user["id"]))
    if not row:
        raise HTTPException(404, "choix expiré : relancez la connexion")
    raw = request.app.state.vault.open(row["candidates"])
    return row, json.loads(raw or "[]")


@router.get("/connect/pending/{pid}")
async def pending(pid: str, request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    row, cands = await _load_pending(conn, request, pid, user)
    proj = await project_or_404(conn, row["project_id"])
    return {"project": {"id": proj["id"], "name": proj["name"]}, "candidates": [_public(c, i) for i, c in enumerate(cands)]}


class ChooseIn(BaseModel):
    keys: list[int] = Field(max_length=200)


@router.post("/connect/pending/{pid}")
async def choose(pid: str, body: ChooseIn, request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    row, cands = await _load_pending(conn, request, pid, user)
    vault = request.app.state.vault
    now = datetime.now(timezone.utc)
    added = 0
    for k in sorted(set(body.keys)):
        if not 0 <= k < len(cands):
            continue
        c = cands[k]
        exp = now + timedelta(seconds=int(c["expires_in"])) if c.get("expires_in") else None
        rexp = now + timedelta(seconds=int(c["refresh_expires_in"])) if c.get("refresh_expires_in") else None
        await conn.execute(
            "INSERT INTO social_accounts(project_id, platform, external_id, name, handle, avatar_url, access_token_enc, "
            " refresh_token_enc, expires_at, refresh_expires_at, meta, simulated, connected_by) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (project_id, platform, external_id) DO UPDATE SET name=EXCLUDED.name, handle=EXCLUDED.handle, "
            " avatar_url=EXCLUDED.avatar_url, access_token_enc=EXCLUDED.access_token_enc, "
            " refresh_token_enc=EXCLUDED.refresh_token_enc, expires_at=EXCLUDED.expires_at, "
            " refresh_expires_at=EXCLUDED.refresh_expires_at, "
            " meta=social_accounts.meta || EXCLUDED.meta, status='ok', last_error='', updated_at=now()",
            (row["project_id"], c["platform"], c["external_id"], c["name"], c.get("handle", ""),
             c.get("avatar_url", ""), vault.seal(c["access_token"]), vault.seal(c.get("refresh_token")), exp, rexp,
             Jsonb(c.get("meta", {})), bool(c.get("simulated")), user["id"]))
        added += 1
    await conn.execute("DELETE FROM pending_connections WHERE id=%s", (pid,))
    await conn.commit()
    return {"added": added}


# --- Comptes connectés

@router.get("/projects/{project_id}/accounts")
async def list_accounts(project_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    await project_or_404(conn, project_id)
    return await fetchall(conn, f"SELECT {ACCOUNT_COLS} FROM social_accounts WHERE project_id=%s "
                                "ORDER BY array_position(ARRAY['instagram','facebook','x','tiktok'], platform), name",
                          (project_id,))


class AccountPatch(BaseModel):
    privacy: str | None = Field(default=None, pattern="^(PUBLIC_TO_EVERYONE|MUTUAL_FOLLOW_FRIENDS|FOLLOWER_OF_CREATOR|SELF_ONLY)$")


@router.patch("/accounts/{account_id}")
async def patch_account(account_id: int, body: AccountPatch, user=Depends(current_user), conn=Depends(get_conn)):
    acc = await fetchone(conn, "SELECT id, platform FROM social_accounts WHERE id=%s", (account_id,))
    if not acc:
        raise HTTPException(404, "compte introuvable")
    if body.privacy is not None:
        if acc["platform"] != "tiktok":
            raise HTTPException(422, "la visibilité ne se règle que pour TikTok")
        await conn.execute("UPDATE social_accounts SET meta = meta || %s, updated_at=now() WHERE id=%s",
                           (Jsonb({"privacy": body.privacy}), account_id))
    await conn.commit()
    return await fetchone(conn, f"SELECT {ACCOUNT_COLS} FROM social_accounts WHERE id=%s", (account_id,))


SIMULATED_CREATOR = {"creator_nickname": "Compte démo", "creator_username": "demo", "creator_avatar_url": "",
                     "privacy_level_options": ["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"],
                     "comment_disabled": False, "duet_disabled": False, "stitch_disabled": True,
                     "max_video_post_duration_sec": 600}


@router.get("/accounts/{account_id}/tiktok-creator")
async def tiktok_creator(account_id: int, request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    """Infos du créateur TikTok à afficher au moment d'écrire le post (lues à chaque ouverture, comme l'exige TikTok)."""
    acc = await fetchone(conn, "SELECT id, platform, simulated FROM social_accounts WHERE id=%s", (account_id,))
    if not acc or acc["platform"] != "tiktok":
        raise HTTPException(404, "compte TikTok introuvable")
    if acc["simulated"]:
        return {"can_post": True, **SIMULATED_CREATOR}
    await conn.commit()
    try:
        full = await worker.account_with_token(request.app.state.pool, request.app.state.vault, account_id)
        info = await platforms.tiktok.creator_info(full["access_token"])
    except (PublishError, AuthExpired) as exc:
        return {"can_post": False, "message": str(exc)}
    return {"can_post": True, **{k: info.get(k) for k in SIMULATED_CREATOR}}


@router.post("/accounts/{account_id}/test")
async def test_account(account_id: int, request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    """Vérifie que l'autorisation est toujours valable (renouvelle le jeton X / TikTok au besoin)."""
    from ..platforms import meta, tiktok

    s = request.app.state.settings
    try:
        acc = await worker.account_with_token(request.app.state.pool, request.app.state.vault, account_id)
        if not acc["simulated"]:
            if acc["platform"] in ("facebook", "instagram"):
                await meta.check_token(acc, s.graph_version)
            elif acc["platform"] == "tiktok":
                await tiktok.creator_info(acc["access_token"])
        await conn.execute("UPDATE social_accounts SET status='ok', last_error='' WHERE id=%s", (account_id,))
        await conn.commit()
        return {"ok": True, "message": "Autorisation valable."}
    except PublishError as exc:
        expired = isinstance(exc, platforms.AuthExpired)
        await conn.execute("UPDATE social_accounts SET status=%s, last_error=%s WHERE id=%s",
                           ("expired" if expired else "error", str(exc)[:500], account_id))
        await conn.commit()
        return {"ok": False, "message": str(exc)}


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    """Retire le compte de Tamtam (les jetons sont effacés ; les posts déjà parus restent sur le réseau)."""
    cur = await conn.execute("DELETE FROM social_accounts WHERE id=%s", (account_id,))
    if cur.rowcount == 0:
        raise HTTPException(404, "compte introuvable")
    await conn.commit()
    return {"ok": True}
