from datetime import timedelta
from sqlalchemy import select
from app.crawlers.parser import parse_detail, parse_list
from app.models import CrawlRun, Notice, Source, now_ts
from app.reference import list_url
from app.services.analysis import analyze, apply_analysis
from app.services.dates import local_today

def upsert_notice(factory, settings, code, parsed, analyzer=analyze):
    # Network/AI work must happen outside a DB transaction.
    with factory() as db:
        old = db.scalar(select(Notice).where(Notice.source_code==code, Notice.external_id==parsed.external_id))
        if old and old.content_hash == parsed.content_hash:
            old.last_seen_at = now_ts()
            db.commit()
            return "unchanged"
    data, provider, status, warnings = analyzer(settings, parsed.title, parsed.body_text, parsed.image_only)
    with factory() as db:
        notice = db.scalar(select(Notice).where(Notice.source_code==code, Notice.external_id==parsed.external_id))
        created = notice is None
        if notice is None:
            notice = Notice(source_code=code, external_id=parsed.external_id)
            db.add(notice)
        for key in ("title", "body_text", "posted_date", "original_url", "attachments", "image_only", "content_hash"):
            setattr(notice, key, getattr(parsed, key))
        notice.updated_at = notice.last_seen_at = now_ts()
        apply_analysis(notice, data, provider, status, warnings)
        db.commit()
        return "created" if created else "updated"

def crawl_source(factory, settings, client, code, options, job_id):
    counts = {"created":0, "updated":0, "unchanged":0, "skipped_old":0, "failed":0, "pages":0}
    errors = []
    with factory() as db:
        source = db.get(Source, code)
        if not source or not source.enabled:
            return {"source": code, "status":"skipped", "counts": counts, "errors":["SOURCE_DISABLED"]}
        run = CrawlRun(source_code=code, job_id=job_id)
        db.add(run)
        db.commit()
        run_id = run.id
    seen, processed, page_fingerprints = set(), 0, set()
    cutoff = local_today() - timedelta(days=options.max_age_days)
    try:
        for page in range(1, options.pages + 1):
            rows = parse_list(client.get_html(list_url(code, page)), code)
            counts["pages"] += 1
            fingerprint = tuple(row.external_id for row in rows)
            if fingerprint in page_fingerprints and rows:
                raise RuntimeError("PAGINATION_DID_NOT_ADVANCE")
            page_fingerprints.add(fingerprint)
            if not rows:
                break
            for listed in rows:
                if listed.external_id in seen:
                    continue
                seen.add(listed.external_id)
                if listed.posted_date < cutoff and not listed.pinned:
                    counts["skipped_old"] += 1
                    continue
                if processed >= options.max_notices:
                    break
                processed += 1
                try:
                    parsed = parse_detail(client.get_html(listed.original_url), listed)
                    result = upsert_notice(factory, settings, code, parsed)
                    counts[result] += 1
                except Exception as exc:
                    counts["failed"] += 1
                    # Errors are operational codes only; never persist whole page bodies.
                    safe = str(exc) if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__
                    errors.append({"external_id": listed.external_id, "code": safe[:100]})
            if processed >= options.max_notices:
                break
            regular = [r for r in rows if not r.pinned]
            if regular and all(r.posted_date < cutoff for r in regular):
                break
    except Exception as exc:
        safe = str(exc) if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__
        errors.append({"code": safe[:100]})
    successful = counts["created"] + counts["updated"] + counts["unchanged"]
    status = "partial" if errors and successful else "failed" if errors else "completed"
    with factory() as db:
        run = db.get(CrawlRun, run_id)
        run.status, run.counts, run.errors, run.finished_at = status, counts, errors, now_ts()
        if successful:
            db.get(Source, code).last_success_at = now_ts()
        db.commit()
    return {"source":code, "status":status, "counts":counts, "errors":errors}
