"""Rédaction avec Claude : réglages (Administration) et demande de proposition (écran de rédaction)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .. import ai, log
from ..platforms import PLATFORMS
from .common import admin_user, current_user, fetchone, get_conn, project_or_404

router = APIRouter()
_log = log.get("api.ai")

MODELS = [
    {"id": "claude-opus-5-5", "label": "Claude Opus 5.5 (meilleure qualité)"},
    {"id": "claude-sonnet-5-5", "label": "Claude Sonnet 5.5 (plus rapide, moins cher)"},
    {"id": "claude-haiku-5-5", "label": "Claude Haiku 5.5 (le plus économique)"},
]


async def _settings(conn) -> dict:
    row = await fetchone(conn, "SELECT * FROM ai_settings WHERE id=1")
    return row or {"api_key_enc": None, "model": ai.DEFAULT_MODEL, "daily_limit": 50, "updated_at": None}


async def _used_today(conn) -> int:
    row = await fetchone(conn, "SELECT count(*)::int AS n FROM ai_calls WHERE ok AND created_at >= date_trunc('day', now())")
    return row["n"]


@router.get("/ai/status")
async def status(request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    s = await _settings(conn)
    simulated = not s["api_key_enc"] and request.app.state.settings.simulation
    return {"enabled": bool(s["api_key_enc"]) or simulated, "simulated": simulated,
            "used_today": await _used_today(conn), "daily_limit": s["daily_limit"]}


class DraftIn(BaseModel):
    project_id: int
    instructions: str = Field(default="", max_length=4000)
    current_text: str = Field(default="", max_length=10000)
    tone: str = Field(default="", pattern="^(|enthousiaste|pro|decontracte|humour)$")
    platforms: list[str] = Field(default_factory=list, max_length=4)
    media_kinds: list[str] = Field(default_factory=list, max_length=35)
    has_link: bool = False


@router.post("/ai/draft")
async def make_draft(body: DraftIn, request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    project = await project_or_404(conn, body.project_id)
    platforms = [p for p in PLATFORMS if p in body.platforms]
    if not platforms:
        raise HTTPException(422, "choisissez au moins un compte avant de demander à Claude")
    if not body.instructions.strip() and not body.current_text.strip():
        raise HTTPException(422, "dites à Claude ce que vous voulez annoncer, ou écrivez un premier jet à améliorer")
    kinds = [k for k in body.media_kinds if k in ("image", "video")]
    s = await _settings(conn)
    if not s["api_key_enc"]:
        if not request.app.state.settings.simulation:
            raise HTTPException(409, "Claude n'est pas configuré : un administrateur doit saisir la clé API dans "
                                     "Administration")
        d = ai.simulated_draft(project, body.instructions, body.current_text, platforms)
    else:
        if await _used_today(conn) >= s["daily_limit"]:
            raise HTTPException(429, f"limite de {s['daily_limit']} rédactions par jour atteinte (réglable dans "
                                     "Administration)")
        await conn.commit()  # ne pas garder de transaction ouverte pendant l'appel à Claude
        key = request.app.state.vault.open(s["api_key_enc"])
        try:
            d = await ai.draft(key, s["model"], project, body.instructions, body.current_text, body.tone, platforms,
                               body.has_link, kinds)
        except ai.AIError as exc:
            await conn.execute("INSERT INTO ai_calls(user_id, project_id, model, ok) VALUES (%s,%s,%s,false)",
                               (user["id"], project["id"], s["model"]))
            await conn.commit()
            raise HTTPException(502, str(exc)) from exc
        await conn.execute("INSERT INTO ai_calls(user_id, project_id, model, input_tokens, output_tokens) "
                           "VALUES (%s,%s,%s,%s,%s)", (user["id"], project["id"], d.model, d.input_tokens,
                                                         d.output_tokens))
        await conn.commit()
        _log.info("rédaction Claude : projet %s, %s réseau(x), %s+%s jetons", project["id"], len(platforms),
                  d.input_tokens, d.output_tokens)
    return {"common": d.common, "versions": d.versions, "note": d.note, "model": d.model,
            "too_long": [p for p, t in d.versions.items() if ai.too_long(p, t, body.has_link)]}


@router.get("/admin/ai")
async def get_admin(user=Depends(admin_user), conn=Depends(get_conn)):
    s = await _settings(conn)
    month = await fetchone(conn, """SELECT count(*)::int AS calls, COALESCE(sum(input_tokens),0)::bigint AS input_tokens,
        COALESCE(sum(output_tokens),0)::bigint AS output_tokens FROM ai_calls
        WHERE ok AND created_at >= date_trunc('month', now())""")
    return {"has_key": bool(s["api_key_enc"]), "model": s["model"], "daily_limit": s["daily_limit"],
            "updated_at": s["updated_at"], "models": MODELS, "used_today": await _used_today(conn), "month": month}


class AdminIn(BaseModel):
    api_key: str | None = Field(default=None, max_length=300)  # None = garder l'actuelle ; "" = effacer
    model: str = Field(default=ai.DEFAULT_MODEL, pattern=r"^claude-[a-z0-9.-]{1,60}$")
    daily_limit: int = Field(default=50, ge=0, le=10000)


@router.put("/admin/ai")
async def save_admin(body: AdminIn, request: Request, user=Depends(admin_user), conn=Depends(get_conn)):
    vault = request.app.state.vault
    if body.api_key is None:
        await conn.execute("INSERT INTO ai_settings(id, model, daily_limit) VALUES (1,%s,%s) ON CONFLICT (id) DO UPDATE "
                           "SET model=EXCLUDED.model, daily_limit=EXCLUDED.daily_limit, updated_at=now()",
                           (body.model, body.daily_limit))
    else:
        key = body.api_key.strip()
        if key and not key.startswith("sk-ant-"):
            raise HTTPException(422, "une clé API Claude commence par sk-ant-")
        await conn.execute("INSERT INTO ai_settings(id, api_key_enc, model, daily_limit) VALUES (1,%s,%s,%s) "
                           "ON CONFLICT (id) DO UPDATE SET api_key_enc=EXCLUDED.api_key_enc, model=EXCLUDED.model, "
                           "daily_limit=EXCLUDED.daily_limit, updated_at=now()",
                           (vault.seal(key) if key else None, body.model, body.daily_limit))
    await conn.commit()
    return {"ok": True}


@router.post("/admin/ai/test")
async def test_key(request: Request, user=Depends(admin_user), conn=Depends(get_conn)):
    s = await _settings(conn)
    if not s["api_key_enc"]:
        raise HTTPException(409, "aucune clé enregistrée")
    await conn.commit()
    try:
        model = await ai.check_key(request.app.state.vault.open(s["api_key_enc"]), s["model"])
    except ai.AIError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"ok": True, "model": model}
