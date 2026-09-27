import calendar as cal
from datetime import date
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import delete, select
from app.db import dialect_insert, get_db
from app.errors import APIError
from app.models import Bookmark, Notice
from app.schemas import AnalysisData, CalendarOut, NoticePage
from app.security import current_principal
from app.services.notices import bookmarked_ids, paginate

router = APIRouter(tags=["찜·캘린더"])

@router.get("/bookmarks", summary="본인이 찜한 공지 목록", response_model=NoticePage)
def bookmarks(page: int = Query(1, ge=1, le=100000), page_size: int = Query(20, ge=1, le=100),
              principal=Depends(current_principal), db=Depends(get_db)):
    stmt = select(Notice).join(Bookmark).where(Bookmark.user_id == principal.user.id).order_by(
        Bookmark.created_at.desc(), Notice.id.desc())
    return paginate(db, stmt, page, page_size, bookmarked_ids(db, principal.user.id))

@router.post("/bookmarks/{notice_id}", summary="공지 찜하기", status_code=204)
def add_bookmark(notice_id: int, principal=Depends(current_principal), db=Depends(get_db)):
    if not db.get(Notice, notice_id):
        raise APIError(404, "NOTICE_NOT_FOUND", "공지를 찾을 수 없습니다.")
    db.execute(dialect_insert(db, Bookmark).values(user_id=principal.user.id, notice_id=notice_id)
               .on_conflict_do_nothing(index_elements=["user_id", "notice_id"]))
    db.commit()
    return Response(status_code=204)

@router.delete("/bookmarks/{notice_id}", summary="공지 찜 취소", status_code=204)
def delete_bookmark(notice_id: int, principal=Depends(current_principal), db=Depends(get_db)):
    db.execute(delete(Bookmark).where(Bookmark.user_id == principal.user.id, Bookmark.notice_id == notice_id))
    db.commit()
    return Response(status_code=204)

@router.get("/calendar", response_model=CalendarOut, summary="찜 공지의 월간 신청·행사 일정")
def calendar(month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
             principal=Depends(current_principal), db=Depends(get_db)):
    year, m = map(int, month.split("-"))
    if not 1900 <= year <= 2200:
        raise APIError(422, "INVALID_MONTH", "연도는 1900~2200 범위여야 합니다.")
    first, last = date(year, m, 1), date(year, m, cal.monthrange(year, m)[1])
    notices = db.scalars(select(Notice).join(Bookmark).where(Bookmark.user_id == principal.user.id)
                        .order_by(Notice.id)).all()
    events, undated = [], []
    for notice in notices:
        schedules = AnalysisData.model_validate(notice.analysis.data).schedules
        if not schedules:
            undated.append({"notice_id": notice.id, "title": notice.title, "label": "일정 미정"})
        for idx, s in enumerate(schedules):
            if not s.start_date and not s.end_date:
                undated.append({"notice_id": notice.id, "title": notice.title, "label": s.label + " · 일정 미정"})
                continue
            # A lone known boundary is shown as a point; the missing boundary remains null.
            start, end = s.start_date or s.end_date, s.end_date or s.start_date
            if start > last or end < first:
                continue
            events.append({"id": f"{notice.id}:{idx}", "notice_id": notice.id, "title": notice.title,
                "kind": s.kind, "label": s.label, "start_date": s.start_date, "end_date": s.end_date,
                "start_time": s.start_time, "end_time": s.end_time,
                "display_start": max(start, first), "display_end": min(end, last),
                "is_partial": s.start_date is None or s.end_date is None,
                "continues_before_month": start < first, "continues_after_month": end > last})
    events.sort(key=lambda x: (x["display_start"], x["kind"], x["id"]))
    return {"month": month, "events": events, "undated": undated}
