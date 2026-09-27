# GitHub 업로드와 통합 안내

현재 저장소에는 React 프론트와 FastAPI 백엔드가 함께 구현돼 있습니다. ZIP 폴더 전체 교체가 아니라 Git 변경분을 검토해 반영합니다. 개인 `.env`·DB와 다른 팀원의 변경을 보존합니다.

## 작업 브랜치

저장소 루트에서 작업합니다. 미커밋 변경은 먼저 본인 브랜치에 보존합니다.

```sh
git fetch origin
git switch dev
git pull --ff-only origin dev
git switch -c feature/backend-task
```

브랜치 이름은 실제 작업에 맞게 정합니다. GitHub Download ZIP에는 `.git` 이력이 없으므로 협업에는 clone한 저장소를 사용합니다.

## 커밋 전 확인

```sh
git status --short
git diff
git add <검토한-파일-경로>
git diff --cached
git commit
git push -u origin HEAD
```

실제 키·토큰·개인정보·운영 DB·로그·가상환경·빌드 산출물을 올리지 않습니다. `.gitignore`는 이미 추적된 비밀값을 숨기지 못합니다. 노출된 키는 삭제만 하지 말고 폐기·재발급합니다.

API 변경에는 공유 계약과 OpenAPI, 실행 변경에는 README와 예제 환경 설정을 함께 갱신합니다. 프론트 담당자에게는 주소·허용 origin·계약을 공유하고 개인 `.env` 자체는 전달하지 않습니다.

## 검토와 배포

일반 PR은 base `dev`, 최종 통합 PR만 base `main`입니다. [팀 규칙](../../CONTRIBUTING.md)과 [PR 양식](../../.github/pull_request_template.md)을 사용합니다. 커밋 본문은 과거 `COMMIT_*.txt`를 그대로 쓰지 않고 이번 diff와 직접 확인한 결과로 작성합니다.

백엔드 CI 예시는 `backend-ci.yml.example`이며 실제 `.github/workflows/`에 설치된 자동 CI는 없습니다. 프론트·백엔드 검증을 통과한 뒤 [배포 확인 목록](../../docs/deployment-checklist.md)을 별도로 완료합니다. push·PR 병합은 운영 배포 완료를 의미하지 않습니다.
