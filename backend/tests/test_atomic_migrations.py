from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import inspect, select, text
from app.cli import migrate
from app.db import make_engine
from app.models import Interest, Notice, Source, User
from tests.conftest import PASSWORD

def test_migration_and_reference_seed_are_idempotent(app,settings):
    migrate(settings)
    migrate(settings)
    with app.state.sessions() as db:
        assert len(db.scalars(select(Source)).all())==3
        assert len(db.scalars(select(Interest)).all())==15
        assert len(db.scalars(select(Notice)).all())==0
    columns={c["name"]:str(c["type"]).upper() for c in inspect(app.state.engine).get_columns("notice_analyses")}
    assert columns["deadline_at"]=="BIGINT"

def test_duplicate_username_creation_is_atomic(client):
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses=list(pool.map(lambda _:client.post("/api/auth/register",json={"username":"atomic","password":PASSWORD}).status_code,range(2)))
    assert sorted(statuses)==[201,409]


def test_existing_account_migrates_to_username(settings):
    migrate(settings)
    engine = make_engine(settings.database_url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id,username,password_hash,is_admin,created_at) VALUES ('00000000-0000-0000-0000-000000000001','alice','stored-hash',0,1)"))
        connection.execute(text("ALTER TABLE users RENAME COLUMN username TO email"))
        connection.execute(text("UPDATE users SET email='Alice@example.test'"))
        connection.execute(text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT 1"))
        connection.execute(text("CREATE TABLE auth_tokens (token_hash VARCHAR(64) PRIMARY KEY, user_id VARCHAR(36), purpose VARCHAR(12), expires_at BIGINT, created_at BIGINT)"))
        connection.execute(text("UPDATE alembic_version SET version_num='0001'"))
    engine.dispose()
    migrate(settings)
    engine = make_engine(settings.database_url)
    with engine.connect() as connection:
        row = connection.execute(text("SELECT username,password_hash FROM users")).one()
        assert row == ("alice", "stored-hash")
        assert "email_verified" not in {c["name"] for c in inspect(connection).get_columns("users")}
        assert "auth_tokens" not in inspect(connection).get_table_names()
    engine.dispose()
