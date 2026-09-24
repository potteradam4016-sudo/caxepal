# 전체 백엔드 파일 목록

통합 ZIP의 `backend/`에는 파일 87개가 들어 있습니다.
개인 설정, DB, 가상환경, 테스트 캐시는 제외합니다.

| 경로 | 역할 |
| --- | --- |
| `.dockerignore` | 구성 파일 |
| `.env.example` | 구성 파일 |
| `.gitattributes` | 구성 파일 |
| `.gitignore` | 구성 파일 |
| `Dockerfile` | 구성 파일 |
| `README.md` | 설명·명세 |
| `SHA256SUMS.txt` | 구성 파일 |
| `START.cmd` | 실행·검증 도구 |
| `alembic.ini` | 구성 파일 |
| `app/__init__.py` | API·업무 코드 |
| `app/api/__init__.py` | API·업무 코드 |
| `app/api/admin.py` | API·업무 코드 |
| `app/api/auth.py` | API·업무 코드 |
| `app/api/bookmarks.py` | API·업무 코드 |
| `app/api/notices.py` | API·업무 코드 |
| `app/api/profile.py` | API·업무 코드 |
| `app/asgi.py` | API·업무 코드 |
| `app/cli.py` | API·업무 코드 |
| `app/config.py` | API·업무 코드 |
| `app/crawlers/__init__.py` | API·업무 코드 |
| `app/crawlers/client.py` | API·업무 코드 |
| `app/crawlers/parser.py` | API·업무 코드 |
| `app/db.py` | API·업무 코드 |
| `app/errors.py` | API·업무 코드 |
| `app/factory.py` | API·업무 코드 |
| `app/middleware.py` | API·업무 코드 |
| `app/models.py` | API·업무 코드 |
| `app/reference.py` | API·업무 코드 |
| `app/schemas.py` | API·업무 코드 |
| `app/security.py` | API·업무 코드 |
| `app/services/__init__.py` | API·업무 코드 |
| `app/services/analysis.py` | API·업무 코드 |
| `app/services/crawl.py` | API·업무 코드 |
| `app/services/dates.py` | API·업무 코드 |
| `app/services/jobs.py` | API·업무 코드 |
| `app/services/notices.py` | API·업무 코드 |
| `app/services/profiles.py` | API·업무 코드 |
| `app/services/rate_limit.py` | API·업무 코드 |
| `app/services/recommendations.py` | API·업무 코드 |
| `app/worker.py` | API·업무 코드 |
| `compose.yml` | 구성 파일 |
| `config/recommendation-policy.json` | 구성 파일 |
| `docs/API_CONTRACT.md` | 설명·명세 |
| `docs/ARCHITECTURE.md` | 설명·명세 |
| `docs/COMMIT_GUIDE.md` | 설명·명세 |
| `docs/COMMIT_INITIAL.txt` | 설명·명세 |
| `docs/COMMIT_UPDATE.txt` | 설명·명세 |
| `docs/COMMIT_USERNAME_API.txt` | 설명·명세 |
| `docs/CRAWLER_AND_AI.md` | 설명·명세 |
| `docs/DEPLOYMENT.md` | 설명·명세 |
| `docs/FILE_MANIFEST.md` | 설명·명세 |
| `docs/LOCAL_TEST_GUIDE.md` | 설명·명세 |
| `docs/REQUIREMENTS_TRACEABILITY.md` | 설명·명세 |
| `docs/SOURCES_AND_DECISIONS.md` | 설명·명세 |
| `docs/STARTUP_FIX.md` | 설명·명세 |
| `docs/TEST_REPORT.md` | 설명·명세 |
| `docs/UPLOAD_GUIDE.md` | 설명·명세 |
| `docs/USERNAME_AUTH_CHANGES.md` | 설명·명세 |
| `docs/backend-ci.yml.example` | 설명·명세 |
| `docs/http-verification.json` | 설명·명세 |
| `docs/openapi.json` | 설명·명세 |
| `docs/requests.http` | 설명·명세 |
| `docs/verification-summary.json` | 설명·명세 |
| `migrations/env.py` | DB 마이그레이션 |
| `migrations/script.py.mako` | DB 마이그레이션 |
| `migrations/versions/0001_initial_backend_schema.py` | DB 마이그레이션 |
| `migrations/versions/0002_username_auth.py` | DB 마이그레이션 |
| `pyproject.toml` | 구성 파일 |
| `requirements-dev.txt` | 구성 파일 |
| `requirements-postgres.txt` | 구성 파일 |
| `requirements.txt` | 구성 파일 |
| `scripts/package_backend.py` | 실행·검증 도구 |
| `scripts/verify_backend.py` | 실행·검증 도구 |
| `start.py` | 실행·검증 도구 |
| `tests/__init__.py` | 자동 테스트 |
| `tests/conftest.py` | 자동 테스트 |
| `tests/fixtures/detail.html` | 자동 테스트 |
| `tests/fixtures/list.html` | 자동 테스트 |
| `tests/test_analysis_security.py` | 자동 테스트 |
| `tests/test_atomic_migrations.py` | 자동 테스트 |
| `tests/test_auth.py` | 자동 테스트 |
| `tests/test_crawler.py` | 자동 테스트 |
| `tests/test_dates_calendar.py` | 자동 테스트 |
| `tests/test_documentation.py` | 자동 테스트 |
| `tests/test_profile_notices.py` | 자동 테스트 |
| `tests/test_runtime_smoke.py` | 자동 테스트 |
| `tests/test_startup.py` | 자동 테스트 |
