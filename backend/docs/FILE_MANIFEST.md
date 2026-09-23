# 전체 백엔드 파일 목록

이번 ZIP에는 `backend/` 아래 **84개 파일**이 있습니다.
첫 실행 수정본과 한국어 문서를 합친 전체 통합본이며, 별도 패치를 다시 적용하지 않습니다.

아래 경로는 `backend/` 기준입니다. 파일명은 코드·협업 링크와 맞추기 위해 유지했습니다.
설명 문서 13개는 한국어입니다. `.env`, `.venv/`, `data/`, 실제 DB·메일·로그·캐시는 포함하지 않습니다.
`tests/fixtures`와 검증 도구의 공지는 명시적인 합성 시험 자료이며 실제 학교 수집 결과가 아닙니다.

| 파일 | 역할 |
| --- | --- |
| `.dockerignore` | 컨테이너에 개인 설정·DB·캐시가 포함되지 않도록 제외 |
| `.env.example` | 비밀값이 비어 있는 개인 환경설정 양식 |
| `.gitattributes` | Windows 실행 파일·Python 파일의 줄바꿈 규칙 |
| `.gitignore` | 개인 설정·DB·가상환경·캐시의 Git 업로드 방지 |
| `Dockerfile` | API·작업 처리기용 컨테이너 빌드 제안 |
| `README.md` | 한국어 개요, 실행 방법, 문서 읽는 순서 |
| `SHA256SUMS.txt` | 이 파일을 제외한 배포 원본의 SHA-256 목록 |
| `START.cmd` | Windows에서 Python을 찾아 백엔드를 실행 |
| `alembic.ini` | DB 마이그레이션 기본 설정 |
| `app/__init__.py` | Python 패키지 표시; 빈 파일이어도 정상 |
| `app/api/__init__.py` | Python 패키지 표시; 빈 파일이어도 정상 |
| `app/api/admin.py` | 인증·학적·공지·찜·관리자 HTTP API |
| `app/api/auth.py` | 인증·학적·공지·찜·관리자 HTTP API |
| `app/api/bookmarks.py` | 인증·학적·공지·찜·관리자 HTTP API |
| `app/api/notices.py` | 인증·학적·공지·찜·관리자 HTTP API |
| `app/api/profile.py` | 인증·학적·공지·찜·관리자 HTTP API |
| `app/asgi.py` | 서버 설정·DB·모델·보안·작업 처리 |
| `app/cli.py` | 서버 설정·DB·모델·보안·작업 처리 |
| `app/config.py` | 서버 설정·DB·모델·보안·작업 처리 |
| `app/crawlers/__init__.py` | Python 패키지 표시; 빈 파일이어도 정상 |
| `app/crawlers/client.py` | 허용된 학교 페이지 요청·HTML 분석 |
| `app/crawlers/parser.py` | 허용된 학교 페이지 요청·HTML 분석 |
| `app/db.py` | 서버 설정·DB·모델·보안·작업 처리 |
| `app/errors.py` | 서버 설정·DB·모델·보안·작업 처리 |
| `app/factory.py` | 서버 설정·DB·모델·보안·작업 처리 |
| `app/middleware.py` | 서버 설정·DB·모델·보안·작업 처리 |
| `app/models.py` | 서버 설정·DB·모델·보안·작업 처리 |
| `app/reference.py` | 서버 설정·DB·모델·보안·작업 처리 |
| `app/schemas.py` | 서버 설정·DB·모델·보안·작업 처리 |
| `app/security.py` | 서버 설정·DB·모델·보안·작업 처리 |
| `app/services/__init__.py` | Python 패키지 표시; 빈 파일이어도 정상 |
| `app/services/analysis.py` | 분석·추천·일정·메일·수집 등 업무 처리 |
| `app/services/crawl.py` | 분석·추천·일정·메일·수집 등 업무 처리 |
| `app/services/dates.py` | 분석·추천·일정·메일·수집 등 업무 처리 |
| `app/services/jobs.py` | 분석·추천·일정·메일·수집 등 업무 처리 |
| `app/services/mail.py` | 분석·추천·일정·메일·수집 등 업무 처리 |
| `app/services/notices.py` | 분석·추천·일정·메일·수집 등 업무 처리 |
| `app/services/profiles.py` | 분석·추천·일정·메일·수집 등 업무 처리 |
| `app/services/rate_limit.py` | 분석·추천·일정·메일·수집 등 업무 처리 |
| `app/services/recommendations.py` | 분석·추천·일정·메일·수집 등 업무 처리 |
| `app/worker.py` | 서버 설정·DB·모델·보안·작업 처리 |
| `compose.yml` | 외부 PostgreSQL·SMTP를 전제로 한 운영 구성 예시 |
| `config/recommendation-policy.json` | 팀 검토용 추천 배점·노출 정책 |
| `docs/API_CONTRACT.md` | 프론트 연동용 API·인증·오류·날짜 계약 |
| `docs/ARCHITECTURE.md` | 구조·DB 테이블·코드별 담당 역할 |
| `docs/COMMIT_GUIDE.md` | 초기 커밋·수정 커밋·PR 작성과 명령 |
| `docs/COMMIT_INITIAL.txt` | 처음 올리는 백엔드의 한국어 커밋 제목과 본문 |
| `docs/COMMIT_UPDATE.txt` | 기존 커밋 이후 이번 갱신의 한국어 커밋 제목과 본문 |
| `docs/CRAWLER_AND_AI.md` | 수집 허가·활성화·분석·재분석·검수 절차 |
| `docs/DEPLOYMENT.md` | 운영 DB·SMTP·배포·권한 검수 |
| `docs/FILE_MANIFEST.md` | 전체 파일 목록과 역할 |
| `docs/LOCAL_TEST_GUIDE.md` | Windows 기준 실행·가입·인증·API 시험 |
| `docs/REQUIREMENTS_TRACEABILITY.md` | 기획 요구사항과 구현·테스트의 대응 |
| `docs/SOURCES_AND_DECISIONS.md` | 입력 자료·설계 결정·공식 참고 문서 |
| `docs/STARTUP_FIX.md` | 이미 반영한 첫 실행 수정과 한국어 통합 이력 |
| `docs/TEST_REPORT.md` | 이번 통합본의 실제 검증 결과와 미검증 범위 |
| `docs/UPLOAD_GUIDE.md` | 협업용 설정·자료 |
| `docs/backend-ci.yml.example` | 검토 후 활성화할 Windows/Linux 자동 검증 예시 |
| `docs/http-verification.json` | 55개 실제 HTTP 요청의 경로·기대값·실제 상태 |
| `docs/openapi.json` | 현재 코드에서 생성한 전체 API 명세 |
| `docs/requests.http` | 한국어 주석이 있는 개발 API 요청 예제 |
| `docs/verification-summary.json` | 환경·패키지·전체 검증 결과의 기계 판독 요약 |
| `migrations/env.py` | DB 스키마 변경 이력과 실행 환경 |
| `migrations/script.py.mako` | DB 스키마 변경 이력과 실행 환경 |
| `migrations/versions/0001_initial_backend_schema.py` | DB 스키마 변경 이력과 실행 환경 |
| `pyproject.toml` | 프로젝트 정보와 자동 테스트 설정 |
| `requirements-dev.txt` | 자동 테스트 패키지 |
| `requirements-postgres.txt` | 운영 PostgreSQL 드라이버 |
| `requirements.txt` | 기본 API·DB·수집 패키지 버전 |
| `scripts/verify_backend.py` | 임시 DB·실제 HTTP 서버의 전체 사용자 흐름 검증 |
| `start.py` | 개인 설정·가상환경·패키지·DB 준비와 API·작업 처리기 실행 |
| `tests/__init__.py` | Python 패키지 표시; 빈 파일이어도 정상 |
| `tests/conftest.py` | 환경 격리·임시 DB·계정·공지 시험 구성 |
| `tests/fixtures/detail.html` | 실제 학교 자료가 아닌 합성 HTML 시험 입력 |
| `tests/fixtures/list.html` | 실제 학교 자료가 아닌 합성 HTML 시험 입력 |
| `tests/test_analysis_security.py` | 기능·오류·권한·수집 회귀 테스트 |
| `tests/test_atomic_migrations.py` | 기능·오류·권한·수집 회귀 테스트 |
| `tests/test_auth.py` | 기능·오류·권한·수집 회귀 테스트 |
| `tests/test_crawler.py` | 기능·오류·권한·수집 회귀 테스트 |
| `tests/test_dates_calendar.py` | 기능·오류·권한·수집 회귀 테스트 |
| `tests/test_documentation.py` | 한국어 문서·내부 링크·API 명세·예제 설정 검사 |
| `tests/test_profile_notices.py` | 기능·오류·권한·수집 회귀 테스트 |
| `tests/test_runtime_smoke.py` | 독립 실제 HTTP 검증 도구를 실행하는 통합 테스트 |
| `tests/test_startup.py` | 최초 DB 경로·실행 오류·비밀값·프로세스 정리 회귀 테스트 |

## 업로드·해시 확인 시 주의

ZIP의 `backend/`와 저장소의 `backend/`가 같은 위치입니다.
기존 `.env`, DB, 팀원의 소스는 삭제하지 말고 차이를 비교하세요.
`START.cmd`는 업로드 대상이며 실행 과정에서 생기는 개인 파일은 제외합니다.

`SHA256SUMS.txt`는 이 통합본을 압축 해제한 **원본 바이트** 기준입니다.
파일을 수정하거나 Git 설정이 줄바꿈을 변환하면 해시가 달라질 수 있습니다.
해시가 있다는 사실은 보안 심사나 운영 배포가 완료되었다는 뜻이 아닙니다.
