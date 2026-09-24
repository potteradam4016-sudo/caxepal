from datetime import date
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.cli import migrate
from app.config import Settings
from app.factory import create_app
from app.models import Notice, User
from app.services.analysis import analyze, apply_analysis

PASSWORD = "only-for-tests-passphrase-123"


@pytest.fixture(autouse=True)
def isolate_test_environment(monkeypatch):
    """운영/개인 환경변수가 임시 시험 설정을 덮어쓰지 않게 합니다."""
    names = {name.upper() for name in Settings.model_fields}
    import os
    for name in list(os.environ):
        if name.upper() in names:
            monkeypatch.delenv(name, raising=False)


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, secret_key="test-secret-only-not-for-deployment-"*2,
        app_env="test", database_url=f"sqlite:///{tmp_path / 'test.sqlite3'}",
        request_limit_per_minute=1000,
        auth_limit_per_15_minutes=100)

@pytest.fixture
def app(settings):
    migrate(settings)
    application = create_app(settings)
    yield application
    application.state.engine.dispose()

@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c

@pytest.fixture
def user_factory(client):
    def create(username="alice", with_profile=True):
        assert client.post("/api/auth/register", json={"username":username,"password":PASSWORD}).status_code == 201
        login = client.post("/api/auth/login", json={"username":username,"password":PASSWORD})
        assert login.status_code == 200, login.text
        headers = {"Authorization":"Bearer "+login.json()["access_token"]}
        if with_profile:
            profile = client.put("/api/profile",headers=headers,json={
                "department":"컴퓨터공학과", "grade":2,"academic_status":"enrolled",
                "interest_ids":["ai_sw","hackathon"]})
            assert profile.status_code == 200, profile.text
        return headers, login.json()["user"]["id"]
    return create

@pytest.fixture
def notice_factory(app):
    counter = 0
    def create(title="AI 해커톤", body="대상: 컴퓨터공학과 2학년 재학생\n신청 마감: 2070.09.30 18:00",
               posted=date(2026,9,18), source="SCNU_SW", modify=None):
        nonlocal counter
        counter += 1
        import hashlib
        with app.state.sessions() as db:
            n = Notice(source_code=source, external_id=str(1000+counter), title=title,
                body_text=body, posted_date=posted,
                original_url=f"https://www.scnu.ac.kr/scnusw/na/ntt/selectNttInfo.do?nttSn={1000+counter}",
                content_hash=hashlib.sha256((title+body).encode()).hexdigest(), attachments=[], image_only=False)
            result = list(analyze(app.state.settings,title,body,False))
            if modify:
                result[0] = modify(result[0])
            apply_analysis(n, *result)
            db.add(n)
            db.commit()
            return n.id
    return create
