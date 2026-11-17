# 나라장터 제안서 자동생성기 설계서

| 항목 | 내용 |
|---|---|
| 문서 상태 | v0.8 — 16장 결정 확정, M0 원문 대조(1차), M1·M2·M3(1차)·별지 채우기·도식 렌더·승인 게이트 구현 반영 |
| 작성일 | 2026-11-16 (v0.1), 2026-11-17 (v0.2) |
| 근거 자료 | [조사 보고서](<../reports/나라장터 제안서 자동화 조사.md>), [조사 노트](<../research_notes/나라장터 제안서 자동화 조사/>) |
| 대상 범위 | 국가·지자체 **협상에 의한 계약**의 기술제안서(정성제안서). SW 개발·유지관리, 정보화 용역을 먼저 다룬다 |
| 결정 사항 | [16장](#16-결정-사항)에 확정본 정리. 변경 이력은 [17장](#17-변경-이력) |

---

## 0. 요약

이 생성기는 **"평가표를 빠짐없이 채우는 제안 작업대"**를 목표로 한다. 문장을 잘 쓰는 AI는 목표가 아니다. 이렇게 정한 근거는 조사 결과 세 가지다.

- 업체 간 기술점수 차이는 보통 1~2점이다.
- 실무에서 요구사항 누락은 0점으로 처리된다.
- 조달청은 2026년 8월부터 AI가 정리한 "요구사항 충족 여부"를 평가위원에게 제공하는 실증을 시작했다.

따라서 생성기의 핵심 지표는 수주율이 아니다. **요구사항 누락 0건, 형식 위반 0건, 작성 시간 단축** 세 가지로 잡는다.

핵심 설계 결정은 다음과 같다.

| # | 결정 | 근거(보고서 위치) |
|---|---|---|
| D1 | 평가표 → 목차 → 요구사항 ID → 쪽을 하나의 계층으로 묶는 데이터 모델을 중심에 둔다 | 별지 제5호 목차와 SW 평가부문이 거의 1:1로 대응 (4장) |
| D2 | 요구사항 추적표를 1급 산출물로 만들고, 제출 게이트는 커버리지 100%로 둔다 | 누락 0점 관행, 조달청 AI 기술평가 실증 (1·2장) |
| D3 | 숫자·날짜·배점은 코드가 판정하고, LLM은 서술과 보조 추출만 맡는다 | nara-detector 패턴, LLM 추출 개수가 68↔51개로 흔들린 Yu et al.(2026) (1·3장) |
| D4 | 모든 제도 수치는 계층형 설정 프로필로 뺀다. 공고에서 파싱한 값이 항상 우선하고, 원문으로 확인하지 않은 값에는 `provisional` 표시를 붙인다 | 원문 미대조 수치 다수 (5장) |
| D5 | 출력은 HWPX(A4 세로 본문·별지)와 PPTX(가로 장표·발표)를 거쳐 PDF로 낸다. 렌더 경로는 서버와 한컴 두 가지를 둔다 | 제출은 PDF, 한컴 번들 글꼴 라이선스 (4장) |
| D6 | 모든 추출·생성 결과에 원문 근거 위치(locator)를 강제한다 | rfp-lens, bid-deep-agent, 조달청 AI의 원문 위치 확인 기능 (1장) |
| D7 | LLM은 공급자 추상화 뒤에 두고, 로컬 모델 전용 모드를 1급 기능으로 지원한다 | 공공사업 문서의 외부 전송에 대한 경계 (1·6장) |
| D8 | Python 단일 코어에 Node 사이드카(HWP 파싱·렌더)를 붙인다 | python-hwpx·python-pptx 생태계, kordoc·rhwp (1장) |
| D9 | 사람 승인 게이트를 5개 둔다. 나라장터 제출 자체는 자동화하지 않는다 | 허위 기재 감점, 최종 제출 후 수정 불가 (2·4장) |

---

## 1. 배경과 문제

### 1.1 제안 작업의 현실

| 사실 | 값 | 설계에 주는 의미 |
|---|---|---|
| 공고기간 | 제안서 제출마감 40일 전 공고(긴급 등은 10일) | 실제 작성 기간은 4~6주다. 시간 단축이 일차 가치다 |
| 배점 | SW사업 기술 90 : 가격 10 (예: 정량 20 + 정성 70) | 정성 70점이 본문 분량 배분의 기준이 된다 |
| 협상적격 | 기술점수 ≥ 배점한도의 85%, 가격 ≤ 예산 | 85%는 적격 통과선이다. 누락으로 깎이면 탈락할 수 있다 |
| 평가부문 | 6개 부문, 부문당 30점 상한, 상생협력·하도급 각 5점 이상 | 상생협력·하도급 장은 사실상 필수다 |
| 정성평가 | 위원별 최고·최저점을 빼고 평균, 세부항목 최대 5등급 | 평가 질문이 곧 절별 체크리스트다 |
| 온라인 평가 | 검토시간 60분 이상, 5억원 미만은 발표 의무 없음 | 본문이 서면만으로 읽혀야 하고, 요약본과 장 첫머리가 중요하다 |
| 제출 | 제안서류 일체 PDF, 총 300MB 이하(공고별 조건), 최종 제출 후 수정 불가 | 렌더·용량·메타데이터 점검이 필수다 |
| 블라인드 | 회사명·로고·CI·대표자 표기 금지, 위반 시 감점(기관 규정) | 메타데이터까지 지우는 블라인드 모드가 필요하다 |

> 위 수치 상당수는 원문 대조 전 값이다. 부록 A의 대조가 끝나기 전에는 모두 `provisional`로 다룬다.

### 1.2 기존 도구의 공백

조사 보고서 6장이 정리한 빈자리 가운데 이 프로젝트가 직접 겨냥하는 것은 다음 다섯 가지다.

1. **RFP 구조화 스키마와 파서.** 평가표, 요구사항, 작성지침, 제출서류를 원문 위치와 함께 뽑는 공개 구현이 없다.
2. **평가표 기반 목차·쪽수 배분과 추적표.** 여러 PoC에 조각으로만 존재한다.
3. **HWPX와 한국형 가로 PPTX 동시 출력, 양식 충실도 검증.** 상용 도구도 완전히 해결하지 못했다.
4. **결정적 제출 전 점검.** 중국 标书 생성기의 실격사유(废标项) 검사에 해당하는 기능이 한국 도구에는 없다.
5. **사전규격 단계 조기 착수와 정정공고 diff.** 수집기는 많지만 생성기와 이어진 사례가 없다.

### 1.3 이 문서가 답하는 질문

- 무엇을 만들고 무엇을 만들지 않는가 (2장)
- 어떤 구조와 데이터로 만드는가 (5~11장)
- 무엇을 어떻게 검증하는가 (7.8절, 13장)
- 어떤 순서로 만드는가 (14장)
- 무엇이 아직 정해지지 않았는가 (16장)

---

## 2. 목표, 비목표, 성공 지표

### 2.1 목표

| ID | 목표 |
|---|---|
| G1 | 공고·RFP 첨부에서 계약방법, 평가표, 요구사항, 작성지침, 제출서류, 참가자격을 원문 위치와 함께 구조화한다 |
| G2 | 평가표를 기준으로 목차, 쪽수 예산, 요구사항 추적표를 자동으로 작성한다 |
| G3 | 사내 근거(실적·인력·기술)에 기반한 섹션 초안을 생성한다. 근거 없는 수치는 0건이어야 한다 |
| G4 | 발주처 양식에 맞는 HWPX/PPTX/PDF를 출력하고, 공고 첨부 별지를 채운다 |
| G5 | 누락, 분량, 형식, 블라인드, 용량을 제출 전에 결정적으로 점검한다 |
| G6 | 사전규격 단계부터 착수할 수 있게 하고, 본공고와 정정공고의 변경을 자동으로 반영한다 |

### 2.2 비목표

- **나라장터 제출 자동화**(인증서 로그인, 업로드). 제출은 사람이 한다.
- **가격(투찰가) 산정과 예측**
- **공고 추천 서비스 자체.** 수집은 생성기 입력에 필요한 만큼만 한다.
- **발주기관용 RFP 작성 지원**
- **수주율이나 평가 점수 예측을 제품 지표로 쓰는 것.** 공개된 점수 데이터가 없어 검증할 수 없다.
- **평가위원 정보 수집·접촉과 관련된 모든 기능.** 사전접촉은 감점과 해촉 사유다.

### 2.3 성공 지표

아래 목표치는 이 설계서가 제안하는 값이다. M1 벤치마크(13장)를 만든 뒤 다시 정한다.

| 지표 | 목표 | 측정 방법 |
|---|---|---|
| 요구사항 커버리지(제출본) | 100% | 제출 게이트 COV-001 |
| 요구사항 ID 추출 재현율(표 기반 RFP) | ≥ 99% | 라벨링한 RFP 30건 |
| 평가표 추출 정확도(항목·배점 완전 일치) | ≥ 95% | 같은 데이터셋 |
| 제출 시점 형식 위반(분량·글꼴·용량·필수서류) | 0건 | 점검 리포트 |
| 블라인드 누출 탐지 재현율 | ≥ 99% | 합성 누출 주입 테스트 |
| 근거 없는 수치 | 0건 | FACT-001·002 |
| RFP 투입부터 추적표·목차 초안까지 자동 처리 시간 | 30분 이내 | 로그 |
| 착수부터 1차 전체 초안까지 걸리는 시간 | 기존 방식 대비 50% 단축 | 파일럿 병행 작성 비교 |

---

## 3. 사용자와 작업 흐름

### 3.1 사용자

| 역할 | 하는 일 | 생성기에서 주로 보는 것 |
|---|---|---|
| 제안 PM | 착수 판단, 목차·전략 확정, 일정 관리, 최종 승인 | 추출 확인 화면, 추적표, 스토리보드, 점검 리포트 |
| 섹션 작성자(SME) | 담당 절 작성·수정, 자료 제공 | 절 초안, 자료 요청서, 근거 패널 |
| 리뷰어(레드팀) | 평가위원 관점의 검토 | LLM 리뷰 결과, 60분 훑어보기 테스트 |
| KB 관리자 | 실적·인력·인증·재사용 콘텐츠 관리 | KB 편집, 유효기간 알림 |

### 3.2 작업 흐름과 승인 게이트

```
[감지] 사전규격·입찰공고 ─▶ [분석] RFP 구조화 ──G1──▶ [판단] Go/No-Go
   ─▶ [설계] 목차·쪽수·추적표 ──G2──▶ [전략] Win theme·스토리보드·자료요청 ──G3──▶
   [작성] 절 초안 ──G4──▶ [파생] 요약본·발표자료·대본·정량서식
   ─▶ [렌더] HWPX/PPTX → PDF ─▶ [점검] 결정적 규칙 + LLM 리뷰 ─(실패)─▶ [작성]
   ─▶ [패키지] 제출 파일 세트 ──G5──▶ (사람이 나라장터에 제출)

정정공고·본공고 발생 → diff → 영향받는 단계부터 재실행 (7.11절)
```

| 게이트 | 사람이 확정하는 것 | 이 게이트를 통과하지 않으면 |
|---|---|---|
| G1 추출 확정 | 평가표(항목·배점), 요구사항 목록, 작성지침(분량·글꼴·형식·블라인드), 계약방법 | 계획 단계 진입 불가 |
| G2 설계 확정 | 목차, 쪽수 예산, 요구사항→절 매핑 | 전략·작성 진입 불가 |
| G3 전략 확정 | Win theme, 장별 핵심 메시지, 스토리보드, 자료 요청 배정 | 절 생성 불가 |
| G4 절 승인 | 절 초안(절별) | 해당 절은 렌더에 "초안" 워터마크 |
| G5 제출 승인 | 점검 리포트의 blocker 0건, 제출 전 점검표 서명 | 패키지 확정 불가 |

---

## 4. 설계 원칙

| ID | 원칙 | 구체적 의미 |
|---|---|---|
| P1 | 평가표가 구조를 정한다 | 목차, 쪽수, 체크리스트, 리뷰 기준이 모두 평가표에서 나온다. RFP가 지정한 목차는 바꾸지 않는다 |
| P2 | 숫자는 코드가, 문장은 LLM이 | 배점 합계, 쪽수, 용량, 실적 금액, 인력 수는 결정적으로 계산하거나 KB에서 가져온다 |
| P3 | 모든 산출물은 근거를 가진다 | 추출값에는 RFP 위치를, 생성 문장에는 연결된 요구사항·fact·RFP 블록을 붙인다 |
| P4 | 하드코딩 금지 | 제도 수치는 프로필로 뺀다. 요구사항 접두어 집합도 RFP에서 읽는다 |
| P5 | 사람이 최종 책임을 진다 | 다섯 게이트를 두고, 생성기는 자동 제출하지 않는다 |
| P6 | 가드레일은 프롬프트가 아니라 후처리에 둔다 | 금지 표현 목록을 프롬프트에 나열하지 않고 생성 후 필터로 잡는다(Yu et al. 2026) |
| P7 | 데이터는 밖으로 나가지 않는 것이 기본값 | 데이터 분류별로 LLM 경로를 제한하고, 로컬 전용 모드를 지원한다 |
| P8 | 라이선스를 추적한다 | GPL·AGPL 코드는 분석해 이식·튜닝하되 출처·커밋·원 라이선스를 기록하고 별도 하위 패키지로 모은다(11.2절). 라이선스 미명시 코드는 복사하지 않는다. 한컴 번들 글꼴은 배포하지 않는다 |

---

## 5. 시스템 아키텍처

### 5.1 구성도

```
┌──────────────── 인터페이스: CLI (M1~) · REST API · Web UI (M4~) ────────────────┐
│                                                                                   │
│  ingest ─▶ parse ─▶ extract ─▶ plan ─▶ strategy ─▶ generate ─▶ derive             │
│                                                        ▲            │             │
│                                                        │ 수정 요청   ▼             │
│                                       package ◀─ check ◀──────── render           │
│                                                                                   │
├───────────────────────────────────────────────────────────────────────────────────┤
│ 공통 계층                                                                          │
│  Project Store(산출물·버전·DAG 캐시) · Company KB · Profile Resolver · Rule Engine │
│  LLM Gateway(공급자 추상화·데이터 분류 라우팅) · Audit Log                          │
│  Sidecars: Node(kordoc 파싱, rhwp 렌더) · 외부 프로세스(LibreOffice/H2Orestart, 선택)│
│  선택 에이전트: Windows + 한글 COM(pyhwpx) 렌더 에이전트                             │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 단계별 명세

| # | 단계 | 입력 | 산출물 | 처리 방식 | 게이트 |
|---|---|---|---|---|---|
| 1 | ingest | 공고번호 또는 업로드 파일 | `notices/*.json`, `raw/*` | 결정적 | – |
| 2 | parse | 원본 첨부 | `docir/*.json` | 결정적(비전 폴백) | – |
| 3 | extract | DocIR | `rfp/rfp.v{n}.json`, 질의서 초안 | 규칙 우선, LLM 보조 | G1 |
| 4 | plan | rfp.json, 프로필 | `plan/outline.json`, `budget.json`, `trace.json`·`.xlsx` | 결정적, LLM 매핑 제안 | G2 |
| 5 | strategy | outline, KB | `strategy/storyboard.json`, `data_requests.xlsx` | LLM | G3 |
| 6 | generate | storyboard, KB, RFP | `sections/*.json` | LLM, fact 치환은 결정적 | G4 |
| 7 | derive | sections | 요약본·발표자료·대본·정량서식 데이터 | LLM | – |
| 8 | render | sections, 템플릿, 스타일 | `out/*.hwpx`, `*.pptx`, `forms/*`, `pdf/*` | 결정적 | – |
| 9 | check | 렌더 결과, 모든 산출물 | `checks/{run}.json`·`.html` | 규칙, LLM 리뷰는 보조 | – |
| 10 | package | PDF, 점검 결과 | `submission/`, 제출 전 점검표 | 결정적 | G5 |

### 5.3 실행 모델

각 단계는 **입력 산출물의 해시를 키로 하는 순수 함수**처럼 동작한다. 빌드 시스템과 같은 구조다.

- 상위 산출물이 바뀌면 그 하위 단계만 다시 실행한다. 정정공고 반영과 재현성이 여기서 나온다.
- 모든 산출물은 Pydantic 스키마로 검증하는 JSON이다. `schema_version`을 붙이고 마이그레이션 함수를 둔다.
- 사람이 수정한 값은 `origin: human`으로 기록한다. 재실행해도 덮어쓰지 않고, 충돌하면 사람에게 묻는다.

### 5.4 프로젝트 저장 구조

```
projects/{project_id}/
  project.yaml                 # 공고번호, 프로필, 블라인드 여부, 상태, 게이트 승인 기록
  raw/{sha256}.{ext}           # 원본 첨부(불변, 내용 주소)
  notices/{bid_ord}.json       # 공고·정정공고 버전
  docir/{doc_id}.json
  rfp/rfp.v{n}.json  rfp/extraction_report.v{n}.json
  plan/outline.json  plan/budget.json  plan/trace.json  plan/trace.xlsx
  strategy/storyboard.json  strategy/data_requests.xlsx
  sections/{section_id}.v{n}.json
  derive/summary.json  derive/slides.json  derive/script.md
  out/main.hwpx  out/slides.pptx  out/forms/*.hwpx  out/pdf/*.pdf
  checks/{run_id}.json  checks/{run_id}.html
  submission/                  # 문서구분별 최종 PDF + 점검표
  audit/llm_calls.jsonl  audit/approvals.jsonl
```

---

## 6. 데이터 모델

### 6.1 근거 위치와 추출값

모든 추출값은 "값, 근거, 추출 방법, 상태"를 함께 가진다.

```python
class Locator(BaseModel):
    doc_id: str            # 원본 파일 단위 ID
    block_id: str          # DocIR 블록(문단·표 셀) ID, 예: "d03:b0142"
    page: int | None       # 원본 PDF/렌더 기준 쪽
    char_start: int | None
    char_end: int | None
    quote: str             # 원문 인용. 블록 텍스트에 실제로 포함되어야 함(검증 대상)

class Extracted(BaseModel, Generic[T]):
    value: T
    locators: list[Locator]
    method: Literal["rule", "llm", "human"]
    confidence: float      # rule=1.0, llm=교차검증 결과, human=1.0
    status: Literal["proposed", "confirmed", "rejected"]
```

### 6.2 정규화 문서 표현(DocIR)

HWP·HWPX·PDF·DOCX를 하나의 블록 트리로 정규화한다. 요구사항 정의서와 평가표가 모두 표이므로 **셀 병합 정보까지 보존**하는 것이 핵심이다.

```python
class Block(BaseModel):
    id: str                       # "d03:b0142"
    kind: Literal["heading", "para", "list_item", "table", "cell",
                  "image", "caption", "header", "footer"]
    text: str
    level: int | None             # 제목 수준·목록 깊이
    page: int | None
    numbering: str | None         # 원문 번호 "Ⅲ-2-가"
    table: TableRef | None        # table_id, row, col, rowspan, colspan
    parent: str | None
```

### 6.3 RFP 스키마

```python
class Notice(BaseModel):
    bid_no: str                   # 공고번호
    bid_ord: str                  # 차수(정정공고)
    stage: Literal["사전규격", "본공고", "정정공고"]
    agency: str
    demand_agency: str | None
    title: str
    budget_krw: int | None
    contract_method: Extracted[ContractMethod]
    deadlines: Deadlines          # 제안서 제출 마감, 질의 기한, 발표·평가일

class EvalArea(BaseModel):
    name: str                     # "전략 및 방법론"
    points: float
    items: list["EvalItem"]

class EvalItem(BaseModel):
    id: str                       # 내부 ID "E-02-03"
    name: str                     # "개발 방법론"
    kind: Literal["정량", "정성"]
    points: float
    criteria: list[str]           # 평가 질문: "단계별 산출물을 제시했는가"
    grades: int | None            # 5등급 등
    locators: list[Locator]

class EvaluationTable(BaseModel):
    tech_price_ratio: Extracted[tuple[int, int]]
    areas: list[EvalArea]
    bonus: list[EvalItem]         # 총점 밖 가점

class Requirement(BaseModel):
    id: str                       # RFP 원문 ID "SFR-001". 없으면 내부 발급 "X-0007"
    prefix: str | None
    category: str                 # 기능, 성능, 보안 …
    name: str
    definition: str
    details: list[str]
    outputs: list[str]            # 산출정보
    related: list[str]
    source: str | None            # 요구사항 출처
    detail_grade: Literal["S", "A", "B", "C", "D"] | None  # 상세화 등급 추정(SPRi 2017)
    ambiguities: list[str]        # 모호 표현 → 질의서 후보
    origin: Literal["table", "text_llm", "human"]
    locators: list[Locator]

class WritingGuideline(BaseModel):
    prescribed_toc: Extracted[list["TocNode"]] | None
    main_page_limit: Extracted[int] | None
    summary_page_limit: Extracted[int] | None
    count_exclusions: Extracted[list[str]]          # 표지·목차·간지
    paper: Extracted[Literal["A4", "A3"]]
    orientation: Extracted[Literal["portrait", "landscape", "any"]]
    min_font_pt: Extracted[float] | None
    table_min_font_pt: Extracted[float] | None
    editor: Extracted[str] | None                   # "아래한글 권장" 등
    file_format: Extracted[str]                     # "PDF"
    total_size_limit_mb: Extracted[int] | None
    blind: Extracted[bool]
    presentation: Extracted["Presentation"] | None  # 발표·질의 시간, PM 발표 의무
    required_documents: list["RequiredDoc"]         # 별지 서식, 문서구분

class Rfp(BaseModel):
    schema_version: str
    notice: Notice
    evaluation: EvaluationTable
    requirements: list[Requirement]
    guideline: WritingGuideline
    eligibility: list[Extracted[str]]               # 참가자격(하드 게이트)
    glossary: dict[str, str]                        # RFP 고유 용어 → 정의
```

### 6.4 계획 산출물

```python
class OutlineNode(BaseModel):
    id: str                       # "S-3-2"
    number: str                   # "Ⅲ.2"
    title: str                    # 평가항목 용어를 그대로 사용
    eval_items: list[str]         # EvalItem.id
    requirements: list[str]       # Requirement.id
    page_budget: int
    checklist: list[str]          # 평가 질문 → 이 절이 반드시 답할 항목
    origin: Literal["prescribed", "eval_table", "default_template", "human"]
    children: list["OutlineNode"]

class TraceRow(BaseModel):
    req_id: str
    req_name: str
    category: str
    eval_item: str | None
    sections: list[str]           # OutlineNode.id (1개 이상)
    summary: str                  # 제안 요약 1~2문장
    acceptance: Literal["수용", "부분수용", "대안제시", "미정"]
    pages: list[int]              # 렌더 후 채움
    rfp_locators: list[Locator]
    status: Literal["unmapped", "mapped", "drafted", "verified"]
```

추적표 XLSX 열은 다음 순서로 고정한다: `요구사항 ID | 명칭 | 분류 | 연결 평가항목 | 제안 요약 | 수용 여부 | 제안서 쪽 | RFP 원문 위치`. 공식 서식이 없으므로 이 구성은 업계 관행과 rfp-lens의 근거 위치 방식을 합친 제안이다.

### 6.5 회사 지식베이스(KB)

| 엔터티 | 주요 필드 | 비고 |
|---|---|---|
| Fact | id, kind(실적/인력/인증/수치/제품), value(구조화), evidence(증빙 파일), valid_from/to, blind_sensitive, confidential | **본문에 들어가는 모든 수치의 유일한 출처** |
| ReferenceProject(실적) | 사업명, 발주기관, 기간, 계약금액, 역할(주관/참여), 기술 키워드, 증빙 | 정량제안서와 유사사업 실적 표에 사용 |
| Person(인력) | 가명 ID, 등급·자격, 경력 연수, 보유 기술, 참여 가능 기간 | 실명·연락처는 별도 저장소, 렌더 시에만 결합 |
| Certification | 인증명, 번호, 유효기간 | 만료 알림(FACT-003) |
| ContentBlock | 과거 제안서 절(텍스트·표·그림), 태그(평가항목·접두어·기술), 출처, 수주 여부, 최종 검토일 | 재사용 후보 검색 대상 |
| Asset | 로고, CI 색, 다이어그램 원본, 템플릿 | 블라인드 모드에서 사용 금지 |
| Identity | 회사명(국문·영문·약칭), 도메인, 대표자, 제품·솔루션명, 로고 지각 해시 | 블라인드 점검 사전 |

### 6.6 절 초안

```python
class DraftBlock(BaseModel):
    kind: Literal["para", "bullets", "table", "figure", "callout"]
    level: int | None             # bullets 깊이(□ ○ - · ※)
    text: str | None              # "{{fact:F-0123}}" 토큰 포함 가능
    items: list[str] | None
    table: TableSpec | None       # 병합 최소화
    figure: DiagramSpec | None    # 조직도·추진체계도·일정·구성도
    req_refs: list[str]
    fact_refs: list[str]
    rfp_refs: list[Locator]

class SectionDraft(BaseModel):
    section_id: str
    version: int
    head_message: str             # 거버닝 메시지 1문장
    blocks: list[DraftBlock]
    placeholders: list[str]       # "[확인 필요: 유사사업 계약금액]"
    est_pages: float              # 렌더 전 추정 쪽수
    llm_call_ids: list[str]       # 감사 추적
```

### 6.7 엔터티 관계

```
EvalArea 1─N EvalItem N─M OutlineNode N─M Requirement
                               │ 1                 │
                               N                   └─ TraceRow (요구사항당 1행)
                         SectionDraft N─M Fact(KB)          │
                               │                            │
                         렌더된 쪽 번호 ──────────────────────▶ TraceRow.pages
```

---

## 7. 모듈 설계

### 7.1 ingest — 공고 수집

| 입력 경로 | 내용 | 시기 |
|---|---|---|
| 수동 업로드 | 공고문·RFP·별지 파일, ZIP | M1부터 항상 지원 |
| 공공데이터포털 조달청 OpenAPI | 입찰공고 `/1230000/ad/BidPublicInfoService`, 사전규격 `/1230000/ao/HrcspSsstndrdInfoService`(별도 활용신청), 낙찰 `/1230000/as/ScsbidInfoService` | M4 |
| MCP 어댑터(선택) | narajangteo-bid-mcp(MIT) 등 기존 서버를 입력 어댑터로 사용 | M4 |

- **감시:** 키워드, 기관, 업종 코드로 사전규격과 입찰공고를 주기적으로 조회한다. 공고번호와 차수로 버전을 관리한다.
- **첨부:** 다운로드 후 ZIP을 풀고 원본을 `raw/`에 내용 주소로 저장한다.
- **확인 필요:** 서비스명, 오퍼레이션, 트래픽 한도, 첨부 다운로드 URL의 안정성은 공개 코드를 근거로 했고 data.go.kr 명세로 확인하지 않았다(부록 A). 다운로드가 실패하면 수동 업로드로 안내한다.
- API 키는 환경변수나 비밀 저장소에서만 읽고, 로그와 산출물에 기록하지 않는다.

### 7.2 parse — 문서 정규화

| 포맷 | 1차 경로 | 대안·교차검증 | 비고 |
|---|---|---|---|
| HWPX | python-hwpx 또는 OWPML XML 직접 해석 | kordoc(사이드카) | 셀 병합 보존 |
| HWP5 | python-hwpx의 HWP5→HWPX 변환 후 HWPX 경로 | kordoc, hwplib | 변환 품질 회귀 테스트 필수 |
| PDF | pdfplumber(M1 구현) — 셀을 못 찾은 칸은 격자 좌표로 다시 읽음 | opendataloader-pdf(후보), 텍스트 레이어가 없으면 OCR 또는 비전 | 쪽 번호 보존 |
| DOCX | python-docx | – | |
| XLSX | openpyxl | – | 평가표가 엑셀로 첨부되는 경우 |

- **이중 파싱:** 요구사항 표와 평가표처럼 중요한 표는 두 경로로 파싱해 셀 텍스트 일치율을 비교한다. 불일치가 기준을 넘으면 해당 쪽 이미지를 비전 모델로 재구성하고 G1 검토 큐에 올린다.
- **문서 분류:** 첨부 중 제안요청서, 과업지시서, 공고문, 평가기준, 별지서식을 파일명 규칙과 내용 분류로 식별한다.
- **보안:**
  - ZIP 해제 총 크기와 파일 수를 제한한다.
  - XML 외부 엔티티를 차단한다(defusedxml).
  - 매크로와 스크립트는 실행하지 않는다.
  - 파싱은 시간·메모리 제한을 건 별도 워커 프로세스에서 한다.

### 7.3 extract — RFP 구조화

추출은 세 번의 패스로 나눈다.

**(A) 규칙 기반 (결정적)**

- **요구사항 표 탐지:** 헤더 키워드(요구사항 고유번호, 요구사항 명칭, 정의, 세부내용, 산출정보)로 찾는다. ID는 정규식 `^[A-Z]{3}-(?:[A-Z]{2,4}-)?\d{3}$`로 뽑는다. 접두어 집합은 문서에서 수집하고 하드코딩하지 않는다.
- **총괄표·정의서 대조:** 두 곳의 ID 목록을 비교해 누락과 중복을 찾는다.
- **평가표 검증:** 부문 합계가 총점과 같은지, 정량과 정성의 합이 기술 배점과 같은지 확인한다. 30점 상한이나 5점 하한을 어기면 오류가 아니라 정보로 표시한다. RFP 값이 우선이기 때문이다.
- **작성지침 패턴 사전:** 각 매치에 locator를 붙인다.

  | 대상 | 패턴 예시 |
  |---|---|
  | 분량 | `(\d+)\s*(쪽\|페이지\|매\|장)\s*(이내\|이하)` |
  | 글자 크기 | `(\d+(?:\.\d+)?)\s*(pt\|포인트)` |
  | 용량 | `(\d+)\s*MB` |
  | 블라인드 | `블라인드\|업체정보\s*삭제` |
  | 용지 | `A4\|A3`, `가로\|세로` |

**(B) LLM 보조 (구조화 출력, locator 필수)**

- ID 없는 서술형 요구("~하여야 한다")의 후보를 추출하고 내부 ID `X-nnnn`을 붙인다.
- 평가 세부질문을 정규화하고 정성 항목의 의도를 요약한다.
- 계약방법 판별의 근거 문장을 찾는다.
- 모호한 표현을 표시하고 상세화 등급(S~D)을 추정해 **질의서 초안**을 만든다.

**(C) 대조와 확정**

- **충돌 검토:** 규칙 결과와 LLM 결과의 차이 중 충돌하는 항목만 G1 검토 큐에 올린다.
- **불안정 감지:** LLM 추출은 같은 입력으로 기본 2회 실행한다. 합집합과 교집합의 차이를 불안정 신호로 쓴다(Yu et al. 2026: 같은 파일에서 68개와 51개).
- **인용 검증:** LLM이 반환한 `quote`가 해당 블록 텍스트에 실제로 포함되는지 문자열로 확인한다. 포함되지 않으면 그 결과를 버린다.

산출물은 `rfp.json`과 `extraction_report.json`(신뢰도, 충돌, 미확정 항목)이다.

### 7.4 plan — 목차, 쪽수 예산, 추적표

1. **프로필 해석:** 9장의 계층 규칙에 따라 배점, 컷오프, 기본 목차를 정한다.
2. **목차 생성 우선순위:**
   1. RFP 지정 목차. 그대로 쓰고 바꾸지 않는다.
   2. 평가표의 부문·세부항목 순서
   3. 기본 템플릿: 제안 개요, 제안업체 일반, 별지 제5호 Ⅱ~Ⅵ, Ⅶ 그 밖의 사항

   SW사업이면 "상생협력·하도급 계획" 장을 자동으로 넣는다. 장·절 제목에는 평가항목 용어를 그대로 쓴다.
3. **요구사항→절 매핑:** 접두어 기본 맵(Ⅲ: ECR·SFR·SER·DAR·COR, Ⅳ: PER·QUR·SIR·INR·TER, Ⅴ: PMR, Ⅵ: PSR)에 LLM의 매핑 제안을 더한다. 사람이 G2에서 확정하며, 모든 요구사항은 1개 이상의 절에 연결되어야 한다.
4. **쪽수 예산:** 정량항목은 정량제안서로 분리하고 본문 예산에서 뺀다.

   > 절 i의 쪽수 = (본문 상한 − 고정 장 쪽수) × (절 i에 연결된 정성 배점 / 정성 배점 합계)

   - 정수화는 최대잉여법(largest remainder)으로 하고, 절마다 최소 1쪽을 보장한다.
   - 쪽수 제외 항목(표지·목차·간지)은 RFP에서 파싱한 값을 쓴다.
   - 이 식은 "배점 비례 분량" 실무 원칙을 계량화한 제안이며 검증된 최적식은 아니다.
5. **체크리스트:** 평가 질문을 절별 필수 응답 항목으로 바꾼다.

**쪽수 예산 예시(가상).** 본문 100쪽, 고정 장(제안 개요·일반현황) 10쪽, 정성 70점일 때 1점당 약 1.29쪽이 된다.

| 부문 | 배점 | 비례값 | 1차(내림) | 최종(최대잉여) |
|---|---|---|---|---|
| 전략 및 방법론 | 20 | 25.71 | 25 | 26 |
| 기술 및 기능 | 20 | 25.71 | 25 | 26 |
| 성능 및 품질 | 10 | 12.86 | 12 | 13 |
| 프로젝트 관리 | 10 | 12.86 | 12 | 13 |
| 프로젝트 지원 | 5 | 6.43 | 6 | 6 |
| 상생협력·하도급 | 5 | 6.43 | 6 | 6 |
| 합계 | 70 | 90.00 | 86 | **90** |

산출물은 `outline.json`, `budget.json`, `trace.json`·`trace.xlsx`, 질의서 초안이다.

### 7.5 strategy — 전략과 스토리보드

- **Win theme 3개:** 사업 이해, 차별화, 리스크 저감 관점에서 정하고 각 장의 핵심 메시지로 내려보낸다.
- **스토리보드:** 쪽 또는 장표 단위로 거버닝 메시지, 평가항목 태그, 요구사항 ID 칩, 콘텐츠 유형(표·도식·본문), 필요한 fact를 정한다.
- **자료 요청서:** 스토리보드에 필요한 fact 중 KB에 없는 것을 담당자 배정용 XLSX로 뽑는다.
  - 이 기능이 가장 중요하다. Yu et al.(2026)에서 불리한 판정의 68%가 시스템 소스에 없던 정보 때문이었다. 생성 **전에** 공백을 드러내야 한다.
- **Go/No-Go 보조:** 참가자격 하드 게이트(결정적), 요구사항 대비 KB 커버리지, 일정 여유를 점수표로 보여 준다. 판단은 사람이 한다.

### 7.6 generate — 절 생성

- **단위와 순서:** 절 단위로 호출하고 배점이 높은 절부터 생성한다. 비용·시간 예산이 소진되면 고배점 절이 먼저 완성된 상태가 된다.
- **컨텍스트 순서:** 아래 순서를 고정한다. 프롬프트 캐싱에 유리하다(8.4절).
  1. [전역 고정] 시스템 지침, 문체 가이드
  2. [프로젝트 고정] RFP 정규화 텍스트(블록 ID 포함), 평가표, 용어집, Win theme
  3. [절 가변] 체크리스트, 연결 요구사항 원문, 스토리보드, KB 검색 결과, 목표 글자 수
- **출력:** 자유 Markdown이 아니라 `SectionDraft` 구조로 받는다. 블록 종류는 문단, 개조식(□ ○ - · ※), 표(병합 최소화, 행안부 표 병합 지양 원칙), 그림 스펙이다.
- **수치 규칙:**
  - 본문의 숫자는 `{{fact:ID}}` 토큰이거나 연결된 RFP 블록에 있는 숫자여야 한다. 그 밖의 숫자는 FACT-002에 걸린다.
  - KB에 근거가 없으면 `[확인 필요: …]` 자리표시자를 남긴다. 숫자를 지어내지 않는다.
- **문체:** 개조식, 명사형 종결("~함", "~제공"), RFP 용어 그대로. 비방·타사 비교와 과장은 후처리 필터(LANG-*)로 잡는다.
- **지시문은 산문으로 쓴다.** 태그는 입력 데이터를 구분하는 데만 쓴다. Yu et al.(2026)에서 지시를 중첩 XML로 바꾸자 품질이 74%에서 48%로 떨어졌다.
- **분량 맞춤:**
  - 스타일별 "쪽당 글자 수" 추정치로 목표 글자 수를 정한다. 추정치는 렌더 실측으로 보정한다.
  - 렌더 후 예산을 넘으면 해당 절에 축약을 재요청한다(최대 2회).
  - 모자라면 경고만 하고 억지로 늘리지 않는다.
- **재사용:** KB의 ContentBlock과 유사도가 높으면 "재사용 후 수정" 모드로 쓰고, RFP 용어로 치환한다.
- **절 간 일관성:** 투입 인력 수, 일정, 산출물 목록 같은 공통 수치는 프로젝트 fact(SSOT)에서만 가져온다(BidKit 패턴).

### 7.7 derive — 파생 산출물

| 산출물 | 생성 규칙 |
|---|---|
| 요약본 | 상한(기본 30쪽, RFP 우선) 안에서 장별 거버닝 메시지, 평가항목별 답 요약, 추적표 요약을 담는다. "발표본으로 대체 가능"이면 생략할 수 있다 |
| 발표자료 | 발표 20분 기준 20~25장, 16:9 또는 A4 가로 |
| 발표 대본·예상 질문 | 평가항목과 약점 기반 질문, 공통질문(2개 이상) 대비. 블라인드면 회사명 언급 금지 |
| 정량제안서 서식 | 인력·실적·인증 표를 KB에서 채워 공고 첨부 별지에 기입한다 |

### 7.8 check — 제출 전 점검

**결정적 규칙이 주 평가이고, LLM 리뷰는 보조다.** 규칙은 `config/rules/*.yaml`에 ID, 심각도, 파라미터 출처(프로필 키)를 선언한다.

| ID | 검사 | 심각도 | 기준 출처 |
|---|---|---|---|
| COV-001 | 모든 요구사항이 1개 이상 절에 연결되고 초안에서 다뤄짐(TraceRow `verified`) | blocker | 추적표 |
| COV-002 | 모든 정성 평가항목에 대응 절 존재 | blocker | 평가표 |
| COV-003 | 절 제목에 평가항목 용어 포함 | minor | 실무 원칙 |
| TOC-001 | RFP 지정 목차와 장·절 번호·제목 일치 | blocker | 작성지침 |
| TOC-002 | SW사업의 상생협력·하도급 장 존재 | major | 프로필 |
| PAGE-001 | 본문 쪽수 ≤ 상한(제외 항목 반영) | blocker | 작성지침 |
| PAGE-002 | 요약본·발표자료 분량 ≤ 상한 | blocker | 작성지침 |
| PAGE-003 | 절별 쪽수가 예산 ±20% 이내 | minor | 계획 |
| FMT-001 | 본문·표 최소 글자 크기 | blocker | 작성지침 |
| FMT-002 | 용지 크기·방향 | blocker | 작성지침 |
| FMT-003 | 글꼴이 임베딩됐고 허용 목록에 있음 | major | 스타일 정책 |
| SUB-001 | 제출 형식 PDF, 총 용량 ≤ 상한 | blocker | 작성지침·프로필 |
| SUB-002 | 필수 문서구분과 별지 서식이 모두 있음 | blocker | 작성지침 |
| BLD-001 | 본문·표·대체텍스트·머리말·꼬리말에 회사 식별어 | blocker(블라인드 시) | 작성지침 |
| BLD-002 | 등록 로고와 지각 해시가 유사한 이미지 | blocker(블라인드 시) | KB Identity |
| BLD-003 | 파일 메타데이터(PDF Info·XMP, PPTX `docProps`, HWPX 문서정보)와 파일명 | blocker(블라인드 시) | 작성지침 |
| FACT-001 | `[확인 필요]` 자리표시자 잔존 | blocker | P2 |
| FACT-002 | fact 토큰이나 RFP 근거가 없는 숫자 | major | P2 |
| FACT-003 | 유효기간이 지난 fact(인증 만료 등) | major | KB |
| CONS-001 | 절 간 수치 불일치(투입 인력, 일정, 산출물 수) | major | SSOT |
| LANG-001 | 타사 비방·비교 표현 | major | 세부기준(비방 불이익) |
| LANG-002 | RFP 용어집과 다른 명칭 사용 | minor | 용어집 |
| LANG-003 | 근거 없는 최상급·보장 표현("최고", "100% 보장") | minor | 허위 기재 위험 |
| HWPX-001 | OWPML 스키마·무결성(polaris_dvc) | blocker | 출력 품질 |
| REND-001 | 렌더 결과의 넘침, 잘림, 빈 쪽 | major | 출력 품질 |

규칙 기준값이 `provisional` 프로필 값에만 의존하면 심각도를 한 단계 낮춘다(blocker → major). 확인되지 않은 기준 때문에 제출이 막히지 않게 하려는 것이다. 이때 리포트에 "기준 미확인"을 표시한다.

**LLM 리뷰어 (참고용)**

- **세부항목 채점:** 평가표 세부항목별로 5등급 점수, 근거 인용, 개선 제안을 낸다. 보조 축으로 이해력·수행력·관리력(김홍삼·김종수 2017)을 쓴다.
- **60분 훑어보기 테스트:** 요약본과 각 장의 첫 2쪽만 주고, 각 평가 질문의 답을 찾을 수 있는지 확인한다. 찾지 못하면 해당 절에 "핵심 메시지 보강"을 제안한다.
- **한계 고지:** 화면과 리포트에 "LLM 점수와 전문가 점수의 상관은 선행연구에서 약 0.22"임을 표시한다. 이 점수는 게이트에 쓰지 않는다.

### 7.9 render — 출력

**HWPX 본문 (A4 세로)**

- **템플릿과 스타일 매퍼:** 조직별 템플릿 HWPX를 한글에서 스타일을 정의해 만든다. 스타일 ID는 문서마다 다르므로, 생성기는 `header.xml`의 스타일을 **이름으로 조회하는 StyleMapper**로 찾는다.
- **작성:** python-hwpx로 문단, 개조식, 표, 그림, 머리말(사업명), 꼬리말(`- n -`), 목차를 쓴다.
- **번호 체계:** Ⅰ. → 1. → 가. → 1) → 가)

**별지 채우기** (v0.5 구현, 17장)

- 원본 양식을 보존한 채 셀 경로(이름표) 기반으로 값만 채운다(hwpx-mcp-server `fill_by_path` 방식). 레이아웃은 바꾸지 않는다. 표가 모자랄 때만 마지막 빈 행을 같은 서식으로 복제한다.
- HWP5 별지는 HWPX로 변환한 뒤 채우고, 렌더해서 비교 확인한다.
- 서식 영역은 `[별지 제N호서식]` 표지 줄(최상위 문단 또는 쪽 테두리용 1칸 표의 첫 문단)에서 다음 표지 줄 앞까지다. 서식마다 원본을 새로 열어 그 영역만 남기고, 구역 설정(secPr)은 남는 첫 문단으로 옮긴다.
- 값의 출처는 KB(identity·company·실적·인력·인증), RFP(사업명·공고번호·발주기관), 날짜(`--date`), 사람이 준 값(`kb/private/forms.yaml`)뿐이다. 실명은 `kb/private/people.csv`에서 서식에만 넣고 보고서·로그에는 가린다.
- 지정 목차가 가리키는 서식은 블라인드 평가 문서로 보고 회사 식별 정보·실명을 넣지 않는다.
- 서명·날인, 선택 칸(□), 모르는 이름표, 남은 자리표시자는 채우지 않고 점검 결과(FORM-*)로 남긴다.

**PPTX 장표 (요약본·발표·가로형 본문)**

- python-pptx로 마스터 레이아웃 위에 슬롯을 배치한다. 슬롯은 breadcrumb, 평가항목 태그, 요구사항 ID 칩, 거버닝 메시지, 본문 그리드, 하단 요약 박스, 쪽 번호다.
- **회사 템플릿 온보딩:** 비전 모델로 레이아웃과 슬롯 좌표를 추출해 `style.yaml`을 만들고, 사람이 확인한다(dsi 패턴).

**도식** (v0.6 구현, 17장)

- `DiagramSpec`(조직도, 추진체계도, 일정 간트, WBS, 추진 절차, 시스템 구성도)을 SVG로 렌더하고 PNG(200dpi)로 넣는다. EMF는 쓰지 않는다.
- 스펙은 RFP·KB·템플릿에서 결정적으로 만들고, 사람이 `strategy/figures/<id>.json`으로 고친다. 그림을 줄여 넣지 않으므로 그림 속 글자도 RFP 최소 글자 크기를 지킨다.

**PDF 변환 경로**

| 경로 | 구성 | 장점 | 한계 |
|---|---|---|---|
| server(기본) | HWPX → rhwp(MIT, WASM) → PDF, PPTX → LibreOffice → PDF, 선택적으로 H2Orestart(GPL-3.0, 외부 프로세스) | 자동화, 라이선스 안전 글꼴 | 한컴 렌더와 픽셀 단위로 같다는 보장 없음 |
| hancom | Windows 에이전트에서 한글 COM(pyhwpx)으로 열어 PDF 저장 | 충실도 최고, 보고서체 글꼴 사용 가능 | 사용자의 한글 라이선스와 Windows 필요 |
| manual | 생성기는 HWPX·PPTX만 내보내고, 사용자가 직접 PDF로 저장해 다시 올림 | 환경 제약 없음 | 점검만 자동 |

**PDF 후처리 (pikepdf, MPL-2.0)**

- 글꼴 서브셋 임베딩 확인
- 메타데이터(Author/Creator/Producer/Title, XMP) 정리
- 이미지 150~200dpi 다운샘플
- 목차 북마크 생성
- 쪽수·용량 측정

**렌더 검증**

- HWPX 스키마를 검증한다(polaris_dvc).
- 렌더 PNG로 쪽수와 넘침을 확인한다.
- 템플릿 회귀는 쪽 이미지 diff로 잡는다.

### 7.10 package — 제출 패키지

- 나라장터 문서구분별로 파일 세트를 만든다: 정성제안서, 정량제안서, 발표자료, 제안요약서, 하도급 계획서, 기타문서.
- 파일명 규칙을 적용한다. 블라인드면 회사명을 쓰지 않는다.
- 총 용량을 재확인한다.
- **제출 전 점검표(PDF)**를 생성한다. 점검 결과 요약, 게이트 승인 기록, 사람 서명란을 담는다.
- 업로드는 사람이 한다. 점검표에 다음 주의사항을 명시한다.
  - 임시저장 시점에 파일이 암호화된다.
  - 최종 제출 뒤에는 수정할 수 없다.
  - 가격입찰서와 제안서 중 하나라도 빠지면 입찰이 무효가 된다.

### 7.11 변경 관리 — 사전규격, 본공고, 정정공고

1. 새 공고나 새 차수를 감지하면 재파싱한다.
2. DocIR diff와 `rfp.json` diff를 계산한다. 대상은 요구사항 추가·삭제·변경, 배점·분량·마감 변경이다.
3. **영향 분석:** 연결된 절, 추적표 행, 스토리보드 항목을 "재검토 필요"로 되돌린다.
4. 변경 보고서를 만들고 PM에게 알린다.
5. DAG 캐시에 따라 영향받는 하위 단계만 다시 실행한다. 사람이 확정한 값과 충돌하면 자동으로 덮어쓰지 않는다.

사전규격 RFP로 미리 만든 목차와 추적표는 본공고가 나오면 같은 메커니즘으로 갱신된다. 이것이 "조기 착수"를 실현하는 방법이다.

---

## 8. LLM 계층

### 8.1 Gateway 인터페이스

```python
class LLMGateway(Protocol):
    def generate_structured(
        self,
        task: TaskName,               # 아래 작업 목록
        schema: type[BaseModel],      # 응답 스키마(Pydantic)
        context: PromptContext,       # 고정 접두부 + 가변부, 데이터 분류 태그 포함
        policy: CallPolicy,           # 허용 공급자, 모델, effort, max_tokens, 재시도, 시간제한
    ) -> LLMResult: ...
```

`TaskName` 목록은 다음과 같다: `parse.vision_table`, `extract.text_requirements`, `extract.eval_criteria`, `extract.ambiguity`, `plan.map_requirements`, `strategy.storyboard`, `generate.section`, `generate.shorten`, `derive.summary`, `derive.slides`, `derive.script`, `review.evaluator`, `review.skim_test`.

### 8.2 공급자

| 공급자 | 용도 | 비고 |
|---|---|---|
| Anthropic Claude API | 클라우드 기본 경로 | 공식 Python SDK(`anthropic`)로만 호출한다. 기본 모델은 Opus급 최신 모델로 하고, 모델 ID는 `config/llm.yaml`에서 지정한다. 단계별로 오버라이드할 수 있다 |
| 로컬 추론 서버 | 망분리·온프레미스 | Ollama, vLLM 등. 같은 벤치마크로 품질 차이를 측정해 사용자에게 공개한다 |
| 기타 국내 처리 API | 확장점 | 인터페이스만 정의한다 |

- **단계별 모델 선택은 측정으로 정한다.** 대량 추출이나 재점검처럼 가벼운 작업에 하위 모델을 쓰는 것은 13장 벤치마크에서 품질이 유지될 때만 허용한다.

### 8.3 데이터 분류와 라우팅

| 분류 | 예 | 기본 정책 |
|---|---|---|
| public | 공고문, RFP, 공개 첨부 | 모든 공급자 허용 |
| confidential | 회사 KB, 미공개 전략, 단가 | 조직 설정에 따름. 망분리 모드에서는 로컬 전용 |
| personal | 인력 실명·연락처·경력 상세 | 가명화 후 전송, 렌더 단계에서만 복원 |

`PromptContext`의 각 조각에 분류 태그를 붙인다. Gateway는 정책이 허용하지 않는 공급자로 해당 조각을 보내는 호출을 거부한다.

### 8.4 Claude API 사용 원칙

- **구조화 출력:**
  - 추출과 절 생성은 `output_config.format`(JSON Schema)으로 응답 형식을 고정한다.
  - 받은 응답을 Pydantic으로 다시 검증한다.
  - 최신 Opus 계열은 강제 `tool_choice`를 지원하지 않는다. 형식 강제가 필요하면 구조화 출력을 쓴다.
- **근거 위치:**
  - API의 citations 기능은 구조화 출력과 함께 쓸 수 없다(동시에 쓰면 400).
  - 그래서 **기본은 자체 방식**이다. 입력에 DocIR 블록 ID를 넣고, 응답에서 `block_id`와 `quote`를 받아 결정적으로 검증한다.
  - native citations는 자유 질의응답(RFP Q&A) 모드에서만 쓴다.
- **사고와 effort:**
  - adaptive thinking을 쓰고, effort는 작업별로 명시한다. 최신 Opus의 기본 effort는 `medium`이므로 생략하지 않는다.
  - 시작값은 추출·전략·생성·리뷰 `high`, 대량 재점검 `medium`이다. 벤치마크로 조정한다.
- **프롬프트 캐싱:**
  - [전역 고정]과 [프로젝트 고정] 블록(시스템 지침, 문체 가이드, RFP 정규화 텍스트, 평가표, 용어집)을 접두부에 두고 cache breakpoint를 건다.
  - 절별 가변 내용은 그 뒤에 둔다. 타임스탬프나 요청 ID 같은 가변값은 접두부에 넣지 않는다.
  - `usage.cache_read_input_tokens`로 적중을 모니터링한다.
- **배치:**
  - 비대화형 대량 작업은 Message Batches로 돌린다. 예: 전체 절 야간 재점검, 벤치마크 추출. 비용이 50%로 줄어든다.
  - 결과는 `custom_id`로 매칭한다. 결과 순서는 보장되지 않는다.
- **긴 입출력:**
  - 긴 출력은 스트리밍으로 받는다.
  - 1M 컨텍스트라 100~200쪽 RFP도 한 번에 넣을 수 있다. 그래도 위치 추적을 위해 원본 PDF 대신 **블록 ID가 붙은 DocIR 텍스트**를 넣는다.
  - 비전 폴백에서만 PDF 문서 블록을 쓴다(요청당 32MB·600쪽 한도).
- **거부와 오류:**
  - `stop_reason`이 `refusal`인지 확인한 뒤 본문을 쓴다. 서버 측 fallback 옵션을 켠다.
  - 오류는 SDK의 타입별 예외로 구분한다. 429와 5xx는 재시도하고, 400은 즉시 실패시켜 사람 큐로 보낸다.
- **프롬프트 작성 규칙:**
  - 지시는 산문으로 쓰고, 태그는 데이터 구분에만 쓴다.
  - 금지어 목록 대신 후처리 필터를 쓴다.
  - 응답 길이는 목표 글자 수로 명시한다.
  - assistant prefill은 쓰지 않는다.
- **비용 추정:** 지금은 수치를 두지 않는다. M1에서 실제 RFP 5건으로 단계별 토큰(`count_tokens`, `usage` 로그)을 측정해 제안서 1건당 비용 추정을 이 문서에 추가한다.

### 8.5 감사 로그

모든 호출을 `audit/llm_calls.jsonl`에 기록한다. 기록 항목은 task, 공급자, 모델, effort, 입력 조각 해시와 데이터 분류, 토큰·캐시 적중, 출력, 소요 시간, 오류다. `SectionDraft.llm_call_ids`로 각 문장이 어느 호출에서 나왔는지 추적할 수 있다. 허위 기재 문제가 생기면 책임 소재를 가릴 근거가 된다.

---

## 9. 설정 프로필

### 9.1 계층과 출처 표시

```
내장 기본값(config/profiles) < 조직 설정(템플릿·글꼴·팔레트) < 프로젝트 오버라이드 < RFP 파싱값(G1 확정 후 최우선)
```

해석된 모든 값은 출처(계층, 문서 참조나 locator)와 상태를 함께 가진다.

| 상태 | 의미 |
|---|---|
| `verified` | 원문과 대조 완료 |
| `provisional` | 조사 보고서 값, 원문 미대조 |
| `parsed` | 이 공고의 RFP에서 추출해 G1에서 확정 |
| `user` | 조직 또는 사람이 정한 값 |

### 9.2 계약 프로필

| 프로필 | 적용 | 핵심 차이 | 구현 시기 |
|---|---|---|---|
| `national_negotiation_sw` | 국가 협상계약(SW·정보화) | 90:10, 기술 85% 컷오프, 6부문 | M1 기본 |
| `local_negotiation` | 지자체 협상계약 | 80:20 또는 90:10, 합산 70점(SW는 기술 85%) | M4 |
| `competitive_dialogue` | 경쟁적 대화 | 대화로 요구사항이 바뀜 → 요구사항 버전 관리 강화 | M5 |
| `two_stage_spec_price` | 2단계·규격가격 동시입찰 | 규격은 85점 적격 여부만 판정 → 통과형 점검 | M5 |
| `digital_service_catalog` | 디지털서비스 카탈로그 | 수요기관 자체 평가표, 짧은 자유형식 | M5 |
| `defense` | 방위력개선사업 | 방사청 예규, 별도 규칙 세트 | 미정 |

### 9.3 프로필 예시

```yaml
# config/profiles/national_negotiation_sw.yaml (발췌)
profile: national_negotiation_sw
evaluation:
  tech_price_ratio:
    value: [90, 10]
    status: provisional
    ref: "SW사업 기술:가격 배점 관행 — 조사 보고서 2장, 원문 대조 필요"
  tech_quant_qual:
    value: [20, 70]
    status: provisional
    ref: "2025년 공고 예시값(R25BK00879799)"
  tech_cutoff_pct:
    value: 85
    status: provisional
    ref: "협상에 의한 계약체결기준(재정경제부계약예규 제40호) 협상적격 기준"
  max_points_per_area: {value: 30, status: provisional, ref: "SW 기술성 평가기준 별표1"}
  min_points: {value: {상생협력: 5, 하도급계획: 5}, status: provisional, ref: "SW 기술성 평가기준 별표1"}
  qualitative_grades: {value: 5, status: provisional}
outline:
  default_template: [제안개요, 제안업체일반, 전략및방법론, 기술및기능, 성능및품질, 프로젝트관리, 프로젝트지원, 상생협력하도급, 그밖의사항]
  insert_mandatory: [상생협력하도급]
  page_budget: proportional_to_points
requirements:
  id_regex: {value: '^[A-Z]{3}-(?:[A-Z]{2,4}-)?\d{3}$', status: user}
  prefix_chapter_map:
    value: {ECR: 기술및기능, SFR: 기술및기능, SER: 기술및기능, DAR: 기술및기능, COR: 기술및기능,
            PER: 성능및품질, QUR: 성능및품질, SIR: 성능및품질, INR: 성능및품질, TER: 성능및품질,
            PMR: 프로젝트관리, PSR: 프로젝트지원}
    status: user          # 기본 매핑 제안값. G2에서 사람이 확정
  coverage_gate: 1.0
submission:
  format: {value: pdf, status: provisional}
  total_size_limit_mb:
    value: 300
    status: provisional
    ref: "공고별 조건 — 나라장터 「입찰공고문 작성시 이용안내」(2025.4.2) 문구"
  doc_types: [정성제안서, 정량제안서, 발표자료, 제안요약서, 하도급계획서, 기타문서]
  blind_mode: auto        # RFP에 '블라인드/업체정보 삭제본' 문구가 있으면 켬
page_limits:
  main_pages: {value: 100, status: provisional, ref: "관측 범위 20~200, 최빈값"}
  summary_pages: {value: 30, status: provisional}
  presentation: {value: {minutes: 20, qa_minutes: 10, slides: 25}, status: provisional}
  exclude_from_count: {value: [표지, 목차, 간지], status: provisional}
```

전체 기본값은 조사 보고서 "생성기 기본값 프로필" YAML을 초기값으로 옮긴다. 원문 대조표(부록 A)에 있는 항목은 모두 `provisional`로 시작한다. 렌더링 기본값(글꼴, 여백, 팔레트)은 `config/styles/*.yaml`로 분리한다(10장).

---

## 10. 스타일과 템플릿

### 10.1 렌더 경로별 글꼴

| 용도 | hancom 경로(이름 참조만) | server 경로(기본, 라이선스 안전) |
|---|---|---|
| 장·절 제목 | HY헤드라인M | KoPub World 돋움 Bold, 나눔스퀘어 ExtraBold, Pretendard Bold |
| 본문(명조) | 휴먼명조 | KoPub World 바탕, 나눔명조, Noto Serif KR |
| 본문(고딕)·표 | 한컴돋움, 중고딕 | Pretendard, Noto Sans KR, 나눔고딕 |
| 장표(PPTX) | – | Pretendard(GOV), Noto Sans KR. 2종 이내 |

- 저장소와 배포 패키지에는 **SIL OFL 또는 공공누리 제1유형 글꼴만** 넣고, 라이선스 파일을 함께 둔다.
- 한컴 번들 글꼴(HY·휴먼 계열)은 어떤 경우에도 배포하지 않고 hancom 경로에서 이름으로만 참조한다.
- 함초롬체와 Pretendard의 라이선스는 원문을 확인하기 전까지 허용 목록에 넣지 않는다.

### 10.2 HWPX 본문 기본값

RFP 값이 항상 우선한다. 예를 들어 "본문 13pt, 표 12pt"로 지정되면 표 최소 크기는 12pt가 된다.

| 항목 | 기본값 | 근거 |
|---|---|---|
| 용지 | A4 세로 | 다수 RFP |
| 여백 | 위 20, 아래 15, 좌·우 20, 머리말·꼬리말 10 (mm) | 보고서 프로필(관행 추정) |
| 번호 체계 | Ⅰ. → 1. → 가. → 1) → 가) | RFP 관행 |
| 개조식 기호 | □ → ○ → - → · → ※ | 정부 보고서 관행 |
| 글자 크기 | 제목 22, 장 18, 절 16, 항 14(굵게), 본문 13, 표 10.5, 주석 11 (pt) | 보고서체 관행(15pt)을 분량 압박에 맞춰 조정한 제안값 |
| 줄간격 | 본문 160%, 표 130% | 관행 |
| 머리말·꼬리말 | 머리말 `{사업명}`, 꼬리말 `- {쪽} -` | 관행 추정. 블라인드면 업체명 금지 |

### 10.3 PPTX 장표 기본값

| 항목 | 기본값 |
|---|---|
| 판형 | A4 가로(열람용). 발표 전용은 16:9 |
| 슬롯 | breadcrumb, 평가항목 태그, 요구사항 ID 칩, 거버닝 메시지, 본문 그리드, 하단 요약 박스, 쪽 번호 |
| 글자 | 거버닝 메시지 20pt, 본문 11pt(열람용) / 16~20pt(발표용) |
| 색 | 중립 블루 계열 3색 이내, 배경·본문·강조 60:30:10. 공공기관 대상이면 기관 CI색을 강조색으로 쓸 수 있다 |

요구사항 ID 칩과 평가항목 태그의 위치에는 공식 표준이 없다. 위 슬롯 배치는 이 생성기의 자체 규칙이다.

### 10.4 블라인드 스타일

블라인드 모드가 켜지면 다음을 적용한다.

- 로고 슬롯을 제거한다.
- 회사 CI 색을 중립 팔레트로 바꾼다.
- 머리말에는 사업명만 남긴다.
- 파일명에서 회사명을 빼고, 문서 속성(작성자·회사)을 비운다.

### 10.5 템플릿과 자산의 라이선스

저장소 코드는 GPL-3.0이다. 템플릿, 스타일 파일, 샘플 도식은 생성된 제안서에 그대로 복제된다. 그래서 GPL 적용 범위를 두고 논란이 생길 수 있다. 이를 피하려고 `templates/`와 `config/styles/`는 CC0로 분리한다(16장 Q5 확정).

---

## 11. 기술 스택과 저장소 구조

### 11.1 기술 선택

| 영역 | 선택 | 라이선스 | 통합 방식 |
|---|---|---|---|
| 코어 언어 | Python 3.12, uv | – | – |
| 스키마 | Pydantic v2 | MIT | 프로세스 내 |
| CLI / API | Typer / FastAPI(M4) | MIT | 프로세스 내 |
| 저장 | 파일시스템 산출물 + SQLite 인덱스(M1~M3), PostgreSQL(M4) | – | – |
| KB 검색 | BM25 + 임베딩 하이브리드. 임베딩은 로컬 다국어 모델(예: bge-m3) 후보 | 확정 전 확인 | 프로세스 내 |
| HWPX 쓰기 | python-hwpx | Apache-2.0 | 프로세스 내 |
| 별지 채우기 | python-hwpx-automation(hwpx-mcp-server) | Apache-2.0 | 프로세스 내 또는 MCP |
| HWP/HWPX 파싱 | python-hwpx, kordoc | Apache-2.0, MIT | kordoc은 Node 사이드카 |
| HWPX 렌더·PDF | rhwp(`@rhwp/core` 0.9.0) + Chromium(Playwright) | MIT / BSD | Node 사이드카(`sidecars/node`) |
| HWPX 검증 | polaris_dvc | Apache-2.0 | CLI 호출 |
| PPTX / DOCX / XLSX | python-pptx / python-docx / openpyxl | MIT | 프로세스 내 |
| PDF 파싱 | pdfplumber(M1) / opendataloader-pdf(후보) | MIT / Apache-2.0 | 프로세스 내 / 외부 프로세스 |
| PDF 후처리 | pikepdf | MPL-2.0 | 프로세스 내 |
| 선택: HWP→PDF | H2Orestart + LibreOffice | GPL-3.0 / MPL-2.0 | 외부 프로세스 |
| 선택: 고충실도 렌더 | pyhwpx(한글 COM) | MIT | Windows 에이전트 |
| LLM | `anthropic` 공식 SDK, 로컬 추론 서버 어댑터 | MIT 등 | 프로세스 내 |
| 분석 후 이식 대상 | OpenBidKit_Yibiao, BidMaster-Pro, hwpx-docs(AGPL-3.0), H2Orestart(GPL-3.0) 등 | AGPL-3.0 / GPL-3.0 | 11.2절 정책에 따름 |

### 11.2 라이선스 정책

- 이 저장소는 **GPL-3.0**이다. Apache-2.0, MIT, MPL-2.0 의존성은 GPL-3.0 저작물과 결합할 수 있다.
- **GPL·AGPL 프로젝트는 코드를 받아 분석하고, 작동 원리를 파악해 이 프로젝트에 맞게 이식·튜닝한다**(2026-11-17 프로젝트 소유자 결정, v0.1의 "아이디어만 참고"를 대체). 대상은 중국 标书 생성기(OpenBidKit_Yibiao, BidMaster-Pro 등), hwpx-docs, H2Orestart 등이다. 분석 결과는 `docs/analysis/`에 둔다.
  - GPL-3.0 코드(H2Orestart 등)는 이 저장소와 같은 라이선스라 그대로 이식할 수 있다. 원 저작권 표시와 변경 사실을 남긴다.
  - AGPL-3.0 코드는 GPL-3.0 제13조에 따라 결합할 수 있다. 다만 이식한 부분은 AGPL 조건을 유지하므로, 이 프로그램을 웹 서비스(M4의 Web UI·API)로 제공하면 **네트워크 이용자에게 실행 중인 버전의 전체 소스를 제공할 의무**가 생긴다. 이 의무는 수용한다.
  - 이식한 코드는 출처 저장소, 커밋, 원 라이선스를 파일 머리 주석과 `docs/analysis/`에 기록하고, 가능하면 별도 하위 패키지(`rfpgen/vendor_*`)로 모은다. 라이선스 조건이 다른 코드가 섞이는 범위를 추적하기 위해서다.
  - 짧은 알고리즘(차트 XML, 개조식 스타일 값 등)은 이식보다 재구현이 단순하면 재구현한다. 이식 여부는 분석 문서의 권고를 따르되 기능 단위로 정한다.
  - 배포용·암호 문서 복호화처럼 다른 법(저작권법 기술적 보호조치 조항 등)이 걸리는 기능은 라이선스와 별개로 법률 검토 전까지 기본 비활성으로 둔다.
- 라이선스를 명시하지 않은 공개 저장소(다수의 나라장터 PoC)는 저작권자 허락 없이 코드를 복사할 수 없으므로 설계 패턴만 참고하고 출처를 부록 C에 남긴다.
- 사이드카와 외부 프로세스는 표준 입출력·파일로만 통신한다.

### 11.3 저장소 구조

```
auto-rfp-generator/
  docs/
    design.md                 # 이 문서
    adr/                      # 결정 기록(ADR)
  reports/  research_notes/   # 조사 자료
  config/
    profiles/*.yaml           # 조직·프로젝트 오버라이드(내장 프로필은 src/rfpgen/config/profiles/)
    rules/*.yaml              # 점검 규칙(7.8절)
    styles/*.yaml             # 글꼴·여백·팔레트(10장, 별도 라이선스 제안)
    llm.yaml                  # 공급자·모델·effort·데이터 분류 정책
  templates/
    hwpx/                     # 본문 템플릿(스타일 이름 규약 포함)
    pptx/                     # 장표 마스터
  fonts/                      # OFL·공공누리 글꼴 + 각 LICENSE
  src/rfpgen/
    ingest/ parse/ extract/ plan/ strategy/ generate/ derive/
    render/ check/ package/
    kb/ llm/ profile/ store/ audit/
    cli/ api/
    schemas/                  # 6장 Pydantic 모델
  sidecars/
    node/                     # kordoc·rhwp 래퍼
  tests/
    fixtures/                 # 공개 RFP 메타데이터(URL·해시), 합성 샘플
    golden/                   # 렌더·추출 기대 결과
  eval/                       # 벤치마크 스크립트와 라벨(13장)
```

---

## 12. 보안과 컴플라이언스

### 12.1 배포 모드

| 모드 | 구성 | 허용 LLM |
|---|---|---|
| local | 개인 PC 단일 사용자 | 로컬 또는 클라우드(조직 정책에 따름) |
| on-prem | 사내 서버, 망분리 | 로컬만 |
| cloud | 조직 클라우드 | 데이터 분류 정책에 따라 클라우드와 로컬 |

### 12.2 위협과 대응

| 위협 | 대응 |
|---|---|
| 악성 첨부(ZIP 폭탄, XXE, 매크로) | 격리된 파싱 워커, 크기·시간 제한, defusedxml, 매크로 미실행 |
| 프롬프트 인젝션(RFP 속 숨은 지시) | RFP 텍스트는 데이터 구분 태그 안에만 넣는다. LLM에는 외부 전송이나 파일 쓰기 도구를 주지 않는다. 출력은 스키마 검증 후에만 쓴다 |
| 공고 전·미공개 정보 유출 | 데이터 분류 라우팅, 망분리 모드, 감사 로그 |
| 개인정보(참여 인력) | 가명화, 접근 통제, 보관 기한, 렌더 시에만 실명 결합 |
| 허위 기재 | 수치는 KB 근거만, `[확인 필요]`가 남아 있으면 제출 차단, G5 서명 |
| 평가 공정성 | 평가위원 관련 정보 수집·연락 기능을 두지 않는다. 사전접촉은 감점·해촉 사유다 |
| API 키·인증서 | 비밀 저장소에만 둔다. 공동인증서는 다루지 않는다(제출은 사람이 함) |

### 12.3 생성형 AI 사용 고지

생성형 AI로 쓴 제안서를 감점하거나 고지하도록 한 규정은 조사 시점에 확인되지 않았다. 규정 변화를 모니터링하고, 필요하면 고지 문구를 넣는 옵션을 둔다. 조달청이 평가 쪽에 AI를 넣고 있으므로, 공급자 측 AI 사용에 대한 지침이 나올 가능성이 있다.

---

## 13. 품질 평가 계획

### 13.1 데이터셋

- **원천:** 공개 정보화사업 RFP. 2013년부터 공개가 의무화됐다. 나라장터 공고 첨부에서 수집한다.
- **1차 라벨:** 30건(SW 개발 15, 유지관리 10, 기타 용역 5). 라벨 항목은 요구사항 ID 목록, 평가표(항목·배점), 작성지침 필드, 지정 목차다.
- **저장 원칙:** 재배포 라이선스를 확인하기 전에는 원문을 저장소에 넣지 않는다. URL과 해시만 둔다.

### 13.2 지표

| 단계 | 지표 |
|---|---|
| 추출 | 요구사항 ID 재현율·정밀도, 평가표 완전 일치율, 작성지침 필드 정확도, 같은 입력 N회 실행 시 추출 개수 분산 |
| 계획 | 사람이 수정한 요구사항→절 매핑 비율, 목차 지정 준수율 |
| 생성 | 근거 없는 수치 수, `[확인 필요]` 수, 사람 편집 거리, 쪽 예산 준수율 |
| 점검 | 합성 블라인드 누출 탐지율, 분량·형식 위반 탐지율, 오탐률 |
| 렌더 | HWPX 스키마 통과율, 한글에서 열람 성공률, 렌더 경로 간 쪽수 오차 |

### 13.3 LLM 리뷰어 보정

파일럿 PM 채점과 LLM 리뷰어 점수의 상관을 측정해 공개한다. 선행연구의 상관(약 0.22)을 감안해 기대치를 낮게 잡는다.

### 13.4 회귀 테스트

- 골든 픽스처(추출 기대 결과, 렌더 쪽수)
- 템플릿 렌더 스냅샷
- 스키마 버전 마이그레이션 테스트

### 13.5 파일럿

실제 입찰 2~3건에서 사람이 병행으로 작성해 비교한다. 비교 항목은 소요 시간, 누락 건수, 수정량이다. 수주 여부는 지표로 쓰지 않는다.

---

## 14. 로드맵

| 단계 | 내용 | 종료 조건 |
|---|---|---|
| **M0 원문 대조** (선행) | 부록 A 항목을 원문으로 확인하고, 프로필 `status`를 갱신한다. **진행: 1차 완료(2026-11-17) — 컷오프·기술:가격·부문 배점 상한·상생/하도급 최소 배점·등급 수·별지 제5호 목차·PDF·300MB를 원문으로 확인(`docs/analysis/m0-source-check.md`).** 남은 것: 입찰무효(가격입찰서·제안서 미제출) 근거, 지방계약 컷오프 | 컷오프·배점·제출형식 항목이 `verified`이거나, 대조 불가 사유가 기록됨 |
| **M1 RFP 분석기** | 업로드 → parse(HWPX·HWP·PDF·DOCX) → extract → plan. 산출물은 `rfp.json`, 추적표 XLSX, 목차, 쪽수 예산, 질의서 초안. CLI 제공. **진행: 규칙 기반 1차 구현과 LLM 보조 추출 구현 완료(2026-11-17, 실제 API 호출 검증 전).** 남은 것: 실제 API로 품질·비용 측정, 라벨 30건 벤치마크 | 라벨 30건에서 ID 재현율 ≥ 99%, 평가표 완전 일치 ≥ 95%, 비용 측정 결과 문서화 |
| **M2 본문 초안 + HWPX** | KB(YAML/CSV 입력), strategy(스토리보드·자료 요청), generate, HWPX render, check(COV·PAGE·BLD·FACT 규칙). **진행: 1차 구현 완료(2026-11-17) — 골격 모드는 실물 RFP로 확인, LLM 모드는 가짜 공급자로만 검증.** 남은 것: 실제 API로 생성 품질 측정, 한글에서 열람 확인, 과거 제안서 일괄 가져오기, 렌더 기반 쪽수(M3) | 샘플 RFP 3건 end-to-end, blocker 0건, 한글에서 열람 확인 |
| **M3 장표·파생·제출 패키지** | PPTX 템플릿·슬롯, 요약본·발표자료·대본, 별지 채우기, 도식 렌더, PDF 파이프라인, package. **진행: 1차 구현 완료(2026-11-17) — 장표 슬롯·대본(골격)·PDF 파이프라인·제출 패키지·정확한 쪽수 점검, 별지 서식 찾기·채우기와 문서구분별 묶음(합성 서식으로만 검증), 도식 자동 렌더(조직도·추진체계·일정·WBS·절차·시스템 구성도).** 남은 것: 실제 공고 HWP 서식으로 별지 채우기 검증, LLM 도식 스펙, LLM 대본·예상 답변, 회사 PPTX 템플릿 온보딩, 이미지 다운샘플·PDF 북마크 | 문서구분별 제출 세트 생성, 용량·메타데이터 점검 통과 |
| **M4 연동·협업** | 나라장터 OpenAPI 감시(사전규격), 정정공고 자동 감시·재실행(diff 엔진은 M1에 구현), Web UI 검토 흐름(**AGPL §13에 따른 '소스 코드' 제공 링크 포함**), LLM 리뷰어, PostgreSQL, 지자체 프로필 | 사전규격→본공고 갱신 시나리오 통과, 다중 사용자 게이트 운영 |
| **M5 보안 배포·확장** | on-prem 패키지, 로컬 LLM 품질 리포트, 경쟁적 대화·2단계·카탈로그 프로필, 벤치마크 공개 | 망분리 환경 설치 문서, 공개 벤치마크 v1 |

M1만으로도 단독 가치가 있다. 시장의 체크리스트·대응표 도구(프리세일즈 CheckAI 등)와 같은 층이므로, 생성 기능 없이도 파일럿을 시작할 수 있다.

---

## 15. 위험과 대응

| 위험 | 영향 | 대응 |
|---|---|---|
| 제도 수치 오류(원문 미대조) | 잘못된 기준으로 점검하거나 생성 | M0 대조, `provisional` 표시, RFP 파싱값 우선, provisional 기준 규칙의 심각도 하향 |
| HWP5 파싱 품질 | 요구사항·평가표 누락 | 이중 파싱, 비전 폴백, G1 검토, 회귀 테스트 |
| HWPX 렌더 충실도(한컴과의 차이) | 쪽수 초과, 레이아웃 깨짐 | 세 가지 렌더 경로, 렌더 기반 쪽수 측정, hancom 경로 옵션 |
| LLM 환각·수치 날조 | 허위 기재 감점·실격 | 수치는 fact 토큰만, FACT 규칙, 사람 게이트 |
| LLM 추출 불안정 | 요구사항 누락 | 규칙 우선, 2회 교차 실행, 총괄표 대조 |
| 정보 유출 | 신뢰 상실, 계약 위험 | 데이터 분류 라우팅, 망분리 모드, 감사 로그 |
| 조달청 API 변경·첨부 다운로드 실패 | 수집 중단 | 어댑터 계층, 수동 업로드 상시 지원 |
| 라이선스 위반 | 배포 제약 | 격리 정책(11.2절), 글꼴 허용 목록, 의존성 라이선스 CI 검사 |
| 과의존(검토 없이 제출) | 품질·책임 문제 | 게이트, 초안 워터마크, 점검표 서명 |
| 효과 검증 불가(점수 비공개) | 제품 가치 설명 어려움 | 시간·누락·형식 지표로 가치 측정, 파일럿 병행 비교 |

---

## 16. 결정 사항

2026-11-17 프로젝트 소유자가 v0.1의 제안 기본값을 모두 확정했다. Q8은 같은 날 추가된 결정이다.

| # | 질문 | 확정 | 이유 |
|---|---|---|---|
| Q1 | 첫 대상 사업 범위 | **국가 협상계약의 SW 개발·유지관리** | 요구사항 ID·평가부문 표준이 가장 뚜렷하고 공개 RFP가 많다 |
| Q2 | 첫 출력 형식 | **HWPX 세로 본문을 먼저(M2), PPTX 장표는 M3** | 별지·정량서식이 HWP 기반이고, HWPX 출력이 경쟁 도구 대비 차별점이다 |
| Q3 | 배포 모드와 LLM | **local 단일 사용자 + Claude API 기본.** 로컬 LLM은 M2부터 인터페이스, M5에서 품질 리포트 | 빠른 검증과 망분리 요구의 균형 |
| Q4 | UI | **M1~M3는 CLI와 HTML/XLSX 리포트, Web UI는 M4** | 핵심 가치(추출·추적·점검)를 먼저 검증한다 |
| Q5 | 템플릿·자산 라이선스 | **코드는 GPL-3.0 유지, `templates/`·`config/styles/`는 CC0로 분리** | 생성 문서에 GPL 논란이 생기지 않게 한다 |
| Q6 | KB 입력 방식 | **YAML/CSV + 과거 제안서(HWPX/PPTX/PDF) 일괄 가져오기** | 초기 도입 부담을 낮춘다 |
| Q7 | 원문 대조(M0) 수행 환경 | **law.go.kr·pps.go.kr·g2b.go.kr·data.go.kr에 접근할 수 있는 환경에서 수행** | 조사·구현 세션에서는 이 사이트들이 차단돼 있었다 |
| Q8 | GPL·AGPL 프로젝트 활용 | **코드를 받아 분석하고 작동 원리를 파악해 이 프로젝트에 맞게 이식·튜닝** (11.2절) | 중국 标书 생성기 등은 실격사유 점검·평가기준 해석이 이미 검증돼 있다. AGPL 이식에 따른 웹 서비스 소스 공개 의무는 수용한다 |

## 17. 변경 이력

### v0.2 (2026-11-17) — 결정 확정과 M1 구현 반영

- **16장:** Q1~Q7 확정, Q8(GPL·AGPL 코드 이식) 추가. 11.2절 라이선스 정책을 그에 맞게 바꿨다.
- **M1 구현 결정:**
  - **추출은 결정적 규칙만으로 구현했다.** LLM 보조 패스(7.3절 B)는 M1 후속 작업으로 미뤘다. 규칙만으로 공개 RFP 실물에서 평가표 100점·요구사항 219건을 뽑았고, LLM이 필요한 곳(ID 없는 서술형 요구, 표가 그림인 문서)이 분명해진 뒤 붙이는 편이 낫다고 판단했다.
  - **PDF 파서는 pdfplumber(MIT)를 쓴다.** opendataloader-pdf는 Java 런타임이 필요해 M1에서는 미뤘다. pdfplumber가 셀을 찾지 못한 칸(경계선을 생략한 표)은 격자 좌표로 다시 읽어 채운다.
  - **요구사항 ID 정규식은 일련번호 3~4자리를 허용한다:** `[A-Z]{3}-(?:[A-Z]{2,4}-)?\d{3,4}`.
  - **내장 프로필은 패키지 안**(`src/rfpgen/config/profiles/`)에 두고, 조직·프로젝트 오버라이드는 `--profile` YAML로 준다.
  - **추적표 XLSX는 6.4절의 8개 열 순서를 지킨다.** 그 뒤에 `연결 목차 | 연결 근거 | 상태` 3개 열을 덧붙였다.
- **공개 RFP 실물(404쪽 PDF)에서 배운 점과 추가한 점검:**
  - **숫자가 도형 글자인 PDF가 있다.** HWP→PDF 변환에서 숫자·영문 일부가 글자가 아니라 곡선으로 남아 분량("페이지 이내"), 용지("지 규격"), 일부 배점 문구의 숫자가 사라진다. 이런 문장은 값을 지어내지 않고 `GUIDE-PAGE-UNREADABLE` 오류로 보고해 G1에서 사람이 입력하게 했다.
  - **선언 요구사항 수와 대조한다.** RFP의 "ID 부여규칙 | 요구사항수" 표를 읽어 접두어별 추출 수와 비교한다(`REQ-COUNT-MISMATCH`). 실물에서 ECR 23건 누락(ID가 글자로 들어 있지 않음)을 이 점검으로 찾았다.
  - **RFP 쪽 오류도 질의서 후보가 된다.** 표에 없는 접두어가 알려진 접두어와 한 글자 차이면 RFP 오타로 본다(`REQ-ID-TYPO`, 실물의 `SRF-EHR-008`). 다른 곳에서 참조만 되고 정의서가 없는 ID는 `REQ-UNKNOWN-REF`로 보고한다.
  - **요구사항 정의서는 한 행에 항목명-값 쌍이 둘 이상일 수 있다**("요구사항 분류 | 기능 | 요구사항 ID | SFR-…"). 그래서 항목명 사전 기반으로 읽는다.
  - **평가표가 쪽 넘김으로 잘리면** 다음 쪽 표의 부문 칸이 빈다. 이때는 앞 부문을 이어받는다.
  - **'계량/비계량'은 '정량/정성'과 같은 뜻으로 처리한다.**
  - **지정 목차 표의 별지 번호로 제출 서식 목록을 만든다.**
  - **작성지침 문장은 제안·작성·분량 문맥에서만 읽는다.** 요구사항 정의서 표 안의 문장(예: "pdf 업로드 기능", "A3 용지 인쇄")은 제외한다.
- **외부 코드 분석과 M1 이식:** `docs/analysis/hwpx-rendering-tools.md`(hwpx-docs, H2Orestart), `docs/analysis/chinese-bid-generators.md`(중국 标书 생성기 4종, 고정 커밋·LICENSE 확인). 분석 문서 5장의 결정적 제안을 M1에 재구현했다.
  - **평가항목/평가규칙 분리**(OpenBidKit): 등급 정의·감점·가점·산식은 `EvaluationTable.rules`로, 제안서가 답할 질문만 `EvalItem.criteria`로 둔다.
  - **입찰무효·평가제외·감점 사유**(OpenBidKit 无效投标/废标项): 원문 명시(`stated`)와 프로필 권고(`suggested`, G1 채택 대상)를 나누고, 관련 점검 규칙(PAGE·FMT·BLD·SUB·FACT·LANG)을 붙인다. 위반이 '제외·무효'로 규정되면 작성지침 값에 근거를 메모한다. 입찰참가자격 줄도 모은다.
  - **작성지침 극성·누락 점검**(OpenBidKit valueIssue·findOmissions): "블라인드 평가를 실시하지 않음" 같은 부정을 먼저 판정하고, 주제 문구는 있는데 값이 빈 경우 `GUIDE-OMISSION`으로 보고한다.
  - **지정 목차 작성 방식 태그**(OpenBidKit content_mode): 자유서식·별지서식·대응표·증빙첨부와 별지 번호.
  - **쪽당 글자 수**(OpenBidKit pageMetrics): 본문 폭·높이·글자 크기·줄간격으로 이론 상한(기본 1,184자)과 실효값을 구해 절별 목표 글자 수를 낸다.
  - **RFP diff 엔진**(BidPilot-AI): 분석 문서 권고에 따라 M4에서 M1로 앞당겼다. 항목 단위 비교, 영향 절, 재실행 단계, 고위험 변경 확인 목록을 낸다. 계획 산출물은 `plan/v{n}/`에 버전별로 보관한다.
  - 이식하지 않은 것: OpenBidKit의 기본 사실 모드 `fabricate`(자료가 없으면 값을 지어냄), BiaoShu의 근거 없는 고정 수치 문구, BidMaster의 가격 안전구간 규칙, BidPilot의 3.6만 자 이후 입력 절단.
  - LLM 프롬프트(분석 문서 6장 한국어 초안)는 LLM 계층을 붙일 때 이식한다.
- **LLM 보조 추출(7.3절 B·C, 8장) 구현:**
  - `rfpgen/llm/`: 공급자 추상화 게이트웨이(데이터 분류 정책 — 현재 공개 RFP만 전송), Claude API 공급자(공식 SDK, 구조화 출력, 시스템 지침·RFP 발췌 캐시 지점, effort 명시, 서버 측 fallback `default`, 거부·잘림·인증 오류 처리, 스트리밍), 엄격 JSON Schema 변환, 근거 검증기, 키워드 창 발췌, 감사 로그(`audit/llm_calls.jsonl`).
  - **모델 ID는 저장소에 고정하지 않는다.** `--llm-model` 또는 `RFPGEN_LLM_MODEL`, 없으면 Models API에서 가장 최근 Opus 계열을 고른다.
  - 과제 3종: 작성지침 빈칸 채우기(`guideline`), 무효·감점 사유와 참가자격 보강(`compliance`), ID 없는 서술형 요구사항(`text_requirements`, X-0001…). 뒤의 둘은 같은 입력으로 2회 실행해 한쪽에만 나온 항목을 불안정(신뢰도 0.5)으로 표시한다.
  - **근거 검증을 통과한 값만 받는다.** 블록 ID가 보낸 발췌 안에 있고, 인용문이 그 블록에 실제로 있어야 하며, 숫자 값은 그 숫자가 인용문에 적혀 있어야 한다. 숫자가 도형 글자인 PDF에서 LLM이 관행 값(예: 100쪽)을 넣어도 버린다. 결정적 추출값과 다르면 규칙 값을 유지하고 충돌로 보고한다.
  - 과제가 실패(거부·인증·네트워크)해도 결정적 결과와 나머지 과제는 그대로 낸다.
  - **AGPL 번안 분리:** OpenBidKit·BidMaster-Pro 프롬프트를 번안한 지시문은 `src/rfpgen/_third_party/agpl/openbidkit_yibiao/`에 SPDX `AGPL-3.0-only`, 원저작권, 커밋, 변경 사실과 함께 두고, 원 LICENSE·NOTICE를 `third_party/`에 보관한다. 서술형 요구사항 지시문과 시스템 지침은 자체 작성(GPL-3.0)이다. 배포용·암호 HWP 복호화는 법률 검토 전까지 비활성이며, 그런 문서는 한글에서 PDF로 저장해 올리도록 안내한다.

---

### v0.3 (2026-11-17) — M2 본문 초안 1차 구현

- **KB(6.5절):** `rfpgen kb init`이 만드는 폴더 형식(company.yaml의 identity·facts, projects.csv, people.csv, certifications.csv, content/*.md). 인력은 역할·등급·경력만 두고 실명·연락처는 넣지 않는다. `rfpgen kb check`는 ID 중복, 설명 속 숫자, 유효기간 만료, 블라인드 사전 누락을 본다.
- **수치 값은 LLM에 보내지 않는다(원칙 P2·P7 강화).** LLM은 `{{fact:F-001}}`, `{{kb:P-001.amount_krw}}` 토큰만 쓰고 값은 코드가 넣는다. KB에 없는 토큰은 `[확인 필요]`로 바뀌어 FACT-001 blocker가 된다.
- **데이터 분류 `internal` 추가(8.3절):** KB의 ID·설명·재사용 문단은 `internal`이다. 기본은 공개 RFP만 보내고, `--llm-share-kb`를 줄 때만 `internal`을 허용한다. 공급자가 허용하지 않는 분류를 보내려 하면 게이트웨이가 막고 그 단계는 골격으로 대신한다.
- **두 모드:** LLM 없이도 평가 질문·요구사항·필요 근거·재사용 후보를 자리표시자와 함께 배치한 **작성용 골격**을 낸다. LLM 모드는 스토리보드(win theme 3개, 절별 거버닝 메시지·핵심 내용·필요 근거)와 절 본문을 생성한다. 절 호출은 RFP 요약(+KB 카탈로그)을 같은 접두부로 써서 캐시를 공유하고, 배점이 큰 절부터 쓴다.
- **G3·G4:** `strategy/storyboard.json`이 있으면 다시 만들지 않고 사람이 고친 내용을 쓴다(`--refresh-storyboard`로 새로 만듦). 절 초안은 `sections/{id}.vN.json`으로 버전을 쌓고 `--section`으로 일부만 다시 쓴다.
- **자료 요청서:** 스토리보드의 필요 근거 중 KB에 없는 것을 `out/trace_draft.xlsx`의 자료 요청서 시트로 낸다. 실적·인력·인증 근거는 그 종류의 KB 항목에 근거의 고유한 낱말이 있어야 있는 것으로 본다.
- **HWPX 렌더(7.9절):** python-hwpx 위에 보고서체 스타일(`src/rfpgen/config/styles/report.yaml`, CC0)을 얹었다. 제목 번호와 개조식 기호는 글자로 넣고 기호 폭만큼 내어쓴다. 글꼴은 모든 언어에 지정하고, 거버닝 메시지는 음영 상자로, 절마다 요구사항 대응표를 붙인다. 머리말은 사업명, 꼬리말은 `- 쪽 -`, 표지에는 숨긴다. RFP 최소 글자 크기가 스타일보다 크면 그 값으로 올린다. 렌더에는 회사 식별 정보를 넣지 않고, 새 문서 메타데이터는 작성자가 비어 있다.
- **점검(7.8절, M2 범위):** COV-001·002, TOC-001, PAGE-001(글자 수 기반 추정, M3 렌더로 확정)·PAGE-003, FACT-001·002·003, BLD-001·003(파일 정보·파일명 포함), LANG-001·003, HWPX-001(python-hwpx 검증 오류는 blocker, 패키지 경고는 정보). 결과는 `checks/{run}.json·md`.
- **공개 RFP 실물(404쪽)로 확인한 것:** 골격 모드로 37개 절, 요구사항 219건 대응표, HWPX 검증 오류 0건, 약 2초.

### v0.4 (2026-11-17) — M3 장표·PDF·제출 패키지 1차 구현

- **PDF 경로(7.9절) 실제 구성:**
  - HWPX → PDF: Node 사이드카(`sidecars/node/hwpx_to_pdf.mjs`)가 `@rhwp/core`(MIT, 0.9.0)로 쪽별 SVG를 만들고 Chromium(Playwright)으로 벡터 PDF를 인쇄한다. rhwp의 쪽 나눔으로 **정확한 쪽수**를 얻는다.
  - PPTX → PDF: LibreOffice headless. 변환마다 별도 사용자 프로필·캐시 폴더를 쓴다.
  - H2Orestart(GPL)와 한글 COM 경로는 아직 붙이지 않았다.
- **글꼴:** 서버에는 OFL 글꼴(`fonts-noto-cjk`)을 설치하고, 문서 글꼴 이름(Google Fonts 명 `Noto Sans KR`)을 설치 이름(`Noto Sans CJK KR`)에 `@font-face local()` 별칭으로 잇는다(`--font-alias`로 바꿀 수 있음). Chromium은 CJK CFF 글꼴을 Type3(ToUnicode 포함)로 넣으므로 글자 검색·추출은 된다. 글꼴 파일은 저장소에 넣지 않는다.
- **후처리(pikepdf, MPL-2.0):** 작성자·제작 도구·날짜·XMP를 지우고 제목만 남긴다(BLD-003). 쪽수·용량·글꼴 임베딩을 잰다. 이미지 다운샘플과 북마크는 남은 작업이다.
- **장표(10.3절):** python-pptx로 요약본(A4 가로)·발표자료(16:9)를 만든다. 슬롯은 breadcrumb·평가항목 태그·요구사항 ID 칩(8개 + 나머지 수)·거버닝 메시지·본문(개조식 3단계)·우측 표 또는 핵심 상자·하단 요약·사업명 꼬리·쪽 번호다. 동아시아 글꼴 슬롯까지 지정하고, 문서 속성(작성자 등)은 비운다. 요약본은 절 수가 상한을 넘으면 장 단위로 묶는다. 발표자료 장 수는 RFP 발표 쪽 상한, 없으면 발표 분 × 1.2, 없으면 25장이다.
- **대본·예상 질문:** 발표자 노트와 `out/script.md`에 거버닝 메시지·핵심 항목으로 만든 대본을 넣는다. 예상 질문은 정성 평가 질문과 `[확인 필요]`가 남은 절에서 뽑는다. LLM 대본은 남은 작업이다.
- **제출 패키지(7.10절):** `submission/01_정성제안서.pdf`, `02_제안요약서.pdf`, `03_발표자료.pdf`(회사명 없는 이름), `manifest.json`, `제출전점검표.md`(사람 확인 항목: blocker 0, 문서구분 지정, 정량·별지·하도급 별도 준비, 가격입찰서 별도 제출, 임시저장 암호화·최종 제출 후 수정 불가, 쪽마다 육안 확인).
- **점검:** PAGE-001을 렌더 쪽수로 확정한다(표지 제외 규칙 반영). 이 밖에 PAGE-002(요약본·발표 쪽수), SUB-001(총 용량), SUB-002(필수 문서구분), FMT-003(글꼴 임베딩), BLD-003(PDF 파일 정보·파일 이름)을 본다. 초안 단계 점검 결과를 이어 붙여 `checks/package-*.md` 하나로 본다.
- **공개 RFP 실물(404쪽, 골격 모드)로 확인한 것:** 정성제안서 29쪽(글자 수 추정 29.8쪽), 요약본 11장(장 단위), 발표자료 12장, 총 0.81MB, 약 10초.

### v0.5 (2026-11-17) — 별지 서식 찾기·채우기

- **명령:** `rfpgen forms 프로젝트 --kb kb [--date YYYY-MM-DD]` → `out/forms/별지NN_제목.hwpx`, `out/forms/forms.json|md`, `checks/forms-*.json|md`. `rfpgen package`는 채운 서식을 문서구분별로 묶어 `01-1_정성제안서_별지.pdf`, `04_정량제안서.pdf`, `05_하도급계획서.pdf`, `06_기타문서.pdf`를 만들고 별지 점검을 이어 붙인다.
- **서식 찾기(`forms/locate.py`):** analyze가 보관한 원본(raw/) 중 HWPX·HWP에서 표지 줄을 찾는다. 본문 속 언급("별지 제3호 서식에 따라")은 표지 뒤 조사·동사와 줄 길이로 거르고, 서식 목록(표지 줄만 이어진 목차)은 내용이 없는 영역이라 버린다. 같은 번호가 여러 번 나오면 내용(표·문단)이 많은 쪽을 쓴다. 표지 없는 첨부 파일이 '별지서식'으로 분류되면 파일 전체를 서식 하나로 본다.
- **채우기(`forms/fill.py`, hwpx-rendering-tools 분석 6장의 규칙을 다시 구현):**
  1. 이름표 칸: 이름표(20자 이하) 오른쪽 칸이 비었으면 그 칸, 아니면 아래 칸(아는 이름표만). 빈칸 판정은 공백·`○`·`_`·점·`(인)`·단위 접미사·날짜 뼈대(`    .   .   .`, `년 월 일`)를 빈칸으로 본다.
  2. 목록 표: 머리글 어휘로 실적(사업명·발주기관·계약금액 …), 인력(성명·등급·경력 …), 인증(인증명·인증번호 …)을 가린다. 2행 머리글(사업기간 아래 시작·종료)과 단위(`계약금액(백만원)`, `경력(년)`)을 읽고, 빈 행이 모자라면 python-hwpx `insert_rows(blank=True)`로 늘린다(기본 상한 20행). 바로 아래 '합계' 행에 금액 합을 넣는다. 머리글 둘에 빈 행 하나뿐인 표([사업명|발주기관])는 목록이 아니라 이번 사업 정보 칸으로 본다.
  3. 문단: `상    호 :`, `대 표 자 :      (인)` 같은 이름표-쌍점 빈칸과 날짜 줄(최상위 문단·1~2칸 표 안만). 앞에 제출자 역할어(신청인·서약자 …)가 붙으면 떼고 찾되, 그 밖의 앞말("하도급 업체")은 떼지 않는다 — 다른 회사 칸에 우리 값을 넣지 않기 위해서다.
  - 글자는 빈칸 구간만 바꾸고 값은 빈칸 쪽 글자 모양을 따른다. 바뀐 문단의 줄 배치 캐시는 python-hwpx가 저장할 때 지운다.
- **문서구분 추정:** 하도급 → 하도급계획서, 지정 목차가 가리킴 → 정성제안서(블라인드), 실적·인력·인증·신용 등 → 정량제안서, 그 밖 → 기타문서. `project/forms.yaml`의 `doc_types`·`skip`으로 바꾼다.
- **점검(FORM-*):** UNFILLED(모르는 이름표·KB 값 없음, major), LIST(빈 행 없음·자료 없음·행 추가 실패·못 채운 열·건수 확인), NAMES(실명 없음·블라인드), BLIND(식별 정보 생략), BLIND-LEAK(블라인드 서식에 식별 표기, blocker), PLACEHOLDER(○○·XXX·___ 잔존), SEAL(서명·날인 필요), CHECKBOX(□ 선택 칸), DATE(넣은 날짜 확인), MISSING(작성지침·지정 목차가 요구한 서식을 HWP·HWPX에서 못 찾음), OPEN(첨부 열기 실패).
- **KB 확장:** `company.yaml`에 `company`(사업자등록번호·법인등록번호·주소·전화·팩스·이메일·홈페이지·설립일·자본금·종업원 수)를 더했다. LLM에는 보내지 않는다. `kb/private/`(people.csv 실명, forms.yaml 사람이 준 값)은 저장소에 올리지 않도록 `.gitignore`에 넣었다.
- **한계:** 합성 서식(이름표 표·목록 표·쪽 테두리 표·서명 줄)으로만 검증했다. 실제 공고 HWP 서식은 이 세션에서 받지 못해(나라장터 접속 차단) 확인하지 못했다. 체크박스 선택, 서명 이미지, 증빙 첨부, 날인본 교체는 사람이 한다.

### v0.6 (2026-11-17) — 도식 자동 렌더

- **흐름:** 스토리보드 절별 도식 계획(`SectionPlan.figures`) → 스펙(`diagram/build.py`) → 절 초안의 `figure` 블록 → SVG(`diagram/svg.py`) → PNG 200dpi(`sidecars/node/svg_to_png.mjs`, Chromium 한 번 실행으로 여러 장) → HWPX 본문(가운데 정렬 그림 + `[그림 n] 제목` 캡션)과 PPTX 장표(본문 오른쪽 60%).
- **종류와 근거:**
  - 추진 일정(gantt): RFP 사업기간(`N개월`, `YYYY.M ~ YYYY.M`, `N일`)으로 칸 수를 정하고, 사업 유형 템플릿(구축·유지관리·컨설팅)의 단계 비율을 반 달 단위로 맞춘다. 착수·중간·완료보고 이정표. 기간을 못 읽으면 6개월로 두고 FIG-002로 알린다.
  - 조직도(org): KB 인력의 역할별 팀(등급·경력 요약), PM과 품질보증(QA) 지원 조직. 절 제목에 '체계'가 있으면 추진체계도로 보고 발주기관(RFP)과 감리(RFP에 '감리'가 있을 때만)를 위에 점선으로 둔다. 인력이 없으면 일반 팀에 `[확인 필요: 투입 인력]`을 넣는다.
  - WBS·추진 절차(wbs·flow): 사업 유형 템플릿의 단계·활동·산출물.
  - 시스템 구성도(layers): 사용자 층(RFP의 모바일·포털·관리자·외부기관 언급), 업무 서비스(SFR 이름), 연계(SIR), 데이터(DAR), 인프라(ECR·HWR·SWR, 없으면 일반 구성 + FIG-002), 보안(SER, 오른쪽 세로 띠).
  - 회사명·실명은 넣지 않는다. 도식 글은 블라인드·자리표시자 점검(`all_text()`)에는 들어가고, 수치 근거 점검(FACT-002)과 글자 수 추정에서는 빠진다(쪽수 추정은 그림 높이로 따로 센다).
- **배치 규칙(`config/diagrams/default.yaml`, CC0):** 절 제목(없으면 평가항목 이름)의 낱말로 고르고 종류마다 상한(조직도 2, 나머지 1)까지만 넣는다. 맞는 절이 없으면 일정·조직도는 '프로젝트관리' 장, 구성도는 '기술및기능' 장의 첫 절에 넣는다. 사람이 `storyboard.json`의 `figures`를 고치면 그대로 따른다. 도식 기능 전에 만든 스토리보드에는 자동 배치를 채운다.
- **SVG 배치:** 외부 그래프 도구 없이 종류별 고정 배치(나무: 뿌리→가로 1단계→세로 2단계 목록, 절차: 화살표 단계 + 산출물 상자, 일정: 표 격자 + 막대·마름모, 구성도: 층 띠). 폭은 본문 폭(170mm), 글자는 표 글자 크기 이상. 글자 폭은 동아시아 문자 폭(east_asian_width)으로 어림해 줄을 나눈다.
- **사람 수정 루프:** 자동 스펙은 `strategy/figures/<id>.auto.json`에 남는다. `<id>.json`으로 복사해 고친 뒤 `rfpgen figures 프로젝트`를 실행하면 절 초안은 그대로 두고(LLM 호출 없음) 도식만 바꿔 새 판으로 저장하고 본문 HWPX·점검을 다시 만든다.
- **점검:** FIG-001(그림 변환 실패로 자리표시 상자, major), FIG-002(템플릿·기간 가정, minor), FIG-003(쪽보다 커서 줄임 — 글자가 최소 크기보다 작아질 수 있음, major).
- **M1 수정:** 공고 기본정보에서 표 머리글('비고', '구분' 등)을 값으로 읽던 문제를 고쳤다(공개 RFP 실물에서 발주기관이 '비 고'로 읽혔음).
- **공개 RFP 실물(404쪽)로 확인:** 도식 5개(수행 조직·추진 절차·추진 체계·시스템 구성도·일정)가 본문 30쪽 PDF와 요약본·발표자료에 들어갔다. 사업기간 숫자가 도형 글자라 일정은 6개월 가정으로 만들어졌고 FIG-002로 보고됐다. 초안 2.6초, 장표·패키지 약 10초.
- **남은 것:** LLM이 절 내용에 맞춰 도식 스펙을 제안(검증 후 채택), 시스템 구성도의 연결선, 회사 템플릿 색·도형 반영.

### v0.7 (2026-11-17) — 결함 수정, M0 원문 대조(1차)

- **요구사항 ID 규칙:** 가운데 마디가 숫자인 ID(`ECR-01-001`)를 읽도록 넓혔다. 공개 RFP 실물에서 장비구성 요구사항 23건이 빠지던 문제(219/242 → 242/242).
- **사이드카:** `package.json`에 Playwright 버전을 고정하고, 변환기 확인에 Playwright를 넣었다. `RFPGEN_CHROMIUM_PATH`로 다른 Chrome을 지정한다. `rfpgen doctor [--full]`이 설치 상태를 한 번에 점검한다(API 키는 있는지만 보고 값은 출력하지 않음).
- **M0 원문 대조:** 법제처 국가법령정보센터의 현행 행정규칙(협상에 의한 계약체결기준, 소프트웨어 기술성 평가기준 지침, 행정기관 및 공공기관 정보시스템 구축·운영 지침, 조달청 협상에 의한 계약 제안서평가 세부기준)과 별표·별지로 프로필 수치 9개를 `verified`로 바꿨다. 근거 조항은 각 값의 `ref`와 [대조 기록](analysis/m0-source-check.md)에 있다.
  - 기본 목차(`outline.default_template`)의 절 이름을 조달청 세부기준 별지 제5호서식과 같게 고쳤다(예: '시스템 장비구성 요구사항', '관리방법론'). '제안업체 일반' 절도 별지 Ⅰ. 일반현황(입찰자 일반현황, 수행조직 및 업무분장, 핵심투입인력 및 이력사항)과 같게 했다.
  - 권고 무효·감점 사유(`compliance.suggested`)에 항목별 근거(`basis`)를 달고 비방(0.1점)·사전접촉(5점)·허위 처리 문구를 원문대로 고쳤다. 입찰무효(가격입찰서·제안서 미제출)와 임시저장 암호화는 원문을 찾지 못해 미확인으로 남겼다.
  - 이제 기준값이 `verified`이므로 SUB-001(용량) 등은 RFP 값이 없을 때도 심각도를 낮추지 않는다.
- **도식 배치:** 조직도는 추진체계도와 수행조직도를 하나씩만 넣는다(절 이름이 바뀌어 수행조직·핵심투입인력 두 절에 같은 조직도가 들어가던 문제).
- **새로 찾은 의무(기능 후보):** 조견표(목차·평가항목별 쪽수) 시스템 등록(조달청 세부기준 제6조의2③), PM 직접 발표(행안부 지침 제20조), 비방 관련 서약서·확인서(별지 제21·22호), SW 평가기준 가점 항목(제4조④).

### v0.8 (2026-11-17) — 승인 게이트, CI, LLM 전용 키

- **게이트(3장):** `rfpgen gate`가 G1~G5 승인을 `project.yaml`에 기록한다(승인자·시각·메모·근거 지문). 근거는 G1 최신 `rfp.vN.json`, G2 목차·쪽수 예산·요구사항→절 매핑, G3 스토리보드, G4 절별 판, G5 최신 패키지 점검이다. 근거가 바뀌면 승인은 '재확인 필요'가 되고 뒤 게이트도 무효로 본다. 승인 조건: G2는 미연결 요구사항 0건, G5는 패키지 점검 blocker 0건, 모든 게이트는 앞 게이트 승인. `--force`는 조건을 건너뛰되 `forced_over`로 기록한다.
  - 설계 표의 "통과하지 않으면 다음 단계 진입 불가"는 아직 막지 않고 알리기만 한다: 패키지 점검의 GATE-001(major)과 제출 전 점검표의 G5 항목. G4 미승인 절의 "초안" 워터마크도 아직 없다.
- **CI:** `.github/workflows/test.yml` — 파이썬 3.12·3.13 단위 테스트(변환기 없이, 렌더 테스트는 건너뜀)와 렌더 경로(글꼴·LibreOffice·Node 사이드카·Playwright Chromium 설치 후 `rfpgen doctor --full`과 전체 테스트).
- **LLM 인증:** rfpgen 전용 키 `RFP_ANTHROPIC_API_KEY`를 읽고 공식 API 주소로 보낸다. 실행 환경에 다른 도구용 `ANTHROPIC_BASE_URL`이 있으면 SDK 기본 설정이 그 주소로 보내 인증이 실패하던 문제다. 실행별 추정 비용을 감사 기록과 프로필 단가(`llm.pricing_usd_per_mtok`)로 보여 준다.
- **LLM 실측은 아직이다.** 이 세션에서는 키가 환경변수로 저장됐지만 실행 중인 컨테이너에는 들어오지 않았다(다음 세션 시작 때 적용).

## 부록 A. 원문 대조 체크리스트 (코드 영향 기준)

전체 목록은 [조사 보고서 5장](<../reports/나라장터 제안서 자동화 조사.md#원문과-대조하기-전에는-하드코딩하면-안-되는-수치들>)에 있다. 아래는 프로필 키나 규칙에 직접 들어가는 항목만 추린 것이다.

2026-11-17 대조 결과는 [M0 원문 대조 기록](analysis/m0-source-check.md)에 조항 인용과 함께 있다.

| 프로필 키·규칙 | 현재 값 | 대조한 원문 | 결과 |
|---|---|---|---|
| `evaluation.tech_cutoff_pct` | 85 | 「협상에 의한 계약체결기준」(재정경제부계약예규 제40호) 제8조① | **verified** |
| `evaluation.tech_price_ratio` | [90, 10] | 행안부 「정보시스템 구축·운영 지침」(고시 제2025-1호) 제18조①(②: 80점 예외), 조달청 세부기준 제9조① | **verified** |
| `evaluation.max_points_per_area`, `min_points` | 30 / 5·5 | 「소프트웨어 기술성 평가기준 지침」(과기정통부고시 제2025-20호) 별표 1 비고 | **verified** |
| `evaluation.qualitative_grades` | 5 | 같은 별표 1 비고(5등급 내외) | **verified** |
| `local_negotiation` 컷오프 | 합산 70점, SW는 기술 85% | 행안부 예규 「지방자치단체 입찰시 낙찰자 결정기준」 제7장 | 미대조(M4 지자체 프로필) |
| 온라인 평가(발표 기준 5억원, 검토 60분) | 리뷰어 시나리오 파라미터 | 「조달청 협상에 의한 계약 제안서평가 세부기준」(조달청지침 제379호) 제10조 | 미대조(M4 리뷰어) |
| `submission.total_size_limit_mb` | 300 | 조달청 세부기준 제6조의2①2 | **verified** |
| `submission.format`, PDF/A 요구 여부 | pdf | 조달청 세부기준 제6조의2①1(PDF/A 요구 없음) | **verified** |
| 블라인드 감점 규정(BLD-*) | 기관 규정 사례 | 조달청 세부기준(조달청 의뢰 사업 적용 여부) | 미대조 |
| LANG-001 비방 불이익 | 0.1점 감점 | 조달청 세부기준 제10조의9, 별표 26(2026.6.30.까지 오프라인 평가만) | **원문 확인** |
| 사전접촉 감점 | 5점 | 조달청 세부기준 제14조의2① | **원문 확인** |
| 별지 제5호서식 목차(`outline.default_template`) | 7개 대분류 | 조달청 세부기준 별지 제5호서식(제6조의2①) | **verified**(절 이름을 별지와 같게 고침) |
| 조달청 OpenAPI(7.1절) | 서비스명·경로 | data.go.kr 명세, 트래픽 한도, 구 API 폐기일 |
| 글꼴 허용 목록(10.1절) | 함초롬·Pretendard 보류 | 각 배포처 라이선스 원문 |

## 부록 B. 용어

| 용어 | 뜻 |
|---|---|
| 협상에 의한 계약 | 제안서를 평가해 협상 순서를 정하고, 협상을 거쳐 계약하는 방식(국가계약법 시행령 제43조) |
| 협상적격자 | 기술점수가 배점한도의 85% 이상이고 가격이 예산 이하인 입찰자(국가계약 기준) |
| 정량·정성평가 | 정량은 실적·인력 같은 객관 지표, 정성은 평가위원이 등급으로 매기는 제안 내용 평가 |
| 사전규격 | 본공고 전에 공개하는 규격·RFP 초안. 의견 제출 기간이 있다 |
| 정정공고 | 공고 내용 변경. 차수(bid_ord)가 올라간다 |
| 별지(서식) | 공고에 첨부되는 제출 양식(입찰참가신청서, 서약서, 정량 서식 등) |
| 블라인드 평가 | 제출물에서 업체 식별 표시를 금지하는 평가 방식 |
| 요구사항 ID | `SFR-001`처럼 3자 접두어와 일련번호로 된 RFP 요구사항 식별자 |
| 추적표 | 요구사항 ID ↔ 평가항목 ↔ 제안서 절·쪽을 잇는 대응표 |
| 거버닝 메시지 | 장표·절 상단에 두는 결론형 한 문장 |
| HWPX / OWPML | 한글 문서의 개방형 XML 포맷 / 그 국가표준(KS X 6101) |
| DocIR | 이 생성기의 정규화 문서 표현(6.2절) |
| fact 토큰 | `{{fact:ID}}`. KB의 검증된 값을 본문에 넣는 자리표시자 |

## 부록 C. 참고 구현 대응표

| 설계 요소 | 참고한 구현·근거 | 이 설계에서 달라진 점 |
|---|---|---|
| 수치는 코드, 서술은 LLM | yooseungmin9/nara-detector | fact 토큰과 FACT 규칙으로 강제 |
| 원문 인용·위치 강제 | Edell1/rfp-lens, jechoiyyy/bid-deep-agent | DocIR 블록 ID + quote 문자열 검증 |
| 페이지 예산 선설계 | iplip85-create/qwen-proposal-agent | 배점 비례식과 최대잉여법 |
| 평가기준 레드팀 | nasaon/g2b-proposal-automation | LLM 리뷰는 보조, 결정적 규칙이 주 평가 |
| 양식 보존 빈칸 채우기 | kyuhyoung/dsi, hwpx-mcp-server | 별지는 셀 경로 기반으로만 수정 |
| 회사 PPTX 템플릿 온보딩 | kyuhyoung/dsi | 슬롯 모델 + 사람 확인 |
| 서식 품질 게이트 | KAIST Proposal_Writer, Canine89/hwpxskill | polaris_dvc 검증 + 렌더 쪽수 측정 |
| 섹션 간 SSOT | DinN0000/bid-marketplace(BidKit) | 프로젝트 fact로 통합 |
| 실격사유 점검 | OpenBidKit_Yibiao, BidMaster-Pro(AGPL-3.0, 분석 후 재구현) | M1: 입찰무효·평가제외·감점 사유 추출(원문 명시/권고 분리), 평가항목·평가규칙 분리, 작성지침 극성·누락 점검, 지정 목차 작성 방식 태그, 쪽당 글자 수. M2: 한국 작성지침 기반 규칙 카탈로그 |
| 정정공고 재생성 | GovDash, BidPilot-AI(AGPL-3.0, 분석 후 재구현) | M1: 항목 단위 RFP diff, 재실행 단계 미리보기, 고위험 변경 확인 목록(`rfpgen diff`). M4: 자동 감시와 DAG 재실행 |
| 근거자료 공백이 품질 병목 | Yu, Mathew & Wang(2026) | 생성 전 자료 요청서 |
| 산문 지시, 후처리 가드레일 | Yu, Mathew & Wang(2026) | 프롬프트 작성 규칙(8.4절) |
| 입찰공고·사전규격 수집 | narajangteo-bid-mcp, mcp-kr-g2b | 생성기 입력 어댑터로만 사용 |
