# 구조와 담당 파일

## 1. 전체 흐름

```text
공식 게시판 3곳
    -> app/crawlers (안전한 HTTP 요청, HTML 해석)
    -> app/services/crawl (중복·변경 확인)
    -> app/services/analysis (구조화, 근거 검증)
    -> DB (원문과 분석 분리)
    -> app/api (조회, 추천, 찜, 캘린더)
    -> 향후 프론트엔드

사용자 -> 인증 API -> DB 세션 -> 본인 프로필·찜
관리자 -> 작업 접수 -> DB 작업 큐 -> 별도 worker -> 수집 결과
```

API 요청 처리 중 긴 크롤링을 실행하지 않습니다.
수집 접수는 DB에 남고 worker가 가져갑니다.
`start.py`는 개발 편의를 위해 API와 worker 두 프로세스를 함께 켭니다.
배포에서는 두 프로세스를 각각 관리합니다.

## 2. 어떤 파일을 고치면 되는가

| 위치 | 책임 |
| --- | --- |
| `app/config.py` | `.env` 읽기, 운영 금지 설정 검사 |
| `app/factory.py`, `app/asgi.py` | FastAPI 생성·진입점·마이그레이션 확인 |
| `app/db.py`, `app/models.py` | DB 연결과 테이블 |
| `app/schemas.py` | API 입력/출력 및 분석 결과 자료형·검증 |
| `app/security.py` | Argon2id, 무작위 토큰, 인증 사용자·관리자 의존성 |
| `app/middleware.py`, `app/errors.py` | 본문 크기·요청 제한·헤더·오류 |
| `app/api/auth.py` | 계정·메일 확인·세션·복구 |
| `app/api/profile.py` | 관심사·본인 학적 |
| `app/api/notices.py` | 공지·추천·검색·필터·출처 |
| `app/api/bookmarks.py` | 찜과 월간 캘린더 |
| `app/api/admin.py` | 수집 작업·검수 |
| `app/services/dates.py` | 날짜·시간·한국 마감 판정 |
| `app/services/recommendations.py` | 시간 변수를 받지 않는 적합도 계산 |
| `app/services/analysis.py` | 규칙/선택적 AI 분석 및 근거 확인 |
| `app/services/jobs.py`, `app/worker.py` | 작업 큐, 독점 lease, 재실행·자동 주기 |
| `app/crawlers/parser.py`, `client.py` | CMS 선택자 및 허용 URL·robots·재시도 |
| `app/reference.py` | 출처·관심사 사전 제안 |
| `app/cli.py` | 초기화, 관리자, 수집, 메일 확인, 재분석, 정리 |
| `migrations/` | 스키마 변경 이력 |
| `tests/` | 임시 DB·합성 HTML 기반 회귀 시험 |

## 3. DB 테이블

| 테이블 | 내용 |
| --- | --- |
| users | 이메일, 비밀번호 해시, 이메일 확인 여부, 관리자 여부 |
| profiles | 본인 학적·수정 버전 |
| interests / profile_interests | 사전과 사용자 선택 |
| auth_sessions | 로그인 토큰 해시·만료 |
| auth_tokens | 이메일 확인/비밀번호 재설정 토큰 해시·만료 |
| sources | 세 출처, 활성 상태, 마지막 성공 |
| notices | 원문 ID·제목·텍스트·게시일·원문 URL·첨부 정보·hash |
| notice_analyses | 구조화 JSON, 상태, 검수·마감 조회 필드 |
| bookmarks | 사용자-공지 찜, 복합 기본키 |
| crawl_jobs | 영속 수집 작업, 인수·시도·상태·결과 |
| crawl_runs | 출처별 수집 실행, 건수와 오류 |
| leases | worker·scheduler의 독점 처리 상태 |
| rate_buckets | 공유 요청 제한 횟수 |
| audit_logs | 메일 실패·수동 검수 등 안전한 운영 기록 |

원문 공지는 `(source_code, external_id)` 유일 제약으로 중복을 막습니다.
계정 삭제 시 프로필·관심 선택·세션·토큰·찜은 외래키 cascade로 삭제합니다.
개인정보가 아닌 공지 원문을 계정과 함께 지우지 않습니다.
epoch timestamp 열은 BIGINT입니다.

`python -m app.cli init-db`는 Alembic `0001` 마이그레이션 후 출처/관심사만 추가합니다.
반복 실행해도 사용자·공지·기존 reference 설정을 초기화하지 않습니다.
reference seed는 기존 행을 자동 수정하거나 삭제하지 않으므로 사전 변경 시 데이터 마이그레이션이 필요합니다.
개발 API 시작 시 임의 `create_all()`로 스키마를 변경하지 않습니다.

## 4. 인증 방식

이 구현의 계정 원장은 자체 `users` 테이블입니다.
로그인 응답에서만 원본 무작위 세션 토큰을 전달하며 DB에는 SHA-256 해시를 보관합니다.
비밀번호에는 Argon2id를 사용합니다. 토큰 해시와 비밀번호 해시는 목적이 다릅니다.
이메일 확인/재설정 토큰은 일회용 DB DELETE RETURNING으로 소비합니다.

운영 세션은 서버 DB 조회로 확인하므로 폐기 후 바로 무효화됩니다.
Supabase JWT, service-role API key, React에서 직접 DB 접근은 사용하지 않습니다.
테스트의 사용자 격리는 API의 본인 조건을 검증한 것이며 실제 PostgreSQL 사용자별 RLS 시험을 뜻하지 않습니다.

## 5. 추천 제안 정책

점수 입력은 공지의 구조화 결과와 사용자의 학적·관심사뿐입니다.
추천 함수는 게시일·마감일을 인자로 받지 않습니다.

| 기준 | 제안 배점 |
| --- | --- |
| 분야 하나 이상 일치 | 35 |
| 명시적 대상 학과 일치 | 25 |
| 명시적 학적 상태 일치 | 15 |
| 명시적 학년 일치 | 10 |
| 활동 유형 하나 이상 일치 | 15 |

전 학과가 명시되면 학과 12점, 전 학년이 명시되면 학년 5점입니다.
여러 관심사가 맞아도 각 항목 최대점을 초과해 더하지 않습니다.
명시되지 않은 자격에 일치 점수를 주지 않습니다.
미확인 대상은 필터에서 임의 탈락시키지 않지만, 직접 원문에서 자격을 확인해야 합니다.

기본 0점은 숨기고 0점을 초과한 결과부터 표시합니다.
85점 이상 '매우 적합', 70점 이상 '적합', 50점 이상 '관심 가능', 나머지는 '낮은 관련성'입니다.
제안 배점·기준값은 팀 승인 후 `config/recommendation-policy.json`과 테스트를 같이 변경합니다.
이유는 점수를 실제로 올린 항목에서만 선택합니다.

모든 후보를 점수화한 뒤 페이지를 자릅니다.
이 방식은 작은 해커톤 데이터셋에 적합한 단순 구현이며 대규모 데이터에서는 DB 집계·캐시·성능 검증이 필요합니다.
조회 중 프로필이 바뀌는 상황과 다중 사용자 대규모 부하는 별도 운영 검수 대상입니다.

## 6. 안전한 기본값과 한계

메일은 개발 파일 모드, 수집과 자동 수집은 비활성화, 외부 AI는 미사용이 기본입니다.
운영 모드에서 개발 DB/메일이 조용히 사용되지 않도록 시작 시 거부합니다.
회원 데이터는 API에서 본인 ID 조건을 강제합니다. 공개 테이블 직접 읽기 권한은 제공하지 않습니다.

요청 제한은 DB 기반 고정 시간창 방식으로 MVP용입니다.
분산 대규모 서비스의 전문 방어 체계나 완전한 DDoS 보호가 아닙니다.
프록시 뒤의 실사용자 IP 설정, PostgreSQL 역할 최소화, 비밀 관리·백업·독립 보안 검토가 운영 전 필요합니다.
백엔드 코드 제공을 운영 서비스 배포 완료와 혼동하지 않습니다.
