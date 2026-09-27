from datetime import datetime, time, timedelta
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from app.db import get_db
from app.errors import APIError
from app.models import Notice, NoticeAnalysis, Source, now_ts
from app.schemas import AnalysisData, Category, NoticeDetail, NoticePage, SourceCode, SourceOut
from app.security import current_principal, optional_principal
from app.services.dates import SEOUL, local_today
from app.services.notices import bookmarked_ids, card, detail, filtered_query, paginate
from app.services.profiles import profile_payload
from app.services.recommendations import score_notice

router = APIRouter(tags=["공지"])

@router.get("/sources", summary="세 공지 출처와 마지막 수집 시각", response_model=list[SourceOut])
def sources(db=Depends(get_db)):
    return list(db.scalars(select(Source).order_by(Source.code)))

def closing_cutoff(days):
    return int(datetime.combine(local_today() + timedelta(days=days), time(23,59,59), tzinfo=SEOUL).timestamp())

@router.get("/notices", response_model=NoticePage, summary="검색·출처·카테고리·마감 필터", openapi_extra={"security":[{},{"BearerAuth":[]}]})
@router.get("/notices/new", response_model=NoticePage, summary="원문 등록일 기준 신규 공지", openapi_extra={"security":[{},{"BearerAuth":[]}]})
def list_notices(
    source: SourceCode | None = None,
    q: str | None = Query(default=None, max_length=100),
    category: list[Category] | None = Query(default=None),
    days: int | None = Query(default=None, ge=1, le=365),
    closing_days: int | None = Query(default=None, ge=0, le=90),
    include_closed: bool = True,
    page: int = Query(default=1, ge=1, le=100000),
    page_size: int = Query(default=20, ge=1, le=100),
    principal=Depends(optional_principal), db=Depends(get_db),
):
    stmt = filtered_query(source, q, category, include_closed,
        after=local_today() - timedelta(days=days-1) if days else None,
        deadline_before=closing_cutoff(closing_days) if closing_days is not None else None)
    stmt = stmt.order_by(Notice.posted_date.desc(), Notice.id.desc())
    return paginate(db, stmt, page, page_size, bookmarked_ids(db, principal.user.id if principal else None))

@router.get("/notices/recommended", response_model=NoticePage, summary="시간 가산 없는 맞춤 추천")
def recommended(
    request: Request,
    source: SourceCode | None = None,
    category: list[Category] | None = Query(default=None),
    q: str | None = Query(default=None, max_length=100),
    closing_days: int | None = Query(default=None, ge=0, le=90),
    min_score: int | None = Query(default=None, ge=0, le=100),
    page: int = Query(default=1, ge=1, le=100000),
    page_size: int = Query(default=20, ge=1, le=100),
    principal=Depends(current_principal), db=Depends(get_db),
):
    profile = profile_payload(db, principal.user.id)
    if not profile["onboarding_complete"]:
        raise APIError(409, "PROFILE_INCOMPLETE", "학적과 관심 분야·활동을 먼저 등록해주세요.")
    policy = request.app.state.policy
    threshold = min_score if min_score is not None else policy["default_min_score"]
    query = filtered_query(source, q, category, include_closed=False,
        deadline_before=closing_cutoff(closing_days) if closing_days is not None else None)
    bookmarks = bookmarked_ids(db, principal.user.id)
    items = []
    # Intentionally score ALL candidates before pagination. No silent first-N truncation.
    for notice in db.scalars(query.execution_options(yield_per=200)):
        result = score_notice(AnalysisData.model_validate(notice.analysis.data), profile, policy)
        if result is not None and result["score"] > 0 and result["score"] >= threshold:
            items.append(card(notice, bookmarks, result))
    items.sort(key=lambda n: (-n["recommendation"]["score"], n["id"]))
    start = (page-1)*page_size
    return {"items": items[start:start+page_size], "total": len(items), "page": page,
            "page_size": page_size, "profile_version": profile["version"]}

# Keep this below static /new and /recommended paths.
@router.get("/notices/{notice_id}", summary="공지 원문·분석·추천 상세", response_model=NoticeDetail, openapi_extra={"security":[{},{"BearerAuth":[]}]})
def notice_detail(notice_id: int, request: Request, principal=Depends(optional_principal), db=Depends(get_db)):
    notice = db.get(Notice, notice_id)
    if not notice or not notice.analysis:
        raise APIError(404, "NOTICE_NOT_FOUND", "공지를 찾을 수 없습니다.")
    result = None
    if principal:
        profile = profile_payload(db, principal.user.id)
        if profile["onboarding_complete"] and not (
            notice.analysis.deadline_at is not None and notice.analysis.deadline_at < now_ts()
        ):
            result = score_notice(AnalysisData.model_validate(notice.analysis.data), profile, request.app.state.policy)
    return detail(notice, bookmarked_ids(db, principal.user.id if principal else None), result)
