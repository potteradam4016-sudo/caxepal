# 입력 자료와 설계 판단 기록

## 저장소 문서

제공 ZIP: `caxepal-main.zip`.

이번 구현은 `docs/product-scope.md`, `docs/api-contract.md`, `docs/crawling-permission.md`,
`docs/team-tasks.md`, `CONTRIBUTING.md`, 기존 `backend/README.md`를 확인한 뒤 작성했습니다.
이 문서들은 팀의 입력 자료이며 새 backend 폴더로 덮어쓰지 않았습니다.

과거 `SCNU_PICK_상세_서비스_기획서.docx`는 구조화·추천·수집 흐름의 보조 참고였습니다.
출처 수, 인증 공급자, 메인 메뉴 등 현재 저장소와 달라진 항목은 현재 저장소를 따랐습니다.
특히 4개 출처를 3개로, 독립 마감 메뉴를 필터로, 찜 일정을 월간 캘린더로 반영했습니다.

자체 이메일 인증, PostgreSQL 운영/SQLite 개발, 무작위 세션 토큰, 관심사/배점 값은
미정 기술 항목을 구현 가능하게 정한 제안입니다. 이미 팀이 승인했다고 표현하지 않았습니다.

## 공식 기술 자료

확인 기준일: 2026-09-21. 패키지 설치/서비스 계정의 실연결 검증과 문서 확인은 별개입니다.

- FastAPI 인증·비밀번호 해시 안내: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
  비밀번호 해시·인증 의존성 참고. 이 구현 자체는 해당 예제의 JWT 방식을 사용하지 않습니다.
- SQLAlchemy의 SQLite 지원 문서: https://docs.sqlalchemy.org/en/20/dialects/sqlite.html
  충돌 처리와 SQLite 동작 참고. 앱 모델 및 마이그레이션은 제공 코드로 검증했습니다.
- OpenAI 구조화 출력 안내: https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses
  Responses API의 text.format / strict JSON schema 구조 참고. 실 API 호출은 하지 못했습니다.
- PostgreSQL 행 수준 보안 정책: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
  테이블 소유자/BYPASSRLS가 RLS를 우회한다는 보안 경계를 문서에 반영했습니다.
- PostgreSQL 연결 암호화·인증서 검증: https://www.postgresql.org/docs/current/libpq-ssl.html
  실제 외부 DB 연결 시 암호화뿐 아니라 서버 신원 검증 설정을 확인해야 합니다.

- GitHub 공식 actions 저장소: https://github.com/actions/checkout / https://github.com/actions/setup-python
  예시 CI의 사용 인터페이스 참고. 실제 workflow 실행은 검증하지 않았습니다.

## 데이터 검증 한계

공개 웹 페이지와 파서 코드의 실제 실행 성공을 동일하게 취급하지 않습니다.
이번 재검수의 코드 실행 환경에서는 학교 도메인과 PyPI의 DNS 요청에 실패했습니다.
이전 문서의 웹 페이지 열람 기록을 이번 코드의 실수집 성공 근거로 사용하지 않습니다.
합성 HTML fixture를 실제 크롤링 결과라고 표시하지 않았습니다.
학교 원문에서 가져온 실제 공지 데이터·개인정보·비공개 허가 기록을 ZIP에 넣지 않았습니다.


## 이번 재검수의 추가 참고

- [Python 가상환경 공식 문서](https://docs.python.org/ko/3/library/venv.html): 가상환경을 저장소에 넣지 않고 대상 위치에서 재생성하는 실행 안내의 근거입니다.
- [FastAPI 테스트 공식 문서](https://fastapi.tiangolo.com/ko/tutorial/testing/): TestClient와 pytest의 기본 검증 방식입니다.
- 패키지 버전은 실제 검증 환경의 설치값을 기록했으며 최신 버전이라는 뜻은 아닙니다.
- 기술 문서 열람, 패키지의 온라인 설치, 실제 운영 연결은 서로 다른 검증입니다.
