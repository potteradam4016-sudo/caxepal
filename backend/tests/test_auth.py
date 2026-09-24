from sqlalchemy import select, update
from app.models import AuthSession, Profile, ProfileInterest, User, now_ts
from tests.conftest import PASSWORD


def test_root_health_and_empty_database(client):
    assert client.get("/").status_code == 200
    assert client.get("/health").json()["database"] == "ok"
    assert client.get("/api/notices").json()["total"] == 0
    assert {x["code"] for x in client.get("/api/sources").json()} == {"SCNU_MAIN", "SCNU_SW", "SCNU_AI"}


def test_register_login_and_hash(client, app):
    body = {"username": "Alice_1", "password": PASSWORD}
    assert client.post("/api/auth/register", json=body).status_code == 201
    with app.state.sessions() as db:
        user = db.scalar(select(User))
        assert user.username == "alice_1"
        assert user.password_hash.startswith("$argon2id$")
        assert PASSWORD not in user.password_hash
    login = client.post("/api/auth/login", json=body)
    assert login.status_code == 200
    assert login.json()["user"]["username"] == "alice_1"
    assert login.json()["user"]["onboarding_complete"] is False


def test_username_format_and_duplicate(client):
    for username in ("bad@name", "a", "한글아이디", "has-dash"):
        assert client.post("/api/auth/register", json={"username": username, "password": PASSWORD}).status_code == 422
    assert client.post("/api/auth/register", json={"username": "alice", "password": PASSWORD}).status_code == 201
    assert client.post("/api/auth/register", json={"username": "ALICE", "password": "different-passphrase-123"}).status_code == 409
    assert client.post("/api/auth/login", json={"username": "alice", "password": PASSWORD}).status_code == 200


def test_logout_revokes_token_immediately(client, user_factory):
    headers, _ = user_factory()
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_logout_all_revokes_other_sessions(client, user_factory):
    headers, _ = user_factory()
    login = client.post("/api/auth/login", json={"username": "alice", "password": PASSWORD}).json()
    other = {"Authorization": "Bearer " + login["access_token"]}
    assert client.post("/api/auth/logout-all", headers=headers).status_code == 204
    assert client.get("/api/auth/me", headers=other).status_code == 401


def test_change_password_requires_current_password_and_revokes_sessions(client, user_factory):
    headers, _ = user_factory()
    body = {"current_password": "wrong", "new_password": "new-valid-passphrase-123"}
    assert client.post("/api/auth/change-password", headers=headers, json=body).status_code == 401
    body["current_password"] = PASSWORD
    assert client.post("/api/auth/change-password", headers=headers, json=body).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    assert client.post("/api/auth/login", json={"username": "alice", "password": PASSWORD}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "alice", "password": body["new_password"]}).status_code == 200


def test_removed_recovery_routes(client):
    for route in ("/api/auth/verify-email", "/api/auth/resend-verification", "/api/auth/forgot-password", "/api/auth/reset-password"):
        assert client.post(route, json={}).status_code == 404


def test_expired_session_rejected(client, user_factory, app):
    headers, _ = user_factory()
    with app.state.sessions() as db:
        db.execute(update(AuthSession).values(expires_at=now_ts() - 1))
        db.commit()
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_validation_never_echoes_password(client):
    password = "secret"
    response = client.post("/api/auth/register", json={"username": "bad@name", "password": password})
    assert response.status_code == 422
    assert password not in response.text
    assert "input" not in response.text


def test_private_endpoints_require_auth(client):
    for path in ("/api/profile", "/api/bookmarks", "/api/calendar?month=2026-09", "/api/notices/recommended", "/api/admin/crawl-jobs"):
        assert client.get(path).status_code == 401


def test_wrong_credentials_are_generic(client, user_factory):
    user_factory()
    a = client.post("/api/auth/login", json={"username": "alice", "password": "bad"})
    b = client.post("/api/auth/login", json={"username": "missing", "password": "bad"})
    assert a.status_code == b.status_code == 401
    assert a.json()["error"]["code"] == b.json()["error"]["code"]


def test_account_deletion_cascades(client, user_factory, app, notice_factory):
    headers, ident = user_factory()
    notice = notice_factory()
    client.post(f"/api/bookmarks/{notice}", headers=headers)
    assert client.request("DELETE", "/api/auth/account", headers=headers, json={"password": PASSWORD}).status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    with app.state.sessions() as db:
        assert db.get(User, ident) is None
        assert db.get(Profile, ident) is None
        assert db.scalar(select(ProfileInterest).where(ProfileInterest.user_id == ident)) is None
