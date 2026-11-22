"""Boîte de réception : commentaires des posts publiés, réponses (proposées par Claude au besoin)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .. import ai, inbox, platforms, worker
from ..platforms import PublishError
from .ai import _settings as ai_settings, _used_today
from .common import current_user, fetchall, fetchone, get_conn, project_or_404

router = APIRouter()

ITEM_SQL = """
    SELECT i.*, t.platform, t.external_url, t.social_account_id, p.id AS post_id, p.project_id,
           left(COALESCE(t.body_override, p.body), 300) AS post_text, a.name AS account_name, a.handle AS account_handle,
           u.name AS replied_by_name
    FROM inbox_items i JOIN post_targets t ON t.id=i.post_target_id JOIN posts p ON p.id=t.post_id
    LEFT JOIN social_accounts a ON a.id=t.social_account_id LEFT JOIN users u ON u.id=i.replied_by"""


def _out(r: dict) -> dict:
    return {k: r[k] for k in ("id", "platform", "author_name", "author_handle", "author_avatar", "text",
                              "commented_at", "status", "reply_text", "reply_error", "replied_at", "replied_by_name",
                              "post_id", "post_text", "external_url", "account_name", "account_handle")}


@router.get("/inbox")
async def list_inbox(project_id: int, status: str = "new", user=Depends(current_user), conn=Depends(get_conn)):
    if status not in ("new", "replied", "done", "all"):
        raise HTTPException(422, "filtre inconnu")
    sf = "" if status == "all" else "AND i.status=%s"
    params = [project_id] + ([] if status == "all" else [status])
    rows = await fetchall(conn, f"{ITEM_SQL} WHERE p.project_id=%s {sf} "
                                "ORDER BY COALESCE(i.commented_at, i.fetched_at) DESC LIMIT 200", params)
    counts = await fetchone(conn, "SELECT count(*) FILTER (WHERE i.status='new')::int AS new FROM inbox_items i "
                                  "JOIN post_targets t ON t.id=i.post_target_id JOIN posts p ON p.id=t.post_id "
                                  "WHERE p.project_id=%s", (project_id,))
    enabled = await inbox.enabled_platforms(conn)
    return {"items": [_out(r) for r in rows], "new": counts["new"], "enabled": enabled}


@router.post("/inbox/refresh")
async def refresh(project_id: int, request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    await project_or_404(conn, project_id)
    await conn.commit()
    return await inbox.collect(request.app, project_id)


async def _item(conn, item_id: int) -> dict:
    row = await fetchone(conn, f"{ITEM_SQL} WHERE i.id=%s", (item_id,))
    if not row:
        raise HTTPException(404, "commentaire introuvable")
    return row


class SuggestIn(BaseModel):
    instructions: str = Field(default="", max_length=1000)


@router.post("/inbox/{item_id}/suggest")
async def suggest(item_id: int, body: SuggestIn, request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    item = await _item(conn, item_id)
    project = await project_or_404(conn, item["project_id"])
    s = await ai_settings(conn)
    if not s["api_key_enc"]:
        if not request.app.state.settings.simulation:
            raise HTTPException(409, "Claude n'est pas configuré : un administrateur doit saisir la clé API dans "
                                     "Administration")
        return {"reply": f"[Simulation] Merci {item['author_name'] or ''} pour votre message !".replace("  ", " "),
                "note": "Réponse factice : mode simulation sans clé API Claude."}
    if await _used_today(conn) >= s["daily_limit"]:
        raise HTTPException(429, f"limite de {s['daily_limit']} rédactions par jour atteinte")
    await conn.commit()
    try:
        reply, note, model, tin, tout = await ai.suggest_reply(
            request.app.state.vault.open(s["api_key_enc"]), s["model"], project, item["platform"], item["post_text"],
            item["text"], item["author_name"] or item["author_handle"], body.instructions)
    except ai.AIError as exc:
        await conn.execute("INSERT INTO ai_calls(user_id, project_id, model, ok) VALUES (%s,%s,%s,false)",
                           (user["id"], project["id"], s["model"]))
        await conn.commit()
        raise HTTPException(502, str(exc)) from exc
    await conn.execute("INSERT INTO ai_calls(user_id, project_id, model, input_tokens, output_tokens) "
                       "VALUES (%s,%s,%s,%s,%s)", (user["id"], project["id"], model, tin, tout))
    await conn.commit()
    return {"reply": reply, "note": note}


class ReplyIn(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


@router.post("/inbox/{item_id}/reply")
async def send_reply(item_id: int, body: ReplyIn, request: Request, user=Depends(current_user),
                     conn=Depends(get_conn)):
    item = await _item(conn, item_id)
    text = body.text.strip()
    limit = {"x": 280, "bluesky": 300, "threads": 500}.get(item["platform"])
    if limit and len(text) > limit:
        raise HTTPException(422, f"{platforms.LABELS[item['platform']]} : {limit} caractères au plus")
    if item["social_account_id"] is None:
        raise HTTPException(409, "le compte de ce post a été retiré de Tamtam")
    await conn.commit()
    try:
        acc = await worker.account_with_token(request.app.state.pool, request.app.state.vault, item["social_account_id"])
        rid = await platforms.reply(item["platform"], acc, item, text, request.app.state.settings.graph_version)
    except PublishError as exc:
        await conn.execute("UPDATE inbox_items SET reply_error=%s WHERE id=%s", (str(exc)[:500], item_id))
        await conn.commit()
        raise HTTPException(502, str(exc)) from exc
    await conn.execute("UPDATE inbox_items SET status='replied', reply_text=%s, reply_external_id=%s, reply_error='', "
                       "replied_by=%s, replied_at=now() WHERE id=%s", (text, rid, user["id"], item_id))
    await conn.commit()
    return _out(await _item(conn, item_id))


class StatusIn(BaseModel):
    status: str = Field(pattern="^(new|done)$")


@router.post("/inbox/{item_id}/status")
async def set_status(item_id: int, body: StatusIn, user=Depends(current_user), conn=Depends(get_conn)):
    await _item(conn, item_id)
    await conn.execute("UPDATE inbox_items SET status=%s WHERE id=%s AND status <> 'replied'", (body.status, item_id))
    await conn.commit()
    return _out(await _item(conn, item_id))
