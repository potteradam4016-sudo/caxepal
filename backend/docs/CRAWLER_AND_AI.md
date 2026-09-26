# 실제 공지 수집·분석 안내

## 1. 수집 대상과 허가

구현한 출처:

| 코드 | CMS 경로 | mi / bbsId |
| --- | --- | --- |
| SCNU_MAIN | `/SCNU/na/ntt/selectNttList.do` | 1131 / 1040 |
| SCNU_SW | `/scnusw/na/ntt/selectNttList.do` | 8889 / 4548 |
| SCNU_AI | `/scnuai/na/ntt/selectNttList.do` | 10241 / 5045 |

도메인은 `https://www.scnu.ac.kr`로 고정합니다.
Glocal, 외부 취업 사이트, 임의 URL 입력, 첨부파일 다운로드는 수집 기능에 없습니다.

첨부 저장소의 허가 진행표는 미확인입니다.
이전 대화에서 별도 승인을 받았더라도 해당 기록의 범위·주기·첨부 처리 조건을 팀 문서와 실제 설정에 맞춰야 합니다.
이 패키지가 새 허가를 받거나 기존 허가를 확인한 것은 아닙니다.

기본 `CRAWL_ENABLED=false`입니다.
허가 조건이 확인된 뒤에만 `.env`에서 true로 바꿉니다.
식별 가능한 User-Agent에 팀이 허용한 공개 연락 정보를 추가하고 개인 연락처는 공개 저장소에 노출하지 않습니다.

`ROBOTS_POLICY=strict`는 robots를 읽고 허용 경로·지연을 확인합니다.
robots 조회 실패·차단 시 수집을 중단합니다. 접속 오류를 우회하려고 무조건 정책을 바꾸지 않습니다.
`written_permission`은 robots 예외까지 명시한 실제 서면 허가가 있을 때만 쓰는 예외 설정입니다.

## 2. 가장 작은 실제 수집부터

API 준비가 완료된 backend 폴더에서, 허가 범위에 맞게 설정을 변경하고 API/worker를 재시작합니다.

```dotenv
CRAWL_ENABLED=true
AUTO_CRAWL=false
CRAWL_REQUEST_DELAY=1.0
ROBOTS_POLICY=strict
```

두 번째 터미널에서 한 출처부터 시험합니다.

```powershell
.venv\Scripts\python.exe -m app.cli crawl --source SCNU_MAIN --pages 1 --max-notices 3
```

기본 설명의 1초보다 허가된 간격이 길다면 `CRAWL_REQUEST_DELAY`를 더 크게 설정합니다.
CLI는 결과 상태·생성/변경/동일 건수·오류를 출력합니다.
이미 worker가 수집 lease를 잡았다면 작업은 대기로 남고 worker가 처리합니다.
허가와 작은 실수집 결과를 확인한 후:

```powershell
.venv\Scripts\python.exe -m app.cli crawl --source all --pages 1 --max-notices 5
```

`all`은 세 출처 모두를 뜻합니다. source별로 허가가 다르면 허용된 출처를 각각 지정합니다.
글로컬을 `--source`에 넣을 수 없습니다.

`GET /api/notices`, `/api/sources`, 관리자의 `/api/admin/crawl-jobs`, `/api/admin/crawl-runs`로 확인합니다.
성공했는지는 CLI 실행 여부가 아니라 작업 상태와 DB 결과로 판단합니다.
빈 결과·사이트 장애·규칙 미일치는 가짜 공지로 대체하지 않습니다.

## 3. worker·주기·중복·실패 처리

API로 수집을 접수하려면 관리자 인증으로 `POST /api/admin/crawl-jobs`를 호출합니다.
job ID가 반환되는 202는 '접수'입니다. 완료 상태를 별도로 조회합니다.

별도 worker 실행:

```powershell
.venv\Scripts\python.exe -m app.worker
```

`start.py`는 worker도 켜므로 추가로 실행할 필요가 없습니다.
배포에서는 API와 worker를 각각 운영합니다.
공유 DB lease로 한 번에 하나의 수집을 진행합니다.
중간에 죽은 작업은 lease 만료 후 재시도하며 최대 3회입니다.
행 단위 중복 제약과 content hash로 재실행 시 중복 공지를 막습니다.

자동 수집은 기본 꺼져 있습니다.
세 출처 전체에 대해 주기 수집 허가가 확인된 경우에만 `AUTO_CRAWL=true`를 사용합니다.
기본 제안은 10800초(3시간), 최소 설정은 3600초입니다.
일부 출처만 허가된 상태에서 전체 자동 수집을 켜지 않습니다.
출처별 `sources.enabled` 운영값도 확인해야 하며 초기 reference seed는 세 출처 모두 true를 기록합니다.
**source의 enabled=true 자체는 수집 허가나 실제 자동 실행을 뜻하지 않습니다.**

기본 요청은 순차적이며 페이지/공지 수에 상한이 있습니다.
최근 60일 범위와 최대 3페이지를 제안값으로 사용하며 고정 공지는 별도로 다룹니다.
재수집할 때 목록만 보고 본문이 같다고 가정하지 않고 제한된 대상의 상세를 다시 확인합니다.
원문 제목·본문·첨부 메타데이터·게시일·URL hash가 같으면 AI 분석을 재사용합니다.
사이트가 실패해도 기존 공지와 찜을 삭제하지 않습니다.

## 4. 현재 실제 수집 검증 범위

2026-09-24 로컬 검증에서 `ROBOTS_POLICY=strict`로 학교 robots 규칙을 확인한 후, 격리된 임시 DB에 대표·SW·AI 출처 공지를 각각 1건씩 적재했습니다. 이어 현재 로컬 DB에도 각 출처 3건씩 총 9건을 적재했고 세 작업 모두 `completed`, 오류 0건이었습니다. `GET /api/notices/new`와 프론트 개발 서버의 `/api` 프록시에서 9건을 확인했습니다. 이 검증은 해당 시점의 첫 페이지와 소량의 상세에 한정됩니다. 학교의 별도 수집 허가 범위·주기는 팀 기록으로 확인해야 합니다.

`frontend/src/data/mockData.ts`는 화면 테스트용이며 수집 결과의 저장소가 아닙니다. 실제 공지는 백엔드 DB에 저장됩니다. 새로 압축을 푼 폴더에서는 기본 설정 두 값이 `false`이므로, `backend/.env`를 설정한 뒤 백엔드를 재시작해야 자동 수집이 시작됩니다.

`tests/fixtures`는 합성 HTML이며 학교에서 받은 실제 HTML이라고 표시하지 않았습니다.
CMS 선택자 구현과 HTTP/robots/재시도/중복/변경/실패 보존 흐름을 합성 응답으로 시험했습니다.
실제 검증에서는 세 출처의 첫 페이지와 각 1~3건의 상세를 읽을 수 있었습니다. 사이트 구조가 바뀌면 허용된 범위에서 HTML 선택자를 다시 검수해야 합니다.

대표적인 오류:
`SOURCE_NETWORK_ERROR`(네트워크),
`ROBOTS_DISALLOWED`(robots 금지),
`ROBOTS_HTTP_*`(robots 응답 실패),
`LIST_SELECTOR_MISMATCH`(목록 구조 변경),
`DETAIL_BODY_SELECTOR_MISMATCH`(본문 구조 변경),
`PAGINATION_DID_NOT_ADVANCE`(페이지 이동 실패).

오류를 만났을 때 없는 데이터를 만들어 성공으로 처리하지 않습니다.
`parser.py`를 수정하면 실제 허용된 HTML에서 개인/불필요 내용을 제거한 fixture를 추가하고 회귀 테스트합니다.

## 5. 규칙 분석과 AI 분석

기본값:

```dotenv
AI_PROVIDER=rules
```

규칙 모드는 문자열·날짜 패턴을 쓰며 결과는 `provider=rules`, `status=needs_review`입니다.
AI 서비스가 없을 때도 API·DB·날짜·추천 파이프라인을 시험할 수 있도록 한 것이며 AI 결과라고 표시하지 않습니다.

팀에서 외부 AI 사용을 승인했다면:

```dotenv
AI_PROVIDER=openai
OPENAI_API_KEY=<서버에서만 보관하는 실제 키>
OPENAI_MODEL=gpt-5.6-sol
```

실제로 계정에서 사용할 수 있고 구조화 출력을 지원하는 모델 ID를 설정합니다.
OpenAI Responses API의 strict JSON Schema 형식으로 카테고리·관심사·대상·신청 방법·상금 근거·요약을 추출합니다. 요청에는 `store=false`를 설정합니다.
표는 수집 시 행·열 순서를 텍스트로 보존합니다. 모집인원은 지원 자격과 별도 보관하고 추천의 강제 자격 필터에 쓰지 않습니다.
일정·마일리지는 원문에 명시된 근거를 규칙으로 추출하며, 상금도 명시된 금액이 있는 표에서는 규칙 결과를 사용합니다. Pydantic·근거 문자열·날짜·시간 검사를 거칩니다.
공지 원문을 실행 지시로 취급하지 않고 도구·링크 접근 기능도 주지 않습니다.
OpenAI의 데이터 처리·로그·보존 정책, 외부 전송 승인과 비용 한도는 팀이 확인해야 합니다.

일시적인 네트워크·요청 제한·서버·응답 오류만 최대 두 번 시도합니다. 잘못된 요청·키·모델 오류는 재시도하지 않습니다.
실패하면 `provider=rules_fallback`, `status=failed`와 `AI_EXTRACTION_FAILED` 및 원인 코드(`AI_REQUEST_ERROR`, `AI_AUTH_ERROR`, `AI_MODEL_ERROR`, `AI_RATE_LIMITED`, `AI_SERVER_ERROR`, `AI_NETWORK_CONNECT`, `AI_NETWORK_TIMEOUT`, `AI_NETWORK_PROTOCOL`, `AI_NETWORK_ERROR`, `AI_RESPONSE_INVALID`, `AI_RESPONSE_SCHEMA_INVALID`, `AI_RESPONSE_INCOMPLETE`, `AI_RESPONSE_REFUSED`, `AI_GROUNDING_FAILED`)를 기록합니다. 키와 원문은 오류 코드에 포함하지 않습니다.
HTTP 실패에는 `AI_HTTP_503`처럼 실제 상태 코드와, OpenAI 오류 코드가 허용된 값일 때만 `AI_REMOTE_RATE_LIMIT_EXCEEDED` 같은 코드를 추가합니다. 응답의 자유 형식 오류 메시지는 저장하지 않습니다. `reanalyze --notice-id N` 또는 `--limit 1`은 공지 ID·분석 상태·저장 여부·안전한 오류 코드를 터미널에 출력합니다.
규칙 분석도 원문에 명시된 신청 방법을 추출합니다.
규칙 결과를 조용히 AI 성공으로 바꾸지 않습니다.
수집을 한 번 수행할 때마다 신규/변경 건에 AI 비용이 발생할 수 있습니다.
사용자별 추천 조회 때 다시 AI를 호출하지 않습니다.

전체 본문 중 최대 24,000자를 AI에 전달하는 구현이므로 긴 공지의 뒷부분이 빠질 수 있습니다.
이미지·첨부파일의 정보는 분석하지 않습니다. 실제 정확도는 원문 표본 대조로 검증해야 합니다.

## 6. 보수적으로 남기는 미정 값

명시적 전체 연도가 없는 `9.30`, 축약 범위 `2026.09.01~09.10`,
혼합된 신청/행사 문장은 잘못된 마감 계산을 피하기 위해 미정 또는 검수 경고로 남을 수 있습니다.
마감 날짜만 명확하면 해당 한국 날짜 23:59:59까지로 처리하며 원래 시각 필드는 null을 유지합니다.
명시된 시각이 있으면 해당 시각으로 마감을 판정합니다.

상금 미정·문의·지급 여부 추후 안내는 지급 확정으로 바꾸지 않습니다.
자동 마일리지 구조화는 현재 사전에 넣은 `NOVA`, `향림`, `SW`라는 이름이 명시된 경우로 제한합니다.
이 목록은 해당 제도가 실제 운영 중임을 보증하는 목록이 아니라 파서 인식 목록입니다.
제도 이름이 불명확하거나 다른 이름이면 원문은 보존하고 검수 경고를 남깁니다.
새 제도를 자동 인식하려면 원문과 함께 `MILEAGE_SYSTEMS` 및 테스트를 추가합니다.

명확하지 않은 대상 조건을 강제 필터로 쓰지 않습니다.
AI 요약도 혜택·대상을 새로 만들어내지 않도록 원문 근거 또는 제목으로 제한합니다.
이러한 방어가 의미적 정확도를 100% 보장하지는 않습니다.

## 7. 재분석과 수동 검수

AI 설정 또는 파서를 바꾸어도 기존 동일 hash 공지는 자동 재분석되지 않습니다.
의도적인 재분석:

```powershell
.venv\Scripts\python.exe -m app.cli reanalyze --notice-id 1
.venv\Scripts\python.exe -m app.cli reanalyze --limit 100
.venv\Scripts\python.exe -m app.cli reanalyze --failed-only --limit 100
.venv\Scripts\python.exe -m app.cli reanalyze --refresh-fallback --limit 100
```

`--failed-only`는 실패 상태인 공지만 OpenAI로 재시도합니다. `AI_RATE_LIMITED`가 지속되면 배치를 중단하므로 할당량이 회복된 뒤 다시 실행합니다. `--refresh-fallback`은 OpenAI를 호출하지 않고 실패 공지의 규칙 추출 결과만 새로 계산하며, 실패 상태와 기존 AI 오류 코드를 유지합니다. 신청 방법의 띄어쓰기 변형과 시작일 미정인 단측 마감일을 지원하되, 생략된 연도나 날짜는 추정하지 않습니다.

이전 Gemini 분석 데이터를 정리할 때는 worker를 멈추고 `purge-gemini-analyses`를 실행합니다.
`gemini` 결과만 원문 기반 `rules / needs_review`로 교체하며 공지·찜은 남습니다.
`--include-failed-fallbacks`는 제공자를 구분할 수 없는 모든 `rules_fallback / failed` 결과까지 정리하므로,
OpenAI 실패가 아직 섞이지 않았을 때만 사용합니다.

ID는 실제 공지 ID로 바꿉니다.
수동 검수된 결과는 기본적으로 보호하며 `--include-reviewed`를 지정해야 다시 덮어쓸 수 있습니다.
재분석 중 AI가 실패해도 기존 `analyzed`·`reviewed` 결과는 유지합니다. 재분석·원문 변경은 추출 일정과 추천에도 영향을 줄 수 있으므로 찜·캘린더를 함께 확인합니다.

관리자는 상세의 최신 `content_hash`와 수정한 전체 AnalysisData를
`PUT /api/admin/notices/{id}/analysis`로 제출할 수 있습니다.
확인되지 않은 날짜·금액을 채우지 않습니다.
검수는 신뢰된 관리자가 원문을 비교한 뒤 수행하는 기능입니다.

세 출처에서 표본을 뽑아 제목·게시일·대상·신청 마감·실제 행사·상금·제도별 마일리지·원문 링크를 직접 비교합니다.
실제 수집·표본 검수 완료 전에는 추출 정확도 목표를 달성했다고 발표하지 않습니다.
