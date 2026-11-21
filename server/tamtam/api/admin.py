"""Administration : identifiants des applications développeur (Meta, X, TikTok) et état général."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .. import __version__, datadir, platforms
from .common import admin_user, current_user, fetchall, get_conn

router = APIRouter()

CALLBACK_HELP = {
    "meta": "developers.facebook.com → Mes apps → votre app → Facebook Login for Business → Paramètres → "
            "« URI de redirection OAuth valides »",
    "x": "developer.x.com → Projects & Apps → votre app → User authentication settings → Callback URI",
    "tiktok": "developers.tiktok.com → Manage apps → votre app → Login Kit → Redirect URI",
}


@router.get("/admin/apps")
async def list_apps(request: Request, admin=Depends(admin_user), conn=Depends(get_conn)):
    rows = {r["provider"]: r for r in await fetchall(conn, "SELECT * FROM app_credentials")}
    base = request.app.state.settings.public_url
    out = []
    for p in platforms.PROVIDERS:
        r = rows.get(p)
        out.append({"provider": p, "label": platforms.PROVIDER_LABELS[p], "client_id": r["client_id"] if r else "",
                    "has_secret": bool(r and r["client_secret_enc"]), "updated_at": r["updated_at"] if r else None,
                    "redirect_uri": f"{base}/api/v1/connect/{p}/callback", "where": CALLBACK_HELP[p]})
    return {"apps": out, "public_url": base, "media_url_example": f"{base}/m/…"}


class AppIn(BaseModel):
    client_id: str = Field(max_length=300)
    client_secret: str | None = Field(default=None, max_length=500)  # None = garder l'actuel ; "" = effacer


@router.put("/admin/apps/{provider}")
async def save_app(provider: str, body: AppIn, request: Request, admin=Depends(admin_user), conn=Depends(get_conn)):
    if provider not in platforms.PROVIDERS:
        raise HTTPException(404, "réseau inconnu")
    vault = request.app.state.vault
    cid = body.client_id.strip()
    if body.client_secret is None:
        await conn.execute("INSERT INTO app_credentials(provider, client_id) VALUES (%s,%s) ON CONFLICT (provider) "
                           "DO UPDATE SET client_id=EXCLUDED.client_id, updated_at=now()", (provider, cid))
    else:
        sec = body.client_secret.strip()
        await conn.execute("INSERT INTO app_credentials(provider, client_id, client_secret_enc) VALUES (%s,%s,%s) "
                           "ON CONFLICT (provider) DO UPDATE SET client_id=EXCLUDED.client_id, "
                           "client_secret_enc=EXCLUDED.client_secret_enc, updated_at=now()",
                           (provider, cid, vault.seal(sec) if sec else None))
    await conn.commit()
    return {"ok": True}


@router.get("/admin/status")
async def status(request: Request, admin=Depends(admin_user), conn=Depends(get_conn)):
    s = request.app.state.settings
    counts = (await fetchall(conn, """SELECT (SELECT count(*) FROM projects)::int AS projects,
        (SELECT count(*) FROM social_accounts)::int AS accounts,
        (SELECT count(*) FROM social_accounts WHERE status <> 'ok')::int AS accounts_problem,
        (SELECT count(*) FROM posts)::int AS posts,
        (SELECT count(*) FROM media)::int AS media,
        (SELECT COALESCE(sum(size),0)::bigint FROM media) AS media_bytes"""))[0]
    return {"version": __version__, "simulation": s.simulation, "public_url": s.public_url, "timezone": s.timezone,
            "max_upload_mb": s.max_upload_mb, **counts}


@router.get("/docs/guide")
async def guide(request: Request, user=Depends(current_user)):
    text = datadir.read_doc(request.app.state.settings.data_dir, "guide.md")
    if text is None:
        raise HTTPException(404, "guide introuvable")
    return {"markdown": text}
