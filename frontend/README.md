# SCNU PICK Frontend

React 화면은 실제 FastAPI 서버에 연결됩니다. 목 응답은 테스트에서만 사용하며 데모 계정은 제공하지 않습니다.

## 실행

별도 터미널에서 백엔드를 먼저 실행합니다.

```powershell
cd backend
.\START.cmd
```

프론트는 다음 명령으로 실행합니다.

```sh
cd frontend
npm install
npm run dev
```

기본 프론트 주소는 http://localhost:5173, API 서버는 http://localhost:3104 입니다.
빈 DB에서는 회원가입으로 계정을 만들 수 있고 공지 목록은 비어 있는 것이 정상입니다.
실제 공지 수집은 백엔드 담당자의 허가·설정 절차를 따릅니다.

데스크톱 레이아웃은 2560×1440 구성을 기준으로 화면 크기에 맞춰 비례 조정합니다.
가로 680px 이하의 휴대폰 화면에서는 읽기와 터치를 위해 단일 열 배치로 전환합니다.

## 환경 변수

`.env.example`의 `VITE_API_BASE_URL`은 **/api를 제외한 서버 주소**입니다.
생략하면 `http://localhost:3104`를 사용합니다. 변경 후 개발 서버를 재시작합니다.
`VITE_` 변수에는 비밀키를 넣지 않습니다.

백엔드 `CORS_ORIGINS`에는 브라우저가 접속하는 프론트 주소를 정확히 등록합니다.
기본값은 `http://localhost:5173,http://127.0.0.1:5173`입니다.
5173 포트가 사용 중이라 다른 포트로 실행되면 해당 origin도 추가하고 백엔드를 재시작합니다.
프리뷰 서버 주소 역시 별도로 허용해야 합니다. 쿠키 인증은 사용하지 않습니다.

## 인증과 데이터

- 아이디: 영문자로 시작하는 소문자·숫자·밑줄 3~32자. 양쪽 공백 제거 및 소문자 정규화. 내부 공백은 허용하지 않습니다.
- 비밀번호: 가입 12~128자, 로그인 1~128자. 브라우저 저장소에 저장하지 않습니다.
- 가입 성공 후 로그인 API를 호출하여 학적 등록으로 이동합니다.
- 세션 토큰과 만료 시각만 `sessionStorage`에 저장합니다. 새로고침 시 서버에서 계정·프로필을 확인합니다.
- 관심사 초안은 사용자 ID별로 탭 내 보관합니다. 프로필·찜의 영구 데이터는 서버 DB가 기준입니다.
- 기존 목 저장소는 사용하거나 이관하지 않습니다.
- 401 세션 만료는 로그인으로 이동하고, 통신 장애는 재시도할 수 있습니다.
- 프로필 저장은 버전을 검사합니다. 충돌하면 입력을 유지하고 최신 정보 다시 불러오기를 제공합니다.
- 목록은 20개씩, 검색은 300ms 지연, 마감 임박은 7일 기준입니다.
- 출처 필터는 대표 공지의 작성자 6종 분류입니다. 공지 내용 카테고리 8종은 별도로 복수 선택합니다.
- 프로필 수정은 사이드바의 내 정보 수정 모달로 제공합니다. 추천 화면의 AI 분석 성공만·관심사 변경 버튼은 제거했습니다.
- 상세의 별도 본문·일정 영역은 제거했으며, 요약의 대상 / 내용 / 일정과 핵심 정보·원문 링크를 표시합니다.

## 운영 빌드

운영 API 주소를 **빌드 전에** 지정합니다. 아래 도메인은 예시입니다.

```powershell
cd frontend
npm ci
$env:VITE_API_BASE_URL="https://api.pick.example.org"
npm run build
```

정적 호스팅에 `dist/` 내용을 배포하고 `/login`, `/recommend` 등의 직접 접속도 `index.html`로 연결하는 SPA fallback을 설정합니다. 현재 앱은 도메인 루트 경로 배포를 전제로 합니다. `npm run dev`와 `npm run preview`를 운영 서버로 사용하지 않습니다.

SPA fallback을 설정할 수 없는 정적 호스트에서는 빌드 전에 `VITE_STATIC_HOSTING=true`를 지정합니다. 이때 화면 주소는 `/#/login`, `/#/recommend`처럼 해시 경로가 되어 직접 접속·새로고침이 가능합니다. 로컬 개발의 일반 경로는 유지됩니다.

현재 주최 측 호스트의 Nginx는 공개 `/api/`를 백엔드로 전달할 때 첫 `/api/`를 제거합니다. 이 환경에서만 `VITE_API_BASE_URL=<루트 .env의 DEPLOY_ADDRESS>/api`로 빌드하면 브라우저 요청 `/api/api/auth/login`이 백엔드 `/api/auth/login`에 도착합니다. 다른 프록시에는 일반 서버 주소를 사용합니다. 백엔드는 여전히 127.0.0.1:3104에서 실행해야 합니다.

`VITE_` 값은 빌드 결과에 포함되므로 서버 주소를 바꾸면 다시 빌드합니다. 파비콘 원본은 `public/icons/SCNU_PICK_icon.png`이며 `dist/icons`는 빌드 산출물입니다. 상세 설정은 [배포 안내](../backend/docs/DEPLOYMENT.md)를 참고합니다.

## 검증

```sh
npm run lint
npm run typecheck
npm run test:run
npm run build
npm run test:static-hosting
```

실제 API 브라우저 검증은 백엔드 가상환경 준비 후 실행합니다.

```sh
npx playwright install chromium
npm run test:e2e
```

검증 도구는 임시 SQLite DB와 합성 공지를 만들고 별도 API·Vite 프로세스를 실행합니다.
현재 사용자 DB나 개인 환경 설정을 사용하지 않습니다. 종료 시 프로세스와 임시 DB를 정리합니다.
스크린샷은 무시된 `test-results/`에 저장됩니다. 실제 학교 수집·운영 배포 검증은 아닙니다.
