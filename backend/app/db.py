from collections.abc import Iterator
from pathlib import Path
from fastapi import Request
from sqlalchemy import create_engine, event, MetaData
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s", "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })

def make_engine(url: str):
    kw = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        from sqlalchemy.engine import make_url
        path = make_url(url).database
        if path and path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        kw["connect_args"] = {"check_same_thread": False, "timeout": 30}
        if path == ":memory:":
            kw["poolclass"] = StaticPool
    engine = create_engine(url, **kw)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def sqlite_connect(conn, _):
            conn.isolation_level = None
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=30000")
        @event.listens_for(engine, "begin")
        def sqlite_begin(conn):
            conn.exec_driver_sql("BEGIN")
    return engine

def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)

def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.sessions() as db:
        yield db

def dialect_insert(db: Session, model):
    if db.bind.dialect.name == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    elif db.bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        raise RuntimeError("Unsupported database dialect")
    return insert(model)
