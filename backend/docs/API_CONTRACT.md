# SCNU PICK API 계약 — 프론트 연동 v1

이 문서는 현재 백엔드 코드와 일치하는 **팀 검토용 계약**입니다.
React에서 사용하는 경로와 상태 처리는 공유 저장소 루트 `docs/api-contract.md`에도 정리되어 있습니다.
전체 필드·필수 여부는 함께 제공한 `openapi.json` 또는 실행 중인 `/docs`가 기준입니다.
React 구현은 저장소의 `frontend/`에서 확인할 수 있습니다.

## 1. 공통 규칙

개발 서버는 `http://localhost:3104`이며 업무 API의 접두사는 `/api`입니다.
요청과 응답은 JSON입니다. 생성/수정 시 `Content-Type: application/json`을 사용합니다.
경로에는 후행 `/`를 붙이지 않는 것을 기준으로 합니다.

시간이 없는 날짜는 `YYYY-MM-DD`, 시각은 한국 현지의 `HH:MM:SS`입니다.
`*_at`은 별도 설명이 없는 한 **UTC Unix 초**입니다. JavaScript Date 생성 시 `value * 1000`으로 변환합니다.
`null`은 미기재·미확정이며 0이나 임의 날짜로 바꾸지 않습니다.
모든 날짜 판단의 지역 시간대는 `Asia/Seoul`입니다.

성공 상태는 일반 조회 200, 접수 202, 본문 없는 완료 204입니다.
204 응답에 무조건 `response.json()`을 호출하지 않습니다.

인증은 자체 로그인에서 받은 내용을 해석할 수 없는 무작위 세션 토큰을 전달합니다.

```http
Authorization: Bearer <access_token>
```

JWT가 아닙니다. Supabase Auth 토큰도 아닙니다.
기본 유효기간은 24시간이며 토큰 갱신 API는 없습니다.
401이면 클라이언트의 토큰 상태를 지우고 로그인 화면으로 이동합니다.
토큰을 쿼리 문자열·콘솔·오류 추적 로그에 남기지 않습니다.

React는 토큰과 만료 시각을 sessionStorage에 저장하여 탭 내 새로고침을 지원합니다.
비밀번호는 저장하지 않으며 새로고침 시 /auth/me 및 /profile로 상태를 복원합니다.
쿠키/BFF 방식으로 바꾸려면 CSRF·쿠키 속성·CORS·갱신 계약도 함께 변경해야 합니다.
현재 서버는 쿠키 인증을 구현하지 않았고 `allow_credentials=False`입니다.

### 로컬 CORS 설정

로컬 프론트엔드 개발 서버는 `http://localhost:5173` 또는
`http://127.0.0.1:5173`을 사용합니다. 백엔드의 `CORS_ORIGINS`에는 브라우저가
접속한 프론트 origin을 정확히 등록해야 하며 경로나 후행 `/`를 넣지 않습니다.
백엔드 API 요청 대상인 `http://localhost:3104`는 허용 origin이 아니라 프론트의
API base URL입니다.

브라우저 preflight에서는 현재 API가 사용하는 `GET`, `POST`, `PUT`, `DELETE`,
`OPTIONS`와 `Authorization`, `Content-Type` 헤더만 허용합니다. 응답에서
`X-Request-ID`, `Retry-After`를 읽을 수 있습니다. 와일드카드 origin은 허용하지
않으며 등록되지 않은 origin의 preflight는 거부합니다. 운영 환경에서는 실제
HTTPS 프론트 주소를 `CORS_ORIGINS`와 `FRONTEND_URL`에 명시합니다.

## 2. 인증 API

아이디는 영문 소문자로 시작하는 영문 소문자·숫자·밑줄 3~32자입니다. 입력은 양쪽 공백을 제거하고 소문자로 통일합니다. 비밀번호는 가입·변경 시 12~128자입니다.

| 방식 | 경로 | 본문 | 성공 |
| --- | --- | --- | --- |
| POST | `/api/auth/register` | `username`, `password` | 201 |
| POST | `/api/auth/login` | `username`, `password` | 200 |
| GET | `/api/auth/me` | Bearer 토큰 | 200 |
| POST | `/api/auth/logout` | Bearer 토큰 | 204 |
| POST | `/api/auth/logout-all` | Bearer 토큰 | 204 |
| POST | `/api/auth/change-password` | Bearer 토큰, `current_password`, `new_password` | 200 |
| DELETE | `/api/auth/account` | Bearer 토큰, `password` | 204 |

중복 아이디는 409 `USERNAME_TAKEN`입니다. 비밀번호 변경은 현재 비밀번호를 다시 확인하고 모든 세션을 폐기합니다. 비밀번호를 잊은 계정에 대한 셀프 복구는 MVP에서 제공하지 않습니다. 계정 소유를 확인할 수 있는 별도 운영 절차가 확정될 때까지 새 계정을 사용하도록 안내합니다. 관리자도 임의의 비밀번호를 재설정할 수 없습니다.

```json
{
  "access_token": "<opaque random token>",
  "token_type": "bearer",
  "expires_at": 1789999999,
  "user": {
    "id": "<uuid>",
    "username": "student01",
    "is_admin": false,
    "onboarding_complete": false
  }
}
```

## 3. 관심사·프로필

`GET /api/interests`는 공개 API입니다. `id`, 표시 이름 `name`, `type`을 반환합니다.
현재 제안값은 분야 8개, 활동 7개입니다.
ID를 화면 코드에 임의 생성하지 말고 API 응답을 사용합니다.

`GET /api/profile` 및 `PUT /api/profile`은 인증이 필요합니다.

```json
{
  "department": "컴퓨터공학과",
  "grade": 2,
  "academic_status": "enrolled",
  "interest_ids": ["ai_sw", "hackathon"],
  "expected_version": 0
}
```

학년은 1~6, 학적은 `enrolled / on_leave / graduating / graduated`입니다.
과목·학과 이름은 학생이 직접 입력합니다. 학교 원장과 대조하지 않습니다.
동일 관심사 ID는 중복 제거하며 알 수 없는 ID는 422입니다.

분야와 활동을 각각 하나 이상 선택해야 `onboarding_complete=true`입니다.
프로필 수정 시 학적과 관심사를 한 트랜잭션으로 저장합니다.
`expected_version`을 보내면 현재 버전이 다를 때 409 `PROFILE_CONFLICT`입니다.
버전 필드를 생략한 PUT은 조건 없는 최신 저장이므로 실제 화면에서는 버전을 보내는 방식을 사용합니다.

응답은 `user_id`, 학적, `interests`, `onboarding_complete`, `version`, `updated_at`입니다.
`user_id`를 요청 본문으로 지정할 수 없습니다. 항상 인증된 본인 자료를 조회·수정합니다.
취소는 API를 호출하지 않는 동작이며, 수정 완료 후 추천 목록을 다시 조회합니다.
기존 찜과 캘린더는 수정하지 않습니다.

## 4. 공지 목록·검색·신규·추천

| 경로 | 인증 | 의미 |
| --- | --- | --- |
| `GET /api/sources` | 불필요 | 출처 세 곳과 마지막 성공 시각 |
| `GET /api/notices` | 선택 | 전체 수집 공지의 검색·필터 |
| `GET /api/notices/new` | 선택 | 원문 등록일 최신순 목록 |
| `GET /api/notices/recommended` | 필수 | 온보딩 완료 사용자의 맞춤 추천 |
| `GET /api/notices/{notice_id}` | 선택 | 상세·구조화 결과·첨부 메타데이터 |

선택 인증은 **토큰이 아예 없을 때만** 비로그인으로 처리합니다.
잘못된/만료된 토큰을 보내면 공개 조회에서도 401입니다.
비로그인 상태의 `is_bookmarked`는 false, `recommendation`은 null입니다.

공통 목록 쿼리:

| 파라미터 | 범위/기본값 | 비고 |
| --- | --- | --- |
| `source` | 생략 또는 `SCNU_MAIN / SCNU_SW / SCNU_AI` | 글로컬 미지원 |
| `category` | 아래 enum | 반복 쿼리로 복수 선택, OR 조건 |
| `q` | 최대 100자 | 제목·본문·요약·태그의 문자 검색 |
| `closing_days` | 0~90, 생략 시 마감 필터 없음 | 오늘부터 N일 뒤까지; 미정·지난 마감 제외 |
| `page` | 1~100000, 기본 1 | 1부터 시작 |
| `page_size` | 1~100, 기본 20 | 전체 결과 수 `total` 별도 반환 |

`/notices`, `/notices/new`는 추가로 `days`(1~365)와 `include_closed`(기본 true)를 받습니다.
`days`를 생략하면 수집된 전체 기간이며, 최근 7일 화면은 `/api/notices/new?days=7`로 요청합니다.
기간은 한국 날짜 단위로 오늘을 포함한 N일입니다. 정확한 최근 24시간 필터와는 다릅니다.
`include_closed=false`를 명시하면 신청 마감이 지난 공지를 제외합니다.
신규 목록 자체는 신청 상태와 별개로 원문 등록일 내림차순입니다.

`/recommended`는 `min_score`(0~100)를 추가로 받습니다.
기본 설정은 0이지만 **실제 기여 항목이 없는 0점 결과는 노출하지 않습니다**.
추천도 계산 전에 마감·명확한 자격 불일치를 제외합니다.
같은 점수는 ID 순서로 정렬하며 최신성·임박성으로 동점을 깨지 않습니다.
마감 필터를 조합해도 점수 가산은 없습니다.
프로필 미완성이면 409 `PROFILE_INCOMPLETE`입니다.

카테고리:
`contest`, `education`, `scholarship`, `career`, `startup`, `overseas`, `volunteer`, `other`.

`category=education&category=contest`는 두 분류의 합집합입니다. 단일 값도 지원합니다.
필터는 전체 개수 계산, 추천 정렬과 페이지 분할 전에 적용됩니다.

목록 응답:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20,
  "profile_version": null
}
```

추천 응답에는 계산에 사용한 `profile_version`이 들어갑니다.
목록 카드에는 `id`, `title`, `source_code`, `source_name`, `posted_date`, `original_url`,
`category`, `summary_lines`, `deadline_date`, `deadline_at`, `d_day`, `deadline_label`,
`is_closed`, `is_bookmarked`, `needs_review`, `recommendation`이 있습니다.

점수에는 `score`, `grade`, `reasons`, `breakdown`, `policy_version`이 포함됩니다.
이유는 실제 기여 항목에서 최대 3개를 생성합니다.
점수는 확률이 아니며 신청 자격을 학교가 인증했다는 의미도 아닙니다.

## 5. 상세·분석·혜택

상세는 카드 필드에 `body_text`, `attachments`, `content_hash`, `image_only`, `analysis`, `fetched_at`을 추가합니다.
`fetched_at`은 최신 수집 확인 시각입니다. 원문 게시일인 `posted_date`와 구분합니다.
`body_text`는 HTML 실행용 문자열이 아닌 텍스트입니다. React에서 `dangerouslySetInnerHTML`로 렌더링하지 않습니다.

`analysis`에는 다음이 있습니다.

| 필드 | 의미 |
| --- | --- |
| `provider` | 분석 제공 방식: `rules`, `openai`, `rules_fallback`, `manual` |
| `status` | 검수·분석 상태: `needs_review`, `analyzed`, `failed`, `reviewed` |
| `data` | `AnalysisData` 전체 구조 |
| `warnings` | 원문 확인·모호한 일정·미검수 제도 등 경고 코드 |
| `analyzed_at` | 분석 완료 시각, Unix 초 |

`data.summary_lines`는 정확히 세 줄, 대상 / 활동 / 신청·행사 일정입니다.
`target_*`은 근거가 확인된 경우에만 추천의 강제 자격 필터에 쓰입니다.
본문이 이미지/첨부 위주인 경우 그 안의 조건을 읽었다고 가정하지 않습니다.
AI 응답의 confidence는 교정된 정확도 지표가 아닙니다.

상금은 `prize.status`로 구분합니다.
`present`는 있음, `none`은 없음이 명시됨, `not_stated`는 확인 불가/미기재입니다.
설명이 없으면 금액을 0원으로 표시하지 않습니다.
`mileages`는 `system`, `points_text`, `condition`, `evidence`를 갖는 배열입니다.
서로 다른 제도의 점수를 더하지 않습니다. 모호한 제도명은 자동 구성하지 않고 검수 대상으로 남깁니다.

## 6. 찜·월간 캘린더

모두 인증 필요:

| HTTP 방식 / 경로 | 결과 |
| --- | --- |
| `GET /api/bookmarks?page=1&page_size=20` | 본인의 찜 공지, 최근 찜 순 |
| `POST /api/bookmarks/{notice_id}` | 204, 이미 있으면 그대로 유지 |
| `DELETE /api/bookmarks/{notice_id}` | 204, 없어도 동일 완료 |
| `GET /api/calendar?month=YYYY-MM` | 본인 찜 일정의 월간 겹침 조회 |

`month`는 필수입니다. 연도 범위는 1900~2200입니다.
없는 공지를 찜하면 404이고, 다른 사람의 사용자 ID를 지정하는 API는 없습니다.

캘린더 응답의 최상위는 `month`, `timezone`, `end_inclusive`, `events`, `undated`입니다.
`end_inclusive=true`로 **종료일을 포함**합니다.

각 일정 항목의 필드:
`id`, `notice_id`, `title`, `kind`, `label`,
`start_date`, `end_date`, `start_time`, `end_time`,
`display_start`, `display_end`, `is_partial`,
`continues_before_month`, `continues_after_month`.

`kind=application`은 신청 일정, `kind=event`는 실제 행사입니다.
원래 기간이 9월 29일~10월 3일이면 9월과 10월 조회 모두에 포함합니다.
`display_*`만 해당 월 경계로 자르며 원래 `start_date/end_date`는 보존합니다.
달력 라이브러리가 종료일을 포함하지 않는 방식이라면 **프론트 표시 변환에서만** 종료일에 하루를 더합니다.

한쪽 날짜만 아는 일정은 알려진 날에 점으로 표시하고 `is_partial=true`입니다.
모르는 시작/종료 날짜는 응답에서 계속 null입니다.
양쪽 날짜를 모르면 `undated`로 안내합니다.
신청 마감 이후에도 찜과 실제 행사 일정은 삭제하지 않습니다.

## 7. 관리자 API

일반 사용자는 403입니다. 관리자 권한은 서버 CLI로만 부여합니다.

| HTTP 방식 / 경로 | 기능 |
| --- | --- |
| `POST /api/admin/crawl-jobs` | 수집 작업 접수, 202 |
| `GET /api/admin/crawl-jobs?limit=20` | 최근 작업 |
| `GET /api/admin/crawl-jobs/{job_id}` | 단일 작업 상태 |
| `GET /api/admin/crawl-runs?limit=20` | 출처별 실행·오류 |
| `PUT /api/admin/notices/{notice_id}/analysis` | 구조화 결과 수동 검수 |

수집 본문:

```json
{
  "sources": ["SCNU_MAIN","SCNU_SW","SCNU_AI"],
  "pages": 1,
  "max_notices": 5,
  "max_age_days": 60
}
```

최대 3페이지, 출처별 최대 50건, 기간 최대 365일입니다.
202는 수집 완료가 아닙니다. 반환된 job ID로 `queued/running/completed/partial/failed` 상태를 확인합니다.
worker가 실행되어야 대기 작업을 처리합니다.
기본 수집 비활성화 시 403 `CRAWLING_DISABLED`,
기존 대기/실행 작업이 확인되면 409 `CRAWL_ALREADY_PENDING`입니다.
worker lease가 실제 동시 수집을 제한합니다.

수동 검수 본문은 `expected_content_hash`와 `analysis`입니다.
상세에서 받은 최신 content hash 및 전체 AnalysisData를 제출합니다.
원문 변경이 확인되면 409입니다. 수동 검수 값은 관리자의 근거 확인 책임입니다.

## 8. 오류 계약과 프론트 처리

애플리케이션 오류 예시:

```json
{
  "error": {
    "code": "PROFILE_INCOMPLETE",
    "message": "학적과 관심 분야·활동을 먼저 등록해주세요.",
    "details": [],
    "request_id": "<request uuid>"
  }
}
```

| 상태 | 화면 처리 |
| --- | --- |
| 400 | 토큰·요청 확인; 확인 링크는 새로 발급 |
| 401 | 인증 상태 제거 후 로그인 |
| 403 | 관리자 권한 또는 수집 설정 확인 |
| 404 | 없어진 공지·잘못된 경로 안내 |
| 409 | 프로필/원문 재조회, 진행 중 작업 상태 조회 |
| 413 | 입력 크기를 줄임 |
| 422 | 필드와 enum 오류 표시 |
| 429 | `Retry-After`에 맞춰 재시도 |
| 500 | 일반 오류 안내, request_id로 서버 확인 |

프록시나 TrustedHost/CORS에서 발생한 거부 응답은 JSON 계약이 아닐 수 있습니다.
프론트는 HTTP 상태·Content-Type을 확인한 후 JSON을 읽고, 파싱 실패도 처리해야 합니다.
비밀번호·로그인 토큰을 오류 화면이나 수집 로그에 다시 출력하지 않습니다.

## 9. 프론트 연결 검수 순서

가입 → 로그인 → me → 관심사 조회 → 프로필 저장 → 추천/신규 →
상세 → 찜 → 캘린더 → 프로필 수정 후 추천 재조회 → 로그아웃 순서로 검수합니다.

신규 계정, 미완성 프로필, 빈 수집 목록, 일정 미정, 만료된 토큰, 429, 수집 실패의 화면 상태도 구현합니다.
이 문서의 경로와 필드 변경은 프론트와 합의한 뒤 코드·테스트·OpenAPI·문서를 함께 수정합니다.
