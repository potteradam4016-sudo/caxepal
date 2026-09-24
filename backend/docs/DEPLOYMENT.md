# 배포 전 설정

운영 환경은 PostgreSQL, HTTPS 프론트 주소, 명시적인 호스트와 CORS, 비밀키 보관, DB 백업을 갖춰야 합니다. 이 문서는 실제 배포 완료 보고서가 아닙니다.

## 환경 설정

`.env.example`을 복사해 개인 `.env`를 만듭니다. `APP_ENV=production`에서는 PostgreSQL URL과 HTTPS 프론트 주소 및 CORS origin이 필요합니다. `SECRET_KEY`는 32자 이상 무작위 값으로 보관합니다. DB URL의 계정·비밀번호는 외부에 공유하지 않습니다.

```dotenv
APP_ENV=production
DATABASE_URL=postgresql+psycopg://<USER>:<URL_ENCODED_PASSWORD>@<HOST>:5432/<DATABASE>
FRONTEND_URL=https://pick.example.org
CORS_ORIGINS=https://pick.example.org
ALLOWED_HOSTS=api.pick.example.org
```

위 URL은 형식 예시입니다. 실제 값은 배포 플랫폼의 비밀 설정에 보관합니다. DB 계정은 마이그레이션과 API 접근 권한을 점검합니다.

## 실행 순서

패키지를 설치하고 `python -m app.cli init-db`를 실행한 뒤 API와 worker를 시작합니다. `compose.yml`은 API와 worker 구성을 보여주며 외부 PostgreSQL을 사용합니다. `/health`와 `/docs`를 확인합니다.

프론트엔드는 `username`과 `password`로 가입·로그인하고, 현재 비밀번호를 확인하는 변경 API를 사용합니다. 비밀번호 분실 계정의 복구는 이번 MVP에서 제공하지 않습니다. 운영팀의 계정 소유 확인 절차가 마련되기 전까지 임의의 관리자 재설정을 추가하지 않습니다.

실제 공지 수집은 허가 조건을 확인한 뒤 `CRAWL_ENABLED=true`로 활성화합니다. 외부 AI는 모델·키·비용·결과 검증을 마친 뒤 사용합니다.
