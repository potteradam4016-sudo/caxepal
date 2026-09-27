# GitHub에 올리는 방법

## 1. 백엔드만 별도 저장소에 올리는 경우

```text
기존 팀 저장소/
├── frontend/          그대로 둠
├── docs/              그대로 둠
├── .github/           그대로 둠
├── README.md          그대로 둠
└── backend/           이번 ZIP의 backend 내용 적용
    ├── app/
    ├── migrations/
    ├── config/
    ├── tests/
    ├── docs/
    ├── .env.example
    ├── .gitignore
    ├── requirements.txt
    ├── start.py
    └── START.cmd
```

이번 통합 ZIP의 최상위에는 `frontend/`와 `backend/`가 나란히 있습니다. 팀 통합 저장소에서는 `backend/`를 기존 `backend/` 위치에 복사합니다. 백엔드 전용 저장소라면 `backend/` **안의 내용**을 그 저장소 최상위에 복사합니다. `backend/backend/`로 두 번 중첩하지 않습니다.
기존 저장소의 백엔드는 안내용 README뿐이었으므로 해당 README를 새 README로 바꾸고 나머지 파일을 추가하는 구조입니다.

이후 팀원이 backend 코드를 추가했다면 무조건 폴더를 덮어쓰지 말고 차이를 비교합니다.
개인 `.env`와 DB가 이미 있다면 보존하되, 이전 시제품 DB를 새 마이그레이션에 연결하지 않습니다.
이 구현의 초기 스키마는 이전 시제품 데이터 변환 프로그램이 아닙니다.

## 2. GitHub의 Download ZIP과 git clone은 다릅니다

GitHub에서 내려받은 ZIP에는 `.git` 이력이 없습니다. ZIP을 풀었다는 이유만으로 `git push`할 수 있는 것은 아닙니다.
협업은 팀 저장소를 `git clone`한 작업 폴더에서 진행합니다. 저장소 주소는 팀 GitHub의 실제 Clone 주소를 사용합니다.

이미 clone했다면 그 폴더를 계속 사용합니다. 아래 `<...>`는 실제 값으로 바꿉니다.

```bash
git clone <TEAM_REPOSITORY_URL>
cd <CLONED_REPOSITORY_FOLDER>
git fetch origin
git switch dev
git pull --ff-only origin dev
git switch -c feature/backend-implementation
```

로컬에는 dev가 없고 원격에만 있을 때는 `git switch --track origin/dev`를 사용합니다.
원격에도 dev가 없다면 팀의 초기 브랜치 운영부터 합의합니다. 임의로 main에 바로 올리지 않습니다.

위 브랜치에서 ZIP의 `backend/` 내용을 복사한 다음 실행·테스트합니다.
이번 ZIP은 전체 통합본이므로 예전 실행 수정 ZIP을 추가 적용하지 않습니다.

이미 `feature/backend-setup` 등 본인 브랜치가 있으면 그 브랜치를 사용해도 됩니다.
현재 작업 변경이 있는 상태에서 무리하게 `dev`로 전환하지 말고 먼저 본인 브랜치에서 작업을 보존합니다.
아래 예시는 통합 저장소의 `backend/`만 커밋하는 경우입니다. 실제 변경 파일과 메시지 본문이 맞는지 확인한 뒤 사용합니다.

```bash
git status --short
git add backend
git diff --cached --stat
git diff --cached --name-only
git diff --cached
git commit -F backend/docs/COMMIT_USERNAME_API.txt
git push -u origin HEAD
```

백엔드 전용 저장소의 최상위에 파일을 복사했다면 경로가 다릅니다.

```bash
git status --short
git add .
git diff --cached --name-only
git diff --cached
git commit -F docs/COMMIT_USERNAME_API.txt
git push -u origin HEAD
```

GitHub에서 **base: dev / compare: feature/backend-implementation**인 Pull Request를 만듭니다.
main에는 곧바로 병합하지 않습니다. 권한 있는 팀원이 검토하고 dev에서 통합 테스트한 후 진행합니다.

## 3. 올리는 파일 / 올리지 않는 파일

| Git에 올림 | 절대 올리지 않음 |
| --- | --- |
| requirements, Dockerfile, compose | `.venv/`, `__pycache__/`, 테스트 캐시 |
| Markdown 안내, OpenAPI 명세 | 실제 사용자 명단, 로그인 토큰, 개인 정보 로그 |

출력 명세 `docs/openapi.json`에는 비밀키·계정·수집한 실제 공지를 넣지 않았습니다.
합성 HTML fixture는 테스트 전용이라고 표시되어 있으며 서비스 데이터에 자동 등록되지 않습니다.

`backend/.gitignore`가 이를 무시하지만 이미 추적된 비밀 파일에는 소급 적용되지 않습니다.
실제로 노출된 키는 Git에서 지우기만 하지 말고 공급자에서 폐기·재발급해야 합니다.
커밋 전에 반드시 staged diff를 확인합니다.

## 4. 프론트 담당자에게 전달할 것

`backend/docs/API_CONTRACT.md`, `backend/docs/openapi.json`, 개발 API 주소,
허용할 프론트 origin을 공유합니다. `.env` 자체를 전달하지 않습니다.

프론트에서 필요한 기능은 직접 구현할 수 있도록 계약을 적었지만 UI는 포함하지 않았습니다.
학교 서버의 외부 도메인·프록시 경로는 서버 담당자와 확인합니다.
각자의 PC에서 `localhost`는 각자의 PC이므로 내 PC의 localhost 주소만 공유해서는 연결되지 않습니다.

## 5. 공유 파일 변경은 별도 검토

루트 `docs/api-contract.md` 및 허가 진행표는 원본 그대로 둡니다.
API 계약이 승인되면 링크 추가 또는 합의 내용을 해당 공통 문서에 반영하는 별도 변경을 제안합니다.

자동 CI의 예시는 `backend/docs/backend-ci.yml.example`입니다.
GitHub가 자동 실행하려면 팀이 검토해 저장소 루트의 `.github/workflows/backend-ci.yml`로 복사해야 합니다.
이번 ZIP이 CI를 이미 설치하거나 GitHub에 push한 것은 아닙니다.


## 6. 이번 통합본을 적용할 때

이 ZIP 안의 `backend/`와 저장소의 `backend/`가 같은 위치입니다.
`backend/backend/`로 두 번 중첩하지 않습니다. 전체 폴더를 삭제하는 방식으로 교체하지 않습니다.
기존 개인 환경설정·DB와 팀원의 변경은 보존하고, 변경된 소스와 문서를 비교해 반영합니다.

이번 ZIP에 없는 개인 데이터는 자동으로 지워지지 않습니다.
파일을 적용한 뒤 `git diff --cached --name-only`에서 실제 업로드 대상만 다시 확인합니다.
`START.cmd`는 Windows 개발 실행 도구이므로 업로드 대상입니다.
실행 중 생성되는 `.env`, `.venv/`, `data/`는 업로드하지 않습니다.

검증 로그에는 비밀값·임시 경로가 섞일 수 있습니다.
패키지에 포함된 비식별 검증 요약만 공유하고 개인 실행 로그 전체를 무심코 커밋하지 않습니다.
