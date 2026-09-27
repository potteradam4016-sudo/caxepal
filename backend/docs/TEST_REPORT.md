# 현재 구현 검증 보고서

검증일: 2026-09-27. Windows 로컬의 기존 의존성으로 실행했습니다. 운영 배포 완료 보고서가 아닙니다.

## 실행 결과

| 검증 | 결과 |
| --- | --- |
| 프론트 `npm run test:run` | 2개 파일, 34개 통과 |
| 프론트 `npm run lint` | 통과 |
| 프론트 `npm run typecheck` | 통과 |
| 프론트 `npm run build` | TypeScript 검사와 Vite 프로덕션 빌드 통과 |
| 프론트 `npm run test:static-hosting` | 주최 측 정적 호스트 빌드의 해시 경로 직접 접속·새로고침·보호 경로 검증 통과 |
| 백엔드 pytest | 194개 통과, PostgreSQL 전용 6개 skip |
| OpenAPI 일치·문서 링크·안전한 환경 예시 | 백엔드 테스트에 포함, 문서 수정 후 전용 7개 재실행 통과 |
| 실제 로컬 HTTP 검증 | `test_runtime_smoke.py`에 포함, 임시 DB 사용 |
| 실제 API 브라우저 시험 | 기능·레이아웃 검사 성공 출력, browserErrors=[] |
| Python `pip check` | 의존성 충돌 없음 |

브라우저 시험은 가입·온보딩 초안 복원·추천·찜·상세·정보 수정·복수 필터·페이지 이동·캘린더·로그아웃·재로그인을 확인했습니다. 2560x1440 기준 비율 및 320/390px 등 화면의 가로 넘침·이미지·모달 경계도 검사했습니다. 임시 SQLite DB의 합성 공지이며 실제 학교 수집이나 운영 PostgreSQL 검증은 아닙니다.

추가로 주최 측 정적 호스팅용 `VITE_STATIC_HOSTING=true`, `VITE_API_BASE_URL=<루트 .env의 DEPLOY_ADDRESS>/api` 빌드를 만들고 로컬 정적 서버에서 `/#/login` 직접 방문·새로고침과 미로그인 추천 경로 리디렉션을 확인했습니다. 빌드에는 로컬 API 주소가 들어 있지 않습니다. 이 시험은 서버의 PostgreSQL/API 동작을 증명하지 않습니다.

## 재현 명령

프론트 폴더:

```sh
npm run lint
npm run typecheck
npm run test:run
npm run build
npm run test:e2e
```

백엔드 폴더:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -o addopts='' -q -p no:cacheprovider
```

이번 환경에서는 기존 Windows 임시 pytest 폴더의 접근 거부로 첫 실행이 실패했습니다. 새 시험 전용 `--basetemp=.pytest-tmp-audit-20260927`을 지정한 재실행에서 194개가 통과했습니다. `--basetemp`는 pytest가 내용을 지울 수 있으므로 실제 데이터 폴더를 지정하지 않습니다. Starlette의 AnyIO 별칭 사용에 대한 DeprecationWarning 1개가 있었고 앱 테스트 실패는 아닙니다.

브라우저 시험의 성공 출력 이후 테스트용 Vite 프로세스가 자동 종료되지 않아 해당 PID를 확인해 수동 종료했습니다. 이 환경에서는 종료 정리까지 자동 통과했다고 표현하지 않습니다. 실제 운영 서버와 worker는 시험용으로 실행하지 않았습니다.

문서 링크 검사를 루트·공유 docs·프론트 README·GitHub 양식까지 확장했습니다. `git diff --check`도 통과했습니다. 이번 시험용 프로세스와 임시 pytest 폴더는 정리했습니다. 추적 파일명 검사에서 개인 `.env`·DB·키 파일은 발견되지 않았지만 전체 Git 이력에 대한 비밀 탐지 감사는 별도입니다.

## 확인하지 못한 사항

- `TEST_DATABASE_URL` 미설정으로 PostgreSQL 전용 동시성 6개는 실행하지 않았습니다. 과거 통과 기록이 있더라도 이번 실행의 성공 수에 포함하지 않습니다.
- Docker가 없어 이미지 빌드·Compose healthcheck·운영 컨테이너는 실행하지 않았습니다.
- 운영 도메인·TLS·프록시 원본 IP·CORS·DB 최소 권한·백업 복원은 실제 배포 환경에서 확인해야 합니다.
- 학교 실수집과 OpenAI 유료 호출·모델 사용 가능 여부·분석 정확도 표본 검수는 이번 감사에서 수행하지 않았습니다.
- 온라인 취약점 DB를 사용하는 전체 의존성 보안 감사, 부하 시험, 침투 시험은 수행하지 않았습니다.
- `npm ci` 및 Python 의존성의 깨끗한 환경 재설치는 이번 로컬 검증과 별도로 CI/배포 환경에서 확인해야 합니다.

현재 문서 밖의 과거 JSON·ZIP 시험 산출물은 당시 기록입니다. 배포 가능 여부는 [배포 전 확인 목록](../../docs/deployment-checklist.md)의 미완료 항목까지 검수한 뒤 결정합니다.
