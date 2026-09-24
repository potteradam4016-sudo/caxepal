import argparse
import json
import sys
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, select
from app.config import BASE_DIR, get_settings
from app.db import make_engine, session_factory
from app.models import AuthSession, CrawlJob, Notice, RateBucket, User, now_ts
from app.reference import seed_reference
from app.schemas import CrawlInput
from app.services.analysis import analyze, apply_analysis
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

def main():
    parser = argparse.ArgumentParser(description="SCNU PICK 백엔드 관리 명령 (실행 서버 접근 권한 필요)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db")
    admin = sub.add_parser("grant-admin")
    admin.add_argument("--username", required=True)
    admin.add_argument("--revoke", action="store_true")
    crawl = sub.add_parser("crawl")
    crawl.add_argument("--source", choices=["all","SCNU_MAIN","SCNU_SW","SCNU_AI"], default="all")
    crawl.add_argument("--pages", type=int, default=1)
    crawl.add_argument("--max-notices", type=int, default=5)
    crawl.add_argument("--max-age-days", type=int, default=60)
    sub.add_parser("cleanup")
    export = sub.add_parser("export-openapi")
    export.add_argument("--output", default="docs/openapi.json")
    reanalyze = sub.add_parser("reanalyze")
    reanalyze.add_argument("--notice-id", type=int)
    reanalyze.add_argument("--limit", type=int, default=100)
    reanalyze.add_argument("--include-reviewed", action="store_true")
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
            options = CrawlInput(sources=["SCNU_MAIN","SCNU_SW","SCNU_AI"] if args.source=="all" else [args.source],
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
        elif args.command == "reanalyze":
            if not 1 <= args.limit <= 1000:
                parser.error("--limit은 1~1000 범위여야 합니다.")
            with factory() as db:
                query = select(Notice.id).order_by(Notice.id).limit(args.limit)
                if args.notice_id is not None:
                    query = query.where(Notice.id==args.notice_id)
                ids = db.scalars(query).all()
            updated = 0
            for ident in ids:
                with factory() as db:
                    notice = db.get(Notice, ident)
                    if notice.analysis and notice.analysis.provider == "manual" and not args.include_reviewed:
                        continue
                    title, body, image_only, fingerprint = notice.title, notice.body_text, notice.image_only, notice.content_hash
                result = analyze(settings, title, body, image_only)
                with factory() as db:
                    notice = db.get(Notice, ident)
                    if notice.content_hash != fingerprint:
                        continue
                    apply_analysis(notice, *result)
                    db.commit()
                    updated += 1
            print(f"공지 {updated}건을 재분석했습니다. 모의 공지는 추가하지 않았습니다.")
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()
