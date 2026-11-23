"""Page « lien en bio » : une page publique par projet (/b/<slug>) avec ses liens (App Store, Google Play, site…)
et le dernier post publié. À mettre dans la bio Instagram, TikTok, Threads… où les liens des posts ne sont pas
cliquables. Chaque réseau a sa propre adresse (?src=instagram) pour savoir d'où viennent les visites.

Aucun cookie, aucune adresse IP : seulement un nombre de visites et de clics par jour et par source.
"""
from __future__ import annotations

import html
import re
import secrets
import unicodedata
from urllib.parse import quote

from .platforms import LABELS, PLATFORMS
from .worker import with_utm

SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?$")
SOURCES = set(PLATFORMS) | {"direct"}
RESERVED = {"api", "m", "l", "b", "admin", "health"}


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40].strip("-")
    return s or "projet"


def source(raw: str | None) -> str:
    raw = (raw or "").lower().strip()
    return raw if raw in SOURCES else "direct"


def clean_links(links: list[dict]) -> list[dict]:
    out, seen = [], set()
    for ln in links[:20]:
        label, url = str(ln.get("label", "")).strip()[:80], str(ln.get("url", "")).strip()[:1000]
        if not label or not url:
            continue
        if not url.startswith(("https://", "http://")):
            raise ValueError(f"le lien « {label} » doit commencer par https://")
        lid = str(ln.get("id") or "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{4,16}", lid) or lid in seen:
            lid = secrets.token_urlsafe(6)
        seen.add(lid)
        out.append({"id": lid, "label": label, "url": url})
    return out


def target(url: str, src: str) -> str:
    """Adresse finale avec paramètres UTM (utm_source = réseau d'origine de la visite)."""
    return with_utm(url, src if src != "direct" else "bio", "bio", 0).replace("utm_content=post-0", "utm_content=bio")


def _color_ok(c: str) -> str:
    return c if re.fullmatch(r"#[0-9A-Fa-f]{6}", c or "") else "#0E6E5C"


def render(page: dict, project: dict, latest: dict | None, src: str, avatar_url: str = "") -> str:
    color = _color_ok(project.get("color", ""))
    title = html.escape(page.get("title") or project["name"])
    subtitle = html.escape(page.get("subtitle") or "")
    slug = page["slug"]
    qs = f"?src={quote(src)}" if src != "direct" else ""
    buttons = "\n".join(
        f'<a class="btn" href="/b/{slug}/go/{ln["id"]}{qs}" rel="nofollow">{html.escape(ln["label"])}</a>'
        for ln in page.get("links", []))
    initial = html.escape((project["name"][:1] or "?").upper())
    avatar = (f'<img class="av" src="{html.escape(avatar_url)}" alt="">' if avatar_url
              else f'<div class="av">{initial}</div>')
    latest_html = ""
    if latest:
        nets = " · ".join(f'<a href="{html.escape(u)}" rel="nofollow noopener">{html.escape(LABELS.get(p, p))}</a>'
                          for p, u in latest["links"])
        img = (f'<img class="lp-img" src="{html.escape(latest["image"])}" alt="">' if latest.get("image") else "")
        latest_html = (f'<section class="latest"><h2>Dernière publication</h2>{img}'
                       f'<p>{html.escape(latest["text"])}</p>{f"<p class=nets>Voir sur : {nets}</p>" if nets else ""}'
                       f'</section>')
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><meta name="description" content="{subtitle or title}"><meta name="robots" content="index">
<meta property="og:title" content="{title}"><meta property="og:description" content="{subtitle}">
{f'<meta property="og:image" content="{html.escape(avatar_url)}">' if avatar_url else ''}
<link rel="icon" href="/favicon.svg">
<style>
:root {{ --c: {color}; --bg: #f4f6f5; --card: #fff; --ink: #18211e; --muted: #5d6b66; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg: #0f1513; --card: #18201d; --ink: #e8eeeb; --muted: #9fb0aa; }} }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; background: var(--bg); color: var(--ink); }}
main {{ max-width: 520px; margin: 0 auto; padding: 40px 16px 56px; text-align: center; }}
.av {{ width: 96px; height: 96px; border-radius: 50%; margin: 0 auto 14px; display: grid; place-items: center;
  background: var(--c); color: #fff; font-size: 40px; font-weight: 700; object-fit: cover; }}
h1 {{ font-size: 24px; margin: 0 0 6px; }} .sub {{ color: var(--muted); margin: 0 0 24px; }}
.btn {{ display: block; padding: 15px 18px; margin: 0 0 12px; border-radius: 14px; background: var(--c); color: #fff;
  text-decoration: none; font-weight: 650; box-shadow: 0 1px 2px rgba(0,0,0,.12); }}
.btn:hover {{ filter: brightness(1.08); }} .btn:focus-visible {{ outline: 3px solid var(--ink); outline-offset: 2px; }}
.latest {{ margin-top: 28px; background: var(--card); border-radius: 16px; padding: 16px; text-align: left; }}
.latest h2 {{ font-size: 13px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin: 0 0 10px; }}
.latest p {{ margin: 8px 0 0; white-space: pre-wrap; word-break: break-word; }}
.lp-img {{ width: 100%; border-radius: 10px; display: block; }} .nets {{ font-size: 14px; color: var(--muted); }}
.nets a {{ color: var(--c); }}
@media (prefers-color-scheme: dark) {{ .nets a {{ color: #fff; }} }}
</style></head><body><main>
{avatar}<h1>{title}</h1>{f'<p class="sub">{subtitle}</p>' if subtitle else '<div style="height:18px"></div>'}
{buttons}
{latest_html}
</main></body></html>"""


async def latest_post(conn, project_id: int, public_url: str) -> dict | None:
    cur = await conn.execute("""
        SELECT p.id, p.body FROM posts p WHERE p.project_id=%s AND p.status IN ('done','partial')
        ORDER BY p.scheduled_at DESC NULLS LAST, p.id DESC LIMIT 1""", (project_id,))
    post = await cur.fetchone()
    if not post:
        return None
    cur = await conn.execute("SELECT platform, external_url FROM post_targets WHERE post_id=%s AND status='published' "
                             "AND external_url <> '' ORDER BY platform", (post["id"],))
    links = [(r["platform"], r["external_url"]) for r in await cur.fetchall()]
    cur = await conn.execute("SELECT m.token, m.ext FROM post_media pm JOIN media m ON m.id=pm.media_id "
                             "WHERE pm.post_id=%s AND m.kind='image' ORDER BY pm.position LIMIT 1", (post["id"],))
    m = await cur.fetchone()
    text = post["body"].strip()
    if len(text) > 280:
        text = text[:277].rsplit(" ", 1)[0] + "…"
    return {"text": text, "links": links, "image": f"{public_url}/m/{m['token']}{m['ext']}" if m else ""}
