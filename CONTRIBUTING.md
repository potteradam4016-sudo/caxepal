# Git 작업 규칙

## 원칙

- 최초 저장소 초기화 이후 `main`, `dev`에 직접 기능 코드를 push하지 않습니다.
- 기능 브랜치는 최신 `dev`에서 만듭니다. 한 기능을 완료하면 새 기능은 새 브랜치에서 시작합니다.
- 프론트·백 모두 전체 저장소를 clone합니다. 담당 폴더를 중심으로 작업합니다.
- 공통 문서·API 계약을 바꿀 때는 영향받는 담당자와 먼저 맞춥니다.
- `.env`, API 키, 비밀번호, 실제 사용자 데이터는 커밋하지 않습니다. 필요한 변수명만 예제 파일로 공유합니다.
- 현재 규칙은 팀 운영 약속입니다. GitHub에서 강제하려면 별도로 브랜치 보호 설정을 적용해야 합니다.

## 처음 clone하기

아래 `저장소주소`를 실제 GitHub URL로 바꿉니다. PowerShell, Git Bash에서 사용할 수 있습니다.

```sh
git clone "저장소주소" scnu-pick
cd scnu-pick
git switch --track origin/dev
```

이미 로컬 `dev`가 있으면 마지막 명령 대신 `git switch dev`를 사용합니다.

## 첫 환경 구성 브랜치 사용

처음 제공되는 브랜치를 사용할 때는 최신 원격 정보를 받은 후 본인 브랜치만 선택합니다.

```sh
git fetch origin
git switch --track origin/feature/frontend-setup
```

백엔드는 마지막 줄의 브랜치 이름을 `origin/feature/backend-setup`으로 바꿉니다. 해당 로컬 브랜치가 이미 있으면 `git switch feature/backend-setup`처럼 전환만 합니다.

## 이후 새 기능 시작

작업 파일이 남아 있으면 먼저 본인 작업 브랜치에서 커밋하거나 임시 보관합니다. 아래는 프론트 로그인 기능 예시입니다.

```sh
git switch dev
git pull --ff-only origin dev
git switch -c feature/frontend-auth
```

백엔드 예시 이름은 `feature/backend-auth`입니다. `--ff-only`가 실패하면 강제로 덮어쓰지 말고 로컬 `dev`의 별도 커밋 여부를 확인합니다.

## 커밋과 push

```sh
git status
git diff
git add frontend/
git diff --cached
git commit -m "feat(frontend): 로그인 화면 구현"
git push -u origin HEAD
```

`git add frontend/`는 예시입니다. 백엔드는 `backend/`, 문서는 변경한 문서 경로를 지정합니다. 커밋 전에 포함 파일과 내용을 확인합니다.

| 접두어 | 용도 | 예시 |
| --- | --- | --- |
| `feat` | 기능 추가 | `feat(backend): 찜 조회 API 추가` |
| `fix` | 오류 수정 | `fix(frontend): 관심사 선택값 유지` |
| `docs` | 문서 | `docs: 캘린더 동작 설명 추가` |
| `chore` | 환경·설정 | `chore(backend): FastAPI 실행 환경 구성` |
| `refactor` | 동작을 유지한 구조 변경 | `refactor(backend): 날짜 추출 로직 분리` |

## PR과 검토

1. GitHub에서 PR을 만들고 **base: `dev` / compare: 본인 작업 브랜치**인지 확인합니다.
2. 변경 이유, 구현 내용, 실행·확인 방법과 남은 문제를 적습니다.
3. 프론트 화면은 디자인, 프론트 담당자가 디자인·기획을 확인하고, API 변경은 프론트·백 담당자가 함께 확인합니다. 백엔드·보안 담당자는 인증과 데이터 접근 범위도 확인합니다.
4. 검토가 끝나면 `dev`에 병합합니다. 저장소 관리 권한을 가진 팀원이 처리합니다.
5. `dev`에서 로그인부터 추천·찜·캘린더까지 연결된 동작을 검수합니다.
6. 최종 검수 후 **base: `main` / compare: `dev`** PR을 만듭니다. 초기 `main`은 실행 가능한 제품이 아니라 초기 파일 기준점입니다.

리뷰어 GitHub 계정과 최종 병합 담당자는 팀에서 등록합니다. 이 초기 파일에는 임의 계정을 지정하지 않았습니다.

## 내 브랜치에 최신 dev 반영

본인 브랜치에서 작업 내용을 커밋한 뒤 실행합니다.

```sh
git fetch origin
git merge origin/dev
```

충돌이 생기면 양쪽 변경을 확인해 수정하고 해당 파일을 `git add`한 뒤 `git commit`합니다. 해결이 어려우면 `git merge --abort`로 이번 병합을 취소하고 상대 담당자와 확인합니다. 공유 브랜치에 강제 push하지 않습니다.

## 기능 완료 후

```sh
git switch dev
git pull --ff-only origin dev
git switch -c feature/frontend-calendar
```

이미 병합한 브랜치에서 새 기능을 이어 만들지 않습니다. 새 브랜치 이름은 실제 작업에 맞게 바꿉니다.
