"""Visuels d'annonce générés à partir de modèles : titre, accroche, capture d'écran, couleur du projet.

Formats : carré (1080×1080, tous réseaux), portrait (1080×1350, conseillé sur Instagram et Facebook), story
(1080×1920, TikTok, Shorts, stories) et paysage (1600×900, X, LinkedIn, Bluesky).
Modèles :
- « annonce » : fond à la couleur du projet, grand titre, capture d'écran qui dépasse en bas ;
- « clair » : fond clair, bandeau de couleur, capture à côté (paysage) ou dessous ;
- « citation » : un avis ou une phrase forte entre guillemets, avec sa signature.
Le visuel est enregistré en JPEG (Instagram n'accepte que ce format) dans la médiathèque du projet.
Police : Inter (licence SIL Open Font License, fichier fonts/OFL.txt).
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

FONTS = Path(__file__).parent / "fonts"
FORMATS = {"carre": (1080, 1080), "portrait": (1080, 1350), "story": (1080, 1920), "paysage": (1600, 900)}
TEMPLATES = ("annonce", "clair", "citation")
LIGHT_BG = (246, 244, 239)
DARK = (22, 33, 30)


class VisualError(Exception):
    pass


@dataclass
class Spec:
    template: str = "annonce"
    format: str = "carre"
    title: str = ""
    subtitle: str = ""
    badge: str = ""          # petite étiquette au-dessus du titre : « Nouveau », « Version 2.1 »…
    footer: str = ""         # en bas : nom de l'appli, adresse du site
    color: str = "#0E6E5C"
    screenshot: Path | None = None


@lru_cache(maxsize=64)
def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / ("Inter-Bold.ttf" if bold else "Inter-Regular.ttf")), size)


def rgb(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    if len(c) != 6:
        raise VisualError("couleur invalide (format #RRVVBB)")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def luminance(c: tuple[int, int, int]) -> float:
    def ch(v: int) -> float:
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def ink_on(c: tuple[int, int, int]) -> tuple[int, int, int]:
    """Texte lisible sur le fond `c` : blanc ou presque noir, selon le meilleur contraste."""
    lum = luminance(c)
    return (255, 255, 255) if (1.05 / (lum + 0.05)) >= ((lum + 0.05) / (luminance(DARK) + 0.05)) else DARK


def shade(c: tuple[int, int, int], f: float) -> tuple[int, int, int]:
    """f < 0 assombrit, f > 0 éclaircit."""
    return tuple(int(v + (255 - v) * f) if f > 0 else int(v * (1 + f)) for v in c)  # type: ignore[return-value]


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, width: int) -> list[str]:
    lines: list[str] = []
    for para in text.splitlines() or [""]:
        words, cur = para.split(), ""
        for w in words:
            test = f"{cur} {w}".strip()
            if draw.textlength(test, font=fnt) <= width or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def fit(draw, text: str, width: int, max_lines: int, start: int, minimum: int, bold: bool):
    """Plus grande taille (de `start` à `minimum`) où le texte tient en `max_lines` lignes."""
    size = start
    while True:
        fnt = font(size, bold)
        lines = wrap(draw, text, fnt, width)
        if len(lines) <= max_lines or size <= minimum:
            return fnt, lines[:max_lines] if size <= minimum else lines
        size -= 4


def block(draw, xy, lines, fnt, fill, spacing=1.15, align="left", width=0) -> int:
    """Écrit les lignes ; renvoie l'ordonnée sous le bloc."""
    x, y = xy
    asc, desc = fnt.getmetrics()
    step = int((asc + desc) * spacing)
    for line in lines:
        lx = x + (width - draw.textlength(line, font=fnt)) / 2 if align == "center" else x
        draw.text((lx, y), line, font=fnt, fill=fill)
        y += step
    return y


def rounded(img: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def paste_shot(canvas: Image.Image, shot: Image.Image, box: tuple[int, int, int, int], radius: int,
               anchor_top: bool = True) -> None:
    """Capture réduite pour tenir dans `box` (x, y, largeur max, hauteur max), coins arrondis et ombre douce."""
    x, y, bw, bh = box
    shot = shot.copy()
    shot.thumbnail((bw, bh * 3 if anchor_top else bh))
    if anchor_top and shot.height > bh:              # la capture « dépasse » : on la coupe au bord du visuel
        shot = shot.crop((0, 0, shot.width, bh))
    shot = rounded(shot.convert("RGB"), radius)
    px = x + (bw - shot.width) // 2
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((px + 6, y + 14, px + shot.width + 6, y + shot.height + 14), radius, fill=(0, 0, 0, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(shot, (px, y))


def load_shot(path: Path | None) -> Image.Image | None:
    if not path:
        return None
    try:
        with Image.open(path) as im:
            return ImageOps.exif_transpose(im).convert("RGB")
    except (OSError, ValueError) as exc:
        raise VisualError("capture d'écran illisible") from exc


def badge(draw, xy, text: str, size: int, bg, fg) -> int:
    fnt = font(size, True)
    pad_x, pad_y = int(size * 0.7), int(size * 0.35)
    w = draw.textlength(text, font=fnt)
    asc, desc = fnt.getmetrics()
    x, y = xy
    draw.rounded_rectangle((x, y, x + w + 2 * pad_x, y + asc + desc + 2 * pad_y), (asc + desc) // 2 + pad_y, fill=bg)
    draw.text((x + pad_x, y + pad_y), text, font=fnt, fill=fg)
    return y + asc + desc + 2 * pad_y


def render(spec: Spec) -> Image.Image:
    if spec.template not in TEMPLATES:
        raise VisualError("modèle inconnu")
    if spec.format not in FORMATS:
        raise VisualError("format inconnu")
    if not (spec.title.strip() or spec.screenshot):
        raise VisualError("donnez au moins un titre ou une capture d'écran")
    W, H = FORMATS[spec.format]
    color = rgb(spec.color)
    shot = load_shot(spec.screenshot)
    landscape = W > H
    m = int(min(W, H) * 0.08)                         # marge
    u = min(W, H) / 1080                              # unité : tailles pensées pour 1080 px
    canvas = Image.new("RGBA", (W, H), LIGHT_BG + (255,))
    d = ImageDraw.Draw(canvas)

    if spec.template == "citation":
        bg, fg = color, ink_on(color)
        top, bottom = shade(color, 0.12), shade(color, -0.18)
        for yy in range(H):                           # léger dégradé vertical
            t = yy / max(1, H - 1)
            d.line([(0, yy), (W, yy)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
        qf = font(int(260 * u), True)
        d.text((m - int(10 * u), m - int(60 * u)), "“", font=qf, fill=shade(bg, 0.25) if fg != DARK else shade(bg, -0.25))
        width = W - 2 * m
        fnt, lines = fit(d, spec.title.strip() or " ", width, 7 if not landscape else 4, int(84 * u), int(40 * u), True)
        asc, desc = fnt.getmetrics()
        text_h = len(lines) * int((asc + desc) * 1.2)
        y = max(m + int(150 * u), (H - text_h) // 2 - int(40 * u))
        y = block(d, (m, y), lines, fnt, fg, 1.2)
        if spec.subtitle.strip():
            sf = font(int(40 * u))
            block(d, (m, y + int(36 * u)), wrap(d, "— " + spec.subtitle.strip(), sf, width)[:2], sf, fg)
        if spec.footer.strip():
            ff = font(int(34 * u), True)
            d.text((m, H - m - int(34 * u)), spec.footer.strip(), font=ff, fill=fg)
        return canvas.convert("RGB")

    if spec.template == "annonce":
        fg = ink_on(color)
        top, bottom = shade(color, 0.10), shade(color, -0.22)
        for yy in range(H):
            t = yy / max(1, H - 1)
            d.line([(0, yy), (W, yy)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
        badge_bg, badge_fg = (fg, color) if fg != DARK else (DARK, (255, 255, 255))
        title_fill, sub_fill = fg, (fg if fg == DARK else (235, 240, 238))
    else:  # clair
        fg = DARK
        d.rectangle((0, 0, W, int(18 * u)), fill=color)
        badge_bg, badge_fg = color, ink_on(color)
        title_fill, sub_fill = DARK, (80, 94, 90)

    # Zone de texte : à gauche en paysage avec capture, sinon en haut.
    text_w = (W - 2 * m) if not (landscape and shot) else int(W * 0.5) - m
    y = m + (int(18 * u) if spec.template == "clair" else 0)
    center = not landscape and not shot and spec.format != "paysage"
    if spec.badge.strip():
        if center:
            bf = font(int(34 * u), True)
            bw = d.textlength(spec.badge.strip(), font=bf) + 2 * int(34 * u * 0.7)
            y = badge(d, (int((W - bw) / 2), y), spec.badge.strip(), int(34 * u), badge_bg, badge_fg) + int(28 * u)
        else:
            y = badge(d, (m, y), spec.badge.strip(), int(34 * u), badge_bg, badge_fg) + int(28 * u)
    max_title = 3 if shot else 5
    if spec.format == "story":
        max_title += 1
    if center:                                        # sans capture : texte centré verticalement
        fnt, lines = fit(d, spec.title.strip() or " ", text_w, max_title, int(110 * u), int(52 * u), True)
        asc, desc = fnt.getmetrics()
        th = len(lines) * int((asc + desc) * 1.1)
        if spec.subtitle.strip():
            th += int(150 * u)
        y = max(y, (H - th) // 2 - int(30 * u))
    else:
        fnt, lines = fit(d, spec.title.strip() or " ", text_w, max_title, int(96 * u), int(48 * u), True)
    y = block(d, (m, y), lines, fnt, title_fill, 1.1, "center" if center else "left", text_w)
    if spec.subtitle.strip():
        sf = font(int(42 * u))
        y = block(d, (m, y + int(18 * u)), wrap(d, spec.subtitle.strip(), sf, text_w)[:3], sf, sub_fill, 1.25,
                  "center" if center else "left", text_w)
    if spec.footer.strip():
        ff = font(int(32 * u), True)
        fy = H - m - int(32 * u)
        if shot and not landscape:                    # la capture occupe le bas : pied de page sous le texte
            fy = y + int(20 * u)
            y = fy + int(40 * u)
        fx = (W - d.textlength(spec.footer.strip(), font=ff)) / 2 if center else m
        d.text((fx, fy), spec.footer.strip(), font=ff, fill=sub_fill)
    if shot:
        radius = int(36 * u)
        if landscape:
            paste_shot(canvas, shot, (int(W * 0.5) + m // 2, m, int(W * 0.5) - int(m * 1.5), H - 2 * m), radius,
                       anchor_top=False)
        else:
            top_y = y + int(50 * u)
            paste_shot(canvas, shot, (m, top_y, W - 2 * m, H - top_y), radius, anchor_top=True)
    return canvas.convert("RGB")


def save_jpeg(img: Image.Image, path: Path) -> None:
    img.save(path, "JPEG", quality=92, optimize=True, progressive=True)


def preview(img: Image.Image, width: int = 540) -> Image.Image:
    out = img.copy()
    out.thumbnail((width, width * 2))
    return out
