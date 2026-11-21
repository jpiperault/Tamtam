"""Configuration lue dans les variables d'environnement (aucun secret ni domaine dans le code)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from cryptography.fernet import Fernet


class ConfigError(Exception):
    """Variable obligatoire absente ou invalide."""


def _bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "oui", "on")


@dataclass(frozen=True)
class Settings:
    database_url: str
    session_secret: str = field(repr=False)
    token_key: str = field(repr=False)
    admin_email: str = ""
    admin_password: str | None = field(default=None, repr=False)
    public_url: str = "http://127.0.0.1:8080"
    port: int = 8080
    data_dir: str = "/data"
    demo_data: bool = False
    simulation: bool = False
    timezone: str = "Europe/Paris"
    graph_version: str = "v24.0"
    max_upload_mb: int = 250


REQUIRED = ("DATABASE_URL", "SESSION_SECRET", "TOKEN_KEY", "ADMIN_EMAIL", "PUBLIC_URL")


def load_settings(env: dict | None = None) -> Settings:
    env = dict(os.environ if env is None else env)
    missing = [n for n in REQUIRED if not (env.get(n) or "").strip()]
    if missing:
        raise ConfigError("variable(s) d'environnement obligatoire(s) manquante(s) : " + ", ".join(missing))
    secret = env["SESSION_SECRET"].strip()
    if len(secret) < 32:
        raise ConfigError("SESSION_SECRET doit faire au moins 32 caractères (openssl rand -hex 32)")
    key = env["TOKEN_KEY"].strip()
    try:
        Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise ConfigError("TOKEN_KEY invalide : 32 octets en base64 url, par exemple "
                          "python3 -c \"import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())\"") from exc
    if not env["DATABASE_URL"].strip().startswith(("postgresql://", "postgres://")):
        raise ConfigError("DATABASE_URL doit être une adresse postgresql://utilisateur:motdepasse@hote:5432/base")
    email = env["ADMIN_EMAIL"].strip().lower()
    if "@" not in email:
        raise ConfigError("ADMIN_EMAIL doit être une adresse e-mail")
    public = env["PUBLIC_URL"].strip().rstrip("/")
    if not public.startswith(("https://", "http://")):
        raise ConfigError("PUBLIC_URL doit être l'adresse publique complète, par exemple https://tamtam.piperault.fr")
    tz = (env.get("APP_TIMEZONE") or "Europe/Paris").strip()
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ConfigError(f"APP_TIMEZONE inconnu : {tz!r} (exemple : Europe/Paris)") from exc
    try:
        port = int(env.get("PORT") or 8080)
        max_up = int(env.get("MAX_UPLOAD_MB") or 250)
    except ValueError as exc:
        raise ConfigError("PORT et MAX_UPLOAD_MB doivent être des nombres entiers") from exc
    return Settings(
        database_url=env["DATABASE_URL"].strip(),
        session_secret=secret,
        token_key=key,
        admin_email=email,
        admin_password=(env.get("ADMIN_PASSWORD") or "").strip() or None,
        public_url=public,
        port=port,
        data_dir=(env.get("DATA_DIR") or "/data").strip(),
        demo_data=_bool(env.get("DEMO_DATA"), False),
        simulation=_bool(env.get("SIMULATION"), False),
        timezone=tz,
        graph_version=(env.get("META_GRAPH_VERSION") or "v24.0").strip(),
        max_upload_mb=max(1, min(max_up, 1024)),
    )
