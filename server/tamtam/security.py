"""Mots de passe, jetons de session et limitation des tentatives de connexion."""
from __future__ import annotations

import time
from collections import defaultdict, deque

import bcrypt
import jwt

COOKIE_NAME = "tamtam_session"
TOKEN_DAYS = 30
MIN_PASSWORD = 10


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt(rounds=12)).decode()


def check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode())
    except ValueError:
        return False


# Empreinte factice : on vérifie toujours un mot de passe, même pour une adresse inconnue,
# pour que le temps de réponse ne révèle pas quels comptes existent.
_DUMMY_HASH = bcrypt.hashpw(b"tamtam-dummy", bcrypt.gensalt(rounds=12)).decode()


def check_password_constant_time(password: str, hashed: str | None) -> bool:
    ok = check_password(password, hashed or _DUMMY_HASH)
    return ok and hashed is not None


def make_token(user_id: int, version: int, secret: str) -> str:
    now = int(time.time())
    return jwt.encode({"sub": str(user_id), "v": int(version), "iat": now, "exp": now + TOKEN_DAYS * 86400},
                      secret, algorithm="HS256")


def read_token(token: str, secret: str) -> tuple[int, int] | None:
    """(identifiant, version de session) si le jeton est valide, sinon None."""
    try:
        data = jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["exp", "sub"]})
        return int(data["sub"]), int(data.get("v", 0))
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        return None


def set_session_cookie(response, request, user_id: int, version: int, secret: str) -> None:
    response.set_cookie(COOKIE_NAME, make_token(user_id, version, secret), max_age=TOKEN_DAYS * 86400,
                        httponly=True, samesite="lax", secure=is_https(request), path="/")


class RateLimiter:
    """Au plus `limit` essais par clé (adresse IP) sur `window` secondes."""

    def __init__(self, limit: int, window: int):
        self.limit, self.window = limit, window
        self._hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        if len(self._hits) > 10000:  # évite qu'une avalanche d'adresses ne remplisse la mémoire
            for k in [k for k, v in self._hits.items() if not v or now - v[-1] > self.window]:
                del self._hits[k]
        return True


def client_ip(request) -> str:
    """IP réelle du visiteur : derrière Caddy, X-Real-IP puis X-Forwarded-For (seul le proxy joint le conteneur)."""
    real = request.headers.get("x-real-ip", "").strip()
    if real:
        return real
    fwd = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if fwd:
        return fwd
    return request.client.host if request.client else "?"


def is_https(request) -> bool:
    """Vrai si le visiteur est en HTTPS (Cloudflare → Caddy envoie X-Forwarded-Proto: https)."""
    proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    return (proto or request.url.scheme) == "https"


class Vault:
    """Chiffre les jetons des réseaux sociaux et les secrets d'application avant de les écrire en base (TOKEN_KEY)."""

    def __init__(self, key: str):
        from cryptography.fernet import Fernet

        self._f = Fernet(key.encode())

    def seal(self, value: str | None) -> str | None:
        return None if value is None else self._f.encrypt(value.encode()).decode()

    def open(self, value: str | None) -> str | None:
        from cryptography.fernet import InvalidToken

        if value is None:
            return None
        try:
            return self._f.decrypt(value.encode()).decode()
        except InvalidToken:
            return None
