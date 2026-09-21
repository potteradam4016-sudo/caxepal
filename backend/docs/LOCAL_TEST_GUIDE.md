# 처음 실행하고 API를 확인하는 순서

이 문서는 Windows 기준입니다. 프론트 화면 대신 `/docs`에서 API를 시험합니다.
명령을 실행하는 위치는 항상 **팀 저장소/backend**입니다.

## 1. 설치와 실행

터미널에서 다음을 확인합니다.

```powershell
python --version
```

3.11 이상이어야 합니다. 검증 환경은 3.13.5입니다.
Python이 인식되지 않으면 Python 설치와 PATH를 확인하거나 Python Launcher가 있는 PC에서 `py -3 --version`을 사용합니다.

`backend` 폴더에서:

```powershell
python start.py
```

또는 `START.cmd`를 두 번 클릭합니다.
가상환경 활성화 명령은 필요하지 않습니다. 스크립트가 가상환경의 Python을 직접 사용합니다.
실행 도구는 설정 → 가상환경 → 패키지 → 설정 검증 → DB 마이그레이션의 다섯 단계를 표시합니다.
실행 주소가 출력되었다는 사실만으로 성공한 것은 아닙니다. 반드시 `/health` 응답까지 확인하세요.

```text
API 시험: http://localhost:3104/docs
상태 확인: http://localhost:3104/health
```

설정·설치만 하고 실행하지 않으려면:

```powershell
python start.py --dev --setup-only
```

`--dev`는 pytest도 설치합니다. 패키지가 이미 준비되어 있고 재설치를 피하려면 `python start.py --no-install`을 사용합니다.
기존 `.env`에 빈 SECRET_KEY가 있으면 자동으로 덮어쓰지 않으므로 직접 설정해야 합니다.
개인 비밀키 생성 명령:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

출력값을 `.env`의 `SECRET_KEY=` 뒤에 넣고 공개하지 않습니다.

## 2. 정상 상태 확인

브라우저에서 `http://localhost:3104/health`를 엽니다.

```json
{"status":"ok","database":"ok","frontend_included":false}
```

`http://localhost:3104/`의 JSON 응답도 정상입니다.
로그인 화면이 안 뜨는 것은 프론트엔드를 넣지 않았기 때문입니다.

이제 `http://localhost:3104/docs`로 이동합니다.
항목을 펼치고 **Try it out → 본문 입력 → Execute** 순서로 시험합니다.

## 3. 가입

`POST /api/auth/register`에 다음 형태의 본문을 입력합니다.
아래 비밀번호는 문서 예제이므로 실제 계정에는 자신만의 비밀번호를 사용합니다.

```json
{
  "email": "student@example.com",
  "password": "local-test-only-change-this"
}
```

정상 응답은 202입니다. 비밀번호는 12~128자입니다.
학교 이메일로 제한하지 않습니다. 이메일 소유 확인은 학생 신분 인증이 아닙니다.

중복 가입도 같은 접수 문구를 반환합니다.
가입했다고 바로 로그인되지 않으며 먼저 이메일 확인이 필요합니다.

## 4. 개발 메일에서 확인 토큰 읽기

기본 `MAIL_BACKEND=file`에서는 실제 메일함에 메일이 오지 않습니다.
API가 실행 중인 터미널은 그대로 두고 **두 번째 터미널**을 backend 폴더에서 엽니다.

```powershell
.venv\Scripts\python.exe -m app.cli mail
```

최근 개발 메일의 내용과 토큰이 표시됩니다.
`.eml`은 `backend/data/mail/`에 저장되며 Git 업로드 대상이 아닙니다.
다른 사람과 화면·터미널 로그를 공유할 때 토큰을 지웁니다.

`POST /api/auth/verify-email`의 본문:

```json
{"token":"개발 메일에서 복사한 실제 토큰"}
```

200이면 확인 완료입니다. 같은 토큰을 다시 사용하면 400입니다.
메일의 `/verify-email#token=...` 링크는 미래 프론트 화면용입니다.
아직 프론트가 없으므로 그 링크 대신 Swagger에서 토큰을 제출합니다.

## 5. 로그인과 Authorize

`POST /api/auth/login`에 가입한 이메일과 비밀번호를 제출합니다.
응답의 `access_token` 값을 복사합니다.

Swagger 상단 **Authorize**를 열고 토큰 값만 붙여넣습니다.
HTTP Bearer 입력란에는 보통 `Bearer ` 문구를 중복 입력하지 않습니다.
직접 HTTP 요청을 보낼 때는 헤더가 다음 형태입니다.

```http
Authorization: Bearer 실제로그인토큰
```

`GET /api/auth/me`가 본인 계정을 반환하면 인증 연결이 된 것입니다.
세션은 기본 24시간이며 자동 갱신 API는 없습니다.
만료·로그아웃 후에는 다시 로그인합니다.

## 6. 학적·관심사 저장

먼저 `GET /api/interests`로 현재 선택지를 조회합니다.
`field`와 `activity`를 구분하며 각각 하나 이상 골라야 온보딩 완료입니다.

`PUT /api/profile`:

```json
{
  "department": "컴퓨터공학과",
  "grade": 2,
  "academic_status": "enrolled",
  "interest_ids": ["ai_sw", "hackathon"],
  "expected_version": 0
}
```

신규 사용자 버전은 0이며 저장 후 증가합니다.
다시 수정할 때는 `GET /api/profile`의 최신 `version`을 `expected_version`으로 보내거나,
버전 조건을 사용하지 않을 경우 필드 자체를 생략합니다.
충돌 방지를 위해 실제 프론트에서는 최신 버전을 보내는 방식이 권장됩니다.

학적 값은 `enrolled`(재학), `on_leave`(휴학), `graduating`(졸업예정), `graduated`(졸업)입니다.
취소 버튼은 PUT을 호출하지 않아야 합니다.

## 7. 공지·추천·찜·캘린더

`GET /api/notices`는 처음에는 아래처럼 비어 있습니다.

```json
{"items":[],"total":0,"page":1,"page_size":20,"profile_version":null}
```

이것은 수집 전 정상 상태입니다. 별도 테스트 공지를 서비스 DB에 자동 삽입하지 않습니다.
실제 수집은 `CRAWLER_AND_AI.md`를 따라 허가 조건 확인 후 실행합니다.

데이터가 들어오면 실제 반환된 공지 `id`를 사용해 아래 흐름을 확인합니다.

```text
GET    /api/notices/new?days=7
GET    /api/notices/recommended
GET    /api/notices/{실제ID}
POST   /api/bookmarks/{실제ID}
GET    /api/bookmarks
GET    /api/calendar?month=2026-09
DELETE /api/bookmarks/{실제ID}
```

캘린더의 월은 현재 날짜를 추정하지 말고 해당 공지 일정이 있는 월로 바꿉니다.
공지에 날짜가 없으면 `events`가 아니라 `undated`에 나타날 수 있습니다.
신청이 마감되어도 찜한 공지의 실제 행사 일정은 유지됩니다.

## 8. 비밀번호 재설정

`POST /api/auth/forgot-password`에 이메일을 제출하고 `app.cli mail`로 새 reset 토큰을 확인합니다.
`POST /api/auth/reset-password`에 토큰과 새 비밀번호를 제출합니다.
이때 기존 로그인 세션은 모두 폐기됩니다. Swagger의 기존 토큰도 더 이상 유효하지 않습니다.

## 9. 관리자 권한

기본 관리자 계정·비밀번호는 없습니다.
먼저 가입과 이메일 확인을 끝낸 본인 계정을 대상으로, 서버에 접근할 수 있는 관리자가 실행합니다.

```powershell
.venv\Scripts\python.exe -m app.cli grant-admin --email 실제이메일주소
```

회수:

```powershell
.venv\Scripts\python.exe -m app.cli grant-admin --email 실제이메일주소 --revoke
```

일반 사용자가 API 본문으로 관리자 권한을 지정할 수 없습니다.
관리자도 `CRAWL_ENABLED=false`이면 수집을 시작할 수 없습니다.

## 10. 자동 검증

서버를 먼저 종료한 뒤 테스트 패키지를 준비합니다.

```powershell
.\START.cmd --dev --setup-only
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts/verify_backend.py
```

두 번째 명령은 자동 테스트, 세 번째 명령은 임시 서버의 실제 HTTP 통합 검증입니다.
실제 HTTP 검증은 기본적으로 비어 있는 임시 포트를 선택하므로 개발 서버의 3104를 사용하지 않습니다.
3104 자체를 시험할 때만, 그 포트의 기존 서버를 종료한 후 `--port 3104`를 붙입니다.

자동 검증의 합성 공지는 임시 폴더에서만 사용하며 실제 서비스 목록에는 들어가지 않습니다.
검증이 끝나면 임시 계정·DB·메일을 삭제합니다. 실패 시에도 개발자의 기존 파일은 건드리지 않습니다.
성공 결과를 실제 학교 수집이나 실제 SMTP 배달의 성공으로 해석하지 않습니다.

## 11. 자주 만나는 오류

| 증상 | 확인할 것 |
| --- | --- |
| `python`을 찾지 못함 | Python 설치·PATH, `py -3` 사용 가능 여부 |
| 패키지 설치 실패 | 인터넷/PyPI 접근, Python 버전, 프록시 설정, 설치 로그 |
| `SECRET_KEY` 오류 | `.env`의 개인용 32자 이상 비밀키 |
| `Database not initialized` | 가상환경 Python으로 `-m app.cli init-db` 실행 |
| `Address already in use` | 이미 3104에서 서버가 실행 중인지 확인; 기존 프로세스를 먼저 정상 종료 |
| 401 | 토큰 누락·만료·로그아웃, Bearer 중복 입력 |
| 403 `EMAIL_NOT_VERIFIED` | 메일 확인 API 실행 여부 |
| 409 `PROFILE_INCOMPLETE` | 학적 및 분야/활동을 각각 선택했는지 확인 |
| 409 `PROFILE_CONFLICT` | 프로필 최신 버전을 다시 조회 |
| 422 | Swagger의 스키마·필수 값·enum 확인 |
| 429 | `Retry-After` 후 재시도; 무한 재요청하지 않음 |
| 공지 0건 | 수집 전인지, 작업 실패인지, 검색/기간/추천 조건이 과도한지 확인 |
| 수집 후에도 0건 | 관리자 작업 상태·robots·네트워크·HTML 선택자 확인 |
| 메일이 실제 수신되지 않음 | 기본은 파일 메일; SMTP 설정·배달 검증 필요 |

`.env`를 바꾸면 API와 worker를 함께 종료하고 재시작합니다.
학교 서버의 3104는 할당 포트이므로 임의로 바꾸기 전에 담당자와 확인합니다.


### 폴더를 옮겼거나 이전 버전의 가상환경이 남아 있는 경우

`backend/.venv`는 Python 실행 위치를 포함하는 설치 환경입니다.
폴더를 옮긴 뒤 실행되지 않으면 서버를 종료하고 **`.venv`만** 저장소 밖으로 옮긴 후 다시 실행합니다.
소스·`.env`·`data`는 삭제하지 않습니다. Python 공식 문서도 가상환경을 복사해서 이동하는 대신 대상 위치에서 재생성하도록 안내합니다.

Python 설치 자체가 없거나 패키지 다운로드가 차단된 경우에는 코드 수정만으로 해결되지 않습니다.
`py -3 --version`, `python --version`과 마지막 오류 줄을 확인하세요.
오류를 공유할 때는 비밀번호·토큰·DB 연결 문자열을 가리고, `.env` 파일 자체는 보내지 않습니다.
