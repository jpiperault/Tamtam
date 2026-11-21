"""Règles communes aux réseaux : limites de texte et de médias, contenu à publier, erreurs lisibles."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import httpx

PLATFORMS = ("instagram", "facebook", "x", "tiktok")
PROVIDER_OF = {"instagram": "meta", "facebook": "meta", "x": "x", "tiktok": "tiktok"}
LABELS = {"instagram": "Instagram", "facebook": "Facebook", "x": "X", "tiktok": "TikTok"}

# Limites publiques des réseaux (à revoir si elles changent).
RULES = {
    "instagram": {"text": 2200, "media_required": True, "max_images": 10, "max_videos": 1, "mix": True,
                  "link_in_text": False},
    "facebook": {"text": 63206, "media_required": False, "max_images": 10, "max_videos": 1, "mix": False,
                 "link_in_text": True},
    "x": {"text": 280, "media_required": False, "max_images": 4, "max_videos": 1, "mix": False,
          "link_in_text": True},
    "tiktok": {"text": 2200, "media_required": True, "max_images": 35, "max_videos": 1, "mix": False,
               "link_in_text": False},
}
X_URL_LENGTH = 23  # X compte toute adresse comme 23 caractères


class PublishError(Exception):
    """Échec de publication avec un message compréhensible. `retry` : vaut la peine de réessayer plus tard."""

    def __init__(self, message: str, retry: bool = False):
        super().__init__(message)
        self.retry = retry


class AuthExpired(PublishError):
    """Le réseau refuse le jeton : il faut reconnecter le compte."""


@dataclass
class MediaFile:
    kind: str          # image | video
    path: Path
    url: str           # adresse publique (Meta et TikTok viennent la chercher)
    mime: str
    size: int


@dataclass
class Content:
    text: str
    link: str = ""                     # lien court suivi, déjà prêt
    media: list[MediaFile] = field(default_factory=list)


@dataclass
class Result:
    external_id: str
    url: str = ""


def text_length(platform: str, text: str, link: str = "") -> int:
    n = len(text)
    if platform == "x" and link:
        return n + 1 + X_URL_LENGTH
    if link and RULES[platform]["link_in_text"]:
        return n + 1 + len(link)
    return n


def check(platform: str, text: str, kinds: list[str], has_link: bool = False) -> list[str]:
    """Problèmes bloquants pour ce réseau (liste vide = publiable)."""
    r = RULES[platform]
    label = LABELS[platform]
    out = []
    n = text_length(platform, text, "x" * 23 if has_link else "")
    if n > r["text"]:
        out.append(f"{label} : {n - r['text']} caractère(s) de trop ({n}/{r['text']}).")
    images, videos = kinds.count("image"), kinds.count("video")
    if r["media_required"] and not kinds:
        out.append(f"{label} : une image ou une vidéo est obligatoire.")
    if images > r["max_images"]:
        out.append(f"{label} : {r['max_images']} image(s) au plus.")
    if videos > r["max_videos"]:
        out.append(f"{label} : une seule vidéo par post.")
    if images and videos and not r["mix"]:
        out.append(f"{label} : impossible de mélanger images et vidéo dans un même post.")
    if platform == "tiktok" and images and len(text) > 4000:
        out.append("TikTok : 4000 caractères au plus pour un carrousel photo.")
    if platform == "x" and not text.strip() and not kinds:
        out.append("X : le texte est vide.")
    if platform == "facebook" and not text.strip() and not kinds and not has_link:
        out.append("Facebook : le post est vide.")
    return out


def api_error(resp: httpx.Response, network: str) -> PublishError:
    """Transforme une réponse d'erreur en message lisible."""
    try:
        data = resp.json()
    except ValueError:
        data = {}
    msg = ""
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            msg = err.get("error_user_msg") or err.get("message") or err.get("code") or ""
        elif isinstance(err, str):
            msg = data.get("error_description") or err
        if not msg:
            msg = data.get("detail") or data.get("title") or data.get("message") or ""
            errs = data.get("errors")
            if not msg and isinstance(errs, list) and errs:
                msg = errs[0].get("message", "")
    msg = str(msg or resp.text[:200] or f"HTTP {resp.status_code}")
    if resp.status_code in (401,) or "expired" in msg.lower() or "invalid_token" in msg.lower():
        return AuthExpired(f"{network} : autorisation expirée ou retirée, reconnectez le compte ({msg}).")
    if resp.status_code == 429:
        return PublishError(f"{network} : trop de requêtes, nouvel essai plus tard ({msg}).", retry=True)
    if resp.status_code >= 500:
        return PublishError(f"{network} : le service ne répond pas correctement ({msg}).", retry=True)
    return PublishError(f"{network} : {msg}")


def client(timeout: float = 30.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0), follow_redirects=False,
                             headers={"User-Agent": "Tamtam/1.0"})
