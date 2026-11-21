"""Application FastAPI : API, santé, fichiers web, cycle de vie."""
from __future__ import annotations

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from . import __version__, datadir, db, log, media, security, seed, worker
from .api import router
from .config import ConfigError, Settings, load_settings

_log = log.get("main")

CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; media-src 'self' blob:; "
       "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; "
       "frame-ancestors 'none'")
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Content-Security-Policy": CSP,
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}
HSTS = "max-age=31536000"


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def same_origin(request: Request) -> bool:
    """Protection CSRF : une requête qui modifie des données doit venir de l'application elle-même.

    Les navigateurs envoient Sec-Fetch-Site ; « same-site » (un autre sous-domaine de piperault.fr) est refusé aussi.
    À défaut, l'en-tête Origin doit désigner le même hôte. Sans aucun des deux (curl, scripts), on laisse passer :
    ce n'est pas un navigateur, donc pas de cookie volé par rebond.
    """
    site = request.headers.get("sec-fetch-site")
    if site is not None:
        return site in ("same-origin", "none")
    origin = request.headers.get("origin")
    if origin is None:
        return True
    host = request.headers.get("host", "")
    return origin.split("://", 1)[-1].rstrip("/") == host


def _web_dist() -> Path | None:
    candidates = [os.environ.get("WEB_DIST"), "/app/web/dist", str(Path(__file__).resolve().parents[2] / "web" / "dist")]
    for c in candidates:
        if c and (Path(c) / "index.html").is_file():
            return Path(c)
    return None


async def _bootstrap_admin(settings: Settings, pool) -> int | None:
    async with pool.connection() as conn:
        cur = await conn.execute("SELECT id, is_admin, active FROM users WHERE email=%s", (settings.admin_email,))
        row = await cur.fetchone()
        if row:
            if not row["is_admin"] or not row["active"]:
                await conn.execute("UPDATE users SET is_admin=true, active=true WHERE id=%s", (row["id"],))
                _log.info("compte administrateur principal rétabli")
            uid = row["id"]
        elif settings.admin_password:
            cur = await conn.execute(
                "INSERT INTO users(email, name, password_hash, is_admin) VALUES (%s,%s,%s,true) RETURNING id",
                (settings.admin_email, "Administrateur", security.hash_password(settings.admin_password)))
            uid = (await cur.fetchone())["id"]
            _log.info("compte administrateur principal créé")
        else:
            _log.warning("aucun compte administrateur : définissez ADMIN_PASSWORD pour le créer")
            uid = None
        await conn.commit()
        return uid


def create_app(settings: Settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        datadir.ensure_docs(settings.data_dir)
        await db.run_migrations(settings.database_url)
        pool = db.make_pool(settings.database_url)
        await pool.open(wait=False)
        app.state.pool = pool
        admin_id = await _bootstrap_admin(settings, pool)
        media.media_dir(settings.data_dir)
        await worker.reset_interrupted(pool)
        if settings.demo_data and admin_id:
            async with pool.connection() as conn:
                if await seed.seed_if_empty(conn, admin_id):
                    _log.info("données de démonstration ajoutées")
        stop = asyncio.Event()
        task = asyncio.create_task(worker.run(app, stop)) if os.environ.get("TAMTAM_WORKER", "1") != "0" else None
        _log.info("Tamtam %s prêt sur le port %d (adresse publique %s%s)", __version__, settings.port,
                  settings.public_url, ", mode simulation" if settings.simulation else "")
        try:
            yield
        finally:
            stop.set()
            if task:
                try:
                    await asyncio.wait_for(task, 1.5)
                except (asyncio.TimeoutError, Exception):
                    task.cancel()
            try:
                await asyncio.wait_for(pool.close(timeout=1.0), 1.5)
            except asyncio.TimeoutError:
                pass

    app = FastAPI(title="Tamtam", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.limiter = security.RateLimiter(limit=10, window=600)
    app.state.vault = security.Vault(settings.token_key)

    @app.middleware("http")
    async def headers(request: Request, call_next):
        if request.method not in SAFE_METHODS and request.url.path.startswith("/api/") and not same_origin(request):
            return JSONResponse({"detail": "requête refusée : origine différente"}, status_code=403)
        response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        if security.is_https(request):
            response.headers.setdefault("Strict-Transport-Security", HSTS)
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(x) for x in first.get("loc", [])[1:])
        msg = first.get("msg", "requête invalide")
        return JSONResponse({"detail": f"{where} : {msg}" if where else msg}, status_code=422)

    @app.get("/health", include_in_schema=False)
    async def health(request: Request):
        async def ping():
            async with request.app.state.pool.connection(timeout=0.8) as conn:
                await conn.execute("SELECT 1")

        try:
            await asyncio.wait_for(ping(), 0.9)  # toujours répondre en moins d'une seconde
            return PlainTextResponse("ok")
        except Exception:
            return PlainTextResponse("base inaccessible", status_code=503)

    media_root = (Path(settings.data_dir) / "media").resolve()

    @app.get("/m/{name}", include_in_schema=False)
    async def public_media(name: str):
        """Médias publics : Instagram, Facebook et TikTok viennent les chercher à cette adresse."""
        f = (media_root / name).resolve()
        if media_root not in f.parents or not f.is_file() or f.suffix not in (".jpg", ".mp4", ".mov"):
            return PlainTextResponse("introuvable", status_code=404)
        types = {".jpg": "image/jpeg", ".mp4": "video/mp4", ".mov": "video/quicktime"}
        return FileResponse(f, media_type=types[f.suffix], headers={
            "Cache-Control": "public, max-age=86400", "Cross-Origin-Resource-Policy": "cross-origin"})

    @app.get("/l/{code}", include_in_schema=False)
    async def short_link(code: str, request: Request):
        """Lien court suivi : compte le clic du jour puis redirige vers la page avec ses paramètres UTM."""
        if not code.isalnum() or len(code) > 20:
            return PlainTextResponse("lien inconnu", status_code=404)
        try:
            async with request.app.state.pool.connection() as conn:
                cur = await conn.execute("UPDATE links SET clicks=clicks+1 WHERE code=%s RETURNING id, target_url", (code,))
                row = await cur.fetchone()
                if row:
                    await conn.execute("INSERT INTO link_clicks(link_id, day, clicks) VALUES (%s, current_date, 1) "
                                       "ON CONFLICT (link_id, day) DO UPDATE SET clicks=link_clicks.clicks+1", (row["id"],))
                await conn.commit()
        except Exception:
            return PlainTextResponse("service momentanément indisponible", status_code=503)
        if not row:
            return PlainTextResponse("lien inconnu", status_code=404)
        return Response(status_code=302, headers={"Location": row["target_url"], "Cache-Control": "no-store",
                                                  "Referrer-Policy": "no-referrer-when-downgrade"})

    app.include_router(router)

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"], include_in_schema=False)
    async def api_404(path: str):
        return JSONResponse({"detail": "route inconnue"}, status_code=404)

    dist = _web_dist()
    if dist is not None:
        if (dist / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
        index = dist / "index.html"

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str):
            f = (dist / path).resolve()
            if path and f.is_file() and dist.resolve() in f.parents and f.name != "index.html":
                return FileResponse(f)
            return FileResponse(index, headers={"Cache-Control": "no-cache"})
    else:
        @app.get("/", include_in_schema=False)
        async def no_web():
            return Response("Tamtam : interface web non construite (web/dist absent).", media_type="text/plain")

    return BodyLimit(app, settings.max_upload_mb * 1024 * 1024 + 64 * 1024)


class BodyLimit:
    """Refuse (413) les corps trop gros avant de les lire : 1 Mo pour l'API, la taille des médias pour leur envoi.

    Vérifie Content-Length, puis compte les octets reçus (envoi en morceaux), pour qu'un anonyme ne puisse pas
    remplir la mémoire (limite 384 Mo) avec des requêtes géantes.
    """

    DEFAULT_MAX = 1024 * 1024

    def __init__(self, app, upload_max: int):
        self.app = app
        self.UPLOAD_MAX = upload_max
        self.state = app.state  # les tests et le cycle de vie accèdent à app.state

    def __getattr__(self, name):
        return getattr(self.app, name)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope.get("path", "")
        limit = self.UPLOAD_MAX if (path.startswith("/api/v1/projects/") and path.endswith("/media")) else self.DEFAULT_MAX
        for k, v in scope.get("headers", []):
            if k == b"content-length":
                try:
                    if int(v) > limit:
                        return await self._too_big(send, limit)
                except ValueError:
                    return await self._too_big(send, limit)
        received = 0
        too_big = False
        replaced = False

        async def limited_receive():
            nonlocal received, too_big
            if too_big:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    too_big = True  # on arrête de lire : la suite du corps n'est jamais chargée en mémoire
                    raise _TooBig()
            return message

        async def guarded_send(message):
            nonlocal replaced
            if too_big:  # l'application a réagi à la coupure (400…) : on répond 413 à la place
                if not replaced:
                    replaced = True
                    await self._too_big(send, limit)
                return
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except _TooBig:
            if not replaced:
                await self._too_big(send, limit)

    @staticmethod
    async def _too_big(send, limit):
        body = ('{"detail":"requête trop volumineuse (%d Mo au plus)"}' % (limit // (1024 * 1024))).encode()
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()),
                                (b"connection", b"close")]})
        await send({"type": "http.response.body", "body": body})


class _TooBig(Exception):
    pass


def main() -> None:
    log.setup_logging()
    try:
        settings = load_settings()
    except ConfigError as exc:
        _log.error("démarrage impossible : %s", exc)
        sys.exit(2)
    import uvicorn

    config = uvicorn.Config(create_app(settings), host=os.environ.get("HOST", "0.0.0.0"), port=settings.port,
                            proxy_headers=False, access_log=False, log_config=None, timeout_graceful_shutdown=2,
                            server_header=False)
    uvicorn.Server(config).run()
