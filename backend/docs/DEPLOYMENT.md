# 운영 배포 설정과 실행 순서

2026-09-27 코드 기준입니다. 실제 배포 완료 보고서가 아닙니다. 공개 전 [배포 확인 목록](../../docs/deployment-checklist.md)을 완료합니다.

## 구성과 전제

- React 정적 파일, FastAPI API, 별도 worker, 외부 PostgreSQL이 필요합니다.
- `compose.yml`은 API·worker만 실행합니다. DB·프론트 호스팅·도메인·HTTPS 프록시는 별도 준비합니다.
- API는 호스트의 `127.0.0.1:3104`에만 노출됩니다. 외부에는 HTTPS 프록시를 통해 연결합니다.
- `start.py`와 `START.cmd`는 개발 실행 도구이며 운영 실행에 사용하지 않습니다.
- 실제 운영 인프라에서 Docker 빌드·시작·재시작 검증을 수행해야 합니다. 이번 감사 환경에는 Docker가 없습니다.

## 서버 환경 변수

`backend/.env.example`을 참고해 배포 환경의 비밀 저장소 또는 접근 제한된 `.env`에 실제 값을 넣습니다. 아래 값은 형식 예시입니다.

```dotenv
APP_ENV=production
SECRET_KEY=<32자_이상의_충분히_무작위인_비밀값>
DATABASE_URL=postgresql+psycopg://<USER>:<URL_ENCODED_PASSWORD>@<DB_HOST>:5432/<DATABASE>
FRONTEND_URL=https://pick.example.org
CORS_ORIGINS=https://pick.example.org
ALLOWED_HOSTS=api.pick.example.org,localhost,127.0.0.1
DOCS_ENABLED=false
CRAWL_ENABLED=false
AUTO_CRAWL=false
AI_PROVIDER=rules
```

`APP_ENV=production`은 PostgreSQL과 HTTPS 프론트·CORS 주소를 요구합니다. origin에는 경로를 붙이지 않습니다. Compose healthcheck는 `127.0.0.1`로 요청하므로 `ALLOWED_HOSTS`에 이 값을 빼면 DB가 정상이더라도 healthcheck가 실패할 수 있습니다.

DB URL 비밀번호의 `@`, `#` 등은 URL 인코딩합니다. 컨테이너 안의 `127.0.0.1`은 호스트 PC나 외부 DB가 아닙니다. 컨테이너에서 도달 가능한 DB 호스트·방화벽·공급자 SSL/인증서 검증 설정을 확인합니다. 일반 실행 계정에는 필요한 최소 권한만 부여하고 마이그레이션 권한을 별도로 검토합니다.

OpenAI를 사용할 때만 `AI_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_MODEL`을 설정합니다. 예제에 있는 모델 문자열을 그대로 신뢰하지 말고 계정에서 실제 호출 가능한 모델인지 확인합니다. 키는 프론트·Git·로그에 넣지 않습니다. 수집과 AI의 허가·비용·품질 검증을 마친 뒤 활성화합니다.

## API와 worker

운영 DB 백업과 별도 DB 복원 연습을 먼저 수행합니다. `backend`에서 실행합니다.

```sh
docker compose build
docker compose run --rm api python -m app.cli init-db
docker compose up -d api worker
docker compose ps
```

현재 Alembic head는 `0003`입니다. `init-db`는 마이그레이션과 사전 seed를 수행하며 기존 출처의 활성 상태를 코드 정책대로 바꿉니다. 대표 게시판만 활성화하고 과거 SW·AI 출처는 비활성화합니다. 기존 공지·찜은 자동 삭제하지 않습니다.

대상 PostgreSQL에서 `SELECT version_num FROM alembic_version;`으로 `0003`을 확인합니다. 단순 `alembic current/upgrade` 명령은 현재 `alembic.ini`의 기본 SQLite URL을 사용하므로 운영 DB 검증·변경 명령으로 그대로 쓰지 않습니다. 설정의 `DATABASE_URL`을 반영하는 `app.cli init-db`를 사용합니다.

`/health`는 API·DB 접근 확인이지 worker·AI·학교 사이트의 정상 동작 보증이 아닙니다. worker 프로세스, 작업의 완료·실패 상태, 마지막 수집 성공 시각을 따로 확인합니다. 자동 수집은 기본 3시간 간격으로 최신순 최대 5페이지·40건을 확인하며 기존 공지도 한도에 포함됩니다. 재시작은 즉시 수집 명령이 아닙니다.

DB를 되돌릴 때는 무조건 downgrade하지 말고 백업·호환되는 앱 이미지로 복원하는 계획을 마련합니다. 운영 세션·요청 제한 기록은 `python -m app.cli cleanup`을 정기 실행하도록 운영 스케줄을 정합니다.

## HTTPS 프록시와 요청 제한

현재 Dockerfile은 `--no-proxy-headers`로 실행합니다. 이를 그대로 프록시 뒤에 두면 API가 여러 사용자를 프록시 IP 하나로 볼 수 있어 IP별 요청 제한을 공유하게 됩니다. 배포망에 맞는 명령 override가 필요합니다.

아래는 `compose.override.yml`의 형식 예시이며 `<TRUSTED_PROXY_IP>`를 실제 API에서 관측되는 프록시 주소로 교체해야 합니다.

```yaml
services:
  api:
    command: ["python", "-m", "uvicorn", "app.asgi:app", "--host", "0.0.0.0", "--port", "3104", "--no-access-log", "--proxy-headers", "--forwarded-allow-ips", "<TRUSTED_PROXY_IP>"]
```

프록시는 원래 `Host`와 올바른 `X-Forwarded-For`·`X-Forwarded-Proto`를 전달하고 외부에서 온 위조 헤더를 정리해야 합니다. 임의 클라이언트의 헤더를 신뢰하지 않도록 신뢰 대상을 제한합니다. 무조건 `*`를 넣지 않습니다. API 포트 직접 노출 차단과 실제 서로 다른 클라이언트의 요청 제한 분리를 배포 환경에서 확인합니다. [Uvicorn 설정](https://www.uvicorn.org/settings/)

## 프론트 빌드와 호스팅

저장소 루트 기준 PowerShell 예시입니다. 실제 공개 API 주소를 `/api` 없이 넣습니다.

```powershell
cd frontend
npm ci
$env:VITE_API_BASE_URL="https://api.pick.example.org"
npm run build
```

산출물 `frontend/dist/`를 정적 호스팅에 올립니다. 현재 앱은 도메인 루트(`/`) 배포 기준입니다. `/login`, `/recommend`, `/calendar` 직접 접속·새로고침은 `index.html`로 처리하는 SPA fallback이 필요합니다. 같은 호스트에서 API도 프록시한다면 `/api` 요청을 SPA fallback보다 먼저 라우팅합니다.

`VITE_API_BASE_URL`은 빌드 시 포함되므로 호스팅 환경변수만 바꾸어 이미 만들어진 JS를 수정할 수 없습니다. 기본값 localhost로 빌드한 산출물을 공개하지 않습니다. [Vite 환경 변수](https://vite.dev/guide/env-and-mode)

`npm run dev`·`npm run preview`는 운영 서버가 아닙니다. 정적 호스팅의 HTTPS, MIME type, `index.html` 갱신 정책과 해시 asset 캐시를 확인합니다. 파비콘은 `frontend/public/icons/SCNU_PICK_icon.png`를 바꾸고 재빌드합니다. [Vite 정적 배포](https://vite.dev/guide/static-deploy)

현재 주최 측 호스트는 SPA fallback이 없고 `/api/`를 프록시할 때 앞의 `/api/`를 제거합니다. Nginx를 변경할 수 없는 경우 프론트를 `VITE_STATIC_HOSTING=true`, `VITE_API_BASE_URL=<루트 .env의 DEPLOY_ADDRESS>/api`로 빌드합니다. 사용자 화면은 `/#/login`처럼 열리고 `/api/api/...` 요청은 서버에서 `/api/...`로 전달됩니다. 이는 해당 호스트 설정에 한정된 빌드 값입니다.

해당 공유 서버에는 Docker·pip·ensurepip이 없고 제공 계정은 sudo를 사용할 수 없습니다. [uv 공식 설치 방법](https://docs.astral.sh/uv/getting-started/installation/)의 사용자 홈 설치와 `uv venv`·`uv pip install -r requirements-postgres.txt`로 Python 의존성을 준비할 수 있습니다. 실제 설치 전에 서버의 외부 다운로드 접근과 실행 정책을 확인합니다. 현재 PostgreSQL 접속 주소가 제공되지 않았으며 서버 로컬 5432 포트도 열려 있지 않습니다. DB를 확보한 뒤 앱/worker 실행과 재부팅 후 자동 시작 방식을 검증해야 합니다. `Linger=no`인 사용자 서비스만으로는 로그아웃 이후 상시 실행을 보장할 수 없습니다.

## 공개 전 검증

운영과 분리된 `_test` PostgreSQL DB를 만들고 해당 DB에만 접근하는 테스트 자격증명을 사용합니다. 테스트는 테이블을 비우므로 실제 데이터가 있는 DB를 지정하면 안 됩니다.

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -r requirements-postgres.txt
$env:TEST_DATABASE_URL="postgresql+psycopg://<TEST_USER>:<URL_ENCODED_PASSWORD>@<TEST_HOST>:5432/scnu_pick_test"
.\.venv\Scripts\python.exe -m pytest -m postgres
```

`TEST_DATABASE_URL`은 프로세스 환경변수로 전달하며 `.env`에 적기만 해서는 전용 테스트가 활성화되지 않습니다. 성공 6개를 확인하고 종료 후 `Remove-Item Env:TEST_DATABASE_URL`로 현재 셸에서 해제할 수 있습니다.

나머지 테스트 명령·이번 실행 결과는 [검증 보고서](TEST_REPORT.md)를 참고합니다. 운영 주소에서 CORS·보호 경로·세션·프로필 충돌·찜·캘린더·오류 화면·모바일·원문 링크를 재확인하고, 백업·로그·알림·수집 허가·개인정보 안내가 갖춰진 뒤 공개합니다.
