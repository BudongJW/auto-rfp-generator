# rfpgen — 나라장터·조달청 제안서 자동생성기

나라장터(KONEPS)·조달청 협상에 의한 계약의 기술제안서 작성을 돕는 도구입니다. 목표는 "평가표를 빠짐없이 채우는 제안 작업대"입니다. 지표는 요구사항 누락 0건, 형식 위반 0건, 작성 시간 단축입니다.

- 설계: [docs/design.md](docs/design.md)
- 조사 보고서: [reports/](reports/)
- 외부 코드 분석: [docs/analysis/](docs/analysis/)

## 현재 단계: M1 RFP 분석기 + M2 본문 초안(1차) + M3 장표·PDF·별지 서식·제출 패키지(1차)

RFP와 공고 첨부를 넣으면 다음을 만듭니다. 모든 추출값에는 원문 위치(문서·블록·쪽)가 붙습니다.

| 산출물 | 내용 |
|---|---|
| `rfp/rfp.vN.json` | 공고 기본정보, 평가표(부문·항목·배점·평가 질문, 정량/정성)와 평가규칙(등급·감점·산식), 입찰무효·평가제외·감점 사유와 참가자격, 요구사항(ID·분류·명칭·정의·세부내용·산출정보), 작성지침(분량·제외 항목·용지·글자 크기·제출 형식·용량·블라인드·발표·지정 목차·별지 서식), 질의서 후보 |
| `rfp/extraction_report.vN.json` | 사람이 확인할 점검 결과(선언 요구사항 수 불일치, ID 오타 의심, 읽지 못한 분량 숫자 등) |
| `plan/outline.json`, `budget.json`, `trace.json` | 목차(지정 목차 > 평가표 > 기본 템플릿), 배점 비례 쪽수 예산과 절별 목표 글자 수, 요구사항 추적표(버전별 사본은 `plan/vN/`) |
| `rfp/diff_vA_vB.json`, `out/diff_vA_vB.md` | `rfpgen diff`의 버전 비교 결과 |
| `out/analysis.xlsx` | 추적표·평가표·요구사항·목차·쪽수·작성지침·무효·감점 사유·평가규칙·질의서 후보·점검 결과 시트 |
| `out/analysis.md`, `out/questions.md` | 검토용 요약, 발주기관 질의서 초안 |

지원 입력 형식은 HWPX, HWP(5.0), PDF(텍스트 레이어 필요), DOCX, 그리고 이 파일들을 담은 ZIP 묶음입니다.

## 설치와 실행

```bash
uv sync
```

```bash
uv run rfpgen analyze 제안요청서.hwpx 공고문.pdf -o projects/my-bid
```

정정공고나 본공고가 나오면 같은 프로젝트 폴더로 다시 분석한 뒤 두 버전을 비교합니다. 바뀐 요구사항·배점·분량, 영향받는 목차 절, 다시 돌려야 할 단계, 사람이 확인할 고위험 변경을 보여 줍니다.

```bash
uv run rfpgen analyze 정정공고_제안요청서.hwpx -o projects/my-bid
```

```bash
uv run rfpgen diff projects/my-bid
```

### LLM 보조 추출(선택)

결정적 규칙으로 못 채운 작성지침 값, 규칙에 걸리지 않은 무효·감점 사유와 참가자격, 요구사항 ID 없이 문장으로만 적힌 요구사항을 Claude API로 보강합니다. 근거 인용 검증을 통과한 값만 받고, 모두 `method=llm`·`status=proposed`로 들어가 사람이 확인합니다.

```bash
export ANTHROPIC_API_KEY=...
```

```bash
uv run rfpgen analyze 제안요청서.hwpx -o projects/my-bid --llm
```

- 모델은 `--llm-model` 또는 환경변수 `RFPGEN_LLM_MODEL`로 지정합니다. 지정하지 않으면 Models API에서 가장 최근 Opus 계열 모델을 고릅니다.
- 보내는 것은 공개 RFP의 키워드 주변 발췌뿐입니다(과제당 최대 8만 자). 회사 자료는 보내지 않습니다.
- 호출마다 모델·토큰·캐시 적중·결과가 `audit/llm_calls.jsonl`에 남습니다.
- 인증 정보가 없거나 호출이 실패해도 LLM 과제만 건너뛰고 나머지 분석 결과는 그대로 나옵니다.

### 본문 초안(M2)

회사 지식베이스(KB)를 만들고, 분석한 프로젝트에서 본문 초안을 만듭니다. 결과는 `out/proposal.hwpx`(A4 세로 보고서체), `strategy/storyboard.md`(스토리보드), `out/trace_draft.xlsx`(대응 방안이 채워진 추적표와 자료 요청서), `checks/*.md`(제출 전 점검)입니다.

```bash
uv run rfpgen kb init kb
```

```bash
uv run rfpgen draft projects/my-bid --kb kb
```

```bash
uv run rfpgen draft projects/my-bid --kb kb --llm
```

- `--llm` 없이 실행하면 평가 질문·요구사항·필요 근거를 `[확인 필요]` 자리표시자와 함께 배치한 **작성용 골격**을 만듭니다.
- `--llm`이면 스토리보드와 절 본문을 생성합니다. 회사 수치는 LLM이 `{{fact:F-001}}` 같은 토큰으로만 쓰고 값은 KB에서 채웁니다. 수치 값은 보내지 않습니다.
- KB의 ID·설명·재사용 문단까지 보내려면 `--llm-share-kb`를 줍니다(기본은 공개 RFP만).
- `strategy/storyboard.json`을 고친 뒤 다시 실행하면 고친 내용으로 씁니다. `--section S-3-1`로 일부 절만 다시 쓸 수 있습니다.

### 장표·PDF·제출 패키지(M3)

```bash
uv run rfpgen slides projects/my-bid
```

```bash
uv run rfpgen package projects/my-bid --kb kb
```

- `slides`: 최신 절 초안으로 `out/summary.pptx`(요약본, A4 가로), `out/presentation.pptx`(발표자료, 16:9), `out/script.md`(발표 대본·예상 질문)를 만듭니다. 대본은 발표자 노트에도 들어갑니다.
- `package`: HWPX·PPTX를 PDF로 바꾸고 작성자 등 파일 정보를 지워 `submission/`에 `01_정성제안서.pdf`, `02_제안요약서.pdf`, `03_발표자료.pdf`와 `제출전점검표.md`를 만듭니다. 실제 렌더 쪽수·총 용량·글꼴 임베딩·파일 정보의 회사 식별 표기를 점검합니다. 나라장터 업로드는 사람이 합니다.

### 별지 서식 채우기(M3)

공고 첨부(HWPX·HWP)에 들어 있는 별지 서식(입찰참가신청서, 서약서, 유사사업 실적, 참여인력 현황, 하도급 계획서 등)을 서식마다 따로 떼어 내 빈칸을 채웁니다.

```bash
uv run rfpgen forms projects/my-bid --kb kb --date 2026-12-01
```

- 결과: `out/forms/별지NN_제목.hwpx`(서식별), `out/forms/forms.md`(채운 칸과 확인할 것), `checks/forms-*.md`.
- 회사 정보는 `kb/company.yaml`의 `identity`(상호·대표자)와 `company`(사업자등록번호·주소·전화 등), 실적·인력·인증 표는 `projects.csv`·`people.csv`·`certifications.csv`에서 가져옵니다. 빈 행이 모자라면 같은 모양의 행을 늘립니다.
- 성명 칸은 `kb/private/people.csv`(id,name)가 있을 때만 채웁니다. 생성기가 모르는 칸(담당자 등)은 `kb/private/forms.yaml`에 `values: {담당자: 홍길동}`처럼 적습니다. `private/`는 LLM에 보내지 않고 저장소에도 올리지 않습니다.
- 서명·날인, 선택 칸(□), 모르는 이름표는 채우지 않고 확인할 것으로 남깁니다. 블라인드 평가 문서(지정 목차가 가리키는 서식)에는 회사 식별 정보를 넣지 않습니다.
- 문서구분(정성·정량·하도급·기타)은 서식 제목으로 추정합니다. 바꾸려면 프로젝트 폴더에 `forms.yaml`(`doc_types: {"7": 정량제안서}`, `skip: ["3"]`)을 둡니다. `rfpgen package`가 문서구분별 PDF(`04_정량제안서.pdf` 등)로 묶습니다.

PDF 변환에는 다음이 필요합니다(한 번만).

```bash
cd sidecars/node && npm install
```

```bash
sudo apt-get install -y libreoffice-impress fonts-noto-cjk
```

- HWPX → PDF는 Node(18 이상)와 Playwright Chromium, `@rhwp/core`(MIT)를 씁니다. PPTX → PDF는 LibreOffice를 씁니다.
- 서버 렌더는 한글 화면과 다를 수 있습니다. 최종본은 PDF를 쪽마다 열어 확인하세요.

```bash
uv run rfpgen parse 제안요청서.pdf
```

```bash
uv run rfpgen profile
```

`rfpgen profile`은 제도 수치(배점, 협상적격 85%, 300MB 등)를 출처와 상태(`verified`, `provisional`, `user`)와 함께 보여 줍니다. `provisional` 값은 아직 원문과 대조하지 않은 값입니다(설계서 부록 A). RFP에서 읽은 값이 있으면 항상 그 값이 우선합니다. 조직 기준은 `--profile org.yaml`로 덮어씁니다.

## 테스트

```bash
uv run pytest
```

테스트는 공개 RFP 형식을 흉내 낸 합성 문서로 돌아갑니다. 실제 RFP 원문은 재배포 라이선스를 확인하기 전까지 저장소에 넣지 않습니다.

## 알려진 한계

- **LLM 보조 추출과 LLM 초안 생성은 아직 실제 API로 품질·비용을 재지 않았습니다.** 가짜 공급자로 검증 규칙과 요청 형태만 테스트했습니다.
- **쪽수:** `draft`의 쪽수는 글자 수 추정이고, `package`가 렌더한 PDF로 확정합니다. 서버 렌더(rhwp)는 한글과 쪽 나눔이 다를 수 있으니 HWPX를 한글에서도 열어 확인해 주세요.
- **별지 서식 채우기는 합성 서식으로만 검증했습니다.** 실제 공고 HWP 서식에서 이름표·표 모양이 다르면 못 채운 칸이 `forms.md`에 남습니다. 한글에서 열어 칸 넘침을 확인하세요. PDF로만 받은 서식은 채우지 못합니다.
- **M3에서 아직 없는 것:** 도식(조직도·추진체계도) 자동 렌더, LLM 대본, 회사 PPTX 템플릿 적용.
- **스캔 PDF는 아직 읽지 못합니다.** 숫자가 도형으로 그려진 PDF도 마찬가지입니다. 대신 해당 문장을 찾아 "숫자를 읽지 못함"으로 보고합니다.
- **배포용·암호 HWP는 열지 않습니다.** 한글에서 PDF로 저장해 올려 주세요.
- **상세화 등급(S~D)은 휴리스틱 추정입니다.**

## 라이선스

코드는 GPL-3.0입니다(`LICENSE`). `src/rfpgen/_third_party/agpl/` 아래 파일은 AGPL-3.0 저작물(OpenBidKit_Yibiao, BidMaster-Pro)을 번안한 것으로 AGPL-3.0-only 조건을 따르며, 원 라이선스와 저작자 고지는 [third_party/](third_party/)에 있습니다. 이 프로그램을 웹 서비스로 제공하면 이용자에게 전체 소스를 제공해야 합니다(설계서 11.2절).
