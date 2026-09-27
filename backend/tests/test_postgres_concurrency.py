import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier, Lock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url

from app.cli import migrate
from app.config import Settings
from app.factory import create_app
from app.models import Bookmark, CrawlJob, Notice, User
from app.schemas import CrawlInput
from app.services.analysis import analyze, apply_analysis
from app.services.jobs import acquire_lease, enqueue, run_next_job


pytestmark = pytest.mark.postgres
PASSWORD = "postgres-test-passphrase-123"
MUTABLE_TABLES = (
    "audit_logs, rate_buckets, leases, crawl_runs, crawl_jobs, bookmarks, "
    "auth_sessions, profile_interests, notice_analyses, notices, profiles, users"
)


@pytest.fixture(scope="session")
def postgres_settings():
    database_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL integration tests.")

    url = make_url(database_url)
    if url.get_backend_name() != "postgresql":
        pytest.fail("TEST_DATABASE_URL must use PostgreSQL.")
    if not url.database or not url.database.endswith("_test"):
        pytest.fail("TEST_DATABASE_URL database name must end with '_test'.")

    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=database_url,
        secret_key="postgres-test-secret-not-for-deployment-" * 2,
        request_limit_per_minute=10_000,
        auth_limit_per_15_minutes=1_000,
    )
    migrate(settings)
    return settings


def clear_mutable_data(settings):
    from app.db import make_engine

    engine = make_engine(settings.database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text(f"TRUNCATE TABLE {MUTABLE_TABLES} RESTART IDENTITY CASCADE"))
            connection.execute(text("UPDATE sources SET enabled=TRUE, last_success_at=NULL"))
    finally:
        engine.dispose()


@pytest.fixture
def postgres_app(postgres_settings):
    clear_mutable_data(postgres_settings)
    application = create_app(postgres_settings)
    yield application
    application.state.engine.dispose()
    clear_mutable_data(postgres_settings)


@pytest.fixture
def postgres_client(postgres_app):
    with TestClient(postgres_app) as client:
        yield client


def register_and_login(client, username="alice"):
    credentials = {"username": username, "password": PASSWORD}
    assert client.post("/api/auth/register", json=credentials).status_code == 201
    response = client.post("/api/auth/login", json=credentials)
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def create_notice(app):
    title = "PostgreSQL 동시성 검증 공지"
    body = "대상: 전체 학생\n신청 마감: 2070.09.30 18:00"
    with app.state.sessions() as db:
        notice = Notice(
            source_code="SCNU_MAIN",
            external_id="postgres-concurrency-1",
            title=title,
            body_text=body,
            posted_date=date(2026, 9, 26),
            original_url="https://www.scnu.ac.kr/",
            attachments=[],
            content_hash="a" * 64,
            image_only=False,
        )
        data, provider, status, warnings = analyze(app.state.settings, title, body)
        apply_analysis(notice, data, provider, status, warnings)
        db.add(notice)
        db.commit()
        return notice.id


def concurrently(count, action):
    barrier = Barrier(count)

    def run(index):
        barrier.wait()
        return action(index)

    with ThreadPoolExecutor(max_workers=count) as pool:
        return list(pool.map(run, range(count)))


def test_postgres_connection_and_revision(postgres_app):
    with postgres_app.state.engine.connect() as connection:
        assert connection.dialect.name == "postgresql"
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0002"


def test_duplicate_registration_is_atomic(postgres_client, postgres_app):
    payload = {"username": "atomic", "password": PASSWORD}
    statuses = concurrently(2, lambda _: postgres_client.post("/api/auth/register", json=payload).status_code)
    assert sorted(statuses) == [201, 409]
    with postgres_app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1


def test_profile_optimistic_lock_allows_one_writer(postgres_client):
    headers = register_and_login(postgres_client)
    base = {
        "grade": 2,
        "academic_status": "enrolled",
        "interest_ids": ["ai_sw"],
        "expected_version": 0,
    }

    def update_profile(index):
        body = {**base, "department": "컴퓨터공학과" if index == 0 else "인공지능공학과"}
        return postgres_client.put("/api/profile", headers=headers, json=body).status_code

    assert sorted(concurrently(2, update_profile)) == [200, 409]
    profile = postgres_client.get("/api/profile", headers=headers).json()
    assert profile["version"] == 1
    assert profile["department"] in {"컴퓨터공학과", "인공지능공학과"}


def test_duplicate_bookmark_is_idempotent(postgres_client, postgres_app):
    headers = register_and_login(postgres_client)
    notice_id = create_notice(postgres_app)
    statuses = concurrently(
        4,
        lambda _: postgres_client.post(f"/api/bookmarks/{notice_id}", headers=headers).status_code,
    )
    assert statuses == [204] * 4
    with postgres_app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Bookmark)) == 1


def test_only_one_worker_acquires_lease(postgres_app):
    acquired = concurrently(
        2,
        lambda index: acquire_lease(postgres_app.state.sessions, "postgres-worker", f"worker-{index}"),
    )
    assert sorted(acquired) == [False, True]


def test_concurrent_workers_process_job_once(postgres_app, monkeypatch):
    calls = 0
    calls_lock = Lock()

    def fake_crawl(_factory, _settings, _client, code, _options, _job_id):
        nonlocal calls
        with calls_lock:
            calls += 1
        time.sleep(0.2)
        return {"source": code, "status": "completed", "counts": {}, "errors": []}

    class FakeClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def prepare_robots(self):
            pass

    monkeypatch.setattr("app.services.jobs.crawl_source", fake_crawl)
    with postgres_app.state.sessions() as db:
        job_id = enqueue(db, CrawlInput(sources=["SCNU_MAIN"])).id

    postgres_app.state.settings.crawl_enabled = True
    results = concurrently(
        2,
        lambda _: run_next_job(
            postgres_app.state.sessions,
            postgres_app.state.settings,
            target_id=job_id,
            client_factory=FakeClient,
        ),
    )

    assert results.count(job_id) == 1
    assert results.count(None) == 1
    assert calls == 1
    with postgres_app.state.sessions() as db:
        job = db.get(CrawlJob, job_id)
        assert job.status == "completed"
        assert job.attempts == 1
