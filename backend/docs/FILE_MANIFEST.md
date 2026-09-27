# 백엔드 파일 구성

현재 Git 저장소 기준의 역할 안내입니다. 초기 ZIP의 고정 파일 개수는 현재 소스 개수와 다르므로 사용하지 않습니다.

| 위치 | 역할 |
| --- | --- |
| `app/config.py`, `.env.example` | 서버 설정·운영 검증·비밀값 없는 예시 |
| `app/asgi.py`, `app/factory.py` | FastAPI 진입점·미들웨어·라우터 |
| `app/api/` | 인증·프로필·공지·찜·캘린더·관리자 API |
| `app/models.py`, `app/schemas.py`, `app/db.py` | DB 모델·입출력·연결 |
| `app/crawlers/` | 대표 게시판 수집·작성자·표 본문 파싱 |
| `app/services/` | 분석·일정·요약 정리·추천·수집·세션·요청 제한 |
| `app/reference.py`, `config/` | 게시판·작성자 분류·관심사·추천 정책 |
| `app/cli.py`, `app/worker.py` | 운영 명령·독립 작업 처리기 |
| `migrations/versions/` | 0001 초기, 0002 아이디 인증, 0003 작성자·출처 분류 |
| `start.py`, `START.cmd` | 개발 환경 준비·API와 worker 실행 |
| `Dockerfile`, `compose.yml` | 운영 API·worker 컨테이너 구성 |
| `requirements*.txt`, `pyproject.toml` | 의존성·테스트 설정 |
| `tests/` | 합성 입력·임시 SQLite·별도 PostgreSQL·실제 HTTP 검증 |
| `tests/serve_frontend_fixture.py` | 프론트 브라우저 시험용 격리 API |
| `scripts/verify_backend.py` | 실제 로컬 HTTP 흐름 검증 |
| `scripts/package_backend.py` | 별도 전달용 패키지 생성 도구 |
| `docs/` | 현재 계약·실행·배포 안내와 초기 전달 기록 |

전체 추적 파일은 저장소 루트에서 `git ls-files backend`로 확인합니다. `.env`, `.venv/`, 실제 DB·로그·캐시는 배포 소스에 포함하지 않습니다.

과거 `COMMIT_*.txt`와 ZIP 검증 산출물은 당시 기록이며 현재 변경 내용·테스트 결과를 보증하지 않습니다. 현재 결과는 [검증 보고서](TEST_REPORT.md)가 기준입니다.
