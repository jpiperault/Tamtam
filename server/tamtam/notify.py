"""Alertes Telegram : post en échec, compte à reconnecter, et (au choix) post publié.

Le bot se crée chez @BotFather ; son jeton est saisi dans Administration (chiffré avec TOKEN_KEY, table
site_settings). Les destinataires sont les conversations qui ont écrit au bot, choisies dans Administration.
Un envoi raté est seulement noté dans le journal : une alerte ne doit jamais bloquer la publication.
"""
from __future__ import annotations

import asyncio

from . import log
from .platforms.base import LABELS, client

_log = log.get("notify")
API = "https://api.telegram.org"
KINDS = {"failures": "alert_failures", "accounts": "alert_accounts", "success": "alert_success"}
DEFAULTS = {"alert_failures": "1", "alert_accounts": "1", "alert_success": "0"}
_tasks: set[asyncio.Task] = set()


class TelegramError(Exception):
    pass


async def settings(conn) -> dict:
    cur = await conn.execute("SELECT key, value FROM site_settings WHERE key LIKE 'telegram_%' OR key LIKE 'alert_%'")
    out = dict(DEFAULTS)
    out.update({r["key"]: r["value"] for r in await cur.fetchall()})
    return out


def chats(conf: dict) -> list[dict]:
    """« id|nom » séparés par des retours à la ligne → [{id, name}]."""
    out = []
    for line in (conf.get("telegram_chats") or "").splitlines():
        cid, _, name = line.partition("|")
        if cid.strip():
            out.append({"id": cid.strip(), "name": name.strip()})
    return out


async def call(token: str, method: str, payload: dict | None = None) -> dict:
    async with client(20) as c:
        try:
            r = await c.post(f"{API}/bot{token}/{method}", json=payload or {})
        except Exception as exc:  # noqa: BLE001 - réseau
            raise TelegramError("Telegram injoignable depuis le serveur") from exc
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code == 401 or data.get("error_code") == 401:
        raise TelegramError("jeton du bot refusé par Telegram : vérifiez-le auprès de @BotFather")
    if not data.get("ok"):
        raise TelegramError(f"Telegram a refusé la demande : {data.get('description') or r.status_code}")
    return data["result"]


async def send_to_all(token: str, chat_list: list[dict], text: str) -> int:
    sent = 0
    for ch in chat_list:
        try:
            await call(token, "sendMessage", {"chat_id": ch["id"], "text": text[:4000],
                                               "disable_web_page_preview": True})
            sent += 1
        except TelegramError as exc:
            _log.warning("alerte Telegram non envoyée à %s : %s", ch.get("name") or ch["id"], exc)
    return sent


async def _send(pool, vault, kind: str, text: str) -> None:
    try:
        async with pool.connection() as conn:
            conf = await settings(conn)
        if conf.get(KINDS[kind]) != "1" or not conf.get("telegram_token_enc"):
            return
        token = vault.open(conf["telegram_token_enc"])
        if token:
            await send_to_all(token, chats(conf), text)
    except Exception:  # noqa: BLE001 - une alerte ne doit jamais casser la publication
        _log.exception("alerte Telegram impossible")


def fire(app, kind: str, text: str) -> None:
    """Envoie l'alerte en tâche de fond (sans attendre)."""
    task = asyncio.create_task(_send(app.state.pool, app.state.vault, kind, text))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


def failure_text(public_url: str, platform: str, account: str, project: str, error: str) -> str:
    return (f"❌ Tamtam : échec de publication sur {LABELS.get(platform, platform)} ({account}), projet {project}.\n"
            f"{error}\n{public_url}/#/?status=problems")


def account_text(public_url: str, platform: str, account: str, project: str, error: str) -> str:
    return (f"⚠️ Tamtam : le compte {LABELS.get(platform, platform)} « {account} » (projet {project}) doit être "
            f"reconnecté.\n{error}\n{public_url}/#/comptes")


def success_text(platform: str, account: str, project: str, url: str) -> str:
    return f"✅ Tamtam : publié sur {LABELS.get(platform, platform)} ({account}), projet {project}.{chr(10) + url if url else ''}"
