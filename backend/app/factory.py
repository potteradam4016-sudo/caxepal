from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import text
from app.config import Settings
from app.db import make_engine, session_factory
from app.errors import install_handlers
from app.middleware import SafetyMiddleware
from app.schemas import ErrorOut
from app.services.recommendations import load_policy

def create_app(settings: Settings) -> FastAPI:
    engine = make_engine(settings.database_url)
    sessions = session_factory(engine)

    @asynccontextmanager
    async def lifespan(app):
        # Migrations are explicit, never automatic destructive schema changes on startup.
        try:
            with engine.connect() as conn:
                revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                if revision != "0001":
                    raise RuntimeError("Database schema is not at the expected revision.")
        except Exception as exc:
            engine.dispose()
            raise RuntimeError("Database not initialized. Run: python -m app.cli init-db") from exc
        yield
        engine.dispose()

    app = FastAPI(title="SCNU PICK 백엔드", version="1.0.0",
        description="프론트엔드와 분리된 백엔드 API입니다. 기능 기준은 저장소의 docs/product-scope.md이며, "
                    "프론트 연동 계약 제안은 backend/docs/API_CONTRACT.md에 있습니다.",
        docs_url="/docs" if settings.docs_enabled else None, redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan, responses={code:{"model":ErrorOut} for code in [400,401,403,404,409,413,422,429,500]})
    app.state.engine, app.state.sessions = engine, sessions
    app.state.settings, app.state.policy = settings, load_policy()
    install_handlers(app)

    from app.api import auth, profile, notices, bookmarks, admin
    for router in [auth.router, profile.router, notices.router, bookmarks.router, admin.router]:
        app.include_router(router, prefix="/api")

    @app.get("/", tags=["상태"], summary="백엔드 서비스 정보")
    def root() -> dict:
        return {"service":"SCNU PICK backend", "status":"ok",
                "docs": "/docs" if settings.docs_enabled else None, "health":"/health"}
    @app.get("/health", tags=["상태"], summary="서버와 DB 상태 확인")
    def health() -> dict:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status":"ok", "database":"ok", "frontend_included":False}

    app.add_middleware(SafetyMiddleware, factory=sessions, settings=settings)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.hosts)
    app.add_middleware(CORSMiddleware, allow_origins=settings.origins,
        allow_credentials=False, allow_methods=["GET","POST","PUT","DELETE","OPTIONS"],
        allow_headers=["Authorization","Content-Type"], expose_headers=["X-Request-ID","Retry-After"])
    return app
