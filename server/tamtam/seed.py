"""Données de démonstration (DEMO_DATA=true) : deux projets fictifs avec des comptes simulés et quelques posts."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from psycopg.types.json import Jsonb


async def seed_if_empty(conn, admin_id: int) -> bool:
    cur = await conn.execute("SELECT count(*) AS n FROM projects")
    if (await cur.fetchone())["n"]:
        return False
    now = datetime.now(timezone.utc)
    projects = [
        ("Vent Fort (exemple)", "https://ventfort.example", "Appli météo pour le kitesurf.", "#0E6E5C"),
        ("Le Bon Plat (exemple)", "https://lebonplat.example", "Site de recettes du quotidien.", "#B5532A"),
    ]
    ids = []
    for name, url, desc, color in projects:
        cur = await conn.execute("INSERT INTO projects(name, url, description, color) VALUES (%s,%s,%s,%s) RETURNING id",
                                 (name, url, desc, color))
        ids.append((await cur.fetchone())["id"])
    acc = {}
    for pid, handle in ((ids[0], "ventfort.demo"), (ids[1], "lebonplat.demo")):
        for platform in ("instagram", "facebook", "x"):
            cur = await conn.execute(
                "INSERT INTO social_accounts(project_id, platform, external_id, name, handle, access_token_enc, meta, "
                "simulated, connected_by) VALUES (%s,%s,%s,%s,%s,NULL,%s,true,%s) RETURNING id",
                (pid, platform, f"demo-{platform}-{pid}", "Compte démo", handle, Jsonb({}), admin_id))
            acc[(pid, platform)] = (await cur.fetchone())["id"]
    posts = [
        (ids[0], "La v2 de Vent Fort est là 🪁\nPrévisions à 1 km près et alertes quand votre spot dépasse 18 nœuds.",
         "https://ventfort.example/telecharger", "lancement-v2", now + timedelta(days=1, hours=2), "scheduled",
         ("facebook", "x")),
        (ids[0], "Astuce : activez le mode hors-ligne avant d'aller à la plage.", "", "", None, "draft", ("x",)),
        (ids[1], "Recette du vendredi : la tarte fine aux tomates, prête en 25 minutes.",
         "https://lebonplat.example/tarte-tomates", "recette-vendredi", now + timedelta(days=3), "scheduled",
         ("facebook", "x")),
    ]
    for pid, body, link, campaign, when, status, nets in posts:
        cur = await conn.execute("INSERT INTO posts(project_id, created_by, body, link_url, campaign, scheduled_at, status) "
                                 "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                                 (pid, admin_id, body, link, campaign, when, status))
        post_id = (await cur.fetchone())["id"]
        for n in nets:
            await conn.execute("INSERT INTO post_targets(post_id, social_account_id, platform) VALUES (%s,%s,%s)",
                               (post_id, acc[(pid, n)], n))
    await conn.commit()
    return True
