# 고급 설정

README의 사용법으로 충분하지 않을 때 보는 설정 모음입니다.

## 환경변수

| 이름 | 쓰임 |
|---|---|
| `RFP_ANTHROPIC_API_KEY` | `--llm`에 쓸 Claude API 키(rfpgen 전용). 있으면 공식 API 주소로 보냅니다 |
| `RFPGEN_ANTHROPIC_BASE_URL` | 위 키로 보낼 API 주소를 바꿀 때(사내 게이트웨이 등) |
| `ANTHROPIC_API_KEY` | 전용 키가 없을 때 쓰는 일반 키(이때는 `ANTHROPIC_BASE_URL`도 따릅니다) |
| `RFPGEN_LLM_MODEL` | 쓸 모델 ID(`--llm-model`과 같음). 없으면 Models API에서 가장 최근 Opus 계열을 고릅니다 |
| `RFPGEN_SIDECAR_DIR` | Node 사이드카 폴더(기본: 저장소의 `sidecars/node`) |
| `RFPGEN_CHROMIUM_PATH` | Playwright가 받은 Chromium 대신 쓸 Chrome 실행 파일 |
| `RFPGEN_SOFFICE` | LibreOffice 실행 파일(PATH·기본 설치 위치에 없을 때) |

## 설정 파일

| 파일 | 쓰임 |
|---|---|
| 조직 프로필 YAML(`--profile org.yaml`) | 제도 기준값·LLM 과제 설정을 덮어씁니다. `rfpgen profile`로 현재 값과 근거를 봅니다. RFP에서 읽은 값이 있으면 항상 RFP 값이 우선합니다 |
| 스타일 YAML(`--style my.yaml`) | 본문 HWPX·장표의 글꼴·크기·색. 기본은 `src/rfpgen/config/styles/report.yaml`(CC0) |
| `kb/private/forms.yaml` | 별지 서식에서 생성기가 모르는 칸의 값: `values: {담당자: 홍길동, 담당자 연락처: 010-…}` |
| `kb/private/people.csv` | 별지 성명 칸용 실명(`id,name` — `people.csv`의 id와 같게) |
| `<프로젝트>/forms.yaml` | 별지 서식의 나라장터 문서구분 바꾸기·건너뛰기: `doc_types: {"7": 정량제안서}`, `skip: ["3"]` |
| `<프로젝트>/strategy/storyboard.json` | 절별 거버닝 메시지·핵심 내용·필요 근거·넣을 도식(`figures`). 고친 뒤 `rfpgen draft`(다시 만들려면 `--refresh-storyboard`) |
| `<프로젝트>/strategy/figures/<id>.json` | 도식 스펙(자동 스펙 `<id>.auto.json`을 복사해 고침). 고친 뒤 `rfpgen figures` |

## LLM 비용 추정 단가

저장소에는 모델 ID를 두지 않으므로 기본값으로는 토큰 수만 보입니다. 조직 프로필에 단가(백만 토큰당 달러)를 적으면 실행마다 추정 비용을 보여 줍니다.

```yaml
llm:
  pricing_usd_per_mtok:
    value:
      <모델 ID>: {input: 0.0, output: 0.0, cache_read: 0.0, cache_write: 0.0}
    status: user
```

단가는 Anthropic 공개 가격표를 따르고, 실제 청구액은 Console에서 확인합니다.

## LLM 절 초안: 동시 호출·분량 보강

본문 절은 배점 순으로 첫 절을 혼자 보낸 뒤(공통 RFP 요약을 캐시에 올리고 인증 문제를 먼저 확인) 나머지를 기본 3개씩 동시에 보냅니다. 사용량 한도(rate limit) 오류가 나면 `parallel`을 줄이세요.


Claude가 쓴 절이 목표 최소 글자 수(쪽수 예산에서 계산)의 0.8배보다 짧으면, 1차 초안을 주고 한 번 더 써서 보강합니다(호출이 하나 늘어남). 끄거나 기준을 바꾸려면 조직 프로필에 적습니다.

```yaml
llm:
  tasks:
    value:
      section: {effort: high, max_tokens: 32000, runs: 1, expand_below: 0, parallel: 1}   # 보강 끔, 차례로
    status: user
```

`llm.tasks`는 과제 묶음 전체를 덮어쓰므로, 바꾸지 않는 과제도 `rfpgen profile`에 나온 값 그대로 함께 적습니다.

## 산출물 형식(개발·연동용)

| 파일 | 내용 |
|---|---|
| `rfp/rfp.vN.json` | 공고 기본정보, 평가표·평가규칙, 무효·감점 사유와 참가자격, 요구사항, 작성지침, 질의서 후보. 모든 값에 원문 위치(문서·블록·쪽)가 붙습니다 |
| `rfp/extraction_report.vN.json` | 사람이 확인할 점검 결과 |
| `plan/outline.json`, `budget.json`, `trace.json` | 목차, 쪽수 예산·절별 목표 글자 수, 요구사항 추적표(판별 사본은 `plan/vN/`) |
| `sections/<절 ID>.vN.json` | 절 초안(판을 쌓음) |
| `audit/llm_calls.jsonl` | LLM 호출 기록(모델·토큰·캐시·결과) |
| `project.yaml` | 분석 이력, 기억한 KB 폴더, 승인 기록(G1~G5) |

설계와 데이터 모델은 [설계서](design.md)에 있습니다.
