# SCNU PICK Frontend

순천대학교 교내 공지 추천 서비스의 React 프론트엔드입니다. `docs/design/pc/notice-prototype.html`을 기준으로 추천 공지, 신규 공지, 내 캘린더, 공지 상세, 내 정보 수정 화면을 구현합니다.

현재 데이터는 실제 API가 아닌 **데모용 목 데이터**입니다. 공지 원문, 혜택, 추천 점수와 일정은 운영 데이터나 실제 수집 결과로 간주하지 않습니다.

## 실행 환경

- Node.js 22
- npm 10
- Vite + React + TypeScript

## 설치와 실행

```sh
npm install
npm run dev
```

Vite가 안내하는 로컬 주소(기본값 `http://localhost:5173`)에서 확인합니다.

## 확인 명령

```sh
npm run lint
npm run typecheck
npm run test:run
npm run build
npm run preview
```

## 환경 변수

필요하면 `.env.example`을 `.env.local`로 복사합니다.

| 변수 | 설명 |
| --- | --- |
| `VITE_API_BASE_URL` | 실제 API가 합의된 뒤 사용할 기본 URL. 현재는 비워 둡니다. |
| `VITE_USE_MOCKS` | 현재 구현은 `true`인 목 데이터 모드만 지원합니다. |

브라우저에 포함되는 `VITE_` 변수에는 비밀키를 넣지 않습니다.

## 목 데이터 동작

- 공지 조회는 실제 네트워크 요청처럼 짧은 지연을 가진 비동기 서비스로 처리합니다.
- 찜과 프로필은 `localStorage`에 저장되어 새로고침 후에도 유지됩니다.
- 손상된 저장값은 기본 데모 값으로 안전하게 복구합니다.
- 개발 서버에서만 추천 화면의 로딩·빈 결과·오류 상태 전환 패널이 표시됩니다.
- 실제 API 경로, 인증, 페이지네이션, 추천 가중치와 마감 임박 기준은 아직 확정하지 않습니다.

## 이번 구현에서 제외한 범위

- 로그인, 회원가입, 메일 확인, 비밀번호 재설정
- 최초 학적·관심사 온보딩
- 실제 백엔드 API 및 인증 연동
- 실제 공지 수집과 원문 링크
