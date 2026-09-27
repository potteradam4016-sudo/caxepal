"""Epoch seconds are UTC; notice dates without times remain SQL DATE values."""
import time
import uuid
from datetime import date
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

def uid() -> str:
    return str(uuid.uuid4())

def now_ts() -> int:
    return int(time.time())

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[int] = mapped_column(BigInteger, default=now_ts)

class Profile(Base):
    __tablename__ = "profiles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    department: Mapped[str | None] = mapped_column(String(80), nullable=True)
    grade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    academic_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[int] = mapped_column(BigInteger, default=now_ts)
    __table_args__ = (CheckConstraint("grade IS NULL OR (grade >= 1 AND grade <= 6)", name="grade_range"),)

class Interest(Base):
    __tablename__ = "interests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    type: Mapped[str] = mapped_column(String(12))
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    __table_args__ = (CheckConstraint("type IN ('field','activity')", name="interest_type"),)

class ProfileInterest(Base):
    __tablename__ = "profile_interests"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    interest_id: Mapped[str] = mapped_column(ForeignKey("interests.id"), primary_key=True)

class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[int] = mapped_column(BigInteger, index=True)
    created_at: Mapped[int] = mapped_column(BigInteger, default=now_ts)

class Source(Base):
    __tablename__ = "sources"
    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    list_url: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_success_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

class Notice(Base):
    __tablename__ = "notices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_code: Mapped[str] = mapped_column(ForeignKey("sources.code"))
    external_id: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(1000))
    body_text: Mapped[str] = mapped_column(Text)
    posted_date: Mapped[date] = mapped_column(Date)
    original_url: Mapped[str] = mapped_column(Text)
    attachments: Mapped[list] = mapped_column(JSON, default=list)
    content_hash: Mapped[str] = mapped_column(String(64))
    image_only: Mapped[bool] = mapped_column(Boolean, default=False)
    search_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[int] = mapped_column(BigInteger, default=now_ts)
    updated_at: Mapped[int] = mapped_column(BigInteger, default=now_ts)
    last_seen_at: Mapped[int] = mapped_column(BigInteger, default=now_ts)
    analysis: Mapped["NoticeAnalysis"] = relationship(
        back_populates="notice", uselist=False, lazy="selectin", cascade="all, delete-orphan"
    )
    __table_args__ = (
        UniqueConstraint("source_code", "external_id", name="uq_notices_source_external"),
        Index("ix_notices_posted_id", "posted_date", "id"),
    )

class NoticeAnalysis(Base):
    __tablename__ = "notice_analyses"
    notice_id: Mapped[int] = mapped_column(ForeignKey("notices.id", ondelete="CASCADE"), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
    provider: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="needs_review")
    category: Mapped[str] = mapped_column(String(40), default="other", index=True)
    deadline_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    analyzed_at: Mapped[int] = mapped_column(BigInteger, default=now_ts)
    notice: Mapped[Notice] = relationship(back_populates="analysis")

class Bookmark(Base):
    __tablename__ = "bookmarks"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    notice_id: Mapped[int] = mapped_column(ForeignKey("notices.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[int] = mapped_column(BigInteger, default=now_ts)

class CrawlJob(Base):
    __tablename__ = "crawl_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    requested_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    parameters: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_owner: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lease_expires_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[int] = mapped_column(BigInteger, default=now_ts, index=True)
    started_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    finished_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

class CrawlRun(Base):
    __tablename__ = "crawl_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("crawl_jobs.id"), index=True)
    source_code: Mapped[str] = mapped_column(ForeignKey("sources.code"))
    status: Mapped[str] = mapped_column(String(16), default="running")
    counts: Mapped[dict] = mapped_column(JSON, default=dict)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[int] = mapped_column(BigInteger, default=now_ts)
    finished_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

class Lease(Base):
    __tablename__ = "leases"
    name: Mapped[str] = mapped_column(String(80), primary_key=True)
    owner: Mapped[str] = mapped_column(String(36))
    expires_at: Mapped[int] = mapped_column(BigInteger)

class RateBucket(Base):
    __tablename__ = "rate_buckets"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window: Mapped[int] = mapped_column(Integer, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=1)
    expires_at: Mapped[int] = mapped_column(BigInteger, index=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    resource_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[int] = mapped_column(BigInteger, default=now_ts)
