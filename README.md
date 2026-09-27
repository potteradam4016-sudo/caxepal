# SCNU PICK

순천대학교 교내 공지를 모아 학적정보와 관심사에 맞게 추천하고, 찜한 공지의 신청·행사 일정을 월간 캘린더로 확인하는 웹 서비스입니다.

React 프론트와 FastAPI 백엔드가 실제 API로 연결되어 있습니다. 로그인·최초 등록·공지·찜·캘린더를 로컬에서 실행할 수 있습니다. 운영 배포와 GitHub 브랜치 보호 설정은 별도로 확인해야 합니다.

## 처음 참여한 팀원

1. 이 README와 [Git 작업 규칙](CONTRIBUTING.md)을 읽습니다.
2. [확정 기능](docs/product-scope.md)과 [담당별 작업](docs/team-tasks.md)을 확인합니다.
3. `dev`에서 본인 작업 브랜치를 만들고 작업합니다.
4. 작업이 끝나면 `dev`를 대상으로 PR을 열어 검토받습니다.

프론트 화면과 API 변경은 기획·디자인 및 백엔드 담당자와 함께 검토합니다. 현재 화면 동작은 React 구현과 갱신된 PC 구현 명세를 기준으로 합니다.

## 담당과 폴더

| 담당 | 작업 위치 | 책임 |
| --- | --- | --- |
| 기획/디자인 | `docs/`, Figma | 요구사항, 전체 디자인, 전달, 화면 검수 |
| 프론트엔드 담당 | `frontend/` | React 화면, 사용자 동작, API 연동 |
| 백엔드·정보보안 담당 | `backend/` | FastAPI, 인증, DB, 수집·분석·추천, 접근 권한 |
| 크롤링 허가 협조 2명 | `docs/crawling-permission.md` | 담당 부서 문의, 수집 허용 여부와 조건 정리 |

## 브랜치

| 브랜치 | 목적 | 합치는 곳 |
| --- | --- | --- |
| `main` | 최종 검수가 끝난 제출·배포 기준 | `dev` 검수 후 반영 |
| `dev` | 프론트·백 통합과 기능 검수 | `main` |
| `feature/frontend-setup` | 프론트 초기 환경 구성 | `dev` |
| `feature/backend-setup` | 백엔드 초기 환경 구성 | `dev` |
| `feature/frontend-기능명` | 프론트 기능별 작업 | `dev` |
| `feature/backend-기능명` | 백엔드 기능별 작업 | `dev` |
| `docs/작업명` | 기획·디자인 문서 작업 | `dev` |

통합 브랜치 이름은 **`dev`**로 통일합니다. `develop`을 별도로 만들지 않습니다.
초기 제공 브랜치는 `main`, `dev`, `feature/frontend-setup`, `feature/backend-setup` 네 개이며 최신 통합 상태는 `dev`에서 확인합니다.

**작업 흐름:** `dev`에서 작업 브랜치 생성 → 작업·커밋 → 작업 브랜치 push → PR의 base를 `dev`로 지정 → 검토·병합 → 통합 검수 → `dev`에서 `main`으로 PR.

## 확정 기술과 남은 결정

| 항목 | 상태 |
| --- | --- |
| 프론트엔드 | React |
| 백엔드 | FastAPI |
| 디자인 전달 | Figma |
| 회원가입·로그인 | 아이디 + 비밀번호, 서버 Bearer 세션 인증 |
| DB·배포·AI 제공자 | 미정, 담당자가 제안하고 팀에서 결정 |
| 프론트 도구 | Vite + React + TypeScript, npm |
| 실행 명령 | 백엔드: `backend/START.cmd`, 프론트: `cd frontend` 후 `npm run dev` |

## 로컬 실행

백엔드는 [실행 안내](backend/README.md)에 따라 시작합니다. API는 기본 `http://localhost:3104`입니다.
프론트는 `frontend`에서 `npm install`, `npm run dev`로 실행하며 기본 주소는 `http://localhost:5173`입니다.
브라우저에서 회원가입 후 학적·관심사를 등록합니다. 수집 전에는 공지 목록이 비어 있는 것이 정상입니다.
서버 주소 변경과 CORS 설정, 검증 명령은 [프론트 안내](frontend/README.md)를 참고합니다.

## 문서

- [기능과 화면 범위](docs/product-scope.md)
- [Git·커밋·PR 규칙](CONTRIBUTING.md)
- [역할별 첫 작업](docs/team-tasks.md)
- [디자인 전달 체크리스트](docs/design-handoff.md)
- [프론트·백 API 계약](docs/api-contract.md)
- [크롤링 허가 진행표](docs/crawling-permission.md)
- [저장소 관리자 설정](docs/repository-setup.md)

PR과 이슈 작성 양식을 포함합니다. 코드 구현을 시작한 뒤 실제 빌드·테스트 명령이 정해지면 CI를 추가합니다.
