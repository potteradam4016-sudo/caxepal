from sqlalchemy import func, select
from app.models import Bookmark, Notice, NoticeAnalysis, Source, now_ts
from app.reference import PUBLISHER_CATEGORIES, SOURCES
from app.schemas import AnalysisData
from app.services.analysis import clean_summary_lines
from app.services.dates import deadline_badge
from app.services.recommendations import score_notice

def bookmarked_ids(db, user_id):
    if user_id is None:
        return set()
    return set(db.scalars(select(Bookmark.notice_id).where(Bookmark.user_id == user_id)))

def card(notice, bookmarks=None, recommendation=None, now=None):
    now = now_ts() if now is None else now
    a = notice.analysis
    data = AnalysisData.model_validate(a.data)
    day, label, closed = deadline_badge(a.deadline_date, a.deadline_at, now)
    return {"id": notice.id, "title": notice.title, "source_code": notice.source_code,
        "source_name": PUBLISHER_CATEGORIES[notice.publisher_category] if notice.source_code == "SCNU_MAIN"
                       else SOURCES[notice.source_code]["name"],
        "author_name": notice.author_name, "publisher_category": notice.publisher_category,
        "posted_date": notice.posted_date,
        "original_url": notice.original_url, "category": data.category,
        "summary_lines": clean_summary_lines(data.summary_lines), "deadline_date": a.deadline_date,
        "deadline_at": a.deadline_at, "d_day": day, "deadline_label": label,
        "is_closed": closed, "is_bookmarked": notice.id in (bookmarks or set()),
        "needs_review": a.status != "reviewed", "recommendation": recommendation}

def detail(notice, bookmarks=None, recommendation=None):
    result = card(notice, bookmarks, recommendation)
    result.update(body_text=notice.body_text, attachments=notice.attachments,
        content_hash=notice.content_hash, image_only=notice.image_only,
        analysis={"provider": notice.analysis.provider, "status": notice.analysis.status,
                  "data": notice.analysis.data, "warnings": notice.analysis.warnings,
                  "analyzed_at": notice.analysis.analyzed_at},
        fetched_at=notice.last_seen_at)
    return result

def filtered_query(source=None, q=None, category=None, publisher_category=None, include_closed=True,
                   after=None, deadline_before=None, now=None, analysis_success_only=False):
    now = now_ts() if now is None else now
    stmt = select(Notice).join(NoticeAnalysis).where(Notice.source_code == "SCNU_MAIN")
    if source:
        stmt = stmt.where(Notice.source_code == source)
    if q:
        stmt = stmt.where(Notice.search_text.contains(q, autoescape=True))
    if category:
        categories = [category] if isinstance(category, str) else category
        stmt = stmt.where(NoticeAnalysis.category.in_(categories))
    if publisher_category:
        stmt = stmt.where(Notice.publisher_category == publisher_category)
    if analysis_success_only:
        stmt = stmt.where(NoticeAnalysis.provider == "openai",
                          NoticeAnalysis.status.in_(("analyzed", "needs_review")))
    if not include_closed:
        stmt = stmt.where((NoticeAnalysis.deadline_at.is_(None)) | (NoticeAnalysis.deadline_at >= now))
    if after:
        stmt = stmt.where(Notice.posted_date >= after)
    if deadline_before is not None:
        stmt = stmt.where(NoticeAnalysis.deadline_at >= now, NoticeAnalysis.deadline_at <= deadline_before)
    return stmt

def paginate(db, stmt, page, page_size, bookmarks):
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    notices = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [card(n, bookmarks) for n in notices], "total": total,
            "page": page, "page_size": page_size}
