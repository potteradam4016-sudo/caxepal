from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import inspect, select
from app.cli import migrate
from app.models import Interest, Notice, Source
from tests.conftest import PASSWORD, latest_token

def test_migration_and_reference_seed_are_idempotent(app,settings):
    migrate(settings)
    migrate(settings)
    with app.state.sessions() as db:
        assert len(db.scalars(select(Source)).all())==3
        assert len(db.scalars(select(Interest)).all())==15
        assert len(db.scalars(select(Notice)).all())==0
    columns={c["name"]:str(c["type"]).upper() for c in inspect(app.state.engine).get_columns("notice_analyses")}
    assert columns["deadline_at"]=="BIGINT"

def test_verification_token_consumption_is_atomic(client,settings):
    client.post("/api/auth/register",json={"email":"atomic@example.com","password":PASSWORD})
    token=latest_token(settings,"atomic@example.com")
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses=list(pool.map(lambda _:client.post("/api/auth/verify-email",json={"token":token}).status_code,range(2)))
    assert sorted(statuses)==[200,400]
