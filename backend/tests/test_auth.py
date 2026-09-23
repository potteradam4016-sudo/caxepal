from sqlalchemy import select, update
from app.models import AuthSession, AuthToken, Profile, ProfileInterest, User, now_ts
from app.security import digest_token
from tests.conftest import PASSWORD, latest_token

def test_root_health_and_empty_database(client):
    assert client.get("/").status_code == 200
    assert client.get("/health").json()["database"] == "ok"
    assert client.get("/api/notices").json()["total"] == 0
    assert {x["code"] for x in client.get("/api/sources").json()} == {"SCNU_MAIN","SCNU_SW","SCNU_AI"}

def test_register_requires_verification_and_hashes_password(client,settings,app):
    email = "Alice@example.com"
    body = {"email":email, "password":PASSWORD}
    assert client.post("/api/auth/register",json=body).status_code == 202
    login = client.post("/api/auth/login",json=body)
    assert login.status_code == 403
    assert login.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"
    token = latest_token(settings,"alice@example.com")
    with app.state.sessions() as db:
        user = db.scalar(select(User))
        assert user.email == "alice@example.com"
        assert user.password_hash.startswith("$argon2id$")
        assert PASSWORD not in user.password_hash
        assert db.scalar(select(AuthToken.token_hash)) == digest_token(token)
    assert client.post("/api/auth/verify-email",json={"token":token}).status_code == 200
    assert client.post("/api/auth/verify-email",json={"token":token}).status_code == 400
    r = client.post("/api/auth/login",json=body)
    assert r.status_code == 200
    assert r.json()["user"]["onboarding_complete"] is False

def test_duplicate_signup_does_not_replace_password(client,user_factory):
    headers, _ = user_factory()
    r = client.post("/api/auth/register",json={"email":"alice@example.com","password":"different-passphrase-123"})
    assert r.status_code == 202
    assert client.post("/api/auth/login",json={"email":"alice@example.com","password":PASSWORD}).status_code == 200

def test_logout_revokes_token_immediately(client,user_factory):
    headers,_ = user_factory()
    assert client.get("/api/auth/me",headers=headers).status_code == 200
    assert client.post("/api/auth/logout",headers=headers).status_code == 204
    assert client.get("/api/auth/me",headers=headers).status_code == 401

def test_logout_all_revokes_other_sessions(client,user_factory):
    headers,_ = user_factory()
    login = client.post("/api/auth/login",json={"email":"alice@example.com","password":PASSWORD}).json()
    other = {"Authorization":"Bearer "+login["access_token"]}
    assert client.post("/api/auth/logout-all",headers=headers).status_code == 204
    assert client.get("/api/auth/me",headers=other).status_code == 401

def test_reset_one_time_token_invalidates_sessions(client,user_factory,settings):
    headers,_ = user_factory()
    result = client.post("/api/auth/forgot-password",json={"email":"alice@example.com"})
    unknown = client.post("/api/auth/forgot-password",json={"email":"missing@example.com"})
    assert result.json() == unknown.json()
    token = latest_token(settings,"alice@example.com","재설정")
    body={"token":token, "password":"new-valid-passphrase-123"}
    assert client.post("/api/auth/reset-password",json=body).status_code == 200
    assert client.post("/api/auth/reset-password",json=body).status_code == 400
    assert client.get("/api/auth/me",headers=headers).status_code == 401
    assert client.post("/api/auth/login",json={"email":"alice@example.com","password":PASSWORD}).status_code == 401
    assert client.post("/api/auth/login",json={"email":"alice@example.com","password":body["password"]}).status_code == 200

def test_token_purpose_cannot_be_swapped(client,settings):
    client.post("/api/auth/register",json={"email":"one@example.com","password":PASSWORD})
    token = latest_token(settings,"one@example.com")
    assert client.post("/api/auth/reset-password",json={"token":token,"password":PASSWORD}).status_code == 400

def test_expired_verification_rejected(client,settings,app):
    client.post("/api/auth/register",json={"email":"one@example.com","password":PASSWORD})
    token = latest_token(settings,"one@example.com")
    with app.state.sessions() as db:
        db.execute(update(AuthToken).values(expires_at=now_ts()-1))
        db.commit()
    assert client.post("/api/auth/verify-email",json={"token":token}).status_code == 400

def test_expired_session_rejected(client,user_factory,app):
    headers,_ = user_factory()
    with app.state.sessions() as db:
        db.execute(update(AuthSession).values(expires_at=now_ts()-1))
        db.commit()
    assert client.get("/api/auth/me",headers=headers).status_code == 401

def test_validation_never_echoes_password(client):
    password="secret"
    r=client.post("/api/auth/register",json={"email":"bad","password":password})
    assert r.status_code == 422
    assert password not in r.text
    assert "input" not in r.text

def test_private_endpoints_require_auth(client):
    for path in ["/api/profile","/api/bookmarks","/api/calendar?month=2026-09","/api/notices/recommended","/api/admin/crawl-jobs"]:
        assert client.get(path).status_code == 401

def test_wrong_credentials_are_generic(client,user_factory):
    user_factory()
    a=client.post("/api/auth/login",json={"email":"alice@example.com","password":"bad"})
    b=client.post("/api/auth/login",json={"email":"missing@example.com","password":"bad"})
    assert a.status_code == b.status_code == 401
    assert a.json()["error"]["code"] == b.json()["error"]["code"]

def test_account_deletion_cascades(client,user_factory,app,notice_factory):
    headers, ident=user_factory()
    n=notice_factory()
    client.post(f"/api/bookmarks/{n}",headers=headers)
    assert client.request("DELETE","/api/auth/account",headers=headers,json={"password":PASSWORD}).status_code == 204
    assert client.get("/api/auth/me",headers=headers).status_code == 401
    with app.state.sessions() as db:
        assert db.get(User,ident) is None
        assert db.get(Profile,ident) is None
        assert db.scalar(select(ProfileInterest).where(ProfileInterest.user_id==ident)) is None
