"""Recadrage des images au format de chaque réseau, au moment de publier (l'original n'est pas modifié).

- Toujours : Instagram refuse une image plus haute que 4:5 ou plus large que 1,91:1 ; elle est recadrée au plus
  proche format accepté (au centre).
- Si « adapter le cadrage » est coché sur le post : Instagram 4:5, TikTok 9:16, X 16:9 (Facebook garde l'original).

Les images recadrées sont gardées à côté de l'original (<jeton>-c<ratio>.jpg) et servies à /m/ comme lui.
"""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image

TARGETS = {"instagram": 4 / 5, "tiktok": 9 / 16, "x": 16 / 9}
INSTAGRAM_RANGE = (4 / 5, 1.91)
TOLERANCE = 0.01


def ratio_for(platform: str, width: int | None, height: int | None, auto: bool) -> float | None:
    """Format à appliquer à cette image pour ce réseau, ou None pour garder l'original."""
    if not width or not height:
        return None
    r = width / height
    if auto and platform in TARGETS:
        target = TARGETS[platform]
        return target if abs(r - target) / target > TOLERANCE else None
    if platform == "instagram":
        lo, hi = INSTAGRAM_RANGE
        if r < lo * (1 - TOLERANCE):
            return lo
        if r > hi * (1 + TOLERANCE):
            return hi
    return None


def box(width: int, height: int, ratio: float) -> tuple[int, int, int, int]:
    """Zone centrée au format `ratio` (largeur / hauteur), la plus grande possible."""
    if width / height > ratio:
        w = round(height * ratio)
        x = (width - w) // 2
        return x, 0, x + w, height
    h = round(width / ratio)
    y = (height - h) // 2
    return 0, y, width, y + h


def name_for(token: str, ratio: float) -> str:
    return f"{token}-c{round(ratio * 1000)}.jpg"


def cropped(src: Path, token: str, ratio: float) -> tuple[Path, str]:
    """Chemin et nom du fichier recadré (créé s'il n'existe pas encore)."""
    name = name_for(token, ratio)
    dst = src.with_name(name)
    if not dst.exists():
        with Image.open(src) as im:
            out = im.convert("RGB").crop(box(im.width, im.height, ratio))
            tmp = dst.with_suffix(".tmp")
            out.save(tmp, "JPEG", quality=88, optimize=True, progressive=True)
            os.replace(tmp, dst)
    return dst, name


def remove_all(src: Path, token: str) -> None:
    for f in src.parent.glob(f"{token}-c*.jpg"):
        try:
            f.unlink()
        except FileNotFoundError:
            pass
