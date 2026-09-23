# 배포 전 설정·검수

이 문서는 배포 방법과 남은 검증 항목입니다.
실제 학교 서버·클라우드·PostgreSQL·SMTP·AI 계정에 배포하거나 연결해 검증한 결과 보고서가 아닙니다.
현재 검증 완료 범위는 `TEST_REPORT.md`를 봅니다.

## 1. 로컬 기본값 그대로 공개하지 않기

로컬은 SQLite·파일 메일·HTTP·수집 비활성화입니다.
운영은 PostgreSQL, 실제 SMTP, HTTPS 프론트 주소, 명시적 호스트/CORS가 필요합니다.
운영 예시의 `<...>`는 실제 값으로 바꿔야 하며 그대로 실행할 수 있는 자격증명이 아닙니다.

```dotenv
APP_ENV=production
SECRET_KEY=<무작위로_생성한_개인_비밀키>
DATABASE_URL=postgresql+psycopg://<USER>:<URL_ENCODED_PASSWORD>@<HOST>:5432/<DATABASE>
ALLOWED_HOSTS=<API_HOST>,127.0.0.1,localhost
CORS_ORIGINS=https://<FRONTEND_HOST>
FRONTEND_URL=https://<FRONTEND_HOST>
DOCS_ENABLED=false

MAIL_BACKEND=smtp
MAIL_FROM=<VERIFIED_SENDER_ADDRESS>
SMTP_HOST=<SMTP_HOST>
SMTP_PORT=587
SMTP_USERNAME=<SMTP_USERNAME>
SMTP_PASSWORD=<SMTP_PASSWORD>
SMTP_TLS=starttls

CRAWL_ENABLED=false
AUTO_CRAWL=false
ROBOTS_POLICY=strict

AI_PROVIDER=rules
```

DB 비밀번호의 특수문자는 URL 인코딩합니다. URL을 로그·PR·프론트 환경변수에 붙이지 않습니다.
외부 DB는 공급자의 TLS 요구 설정을 적용합니다.
PostgreSQL의 `sslmode=require`는 암호화를 요구하는 설정이며 완전한 서버 신원 확인과 동일하지 않습니다.
공급자가 제공하는 CA와 `sslmode=verify-full` 등 적절한 검증 옵션을 사용할 수 있는지 확인합니다.
여기서 제공하지 않은 인증서 경로를 있는 것처럼 설정하지 않습니다.

SECRET_KEY를 만드는 방법:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

소스 저장소에는 `.env.example`만 올리고 실제 값은 서버의 비밀 설정으로 넣습니다.
이 서버에서 SECRET_KEY는 요청 제한 식별자의 HMAC 등에 사용되며 로그인 토큰은 DB 세션으로 검증합니다.
키를 바꿨다는 이유만으로 모든 세션이 자동 로그아웃된다고 가정하지 않습니다.

## 2. PostgreSQL 연결과 마이그레이션

개발 가상환경이 준비된 상태에서 PostgreSQL 드라이버를 추가합니다.

```bash
.venv/bin/python -m pip install -r requirements-postgres.txt
```

Windows는 `.venv\Scripts\python.exe`로 바꿉니다.
운영 `.env`를 설정한 후, 서비스 시작 전에 **한 번의 배포 작업**에서 실행합니다.

```bash
.venv/bin/python -m app.cli init-db
```

이 CLI가 `.env`의 DATABASE_URL을 Alembic에 전달합니다.
`alembic.ini`만 읽는 단순 `alembic upgrade head`는 환경변수 연결을 빠뜨릴 수 있으므로 위 CLI를 기준으로 합니다.
모든 API worker가 각각 마이그레이션을 수행하게 하지 않습니다.
이미 다른 프로젝트 테이블이 있는 DB나 이전 시제품 SQLite를 새 스키마의 빈 DB로 간주하지 않습니다.
전용 DB/스키마와 백업을 준비하고 테스트 환경에서 먼저 적용합니다.

마이그레이션은 인증·프로필·공지·찜·작업·운영 테이블과 인덱스·제약을 생성합니다.
SQLite 초기화·반복 실행·ORM 스키마 일치 검사는 수행했습니다.
PostgreSQL은 오프라인 SQL 생성만 확인했으며 실제 서버 실행·권한·동시성 검증은 별도로 해야 합니다.

## 3. Supabase를 선택하는 경우의 중요한 차이

현재 구현은 Supabase Auth를 사용하지 않습니다.
Supabase를 사용한다면 현재 코드에서는 **PostgreSQL 접속 서비스**로만 사용합니다.
React에서 Supabase Data API로 프로필/찜/세션 테이블을 직접 읽게 연결하지 않습니다.

초기 PostgreSQL 마이그레이션은 업무 테이블에 RLS를 켜고 PUBLIC 및 존재하는 `anon`/`authenticated` 역할의
테이블 권한을 회수합니다. 공개 Data API의 의도하지 않은 접근을 줄이기 위한 차단 설정입니다.

**이것은 사용자별 Supabase RLS 정책 구현이 아닙니다.**
현재 서버는 테이블을 만든 신뢰된 DB 역할로 연결하는 구조이고, 테이블 소유자는 일반적으로 RLS를 우회합니다.
본인 사용자 데이터 격리는 API의 현재 사용자 ID 조건으로 수행합니다.
따라서 “DB의 사용자별 RLS로 격리 완료”라고 발표하면 안 됩니다.

운영에서는 API/worker 역할 최소 권한, 전용 스키마, 노출 API 비활성화, SQL 함수·기존 역할 권한까지 검토합니다.
애플리케이션 쿼리 실수에도 DB가 사용자별 행을 강제로 막도록 하려면 별도의 request context·역할·RLS 정책 설계가 필요합니다.
서버 DB 비밀번호는 프론트에 절대 전달하지 않습니다.

## 4. API와 worker 실행

로컬 통합 시작 도구 `start.py`는 운영 모드를 거부합니다.
운영에서는 프로세스 관리자 또는 Docker를 사용합니다.

Linux 프로세스 실행 형태:

```bash
.venv/bin/python -m uvicorn app.asgi:app --host 127.0.0.1 --port 3104 --no-access-log --no-proxy-headers
.venv/bin/python -m app.worker
```

두 명령은 각각의 서비스로 관리합니다. 한 터미널에서 첫 명령이 실행 중이면 두 번째가 자동 실행되지 않습니다.
서버 경로·사용자·가상환경을 서비스 설정에 맞게 지정하고 재시작·로그·종료를 검증합니다.

학교 서버 할당 포트는 3104를 기준으로 하되 외부 공개 도메인은 실제 할당 내용을 확인합니다.
아직 프론트엔드가 없어 이 패키지는 루트 페이지에 API JSON을 반환합니다.
추후 하나의 외부 도메인에서 운영한다면 프록시는 `/api`를 백엔드로,
나머지는 프론트 정적 파일/앱으로 보내도록 팀에서 구성합니다.
`/health`, 필요 시 `/docs`와 `/openapi.json`의 공개 여부도 정합니다.
프론트 SPA의 `/verify-email`, `/reset-password` 경로를 제공해야 실제 이메일 링크 UX가 완성됩니다.

## 5. 프록시와 요청 제한

기본 실행은 임의 `X-Forwarded-For`를 신뢰하지 않도록 proxy header 사용을 끕니다.
이 상태에서 프록시를 거치면 여러 사용자가 같은 프록시 IP로 보일 수 있습니다.
그 결과 사용자 전체가 같은 IP 요청 제한에 묶일 수 있습니다.

예를 들어 **실제 신뢰된 프록시가 127.0.0.1임을 확인한 경우에만**:

```bash
.venv/bin/python -m uvicorn app.asgi:app --host 127.0.0.1 --port 3104 --no-access-log --proxy-headers --forwarded-allow-ips 127.0.0.1
```

Docker/학교 프록시의 실제 접속 IP는 달라질 수 있습니다.
확인 없이 `--forwarded-allow-ips '*'`로 공개 입력을 신뢰하지 않습니다.
원본 사용자 IP 유지, 프록시 자체의 요청 제한·본문/응답 timeout·HTTPS 설정을 함께 검수합니다.
현재 DB 고정 시간창 요청 제한은 전문적인 대규모 DDoS 방어를 대체하지 않습니다.

## 6. Docker 예시

`compose.yml`은 API+worker만 포함하고 외부 PostgreSQL/SMTP를 전제로 합니다.
APP_ENV는 compose에서 production으로 강제합니다.
서비스는 비루트 사용자, 읽기 전용 파일시스템, cap drop, localhost 3104 공개로 설정했습니다.

운영 `.env` 준비 후:

```bash
docker compose build
docker compose run --rm api python -m app.cli init-db
docker compose up -d
docker compose logs --tail 100 api worker
```

컨테이너 이미지를 실제 빌드하거나 Docker로 배포한 검증은 이 환경에서 하지 못했습니다.
네트워크·플랫폼별 의존성 설치·외부 DB TLS·read-only 상태에서의 실행을 대상 서버에서 확인합니다.
SQLite와 파일 메일의 로컬 설정은 이 compose의 운영 구성에 맞지 않습니다.
3104를 외부 전체 인터페이스로 바로 공개하기보다 학교의 프록시·HTTPS 경로를 따릅니다.

## 7. 메일·AI·수집 승인 후 단계적 활성화

SMTP 테스트 계정으로 가입/메일 확인/복구가 실제 받은 편지함까지 도달하는지 확인합니다.
이메일 미배달도 API가 계정 존재 여부를 숨기기 위해 202를 반환할 수 있으므로 운영 기록도 확인합니다.
서비스 수신 주소·인증서·타임아웃·재발송 흐름을 점검합니다.

AI는 작은 표본에서 스키마 호환·비용·근거·실패 fallback을 확인합니다.
제공자는 팀 합의 후 선택합니다. 코드가 있다는 사실과 실제 키로 호출이 성공했다는 사실은 다릅니다.

수집은 허가된 출처 하나의 소수 공지부터 시험합니다.
세 출처 모두 주기 수집 허가와 파서 검증이 끝나기 전에는 전체 자동 수집을 켜지 않습니다.

## 8. 정리·백업·운영 전 통과 조건

만료 데이터 정리 명령:

```bash
.venv/bin/python -m app.cli cleanup
```

인증 만료 판단은 정리 여부와 독립적으로 적용됩니다.
운영에서는 정리 명령의 주기 실행을 별도로 설정해야 합니다.
개발 메일은 이 명령에서 오래된 파일을 삭제합니다.

실제 운영 전 최소 검수:
인증/복구 배달, 프론트↔API 연결, PostgreSQL 마이그레이션·권한·백업 복구,
실제 세 출처 목록·상세·중복·원문 변경, 날짜/혜택 표본 대조,
사용자 A/B 격리, worker 중단·재기동, HTTPS/CORS/프록시 IP,
부하·비용·장애 기록·비밀 노출 여부.

이 패키지의 자동 테스트를 독립 보안 심사나 실제 서비스의 운영 승인으로 대체하지 않습니다.
