# 저장소 관리자 설정

이 문서는 설정 방법입니다. 아직 원격 저장소 생성, 팀원 초대, 브랜치 보호, CI 설정은 수행되지 않았습니다.

## GitHub에 만들기

기본 제안 이름은 `scnu-pick`입니다. 소유자와 공개/비공개는 저장소 생성 시 사용자가 선택합니다.
초기 파일을 가져올 예정이므로 GitHub에서 README·.gitignore·라이선스를 자동 생성하지 않은 빈 저장소를 만듭니다.

## 초기 브랜치

압축본의 `scnu-pick.bundle`에는 초기 커밋과 네 브랜치가 들어 있습니다. ZIP을 웹으로 업로드하기만 하면 브랜치는 생성되지 않습니다. 압축본의 `START_HERE.md` 절차로 복원·push하거나, 빈 GitHub 저장소 URL을 전달해 파일·브랜치를 초기화합니다.

## 팀원과 권한

팀원 GitHub 아이디를 확인한 뒤 저장소 접근 권한을 부여합니다. 초기 파일에는 실명과 GitHub 아이디를 임의로 연결하지 않습니다. 초대·리뷰 요청은 실제 팀원이 정해진 뒤 합니다.

## 브랜치 보호 제안

저장소 설정에서 `main`, `dev`에 PR 기반 병합을 요구하고 강제 push·삭제를 제한하는 규칙을 검토합니다. 지원 여부는 저장소 공개 범위와 GitHub 플랜 등에 따라 달라질 수 있습니다. 지원되지 않아도 팀 규칙은 유지하되 기술적으로 강제되는 것으로 설명하지 않습니다.

CI가 없으므로 존재하지 않는 상태 검사를 필수로 지정하지 않습니다. 실제 워크플로를 추가하고 성공 실행을 확인한 뒤 연결합니다. 최종 리뷰어·필수 승인 수·병합 방식은 팀에서 정합니다.

## 참고

- [GitHub에 기존 로컬 저장소 추가](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)
- [PR 템플릿](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository)
- [보호 브랜치](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
