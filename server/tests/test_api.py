"""Tests de l'API sur une vraie base PostgreSQL (mode simulation : aucun réseau social n'est contacté).

Lancés seulement si TEST_DATABASE_URL pointe vers une base dont le nom finit par « _test » (elle est vidée).
"""
from __future__ import annotations

import asyncio
import io
import os
import tempfile
from urllib.parse import parse_qs, urlsplit

import psycopg
import pytest
from cryptography.fernet import Fernet

URL = os.environ.get("TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not URL.rsplit("/", 1)[-1].endswith("_test"),
                                reason="TEST_DATABASE_URL (base *_test) non défini")
os.environ["TAMTAM_WORKER"] = "0"   # la publication est déclenchée à la main dans les tests

ADMIN = ("admin@example.test", "admin-password-123")
MEMBER = ("membre@example.test", "membre-password-12")


def _reset_db():
    with psycopg.connect(URL, autocommit=True) as c:
        c.execute("DROP SCHEMA public CASCADE")
        c.execute("CREATE SCHEMA public")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from tamtam.config import load_settings
    from tamtam.main import create_app

    _reset_db()
    settings = load_settings({"DATABASE_URL": URL, "SESSION_SECRET": "t" * 40, "ADMIN_EMAIL": ADMIN[0],
                              "ADMIN_PASSWORD": ADMIN[1], "DATA_DIR": tempfile.mkdtemp(),
                              "TOKEN_KEY": Fernet.generate_key().decode(), "PUBLIC_URL": "https://tamtam.example.test",
                              "SIMULATION": "true"})
    app = create_app(settings)
    with TestClient(app, base_url="https://testserver") as c:
        c.app_ref = app
        login(c, *ADMIN)
        yield c


def login(client, email, password):
    client.cookies.clear()
    client.app_ref.state.limiter._hits.clear()
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text


def ok(r, code=200):
    assert r.status_code == code, r.text
    return r.json()


def png_bytes(color=(200, 30, 30, 128)) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGBA", (3000, 1500), color).save(buf, "PNG")
    return buf.getvalue()


def run_worker(client):
    from tamtam import worker

    app = client.app_ref

    async def go():
        for tid in await worker.claim(app.state.pool, 20):
            await worker.publish_target(app, tid)

    client.portal.call(go)


@pytest.fixture(scope="module")
def project(client):
    return ok(client.post("/api/v1/projects", json={"name": "Appli test", "url": "https://app.example.test"}), 201)


@pytest.fixture(scope="module")
def accounts(client, project):
    out = {}
    for provider in ("meta", "x", "tiktok"):
        r = ok(client.post(f"/api/v1/connect/{provider}/start", json={"project_id": project["id"], "demo": True}))
        cands = ok(client.get(f"/api/v1/connect/pending/{r['choose']}"))["candidates"]
        ok(client.post(f"/api/v1/connect/pending/{r['choose']}", json={"keys": [c["key"] for c in cands]}))
    for a in ok(client.get(f"/api/v1/projects/{project['id']}/accounts")):
        out[a["platform"]] = a
    return out


def test_health_and_auth(client):
    assert client.get("/health").text == "ok"
    client.cookies.clear()
    assert client.get("/api/v1/projects").status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": ADMIN[0], "password": "faux"}).status_code == 401
    login(client, *ADMIN)
    assert ok(client.get("/api/v1/auth/me"))["is_admin"]
    assert client.get("/api/v1/nimporte").status_code == 404


def test_config_errors():
    from tamtam.config import ConfigError, load_settings

    base = {"DATABASE_URL": "postgresql://u:p@h:5432/b", "SESSION_SECRET": "s" * 40, "ADMIN_EMAIL": "a@b.c",
            "TOKEN_KEY": Fernet.generate_key().decode(), "PUBLIC_URL": "https://x.example"}
    for missing in ("DATABASE_URL", "SESSION_SECRET", "ADMIN_EMAIL", "TOKEN_KEY", "PUBLIC_URL"):
        with pytest.raises(ConfigError, match=missing):
            load_settings({k: v for k, v in base.items() if k != missing})
    with pytest.raises(ConfigError, match="TOKEN_KEY"):
        load_settings({**base, "TOKEN_KEY": "pas-une-cle"})
    with pytest.raises(ConfigError, match="PUBLIC_URL"):
        load_settings({**base, "PUBLIC_URL": "tamtam.example"})


def test_csrf_refused(client):
    r = client.post("/api/v1/projects", json={"name": "X"}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_projects(client, project):
    assert client.post("/api/v1/projects", json={"name": "appli TEST"}).status_code == 409
    assert client.post("/api/v1/projects", json={"name": "Mauvais lien", "url": "ftp://x"}).status_code == 422
    p = ok(client.patch(f"/api/v1/projects/{project['id']}", json={"description": "Une appli"}))
    assert p["description"] == "Une appli"
    assert any(x["id"] == project["id"] for x in ok(client.get("/api/v1/projects")))


def test_admin_apps(client):
    apps = ok(client.get("/api/v1/admin/apps"))["apps"]
    x = next(a for a in apps if a["provider"] == "x")
    assert x["redirect_uri"] == "https://tamtam.example.test/api/v1/connect/x/callback"
    assert not x["has_secret"]
    ok(client.put("/api/v1/admin/apps/x", json={"client_id": "cid-x", "client_secret": "secret-x"}))
    x = next(a for a in ok(client.get("/api/v1/admin/apps"))["apps"] if a["provider"] == "x")
    assert x["client_id"] == "cid-x" and x["has_secret"] and "secret-x" not in str(x)
    ok(client.put("/api/v1/admin/apps/x", json={"client_id": "cid-x2"}))  # garde le secret
    with psycopg.connect(URL) as c:
        enc = c.execute("SELECT client_secret_enc FROM app_credentials WHERE provider='x'").fetchone()[0]
    assert enc and "secret-x" not in enc
    assert client.app_ref.state.vault.open(enc) == "secret-x"


def test_oauth_start_and_bad_callback(client, project):
    r = ok(client.post("/api/v1/connect/x/start", json={"project_id": project["id"]}))
    q = parse_qs(urlsplit(r["url"]).query)
    assert q["client_id"] == ["cid-x2"] and q["code_challenge_method"] == ["S256"]
    assert q["redirect_uri"] == ["https://tamtam.example.test/api/v1/connect/x/callback"]
    assert "offline.access" in q["scope"][0]
    # Pas d'application TikTok configurée : message clair
    r = client.post("/api/v1/connect/tiktok/start", json={"project_id": project["id"]})
    assert r.status_code == 422 and "Administration" in r.json()["detail"]
    # Retour avec un état inconnu → retour à la page Comptes avec une erreur
    r = client.get("/api/v1/connect/x/callback?state=faux&code=abc", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/#/comptes?err=")
    # Retour avec refus de l'utilisateur
    state = q["state"][0]
    r = client.get(f"/api/v1/connect/x/callback?state={state}&error=access_denied", follow_redirects=False)
    assert "err=" in r.headers["location"]


def test_demo_accounts(client, accounts):
    assert set(accounts) == {"instagram", "facebook", "x", "tiktok"}
    assert all(a["simulated"] for a in accounts.values())
    assert "access_token" not in str(accounts)
    r = ok(client.post(f"/api/v1/accounts/{accounts['x']['id']}/test"))
    assert r["ok"]
    a = ok(client.patch(f"/api/v1/accounts/{accounts['tiktok']['id']}", json={"privacy": "SELF_ONLY"}))
    assert a["meta"]["privacy"] == "SELF_ONLY"
    assert client.patch(f"/api/v1/accounts/{accounts['x']['id']}", json={"privacy": "SELF_ONLY"}).status_code == 422


def test_media_upload(client, project):
    m = ok(client.post(f"/api/v1/projects/{project['id']}/media",
                       files={"file": ("photo.png", png_bytes(), "image/png")}), 201)
    assert m["kind"] == "image" and m["mime"] == "image/jpeg" and max(m["width"], m["height"]) == 2048
    r = client.get(m["url"])
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert r.headers["cross-origin-resource-policy"] == "cross-origin"
    bad = client.post(f"/api/v1/projects/{project['id']}/media", files={"file": ("x.txt", b"bonjour", "text/plain")})
    assert bad.status_code == 422
    vid = ok(client.post(f"/api/v1/projects/{project['id']}/media",
                         files={"file": ("v.mp4", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 100, "video/mp4")}), 201)
    assert vid["kind"] == "video" and vid["url"].endswith(".mp4")
    assert client.get("/m/../../etc/passwd").status_code == 404


def test_validation(client, project, accounts):
    base = {"project_id": project["id"], "mode": "now"}
    r = client.post("/api/v1/posts", json={**base, "body": "Sans image", "account_ids": [accounts["instagram"]["id"]]})
    assert r.status_code == 422 and "Instagram" in r.json()["detail"]
    r = client.post("/api/v1/posts", json={**base, "body": "a" * 281, "account_ids": [accounts["x"]["id"]]})
    assert r.status_code == 422 and "X" in r.json()["detail"]
    # un texte adapté pour X résout le problème
    ok(client.post("/api/v1/posts", json={**base, "mode": "draft", "body": "a" * 281,
                                          "account_ids": [accounts["x"]["id"]]}), 201)
    r = client.post("/api/v1/posts", json={**base, "body": "a" * 281, "account_ids": [accounts["x"]["id"]],
                                           "overrides": {str(accounts["x"]["id"]): "court"}})
    assert r.status_code == 201
    r = client.post("/api/v1/posts", json={**base, "mode": "at", "body": "hier", "account_ids": [accounts["x"]["id"]],
                                           "scheduled_at": "2020-01-01T10:00:00Z"})
    assert r.status_code == 422 and "passée" in r.json()["detail"]


def test_publish_flow_and_links(client, project, accounts):
    img = ok(client.post(f"/api/v1/projects/{project['id']}/media",
                         files={"file": ("p.png", png_bytes((10, 120, 90, 255)), "image/png")}), 201)
    ids = [accounts[p]["id"] for p in ("instagram", "facebook", "x", "tiktok")]
    post = ok(client.post("/api/v1/posts", json={
        "project_id": project["id"], "mode": "now", "body": "Nouvelle version !", "account_ids": ids,
        "media_ids": [img["id"]], "link_url": "https://app.example.test/dl?ref=a&utm_source=old",
        "campaign": "lancement", "facebook_short_link": True}), 201)
    assert post["status"] == "scheduled" and len(post["targets"]) == 4 and post["facebook_short_link"]
    run_worker(client)
    post = ok(client.get(f"/api/v1/posts/{post['id']}"))
    assert post["status"] == "done", post
    assert all(t["status"] == "published" for t in post["targets"])
    # liens suivis seulement là où ils sont cliquables (Facebook, X)
    coded = {t["platform"]: t["link_code"] for t in post["targets"]}
    assert coded["facebook"] and coded["x"] and not coded["instagram"] and not coded["tiktok"]
    r = client.get(f"/l/{coded['x']}", follow_redirects=False)
    assert r.status_code == 302
    q = parse_qs(urlsplit(r.headers["location"]).query)
    assert q["utm_source"] == ["x"] and q["utm_campaign"] == ["lancement"] and q["ref"] == ["a"]
    assert q["utm_content"] == [f"post-{post['id']}"]
    client.get(f"/l/{coded['x']}", follow_redirects=False)
    client.get(f"/l/{coded['facebook']}", follow_redirects=False)
    assert client.get("/l/inconnu", follow_redirects=False).status_code == 404
    st = ok(client.get(f"/api/v1/stats?project_id={project['id']}"))
    clicks = {r["platform"]: r["clicks"] for r in st["by_platform"]}
    assert clicks["x"] == 2 and clicks["facebook"] == 1
    assert st["top"][0]["id"] == post["id"]
    # sans l'option, Facebook reçoit le lien direct : pas de lien court ; X garde le sien
    p2 = ok(client.post("/api/v1/posts", json={
        "project_id": project["id"], "mode": "now", "body": "Sans lien court", "account_ids": ids[1:3],
        "link_url": "https://app.example.test/"}), 201)
    assert p2["facebook_short_link"] is False
    run_worker(client)
    p2 = ok(client.get(f"/api/v1/posts/{p2['id']}"))
    coded = {t["platform"]: t["link_code"] for t in p2["targets"]}
    assert p2["status"] == "done" and not coded["facebook"] and coded["x"]
    # un post publié ne se modifie plus, et le média utilisé reste supprimable après publication
    r = client.put(f"/api/v1/posts/{post['id']}", json={"project_id": project["id"], "body": "x", "mode": "draft"})
    assert r.status_code == 409
    assert client.post(f"/api/v1/posts/{post['id']}/retry").status_code == 409


def test_failure_and_retry(client, project, accounts):
    post = ok(client.post("/api/v1/posts", json={"project_id": project["id"], "mode": "now", "body": "Essai",
                                                 "account_ids": [accounts["x"]["id"], accounts["facebook"]["id"]]}), 201)
    with psycopg.connect(URL, autocommit=True) as c:   # le compte X disparaît avant la publication
        c.execute("UPDATE post_targets SET social_account_id=NULL WHERE post_id=%s AND platform='x'", (post["id"],))
    run_worker(client)
    post = ok(client.get(f"/api/v1/posts/{post['id']}"))
    assert post["status"] == "partial"
    x = next(t for t in post["targets"] if t["platform"] == "x")
    assert x["status"] == "failed" and "reconnectez" in x["error"]
    post = ok(client.post(f"/api/v1/posts/{post['id']}/retry"))
    assert post["status"] in ("scheduled", "publishing")
    assert next(t for t in post["targets"] if t["platform"] == "facebook")["status"] == "published"


def test_interrupted_publication(client, project, accounts):
    from tamtam import worker

    post = ok(client.post("/api/v1/posts", json={"project_id": project["id"], "mode": "now", "body": "Coupé",
                                                 "account_ids": [accounts["x"]["id"]]}), 201)
    with psycopg.connect(URL, autocommit=True) as c:
        c.execute("UPDATE post_targets SET status='publishing' WHERE post_id=%s", (post["id"],))
    client.portal.call(worker.reset_interrupted, client.app_ref.state.pool)
    post = ok(client.get(f"/api/v1/posts/{post['id']}"))
    assert post["status"] == "failed" and "redémarrage" in post["targets"][0]["error"]


def test_draft_edit_and_delete(client, project, accounts):
    d = ok(client.post("/api/v1/posts", json={"project_id": project["id"], "mode": "draft", "body": "brouillon"}), 201)
    assert d["status"] == "draft"
    d = ok(client.put(f"/api/v1/posts/{d['id']}", json={"project_id": project["id"], "mode": "at", "body": "prêt",
                                                       "account_ids": [accounts["facebook"]["id"]],
                                                       "scheduled_at": "2099-01-01T09:00:00+01:00"}))
    assert d["status"] == "scheduled" and d["targets"][0]["platform"] == "facebook"
    run_worker(client)  # pas encore l'heure
    assert ok(client.get(f"/api/v1/posts/{d['id']}"))["status"] == "scheduled"
    lst = ok(client.get(f"/api/v1/posts?project_id={project['id']}&status=upcoming"))
    assert any(p["id"] == d["id"] for p in lst)
    ok(client.delete(f"/api/v1/posts/{d['id']}"))
    assert client.get(f"/api/v1/posts/{d['id']}").status_code == 404


def test_member_rights(client):
    ok(client.post("/api/v1/admin/users", json={"email": MEMBER[0], "password": MEMBER[1], "name": "Membre"}), 201)
    login(client, *MEMBER)
    assert client.get("/api/v1/admin/apps").status_code == 403
    assert client.get("/api/v1/projects").status_code == 200
    login(client, *ADMIN)


def test_rules_unit():
    from tamtam.platforms import check, text_length

    assert text_length("x", "a" * 250, "https://long.example/" + "z" * 100) == 250 + 1 + 23
    assert check("x", "a" * 256, [], True) == []
    assert check("x", "a" * 257, [], True)
    assert check("tiktok", "ok", ["image", "video"])
    assert check("instagram", "ok", ["image", "video"]) == []
    assert check("x", "ok", ["image"] * 5)


def test_concurrent_targets_finish_done(client, project, accounts):
    """Plusieurs réseaux publiés en parallèle : le post doit finir « done », pas rester « publishing »."""
    from tamtam import worker

    ids = [accounts[p]["id"] for p in ("facebook", "x")]
    post = ok(client.post("/api/v1/posts", json={"project_id": project["id"], "mode": "now", "body": "Parallèle",
                                                 "account_ids": ids}), 201)
    app = client.app_ref

    async def go():
        import asyncio as aio
        tids = await worker.claim(app.state.pool, 20)
        await aio.gather(*(worker.publish_target(app, t) for t in tids))

    client.portal.call(go)
    assert ok(client.get(f"/api/v1/posts/{post['id']}"))["status"] == "done"
