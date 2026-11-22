"""Administration : identifiants des applications développeur (Meta, X, TikTok) et état général."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .. import __version__, datadir, notify, platforms
from .common import admin_user, current_user, fetchall, get_conn

router = APIRouter()

CALLBACK_HELP = {
    "meta": "developers.facebook.com → Mes apps → votre app → Facebook Login for Business → Paramètres → "
            "« URI de redirection OAuth valides »",
    "x": "developer.x.com → Projects & Apps → votre app → User authentication settings → Callback URI",
    "tiktok": "developers.tiktok.com → Manage apps → votre app → Login Kit → Redirect URI",
    "threads": "developers.facebook.com → votre app Threads → Cas d'utilisation → Accéder à l'API Threads → "
               "Paramètres → « URL de rappel de redirection »",
    "linkedin": "linkedin.com/developers → votre app → Auth → « Authorized redirect URLs for your app »",
    "google": "console.cloud.google.com → API et services → Identifiants → votre ID client OAuth (application Web) → "
              "« URI de redirection autorisés »",
}


@router.get("/admin/apps")
async def list_apps(request: Request, admin=Depends(admin_user), conn=Depends(get_conn)):
    rows = {r["provider"]: r for r in await fetchall(conn, "SELECT * FROM app_credentials")}
    base = request.app.state.settings.public_url
    out = []
    for p in platforms.PROVIDERS:
        if p in platforms.NO_APP:
            continue
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
    if provider not in platforms.PROVIDERS or provider in platforms.NO_APP:
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


# --- Pages légales (éditeur et contact affichés sur /confidentialite, /conditions, /privacy, /terms)

class LegalIn(BaseModel):
    operator: str = Field(default="", max_length=200)
    contact: str = Field(default="", max_length=200)


@router.get("/admin/legal")
async def get_legal(request: Request, admin=Depends(admin_user), conn=Depends(get_conn)):
    rows = {r["key"]: r["value"] for r in await fetchall(conn, "SELECT key, value FROM site_settings WHERE key IN "
                                                               "('legal_operator', 'legal_contact')")}
    base = request.app.state.settings.public_url
    return {"operator": rows.get("legal_operator", ""), "contact": rows.get("legal_contact", ""),
            "urls": {"privacy_fr": f"{base}/confidentialite", "terms_fr": f"{base}/conditions",
                     "privacy_en": f"{base}/privacy", "terms_en": f"{base}/terms"}}


@router.put("/admin/legal")
async def save_legal(body: LegalIn, admin=Depends(admin_user), conn=Depends(get_conn)):
    for key, value in (("legal_operator", body.operator.strip()), ("legal_contact", body.contact.strip())):
        await conn.execute("INSERT INTO site_settings(key, value) VALUES (%s,%s) ON CONFLICT (key) DO UPDATE "
                           "SET value=EXCLUDED.value, updated_at=now()", (key, value))
    await conn.commit()
    return {"ok": True}


# --- Alertes Telegram

async def _set(conn, key: str, value: str) -> None:
    await conn.execute("INSERT INTO site_settings(key, value) VALUES (%s,%s) ON CONFLICT (key) DO UPDATE "
                       "SET value=EXCLUDED.value, updated_at=now()", (key, value))


async def _telegram_token(conn, vault) -> str:
    conf = await notify.settings(conn)
    token = vault.open(conf["telegram_token_enc"]) if conf.get("telegram_token_enc") else None
    if not token:
        raise HTTPException(409, "enregistrez d'abord le jeton du bot")
    return token


@router.get("/admin/telegram")
async def get_telegram(admin=Depends(admin_user), conn=Depends(get_conn)):
    conf = await notify.settings(conn)
    return {"has_token": bool(conf.get("telegram_token_enc")), "bot": conf.get("telegram_bot", ""),
            "chats": notify.chats(conf), **{k: conf.get(v) == "1" for k, v in notify.KINDS.items()}}


class TelegramIn(BaseModel):
    token: str | None = Field(default=None, max_length=200)   # None = garder ; "" = effacer
    chats: list[dict] | None = Field(default=None, max_length=20)
    failures: bool = True
    accounts: bool = True
    success: bool = False
    report: bool = True


@router.put("/admin/telegram")
async def save_telegram(body: TelegramIn, request: Request, admin=Depends(admin_user), conn=Depends(get_conn)):
    vault = request.app.state.vault
    if body.token is not None:
        token = body.token.strip()
        if token:
            await conn.commit()
            try:
                me = await notify.call(token, "getMe")
            except notify.TelegramError as exc:
                raise HTTPException(422, str(exc)) from exc
            await _set(conn, "telegram_token_enc", vault.seal(token))
            await _set(conn, "telegram_bot", me.get("username", ""))
        else:
            await _set(conn, "telegram_token_enc", "")
            await _set(conn, "telegram_bot", "")
            await _set(conn, "telegram_chats", "")
    if body.chats is not None:
        lines = []
        for ch in body.chats:
            cid = str(ch.get("id", "")).strip()
            if cid.lstrip("-").isdigit():
                lines.append(f"{cid}|{str(ch.get('name', ''))[:80].replace(chr(10), ' ')}")
        await _set(conn, "telegram_chats", "\n".join(dict.fromkeys(lines)))
    for kind, key in notify.KINDS.items():
        await _set(conn, key, "1" if getattr(body, kind) else "0")
    await conn.commit()
    return await get_telegram(admin, conn)


@router.post("/admin/telegram/discover")
async def discover_telegram(request: Request, admin=Depends(admin_user), conn=Depends(get_conn)):
    """Conversations qui ont écrit au bot récemment (il faut lui envoyer un message, par exemple /start)."""
    token = await _telegram_token(conn, request.app.state.vault)
    await conn.commit()
    try:
        updates = await notify.call(token, "getUpdates", {"limit": 100, "allowed_updates": ["message", "my_chat_member"]})
    except notify.TelegramError as exc:
        raise HTTPException(502, str(exc)) from exc
    found = {}
    for u in updates:
        msg = u.get("message") or u.get("my_chat_member") or {}
        chat = msg.get("chat") or {}
        if "id" in chat:
            name = chat.get("title") or " ".join(x for x in (chat.get("first_name"), chat.get("last_name")) if x) \
                or chat.get("username") or str(chat["id"])
            found[str(chat["id"])] = {"id": str(chat["id"]), "name": name}
    return {"chats": list(found.values())}


@router.post("/admin/telegram/test")
async def test_telegram(request: Request, admin=Depends(admin_user), conn=Depends(get_conn)):
    token = await _telegram_token(conn, request.app.state.vault)
    chat_list = notify.chats(await notify.settings(conn))
    await conn.commit()
    if not chat_list:
        raise HTTPException(409, "ajoutez au moins un destinataire")
    sent = await notify.send_to_all(token, chat_list, "🥁 Tamtam : test des alertes réussi. Vous serez prévenu ici "
                                                       "des posts en échec et des comptes à reconnecter.")
    if not sent:
        raise HTTPException(502, "aucun message n'a pu être envoyé : vérifiez que chaque destinataire a écrit au bot")
    return {"sent": sent}


class StatsIn(BaseModel):
    scopes_meta: bool = False      # demander read_insights + instagram_manage_insights à la connexion
    scopes_tiktok: bool = False    # demander video.list à la connexion
    scopes_threads: bool = False   # demander threads_manage_insights à la connexion
    linkedin_pages: bool = False   # demander les permissions des Pages d'entreprise LinkedIn
    report_weekly: bool = False    # rapport rédigé par Claude chaque lundi


@router.get("/admin/stats")
async def get_stats_settings(admin=Depends(admin_user), conn=Depends(get_conn)):
    rows = {r["key"]: r["value"] for r in await fetchall(conn, "SELECT key, value FROM site_settings WHERE key IN "
                                                               "('stats_scopes_meta','stats_scopes_tiktok','stats_scopes_threads',"
                                                               "'linkedin_pages','report_weekly')")}
    return {"scopes_meta": rows.get("stats_scopes_meta") == "1", "scopes_tiktok": rows.get("stats_scopes_tiktok") == "1",
            "scopes_threads": rows.get("stats_scopes_threads") == "1", "linkedin_pages": rows.get("linkedin_pages") == "1",
            "report_weekly": rows.get("report_weekly") == "1",
            "scopes": {k: platforms.STATS_SCOPES[k] for k in ("meta", "tiktok", "threads")}}


@router.put("/admin/stats")
async def save_stats_settings(body: StatsIn, admin=Depends(admin_user), conn=Depends(get_conn)):
    await _set(conn, "stats_scopes_meta", "1" if body.scopes_meta else "0")
    await _set(conn, "stats_scopes_tiktok", "1" if body.scopes_tiktok else "0")
    await _set(conn, "stats_scopes_threads", "1" if body.scopes_threads else "0")
    await _set(conn, "linkedin_pages", "1" if body.linkedin_pages else "0")
    await _set(conn, "report_weekly", "1" if body.report_weekly else "0")
    await conn.commit()
    return await get_stats_settings(admin, conn)
