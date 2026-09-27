# 아이디 인증 전환 검증 보고서

검증일: 2026-09-24. Windows / Python 3.12.14 / SQLite 임시 DB에서 전체 자동 테스트 **105개 통과**, 실제 로컬 서버 HTTP 요청 **12건 통과**를 확인했습니다. 프론트엔드는 린트·타입 검사·화면 테스트 16개·배포 빌드를 통과했습니다. 이전 버전의 수치는 현재 버전의 검증으로 간주하지 않습니다.

## 검증 범위

자동 테스트는 가입·중복 아이디·로그인·비밀번호 해시·세션 폐기·현재 비밀번호 확인·관리자 권한·마이그레이션·공지 기능을 확인합니다. `scripts/verify_backend.py`는 임시 DB에 실제 HTTP 서버를 띄워 가입부터 비밀번호 변경까지 확인합니다. 실제 학교 공지 수집, 외부 AI, PostgreSQL 운영 접속은 별도 검증 대상입니다.

## 실행 명령

```powershell
python -m pytest -q
python scripts/verify_backend.py --output docs/http-verification.json
```

`docs/openapi.json`은 현재 코드에서 다시 생성했고 자동 테스트에서 실행 중 명세와 일치하는지 확인했습니다. 기존 DB의 아이디 전환과 신규 DB 초기화도 자동 테스트에 포함됩니다. Windows `START.cmd`를 직접 두 번 클릭하는 과정, 실제 학교 수집, 외부 AI, PostgreSQL 운영 접속과 배포는 확인하지 않았습니다.
