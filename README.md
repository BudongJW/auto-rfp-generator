# rfpgen — 나라장터·조달청 제안서 자동생성기

나라장터(KONEPS)·조달청 협상에 의한 계약의 기술제안서 작성을 돕는 도구입니다. 목표는 "평가표를 빠짐없이 채우는 제안 작업대"입니다. 지표는 요구사항 누락 0건, 형식 위반 0건, 작성 시간 단축입니다.

- 설계: [docs/design.md](docs/design.md)
- 조사 보고서: [reports/](reports/)
- 외부 코드 분석: [docs/analysis/](docs/analysis/)

## 현재 단계: M1 RFP 분석기

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

- **LLM 보조 추출은 아직 실제 API로 품질·비용을 재지 않았습니다.** 가짜 공급자로 검증 규칙과 요청 형태만 테스트했습니다.
- **스캔 PDF는 아직 읽지 못합니다.** 숫자가 도형으로 그려진 PDF도 마찬가지입니다. 대신 해당 문장을 찾아 "숫자를 읽지 못함"으로 보고합니다.
- **배포용·암호 HWP는 열지 않습니다.** 한글에서 PDF로 저장해 올려 주세요.
- **상세화 등급(S~D)은 휴리스틱 추정입니다.**

## 라이선스

코드는 GPL-3.0입니다(`LICENSE`). `src/rfpgen/_third_party/agpl/` 아래 파일은 AGPL-3.0 저작물(OpenBidKit_Yibiao, BidMaster-Pro)을 번안한 것으로 AGPL-3.0-only 조건을 따르며, 원 라이선스와 저작자 고지는 [third_party/](third_party/)에 있습니다. 이 프로그램을 웹 서비스로 제공하면 이용자에게 전체 소스를 제공해야 합니다(설계서 11.2절).
