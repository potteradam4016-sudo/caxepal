import argparse
import json
import sys
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, func, select
from app.config import BASE_DIR, get_settings
from app.db import make_engine, session_factory
from app.models import AuthSession, Bookmark, CrawlJob, Notice, NoticeAnalysis, RateBucket, User, now_ts
from app.reference import publisher_category, seed_reference
from app.schemas import AnalysisData, CrawlInput
from app.services.analysis import analyze, apply_analysis, clean_summary_lines, extract_rules, schedule_evidence_text
from app.services.dates import deadline_values, has_date_expression
from app.services.jobs import enqueue, run_next_job

def migrate(settings):
    config = Config(str(BASE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%","%%"))
    command.upgrade(config, "head")
    engine = make_engine(settings.database_url)
    if settings.database_url.startswith("sqlite") and ":memory:" not in settings.database_url:
        # WAL improves local concurrent readers; still not a multi-server production DB.
        raw = engine.raw_connection()
        try:
            raw.execute("PRAGMA journal_mode=WAL")
        finally:
            raw.close()
    with session_factory(engine)() as db:
        seed_reference(db)
    engine.dispose()

def purge_legacy_notices(db, apply=False):
    legacy = ("SCNU_SW", "SCNU_AI")
    notice_count = db.scalar(select(func.count()).select_from(Notice)
        .where(Notice.source_code.in_(legacy)))
    bookmark_count = db.scalar(select(func.count()).select_from(Bookmark).join(Notice)
        .where(Notice.source_code.in_(legacy)))
    if apply:
        db.execute(delete(Notice).where(Notice.source_code.in_(legacy)))
        db.commit()
    return notice_count, bookmark_count

def main():
    parser = argparse.ArgumentParser(description="SCNU PICK 백엔드 관리 명령 (실행 서버 접근 권한 필요)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db")
    admin = sub.add_parser("grant-admin")
    admin.add_argument("--username", required=True)
    admin.add_argument("--revoke", action="store_true")
    crawl = sub.add_parser("crawl")
    crawl.add_argument("--source", choices=["SCNU_MAIN"], default="SCNU_MAIN")
    crawl.add_argument("--pages", type=int, default=1)
    crawl.add_argument("--max-notices", type=int, default=5)
    crawl.add_argument("--max-age-days", type=int, default=60)
    sub.add_parser("cleanup")
    purge_legacy = sub.add_parser("purge-legacy-notices")
    purge_legacy.add_argument("--apply", action="store_true")
    author_refresh = sub.add_parser("refresh-authors")
    author_refresh.add_argument("--limit", type=int, default=100)
    purge = sub.add_parser("purge-gemini-analyses")
    purge.add_argument("--include-failed-fallbacks", action="store_true")
    export = sub.add_parser("export-openapi")
    export.add_argument("--output", default="docs/openapi.json")
    reanalyze = sub.add_parser("reanalyze")
    reanalyze.add_argument("--notice-id", type=int)
    reanalyze.add_argument("--limit", type=int, default=100)
    reanalyze.add_argument("--include-reviewed", action="store_true")
    reanalyze.add_argument("--failed-only", action="store_true")
    reanalyze.add_argument("--refresh-fallback", action="store_true")
    schedule_refresh = sub.add_parser("refresh-schedules")
    schedule_refresh.add_argument("--notice-id", type=int)
    schedule_refresh.add_argument("--limit", type=int, default=100)
    schedule_refresh.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    if args.command == "init-db":
        migrate(settings)
        print("DB 마이그레이션과 출처·관심사 사전 준비를 완료했습니다. 가짜 공지는 넣지 않았습니다.")
        return
    if args.command == "export-openapi":
        from app.factory import create_app
        app = create_app(settings)
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
        app.state.engine.dispose()
        print(f"저장 완료: {path}")
        return
    engine = make_engine(settings.database_url)
    factory = session_factory(engine)
    try:
        if args.command == "grant-admin":
            with factory() as db:
                user = db.scalar(select(User).where(User.username==args.username.strip().casefold()))
                if not user:
                    parser.error("먼저 해당 아이디로 가입하세요.")
                user.is_admin = not args.revoke
                db.commit()
            print("관리자 권한을 변경했습니다. 새 비밀번호나 테스트 관리자는 생성하지 않았습니다.")
        elif args.command == "crawl":
            if not settings.crawl_enabled:
                parser.error("허가받은 수집 조건을 반영한 뒤 backend/.env에서 CRAWL_ENABLED=true로 설정하세요.")
            options = CrawlInput(sources=[args.source],
                pages=args.pages, max_notices=args.max_notices, max_age_days=args.max_age_days)
            with factory() as db:
                job = enqueue(db, options)
                job_id = job.id
            result_id = run_next_job(factory, settings, target_id=job_id)
            with factory() as db:
                job = db.get(CrawlJob, job_id)
                print(json.dumps({"id":job.id,"status":job.status,"result":job.result,"error_code":job.error_code}, ensure_ascii=False, indent=2))
                if result_id is None:
                    print("다른 작업 처리기가 수집 중이므로 이 작업은 대기열에 남아 있습니다.")
                if job.status in {"failed","partial"}:
                    sys.exit(1)
        elif args.command == "cleanup":
            with factory() as db:
                for model in (AuthSession, RateBucket):
                    db.execute(delete(model).where(model.expires_at < now_ts()))
                db.commit()
            print("만료된 세션·요청 제한 기록을 정리했습니다.")
        elif args.command == "purge-legacy-notices":
            with factory() as db:
                notice_count, bookmark_count = purge_legacy_notices(db, args.apply)
            action = "삭제" if args.apply else "삭제 예정"
            print(f"별도 게시판 공지 {notice_count}건, 연결된 찜 {bookmark_count}건 {action}."
                  + ("" if args.apply else " 실제 삭제는 --apply를 붙이세요."))
        elif args.command == "refresh-authors":
            if not 1 <= args.limit <= 1000:
                parser.error("--limit은 1~1000 범위여야 합니다.")
            from app.crawlers.client import SafeClient
            from app.crawlers.parser import detail_author
            from bs4 import BeautifulSoup
            with factory() as db:
                notices = db.execute(select(Notice.id, Notice.original_url)
                    .where(Notice.source_code == "SCNU_MAIN", Notice.author_name.is_(None))
                    .order_by(Notice.id).limit(args.limit)).all()
            updated = failed = 0
            with SafeClient(settings) as client:
                client.prepare_robots()
                for notice_id, url in notices:
                    try:
                        soup = BeautifulSoup(client.get_html(url), "html.parser")
                        author = detail_author(soup)
                        if not author:
                            failed += 1
                            continue
                        with factory() as db:
                            notice = db.get(Notice, notice_id)
                            if notice and notice.source_code == "SCNU_MAIN":
                                notice.author_name = author[:100]
                                notice.publisher_category = publisher_category(author)
                                db.commit()
                                updated += 1
                    except Exception:
                        failed += 1
            print(f"대표 공지 작성자 {updated}건 갱신, {failed}건 실패. AI 재분석은 하지 않았습니다.")
        elif args.command == "purge-gemini-analyses":
            with factory() as db:
                target = NoticeAnalysis.provider == "gemini"
                if args.include_failed_fallbacks:
                    target |= ((NoticeAnalysis.provider == "rules_fallback") &
                               (NoticeAnalysis.status == "failed"))
                notices = db.scalars(select(Notice).join(NoticeAnalysis)
                    .where(target).with_for_update()).all()
                for notice in notices:
                    data, warnings = extract_rules(notice.title, notice.body_text, notice.image_only)
                    apply_analysis(notice, data, "rules", "needs_review", warnings)
                db.commit()
            print(f"Gemini 분석 {len(notices)}건을 규칙 분석으로 교체했습니다. 공지와 찜은 유지했습니다.")
        elif args.command == "refresh-schedules":
            if not 1 <= args.limit <= 1000:
                parser.error("--limit은 1~1000 범위여야 합니다.")
            with factory() as db:
                query = select(Notice.id).order_by(Notice.id).limit(args.limit)
                if args.notice_id is not None:
                    query = query.where(Notice.id == args.notice_id)
                ids = db.scalars(query).all()
            updated = reviewed = 0
            for ident in ids:
                with factory() as db:
                    notice = db.get(Notice, ident, with_for_update=args.apply)
                    if not notice or not notice.analysis:
                        continue
                    analysis = notice.analysis
                    if analysis.provider == "manual":
                        reviewed += 1
                        continue
                    current = AnalysisData.model_validate(analysis.data)
                    fresh, _ = extract_rules(notice.title, notice.body_text, notice.image_only)
                    old_dates = sum(int(s.start_date is not None) + int(s.end_date is not None)
                                    for s in current.schedules)
                    new_dates = sum(int(s.start_date is not None) + int(s.end_date is not None)
                                    for s in fresh.schedules)
                    empty_heading = any(not has_date_expression(s.evidence) for s in current.schedules)
                    if new_dates <= old_dates and not empty_heading:
                        continue
                    current.schedules = fresh.schedules
                    current.summary_lines[2] = clean_summary_lines([
                        current.summary_lines[0], current.summary_lines[1],
                        f"일정: {schedule_evidence_text(current.schedules)}",
                    ])[2]
                    if args.apply:
                        analysis.data = current.model_dump(mode="json")
                        analysis.deadline_date, analysis.deadline_at = deadline_values(current.schedules)
                        notice.search_text = "\n".join([
                            notice.title, notice.body_text, *current.summary_lines, *current.tags])
                        db.commit()
                    updated += 1
            action = "갱신" if args.apply else "갱신 예정"
            print(f"공지 일정 {updated}건 {action}, 관리자 검수 {reviewed}건 보존. AI는 호출하지 않았습니다."
                  + ("" if args.apply else " 실제 반영은 --apply를 붙이세요."))
        elif args.command == "reanalyze":
            if not 1 <= args.limit <= 1000:
                parser.error("--limit은 1~1000 범위여야 합니다.")
            with factory() as db:
                query = select(Notice.id).order_by(Notice.id).limit(args.limit)
                if args.notice_id is not None:
                    query = query.where(Notice.id==args.notice_id)
                if args.failed_only or args.refresh_fallback:
                    query = query.join(NoticeAnalysis).where(NoticeAnalysis.status=="failed")
                ids = db.scalars(query).all()
            updated = retained = 0
            for ident in ids:
                with factory() as db:
                    notice = db.get(Notice, ident)
                    if notice.analysis and notice.analysis.provider == "manual" and not args.include_reviewed:
                        continue
                    title, body, image_only, fingerprint = notice.title, notice.body_text, notice.image_only, notice.content_hash
                    old_warnings = list(notice.analysis.warnings) if notice.analysis else []
                if args.refresh_fallback:
                    data, rule_warnings = extract_rules(title, body, image_only)
                    failure_warnings = [item for item in old_warnings if item.startswith("AI_")]
                    result = data, "rules_fallback", "failed", list(dict.fromkeys(rule_warnings + failure_warnings))
                else:
                    result = analyze(settings, title, body, image_only)
                rate_limited = not args.refresh_fallback and "AI_RATE_LIMITED" in result[3]
                saved = False
                with factory() as db:
                    notice = db.get(Notice, ident)
                    if notice.content_hash != fingerprint:
                        continue
                    if result[2] == "failed" and notice.analysis and notice.analysis.status in {"analyzed", "reviewed"}:
                        retained += 1
                    else:
                        apply_analysis(notice, *result)
                        db.commit()
                        updated += 1
                        saved = True
                if args.notice_id is not None or args.limit == 1:
                    codes = ",".join(item for item in result[3] if item.startswith("AI_")) or "none"
                    print(f"notice_id={ident} provider={result[1]} status={result[2]} saved={saved} codes={codes}")
                if rate_limited:
                    print("OpenAI rate limit reached; stop this batch and retry later.")
                    break
            print(f"공지 {updated}건을 재분석하고, 기존 정상 결과 {retained}건을 유지했습니다. 모의 공지는 추가하지 않았습니다.")
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()
