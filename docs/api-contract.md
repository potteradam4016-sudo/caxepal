# 프론트와 백엔드 API 연동 계약

2026-09-26 기준 실제 백엔드 코드와 React가 사용하는 계약입니다.
전체 필드는 [백엔드 명세](../backend/docs/API_CONTRACT.md)와 [OpenAPI](../backend/docs/openapi.json)를 참고합니다.

## 연결과 인증

- 서버 기본 주소: `http://localhost:3104`. 업무 API 접두사: `/api`.
- 프론트 `VITE_API_BASE_URL`에는 서버 주소만 지정합니다.
- 로그인 결과의 opaque 토큰을 `Authorization: Bearer <token>`으로 보냅니다.
- 토큰과 만료 시각은 탭의 `sessionStorage`에 보관하고 비밀번호는 저장하지 않습니다.
- 새로고침은 `/auth/me`와 `/profile`로 상태를 복원합니다. 갱신 API는 없으며 만료 후 다시 로그인합니다.
- 쿠키 인증은 사용하지 않습니다. 다른 개발 포트는 백엔드 CORS 허용 목록에 명시합니다.

## 화면별 API

| 화면/동작 | Method / Path | 처리 |
| --- | --- | --- |
| 가입 | POST /api/auth/register | username, password. 201 후 로그인 호출 |
| 로그인 | POST /api/auth/login | 토큰·만료 시각·사용자 반환 |
| 현재 계정 | GET /api/auth/me | 사용자 ID, username, onboarding_complete |
| 로그아웃 | POST /api/auth/logout | 204, 현재 세션 폐기 |
| 프로필 | GET /api/profile, PUT /api/profile | 학적·관심사·version |
| 선택지 | GET /api/interests, GET /api/sources | 서버 ID와 표시 이름 |
| 추천 | GET /api/notices/recommended | 등록 완료 사용자, 서버 점수순 |
| 신규 | GET /api/notices/new | 전체 기간, 원문 등록일순 |
| 상세 | GET /api/notices/{notice_id} | 본문·혜택·모든 일정·첨부 |
| 찜 조회 | GET /api/bookmarks | 사용자별 페이지 목록 |
| 찜 추가/해제 | POST / DELETE /api/bookmarks/{notice_id} | 204 |
| 캘린더 | GET /api/calendar?month=YYYY-MM | 찜 공지의 월간 기간 일정과 미정 목록 |

## 입력·목록 규칙

- 아이디는 영문자로 시작하는 소문자·숫자·밑줄 3~32자이며 공백을 제거하고 소문자로 정규화합니다.
- 가입 비밀번호는 12~128자, 로그인은 1~128자입니다.
- 학과 2~80자, 학년 1~6, 학적 상태는 enrolled/on_leave/graduating/graduated입니다.
- 관심사 ID를 서버 사전에서 선택하며 분야와 활동이 각각 1개 이상이면 등록 완료입니다.
- PUT에는 `department, grade, academic_status, interest_ids, expected_version`을 보냅니다.
- 학적 단계에서는 빈 관심사 목록으로 저장하고, 최종 단계에서 전체 프로필을 저장합니다.
- `category=education&category=contest`처럼 반복 쿼리를 보내 OR 필터를 적용합니다. 단일 값 요청도 지원합니다.
- 출처 `source`, 검색 `q`(100자 이하), 마감 `closing_days=7`을 조합합니다.
- 응답의 `total/page/page_size`를 사용하며 UI는 20개씩 표시합니다.
- 카드의 3줄 요약과 상세 데이터를 분리합니다. 서버 점수·추천 이유·정렬을 재계산하지 않습니다.

## 오류·날짜

- 오류 형식은 `{error: {code, message, details, request_id}}`입니다.
- 204에는 JSON 본문이 없습니다. 422는 입력 오류, 429는 Retry-After와 함께 재시도를 안내합니다.
- 401 세션 만료 시 상태를 초기화합니다. 로그인 자격증명 오류는 폼에 표시합니다.
- 409 PROFILE_CONFLICT는 초안을 유지하고 명시적인 최신 정보 조회 후 편집합니다.
- 409 PROFILE_INCOMPLETE는 프로필을 다시 조회하고 온보딩 단계로 이동합니다.
- 날짜는 YYYY-MM-DD, 시간은 서울 현지 HH:MM:SS, 타임스탬프는 Unix 초입니다.
- 캘린더의 display_start~display_end 양 끝을 포함해 표시합니다. 월 경계와 미정 날짜를 보존합니다.
- 혜택의 없음과 미기재를 구분하며 points_text는 숫자로 강제 변환하지 않습니다.
