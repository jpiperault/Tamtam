"""Posts : création (brouillon, immédiat ou programmé), modification, liste, nouvel essai."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from .. import notify, platforms, slots, worker
from .common import admin_user, current_user, fetchall, fetchone, get_conn, project_or_404

router = APIRouter()


class TikTokOptions(BaseModel):
    """Réglages TikTok choisis à chaque post (exigés par les règles de partage de TikTok : rien par défaut)."""
    privacy_level: str = Field(default="", pattern="^(|PUBLIC_TO_EVERYONE|MUTUAL_FOLLOW_FRIENDS|FOLLOWER_OF_CREATOR|SELF_ONLY)$")
    allow_comment: bool = False
    allow_duet: bool = False
    allow_stitch: bool = False
    disclose: bool = False          # « Content Disclosure Setting »
    brand_organic: bool = False     # « Votre marque » → « Contenu promotionnel »
    brand_content: bool = False     # « Contenu de marque » → « Partenariat rémunéré »


def tiktok_problems(o: TikTokOptions) -> list[str]:
    out = []
    if not o.privacy_level:
        out.append("TikTok : choisissez qui peut voir le post.")
    if o.disclose and not (o.brand_organic or o.brand_content):
        out.append("TikTok : indiquez si le contenu fait votre promotion, celle d'un tiers, ou les deux.")
    if o.disclose and o.brand_content and o.privacy_level == "SELF_ONLY":
        out.append("TikTok : un contenu de marque ne peut pas être privé.")
    return out


class YouTubeOptions(BaseModel):
    """Réglages YouTube du post. Titre vide = première ligne du texte."""
    title: str = Field(default="", max_length=100)
    privacy: str = Field(default="public", pattern="^(public|unlisted|private)$")
    made_for_kids: bool = False     # déclaration obligatoire chez YouTube (loi américaine COPPA)


class PostIn(BaseModel):
    project_id: int
    body: str = Field(default="", max_length=10000)
    account_ids: list[int] = Field(default_factory=list, max_length=20)
    overrides: dict[str, str] = Field(default_factory=dict)   # identifiant du compte → texte adapté
    media_ids: list[int] = Field(default_factory=list, max_length=35)
    link_url: str = Field(default="", max_length=2000)
    campaign: str = Field(default="", max_length=80)
    facebook_short_link: bool = False   # Facebook : lien court suivi /l/… au lieu du lien direct
    tiktok: dict[str, TikTokOptions] = Field(default_factory=dict)   # identifiant du compte TikTok → réglages
    youtube: dict[str, YouTubeOptions] = Field(default_factory=dict)  # identifiant de la chaîne YouTube → réglages
    auto_crop: bool = False             # recadrer les images au format conseillé de chaque réseau
    recycled_from: int | None = None    # post d'origine (nouvelle version d'un ancien post)
    mode: str = Field(default="draft", pattern="^(draft|now|at|queue)$")   # queue : prochain créneau libre
    scheduled_at: datetime | None = None


async def _post_full(conn, post_id: int) -> dict | None:
    post = await fetchone(conn, "SELECT p.*, u.name AS author FROM posts p LEFT JOIN users u ON u.id=p.created_by "
                                "WHERE p.id=%s", (post_id,))
    if not post:
        return None
    post["targets"] = await fetchall(conn, """
        SELECT t.id, t.platform, t.social_account_id, t.body_override, t.options, t.status, t.external_url, t.error, t.attempts,
               t.published_at, t.not_before, a.name AS account_name, a.handle AS account_handle,
               a.simulated, l.code AS link_code, COALESCE(l.clicks, 0) AS clicks
        FROM post_targets t LEFT JOIN social_accounts a ON a.id=t.social_account_id
        LEFT JOIN links l ON l.post_target_id=t.id
        WHERE t.post_id=%s ORDER BY array_position(%s::text[], t.platform)""", (post_id, list(platforms.PLATFORMS)))
    post["media"] = [{"id": m["id"], "kind": m["kind"], "url": f"/m/{m['token']}{m['ext']}", "filename": m["filename"],
                      "duration_s": m["duration_s"], "width": m["width"], "height": m["height"]}
                     for m in await fetchall(conn, "SELECT m.* FROM post_media pm JOIN media m ON m.id=pm.media_id "
                                                   "WHERE pm.post_id=%s ORDER BY pm.position", (post_id,))]
    return post


async def _validate(conn, body: PostIn, tz: str = "Europe/Paris", post_id: int | None = None) -> tuple[list[dict], list[dict]]:
    project = await project_or_404(conn, body.project_id)
    if body.recycled_from and not await fetchone(conn, "SELECT 1 FROM posts WHERE id=%s AND project_id=%s",
                                                 (body.recycled_from, body.project_id)):
        body.recycled_from = None
    if body.link_url and not body.link_url.startswith(("https://", "http://")):
        raise HTTPException(422, "le lien doit commencer par https://")
    accounts = []
    if body.account_ids:
        accounts = await fetchall(conn, "SELECT id, platform, name, status FROM social_accounts "
                                        "WHERE project_id=%s AND id = ANY(%s)", (body.project_id, body.account_ids))
        if len(accounts) != len(set(body.account_ids)):
            raise HTTPException(422, "un des comptes choisis n'appartient pas à ce projet")
    media = []
    if body.media_ids:
        rows = await fetchall(conn, "SELECT id, kind FROM media WHERE project_id=%s AND id = ANY(%s)",
                              (body.project_id, body.media_ids))
        by_id = {r["id"]: r for r in rows}
        if len(by_id) != len(set(body.media_ids)):
            raise HTTPException(422, "un des médias n'appartient pas à ce projet")
        media = [by_id[i] for i in dict.fromkeys(body.media_ids)]
    if body.mode != "draft":
        if not accounts:
            raise HTTPException(422, "choisissez au moins un compte")
        problems = []
        kinds = [m["kind"] for m in media]
        for a in accounts:
            text = body.overrides.get(str(a["id"]), body.body)
            problems += platforms.check(a["platform"], text, kinds, bool(body.link_url))
            if a["platform"] == "tiktok":
                problems += tiktok_problems(body.tiktok.get(str(a["id"])) or TikTokOptions())
            if a["platform"] == "youtube":
                yt = body.youtube.get(str(a["id"])) or YouTubeOptions()
                if not (yt.title.strip() or text.strip()):
                    problems.append("YouTube : donnez un titre à la vidéo.")
        if problems:
            raise HTTPException(422, " ".join(dict.fromkeys(problems)))
        if body.mode == "queue":
            if not project["slots"]:
                raise HTTPException(422, "ce projet n'a pas de créneaux de publication : ajoutez-en dans Projets")
            found = slots.upcoming(project["slots"], tz, await slots.taken(conn, body.project_id, post_id),
                                   datetime.now(timezone.utc))
            if not found:
                raise HTTPException(422, "aucun créneau libre dans l'année qui vient")
            body.scheduled_at = found[0]
        if body.mode == "at":
            if body.scheduled_at is None:
                raise HTTPException(422, "indiquez la date de publication")
            when = body.scheduled_at if body.scheduled_at.tzinfo else body.scheduled_at.replace(tzinfo=timezone.utc)
            if when < datetime.now(timezone.utc) - timedelta(minutes=2):
                raise HTTPException(422, "la date de publication est déjà passée")
    return accounts, media


async def _write(conn, post_id: int, body: PostIn, accounts: list[dict], media: list[dict]) -> None:
    await conn.execute("DELETE FROM post_targets WHERE post_id=%s", (post_id,))
    await conn.execute("DELETE FROM post_media WHERE post_id=%s", (post_id,))
    for a in accounts:
        ov = body.overrides.get(str(a["id"]))
        opts = (body.tiktok.get(str(a["id"])) if a["platform"] == "tiktok"
                else body.youtube.get(str(a["id"])) if a["platform"] == "youtube" else None)
        await conn.execute("INSERT INTO post_targets(post_id, social_account_id, platform, body_override, options) "
                           "VALUES (%s,%s,%s,%s,%s)", (post_id, a["id"], a["platform"],
                                                       ov if ov is not None and ov != body.body else None,
                                                       Jsonb(opts.model_dump() if opts else {})))
    for i, m in enumerate(media):
        await conn.execute("INSERT INTO post_media(post_id, media_id, position) VALUES (%s,%s,%s)", (post_id, m["id"], i))


async def approval_required(conn) -> bool:
    row = await fetchone(conn, "SELECT value FROM site_settings WHERE key='approval_required'")
    return bool(row and row["value"] == "1")


async def _needs_review(conn, user: dict, body: PostIn) -> bool:
    """Validation à deux : un membre (non administrateur) ne publie pas directement si l'option est active."""
    return body.mode != "draft" and not user["is_admin"] and await approval_required(conn)


def _review_alert(request: Request, post_id: int, author: str, project: str, body: str) -> None:
    s = request.app.state.settings
    excerpt = (body.strip().splitlines() or ["(texte adapté par réseau)"])[0][:140]
    notify.fire(request.app, "approval", f"📝 Tamtam : {author} propose un post pour {project}, à valider.\n"
                                         f"« {excerpt} »\n{s.public_url}/#/?status=review")


def _sched(body: PostIn) -> tuple[str, datetime | None]:
    if body.mode == "draft":
        return "draft", body.scheduled_at
    if body.mode == "now":
        return "scheduled", datetime.now(timezone.utc)
    return "scheduled", body.scheduled_at   # at, ou queue (heure du créneau trouvée par _validate)


@router.post("/posts", status_code=201)
async def create_post(body: PostIn, request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    accounts, media = await _validate(conn, body, request.app.state.settings.timezone)
    status, when = _sched(body)
    review = await _needs_review(conn, user, body)
    if review:
        status = "review"
    row = await fetchone(conn, "INSERT INTO posts(project_id, created_by, body, link_url, campaign, facebook_short_link, "
                               "auto_crop, recycled_from, scheduled_at, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                               "RETURNING id",
                         (body.project_id, user["id"], body.body, body.link_url.strip(), body.campaign.strip(),
                          body.facebook_short_link, body.auto_crop, body.recycled_from, when, status))
    await _write(conn, row["id"], body, accounts, media)
    await conn.commit()
    if review:
        project = await project_or_404(conn, body.project_id)
        _review_alert(request, row["id"], user["name"] or user["email"], project["name"], body.body)
    return await _post_full(conn, row["id"])


@router.put("/posts/{post_id}")
async def update_post(post_id: int, body: PostIn, request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    post = await fetchone(conn, "SELECT * FROM posts WHERE id=%s FOR UPDATE", (post_id,))
    if not post:
        raise HTTPException(404, "post introuvable")
    if post["status"] not in ("draft", "scheduled", "review") or post["project_id"] != body.project_id:
        raise HTTPException(409, "ce post est déjà en cours de publication ou publié : dupliquez-le pour le modifier")
    accounts, media = await _validate(conn, body, request.app.state.settings.timezone, post_id)
    status, when = _sched(body)
    review = await _needs_review(conn, user, body)
    if review:
        status = "review"
    await conn.execute("UPDATE posts SET body=%s, link_url=%s, campaign=%s, facebook_short_link=%s, auto_crop=%s, "
                       "scheduled_at=%s, status=%s, updated_at=now() WHERE id=%s",
                       (body.body, body.link_url.strip(), body.campaign.strip(), body.facebook_short_link,
                        body.auto_crop, when, status, post_id))
    await _write(conn, post_id, body, accounts, media)
    await conn.commit()
    if review and post["status"] != "review":
        project = await project_or_404(conn, body.project_id)
        _review_alert(request, post_id, user["name"] or user["email"], project["name"], body.body)
    return await _post_full(conn, post_id)


class RejectIn(BaseModel):
    note: str = Field(default="", max_length=1000)


@router.post("/posts/{post_id}/approve")
async def approve_post(post_id: int, user=Depends(admin_user), conn=Depends(get_conn)):
    """Validation par un administrateur : le post part à l'heure prévue (tout de suite si elle est passée)."""
    post = await fetchone(conn, "SELECT status FROM posts WHERE id=%s FOR UPDATE", (post_id,))
    if not post:
        raise HTTPException(404, "post introuvable")
    if post["status"] != "review":
        raise HTTPException(409, "ce post n'attend pas de validation")
    await conn.execute("UPDATE posts SET status='scheduled', scheduled_at=GREATEST(COALESCE(scheduled_at, now()), now()), "
                       "review_note='', reviewed_by=%s, reviewed_at=now(), updated_at=now() WHERE id=%s",
                       (user["id"], post_id))
    await conn.commit()
    return await _post_full(conn, post_id)


@router.post("/posts/{post_id}/reject")
async def reject_post(post_id: int, body: RejectIn, user=Depends(admin_user), conn=Depends(get_conn)):
    """Refus : le post redevient un brouillon, avec la raison, pour que son auteur le corrige."""
    post = await fetchone(conn, "SELECT status FROM posts WHERE id=%s FOR UPDATE", (post_id,))
    if not post:
        raise HTTPException(404, "post introuvable")
    if post["status"] != "review":
        raise HTTPException(409, "ce post n'attend pas de validation")
    await conn.execute("UPDATE posts SET status='draft', review_note=%s, reviewed_by=%s, reviewed_at=now(), "
                       "updated_at=now() WHERE id=%s", (body.note.strip() or "Refusé sans commentaire.", user["id"], post_id))
    await conn.commit()
    return await _post_full(conn, post_id)


@router.get("/posts")
async def list_posts(project_id: int | None = None, status: str | None = None, start: datetime | None = None,
                     end: datetime | None = None, limit: int = 100, user=Depends(current_user), conn=Depends(get_conn)):
    where, params = [], []
    if project_id:
        where.append("project_id=%s")
        params.append(project_id)
    if status == "upcoming":
        where.append("status IN ('scheduled','publishing')")
    elif status == "problems":
        where.append("status IN ('failed','partial')")
    elif status == "review":
        where.append("status='review'")
    elif status:
        where.append("status=%s")
        params.append(status)
    if start:
        where.append("COALESCE(scheduled_at, created_at) >= %s")
        params.append(start)
    if end:
        where.append("COALESCE(scheduled_at, created_at) < %s")
        params.append(end)
    sql = "SELECT id FROM posts" + (" WHERE " + " AND ".join(where) if where else "")
    sql += " ORDER BY COALESCE(scheduled_at, created_at) DESC LIMIT %s"
    params.append(max(1, min(limit, 500)))
    ids = [r["id"] for r in await fetchall(conn, sql, params)]
    return [await _post_full(conn, i) for i in ids]


@router.get("/posts/{post_id}")
async def get_post(post_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    post = await _post_full(conn, post_id)
    if not post:
        raise HTTPException(404, "post introuvable")
    return post


@router.post("/posts/{post_id}/retry")
async def retry_post(post_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    """Relance les réseaux en échec (les réseaux déjà publiés ne sont pas republiés)."""
    post = await fetchone(conn, "SELECT status FROM posts WHERE id=%s", (post_id,))
    if not post:
        raise HTTPException(404, "post introuvable")
    cur = await conn.execute("UPDATE post_targets SET status='pending', attempts=0, not_before=NULL, error='', "
                             "updated_at=now() WHERE post_id=%s AND status='failed'", (post_id,))
    if cur.rowcount == 0:
        raise HTTPException(409, "aucun réseau en échec à relancer")
    await conn.execute("UPDATE posts SET scheduled_at=LEAST(scheduled_at, now()) WHERE id=%s", (post_id,))
    await worker.recompute_status(conn, post_id)
    await conn.commit()
    return await _post_full(conn, post_id)


@router.delete("/posts/{post_id}")
async def delete_post(post_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    """Supprime le post de Tamtam. Ce qui est déjà paru sur les réseaux y reste."""
    busy = await fetchone(conn, "SELECT 1 FROM post_targets WHERE post_id=%s AND status='publishing'", (post_id,))
    if busy:
        raise HTTPException(409, "publication en cours : attendez la fin avant de supprimer")
    cur = await conn.execute("DELETE FROM posts WHERE id=%s", (post_id,))
    if cur.rowcount == 0:
        raise HTTPException(404, "post introuvable")
    await conn.commit()
    return {"ok": True}


@router.get("/rules")
async def rules(request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    return {"approval_required": await approval_required(conn),
            "rules": platforms.RULES, "labels": platforms.LABELS, "x_url_length": platforms.base.X_URL_LENGTH,
            "public_url": request.app.state.settings.public_url, "timezone": request.app.state.settings.timezone}


@router.get("/stats")
async def stats(project_id: int | None = None, days: int = 30, user=Depends(current_user), conn=Depends(get_conn)):
    days = max(1, min(days, 365))
    pf, pp = ("AND l.project_id=%s", [project_id]) if project_id else ("", [])
    by_platform = await fetchall(conn, f"""
        SELECT l.platform, COALESCE(sum(c.clicks), 0)::int AS clicks
        FROM links l LEFT JOIN link_clicks c ON c.link_id=l.id AND c.day >= current_date - %s::int
        WHERE true {pf} GROUP BY l.platform""", [days] + pp)
    daily = await fetchall(conn, f"""
        SELECT c.day, l.platform, sum(c.clicks)::int AS clicks FROM link_clicks c JOIN links l ON l.id=c.link_id
        WHERE c.day >= current_date - %s::int {pf} GROUP BY c.day, l.platform ORDER BY c.day""", [days] + pp)
    qf, qp = ("AND p.project_id=%s", [project_id]) if project_id else ("", [])
    counts = await fetchone(conn, f"""
        SELECT count(*) FILTER (WHERE t.status='published' AND t.published_at >= now() - make_interval(days => %s))::int AS published,
               count(*) FILTER (WHERE t.status='failed' AND t.updated_at >= now() - make_interval(days => %s))::int AS failed,
               count(*) FILTER (WHERE t.status IN ('pending','publishing') AND p.status NOT IN ('draft','review'))::int AS upcoming
        FROM post_targets t JOIN posts p ON p.id=t.post_id WHERE true {qf}""", [days, days] + qp)
    top = await fetchall(conn, f"""
        SELECT p.id, left(p.body, 140) AS body, sum(c.clicks)::int AS clicks, min(t.published_at) AS published_at
        FROM posts p JOIN post_targets t ON t.post_id=p.id JOIN links l ON l.post_target_id=t.id
        JOIN link_clicks c ON c.link_id=l.id AND c.day >= current_date - %s::int
        WHERE true {qf} GROUP BY p.id ORDER BY clicks DESC LIMIT 5""", [days] + qp)
    return {"days": days, "by_platform": by_platform, "daily": daily, "counts": counts, "top": top}
