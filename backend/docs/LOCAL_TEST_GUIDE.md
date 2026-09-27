# 로컬 실행과 인증 시험

Python 3.11 이상에서 `backend` 폴더의 `python start.py`를 실행합니다. Windows에서는 `START.cmd`를 사용할 수 있습니다. 상태는 `http://localhost:3104/health`, API 시험 화면은 `http://localhost:3104/docs`입니다.

## 가입과 로그인

`POST /api/auth/register`에 다음 JSON을 입력합니다.

```json
{"username":"student01","password":"long-passphrase-123"}
```

201이면 바로 `POST /api/auth/login`에 같은 JSON을 보내고 응답의 `access_token`을 Swagger Authorize에 입력합니다. 아이디는 영문 소문자로 시작하는 영문 소문자·숫자·밑줄 3~32자입니다. 중복 아이디는 409입니다.

`GET /api/auth/me`로 계정을 확인한 뒤 `PUT /api/profile`에 학과·학년·학적·관심사를 저장합니다. 공지 목록은 기본적으로 비어 있습니다.

## 비밀번호 변경

로그인한 상태에서 `POST /api/auth/change-password`에 다음 JSON을 보냅니다.

```json
{"current_password":"long-passphrase-123","new_password":"another-passphrase-123"}
```

성공하면 모든 세션이 폐기됩니다. 새 비밀번호로 다시 로그인합니다. 분실한 비밀번호의 셀프 복구는 MVP에 포함하지 않습니다. 운영상 신원 확인 절차가 정해질 때까지 새 계정을 사용합니다.

## 관리자 권한

서버 운영자가 이미 가입한 아이디에 권한을 부여합니다.

```powershell
python -m app.cli grant-admin --username student01
python -m app.cli grant-admin --username student01 --revoke
```

## 자동 검증

```powershell
python -m pytest -q
python scripts/verify_backend.py
```

HTTP 검증 도구는 임시 DB와 로컬 API 프로세스를 사용합니다. 실제 학교 사이트와 외부 AI는 호출하지 않습니다.
