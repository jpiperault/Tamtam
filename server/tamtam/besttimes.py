"""Meilleurs moments pour publier, d'après les chiffres des posts déjà publiés.

Chaque réseau a son échelle (1 000 vues sur X ne valent pas 1 000 vues sur TikTok) : chaque post est donc comparé à
la moyenne de son réseau sur la période. Un score de 1,4 veut dire « 40 % de mieux que d'habitude sur ce réseau ».
Le score d'un post mélange la portée (vues, ou à défaut personnes touchées) et les réactions (j'aime, commentaires,
partages, enregistrements), quand le réseau les donne.

On regroupe ensuite par jour de la semaine et par heure (heure du serveur). Un moment n'est proposé que s'il compte
au moins MIN_POSTS posts mesurés, et le résultat n'est jugé fiable qu'à partir de ENOUGH posts mesurés en tout.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

ENOUGH = 8
MIN_POSTS = 2
TOP = 6


def _sum(r: dict, keys: tuple[str, ...]) -> float | None:
    vals = [r[k] for k in keys if r.get(k) is not None]
    return float(sum(vals)) if vals else None


def scores(rows: list[dict]) -> list[tuple[dict, float]]:
    """(ligne, score relatif à la moyenne de son réseau) pour chaque post mesuré."""
    reach = lambda r: r["views"] if r.get("views") is not None else r.get("reach")  # noqa: E731
    eng = lambda r: _sum(r, ("likes", "comments", "shares", "saves"))  # noqa: E731
    by_net: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_net[r["platform"]].append(r)
    out = []
    for net_rows in by_net.values():
        avg = {}
        for name, f in (("reach", reach), ("eng", eng)):
            vals = [f(r) for r in net_rows if f(r) is not None]
            avg[name] = (sum(vals) / len(vals)) if vals else 0
        for r in net_rows:
            parts = []
            for name, f in (("reach", reach), ("eng", eng)):
                v = f(r)
                if v is not None and avg[name] > 0:
                    parts.append(v / avg[name])
            if parts:
                out.append((r, sum(parts) / len(parts)))
    return out


def compute(rows: list[dict], tz_name: str) -> dict:
    tz = ZoneInfo(tz_name)
    scored = scores(rows)
    buckets: dict[tuple[int, int], list[float]] = defaultdict(list)
    minutes: dict[tuple[int, int], Counter] = defaultdict(Counter)
    days: dict[int, list[float]] = defaultdict(list)
    hours: dict[int, list[float]] = defaultdict(list)
    for r, s in scored:
        local: datetime = r["published_at"].astimezone(tz)
        key = (local.weekday(), local.hour)
        buckets[key].append(s)
        minutes[key][local.strftime("%H:%M")] += 1
        days[local.weekday()].append(s)
        hours[local.hour].append(s)
    mean = lambda xs: round(sum(xs) / len(xs), 2)  # noqa: E731
    slots = [{"day": d, "hour": h, "time": minutes[(d, h)].most_common(1)[0][0], "score": mean(v), "posts": len(v)}
             for (d, h), v in buckets.items() if len(v) >= MIN_POSTS]
    slots.sort(key=lambda x: (-x["score"], -x["posts"], x["day"], x["hour"]))
    return {
        "measured": len(scored),
        "enough": len(scored) >= ENOUGH,
        "best": [s for s in slots if s["score"] >= 1][:TOP],
        "worst": sorted((s for s in slots if s["score"] < 1), key=lambda x: x["score"])[:3],
        "by_day": [{"day": d, "score": mean(days[d]) if days[d] else None, "posts": len(days[d])} for d in range(7)],
        "by_hour": [{"hour": h, "score": mean(hours[h]) if hours[h] else None, "posts": len(hours[h])}
                    for h in range(24)],
    }
