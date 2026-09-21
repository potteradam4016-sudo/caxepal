"""Configuration is server-side only. Never copy .env to the frontend."""
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = f"sqlite:///{(BASE_DIR / 'data/scnu_pick.sqlite3').as_posix()}"
    secret_key: str = Field(min_length=32)
    host: str = "127.0.0.1"
    port: int = Field(default=3104, ge=1, le=65535)
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    docs_enabled: bool = True
    session_hours: int = Field(default=24, ge=1, le=168)
    mail_backend: Literal["file", "smtp"] = "file"
    mail_from: str = "no-reply@example.com"
    mail_directory: Path = BASE_DIR / "data/mail"
    frontend_url: str = "http://localhost:5173"
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_tls: Literal["starttls", "ssl"] = "starttls"
    crawl_enabled: bool = False
    auto_crawl: bool = False
    crawl_interval_seconds: int = Field(default=10800, ge=3600)
    crawl_request_delay: float = Field(default=1.0, ge=1.0, le=60)
    crawl_timeout: float = Field(default=15.0, ge=1, le=60)
    crawl_user_agent: str = "SCNU-PICK/1.0 (university notice aggregation)"
    # Written permission must explicitly cover any exception to robots directives.
    robots_policy: Literal["strict", "written_permission"] = "strict"
    ai_provider: Literal["rules", "openai"] = "rules"
    openai_api_key: str = ""
    openai_model: str = ""
    request_limit_per_minute: int = Field(default=120, ge=1, le=10000)
    auth_limit_per_15_minutes: int = Field(default=10, ge=1, le=1000)
    max_request_bytes: int = Field(default=65536, ge=4096, le=1048576)

    @property
    def origins(self) -> list[str]:
        return [x.strip().rstrip("/") for x in self.cors_origins.split(",") if x.strip()]

    @property
    def hosts(self) -> list[str]:
        return [x.strip() for x in self.allowed_hosts.split(",") if x.strip()]

    @model_validator(mode="after")
    def validate_environment(self):
        if not self.database_url.startswith(("sqlite:///", "postgresql+psycopg://")):
            raise ValueError("Use sqlite:/// or postgresql+psycopg:// DATABASE_URL.")
        if "*" in self.origins or "*" in self.hosts:
            raise ValueError("Explicit CORS origins and hosts are required.")
        for origin in [*self.origins, self.frontend_url]:
            u = urlsplit(origin)
            if u.scheme not in {"http", "https"} or not u.hostname or u.username or u.password:
                raise ValueError("Invalid origin/FRONTEND_URL.")
            if u.query or u.fragment or u.path not in {"", "/"}:
                raise ValueError("Origins must not contain paths, queries, or fragments.")
        if self.ai_provider == "openai" and (not self.openai_api_key or not self.openai_model):
            raise ValueError("OPENAI_API_KEY and OPENAI_MODEL are required for AI_PROVIDER=openai.")
        if self.mail_backend == "smtp" and not self.smtp_host:
            raise ValueError("SMTP_HOST is required.")
        if self.app_env == "production":
            if self.mail_backend != "smtp":
                raise ValueError("Production requires real SMTP, not file mail.")
            if self.database_url.startswith("sqlite"):
                raise ValueError("Production requires PostgreSQL; SQLite is for local validation.")
            if not self.frontend_url.startswith("https://"):
                raise ValueError("Production FRONTEND_URL must use HTTPS.")
            if any(not x.startswith("https://") for x in self.origins):
                raise ValueError("Production CORS origins must use HTTPS.")
            if self.mail_from.endswith("@example.com"):
                raise ValueError("Set the verified production sender MAIL_FROM.")
        return self

@lru_cache
def get_settings() -> Settings:
    return Settings()
