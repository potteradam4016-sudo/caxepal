from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from app.db import get_db
from app.errors import APIError
from app.models import AuditLog, CrawlJob, CrawlRun, Notice
from app.schemas import CrawlInput, CrawlJobOut, ManualAnalysisInput, NoticeDetail
from app.security import admin_principal
from app.services.analysis import apply_analysis
from app.services.jobs import enqueue
from app.services.notices import detail

router = APIRouter(prefix="/admin", tags=["관리자"], dependencies=[Depends(admin_principal)])

@router.post("/crawl-jobs", summary="공지 수집 작업 접수", response_model=CrawlJobOut, status_code=202)
def new_job(body: CrawlInput, request: Request, principal=Depends(admin_principal), db=Depends(get_db)):
    if not request.app.state.settings.crawl_enabled:
        raise APIError(403, "CRAWLING_DISABLED", ".env의 수집 설정과 허가 조건을 확인해주세요.")
    # Bounded queue prevents accidental rapid repeated clicks from enqueuing unlimited work.
    pending = db.scalar(select(CrawlJob.id).where(CrawlJob.status.in_(["queued", "running"])).limit(1))
    if pending:
        raise APIError(409, "CRAWL_ALREADY_PENDING", "진행 중이거나 대기 중인 수집 작업이 있습니다.")
    return enqueue(db, body, principal.user.id)

@router.get("/crawl-jobs", summary="최근 공지 수집 작업 조회", response_model=list[CrawlJobOut])
def jobs(limit: int = Query(20, ge=1, le=100), db=Depends(get_db)):
    return db.scalars(select(CrawlJob).order_by(CrawlJob.created_at.desc()).limit(limit)).all()

@router.get("/crawl-jobs/{job_id}", summary="단일 공지 수집 작업 상태 조회", response_model=CrawlJobOut)
def job_status(job_id: str, db=Depends(get_db)):
    job = db.get(CrawlJob, job_id)
    if not job:
        raise APIError(404, "JOB_NOT_FOUND", "작업을 찾을 수 없습니다.")
    return job

@router.get("/crawl-runs", summary="출처별 수집 실행 기록 조회", response_model=list[dict])
def runs(limit: int = Query(20, ge=1, le=100), db=Depends(get_db)):
    rows = db.scalars(select(CrawlRun).order_by(CrawlRun.id.desc()).limit(limit))
    return [{"id":r.id, "job_id":r.job_id, "source_code":r.source_code, "status":r.status,
             "counts":r.counts, "errors":r.errors, "started_at":r.started_at, "finished_at":r.finished_at} for r in rows]

@router.put("/notices/{notice_id}/analysis", summary="공지 분석 결과 수동 검수", response_model=NoticeDetail)
def review_analysis(notice_id: int, body: ManualAnalysisInput,
                    principal=Depends(admin_principal), db=Depends(get_db)):
    notice = db.get(Notice, notice_id)
    if not notice:
        raise APIError(404, "NOTICE_NOT_FOUND", "공지를 찾을 수 없습니다.")
    if notice.content_hash != body.expected_content_hash:
        raise APIError(409, "NOTICE_CHANGED", "원문이 변경되었습니다. 다시 조회하고 검수해주세요.")
    apply_analysis(notice, body.analysis, "manual", "reviewed", ["HUMAN_REVIEWED"])
    db.add(AuditLog(actor_id=principal.user.id, action="analysis_reviewed", resource_id=str(notice_id),
                    details={"content_hash":notice.content_hash}))
    db.commit()
    return detail(notice)
