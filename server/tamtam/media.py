"""Médias : enregistrement des fichiers envoyés dans /data/media.

Les images sont converties en JPEG (Instagram n'accepte que ce format) et réduites à 2048 px au plus grand côté,
ce qui les garde sous la limite de 5 Mo de X. Les vidéos (MP4 ou MOV) sont gardées telles quelles.
"""
from __future__ import annotations

import os
import secrets
import shutil
from pathlib import Path

from PIL import Image, ImageOps

IMAGE_MAX_SIDE = 2048
VIDEO_TYPES = {"video/mp4": ".mp4", "video/quicktime": ".mov"}


class MediaError(Exception):
    pass


def media_dir(data_dir: str) -> Path:
    d = Path(data_dir) / "media"
    d.mkdir(parents=True, exist_ok=True)
    return d


def path_for(data_dir: str, token: str, ext: str) -> Path:
    return Path(data_dir) / "media" / f"{token}{ext}"


def _is_video(head: bytes) -> str | None:
    if len(head) >= 12 and head[4:8] == b"ftyp":
        brand = head[8:12]
        return "video/quicktime" if brand == b"qt  " else "video/mp4"
    return None


def store(src: Path, data_dir: str) -> dict:
    """Range le fichier temporaire `src` dans le dossier des médias ; renvoie ses caractéristiques."""
    with open(src, "rb") as f:
        head = f.read(16)
    token = secrets.token_urlsafe(16)
    out_dir = media_dir(data_dir)
    vmime = _is_video(head)
    if vmime:
        ext = VIDEO_TYPES[vmime]
        dst = out_dir / f"{token}{ext}"
        shutil.copyfile(src, dst)
        width = height = duration = None
        try:
            import av

            with av.open(str(dst)) as c:
                if c.streams.video:
                    v = c.streams.video[0]
                    width, height = v.codec_context.width or None, v.codec_context.height or None
                duration = round(float(c.duration) / 1_000_000, 2) if c.duration else None
        except Exception:  # noqa: BLE001 - une vidéo que PyAV ne lit pas reste acceptée (durée inconnue)
            pass
        return {"token": token, "ext": ext, "mime": vmime, "kind": "video", "size": dst.stat().st_size,
                "width": width, "height": height, "duration_s": duration}
    try:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, mask=im.split()[-1])
                im = bg
            elif im.mode != "RGB":
                im = im.convert("RGB")
            im.thumbnail((IMAGE_MAX_SIDE, IMAGE_MAX_SIDE))
            dst = out_dir / f"{token}.jpg"
            tmp = dst.with_suffix(".tmp")
            im.save(tmp, "JPEG", quality=88, optimize=True, progressive=True)
            os.replace(tmp, dst)
            w, h = im.size
    except (OSError, Image.DecompressionBombError, ValueError) as exc:
        raise MediaError("format non reconnu : envoyez une image (JPEG, PNG, WebP) ou une vidéo MP4 / MOV") from exc
    return {"token": token, "ext": ".jpg", "mime": "image/jpeg", "kind": "image", "size": dst.stat().st_size,
            "width": w, "height": h, "duration_s": None}


def remove(data_dir: str, token: str, ext: str) -> None:
    from . import crop

    src = path_for(data_dir, token, ext)
    crop.remove_all(src, token)
    try:
        src.unlink()
    except FileNotFoundError:
        pass
