"""Créneaux de publication d'un projet : « mardi 18:30, jeudi 12:00… ».

Un post « dans la file » prend le prochain créneau libre du projet (aucun autre post du projet à cette minute).
Les heures sont celles du fuseau du serveur (variable TZ, Europe/Paris par défaut).
"""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
HORIZON_DAYS = 400


def clean(slots: list[dict]) -> list[dict]:
    """Créneaux valides, sans doublon, triés (lève ValueError sinon)."""
    out = set()
    for s in slots:
        day, at = s.get("day"), str(s.get("time", ""))
        if not isinstance(day, int) or not 0 <= day <= 6 or not TIME_RE.match(at):
            raise ValueError("créneau invalide : jour de 0 (lundi) à 6 (dimanche) et heure HH:MM")
        out.add((day, at))
    if len(out) > 50:
        raise ValueError("50 créneaux au plus par projet")
    return [{"day": d, "time": t} for d, t in sorted(out)]


def _minute(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(second=0, microsecond=0)


def upcoming(slots: list[dict], tz_name: str, taken: set[datetime], after: datetime, count: int = 1) -> list[datetime]:
    """Les `count` prochains créneaux libres après `after` (en UTC). Liste plus courte s'il n'y en a pas assez."""
    if not slots or count <= 0:
        return []
    tz = ZoneInfo(tz_name)
    busy = {_minute(t) for t in taken}
    after = after + timedelta(minutes=2)   # marge : un créneau dans la minute qui vient serait déjà passé
    start: date = after.astimezone(tz).date()
    out: list[datetime] = []
    for offset in range(HORIZON_DAYS):
        day = start + timedelta(days=offset)
        for s in slots:
            if s["day"] != day.weekday():
                continue
            hh, mm = map(int, s["time"].split(":"))
            when = datetime.combine(day, time(hh, mm), tzinfo=tz).astimezone(timezone.utc)
            if when <= after or when in busy:
                continue
            out.append(when)
            busy.add(when)
            if len(out) >= count:
                return out
    return out


async def taken(conn, project_id: int, exclude_post: int | None = None) -> set[datetime]:
    """Heures déjà occupées par un post du projet (programmé, publié ou brouillon daté)."""
    cur = await conn.execute("SELECT scheduled_at FROM posts WHERE project_id=%s AND scheduled_at IS NOT NULL "
                             "AND scheduled_at > now() - interval '1 day' AND id <> %s",
                             (project_id, exclude_post or 0))
    return {r["scheduled_at"] for r in await cur.fetchall()}


def describe(slots: list[dict]) -> str:
    return ", ".join(f"{DAYS[s['day']]} {s['time']}" for s in slots)
