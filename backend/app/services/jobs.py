import uuid
from sqlalchemy import and_, delete, or_, select, update
from app.crawlers.client import SafeClient
from app.db import dialect_insert
from app.errors import APIError
from app.models import CrawlJob, Lease, now_ts
from app.schemas import CrawlInput
from app.services.crawl import crawl_source

LEASE_SECONDS = 600

def acquire_lease(factory, name, owner, ttl=LEASE_SECONDS):
    now = now_ts()
    with factory() as db:
        stmt = dialect_insert(db, Lease).values(name=name, owner=owner, expires_at=now+ttl)
        stmt = stmt.on_conflict_do_update(index_elements=["name"],
            set_={"owner":owner, "expires_at":now+ttl},
            where=(Lease.expires_at < now) | (Lease.owner == owner)).returning(Lease.name)
        acquired = db.execute(stmt).scalar_one_or_none() is not None
        db.commit()
        return acquired

def release_lease(factory, name, owner):
    with factory() as db:
        db.execute(delete(Lease).where(Lease.name==name, Lease.owner==owner))
        db.commit()

def enqueue(db, options: CrawlInput, requested_by=None):
    job = CrawlJob(parameters=options.model_dump(mode="json"), requested_by=requested_by)
    db.add(job)
    db.commit()
    return job

def run_next_job(factory, settings, target_id=None, client_factory=SafeClient):
    if not settings.crawl_enabled:
        return None
    owner = str(uuid.uuid4())
    if not acquire_lease(factory, "global-crawler", owner):
        return None
    job_id = None
    try:
        with factory() as db:
            db.execute(update(CrawlJob).where(
                CrawlJob.status=="running", CrawlJob.lease_expires_at < now_ts(), CrawlJob.attempts >= 3
            ).values(status="failed", error_code="WORKER_RETRY_EXHAUSTED", finished_at=now_ts()))
            eligible = or_(CrawlJob.status=="queued",
                           and_(CrawlJob.status=="running", CrawlJob.lease_expires_at < now_ts()))
            query = select(CrawlJob.id).where(eligible, CrawlJob.attempts < 3).order_by(CrawlJob.created_at, CrawlJob.id).limit(1)
            if target_id:
                query = query.where(CrawlJob.id == target_id)
            job_id = db.scalar(query)
            if job_id is None:
                db.commit()
                return None
            claimed = db.execute(update(CrawlJob).where(CrawlJob.id==job_id, eligible).values(
                status="running", lease_owner=owner, lease_expires_at=now_ts()+LEASE_SECONDS,
                attempts=CrawlJob.attempts+1, started_at=now_ts()
            ).returning(CrawlJob.parameters)).scalar_one_or_none()
            db.commit()
            if claimed is None:
                return None
            options = CrawlInput.model_validate(claimed)

        def heartbeat():
            if not acquire_lease(factory, "global-crawler", owner):
                raise RuntimeError("CRAWL_LEASE_LOST")
            with factory() as db:
                updated = db.execute(update(CrawlJob).where(CrawlJob.id==job_id, CrawlJob.lease_owner==owner,
                    CrawlJob.status=="running").values(lease_expires_at=now_ts()+LEASE_SECONDS))
                db.commit()
                if updated.rowcount != 1:
                    raise RuntimeError("JOB_LEASE_LOST")

        with client_factory(settings, heartbeat=heartbeat) as client:
            client.prepare_robots()
            results = [crawl_source(factory, settings, client, code, options, job_id) for code in options.sources]
        statuses = {r["status"] for r in results}
        status = "completed" if statuses <= {"completed"} else "failed" if statuses <= {"failed","skipped"} else "partial"
        with factory() as db:
            db.execute(update(CrawlJob).where(CrawlJob.id==job_id, CrawlJob.lease_owner==owner).values(
                status=status, result={"sources":results}, finished_at=now_ts(), lease_expires_at=None))
            db.commit()
        return job_id
    except Exception as exc:
        if job_id:
            with factory() as db:
                safe = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
                db.execute(update(CrawlJob).where(CrawlJob.id==job_id, CrawlJob.lease_owner==owner).values(
                    status="failed", error_code=safe[:80], finished_at=now_ts(), lease_expires_at=None))
                db.commit()
        return job_id
    finally:
        release_lease(factory, "global-crawler", owner)

def maybe_schedule(factory, settings):
    if not settings.auto_crawl or not settings.crawl_enabled:
        return
    owner = str(uuid.uuid4())
    if not acquire_lease(factory, "crawl-scheduler", owner, 60):
        return
    try:
        with factory() as db:
            last = db.scalar(select(CrawlJob).order_by(CrawlJob.created_at.desc()).limit(1))
            if last and (last.status in {"queued","running"} or now_ts()-last.created_at < settings.crawl_interval_seconds):
                return
            enqueue(db, CrawlInput(pages=3))
    finally:
        release_lease(factory, "crawl-scheduler", owner)
