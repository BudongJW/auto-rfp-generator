# 중국 标书 생성기 4종 소스 분석과 이식 계획

| 항목 | 내용 |
|---|---|
| 문서 상태 | 분석 v0.1 |
| 작성일 | 2026-11-16 |
| 대상 | FB208/OpenBidKit_Yibiao, guangshu100/BidMaster-Pro, Get00/BiaoShu-SKILL, Router0824/BidPilot-AI |
| 목적 | 네 저장소의 작동 부품을 [설계서](../design.md)의 모듈(ingest·parse·extract·plan·strategy·generate·derive·render·check·package·kb·llm·profile)에 대응시키고, 코드·프롬프트 이식 계획과 라이선스 의무를 기록한다 |
| 전제 | 프로젝트 소유자가 이들 코드를 가져와 조정하기로 결정했다. 라이선스 영향은 감수하되 정확히 기록한다(4.3절) |
| 소스 위치 | `/tmp/claude-0/-home-user-auto-rfp-generator/f3d3ff9a-3973-59c5-bd3d-f4f9b614b83d/scratchpad/ext/<저장소명>/` (세션 스크래치 영역이라 재부팅 시 지워질 수 있다. 1장의 커밋 SHA로 다시 받을 수 있다) |

인용 표기: 경로는 `ext/` 아래 저장소 폴더 기준이고 `파일:시작-끝` 줄 번호를 붙인다. 약칭은 **OBK**(OpenBidKit_Yibiao), **BMP**(BidMaster-Pro), **BSS**(BiaoShu-SKILL), **BPA**(BidPilot-AI)다. 본문에서는 파일 이름만 쓰는 경우가 많으므로, 자주 나오는 파일의 위치를 아래에 모은다. 코드는 읽기만 했고 실행·설치하지 않았다.

| 저장소 | 파일 이름 | 위치 |
|---|---|---|
| OBK | `bidAnalysisTask.cjs`, `blindCheckPresetExtraction.cjs`, `blindCheckPresets.cjs`, `blindCheckReview.cjs`, `outlineFormatExtraction.cjs`, `outlineGenerationTaskV2.cjs`, `globalFactsTask(V2).cjs`, `contentGeneration*.cjs`, `businessTemplateFillTask.cjs`, `rejectionCheckTask.cjs`, `duplicateCheckService.cjs`, `aiService.cjs`, `licenseService.cjs`, `technicalPlanStore.cjs`, `rulePageCompileTask.cjs` | `client/electron/services/` |
| OBK | `userTextSplitter.cjs`, `segmentedAiResultMerger.cjs`, `promptPrefixCache.cjs`, `aiRetry.cjs`, `aiRequestQueue.cjs`, `bidSectionContext.cjs` | `client/electron/utils/` |
| OBK | `rejectionPrompts.ts`, `analysisPrompts.ts`, `jsonRepairPrompts.ts` | `client/src/shared/prompts/` |
| OBK | `pageMetrics.ts`, `sectionSkeleton.ts`, `skeletonPrompt.ts` | `client/src/shared/layoutBudget/` |
| OBK | `RuleCatalog.cs`, `PrivacyRules.cs`, `ConsistencyRules.cs` 등 | `openxmlhelper/src/OpenXmlHelper/BlindCheck/Rules/` |
| OBK | `TableOfContentsBuilder.cs`, `FillTocPageNumbersAction.cs` | `openxmlhelper/src/OpenXmlHelper/Jobs/` |
| BMP | `*_check_skill.py`, `risk_score_skill.py`, `selfcheck_list_skill.py`, `whitelist_filter_skill.py` | `services/check/skills/` |
| BMP | `tender_interpret_skill.py`, `scoring_matrix_skill.py`, `risk_alert_skill.py` | `services/interpret/skills/` |
| BMP | `outline_gen_skill.py`, `content_gen_skill.py`, `structure_template_skill.py`, `mandatory_req_extract_skill.py` | `services/generate/skills/` |
| BMP | `docx_format_skill.py`, `bid_docx_export_skill.py` | `services/format/skills/` |
| BMP | `gateway.py`, `json_repair.py` | `core/llm_gateway/` |
| BMP | `check.py`, `generate.py` | `services/routers/` |
| BSS | `extract_scoring.py`, `extract_requirements.py`, `generate_outline.py`, `generate_content.py`, `check_word_count.py`, `humanizer.py`, `generate_placeholder.py`, `format_docx.py`, `parse_bid_file.py` | `BiaoShu-writer-pro/scripts/` |
| BPA | `agents/__init__.py`, `agents/addendum_agent.py` | `app/agents/` |
| BPA | `engine.py`, `dependency_graph.py`, `workflow_service.py` | `app/workflows/` |
| BPA | `review_export_service.py`, `confidence_service.py`, `evidence_service.py` | `app/application/` |

---

## 0. 요약

1. **네 저장소를 모두 확보했다.** 라이선스는 LICENSE 파일 기준으로 OBK·BMP·BPA가 AGPL-3.0, BSS가 Apache-2.0이다. 그런데 **BMP(README: MIT), BPA(README: Apache-2.0), BSS(README: MIT) 세 곳은 README 표기가 LICENSE 파일과 다르다.** 이 문서는 LICENSE 파일을 따른다. BMP와 BPA는 더 엄격한 AGPL-3.0으로 다룬다(1.2절).
2. **성숙도는 OBK가 압도적이다.** OBK는 Electron(JS) + C# OpenXML 헬퍼 + 에이전트 런타임으로 된 실사용 제품이다. 결정적 검증 코드가 촘촘하다. BMP는 기능 목록은 넓지만 대부분 "LLM 1회 호출 + 입력 3,000~8,000자 자르기" 수준이다. 단계 사이 데이터 연결에도 버그가 있다(2.2.9절). BSS는 정규식 스크립트와 SKILL.md 지침 묶음이고, 본문 "생성" 코드는 고정 문구 템플릿이다. BPA는 워크플로·확인 게이트·근거 추적 골격이 깔끔한 MVP다.
3. **M1(RFP 분석기)에 바로 쓸 것은 OBK에 몰려 있다.**
   - (a) **평가항목과 평가규칙을 나누는 평가기준 추출 프롬프트**(`bidAnalysisTask.cjs:76-104`).
   - (b) **입찰무효와 废标项를 구분하고 "원문 명시"와 "경험 보충"을 섞지 않는 실격사유 추출 프롬프트**(`bidAnalysisTask.cjs:32-65`).
   - (c) **작성지침(형식 요건) 추출 파이프라인**(`blindCheckPresetExtraction.cjs`): 키워드 창 검색 → 필드와 근거 인용을 함께 받는 LLM → 결정적 형변환·범위 검사 → 원문 대조 → 부정·허용 극성 검사 → 누락 탐지 순으로 처리한다. 우리 설계 D3·D6을 그대로 구현한 형태다.
   - (d) **지정 목차·제출서류 추출과 위치 검증**(`outlineFormatExtraction.cjs:99-258`).
   - (e) **평가항목 ID(R1…)를 목차 노드에 "정확히 한 번" 매핑하고 프로그램이 커버리지를 계산하는 목차 생성 절차**(`outlineGenerationTaskV2.cjs:664-731, 840-863`).
4. **정정공고(补遗) 영향 분석은 BPA가 유일하지만 얕다.** 정규식으로 사실 5종(예산·공기·마감·보증기간·배포방식)을 뽑아 기존 값과 비교하고 확인 작업을 만든다. 단계 단위 무효화 신호표(`invalidated_by`)로 하위 단계를 다시 돌린다(`addendum_agent.py:4-84`, `engine.py:68-189`, `dependency_graph.py:33-114`). 텍스트 diff나 항목 단위 전파는 없다. 우리 설계 7.11절이 이미 더 세밀하므로 **신호표·영향 미리보기·확인 게이트 패턴만 가져오면 된다.**
5. **블라인드 평가 점검은 OBK의 暗标 규칙 엔진(64개 규칙, C#)이 거의 그대로 대응한다.** 신원 노출 탐지기는 신분증 번호·통일사회신용코드 체크섬 검증과 제3자 기관 무시 목록을 갖췄다. 확정 적중과 AI 재검토 후보도 분리한다(`PrivacyRules.cs:6-110`). 우리 BLD-001·003, FMT-001·002의 규칙 카탈로그 원형으로 쓸 수 있다. 대상 포맷이 DOCX라 HWPX(OWPML)용으로 다시 구현해야 한다.
6. **가져오면 안 되는 것.**
   - OBK 전역 사실의 **기본 모드가 `fabricate`(사실이 없으면 그럴듯하게 지어냄)** 다(`globalFactsTask.cjs:8-10`).
   - BSS 본문 템플릿에는 "提高业务处理效率30%以上" 같은 **근거 없는 수치가 하드코딩**돼 있다(`generate_content.py:334`).
   - BMP 가격 "안전구간 95~98%" 규칙(`pricing_check_skill.py:96-111`)은 우리 비목표인 가격 전략이다.
   - BPA는 입력을 9,000자×4조각까지만 읽고 나머지를 버린다(`agents/__init__.py:40-49`).
7. **설계서와의 정합.** 이 분석을 쓰는 동안 설계서 작업 트리(미커밋 v0.2)에 이식 결정이 반영됐다(11.1·11.2절, 16장 Q8). 그런데 4장 원칙 P8("GPL·AGPL 도구는 별도 프로세스로만 쓰거나 아이디어만 참고")과 부록 C "실격사유 점검" 행("AGPL, 아이디어만")은 아직 옛 정책이다. 함께 고쳐야 한다(이 작업에서는 이 문서 외의 파일을 수정하지 않았다).

---

## 1. 확보한 소스와 라이선스

### 1.1 저장소별 확보 결과

| 저장소 | 커밋 SHA (브랜치 main) | 커밋 시각 | 확보 방법 | 규모 | LICENSE 파일 | 다른 곳의 표기 | 이 문서의 판정 | 저작권자 표기 |
|---|---|---|---|---|---|---|---|---|
| FB208/OpenBidKit_Yibiao | `77a38f07db822daee0e4be80b84c2281c73d646e` | 2026-11-15 09:37:50 +0000 | `git clone --depth 1` | 830파일, 74MB | AGPL-3.0 전문(661줄) + `NOTICE`(AGPL §7(b) 저작자 표시 요구, "v3.0 only") | README:352-356 AGPL-3.0 | **AGPL-3.0-only + NOTICE 보존 의무** | `NOTICE`: "Copyright (C) 2025-2026 mark / yibiaoai" |
| guangshu100/BidMaster-Pro | `cc89d9093651e3410f68384f926ceef672b76534` | 2026-09-03 17:44:03 +0800 | 얕은 clone 후 `fetch --unshallow`(32커밋) | 201파일, 8.5MB | AGPL-3.0 전문(661줄). 2026-05-25 커밋 `681027e`(빈 파일)→`85401e3`(전문)로 추가 | README:7 배지·373-375 "MIT", `skills/*/SKILL.md` front matter `license: MIT` | **AGPL-3.0으로 취급** | LICENSE에 저작권자 없음. 커밋 작성자 chenjinyong / guangshu100 |
| Get00/BiaoShu-SKILL | `23ec3ae200ce2bdf15df723d96aca62c2f5bc1d7` | 2026-09-24 09:39:07 +0800 | 얕은 clone 후 unshallow(9커밋) | 56파일, 856KB | Apache-2.0 전문(201줄). 최초 커밋 `0265f3e`(2026-05-22)부터 존재 | README:7 배지·267-269 "MIT" | **Apache-2.0으로 취급** | LICENSE 부록의 빈 템플릿 그대로(저작권자 없음). 커밋 작성자 "Eden."(Get00), `_meta.json` author "TreaSkill" |
| Router0824/BidPilot-AI | `cd91f831b2288661111a8ceb97d725b595f578d5` | 2026-10-03 22:23:55 +0800 | 얕은 clone 후 unshallow(21커밋) | 131파일, 2.8MB | AGPL-3.0 전문(661줄). 최초 공개 커밋 `3e65053`(2026-08-07)과 병합된 별도 뿌리 `e5daf92`에 모두 존재 | README:11 front matter `license: Apache License 2.0`, :24 배지, :445-447 "Apache License 2.0"(2026-08-09 커밋 `7f1ef70`·`0110f25`에서 추가) | **AGPL-3.0으로 취급** | LICENSE에 저작권자 없음. 커밋 작성자 Zhang Boyang(Router0824), "BidPilot Release" |

- 세 AGPL LICENSE 파일은 FSF 표준 전문이다. BMP와 BPA 파일은 서로 같고(md5 `4ae09d45…`), OBK 파일과는 524-525줄의 줄바꿈 위치만 다르다.
- `ext/`에는 이 작업과 무관한 `H2Orestart/`, `hwpx-docs/`도 있다. 다른 작업이 받아 둔 것으로 보여 건드리지 않았다.
- GitHub API(`gh api repos/.../license`)는 세션 권한이 없어 403을 받았다. 라이선스 판정은 LICENSE 파일과 git 이력으로만 했다.

### 1.2 라이선스 충돌 판정 근거

- **BMP:** README의 "MIT"는 2026-05-15 커밋(`fefef6a`)에 들어갔다. AGPL LICENSE 파일은 그 뒤인 2026-05-25에 추가됐다. 저장소에 실제로 들어 있는 라이선스 문서가 AGPL이고 시점도 뒤이므로 AGPL-3.0으로 다룬다.
- **BPA:** LICENSE(AGPL)는 GitHub 최초 공개 커밋(`3e65053`, 2026-08-07)부터 있었다. README의 Apache 표기는 이틀 뒤 ModelScope 배포용 front matter 정리와 함께 들어왔다(`7f1ef70`, `0110f25`). 둘 중 무엇이 의도인지 확정할 수 없으므로 엄격한 쪽(AGPL)을 택한다. 저자가 Apache-2.0이라고 확인해 주면 의무가 가벼워진다.
- **BSS:** LICENSE는 Apache-2.0, README는 MIT다. 둘 다 허용형이고 Apache의 의무(고지 유지, 변경 표시)가 MIT의 의무를 포함한다. Apache-2.0을 기준으로 지키면 양쪽을 모두 만족한다.
- **권고:** BMP·BPA 저자에게 이슈로 라이선스 의도를 확인한다. 답을 받기 전까지 이 문서의 판정을 따른다.

### 1.3 용어 대응

| 중국 입찰 용어 | 한국 조달 용어(이 문서의 번역) | 비고 |
|---|---|---|
| 招标文件 / 采购文件 | 제안요청서(RFP)·입찰공고문·과업지시서 | |
| 投标文件 / 标书 / 响应文件 | 제안서(제출서류 일체) | |
| 技术标 / 技术方案 | 기술제안서(정성제안서) 본문 | |
| 商务标 / 资信 | 정량제안서·업체 일반현황 | 가격(报价)은 가격제안서 |
| 评分标准 / 评分办法 / 评标办法 | 제안서 평가기준(평가표) | |
| 技术评分项 | (정성) 평가항목·세부항목 | |
| 技术评分要求 | 평가 방법·감점 규칙·등급 정의 | 항목이 아니라 규칙 |
| 资格性审查 / 投标人资格 | 입찰참가자격 심사 | |
| 符合性检查 | 제출서류·형식 적합성 확인 | 정확한 대응 제도는 없음 |
| 无效投标 / 否决投标 | 입찰무효·평가 제외 | |
| 废标 / 废标项 | 유찰·평가 제외로 이어지는 사유 | 2.1.3절 개념 경계 참조 |
| ★▲ 实质性条款 | 필수 요구사항("반드시", "필수" 표기) | |
| 暗标 | 블라인드 평가(업체정보 삭제본) | |
| 补遗 / 澄清 | 정정공고·질의회신·RFP 변경 | |
| 点对点应答表 / 偏离表 | 요구사항 대비표(추적표)·규격 대비표 | |
| 评分因素页码检索表 | 평가항목별 제안서 쪽 대비표 | |
| 投标函·授权委托书 등 格式 | 별지 서식(입찰참가신청서·위임장·서약서 등) | |
| 标段 | 분할 발주 단위(로트) | 한국 SW사업에서는 드묾 |
| 签字盖章 / 骑缝章 / CA证书 | 서명·날인 / 간인 / 공동인증서 | 제출은 사람이 하므로 대부분 범위 밖 |

---

## 2. 저장소별 분석

### 2.1 OpenBidKit_Yibiao (易标)

#### 2.1.1 구조와 기술 스택

- **제품 코드는 `client/`에 있다**(`AGENTS.md:3-5`).
  - Electron Main(CommonJS `.cjs`)이 업무 로직을 맡는다.
  - Renderer는 React + TypeScript이고(`client/package.json:200`), 저장소는 SQLite다(`AGENTS.md:13, 28`).
  - 장시간 작업(招标 해석, 목차, 전역 사실, 본문)은 Main의 백그라운드 작업으로 돌고 SQLite에 체크포인트를 남긴다(`AGENTS.md:30`).
- **Word 처리는 별도 .NET 프로세스다.** `openxmlhelper/`(C#, DocumentFormat.OpenXml)가 맡는다. 암표 점검 규칙 엔진, 목차(TOC) 생성, 서식 칸 채우기, HTML→Word 삽입이 여기에 있다(`openxmlhelper/src/OpenXmlHelper/BlindCheck/**`, `Jobs/**`).
- **에이전트 런타임("Pi")이 있다.** 목차·전역 사실·본문은 에이전트가 작업 폴더의 파일을 읽고 쓰는 방식으로 돈다. 프로그램이 스키마 검증, 사용자 확인 도구(`ask-user`), 실패 보고(`report-failure`)를 준다(`outlineGenerationTaskV2.cjs:768-994`의 프롬프트 문구).
- **온라인 서비스가 붙어 있다.** `analytics/` Cloudflare Worker가 공지, 모델 정보, 라이선스 활성화, 텔레메트리를 맡는다(`AGENTS.md:5`, `licenseService.cjs:10`). 이식 대상이 아니다.

#### 2.1.2 LLM 호출 구조

| 측면 | 구현 | 위치 |
|---|---|---|
| 공급자 | OpenAI 호환 `/chat/completions`만 사용. 로컬(ollama·LM Studio)도 같은 경로 | `aiService.cjs:1066, 1544-1696` |
| 출력 길이 | 모든 공급자에 `max_completion_tokens`로 통일. 요청별 `output_token_limit` | `aiService.cjs:992-1000` |
| JSON | 기본 `response_format: json_object`. 미지원 오류가 나면 빼고 재시도 | `aiService.cjs:627-631, 899, 938` |
| JSON 복구 | 괄호 균형 후보 추출 → 잘못된 역슬래시 이스케이프 수정 → LLM 복구 프롬프트 | `aiService.cjs:736-820, 886-980`, `jsonRepairPrompts.ts:1-25` |
| 스키마 검증 | 에이전트 산출 JSON을 Ajv 스키마로 검증하고, 실패하면 문제 목록을 돌려보내 고치게 함 | `outlineGenerationTaskV2.cjs:128-322, 373-431`, `rulePageCompileTask.cjs:2, 27-60` |
| 재시도 | 최대 3회, 대기 3초·5초. 408·429·5xx와 네트워크 오류 코드만 재시도 | `aiRetry.cjs:1-35` |
| 동시성 | 설정의 `concurrency_limit` + 요청 큐 | `aiService.cjs:2588`, `aiRequestQueue.cjs` |
| 긴 입력 | 기본 컨텍스트 한도 400,000자×0.8로 분할. 경계 우선순위는 Markdown 제목·빈 줄 > 줄바꿈 > 문장끝 > 세미콜론 > 쉼표, 코드 펜스 내부는 피함 | `userTextSplitter.cjs:1-14, 33-69, 180-211` |
| 분할 결과 병합 | 조각별 결과를 LLM에 다시 넣어 병합. "본 조각에 없음"은 다른 조각 값으로 덮고 새 정보 추가는 금지 | `segmentedAiResultMerger.cjs:12-48` |
| 프롬프트 캐시 | 공유 접두부(system + 招标文件 전문)를 **별도 메시지**로 두고, 출력 1토큰짜리 예열 요청을 보낸 뒤 1.5초 기다렸다가 과제들을 병렬 실행 | `promptPrefixCache.cjs:1-30`, `bidAnalysisTask.cjs:465-475` |
| 무결과 재실행 | Markdown 과제가 "未提取到"만 돌려주면 한 번 다시 실행 | `bidAnalysisTask.cjs:217-228, 289-294` |

#### 2.1.3 招标文件 해석: 평가기준·실격·자격·제출 요건

- **방식.** 招标文件 전체를 Markdown으로 바꿔 공유 접두부에 넣는다. 그 뒤에 **18개 해석 과제**를 각각 user 메시지로 붙여 병렬로 실행한다(`bidAnalysisTask.cjs:67-178, 230-247, 465-475`).
- **필수 과제.** 항상 필수는 5개다: 项目概述, 项目信息, 甲方信息, 交货和服务要求, 响应文件要求. 技术评分要求는 기술 문서 단독 모드와 전체 响应文件 모드에서, 商务评分要求는 상무 문서 단독 모드와 전체 响应文件 모드에서 필수다(`:77, 148, 181-183`).
- **출력 형식.** JSON 과제는 "key 고정, value만 채우고, 없으면 '没有提及'" 틀을 쓴다(`:16-30`). 서술형 과제는 Markdown으로 받는다.
- **평가기준(技术评分).** `:76-104`가 이 저장소에서 가장 가치 있는 프롬프트다.
  - 같은 표 안에서 **评分项**(제안서에서 하나씩 답하고 장·절로 대응시킬 수 있는 평가 대상)과 **评分要求**(평가를 제약·해석하는 규칙, 감점 기준, 판정 기준)를 의미로 나눈다.
  - 판정 기준을 명시한다: "제안서에서 구체적 방안을 써야 하는 내용이 아니면, 배점이 붙어 있어도 评分要求로 분류한다."
  - 각 항목마다 이름, 배점, 평가 기준, **数据来源(장·조·쪽·표 위치)** 을 쓴다.
  - 商务评分(`:147-174`)도 같은 틀이다.
  - 한국 평가표의 "세부 평가항목 vs 평가방법·등급 정의·감점 기준" 구분에 그대로 맞는다.
- **실격사유(无效投标·废标项).** `:32-65`
  - 개념 경계를 정의한다. 无效投标은 투찰인·서류·서명밀봉·제출시간·가격·보증금·자격·실질적 응답 때문에 무효·부결되는 경우다. 废标项은 유찰·재입찰·심사 종료·유효 투찰자 부족으로 이어지는 조항이다.
  - 同义 표현 목록(否决投标·无效响应·重大偏差·实质性偏离…)도 준다.
  - 출력은 **"招标文件中明确提到的"와 "此类标书还可能涉及的"(경험 보충, 항목당 3~5개)** 두 덩어리로 나눈다.
- **자격·적합성.** 资格性审查와 符合性检查는 짧은 Markdown 정리 과제다(`:143-144`).
- **响应文件要求.** `:124-139`는 제출 문서 구성·서식·서명·제출 방식을 **원문 순서 그대로** 뽑게 한다. "必须提供"와 "如适用"을 구분하되, 원문이 구분하지 않으면 추측하지 말라고 지시한다. 우리 `required_documents`(별지·문서구분) 추출에 대응한다.
- **분할 발주 대응.** 다중 标段이면 먼저 标段을 식별하고 범위를 고르게 한다. 그 뒤 모든 프롬프트에 `sectionHint`(선택 범위)를 system 메시지로 덧붙인다(`:316-334`, `bidSectionContext.cjs`).
- **한계.** 해석 결과 대부분이 **Markdown 텍스트**다. 평가항목이 구조화된 표(항목·배점 필드)가 아니다. 구조화는 목차 단계 에이전트가 `technical-score-groups.json`(R1…)을 만들 때 처음 일어난다(2.1.6절). 블록 ID 같은 원문 위치도 없고, "数据来源"은 자유 텍스트다.

#### 2.1.4 작성지침(暗标 排版格式) 추출: M1에 가장 가까운 패턴

파일은 `client/electron/services/blindCheckPresetExtraction.cjs`(484줄)다. 처리 단계는 다음과 같다.

1. **키워드 창 탐색(결정적, `:6-13, 95-132`).**
   - 형식 키워드(字体·字号·行距·页边距·页眉·页码·A4…)가 나온 줄을 중심으로 앞 12줄·뒤 28줄 창을 만든다.
   - 창 점수 = 키워드 수 + 문맥어(暗标·技术标) 가산 5점. 6점 미만 창은 버린다.
   - 겹치지 않는 상위 6개 창(최대 20,000자)만 LLM에 보낸다.
2. **LLM 추출(`:134-172`).**
   - 추출 가능 필드 46개(제목 4단계×3 포함)를 경로·타입·설명으로 준다(`:27-67`).
   - 각 필드에 **evidence(원문 10~60자 그대로 인용)** 를 요구한다.
   - 원문에 없는 필드는 **아예 내지 말라**고 지시한다(기본값으로 채우기 금지).
   - 필드로 표현할 수 없는 요구(장 제목 가운데 정렬, 쪽수 상한, 편집 소프트웨어 등)는 `manual` 목록으로 돌린다.
3. **결정적 형변환·범위 검사(`:174-262`).**
   - 중국식 글자 크기(四号=14pt, 小四=12pt…)를 포인트로 바꾼다.
   - 여백 mm→cm, 범위 검사(글자 크기 5~42pt, 여백 0.5~10cm 등)를 한다.
   - 변환할 수 없는 값은 `dropped`에 기록한다.
4. **근거 원문 대조(`:264-273`).** 공백·문장부호를 지운 뒤 부분문자열로 비교한다. 말줄임표로 이은 근거는 3자 이상 조각 하나라도 맞으면 인정한다.
5. **값과 근거의 극성 검사(`:285-334`).**
   - 부정 사전(不得·禁止·不允许…)과 허용 사전으로 "허용/금지" 방향이 근거 문장과 맞는지 본다.
   - 숫자 값은 근거에 그 숫자의 아라비아·한자 표기가 실제로 있는지 본다.
   - 불일치면 `verified: false`에 사유를 붙인다(`:404-426`).
6. **누락 탐지(`:361-398`).** 창 안에 "下划线" 같은 주제어가 있는데 대응 필드도 manual 항목도 없으면 원문 문장을 `omissions`로 보고한다. "不作要求·不限" 바로 앞의 언급은 면제한다.
7. **미지정 필드 처리(`:71-84, 457-472`).** 원문이 정하지 않은 형식 수치는 `null`(점검 안 함)로 둔다. 일관성 규칙(전문 다수결)이 대신 받친다.

- **우리 대응.** extract의 `WritingGuideline`(설계서 6.3, 7.3절)과 그대로 맞는다.
- **차이.** 우리는 locator가 블록 ID라서 2·4단계를 `block_id`+`quote` 검증으로 바꾼다. 글자 크기는 한국 RFP 표기("13포인트", "13pt", "휴먼명조 13")에 맞춘다. 필드에는 분량(쪽)·용량(MB)·블라인드·편집기·제출형식을 더한다.

#### 2.1.5 지정 목차·제출서류(投标文件格式) 추출과 위치 검증

파일은 `outlineFormatExtraction.cjs`다.

- **입력.** Word 원본은 C# 헬퍼가 "블록번호 [표지] 텍스트" 줄로 만든다. PDF는 Markdown에 `L000123 |` 줄번호를 붙인다(`:41-84, 99-110`).
- **프롬프트(`:99-144`).**
  1. 招标文件이 제출 문서의 구성과 서식을 주는 "격식 장"이 있는지 **내용 기능으로** 판단한다. 제목 문구로 판단하지 않는다.
  2. 있으면 그 장의 조목을 **합치지도 나누지도 더하지도 빼지도 말고** 원문 순서·계층대로 노드로 만든다. 제목은 번호·서식 표지만 떼고 그대로 옮긴다. 각 노드에 원문 위치 `source{start,end}`를 단다. 낙찰 후에만 쓰는 서식에는 `post_award=true`를 표시한다.
  3. 없으면 响应文件要求를 바탕으로 평평한 1차 목차만 만든다.
- **결정적 검증(`:147-258`).**
  - 위치가 원문 범위 안인지, start<end인지 본다.
  - 격식 장 구간끼리 겹치지 않는지, 형제 노드가 위치 순서대로이고 서로 겹치지 않는지, 자식이 부모 구간 안에 있는지 본다.
  - **제목 문자열이 그 위치의 앞 3개 블록 텍스트에 실제로 들어 있는지** 본다.
  - 위반은 blocking 이슈로 에이전트에 돌려보낸다.
- **content_mode 분류(`:17-20`, `outlineGenerationTaskV2.cjs:51-58, 817, 900`).** 목차 잎마다 처리 방식을 붙인다.
  - `ai-generate`(본문 작성)
  - `template-fill`(서식 칸 채우기)
  - `rule-page`(평가항목별 쪽 대비표, 대비표, 편차표처럼 招标文件 요구 한 줄에 한 행인 표. `rule_basis`=technical/business/both)
  - `directory-generate`(제안서 자체 목차)
  - `manual-fill`(사람이 작성)
  - `other`
- **우리 대응.** extract의 `prescribed_toc`·`required_documents`(설계서 6.3)와 plan의 `OutlineNode.origin`(6.4), render의 별지 채우기(7.9)에 대응한다. 우리 TOC-001("지정 목차와 일치")의 기준 데이터를 이 방식으로 만들 수 있다.

#### 2.1.6 평가기준 기반 목차 생성(V2)

파일은 `outlineGenerationTaskV2.cjs`(1,806줄)이고, 에이전트 다단계 절차다.

1. **1차 목차.** 기술 문서를 따로 묶을 때 **1차 목차 = 技术评分大项, 원문 순서와 공식 명칭 유지**로 정한다. "기술방안" 같은 바깥 묶음 장은 금지한다(`:768-797`).
2. **평가항목 구조화와 배치 계획(`:840-863`).**
   - 技术评分项만 `technical-score-groups.json`으로 뽑는다: `{requirement_id: R1…, title, description, detail_points[]}`.
   - 技术评分要求는 항목이 아니라 제약으로만 쓴다.
   - `score-directory-plan.json`에서 **모든 R이 mappings에 정확히 한 번** 나타나야 한다.
   - 합치기·나누기·누락·새 동급 대항목 추가 같은 편차는 **반드시 사용자 승인**(ask-user)을 받는다.
3. **잎 수 목표(`:341-362`).**
   - 총 글자 수 목표를 장당 글자 수(기본 3,000자)로 나눠 "AI 생성 잎" 수를 정한다. 최소·최대가 함께 있으면 평균을 쓰고, 상한만 있으면 −2, 하한만 있으면 +2를 한다.
   - 가지별 배분은 **LLM이 정한다.** 기준은 평가항목 수, 세부점 수, 복잡도다(`:823-836`).
   - **배점을 직접 쓰지 않는다.**
4. **하위 목차 생성(`:865-906`).** 계획의 `score_item_level` 층에 평가항목 노드를 만든다. `detail_points`는 그 아래 층을 만드는 데 쓴다.
5. **결정적 심사 문맥(`:664-731`).**
   - 프로그램이 잎 수(허용 범위 ±2), 최대 깊이(6), content_mode 유효성을 계산한다.
   - **가지별 기대 제목과 실제 제목의 누락·초과 목록**(`collectScoreMappingCoverage`)도 계산한다.
   - LLM 심사관은 이 결과를 "그대로 채택"하고 의미 커버리지·근사 중복·전문성만 판단한다(`:961-994`).
6. **노드 정체성.** 노드 ID는 프로그램이 주는 UUID이고, 표시 번호는 순서에서 계산한다. "ID로 번호·층·순서를 추정하지 말라"(`AGENTS.md:32`). 우리 `OutlineNode.id`(S-3-2)와 `number`(Ⅲ.2) 분리 설계와 같다.

#### 2.1.7 본문 생성: 전역 사실, 사실 결손 모드, 쪽 골격

- **전역 사실(SSOT, `globalFactsTaskV2.cjs:219-292`).**
  - 본문 전체가 같은 값을 써야 하는 사항(공기, 인력 역할, 서비스 약정 등)을 `groups[{id,title,content}]`로 먼저 확정한다.
  - 인력·자격·실적은 资信库(사내 자격·인력 DB)의 실제 기록만 쓴다(`:252-262`).
  - 본문은 이 사실과 충돌하면 안 된다(`contentGenerationAgent.cjs:76-83`).
- **사실 결손 3모드(`globalFactsTaskV2.cjs:88-97`).**
  - `placeholder`: 값이 없으면 **반드시 "【待填写】"로 글자 그대로** 쓴다. "待定·TBD" 같은 변형은 금지다.
  - `omit`: 구체값 없는 올바른 포괄 약속으로 쓴다.
  - `fabricate`: 문맥에 맞는 그럴듯한 값을 만든다.
  - **기본값은 `fabricate`다**(`globalFactsTask.cjs:8-10`, `contentGenerationTask.cjs:112-114`, `technicalPlanStore.cjs:353-355`). 우리는 placeholder 모드만 쓴다(FACT-001과 연결).
- **서식 칸 채우기(`businessTemplateFillTask.cjs:404-411`).**
  - 인력·자격·실적은 资信库 실제 기록 중에서만 고른다.
  - **가격·금액·날짜와 근거 없는 값은 `unresolved`로 넘긴다.** 프로그램은 그 자리에 "【待填写：…】"를 일괄 표시한다.
  - 에이전트가 직접 "【待填写】"를 쓰거나 "暂缺·待补充"을 쓰는 것은 금지다. 우리 별지 채우기(7.9)와 FACT 규칙에 바로 맞는다.
- **쪽 골격(layoutBudget, `src/shared/layoutBudget/*`).**
  - 출력 서식 설정에서 쪽당 글자 수를 결정적으로 계산한다(`pageMetrics.ts:179-235`).
    - 한 줄 글자 수 = ⌊본문폭 ÷ 글자폭⌋
    - 쪽당 줄 수 = ⌊본문높이 ÷ 줄높이⌋
    - 단일 줄 높이 계수 1.3(`:26`)
  - 생성 **전에** 절을 블록 열(단락 90~420자 구간, 그림 위치·크기, 표)로 미리 배치한다. 그림이 다음 쪽으로 밀리면 앞 단락 할당량을 늘려 쪽을 채우는 전방 bin-packing을 쓴다(`sectionSkeleton.ts:1-38, 664-698`).
  - LLM에는 블록 목록과 블록별 글자 수 구간만 주고 "구간 준수는 경성 조건"이라고 한다(`skeletonPrompt.ts:89-180`).
  - 우리 설계 7.6절 "분량 맞춤(쪽당 글자 수 추정→렌더 실측 보정)"의 구현 예다.

#### 2.1.8 점검: 废标项·오탈자·논리

- **3라운드 점검(`rejectionPrompts.ts:13-137`).**
  - 입력: 해석 단계의 无效投标/废标项 결과 + 사용자 정의 점검 항목 + 투찰서 Markdown 전문.
  - ① 분석: 전자 문서로 판단 가능한 항목을 고른다. 서명·날인·밀봉·지류·현장 행위는 **명시적으로 제외**한다.
  - ② 점검: 증거가 있는 위험만 초안으로 낸다.
  - ③ 확정: 중복을 지우고 빠진 것을 채운 뒤 JSON으로 낸다: `{type: invalidBid|rejectionItem, severity, title, requirement, bidEvidence, riskReason, suggestion}`.
  - 핵심 규칙은 **"그림·스캔본 내용이 안 보인다는 이유로 '자료 누락'을 판정하지 말라. 장 제목·목차 항목·첨부 제목·쪽 단서·그림 자리표시자 같은 구조적 단서가 있으면 제출 단서로 본다"** 이다(`:39, 59, 83-84, 113`).
- **장문 롤링 점검(`rejectionCheckTask.cjs:1021-1162, 1326-1370`).**
  - 투찰 패키지가 컨텍스트보다 길면 조각을 차례로 읽는다.
  - LLM은 **증분 patch**만 낸다: `evidenceAdds`, `pendingRiskAdds/Updates/Resolves`, `confirmedRiskAdds`.
  - 완전한 상태는 프로그램이 유지한다.
  - "현재 조각에 없다"는 누락 확정이 아니라 pending이다. 뒤 조각에서 증거가 나오면 resolve된다.
  - 끝에 후보를 배치로 확정하고 전역 병합한다.
  - 우리 COV·실격 대비 LLM 점검에서 100쪽 넘는 제안서를 다룰 때 그대로 쓸 수 있는 상태 기계다.
- **오탈자 점검(`rejectionPrompts.ts:139-175`, `rejectionCheckTask.cjs:271-353`).**
  - LLM이 `wrongText`와 `originalExcerpt`를 내면 프로그램이 **원문에서 위치를 찾는다.** 찾지 못한 결과는 버리고, 앞뒤 문맥을 붙여 다시 인용한다.
  - 우리 설계의 "인용 검증"(7.3 C)과 같은 원리다.
- **논리·일관성 점검(`rejectionPrompts.ts:177-217`).** 같은 업무의 인원 명단, 장비 모델, 공기, 금액, 수량, 서비스 기간, 사업명, 기술 파라미터가 앞뒤로 다르면 찾는다. 우리 CONS-001의 LLM 보조판이다.

#### 2.1.9 점검: 暗标(블라인드) 규칙 엔진

- **구조.** C# 규칙 64개를 범주 순서(개인정보→구조→그림→쪽→단락→글꼴→텍스트→표→일관성)로 등록한다(`openxmlhelper/.../BlindCheck/Rules/RuleCatalog.cs:1-24`). 규칙 ID 집합은 `blindCheckPresets.cjs:185-198`에 있다. 모든 규칙은 **결정적**이다.

| 범주 | 규칙(심각도) | 우리 대응 |
|---|---|---|
| 개인정보 | `privacy.keyword` 신원 노출(H) | BLD-001 |
| 개인정보 성격의 구조 | `struct.doc_props` 문서 속성(H), `struct.hyperlink`(H), `struct.field` 필드 코드(H), `text.hidden` 숨은 글자(H), `image.meta` 그림 메타데이터(H), `image.vector` 벡터 그림 속 글자(H) | BLD-003, BLD-001 확장 |
| 구조 | `struct.revision` 미수락 변경 추적(H), `struct.comment` 메모(H), `struct.header_footer` 머리말·꼬리말 내용(H), `struct.empty_paragraph`(M), `struct.page_number_text`(M), `struct.toc`(M), `struct.heading_number`(M), `struct.textbox`(L), `struct.bookmark`(L) | 신규 BLD(변경 추적·메모 잔존), TOC-001 |
| 쪽 | `page.paper_size`(M), `page.orientation`(L), `page.margins`(M), `page.columns`(L), `page.sections`(L), `page.background`(M) | FMT-002 |
| 단락 | `para.alignment`, `para.line_spacing`, `para.first_line_indent`(M), `para.space_before_after`, `para.page_break_before`, `para.snap_to_grid`(L) | 스타일 정책(minor) |
| 글꼴 | `font.chinese`, `font.western`, `font.size`, `font.bold`, `font.italic`, `font.underline`, `font.color`, `font.highlight`, `font.effects`(M), `font.char_spacing`, `font.scaling`, `font.script`(L) | FMT-001, FMT-003 |
| 텍스트 | `text.english_punct`, `text.spaces`, `text.linebreak`, `text.tabs`, `text.irregular`, `text.halfwidth_punct`, `text.fullwidth_digit`, `text.fullwidth_latin`(L) | LANG(minor) |
| 표 | `table.font`, `table.size`, `table.shading`(M), `table.indent`, `table.style`, `table.nested`, `table.alignment`, `table.merge`(L) | FMT-001(표 최소 글자) |
| 그림 | `image.color`, `image.graphic_color`(M) | 흑백 요구 시 |
| 일관성 | `consistency.heading_format`, `heading_numbering`, `heading_level_jump`, `heading_content`, `body_format`, `mixed_fonts`(L, 전문 다수결로 소수파 탐지, AI 재검토 후보) | minor 스타일 |

- **신원 노출 탐지기(`PrivacyRules.cs:6-75`).** 탐지 대상은 다음과 같다.
  - 사용자 민감어
  - 자기지칭(我公司·我司·本公司…)
  - 강한 접미사로 찾는 회사명(有限公司 등). 제3자(招标人·监理·供电公司 등)는 기본으로 무시한다.
  - 서식 필드 라벨, 저작권 표기
  - 휴대전화·유선전화, **신분증 번호(가중합 체크섬)**, **통일사회신용코드(체크섬)**
  - 이메일·URL·도메인, 계좌번호, 자리표시자(XXX·某公司)
- **판정 분리.** 회사명·라벨·계좌·자리표시자는 문맥을 봐야 하므로 **후보**로 표시해 AI 재검토에 넘긴다. 민감어·자기지칭·연락처·증번호는 프로그램이 확정한다(`:64-75`). 재검토 결과는 후보에 대해서만 결론을 낼 수 있고, 프로그램 결과를 덮을 수 없다(`blindCheckReview.cjs:190-320`).
- **사전값.** 내장 사전값(`blindCheckPresets.cjs:6-143`)이 있고, 지역별 참고 사전값은 "공개 자료 정리, 공식 요구 아님, 招标文件 우선"이라고 밝힌다(`:143-183`). 우리 설계 D4(프로필·provisional 표시)와 같은 태도다.
- **자동 수정.** 일부 규칙에 수정기가 있다(`BlindCheck/Fix/*`). 문서 속성 지우기, 변경 추적 수락, 머리말·꼬리말 비우기, 서식 맞춤 등이다.

#### 2.1.10 查重: 투찰자 사이 유사도(围串标 탐지)

`duplicateCheckService.cjs`(2,869줄)는 **여러 투찰자의 제안서끼리** 비교하는 담합 탐지 도구다. 우리 제품(단일 투찰자)과 목적이 다르지만 부품 일부는 쓸 만하다.

- **메타데이터 지문(`:15-100, 324-347, 703-1094`).** 다음 값을 뽑는다. 우리 **BLD-003(파일 메타데이터 블라인드 점검)** 추출기의 원형이다.
  - DOCX core·app 속성(작성자, 최종 수정자, 회사, 템플릿, 편집 시간)
  - **Word RSID(편집 세션 ID) 지문**
  - OLE 스트림 구조
  - PDF Info·XMP·trailer ID·첨부 이름
- **목차 유사도(`:1328-1452`).** 문자 bigram Dice와 LCS 비율로 잰다. 위험 경계는 ≥0.75 high, ≥0.55 medium, ≥0.35 low다.
- **문장 중복과 招标文件 출처 제외(`:1665-1996`).**
  - 문장을 정규화하고 정보량이 적은 문장을 거른다.
  - **招标文件에서 온 문장**은 다섯 단계로 판별해 중복에서 뺀다: 정확 일치 → 엄격 키 → 서식 필드 → 골격 키 → bigram 근사(길이 30자 이상이면 포함률≥0.9, Dice≥0.82, 길이비≥0.5).
  - 우리에게는 "RFP 문장 그대로 베끼기 비율"이나 "KB 재사용 유사도 계산에서 RFP 인용 제외"에 쓸 수 있다.
- **그림 중복.** 그림 바이트의 SHA-256으로 판정한다(`:2652`). 지각 해시(BLD-002)는 없다.

#### 2.1.11 排版·내보내기

- **경로.** Markdown이 아니라 **제한 HTML**(허용 태그 목록)로 본문을 받는다(`skeletonPrompt.ts:89-160`). C#이 Word에 삽입한다(`Jobs/InsertBodyHtmlAction.cs`, `RestrictedHtmlWordInserter.cs`).
- **목차.** Word 기본 TOC 필드(`\o \u`, PAGEREF 북마크)를 쓴다. 쪽 번호 자리에 "0000"을 넣어 두었다가, Main이 조판 결과를 잰 뒤 `fill-toc-page-numbers`로 채운다(`TableOfContentsBuilder.cs:18-30`, `FillTocPageNumbersAction.cs`).
- **우리와의 관계.** 우리 render는 HWPX(python-hwpx)라서 코드는 쓸 수 없다. "제한된 블록 구조로 받아 렌더러가 스타일을 입힌다"와 "조판 후 쪽 번호를 되채운다(추적표 `pages`)"는 아이디어는 그대로 쓴다.

#### 2.1.12 주의할 점

- **사실 결손 기본 모드가 `fabricate`다(2.1.7절).** 이식할 때 이 경로를 아예 없앤다.
- **해석 결과가 자유 Markdown이다.** 평가표 합계 검증 같은 결정적 검산이 없다. 위치 정보도 자유 텍스트다.
- **비이식 대상.** 라이선스 활성화, 텔레메트리, 원격 공지 코드(`licenseService.cjs`, `analytics/`)는 가져오지 않는다. 이 프로젝트의 `AGENTS.md:54`는 텔레메트리 제거를 금지하지만, 그것은 저장소 기여 규칙이지 라이선스 조건이 아니다. AGPL은 수정본에서 이를 빼는 것을 막지 않는다.

### 2.2 BidMaster-Pro

#### 2.2.1 구조

- **스택.** FastAPI + SQLAlchemy(PostgreSQL) + Celery/Redis + MinIO + Chroma이고, 데스크톱은 Electron/React다(`README.md:112-200`).
- **4단계.** 招标解读 → 投标生成 → 投标检查 → 文档排版. 각 기능은 `Skill` 클래스(`core/skill_engine/base.py`) 하나다. 라우터가 스킬을 직접 불러 쓴다(`services/routers/*.py`).
- **README와 실제의 차이.**
  - README는 LiteLLM·LangGraph를 내세우지만 실제 LLM 호출은 `openai.AsyncOpenAI`를 직접 쓴다(`core/llm_gateway/gateway.py:1-6, 14, 52-70`). 주석에 "OpenBidKit의 직접 호출 방식을 참고"라고 적혀 있다.
  - JSON 복구도 "OpenBidKit의 다층 용결 메커니즘 참고"다(`json_repair.py:1`).
  - LangGraph 편성(`core/agent_engine/orchestrator.py`)은 주 흐름에 쓰이지 않는다.
- **사람 확인 게이트.** 파일 하나(`.stages/<stage>/.reviewed`)로 단계 통과를 기록한다(`core/agent_engine/gate_keeper.py:8-48`).

#### 2.2.2 LLM 게이트웨이

| 측면 | 구현 | 위치 |
|---|---|---|
| 공급자 | OpenAI 호환 하나(DeepSeek 기본). 시도마다 `fallback_models`로 내려감 | `gateway.py:23-37, 344-352` |
| JSON | `collect_json`은 `response_format=json_object`를 강제하고, 미지원 오류면 빼고 재요청 | `gateway.py:146-166, 188-271` |
| 복구 | `<think>` 제거 → 코드펜스 → 괄호 균형 → 잘못된 이스케이프 → 꼬리 쉼표 → 따옴표 없는 키 → 잘린 JSON 닫기 → LLM 복구 | `json_repair.py:22-315` |
| 스트림 중단 | 받은 부분을 assistant 메시지로 넣고 "이어서 써라"로 재요청 | `gateway.py:273-342` |
| 길이 | 기본 `max_tokens` 8192. 본문은 `min(word_count×2, 8192)` | `gateway.py:89`, `content_gen_skill.py:308-312` |
| 동시성 | `asyncio.Semaphore`: 해석 3, 목차 하위 4, 분할 본문 3 | `tender_interpret_skill.py:363-364`, `outline_gen_skill.py:25, 421`, `content_gen_skill.py:475` |
| 온도 | 추출·점검 0.1, 목차 0.7, 본문 0.4~0.5 | 각 스킬 |

#### 2.2.3 招标解读: 15차원 병렬 추출

`services/interpret/skills/tender_interpret_skill.py`

- **차원(`:8-184`).** 15개 차원마다 영문 snake_case 필드 스키마가 있다: 项目信息, 甲方, 资格要求, 技术需求(★▲ 강제 파라미터 포함), 评分细则, 废标红线, 保证金, 开标, 评标办法, 商务评分, 合同, 风险, 竞争态势, 时间节点, 联系人.
- **검색.** 차원별 키워드 사전으로 해당 줄과 앞뒤 3줄을 모아 **최대 12,000자**만 보낸다(`:431-466`). 키워드가 없으면 앞 12,000자를 보낸다.
- **프롬프트(`:377-395, 417-429`).** 다음을 지시한다.
  - 정해진 필드만, 영문 키로 낸다.
  - 원문에서 글자 그대로 옮기고 지어내지 않는다.
  - 없으면 `null`로 둔다.
- **후처리(`:186-345`).** 중문·camelCase 키를 표준 키로 사상하고, 반복 문자·잡음(`z`, `D1D`)을 지운다. 모델 출력 품질 문제를 사후에 메우는 흔적이다.
- **평가.** "차원별 병렬 + 키워드 창"은 비용이 싸다. 하지만 평가표처럼 표가 긴 섹션은 12,000자 자르기로 잘릴 수 있다. 원문 위치도 남기지 않는다.

#### 2.2.4 평가 매트릭스·리스크·실질 요구 추출

- **평가 매트릭스(`scoring_matrix_skill.py:20-63`).** 해석된 评分细则 JSON을 다시 LLM에 넣는다. 결과는 `{seq, category(商务/技术/价格), item, score, criteria, response_section(권장 응답 장), status}` 행이다. 합계는 코드가 계산하지만 **원문 총점과 대조하지 않는다.**
- **리스크 경보(`risk_alert_skill.py:18-80`).** 배타 조항(특정 상표·지역 제한·과도한 자격), 편향 평가, 불합리 요구, 법규 충돌을 원문·위치·법적 근거·**질의·이의 요점**과 함께 낸다. 우리 **질의서 초안**(설계서 7.3 B)과 Go/No-Go 보조에 응용할 수 있다.
- **실질 요구 추출(`mandatory_req_extract_skill.py:18-62`).** ★▲ 강제 파라미터(MP-001…), 废标红线(DQ-001…), 경성 자격(HQ-001…), 배점 가중치를 한 번에 뽑는다. 내부 ID를 붙이는 방식이 우리 `X-nnnn`과 같다.

#### 2.2.5 목차 생성(`outline_gen_skill.py`)

1. **1차 목차(`:183-237`).** 招标文件 앞 15,000자와 평가 매트릭스 문자열을 넣는다. "1차 목차 명칭을 평가기준의 장 명칭과 최대한 일치, 모든 평가항목을 덮을 것, 8~15개, 投标函·资格审查·技术方案·商务报价 포함"을 지시한다.
2. **2·3차 목차(`:240-258, 403-461`).** 1차 장마다 병렬로 만든다(장당 2·3차 3~5×2~3개, 120초 제한).
3. **검증(`:138-153`).** 1차 장이 5개 이상인지, "章节N" 같은 자리표시자 제목이 없는지, 절반 이상의 장에 하위가 있는지 본다. 실패하면 한 번에 생성하는 방식으로 내려간다(`:498-512`).
4. **평가항목→장 매핑(`:170-180, 465-494`).** 한자 2~4자 n-gram 집합의 적중률과, 이름 포함 시 +2.0 가산으로 계산한다. 0.3 이상이면 연결한다(결정적).
- **분량 배분.** 배점과 무관하다. 본문 목표 글자 수는 장 제목 키워드로 정한다: 기술 4,000, 서비스 3,500, 관리 3,000, 기타 2,500자(`content_gen_skill.py:104-115`).

#### 2.2.6 본문 생성(`content_gen_skill.py`)

- **4모드.** A 일반, B RAG, C 템플릿 채우기, D 외부 데이터(`:42-102`).
- **데이터 의존 장 차단(`:10-14, 55-68, 117-132`).** 제목에 人员配置·业绩·资质证书·合同·财务报表 등이 있는데 RAG가 없으면 **생성하지 않고 자리표시 안내문을 낸다.** 우리 FACT 원칙과 같은 방향이다.
- **system 프롬프트(`:204-246`).** 구조(### / ####), 소절당 500자 이상, "본 회사/투찰인" 호칭, **"기업명·자격증·사례·인력·계약금액을 지어내지 말 것"**, 반복 글자·잡문자 금지를 요구한다.
- **절단 감지와 이어쓰기(`:139-202`).** 끝 800자를 문맥으로 최대 2회 이어 쓴다. 4,000자 이상이면 계획 → 소절별 병렬 생성으로 나눈다(`:389-498`).
- **버그.** A·B 모드는 Markdown 본문을 요구하면서 `collect_json`(JSON 모드)으로 호출한다(`:308-313, 346-350`). 출력 형식 지시와 API 모드가 어긋난다.

#### 2.2.7 21개 점검 규칙

**"21"의 정체.** 프런트엔드 점검 화면 목록(`packages/desktop/renderer/src/pages/CheckPage.tsx:259-279`)에서 "全面检查"를 뺀 21개다. 백엔드에서는 19개가 `_CHECK_SKILL_MAP`(`services/routers/check.py:690-710`)에 있다. `selfcheck`는 별도 처리이고, `scoreCoverage`는 생성 라우터(`generate.py:292-305, 378-394`)가 `structure_template_skill.py:192-294`로 처리한다. "全面检查"는 이 가운데 15개를 병렬로 돌린다(`check.py:480-500`).

공통 사항: LLM 규칙은 모두 `collect_json(temperature=0.1)`을 1회 호출하고, 입력을 **招标文件·투찰서 각 3,000~8,000자에서 자른다.** 100쪽 제안서의 앞부분만 본다는 뜻이다.

| # | 키(화면 라벨) | 파일:줄 | 방식 | 입력 | 출력 | 판정 로직 | 우리 대응·이식 판단 |
|---|---|---|---|---|---|---|---|
| 1 | compliance (合规性检查) | `check/skills/compliance_check_skill.py:13-60` | LLM | 招标·투찰 각 6,000자 | items[requirement, source_location, response, response_location, status compliant/non_compliant/partial, severity, suggestion] | LLM이 "必须/应当/须/不得/禁止" 조항을 뽑아 대조. non_compliant·partial이 1건이라도 있으면 `has_critical_issues` | COV-001은 추적표로 결정적 판정. 이 프롬프트는 서술형 요구 보조 리뷰로만 사용 |
| 2 | disqualification (废标项检查) | `disqualification_check_skill.py:13-172` | LLM 3회 | 해석의 废标 조항(없으면 招标 6,000자에서 추출), 투찰 6,000/3,000자 | items[clause_id DQ-xxx, clause_type invalidBid/rejectionItem, response_found, response_content, response_quality 明确/模糊/缺失, risk_level, suggestion] | ①조항 추출 ②조항별 응답 확인(그림·스캔 미가시면 누락 판정 금지) ③누락 조항 보충·중복 제거·확정. high가 있으면 critical | OBK 3라운드의 단순판. 해석 결과 키 불일치로 ①이 매번 다시 돈다(2.2.9) |
| 3 | mandatoryReq (★▲参数对照) | `mandatory_req_check_skill.py:13-70` | LLM | 각 5,000자 | items[param_id MP-xxx, marker ★/▲, category, response_found, response_quality 明确响应/模糊表述/未响应/负偏离, status, severity] | critical이면서 미충족이면 high | 한국 RFP '필수' 요구사항·규격 대비 → COV-001 보조 |
| 4 | qualification (资质核查) | `qualification_check_skill.py:13-59` | LLM | 각 4,000자 + 투찰 마감일 | checks 5종: 유효기간, 증서 명칭 일치, 회사명 일치, 三证合一, 스캔 선명도 | 요약 failed 수 | FACT-003(KB 인증 만료)과 참가자격 하드 게이트(strategy, 결정적)로 대체. 미이식 |
| 5 | deposit (保证金核查) | `deposit_check_skill.py:13-64` | LLM | 각 4,000자 | 4종: 금액(분 단위까지), 납부 형식, 입금 시점, 보증서 유효기간(투찰 유효기간+30일) | fail 있으면 high | 입찰보증금은 제안서 범위 밖. 미이식 |
| 6 | signature (签章核查) | `signature_check_skill.py:13-63` | LLM | 각 3,000자 | 6종: 법인 대표 서명, 위임장, 공장(직인), 간인(骑缝章), CA 인증서, 밀봉 | 동일 | 전자 제출·사람 서명이라 미이식. 별지 서명란 존재만 SUB-002에서 확인 |
| 7 | validity (有效期核查) | `validity_check_skill.py:13-61` | LLM | 각 3,000자 | 4종: 투찰 유효기간, 보증서, 자격 유효기간, CA | 동일 | FACT-003 |
| 8 | pricing (报价核查) | `pricing_check_skill.py:15-111` | **결정적**(정규식) | 투찰 전문, 최고한도가 | ①"投标总价" 값 > 한도가면 fail ②대·소문자 금액 쌍을 나열만 함(일치 판정 없이 "사람 확인 필요") ③"단가×수량=합가" 줄 검산(오차 0.01) ④한도가 대비 95~98%면 pass, 미만 warning, 초과 fail | 가격은 비목표. ③ 산술 검산 아이디어만 정량서식·투입공수 합계에 재사용(M3). ④는 이식 금지 |
| 9 | consistency (一致性校验) | `consistency_check_skill.py:15-183` | **규칙+LLM** | 투찰 5,000자, 招标 2,000자, project_facts | 규칙: 사업명·회사명·발주처·기간·예산 숫자가 투찰 전문에 부분문자열로 있는지(`:59-128`). LLM: 공기·금액·인력·약정·기업정보 일치, 논리 오류, **지어낸 정보 의심**(`:141-166`) | critical≥1 또는 major≥3이면 high | CONS-001(SSOT fact 기반 결정적) + LLM 보조 |
| 10 | duplicate (标书查重) | `duplicate_check_skill.py:21-323` | **결정적**+LLM(중위험 이상) | 투찰 전문, 참고문서(다른 사업의 bid 최대 10건. 전면 점검에서는 빈 목록) | 내부 중복: 50자 넘는 단락끼리 SequenceMatcher≥0.7. 외부 유사도: max(SequenceMatcher, 공백 단어 Jaccard, 문자 3-gram Jaccard). 200자 창·100자 보폭 슬라이딩, 장 제목 집합 Jaccard. LLM: 템플릿 흔적·의역 | max≥0.7 high, ≥0.4 medium | 신규 minor 규칙 후보: 자사 과거 제안서 과다 재사용·내부 중복. 화이트리스트(아래) 함께 |
| 11 | docIntegrity (文件完整性) | `doc_integrity_check_skill.py:13-63` | LLM | 각 3,000자 | 6종: 정·부본 부수, 밀봉 봉투 표지, 간인, 쪽 번호 연속, 목차-본문 대응, 첨부 목록 | fail 있으면 high | SUB-002·TOC-001·REND-001을 결정적으로 |
| 12 | fitScore (贴合度评分) | `fit_score_skill.py:13-62` | 규칙+LLM | 각 4,000자 | 상투어 7개 적중 수 + 4차원 가중점수(내용 40, 기술 맞춤 30, 평가항목 커버 20, 废标 응답 10) | 점수만 | LLM 리뷰어(참고용, 게이트 미사용). 상투어 목록은 LANG 후처리 필터 아이디어 |
| 13 | selfcheck (废标自查清单) | `selfcheck_list_skill.py:5-110` | **결정적** 집계 | 다른 스킬 결과 | SC-01~SC-20 항목을 담당 스킬 결과로 pass/fail/pending 판정 | 전부 pass일 때만 `can_submit` | package의 제출 전 점검표(G5) 구조 참고. 항목은 한국형으로 재작성 |
| 14 | crossCheck (交叉比对) | `cross_check_skill.py:13-75` | LLM | 각 6,000자 | items[scoring_item, score, response_status answered/partial/missing, gap_analysis], risk_assessment{missing_score, partial_score, max_obtainable_score} | missing이 있으면 `has_missing_items` | COV-002(결정적) + LLM 리뷰어 '세부항목 채점' |
| 15 | aiTextCheck (AI文本检查) | `ai_text_check_skill.py:13-66` | LLM | 투찰 8,000자 | issues[type spelling/punctuation/entity, original, location, suggestion, severity] | high가 있으면 critical | 한국어 맞춤법(LANG). OBK의 위치 검증 방식(2.1.8)이 더 낫다 |
| 16 | riskScore (风险评分) | `risk_score_skill.py:5-164` | **결정적** | 저장된 점검 결과 | 6차원 가중합(필드 중첩 .20, 가격 .20, 메타데이터 .15, 구조 .15, 텍스트 .20, 이상 문자열 .10). 데이터 없는 차원은 50점 | ≥70 high, ≥40 medium | 미이식. 우리 게이트는 blocker 수로 판정 |
| 17 | sampleReport (样品/检测报告) | `sample_report_check_skill.py:13-78` | LLM | 각 6,000자 | CMA/CNAS 자격, 검사항목 대응, 유효기간 | fail 있으면 critical | SW 용역은 대부분 해당 없음(시험성적서·GS인증 요구 사업만) |
| 18 | jointBid (联合投标协议) | `joint_bid_check_skill.py:13-82` | LLM | 각 6,000자 | 컨소시엄 자격(낮은 등급 기준), 협정 내용, 중복 투찰 | 동일 | 공동수급 협정서(별지) 존재와 지분 합계 100%를 결정적으로 점검(M3) |
| 19 | ebidSubmit (电子投标提交) | `ebid_submit_check_skill.py:13-90` | LLM | 각 6,000자 | 형식, CA·전자서명, 완결성, 제출 규정 | 동일 | SUB-001(PDF·용량·파일명) 결정적 |
| 20 | pricingLogic (报价逻辑闭环) | `pricing_logic_check_skill.py:13-87` | LLM | 각 6,000자 | 총괄·세부 합계, 인일(人天)×단가, 비용 배분 | 동일 | 가격은 비목표. 투입공수(M/M) 일관성만 CONS-001 |
| 21 | scoreCoverage (评分覆盖检查) | `generate/skills/structure_template_skill.py:192-294` | **결정적** | 평가 매트릭스, 목차 트리 | 항목명과 목차 제목의 부분문자열 포함 → 실패 시 공백 단어 포함. 배점 가중 커버리지율 | 비율만 | COV-002·COV-003. 우리는 ID 연결(추적표)로 판정하므로 이름 매칭은 매핑 제안용 보조 |

**21개 밖의 점검 부품.**
- `whitelist_filter`(`whitelist_filter_skill.py:12-171`): 查重 오탐을 3층으로 거른다. ① 상투어·자리표시자 정규식 화이트리스트 ② 유사도<0.7 제거 ③ LLM 오탐 판정(업계 표준 문구·법령 인용·招标 원문 인용·상용 약정).
- `check_report_export`: Markdown/HTML 보고서.
- `CheckNormalizer`: 스킬마다 다른 결과 스키마를 `findings[{status, severity}]`로 통일한다(`core/skill_engine/check_normalizer.py:1-60`). 결과 스키마를 처음부터 하나로 강제해야 한다는 반면교사다.

#### 2.2.8 排版

- **`docx_format_skill.py`(884줄).** 본문 단락 텍스트의 번호 패턴으로 제목 층을 추정한다(decimal/괄호/한자). 층별 글꼴·크기·간격을 적용하고, 동아시아 글꼴(`w:eastAsia`)을 같이 지정한다. 표 테두리·열 너비·쪽 번호 PAGE 필드를 넣는다(`:458-627`).
- **스타일 기본값.** `templates/default.yaml`(본문 仿宋_GB2312 12pt, 고정 줄간격 28pt, 제목 黑体 16/15pt, 여백 2.6/2.2/2.5/2.5cm).
- **목차.** Word 기본 제목 스타일(`Heading n`)에 의존한다(`bid_docx_export_skill.py:99-118, 167-196`).
- **자리표시자 치환.** `[XX公司]`, `【本公司】`, `${…}`를 사실값으로 바꾼다(`bid_docx_export_skill.py:345-372`).

#### 2.2.9 결함과 교훈

- **단계 사이 키 불일치(데이터 유실).** 해석 스킬은 영문 키(`budget_amount`, `bid_deadline`, `disqualification_clauses`)로 정규화한다(`tender_interpret_skill.py:14-18, 76-79, 166`). 그런데 점검 라우터는 중문 키(`"预算金额"`, `"投标截止日"`)와 `"clauses"`로 읽는다(`check.py:135, 182, 228, 769, 779, 791`).
  - 결과: 가격 점검의 한도가가 늘 `None`이다.
  - 자격 점검의 마감일이 늘 빈 값이다.
  - 废标 점검은 해석 결과를 못 쓰고 매번 다시 추출한다.
  - **Pydantic 스키마를 단계 간 계약으로 강제하는 우리 설계(5.3절)가 옳다는 사례다.**
- **입력 자르기.** 점검은 3,000~8,000자에서 자른다. 해석 차원은 12,000자다. 긴 제안서에서는 대부분을 보지 못한다.
- **출력 지시와 API 모드 불일치.** 2.2.6절의 버그다.
- **평가 매트릭스 검산 없음.** 원문 총점과 대조하지 않는다.

### 2.3 BiaoShu-SKILL

- **형태.** AI IDE(Trae 등) 스킬이다. `SKILL.md`가 호스트 에이전트에게 14단계 흐름을 지시하고, `scripts/*.py`는 보조 도구다(`SKILL.md:1-131, 275-357`). **스크립트에는 LLM 호출이 하나도 없다.** `generate_content.py`의 "생성"은 고정 문구 템플릿을 채우는 일이다(`:28-224, 314-822`). 실제 작문은 호스트 에이전트가 SKILL.md 규칙을 읽고 한다.
- **문서 해석.** PDF는 pdfplumber(첫 쪽 텍스트가 50자 미만이면 스캔본으로 보고 OCR을 안내만 함, `parse_bid_file.py:159-185`), DOCX는 python-docx(단락 다음 표), .doc는 pywin32 Word 자동화(Windows 전용), XLSX를 쓴다(`parse_bid_file.py:79-262`). Markdown 변환본은 `debug/bid_document.md`에 둔다.
- **평가기준 추출(`extract_scoring.py`, 정규식).**
  - 评分办法 장을 키워드로 찾는다. 다음 "第N章"이나 "一、" 제목에서 끝낸다(`:59-88`).
  - 대분류는 `[技术商务价格]+…(\d+)分`으로 찾는다(`:140-175`).
  - 항목은 "번호 + 이름 + N分" 세 패턴으로 찾는다(`:46-51, 205-225`).
  - 평가 방식(客观/主观/价格)은 키워드로 분류한다(`:39-44`). 키워드 추출에는 jieba를 쓴다.
  - **표 구조(병합 셀)를 다루지 못하고, 한 줄에 이름과 점수가 같이 있어야만 잡힌다.**
- **실격·자격 추출(`extract_requirements.py`).** "资质要求" 같은 머리말 이후 줄을 키워드로 분류한다. 废标 조항은 "废标条款/无效投标/不予受理" 구간에서 "未提供/超过/不符合/未响应"이 들어간 줄을 고른다(`:50-54, 217-243`). 재현율이 낮다.
- **평가기준→목차(`generate_outline.py:79-194`).** 대분류에 '技术'가 들어가면 "技术方案" 장, '商务'면 "项目实施与管理", '价格'면 "报价方案"을 만든다. 각 평가항목이 소절 하나가 된다. 항목이 없으면 고정 하위 장 비율(0.3/0.3/0.4)을 쓴다. 끝에 첨부 장(영업집조·자격·실적·인력증서 자리)을 붙인다(`:214-228`).
- **분량 공식(`SKILL.md:252-256, 526-529`, `check_word_count.py:81-117`).**
  - 목표 글자 수 = 배점 × (총쪽수 ÷ 총점) × 784 (주석은 "28행×28자=780"이지만 코드는 `28*28`=784)
  - 합격 범위는 목표의 0.75~1.25배다. 벗어나면 재작성을 지시한다.
  - 총점에 가격·상무 점수가 들어가므로 기술 장 분량이 과소 배정된다. 우리 식(정성 배점만 분모)이 더 정확하다.
- **자리표시자 규격(`SKILL.md:429-473`, `generate_placeholder.py:28-150`).** `[图片占位符]`, `[表格占位符]`, `[资质占位符]` 세 종류다. 각각 유형·설명·권장 크기 또는 열 구성 또는 요건을 적는다. 우리 `DraftBlock.figure`, `table` 스펙과 FACT-001 자리표시자의 표기 규칙으로 쓸 수 있다.
- **"AI 흔적 제거"(`humanizer.py:27-160`).** 상투어 치환, 접속 부사 삭제, 100자 넘는 문장 강제 분할, 같은 동사 3회 이상이면 동의어로 바꾼다. 의미를 훼손할 수 있어 **이식하지 않는다**(우리는 LANG 후처리 필터로 표시만 한다).
- **서식 표준(`format_docx.py:33-95`, `SKILL.md:476-513`).** 정부형(仿宋_GB2312 四号, 고정 28pt), 기업형, 도로공사형의 글꼴·크기·여백 표다.
- **결함.**
  - 템플릿 본문에 **근거 없는 수치**가 박혀 있다(`generate_content.py:332-335`: "提高业务处理效率30%以上", "降低运营成本20%以上").
  - `templates/bid_doc_*.md` 15개, `bid_knowledge_*.md` 5개는 인터넷의 입찰서 범본·해설 문서를 변환한 것으로 보인다. 원저작권이 불명확하므로 **코드 라이선스와 별개로 가져오지 않는다.**

### 2.4 BidPilot-AI

#### 2.4.1 구조

- **스택과 산출물.** FastAPI + Vue 3 + SQLite다. LLM이 없으면 Mock과 규칙 기반으로 돌아간다(`README.md:1-30`, `agents/__init__.py:184-200`).
- **워크플로 정의(`app/workflows/engine.py:41-189`).** 11개 노드다: parse_documents → extract_project_facts(G) → detect_addendum_conflicts → extract_requirements(G) → extract_scoring → generate_matrix → generate_outline(G) → retrieve_knowledge → generate_draft(G) → review_document → ready_to_export.
- **노드 정의(`NodeDefinition`).** 각 노드가 `inputs`/`outputs`/`dependencies`/**`invalidated_by`**/`human_gate`/`risk_level`/`idempotency_key`/`timeout`/`max_retries`/재시도 대기(5s, 30s)/`allowed_models`/`cost_limit`를 선언한다. 우리 설계 5.3절 "산출물 해시 키 DAG"의 선언부로 쓰기 좋은 형태다.
- **모델 라우팅(`agents/__init__.py:888-925`).** 추출은 fast 모델, 본문·리뷰는 quality 모델이다. 사업별 비용 한도를 둔다(`:98-183`).

#### 2.4.2 추출

- **위치 표지.** 모든 쪽 앞에 `[doc:{문서ID} page:{쪽}]` 표지를 넣는다. LLM이 `source_doc_id`·`source_page`를 같이 내게 한다(`:248-253, 344-349, 491-496`). 우리 블록 ID 방식의 간이판이다.
- **사실 추출(`:271-306`).** key는 project_name, bidder, budget, duration, deadline, deployment, warranty를 우선한다. 각각 confidence와 risk_level을 단다. 실패하면 정규식으로 대체한다(`:308-336`).
- **요구사항 추출(`:374-424`).**
  - 9,000자 조각마다 **`subject/action/condition/deadline/penalty` 5필드 분해**를 받는다. 유형은 qualification/technical/commercial/scoring/delivery/format이다.
  - "순수 사실(사업명·예산)은 요구사항으로 뽑지 말라"고 지시한다.
  - 앞 120자 기준으로 중복을 제거한다.
  - 규칙 대체판은 "必须/须/应当/不得/否决/废标" 줄을 고른다(`:426-466`).
- **평가표 추출(`:514-565`).** `{title, score, criteria, evidence, source_page}`, 입력 14,000자다. 대체판은 "N分"이 들어간 줄 전체를 항목으로 잡는다.
- **결함.**
  - `_chunk_text(chunk_size=9000, max_chunks=4)`는 **36,000자 넘는 텍스트를 말없이 버린다**(`:40-49`).
  - `_truncate_text`는 앞뒤 절반만 남기고 가운데를 지운다(`:31-37`). 평가표가 RFP 중간에 있으면 놓친다.

#### 2.4.3 补遗(정정공고) 영향 분석

1. **사실 diff(`app/agents/addendum_agent.py:4-84`).**
   - 문서 유형이 `addendum`인 파일의 쪽마다 정규식 5종(예산·공기·투찰마감·보증기간·배포방식)으로 값을 뽑는다.
   - 기존 `ProjectFact`와 공백·문장부호를 지운 값으로 비교한다.
   - 다르면 `ConfirmationTask(task_type="addendum_conflict", old_value, new_value, source_document_id, source_page, risk_level="high")`를 만든다.
   - LLM도, 텍스트 diff도 쓰지 않는다. 요구사항·평가항목 변경은 잡지 못한다.
2. **변경 신호(`app/workflows/dependency_graph.py:33-52`).**
   - `addendum_uploaded`는 `addendum_document`, `project_facts`, `requirements` 신호를 낸다.
   - 사람 확인 변경은 `manual_confirmation`, `project_facts`를 낸다.
   - 리뷰 변경은 `review_findings`, `draft_versions`를 낸다.
3. **영향 계산(`:54-114`).** 노드 순서대로 진행한다. 노드의 `invalidated_by`와 신호의 교집합(직접 적중)이나 상위 노드의 영향 여부(전파)로 영향 노드를 정한다. 결과는 다음과 같다.
   - 영향 노드: 사유, 우선순위, 위험도, 이전 결과 "will_replace"
   - 비영향 노드: "preserved"
   - 영향 노드 사이의 의존 간선
   - **고위험 노드나 사람 게이트 노드가 있으면 `confirmation_required`**
4. **미리보기 후 실행(`app/workflows/workflow_service.py:165-180`, `api/v1/workflows.py:103-115`).** 재실행 전에 영향 미리보기를 API로 보여 준다.

- **평가.** 전파 단위가 **단계(노드)** 다. "요구사항 SFR-012가 바뀌어 Ⅲ.2절과 추적표 12행이 재검토 필요" 같은 **항목 단위** 전파는 없다.
- **우리에게 쓸모 있는 것.** 설계서 7.11절이 이미 항목 단위로 정의했으므로 다음 세 가지다.
  - (a) 신호→무효화 선언표
  - (b) 재실행 전 영향 미리보기와 확인 게이트
  - (c) 충돌을 사람 확인 작업으로 만드는 방식(옛값·새값·출처 쪽)

#### 2.4.4 리뷰·신뢰도·근거 매트릭스

- **결정적 리뷰 4종(`app/application/review_export_service.py:46-157`).**
  - ① 응답 처리되지 않은 요구사항(`missing_requirement`)
  - ② 사실 key가 본문에 나오는데 사실 값이 없는 경우(`numeric_inconsistency`/`internal_conflict`)
  - ③ 인용 없음·미검증 인용(`citation_missing`)
  - ④ 과잉 약속 키워드(准确率, 99, 100%, 零故障, 绝对安全, 万无一失, 保证中标) → `unsupported_claim`(high)
  - ④는 우리 LANG-003에 대응한다. "99"처럼 너무 넓은 키워드는 오탐이 많다.
- **자동 수정 제한(`:332-347`).** high 위험이나 고위험 유형은 자동 수정하지 않는다. 저위험 허용 유형만 "【待确认】 인용 확인 필요" 문구를 **덧붙이는** 식이다. 사실을 새로 만들지 않는다.
- **신뢰도(`confidence_service.py:38-110`).** 사실 신뢰도 = 모델 0.20 + 출처 무결성 0.30 + **출처 쪽 본문에 값이 실제로 있는지** 0.23 + 값 구체성 0.13 + 충돌 없음 0.09 + 사람 확인 0.05. 요구사항은 구조화 필드 충실도를 더한다. 우리 `Extracted.confidence`(설계서 6.1)를 "rule=1.0, llm=교차검증"에서 이런 요인 분해형으로 넓힐 수 있다.
- **근거 매트릭스(`evidence_service.py:24-272`).** 요구사항 → 원문 쪽 인용 → 대응 절 → 초안 → KB 근거 → 리뷰 이슈를 한 줄로 잇는다. `coverage_status`는 conflicted / missing / pending_confirmation / covered(요구 원문 앞 20자가 초안에 있음) / partially_covered다(`:220-237`). covered 판정이 문자열 포함이라 약하다.
- **사람 편집 보호(`agents/__init__.py:709-713`).** `SectionProtection`이 켜진 절은 재생성하지 않는다. 낙관적 잠금(`expected_version_id`)으로 덮어쓰기를 막는다. 우리 `origin: human` 보호(5.3절)와 같다.
- **검수된 KB만 검색.** `audited_only=True`(`:598, 733`). 우리 KB의 `ContentBlock` 최종 검토일·승인 상태 필터로 대응한다.

#### 2.4.5 결함

- 2.4.2절의 텍스트 절단 문제가 있다.
- 补遗 사실 패턴이 5개뿐이다.
- `generate_outline`은 요구사항 80개만 보고 평가표를 쓰지 않는다(`:647-675`). 평가표 기반 목차가 아니다.

---

## 3. 횡단 비교

### 3.1 기능별 비교

| 기능 | OBK | BMP | BSS | BPA | 우리 설계 |
|---|---|---|---|---|---|
| 문서 정규화 | Markdown + Word 블록 번호(C#), MinerU 선택 | 텍스트+표 따로(순서 손실), MinerU OCR | Markdown(표는 단순 변환) | 쪽 단위 텍스트·표 | DocIR(셀 병합 보존, 블록 ID) |
| 원문 위치 | 목차 추출만 위치 검증. 해석은 자유 텍스트 | 없음 | 없음 | 문서ID·쪽 | 블록 ID + quote 검증 |
| 평가표 구조화 | Markdown(항목·배점·기준·출처) → 목차 단계에서 R1… JSON | 차원 JSON → 매트릭스 | 정규식 | LLM JSON(title·score) | 규칙 표 파서 우선 + LLM 보조 + 합계 검증 |
| 평가항목/규칙 분리 | **있음** | 없음 | 없음 | 없음 | 없음 → 도입 |
| 실격사유 | **无效/废标 경계 정의, 원문/경험 분리** | 废标红线 차원 + DQ-xxx | 키워드 줄 | 요구사항 risk 필드 | `eligibility`만 있음 → 확장 |
| 작성지침(형식) | **필드+근거+검증+누락 탐지** | 없음 | 없음 | 없음 | 정규식 패턴 사전 → 결합 |
| 지정 목차 | **위치 검증 추출** | 없음 | 없음 | 없음 | `prescribed_toc` → 결합 |
| 목차 생성 | 다단계 에이전트 + 결정적 커버리지 | 2단계 LLM + n-gram 매핑 | 대분류→장, 항목→절(결정적) | 고정 템플릿/LLM | 지정 목차 > 평가표 > 기본 템플릿 |
| 분량 배분 | 글자 수 목표→잎 수, LLM 배분, 쪽 골격 bin-packing | 장 제목 키워드별 고정 | 배점×쪽/총점×784 | 없음 | 정성 배점 비례 + 최대잉여법 |
| 날조 방지 | placeholder/omit/**fabricate(기본)** 모드, 서식 칸 unresolved | 데이터 의존 장 차단, 금지 지시 | 지시만 + 고정 문구에 날조 수치 | 【待确认】 지시, 검수 KB만 | fact 토큰 + `[확인 필요]` + FACT 규칙 |
| 점검 | 废标 3라운드·롤링, 오탈자(위치 검증), 논리, 暗标 64규칙(결정적), 메타데이터 | 21개(대부분 LLM 1회, 입력 절단) | 글자 수 | 결정적 4종 + 신뢰도 | 결정적 규칙 우선 + LLM 보조 |
| 정정공고 | 없음 | 없음 | 없음 | 사실 5종 diff + 노드 무효화 | 항목 단위 diff + DAG |
| 출력 | DOCX(C# OpenXML), 제한 HTML | DOCX(python-docx), PDF | DOCX | DOCX | HWPX/PPTX/PDF |
| LLM | OpenAI 호환, 접두부 예열, 분할·병합, 스키마 검증 | OpenAI SDK, 강제 JSON 모드 | 없음(호스트 에이전트) | httpx, 모델 라우팅 | Claude 구조화 출력, 캐시, 로컬 모드 |

### 3.2 평가기준 → 목차·분량 알고리즘 비교

| 저장소 | 1차 장 결정 | 평가항목→절 | 분량 | 배점 사용 |
|---|---|---|---|---|
| OBK | 평가 대항목 = 1차 장(원문 순서·명칭) | R별로 정확히 1노드, 편차는 사용자 승인 | 총 글자 수→잎 수, 잎 배분은 LLM | 직접 사용 안 함 |
| BMP | LLM(평가기준 장 명칭과 "최대한 일치") | n-gram 적중률 ≥0.3 | 장 제목 키워드별 고정 글자 수 | 안 함 |
| BSS | 대분류(技术/商务/价格) | 항목 1개 = 소절 1개 | 배점 × (총쪽/총점) × 784자 | 사용(총점 분모) |
| BPA | 고정 템플릿 또는 LLM | 없음 | 없음 | 안 함 |
| **우리** | 지정 목차 > 평가부문(별지 제5호) > 기본 템플릿 | 접두어 맵 + LLM 제안 + G2 확정 | (본문 상한 − 고정 장) × 정성 배점 비율, 최대잉여법 | 사용(정성 배점 분모) |

결론: 배점 비례 분량은 우리 설계가 가장 정확하다. 가져올 것은 OBK의 **"평가항목 ID를 노드에 정확히 한 번 매핑 + 프로그램이 누락·초과 제목을 계산"** 절차와 **편차 사용자 승인 규칙**이다.

### 3.3 날조 방지 장치 비교와 시사점

| 장치 | 출처 | 우리 적용 |
|---|---|---|
| 없는 값은 "【待填写】"를 글자 그대로, 변형 금지 | OBK `globalFactsTaskV2.cjs:92-94` | `[확인 필요: …]` 고정 형식. FACT-001이 정규식으로 잡는다 |
| 가격·금액·날짜·근거 없는 값은 `unresolved`로 넘기고 프로그램이 표시 | OBK `businessTemplateFillTask.cjs:411` | 별지 채우기에서 LLM이 자리표시를 직접 쓰지 않고 미해결 목록을 낸다 |
| 데이터 의존 장은 KB가 없으면 생성하지 않음 | BMP `content_gen_skill.py:55-68` | strategy의 자료 요청서(7.5)와 연결. 해당 절은 생성 대기 |
| "원문 명시"와 "경험 보충" 분리 | OBK `bidAnalysisTask.cjs:42-44` | 추출값 `method: llm`, `status: proposed`, `origin: llm_suggested`. 원문 근거 없는 항목은 G1에서 별도 표시 |
| LLM 인용의 원문 위치를 프로그램이 확인 | OBK 오탈자·작성지침·목차 위치 검증 | 설계서 7.3(C) 인용 검증을 모든 추출·점검 출력에 적용 |
| 기본 모드 `fabricate` | OBK | **채택 금지** |

---

## 4. 이식 계획

### 4.1 이식 유형

| 유형 | 의미 | 라이선스 결과 |
|---|---|---|
| 코드 이식 | 원 코드의 구조·식별자·로직을 Python으로 옮기거나 그대로 사용 | 원 라이선스 의무 발생 |
| 프롬프트 번역·적응 | 원 프롬프트 문장을 한국어로 번역하고 우리 스키마에 맞게 고침 | 번역은 2차적저작물로 보는 것이 안전하다 → 원 라이선스 의무 발생 |
| 규칙 로직 재구현 | 원 코드에서 판정 기준(임계값·패턴·절차)을 읽고, 코드를 보지 않고 다시 작성 | 아이디어·사실은 저작권 보호 대상이 아니다. 다만 세부 표현을 옮기면 이식으로 본다. 출처는 기록한다 |
| 아이디어만 | 설계 패턴만 참고 | 법적 의무 없음. 부록 C(설계서)에 출처 기록 |

### 4.2 구성요소 대응표

밀스톤: **M1** = RFP 분석기(parse·extract·plan), **M2** = 초안 + HWPX + check, **M3** = 장표·파생·패키지. 설계서 14장 기준으로 KB·strategy·generate·check는 M2, 별지 채우기·package는 M3이다. 라이선스 의무 약칭: **A** = AGPL-3.0 의무 일체(4.3절), **A+N** = A + OBK NOTICE §7(b) 보존, **P** = Apache-2.0 의무(4.3절), **–** = 의무 없음(출처만 기록).

| # | 원천 구성요소(파일) | 우리 모듈 | 이식 유형 | 한국형 조정 | 밀스톤 | 라이선스 |
|---|---|---|---|---|---|---|
| 1 | OBK 招标解析 과제 구조: 공유 접두부 + 과제별 user 프롬프트 병렬, 무결과 재실행(`bidAnalysisTask.cjs:67-294, 465-475`) | extract, llm | 코드 이식(Py 재작성) + 프롬프트 번역 | 과제를 Rfp 스키마 필드 단위로 재편(평가표·요구사항·작성지침·제출서류·참가자격·실격사유·일정). 출력은 Markdown이 아니라 JSON 스키마 + locator. 접두부 = 블록 ID 붙은 DocIR 텍스트, Claude `cache_control` | M1 | A+N |
| 2 | OBK 평가항목/평가규칙 분리 프롬프트(`bidAnalysisTask.cjs:76-104, 147-174`) | extract.eval_criteria | 프롬프트 번역·적응 | 정량/정성 구분, 부문(별지 제5호 Ⅱ~Ⅵ)·세부항목·배점·평가 질문·등급 수. 평가규칙(감점·등급 정의·정량 산식)은 `EvaluationTable.rules`로 분리. 합계 검증은 코드가 함 | M1 | A+N |
| 3 | OBK 无效投标/废标项 프롬프트(`bidAnalysisTask.cjs:32-65`) | extract(eligibility·disqualification) | 프롬프트 번역·적응 | 입찰무효·평가 제외·협상 제외·감점·블라인드 위반 감점의 한국 개념 경계(6.2절). "경험 보충"은 `status=proposed`로 따로 두고 G1에서 확정 | M1 | A+N |
| 4 | OBK 작성지침 추출 파이프라인(`blindCheckPresetExtraction.cjs` 전체) | extract.guideline(WritingGuideline) | 코드 이식 + 프롬프트 번역 | 필드: 분량(쪽)·요약본 분량·쪽수 제외 항목·용지·방향·본문/표 최소 pt·글꼴·줄간격·여백·편집기("아래한글")·제출 형식·총 용량(MB)·블라인드·발표. pt 표기 정규화("13포인트", "13pt", "13 pt"). 부정 사전(금지·불가·하지 않·아니 됨·제외). `quote` 검증은 블록 ID 기반 | M1 | A+N |
| 5 | OBK 지정 목차·제출서류 추출과 위치 검증(`outlineFormatExtraction.cjs:99-258`) | extract.prescribed_toc·required_documents | 코드 이식 + 프롬프트 번역 | 위치 = DocIR 블록 ID 구간. "제안서 목차(작성 순서)" 장과 "제출서류 목록·별지 제N호 서식" 장. content_mode → `OutlineNode.origin`·render 방식(본문/별지 채우기/대비표/목차/사람 작성). `post_award` → 계약 시 제출 서류 | M1 | A+N |
| 6 | OBK 평가항목 R1…·매핑 1회·결정적 커버리지·심사 문맥(`outlineGenerationTaskV2.cjs:158-238, 664-731, 840-863, 961-994`) | plan(outline, trace) | 규칙 로직 재구현 + 프롬프트 번역 | R1… 대신 `EvalItem.id`(E-02-03). 1차 장 = 평가부문, 2차 = 세부항목. 잎 수 목표 대신 쪽수 예산(7.4). 편차(합치기·나누기·추가)는 G2에서 사람 승인 | M1 | A+N |
| 7 | OBK 분할·병합(`userTextSplitter.cjs`, `segmentedAiResultMerger.cjs`) | llm | 코드 이식 | Claude 1M 경로에서는 대개 불필요. 로컬 모델 모드(설계 D7)용. 한국어 문장 경계(다./요./함./음.) | M1(로컬 대비)~M5 | A+N |
| 8 | OBK 접두부 예열(`promptPrefixCache.cjs`) | llm | 아이디어만 | Claude는 `cache_control` breakpoint로 해결. 병렬 호출 전 첫 호출 1회를 먼저 끝내 캐시를 쓰게 하는 순서만 반영 | M1 | – |
| 9 | OBK/BMP JSON 복구(`aiService.cjs:736-980`, `json_repair.py`) | llm | 아이디어만(로컬 모델용 대체 경로) | 기본은 구조화 출력이라 불필요. 로컬 모델 경로에서만 사용 | M1 | – |
| 10 | BMP 15차원 키워드 창 검색(`tender_interpret_skill.py:431-466`) | extract(보조) | 아이디어만 | 키워드 사전을 한국 RFP 장 구조(사업 개요·추진 방안·요구사항·평가·작성지침·제출서류·참가자격·일정)로 다시 정의. 로컬 모델의 짧은 컨텍스트에서만 사용 | M1 | – |
| 11 | BMP 리스크 경보(`risk_alert_skill.py:18-80`) | extract.ambiguity(질의서 초안), strategy | 프롬프트 번역·적응 | 특정 상표·규격 지정, 과도한 실적·인증 제한, 지역 제한, 짧은 공고기간, 모호한 요구 → 질의서 문안. 법적 근거 칸은 "원문 확인 필요"로 고정 | M1 | A |
| 12 | BMP 실질 요구 추출의 내부 ID(MP/DQ/HQ, `mandatory_req_extract_skill.py:18-50`) | extract | 아이디어만 | 요구사항 ID가 없는 서술형 필수 요구는 `X-nnnn`, 실격사유는 `D-nnn`, 자격은 `Q-nnn` | M1 | – |
| 13 | BPA `[doc page]` 표지·요구사항 5필드 분해(`agents/__init__.py:248-253, 374-424`) | extract.text_requirements | 아이디어만 | 블록 ID가 이미 더 세밀하다. `Requirement`에 주체·행위·조건·기한·불이행 조치 필드 추가 검토 | M1 | – |
| 14 | BPA 신뢰도 요인 분해(`confidence_service.py:38-110`) | extract(extraction_report) | 아이디어만 | 가중치는 벤치마크(13장)로 다시 정함. "인용 원문 존재" 요인은 우리 quote 검증 결과로 대체 | M1 | – |
| 15 | BPA 补遗 사실 diff·확인 작업·신호표·영향 미리보기(`addendum_agent.py`, `engine.py`, `dependency_graph.py`) | ingest·extract·store(7.11) | 규칙 로직 재구현 | 정정공고 차수(`bid_ord`), 질의회신 문서. `rfp.v{n}` 항목 단위 diff(요구사항 ID, 평가항목·배점, 작성지침 필드, 마감). 영향은 OutlineNode·TraceRow·storyboard까지 전파. 사람 확정값 충돌은 확인 작업으로 | M1(diff 엔진)·M4(자동 감시) | A |
| 16 | BMP scoreCoverage·n-gram 매핑(`structure_template_skill.py:192-294`, `outline_gen_skill.py:170-180, 465-494`) | plan(매핑 제안 보조), check COV-003 | 규칙 로직 재구현 | 한국어는 한자 n-gram 대신 공백·형태소 토큰. "절 제목에 평가항목 용어 포함"(COV-003) 판정 | M1 | A |
| 17 | BSS 분량 공식과 허용 범위(`check_word_count.py:81-117`) | plan.budget, check PAGE-003 | 아이디어만 | 우리 식 유지. 허용 범위 ±20%(PAGE-003)와 비교. 쪽당 글자 수는 #19로 계산 | M1 | – |
| 18 | OBK 전역 사실 placeholder 모드·서식 칸 unresolved(`globalFactsTaskV2.cjs:88-97, 219-292`, `businessTemplateFillTask.cjs:404-411`) | kb·strategy(프로젝트 fact SSOT), render(별지) | 프롬프트 번역·적응 | 결손 표시는 `[확인 필요: …]` 고정. fabricate 경로 삭제. 인력·인증·실적은 KB의 Fact만 사용 | M2(fact)·M3(별지) | A+N |
| 19 | OBK 쪽 지표·쪽 골격·골격 프롬프트(`pageMetrics.ts`, `sectionSkeleton.ts`, `skeletonPrompt.ts`) | generate(분량 맞춤), render | 코드 이식(TS→Py) | HWPX 스타일(10.2절: 본문 13pt, 줄간격 160%, 여백)로 쪽당 글자 수 계산. 블록 종류는 개조식(□○-·※), 표, 그림 스펙. 계수는 rhwp 렌더 실측으로 보정 | M2 | A+N |
| 20 | BMP 데이터 의존 장 차단(`content_gen_skill.py:10-14, 55-68`) | generate | 규칙 로직 재구현 | 실적·인력·인증·재무 절은 KB fact가 없으면 생성하지 않고 자료 요청서로 보냄 | M2 | A |
| 21 | BMP 절단 감지·이어쓰기(`content_gen_skill.py:139-202`) | generate·llm | 아이디어만 | Claude `stop_reason == "max_tokens"`일 때만 이어 받기. 구조화 출력이면 분할 생성으로 | M2 | – |
| 22 | BSS 자리표시자 3종(`SKILL.md:429-473`) | generate·derive | 아이디어만 | `[그림: 유형/설명/크기]`, `[표: 유형/열]`, `[증빙: 서류명/요건]` → DraftBlock 스펙. FACT-001이 잔존 여부 검사 | M2 | – |
| 23 | OBK 废标项 3라운드·롤링 patch 상태(`rejectionPrompts.ts`, `rejectionCheckTask.cjs:1021-1370`) | check(LLM 리뷰 보조: 실격사유·필수 요구 대비) | 프롬프트 번역 + 상태 기계 코드 이식 | "지류·현장 행위 제외" → "전자 문서에서 판단할 수 없는 항목 제외(인증서 서명, 가격입찰서, 현장 발표)". 증거는 렌더 PDF 쪽과 절 ID로 | M2 | A+N |
| 24 | OBK 오탈자 위치 검증(`rejectionCheckTask.cjs:271-353`) | check(LANG-00x 맞춤법) | 코드 이식 | 한국어 맞춤법·띄어쓰기. 확실한 오류만 | M2 | A+N |
| 25 | OBK 논리·일관성 프롬프트(`rejectionPrompts.ts:177-217`), BMP 일관성 규칙부(`consistency_check_skill.py:59-128`) | check CONS-001 | 프롬프트 번역 + 규칙 재구현 | 투입 인력·M/M, 사업 기간, 산출물 수, 사업명, 발주기관명. SSOT fact와 대조하는 결정적 판정이 주 | M2 | A+N / A |
| 26 | OBK 暗标 규칙 엔진 64규칙·사전값 스키마·후보/확정 분리(`BlindCheck/Rules/*.cs`, `blindCheckPresets.cjs`, `blindCheckReview.cjs`) | check BLD-001·FMT-001~003·TOC·신규 BLD | 규칙 로직 재구현(OWPML 대상) | 신원 탐지기를 한국형으로(4.2.1). 대상은 HWPX(`header.xml` charPr·paraPr, section XML)와 렌더 PDF. 메모·변경 추적·숨은 글자·하이퍼링크·필드도 BLD로 | M2 | A+N |
| 27 | OBK 메타데이터 추출(`duplicateCheckService.cjs:15-100, 324-347, 703-1094`) | check BLD-003, package | 코드 이식 | HWPX `docInfo`·`content.hpf` 메타, PDF Info·XMP, PPTX `docProps`, DOCX rsid | M3 | A+N |
| 28 | OBK 招标 출처 문장 판별기(`duplicateCheckService.cjs:1915-1996`) | check(재사용 과다), kb | 코드 이식 | KB 재사용 유사도 계산에서 RFP 인용 문장 제외. 한국어 정규화(번호 머리 □○, 가. 1) 등) | M2 | A+N |
| 29 | BMP 查重 + 화이트리스트(`duplicate_check_skill.py`, `whitelist_filter_skill.py`) | check(신규 minor: 내부 중복·과거 제안서 과다 재사용) | 규칙 로직 재구현 | 공공 제안서 상투어 화이트리스트("발주기관의 요구사항을 준수" 등) | M2 | A |
| 30 | BMP selfcheck 집계 구조(`selfcheck_list_skill.py`) | package(제출 전 점검표) | 아이디어만 | 항목을 우리 규칙 ID(COV·PAGE·FMT·SUB·BLD·FACT)로 재작성 | M3 | – |
| 31 | BMP 산술 검산(`pricing_check_skill.py:75-94`) | check(정량서식 합계) | 규칙 로직 재구현 | 투입인력표 M/M 합계, 일정표 기간 합. 가격 안전구간은 제외 | M3 | A |
| 32 | OBK rule-page(평가항목 쪽 대비표·대비표)·TOC 쪽 번호 되채움(`outlineFormatExtraction.cjs:20`, `TableOfContentsBuilder.cs`) | plan(OutlineNode 분류), render(추적표 `pages`, 목차) | 아이디어만 | 요구사항 대비표·평가항목 대비표 쪽 번호를 렌더 후 채움. HWPX 목차는 python-hwpx로 따로 구현 | M1(분류)·M3(쪽 채움) | – |
| 33 | BMP·BSS 서식 기본값(`templates/default.yaml`, `format_docx.py:33-95`) | render styles | 아이디어만 | 한국 보고서 스타일(설계서 10.2절)이 우선. 참고만 | M2 | – |
| 34 | BPA 사람 편집 보호·검수 KB만 검색(`agents/__init__.py:709-713, 733`) | generate·kb·store | 아이디어만 | `origin: human` 절 재생성 금지, KB ContentBlock 승인 상태 필터 | M2 | – |
| 35 | BPA NodeDefinition 필드(`engine.py:41-65`) | store(DAG) | 아이디어만 | 단계 선언에 `invalidated_by`·`human_gate`·`risk_level`·`allowed_models`·`cost_limit` 추가 | M1 | – |

#### 4.2.1 신원 노출 탐지기 한국형 조정(#26 세부)

| OBK 탐지기 | 한국형 | 판정 |
|---|---|---|
| 자기지칭 我公司·我司·本公司… | 당사, 우리 회사, 저희 회사, 폐사, 본사(단 "본 사업"·"본 시스템" 오탐 주의), 당 컨소시엄 | 확정 |
| 강한 접미사 회사명 有限公司… | 주식회사, (주), ㈜, 유한회사, 유한책임회사, 합자회사, (재)·재단법인, (사)·사단법인, 협동조합, Co., Ltd., Inc. | 후보 → AI 재검토 |
| 무시 기관 招标人·监理·供电公司… | RFP에서 추출한 발주기관·수요기관명, 조달청, 전문기관(NIA 등), "발주기관", "수요기관", "감리법인" | 무시 목록(사업별 자동 + 사용자) |
| 신분증·통일사회신용코드 체크섬 | 사업자등록번호(10자리, 체크섬), 법인등록번호(13자리, 체크섬 알고리즘 원문 확인 필요). 주민등록번호는 인력 개인정보라 KB 가명화(설계서 8.3)로 차단 | 확정(체크섬 통과 시) |
| 휴대·유선전화 | 010-XXXX-XXXX, 0X(X)-XXX(X)-XXXX, 15XX·16XX 대표번호 | 확정 |
| 이메일·URL·도메인 | .kr, .co.kr, .or.kr, .go.kr(발주기관 도메인은 무시) | 확정 / 기관 도메인 무시 |
| 저작권 표기 版权所有·© | ©, Copyright, 저작권 | 확정 |
| 자리표시자 XXX·某公司 | ○○, OO, XXX, 귀사, [회사명] | 후보 |
| 사용자 민감어 | KB Identity(회사명 국문·영문·약칭, 제품명, 대표자명, 로고 해시) | 확정(BLD-001·002) |

### 4.3 라이선스 의무 상세

#### AGPL-3.0 (OBK, BMP, BPA) — 표의 "A"

- **결합 가능성.** 우리 저장소는 GPL-3.0이다. GPL-3.0 §13은 AGPL-3.0 저작물과 하나의 결합 저작물로 링크·결합하는 것을 허락한다. 결합물에서 AGPL에서 온 부분은 AGPL 조건을 계속 따른다. OBK는 NOTICE에서 "v3.0 only"를 밝혔으나 GPL-3.0 §13의 허락 대상이 바로 AGPL v3이므로 문제없다.
- **이식 파일 표시.**
  - 이식·번역한 파일 머리에 원저작권, 원 저장소 URL, 커밋 SHA, `SPDX-License-Identifier: AGPL-3.0-only`(OBK) 또는 `AGPL-3.0-or-later`/`AGPL-3.0-only`(BMP·BPA는 버전 명시가 없어 AGPL §14에 따라 판단. 보수적으로 `-only`로 표기)를 단다.
  - 수정 사실과 날짜를 적는다(AGPL §5(a)).
- **OBK 귀속 고지.** 원 `NOTICE`의 저작자 귀속 문구(원 저장소, 저작자 mark / yibiaoai, 저작권 행)를 배포물과 소스에 **그대로 보존**한다. 이는 AGPL §7(b)에 따른 추가 조건이다. `third_party/OpenBidKit_Yibiao/NOTICE`로 동봉하고, 이식 파일 머리에서 참조한다.
- **배포 시.** 결합 저작물 전체의 대응 소스를 GPL-3.0/AGPL-3.0 조건으로 제공한다. 우리가 이미 GPL이므로 추가 부담은 작다.
- **네트워크 서비스(가장 큰 의무).** M4에서 REST API·Web UI로 사용자에게 원격 상호작용을 제공하면, AGPL §13에 따라 **그 사용자에게 수정본 전체의 대응 소스를 받을 수단을 눈에 띄게 제공**해야 한다(예: UI 하단 "소스 코드" 링크, 해당 배포 버전 태그). 사내 on-prem 배포도 사용자가 조직 밖 사람이면 해당한다. CLI·로컬 단일 사용자(M1~M3)에는 §13이 걸리지 않는다.
- **프롬프트 번역도 이식으로 다룬다.**
  - 한국어 번역 프롬프트(6장)를 `config/prompts/`나 코드 문자열로 넣으면 그 파일도 AGPL 표시 대상이다.
  - 이를 피하려면 6장 초안 대신, 요구사항만 적은 사양에서 다시 쓰는 클린룸 방식으로 작성해야 한다. 소유자가 라이선스 영향을 받아들였으므로 이 문서는 번역 경로를 기본으로 하고 표시 의무를 지킨다.
- **디렉터리 운영 제안.** 이식 코드는 `src/rfpgen/_third_party/agpl/<원저장소>/`처럼 분리한다. 그래야 결합 범위가 분명해지고, 나중에 클린룸 재작성으로 바꿀 때 대상을 찾기 쉽다.

#### Apache-2.0 (BSS) — 표의 "P"

- LICENSE 사본을 동봉한다(§4(a)).
- 수정한 파일에 변경 사실을 표시한다(§4(b)).
- 원 저작권·특허·상표 고지를 유지한다(§4(c)).
- NOTICE 파일이 없으므로 §4(d) 의무는 없다.
- GPL-3.0과 결합할 수 있다(Apache-2.0 → GPL-3.0 단방향 호환).
- README의 MIT 표기와 충돌하지만 Apache 조건을 지키면 MIT 조건(고지 유지)도 만족한다.
- 실제 이식 대상은 아이디어(#17, #22)뿐이라 지금 당장의 의무는 없다.
- `templates/*.md` 지식 문서는 코드 라이선스와 별개로 원저작권이 불명확하므로 가져오지 않는다.

#### 아이디어만 — 표의 "–"

- 법적 의무는 없다. 설계서 부록 C(참고 구현 대응표)에 출처를 남기는 기존 관행을 따른다.

#### 설계서와 맞출 것(이 작업에서는 수정하지 않음)

이 분석을 쓰는 동안 설계서 작업 트리(미커밋 v0.2)의 11.1·11.2절과 16장 Q8에 이식 결정이 반영됐다. 아직 남은 것은 다음과 같다.

- 4장 원칙 P8: "GPL·AGPL 도구는 별도 프로세스로만 쓰거나 아이디어만 참고한다"
- 부록 C "실격사유 점검" 행: "OpenBidKit_Yibiao, BidMaster-Pro(AGPL, 아이디어만)"
- 14장 M4 Web UI 요구사항: "AGPL §13 소스 제공 링크"가 아직 없다.
- 이식 디렉터리 분리와 SPDX 표기 규칙(위 운영 제안): ADR(`docs/adr/`)로 남기는 것이 좋다.
- 14장 로드맵: 정정공고 diff 엔진을 M1로 당기자는 5.8절 제안을 반영할지 정해야 한다.

### 4.4 이식하지 않는 것

| 대상 | 이유 |
|---|---|
| OBK `fabricate` 사실 모드 | 허위 기재 위험(설계 P2·12.2). 실격·감점 사유 |
| BSS `generate_content.py` 고정 본문 | 근거 없는 수치 포함. 사업 맥락 없음 |
| BSS `humanizer.py` | 의미 훼손 위험. 우리는 표시만 하는 LANG 필터 |
| BSS `templates/*.md` 지식 문서 | 원저작권 불명확 |
| BMP 가격 안전구간·报价逻辑 | 가격은 비목표(설계 2.2) |
| BMP 보증금·서명날인·CA·밀봉 점검 | 제출은 사람이 함. 범위 밖 |
| BMP·BPA 입력 절단 방식(3,000~14,000자, 4조각) | 누락의 직접 원인 |
| OBK 투찰자 사이 담합 탐지(围串标) 기능 자체 | 단일 투찰자 제품과 목적이 다름. 부품(메타데이터·출처 판별)만 사용 |
| OBK 라이선스·텔레메트리·원격 공지 코드 | 제품 성격 다름. 외부 전송 금지 원칙(설계 P7) |
| AI 이미지 생성(BMP `ai_image_skill.py`, OBK aiImage) | 우리 도식은 DiagramSpec → SVG(7.9) |

---

## 5. M1에 지금 바로 쓸 것: extract·plan 구체 제안

> 이 분석과 동시에 규칙 기반 M1 구현이 들어왔다(커밋 `6b61f02`).
> - extract: `src/rfpgen/extract/{evaluation,guideline,requirements,ambiguity,notice}.py`
> - plan: `src/rfpgen/plan/{outline,budget,trace}.py`
>
> 아직 `llm` 모듈은 없다. 아래 제안은 두 갈래로 적용한다. 결정적 부분(근거 원문 대조, 극성 검사, 누락 탐지, 위치 검증, 커버리지 계산)은 기존 파일에 바로 붙인다. LLM 보조 부분(5.1절, 6장 프롬프트)은 `llm` 모듈과 함께 추가한다.

### 5.1 공통 LLM 호출 틀(extract)

1. **접두부 고정.** [system 지침] + [블록 ID가 붙은 DocIR 전문]을 접두부에 두고 cache breakpoint를 건다. 과제마다 짧은 지시와 스키마만 바꾼다. 첫 과제를 먼저 끝낸 뒤 나머지를 병렬로 보내면 캐시 적중률이 높아진다(OBK `bidAnalysisTask.cjs:465-475`의 예열과 같은 효과). 적중 여부는 `usage.cache_read_input_tokens`로 확인한다. 설계서 8.4절과 맞는다.
2. **과제를 필드 단위로 나눈다.** OBK처럼 하나의 거대 추출 대신 다음처럼 나눈다.
   - `extract.eval_criteria`(평가표)
   - `extract.disqualification`(실격·감점·참가자격)
   - `extract.guideline`(작성지침)
   - `extract.prescribed_toc`(지정 목차·제출서류)
   - `extract.text_requirements`(서술형 요구)
   - `extract.schedule`(일정)
   - `extract.ambiguity`(질의서)
   과제별로 effort와 모델을 따로 정할 수 있다.
3. **출력은 구조화 출력(JSON Schema)이다.** 모든 값에 `locators[{block_id, quote}]`를 붙인다. 응답 뒤 코드가 다음 순서로 처리한다.
   - (a) `quote`가 해당 블록 텍스트에 있는지 확인한다(정규화: 공백·문장부호 제거 후 부분문자열. OBK `normalizeForMatch` 방식).
   - (b) 값과 근거의 극성·숫자 표기가 맞는지 확인한다(OBK `valueIssue` 방식).
   - (c) 형변환과 범위를 검사한다.
   - (d) 실패한 것은 버리지 말고 `extraction_report`에 `dropped`/`unverified`로 남긴다.
4. **2회 실행 비교(설계서 7.3 C).** 평가표·실격사유는 같은 입력으로 두 번 돌린다. 교집합 밖 항목을 불안정 신호로 G1 큐에 올린다.
5. **누락 탐지.** 키워드 사전으로 "있어야 할 주제"가 원문에 있는데 결과가 비면 원문 문장을 `omissions`로 보고한다(OBK `findOmissions`). 예: "블라인드", "쪽 이내", "포인트", "MB", "별지 제", "무효", "감점".

### 5.2 평가표 추출(`extract.eval_criteria`)

- **1순위는 규칙 기반 표 파서다(설계서 7.3 A).** 평가표는 거의 항상 표다. DocIR 표에서 헤더 키워드(평가부문·평가항목·세부항목·배점·평가기준·평가방법)를 찾는다. 병합 셀은 부문명을 아래 행에 전파한다. 배점은 숫자 셀에서만 읽는다.
- **LLM의 역할은 셋으로 제한한다.**
  - ① 표 구조가 깨진 경우(PDF·이미지) 비전 재구성
  - ② 세부 평가 질문 정규화
  - ③ **평가항목과 평가규칙 분리**(OBK 프롬프트, 6.1절)
  - 분리 기준은 "제안서에서 내용을 써서 답할 대상인가"다. 등급표(수·우·미·양·가 / A~E), 감점 기준("분량 초과 시 …점 감점"), 정량 산식(실적 금액 구간별 점수)은 규칙이다.
- **결정적 검산.**
  - 부문 합계 = 기술 배점, 정량 + 정성 = 기술 배점
  - 부문당 상한(30점)·하한(상생 5점)은 정보로만 표시한다(provisional)
  - 항목 배점의 소수점 합 오차를 확인한다
- **스키마 보강 제안(설계서 6.3).** `EvaluationTable`에 다음을 더한다.
  - `rules: list[EvalRule]`(감점·가점·등급 정의·정량 산식, 적용 대상 항목 ID)
  - `EvalItem.source_kind: Literal["table","text"]`
  - 둘 다 OBK의 "评分要求" 분리에서 온다.

### 5.3 실격·감점·참가자격 추출(`extract.disqualification`)

- **개념 경계를 프롬프트에 산문으로 정의한다(OBK 방식, 6.2절).**
  - **입찰무효·참가자격 미달:** 자격 요건 불충족, 필수 서류 누락, 제출 기한 위반, 서약·확약 위반 등으로 입찰 자체가 무효이거나 평가에서 제외되는 사유
  - **평가 제외·협상 제외:** 기술평가 점수 기준 미달(협상적격 컷), 허위 기재 판명, 블라인드 위반이 제외로 규정된 경우 등
  - **감점·불이익:** 분량 초과, 형식 위반, 블라인드 위반(감점 규정), 타사 비방, 요구사항 누락 감점
  - 법령 조문 번호는 LLM이 만들지 못하게 한다. RFP 원문에 적힌 근거만 옮긴다(설계 부록 A의 원문 미대조 원칙).
- **"원문 명시" vs "추가 확인 권고"를 분리한다.** 후자는 최대 5개로, 원문에 근거가 없음을 표시해 `status=proposed`·`origin=llm_suggested`로 둔다. 체크리스트에는 넣되 G1에서 사람이 채택해야 rule이 된다.
- **산출물 연결.**
  - 참가자격 → `Rfp.eligibility`(strategy Go/No-Go 하드 게이트)
  - 실격·감점 → `Rfp.disqualifications`(신설 제안)
  - 형식 관련 감점은 작성지침 필드와 교차 연결해 check 규칙(PAGE·FMT·BLD)의 **심각도 근거**로 쓴다. 예: "분량 초과 시 평가 제외"라고 적힌 RFP에서는 PAGE-001을 blocker로 고정한다.

### 5.4 작성지침 추출(`extract.guideline`)

- OBK 파이프라인(2.1.4절)을 거의 그대로 옮긴다. 설계서 7.3(A)의 정규식 패턴 사전은 **1단계 키워드 창 탐색과 결정적 교차 확인**으로 남긴다. LLM 필드 추출이 같은 값을 냈는지 대조하는 용도다.
- **필드 목록 초안.**

| 필드 | 형식 | 비고 |
|---|---|---|
| `main_page_limit` | 정수 | 쪽 |
| `summary_page_limit` | 정수 | 쪽 |
| `count_exclusions` | 목록 | 표지·목차·간지 |
| `paper` / `orientation` | 값 | 용지, 방향 |
| `min_font_pt` / `table_min_font_pt` | 수 | 원문 표기 그대로 받고 코드가 pt로 변환 |
| `fonts` | 목록 | |
| `line_spacing` | 값 | |
| `margins_mm` | 값 | |
| `editor` | 문자열 | "아래한글 권장" 등 |
| `file_format` | 문자열 | |
| `total_size_limit_mb` | 정수 | |
| `blind` + `blind_forbidden_marks` | bool + 목록 | 회사명·로고·CI·대표자·제품명 등 |
| `presentation` | 객체 | 발표 시간·질의 시간·PM 발표 의무 |
| `manual` | 목록 | 필드로 표현할 수 없는 원문 요구 |

- **극성 사전(한국어).** 금지: "금지", "불가", "하지 않", "아니 됨", "말 것", "제외", "삭제". 허용: "가능", "허용", "할 수 있". OBK처럼 부정을 먼저 빼고 허용을 판정한다.
- **미지정 필드는 `null`로 둔다.** 프로필 기본값(설계서 9장, provisional)으로 보완하되, 점검 심각도는 설계서 7.8절 규칙대로 한 단계 낮춘다.

### 5.5 지정 목차·제출서류 추출(`extract.prescribed_toc`, `required_documents`)

- **입력.** "블록 ID + 텍스트" 줄 목록이다(OBK의 `L000123 |` 대신 `d03:b0142`).
- **지시(6.4절).** "제안서 작성 순서/목차" 장과 "제출서류 목록·별지 서식"을 **내용 기능으로** 찾게 한다. 조목을 합치거나 나누거나 더하지 말라고 한다. 제목은 번호만 떼고 그대로 옮긴다. 각 노드에 `start_block`·`end_block`을 단다.
- **결정적 검증(OBK `validateFormatOutline` 이식).** 블록 범위, 순서, 비중첩, 자식⊂부모를 본다. **제목이 해당 위치 블록에 실제로 있는지**도 확인한다. 실패하면 LLM에 문제 목록을 돌려 1회 재시도하고, 그래도 실패하면 G1 큐로 보낸다.
- **content_mode → 우리 처리 방식.**

| content_mode | 우리 처리 |
|---|---|
| ai-generate | `OutlineNode`(본문) |
| template-fill | `RequiredDoc`(별지 채우기, M3) |
| rule-page | 추적표·평가항목 대비표 |
| directory-generate | 목차 |
| manual-fill | 사람 작성(가격제안서 등) |
| post_award | 계약 시 제출(제출 패키지에서 제외) |

- **TOC-001(지정 목차 일치)의 기준 데이터가 여기서 나온다.**

### 5.6 평가표 → 목차·추적표(plan)

1. 지정 목차가 있으면 그대로 쓴다. 없으면 평가부문을 1차 장으로, 정성 세부항목을 2차 절로 쓴다(설계서 7.4). 정량 항목은 정량제안서로 분리한다.
2. **매핑 계약(OBK).** 모든 정성 `EvalItem.id`는 `OutlineNode.eval_items`에 빠짐없이 나타나야 한다(누락 0). 기본은 한 항목에 한 절이다.
   - 합치기(한 절이 여러 항목)와 나누기(한 항목이 여러 절)는 허용하되 `adjustments[]`에 사유를 남기고 G2에서 사람 승인을 받는다. OBK도 같은 방식으로, 승인된 합치기는 같은 `target_title`, 승인된 나누기는 `additional_titles`로 기록한다(`outlineGenerationTaskV2.cjs:857-859`).
   - **프로그램이 계산하는 심사 문맥.** 항목별 기대 절, 실제 절, 누락, 초과, 깊이, 절당 예산 쪽을 낸다. LLM 리뷰는 의미 커버리지와 근사 중복만 본다. COV-002의 사전 버전이다.
3. **요구사항→절.** 접두어 기본 맵(설계서 9.3) → LLM 제안 → G2 확정. BMP의 n-gram 적중률 매칭은 "절 제목 ↔ 요구사항명" 유사도 보조 점수로만 쓴다.
4. **평가규칙의 반영.** `EvaluationTable.rules` 중 절 작성에 영향을 주는 것(예: "단계별 산출물을 제시하지 않으면 최하 등급")은 해당 절 `checklist`로 내린다.

### 5.7 쪽수 예산 보정(plan.budget)

- **식 비교.**
  - 우리 식: 쪽 = (본문 상한 − 고정 장) × 정성 배점 비율, 최대잉여법
  - BSS 식: 목표 글자 = 배점 × (총쪽 ÷ 총점) × 784
  - BSS는 총점에 가격·정량이 들어가 기술 장이 과소 배정된다. 우리 식을 유지한다.
- **쪽당 글자 수.** OBK `resolvePageMetrics`(`pageMetrics.ts:179-235`) 방식으로 스타일에서 계산한다.
  - 예: A4, 좌우 여백 20mm(본문폭 170mm), 위 20·아래 15·머리말 10·꼬리말 10mm(본문높이 242mm), 본문 13pt, 줄간격 160%
  - 한 줄 ≈ ⌊170 ÷ 4.59⌋ = 37자, 한 쪽 ≈ ⌊242 ÷ 7.34⌋ = 32줄
  - **순수 문단만이면 약 1,180자/쪽(이론 상한)** 이다. 개조식·표·그림 비중을 반영한 실효 값은 렌더 실측(rhwp)으로 보정한다(설계서 7.6).
- `budget.json`에 쪽 수와 함께 `target_chars_range = [0.8, 1.2] × 쪽 × 실효 글자/쪽`을 기록한다. PAGE-003(±20%)과 같은 허용 폭이다.

### 5.8 정정공고 diff(M1에 엔진, M4에 자동 감시)

설계서 14장은 정정공고 diff를 M4에 두었다. 그런데 `rfp.v{n}.json` 버전 관리가 M1에 이미 있으므로 **diff 엔진은 M1에 넣는 편이 싸다.** 정정공고·질의회신을 수동 업로드해도 바로 쓸 수 있다.

1. **항목 단위 diff.** 안정 키로 비교한다.
   - `Requirement.id`(없으면 정규화 명칭 해시)
   - `EvalItem`(부문+정규화 항목명 → id)
   - `WritingGuideline` 필드
   - `Notice.deadlines`
   - 값 변경, 추가, 삭제마다 옛 locator와 새 locator를 붙인다.
2. **영향 전파.** `OutlineNode.eval_items/requirements`, `TraceRow`, `budget`, (M2부터) `storyboard`, `sections`를 역참조해 "재검토 필요"로 되돌린다. BPA의 신호→무효화 표(`invalidated_by`)를 단계 선언에 넣는다.
3. **확인 게이트(BPA).** `origin: human` 값과 충돌하거나 고위험(배점·분량·마감·실격사유) 변경이면 확인 작업을 만든다. 확인 작업에는 옛값·새값·출처 블록을 담는다. **재실행 전에 영향 미리보기**(영향/비영향 단계, 대체될 산출물)를 CLI로 보여 준다.
4. **변경 보고서.** 사람이 읽을 수 있는 요약을 만든다(설계서 7.11 4단계).

### 5.9 질의서 초안(extract.ambiguity)

- BMP 리스크 경보 프롬프트(`risk_alert_skill.py:18-80`)를 한국형으로 바꾼다. 대상은 특정 상표·규격 지정, 과도한 실적 제한, 모호한 수량·범위, 평가기준 불명확 같은 "질의 대상"이다.
- 출력에 질의 문안 초안과 원문 locator를 붙인다.
- 법적 근거 칸은 LLM이 채우지 않는다.

### 5.10 M1 작업 순서 제안

1. `llm` 공통 틀: 접두부 캐시, 구조화 출력, locator 검증기, 2회 실행 비교기, `extraction_report`
2. `extract.guideline`: OBK 파이프라인 이식(#4). 단위 테스트는 OBK 검증 함수의 경계 사례를 한국어로 옮긴다
3. `extract.eval_criteria`: 규칙 표 파서 + 평가항목/규칙 분리 프롬프트(#2) + 합계 검산
4. `extract.prescribed_toc`·`required_documents`: 위치 검증 이식(#5)
5. `extract.disqualification`·`eligibility`: 프롬프트(#3)
6. `plan`: 매핑 계약·심사 문맥(#6), 쪽당 글자 수 계산(#19의 계산부만 선행)
7. `rfp diff` 엔진과 영향 미리보기(#15)
8. 라벨 데이터 30건으로 재현율·정확도를 잰다(설계서 13장). 특히 "평가규칙을 항목으로 잘못 분류한 비율"을 지표에 더한다

---

## 6. 핵심 프롬프트 한국어 번역 초안

### 6.0 공통 원칙

- 설계서 8.4절을 따른다.
  - 지시는 산문으로 쓰고, 태그는 입력 데이터 구분에만 쓴다.
  - 출력 형식은 구조화 출력(JSON Schema)으로 강제하고, 프롬프트에는 필드의 **의미**만 설명한다.
  - 금지 표현 목록을 나열하지 않는다.
  - assistant prefill을 쓰지 않는다.
- 입력의 `<rfp>`는 `[d03:b0142] 텍스트` 형식의 DocIR 블록 줄이다.
- **라이선스.** 아래 초안은 OBK·BMP 프롬프트를 번역·변형한 것이다. 저장소에 넣을 때 4.3절 AGPL 표시를 붙인다.
- 원문은 부록 A의 해당 절을 본다.

### 6.1 P-KR-1 평가표 추출(평가항목·평가규칙 분리)

- **원천:** OBK `bidAnalysisTask.cjs:76-104, 147-174`(A.1.2), BMP 평가 차원(A.7.1)
- **바꾼 점:** Markdown 출력 → 스키마 출력, 数据来源 자유 텍스트 → block_id·quote, 기술/상무 → 정량/정성, 합계 검산은 코드로 넘김

```text
이 작업은 공공 정보화사업 제안요청서에서 제안서 평가기준을 구조화하는 것입니다. <rfp> 안의 각 줄은 문서 블록이며, 줄 앞의 대괄호는 블록 ID입니다.

평가표의 내용을 두 종류로 나누어 주십시오. 평가항목은 제안사가 제안서 본문에서 직접 내용을 써서 답해야 하고, 제안서의 장이나 절로 대응시킬 수 있는 평가 대상입니다. 사업 이해도, 추진 전략, 개발 방법론, 테스트 방안, 품질보증, 상생협력 같은 것이 여기에 해당합니다. 평가규칙은 점수를 매기는 방법, 등급 구분과 등급별 점수, 감점과 가점의 조건, 정량 점수 산식, 적용 범위 설명처럼 평가를 제약하거나 해석하는 내용입니다. 배점이 붙어 있더라도 제안서에서 내용을 써서 답할 대상이 아니라면 평가규칙으로 분류합니다.

평가항목마다 평가부문, 항목명, 세부 평가 내용(평가위원이 확인하는 질문), 정량·정성 구분, 배점, 등급 수를 적습니다. 항목명과 부문명은 원문의 용어를 그대로 쓰고 다듬거나 요약하지 않습니다. 원문 순서와 계층도 유지합니다. 표에서 부문명이 병합 셀로 한 번만 적혀 있으면 그 아래 행들에도 같은 부문을 적용합니다. 배점과 등급 수는 원문에 적힌 숫자만 옮기며, 계산하거나 추정하지 않습니다. 원문에 없는 값은 null로 둡니다. 합계가 맞는지는 프로그램이 따로 확인하므로, 합계를 맞추려고 값을 바꾸지 마십시오.

평가규칙마다 규칙 이름, 규칙의 내용, 적용 대상(어느 평가항목이나 부문에 적용되는지, 전체 적용이면 "전체")을 적습니다.

모든 항목과 규칙에는 근거를 붙입니다. 근거는 내용이 실제로 적힌 블록의 ID와, 그 블록 텍스트에서 10자에서 80자 사이를 글자 그대로 옮긴 인용문입니다. 내용이 여러 블록에 걸쳐 있으면 근거를 여러 개 적습니다. 인용문을 고치거나 여러 곳을 이어 붙이지 마십시오.

평가표가 별도 첨부 파일에 있다고만 적혀 있고 <rfp> 안에 표 자체가 없으면, 평가항목을 비워 두고 그 사실과 근거를 notes에 적습니다. 기술평가와 가격평가의 배점 비율이 적혀 있으면 tech_price_ratio에 옮깁니다.
```

출력 스키마(요지, Pydantic):

```python
class EvalItemOut(BaseModel):
    area: str; name: str; questions: list[str]
    kind: Literal["정량", "정성"] | None
    points: float | None; grades: int | None
    locators: list[LocatorOut]          # {block_id, quote}
class EvalRuleOut(BaseModel):
    name: str; content: str; applies_to: list[str]   # 항목명 또는 "전체"
    locators: list[LocatorOut]
class EvalTableOut(BaseModel):
    tech_price_ratio: tuple[int, int] | None
    items: list[EvalItemOut]; rules: list[EvalRuleOut]; notes: str
```

### 6.2 P-KR-2 입찰무효·평가 제외·감점 사유와 참가자격 추출

- **원천:** OBK `bidAnalysisTask.cjs:32-65`(A.1.1), BMP 废标红线 차원(A.7.1), BMP 실질 요구 추출(A.7.6)
- **바꾼 점:** 无效投标/废标项 경계 → 한국 개념 3분류 + 참가자격, "원문 명시/경험 보충" 분리를 스키마 필드로, 법령 조문 생성 금지

```text
이 작업은 제안요청서와 입찰공고문에서 제안사가 탈락하거나 불이익을 받는 조건을 빠짐없이 모으는 것입니다. <rfp> 안의 각 줄은 문서 블록이며, 줄 앞의 대괄호는 블록 ID입니다.

조건을 다음 세 가지로 나누어 주십시오. 입찰무효는 입찰참가자격을 갖추지 못했거나, 필수 제출서류가 빠졌거나, 제출 기한·방법을 어겼거나, 서약·확약 사항을 위반해 입찰 자체가 무효가 되거나 평가에 들어가지 못하는 경우입니다. 평가 제외는 입찰은 유효하지만 제안서가 평가나 협상 대상에서 빠지는 경우입니다. 기술평가 점수가 기준에 못 미치는 경우, 허위 기재가 밝혀진 경우, 블라인드 위반을 제외 사유로 정한 경우가 여기에 해당합니다. 감점은 탈락하지는 않지만 점수가 깎이는 경우입니다. 분량 초과, 형식 위반, 업체 식별 표시, 다른 업체 비방, 요구사항 미반영처럼 감점이나 불이익으로 규정된 것이 여기에 해당합니다. 원문이 "무효", "효력이 없", "평가 대상에서 제외", "협상 대상에서 제외", "부적격", "감점", "불이익" 같은 다른 표현을 쓰더라도 뜻에 따라 이 세 가지로 나눕니다.

참가자격은 따로 모읍니다. 업종 등록, 중소기업 여부, 공동수급 허용 여부와 구성 조건, 하도급 제한, 실적·인증 요건처럼 입찰에 참가하려면 갖춰야 하는 조건을 원문 그대로 적습니다.

각 조건에는 원문 문장을 짧게 옮기고, 결과(무효, 평가 제외, 감점이면 감점 크기)를 원문에 적힌 대로 적습니다. 원문이 근거 법령이나 조항을 밝혔으면 그 표기를 그대로 옮기고, 원문에 없는 법령 조항은 적지 마십시오. 모든 조건에 근거 블록 ID와, 그 블록에서 10자에서 80자 사이를 글자 그대로 옮긴 인용문을 붙입니다.

원문에는 없지만 이런 유형의 사업에서 놓치면 위험이 큰 확인 사항이 있다면, suggested_checks에 따로 적습니다. 최대 다섯 개까지만 적고, 각각 왜 확인해야 하는지 한 문장으로 설명합니다. 일반적인 목록을 늘어놓지 말고, 이 사업의 원문 내용과 관련된 것만 적습니다. 이 항목들은 원문 근거가 없으므로 근거 칸을 비워 둡니다.
```

출력 스키마 요지: `conditions[{category: "입찰무효"|"평가제외"|"감점", text, consequence, legal_ref_in_text|null, locators}]`, `eligibility[{text, locators}]`, `suggested_checks[{text, reason}]`. 코드에서 `suggested_checks`는 `method="llm"`, `status="proposed"`로 저장하고 G1에서만 채택한다.

### 6.3 P-KR-3 제안서 작성지침(분량·형식·블라인드) 추출

- **원천:** OBK `blindCheckPresetExtraction.cjs:134-172`(A.2.2)
- **바꾼 점:** 暗标 排版 → 한국 작성지침 전체, 중국 글자 크기 호수 → pt 원문 표기, 필드 확장(분량·용량·블라인드·제출 형식·편집기·발표), 근거는 블록 ID

```text
이 작업은 제안요청서의 제안서 작성지침에서 분량, 형식, 제출, 블라인드 요건을 정해진 필드로 정리하는 것입니다. <excerpts> 안에는 작성지침과 관련 있어 보이는 부분만 블록 단위로 들어 있으며, 줄 앞의 대괄호는 블록 ID입니다. 채울 수 있는 필드와 뜻은 <fields>에 있습니다.

원문에 명시된 요건만 적습니다. 원문에 없는 필드는 아예 출력하지 말고, 관행적인 기본값을 넣지 마십시오. 원문이 "제한 없음", "자유 양식", "제안사가 정함"이라고 한 필드도 출력하지 않습니다. 정성제안서(기술제안서) 본문, 요약본, 발표자료에 대한 요건만 다루고, 공고문 자체의 서식이나 가격제안서, 입찰참가신청서의 작성 요령은 다루지 않습니다. 대상 문서가 여럿이면 필드 이름에 정해진 접두어(main, summary, presentation)를 씁니다.

글자 크기, 쪽수, 용량 같은 값은 원문의 표기를 그대로 옮깁니다. "13포인트", "12pt 이상", "100쪽 이내(표지·목차 제외)"처럼 적힌 대로 쓰고 단위를 바꾸지 마십시오. 변환은 프로그램이 합니다. 쪽수 제한에서 빼는 항목(표지, 목차, 간지 등)이 적혀 있으면 따로 적습니다. 허용 여부를 묻는 필드는 원문이 금지하면 false, 원문이 명시적으로 허용하면 true로 적습니다. 블라인드 평가라면 표시하지 말아야 할 대상(회사명, 로고, CI, 대표자명, 제품명, 인력 실명 등)을 원문에 적힌 대로 나열합니다.

채운 필드마다 근거를 붙입니다. 근거는 요건이 적힌 블록의 ID와, 그 블록에서 해당 요건을 담은 구절을 10자에서 60자 사이로 글자 그대로 옮긴 인용문입니다. 고치거나 여러 곳을 이어 붙이지 마십시오.

필드로 나타낼 수 없는 작성 요건(장 제목 가운데 정렬, 표 테두리, 쪽 번호 위치, 파일 이름 규칙 등)은 manual에 원문 그대로 한 줄씩, 한 줄에 80자 이내로 적습니다. 원문의 표현이 애매해 해석이 갈리는 부분은 notes에 짧게 적습니다.
```

코드 후처리(OBK 이식): pt 변환과 범위 검사(본문 8~20pt, 쪽 1~1,000, 용량 1~2,000MB), 근거 원문 대조, 극성 검사(5.4절 사전), 숫자 표기 대조(아라비아·한글 수사), 누락 탐지(키워드: 쪽 이내·포인트·pt·MB·블라인드·글꼴·여백·아래한글·PDF).

### 6.4 P-KR-4 지정 목차와 제출서류(별지 서식) 추출

- **원천:** OBK `outlineFormatExtraction.cjs:99-144`(A.3.2), `:17-20`(A.3.1)
- **바꾼 점:** 투찰 문서 격식 장 → "제안서 목차(작성 순서)" + "제출서류·별지 서식", 위치는 블록 ID 구간, content_mode 한국화

```text
이 작업은 제안요청서가 정한 제안서의 목차(작성 순서)와 제출서류 목록을 원문 그대로 옮기는 것입니다. <rfp> 안의 각 줄은 문서 블록이며, 줄 앞의 대괄호는 블록 ID입니다. 블록은 문서 순서대로 있습니다.

먼저 두 부분을 찾습니다. 첫째는 제안서를 어떤 목차와 순서로 작성하라고 정한 부분입니다. 보통 "제안서 작성 목차", "제안서 구성", "작성 순서" 같은 표나 목록입니다. 둘째는 제출해야 하는 서류와 그 서식을 정한 부분입니다. "제출서류 목록", "별지 제○호 서식", "붙임" 같은 이름으로 문서 끝에 모여 있는 경우가 많습니다. 제목 문구가 아니라 내용의 기능으로 판단하십시오. 단순히 어떤 서류를 내야 한다고 언급만 하고 목차나 서식을 주지 않는 부분은 해당하지 않습니다.

찾은 부분의 조목을 원문 순서와 계층 그대로 노드로 만듭니다. 조목을 합치거나 나누거나 새로 만들거나 빼지 마십시오. 원문이 어떤 조목들을 상위 조목 아래 묶어 둔 경우에만 하위 노드를 만듭니다. 제목은 원문에서 번호(Ⅰ., 1., 가., 제5호 등)와 서식 표시만 떼고 나머지 글자는 그대로 옮깁니다. 각 노드에는 시작 블록 ID와, 같은 층 다음 조목이 시작하는 블록 ID를 끝으로 적습니다. 마지막 조목의 끝은 그 부분의 끝입니다.

노드마다 처리 방식을 고릅니다. 제안사가 본문을 직접 써야 하면 본문작성, 주어진 서식의 칸을 채우면 서식채우기, 요구사항이나 평가항목을 한 줄씩 대응시키는 표(요구사항 대비표, 평가항목별 쪽 대비표 등)면 대비표, 제안서 자체의 목차 쪽이면 목차, 가격처럼 제안사가 따로 작성해 내는 것이면 별도작성, 어디에도 맞지 않으면 기타로 하고 이유를 적습니다. 계약 체결 때 내는 서류처럼 제안서 제출 단계에서 필요 없는 조목도 빠뜨리지 말고 적되, 계약시제출로 표시합니다.

두 부분 가운데 하나라도 찾지 못하면 해당 목록을 비우고, 찾지 못했다는 사실을 notes에 적습니다.
```

코드 후처리(OBK `validateFormatOutline` 이식): 블록 ID 존재, 시작<끝, 같은 층 순서·비중첩, 자식⊂부모, **제목이 시작 블록부터 3개 블록 안에 실제로 있는지**(공백·문장부호 정규화 후 포함). 위반 목록을 붙여 1회 재요청하고, 실패하면 G1 큐로 보낸다.

### 6.5 P-KR-5 실격사유·필수 요구 대비 3단계 점검(M2 check, LLM 보조)

- **원천:** OBK `rejectionPrompts.ts:13-137`(A.6.1), BMP `disqualification_check_skill.py:53-172`(A.9.2)
- **바꾼 점:** 지류·현장 제외 → 전자 문서로 판단할 수 없는 항목 제외, 증거는 절 ID와 렌더 쪽, 3단계 유지. 결정적 규칙(COV·PAGE·FMT·BLD·SUB)이 먼저 돌고, 이 점검은 그 밖의 서술형 조건만 맡는다

```text
[공통 입력]
<conditions>는 제안요청서에서 추출해 사람이 확정한 입찰무효·평가 제외·감점 조건과 필수 요구사항입니다. <custom_checks>는 사용자가 덧붙인 확인 사항입니다. <proposal>은 렌더된 제안서 본문으로, 각 단락 앞에 절 ID와 쪽 번호가 붙어 있습니다.

<proposal>은 문서에서 글자만 뽑은 것이라 그림, 도식, 스캔한 증빙의 내용은 보이지 않습니다. 어떤 자료가 빠졌는지 판단할 때 그림이나 스캔본 내용이 보이지 않는다는 이유만으로 빠졌다고 보지 마십시오. 해당 자료의 절 제목, 목차 항목, 첨부 제목, 표 제목, 쪽 단서, 그림 자리표시 같은 구조적 흔적이 있으면 제출 흔적이 있는 것으로 봅니다.

[1단계: 분석]
조건 가운데 제안서 본문만 보고 판단할 수 있는 것과 판단할 수 없는 것을 나눕니다. 인증서 서명, 가격제안서의 금액, 현장 발표, 서류 원본 확인처럼 제안서 본문 밖의 사실이나 행위가 필요한 조건은 "본문 점검 대상 아님"으로 표시합니다. 판단할 수 있는 조건마다 제안서의 어느 절과 표를 확인해야 하는지 적습니다. 최종 위험 목록은 아직 내지 마십시오.

[2단계: 점검]
1단계 분석을 바탕으로 조건을 하나씩 확인해 위험 후보를 적습니다. 모든 후보에는 제안서에서 찾은 근거(절 ID, 쪽, 원문 인용)나, 찾아야 할 곳을 모두 살폈는데도 흔적이 없었다는 설명이 있어야 합니다. 근거가 부족하면 후보로 적지 마십시오.

[3단계: 확정]
2단계 후보를 합치고, 중복을 없애고, 빠진 조건이 없는지 다시 확인합니다. 본문 점검 대상이 아닌 조건, 추측에만 기댄 후보, 그림이나 스캔본이 보이지 않아서 생긴 누락 후보는 지웁니다. 같은 문제는 하나로 합치고 제목을 짧게 씁니다. 남은 위험마다 조건 분류(입찰무효, 평가 제외, 감점), 심각도(높음, 중간, 낮음), 관련 조건 원문, 제안서 근거, 위험한 이유, 고칠 방법을 적습니다. 위험이 없으면 빈 목록을 냅니다.
```

코드 후처리: 제안서 근거 인용이 해당 절 텍스트에 있는지 확인한다(OBK 오탈자 위치 검증 방식). 100쪽 이상이면 롤링 patch 상태 기계(OBK `rejectionCheckTask.cjs:1021-1162`)로 나눠 돌린다. 결과는 check 리포트의 "LLM 리뷰(참고)" 영역에 넣고 게이트에는 쓰지 않는다(설계서 7.8).

---

## 7. 확인하지 못한 것과 한계

- **GitHub API 접근 불가.** 세션 권한이 없어 403을 받았다. 저장소 메타데이터(별 수, 라이선스 자동 판정)는 확인하지 못했다. 라이선스는 LICENSE 파일과 git 이력으로 판정했다.
- **OBK는 얕은 clone(1커밋)만 받았다.** LICENSE·NOTICE 변경 이력은 보지 않았다. NOTICE와 README가 일치해 판정에는 영향이 없다.
- **실행 검증 없음.** 지시에 따라 어떤 코드도 실행·설치하지 않았다. 기능 동작은 소스를 읽어 판단했다. 성능, 정확도, 실제 산출물 품질은 측정하지 않았다.
- **미검토 영역.** OBK `pi/` 에이전트 런타임, `exportService.cjs`(3,053줄)의 세부, C# `BlindCheck/Fix/*` 자동 수정기의 개별 로직, `contentGenerationTask.cjs`(3,113줄)의 배치·이미지 경로는 구조만 확인했다. BMP 데스크톱 UI와 뉴스 수집(`services/news/`)은 범위 밖이라 보지 않았다.
- **한국 제도 수치.** 협상적격 기준, 체크섬 알고리즘(법인등록번호) 등 이 문서에 쓴 한국 제도 값은 설계서 부록 A의 원문 대조 원칙에 따라 provisional로 다룬다.
- **법률 판단.** AGPL·Apache 의무 서술은 라이선스 원문에 근거한 실무 정리다. 배포·서비스 형태가 정해지면 법률 검토를 받는다(설계서 11.2와 같은 입장).

---

<!-- 부록 A는 소스에서 줄 범위를 그대로 잘라 붙인 것이다(scratchpad/tools/build_appendix.py로 생성). -->

## 부록 A. 핵심 프롬프트 원문(중국어, 소스 그대로)

아래 블록은 각 저장소의 소스 파일에서 지정한 줄 범위를 **그대로** 잘라 붙인 것이다. 코드 일부(문자열 결합, 변수 치환 `${...}`/`{...}`)가 함께 들어 있다. 경로는 `scratchpad/ext/` 기준이며, 줄 번호는 1장 표의 커밋 기준이다. 라이선스: OpenBidKit·BidMaster-Pro·BidPilot-AI 원문은 AGPL-3.0, BiaoShu-SKILL 원문은 Apache-2.0이다(1장 참조). 번역·이식 시 4.3절 의무를 따른다.

### A.1 OpenBidKit_Yibiao — 招标文件解析(입찰문서 해석)

#### A.1.1 공통 system 프롬프트, JSON 과제 틀, 无效投标/废标项 프롬프트

`OpenBidKit_Yibiao/client/electron/services/bidAnalysisTask.cjs:8-65`

````javascript
const stableSystemPrompt = `你是专业的投标资料分析助手。请严格基于用户提供的上下文完成提取和总结。

通用要求：
1. 保持信息全面、准确，优先使用用户提供上下文中的内容；除非具体任务明确要求或允许根据经验补充，否则不要自行编造
2. 已提取到相关内容但局部信息没有提及时，明确写“没有提及”
3. 只输出最终结果，不输出过程、提示语或客套话
4. 始终使用简体中文`;

function jsonTask(title, goals, outputJson) {
  return `任务：${title}

目标：${goals}

约束：
1. 输出格式必须为 JSON。
2. 严格按照以下 JSON 格式输出，只修改 value，禁止修改 key 和结构。
3. 招标文件中没有的字段填充“没有提及”。

JSON 格式：
${outputJson}

仅输出 JSON，不要输出其他内容。`;
}

function buildInvalidBidAndRejectionItemsPrompt() {
  return `任务：提取并分析招标文件中的“无效投标”和“废标项”。

概念边界：
1. “无效投标”指投标人、投标文件、签章密封、递交时间、报价、保证金、资格条件、实质性响应等原因导致投标被认定为无效、否决、不予受理或按无效响应处理的情形。
2. “废标项”指可能导致项目废标、采购失败、重新招标、终止评审、有效投标人不足或实质性响应不足的条款或风险项。
3. 招标文件使用“否决投标”“投标无效”“不予受理”“无效响应”“重大偏差”“实质性偏离”“废标情形”等同义表达时，也要按上述边界归类。

输出要求：
1. 必须明确区分“无效投标”和“废标项”。
2. “招标文件中明确提到的”只能提取招标文件中明确出现或同义表达的内容，尽量保留招标文件中的关键句；如果没有提及，写“招标文件未提及”。
3. “此类标书还可能涉及的”需要根据你的经验，补充招标文件中未明确提及、但结合本招标文件类型和招投标经验判断非常重要的高风险遗漏项。
4. 不要罗列所有常见可能项，不要输出泛泛的通用清单；每个小节最多输出 3-5 条。
5. 不要使用表格，使用 Markdown 列表。
6. 仅输出下方格式，不要输出解释、过程或额外段落。
7. 不要输出三重引号、代码块标记或其他格式包裹符。

输出格式：
# 招标文件中明确提到的

## 无效投标
- ...

## 废标项
- ...

# 此类标书还可能涉及的

## 无效投标
- ...

## 废标项
- ...`;
}
````

#### A.1.2 해석 과제 목록(项目概述·技术评分·商务评分·响应文件要求 등 18개)

`OpenBidKit_Yibiao/client/electron/services/bidAnalysisTask.cjs:67-178`

````javascript
const tasks = [
  {
    id: 'projectOverview', label: '项目概述', required: true, output: 'markdown', description: '提取项目基本信息、背景目的、规模预算、时间安排、实施内容和技术特点等。',
    prompt: () => `任务：提取并总结项目概述信息。

请重点关注项目名称、基本信息、背景目的、规模预算、时间安排、实施内容、技术特点和其他关键要求。

工作要求：保持信息全面准确，尽量使用招标文件中的内容；只关注与项目实施有关的内容，不提取商务信息；直接返回整理好的项目概述。`,
  },
  {
    id: 'techRequirements', label: '技术评分要求', required: false, requiredIn: ['response-file', 'standalone-technical'], output: 'markdown', description: '提取技术评分项、权重分值、评分标准和招标文件中的位置。',
    prompt: () => `任务：提取技术评分信息，并按语义区分“技术评分项”和“技术评分要求”。

重点识别“技术评分”“评标方法”“评分标准”“技术参数”“技术要求”“技术方案”“技术部分”“评审要素”相关章节，不要提取商务、价格、资质等无关条目。

分类原则：
1. 技术评分项：指投标人需要在技术方案中一一响应、展开编写，并可对应形成技术方案章节的具体评分内容，例如方案类、措施类、团队类、实施类、服务类、保障类、运维类、应急类、检查类等评分内容。
2. 技术评分要求：指用于约束评分、解释评分、定义扣分或判定规则的通用规则或说明，例如符合性要求、偏离扣分规则、判定口径、适用范围说明、表后说明、通用评审规则等。
3. 判断依据是该内容是否要求投标人在技术方案中展开具体方案内容；如果不是具体方案内容，即使带有分值或扣分规则，也归入技术评分要求。
4. 若原文存在层级关系，请保持顺序和来源，不要自行合并不相关条款。

输出格式：

## 技术评分项

【评分项名称】：<招标文件描述，保留专业术语>
【权重/分值】：<具体分值或占比>
【评分标准】：<详细规则>
【数据来源】：<章节、条款、页码或表格位置>

## 技术评分要求

【评分要求名称】：<要求或规则名称>
【适用范围】：<适用于哪些评分项或评审环节>
【要求/判定口径】：<具体要求、解释、扣分或判定规则>
【数据来源】：<章节、条款、页码或表格位置>

若某一类没有内容，请保留对应标题并写“没有提及”。直接返回提取结果。`,
  },
  { id: 'projectInfo', label: '项目信息', required: true, output: 'json', description: '项目名称、编号、类型、预算和地址。', prompt: () => jsonTask('提取项目信息', '提取项目名称、项目编号、项目类型、项目预算、项目地址。', `{"project_name":"项目名称","project_number":"项目编号","project_type":"项目类型","project_budget":"项目预算","project_address":"项目地址"}`) },
  { id: 'partAInfo', label: '甲方信息', required: true, output: 'json', description: '招标人公司、地址、联系人和电话。', prompt: () => jsonTask('提取甲方信息', '提取公司名称、地址、联系人、联系电话。', `{"company_name":"公司名称","address":"地址","contact_person":"联系人","contact_phone":"联系电话"}`) },
  { id: 'deliveryAndServiceRequirements', label: '交货和服务要求', required: true, output: 'json', description: '实施周期、交付范围、地点、验收、质保、售后、响应、培训和文档要求。', prompt: () => jsonTask('提取交货和服务要求', '提取实施周期/工期/交付期限、交付范围、交付/实施地点、验收要求、质保期、售后服务要求、响应时限、培训要求、资料/文档交付要求。', `{"implementation_period":"实施周期/工期/交付期限","delivery_scope":"交付范围","delivery_location":"交付/实施地点","acceptance_requirements":"验收要求","warranty_period":"质保期","after_sales_service":"售后服务要求","response_time":"响应时限","training_requirements":"培训要求","documentation_requirements":"资料/文档交付要求"}`) },
  {
    id: 'procurementList', label: '采购清单', required: false, output: 'markdown', description: '采购内容、数量、规格参数、交付和验收要求。',
    prompt: () => `任务：提取招标文件、询比文件或采购文件中的采购清单/采购需求信息。

请从招标文件中识别与“采购清单、采购需求、采购内容、货物需求、服务内容、技术参数、规格要求、报价清单、分项报价、工程量清单”等含义相近的内容。

提取要求：
1. 优先保留招标文件中的表格、条目和字段含义，不要自行补充招标文件没有的信息。
2. 如果原文是表格，请尽量整理为 Markdown 表格；如果表格结构复杂，可以按“清单项 + 要求说明”的方式整理。
3. 如果不同章节分别描述采购内容、技术参数、数量、交付、验收、质保等要求，请合并整理，但要避免编造不存在的字段。
4. 字段名称不要求固定，按招标文件实际出现的信息组织，例如名称、规格型号、技术参数、单位、数量、预算/限价、交付地点、交付时间、验收要求、质保要求、备注等。
5. 如果没有找到明确采购清单，请说明“未找到明确采购清单”，并列出可能相关的采购需求段落摘要。
6. 只输出整理结果，不要输出分析过程。`,
  },
  {
    id: 'responseFileRequirements', label: '响应文件要求', required: true, output: 'markdown', description: '响应文件组成、格式模板、签章、递交和偏离表要求。',
    prompt: () => `任务：提取招标文件、询比文件或采购文件中关于响应文件/投标文件编制与提交的要求。

请识别与“响应文件、投标文件、报价文件、资格证明文件、商务响应、技术响应、偏离表、响应文件格式、投标文件格式、递交要求、签字盖章、密封上传”等含义相近的内容。

提取要求：
1. 按招标文件实际结构整理，不要强制套用固定模板。
2. 重点提取响应文件需要包含哪些部分，例如报价文件、商务文件、技术文件、资格证明、承诺函、授权委托书、响应表、偏离表、分项报价表等。
3. 如果招标文件提供了固定格式、表格或附件模板，请提取模板名称、用途、填写要求和关键字段。
4. 提取签字盖章、文件命名、装订/密封、上传格式、份数、递交截止时间、递交方式等要求。
5. 保持投标文件中所列的响应文件顺序，保证后续编写响应文件时，可以直接按照你提取的结果一一对应编写。
6. 区分“必须提供”和“如适用/可选提供”的内容；如果招标文件没有明确区分，不要自行判断。
7. 不要生成供应商自己的最终响应文件，不要编造公司信息、报价、资质、承诺内容。
8. 如果没有找到明确响应文件要求，请说明“未找到明确响应文件要求”，并列出可能相关的投标/响应文件格式段落摘要。
9. 只输出整理结果，不要输出分析过程。`,
  },
  { id: 'agentInfo', label: '代理机构信息', required: false, output: 'json', description: '代理机构联系方式和账户信息。', prompt: () => jsonTask('提取代理机构信息', '提取代理机构名称、地址、联系人、电话、邮箱和银行账户信息。', `{"company_name":"公司名称","address":"地址","contact_person":"联系人","contact_phone":"联系电话","email":"联系邮箱","bank_account_name":"银行账户名称","bank_account_number":"银行账户账号","bank_account_address":"银行账户开户行","bank_account_address_detail":"银行账户开户行地址"}`) },
  { id: 'keyInfo', label: '投标关键节点', required: false, output: 'json', description: '公告、获取文件、递交、截止和开标信息。', prompt: () => jsonTask('提取投标关键节点', '提取招标公告发布日期、招标文件获取方式、售价、获取时间、提交地点、截止时间、开标时间、开标地点和其他注意事项。', `{"bid_announcement_time":"招标公告发布日期","bid_file_get_way":"招标文件获取方式","bid_file_price":"招标文件售价","get_bid_file_time":"获取招标文件时间","bid_document_submission_location":"投标文件提交地点","bid_submission_deadline":"投标截止时间","bid_opening_time":"开标时间","bid_opening_address":"开标地点","other_notes":"其他注意事项"}`) },
  { id: 'marginInfo', label: '投标保证金', required: false, output: 'json', description: '保证金金额、方式、截止和退还条件。', prompt: () => jsonTask('提取投标保证金信息', '提取投标保证金、缴纳方式、截止日期、退还条件、不予退还情形和其他注意事项。', `{"bidding_deposit":"投标保证金","payment_method":"缴纳方式","due_date":"截止日期","refund_conditions":"退还条件","non_refundable_conditions":"不予退还的情形","other_notes":"其他注意事项"}`) },
  { id: 'qualificationReview', label: '资格性审查', required: false, output: 'markdown', description: '投标人资格条件和资格审查要求。', prompt: () => '任务：提取招标文件中关于投标人资格性审查的信息。整理成方便阅读的 Markdown，不要使用表格；如果招标文件是表格，请转换为列表。仅输出整理结果。' },
  { id: 'complianceCheck', label: '符合性检查', required: false, output: 'markdown', description: '文件完整性、有效性、规范和偏差处理要求。', prompt: () => '任务：总结招标文件中关于符合性检查的信息，包括文件完整性、文件有效性、文件规范、偏差处理等。整理成 Markdown，不要使用表格。仅输出整理结果。' },
  { id: 'openBid', label: '开标要求', required: false, output: 'json', description: '开标时间地点、参与要求、无效标和流程。', prompt: () => jsonTask('提取开标信息', '提取时间地点、参与要求、无效标认定、异议处理、开标流程。', `{"time_place":"时间地点","part_req":"参与要求","invalid_bid":"无效标认定","objection":"异议处理","bid_process":"开标流程"}`) },
  { id: 'evaluationBid', label: '评标要求', required: false, output: 'json', description: '评标委员会、评分构成、方法和原则。', prompt: () => jsonTask('提取评标信息', '提取评标委员会组成、职责、评分构成、评标方法类型、评标原则和方法细节、其他评标相关说明。', `{"committee":"评标委员会组成","duties":"评标委员会职责","scoring":"评分构成","method":"评标方法类型","principles":"评标原则和方法细节","others":"其他和评标相关的说明"}`) },
  {
    id: 'businessScoring', label: '商务评分要求', required: false, requiredIn: ['response-file', 'standalone-business'], output: 'markdown', description: '提取技术评分以外的评分项、分值、评分标准和招标文件中的位置。',
    prompt: () => `任务：提取技术评分以外的评分信息（商务、资信、业绩、服务承诺、价格等），并按语义区分“商务评分项”和“商务评分要求”。

分类原则：
1. 商务评分项：评分表中技术评分以外的每一个具体评分项，例如价格、业绩、资质证书、人员资格、服务承诺、商务条款偏离等。
2. 商务评分要求：约束上述评分的通用规则或说明，例如证明材料要求、扣分或判定口径、计分方法、表后说明等。
3. 技术评分项和只适用于技术评分的规则不在本项提取。
4. 若原文存在层级关系，请保持顺序和来源，不要自行合并不相关条款。

输出格式：

## 商务评分项

【评分项名称】：<招标文件描述，保留原文用语>
【权重/分值】：<具体分值或占比>
【评分标准】：<详细规则>
【数据来源】：<章节、条款、页码或表格位置>

## 商务评分要求

【评分要求名称】：<要求或规则名称>
【适用范围】：<适用于哪些评分项或评审环节>
【要求/判定口径】：<具体要求、解释、扣分或判定规则>
【数据来源】：<章节、条款、页码或表格位置>

若某一类没有内容，请保留对应标题并写“没有提及”。直接返回提取结果。`,
  },
  { id: 'discardedBids', label: '无效标与废标项', required: false, output: 'markdown', description: '投标无效、废标相关风险项。', prompt: buildInvalidBidAndRejectionItemsPrompt },
  { id: 'signingProcess', label: '合同授予与签订', required: false, output: 'json', description: '中标公示、合同签订、履约保证金和合同文本。', prompt: () => jsonTask('提取合同授予和签订流程', '提取中标公示、合同签订、履约保证金、合同文本等信息。', `{"bid_notice":"中标公示","contract_sign":"合同签订","performance_bond":"履约保证金","contract_text":"合同文本"}`) },
  { id: 'terminationCondition', label: '合同解除和终止', required: false, output: 'json', description: '违约解除、不可抗力、合同终止和争议解决。', prompt: () => jsonTask('提取合同解除和终止条件', '提取违约解除、不可抗力、合同终止、争议解决等信息。', `{"breach_termination":"违约解除","force_majeure":"不可抗力","contract_termination":"合同终止","dispute_resolution":"争议解决"}`) },
];
````

#### A.1.3 '전체 무결과' 규칙과 공유 접두부(招标文件 전문) 메시지 구성

`OpenBidKit_Yibiao/client/electron/services/bidAnalysisTask.cjs:217-239`

````javascript
// 为 Markdown 解析项统一约定整项无结果标记，避免与局部缺失混淆。
function buildTaskPrompt(task) {
  const prompt = task.prompt();
  if (task.output !== 'markdown') return prompt;
  return `${prompt}

整体无结果规则：仅当当前任务完全未提取到任何相关内容时，只返回“${MARKDOWN_MISSING_RESULT}”，不要附加标题、标点、解释或其他文字。只要提取到任何有效内容，就正常返回结果；局部字段或局部分类缺失时写“没有提及”，不要使用“${MARKDOWN_MISSING_RESULT}”。`;
}

function isMissingMarkdownResult(task, content) {
  return task.output === 'markdown' && String(content || '').trim() === MARKDOWN_MISSING_RESULT;
}

function buildTenderContextMessages(fileContent, sectionHint) {
  const messages = [
    { role: 'system', content: stableSystemPrompt },
  ];
  if (sectionHint) {
    messages.push({ role: 'system', content: sectionHint });
  }
  messages.push({ role: 'user', content: `以下是完整招标文件。后续任务需要基于这份招标文件完成；如后续消息提供补充上下文，请按具体任务要求综合使用：\n\n${fileContent}` });
  return messages;
}
````

#### A.1.4 (Renderer 측 사본) 无效投标/废标项 프롬프트

`OpenBidKit_Yibiao/client/src/shared/prompts/analysisPrompts.ts:1-36`

````javascript
export function buildInvalidBidAndRejectionItemsPrompt() {
  return `任务：提取并分析招标文件中的“无效投标”和“废标项”。

概念边界：
1. “无效投标”指投标人、投标文件、签章密封、递交时间、报价、保证金、资格条件、实质性响应等原因导致投标被认定为无效、否决、不予受理或按无效响应处理的情形。
2. “废标项”指可能导致项目废标、采购失败、重新招标、终止评审、有效投标人不足或实质性响应不足的条款或风险项。
3. 原文使用“否决投标”“投标无效”“不予受理”“无效响应”“重大偏差”“实质性偏离”“废标情形”等同义表达时，也要按上述边界归类。

输出要求：
1. 必须明确区分“无效投标”和“废标项”。
2. “原文中明确提到的”只能提取招标文件原文中明确出现或同义表达的内容，尽量保留原文关键句；如果没有提及，写“- 原文未提及”。
3. “此类标书还可能涉及的”只补充原文未明确提及、但结合本招标文件类型和招投标经验判断非常重要的高风险遗漏项。
4. 不要罗列所有常见可能项，不要输出泛泛的通用清单；每个小节最多输出 3-5 条。
5. 如果没有明显需要补充的关键项，写“- 暂未发现必须补充的高风险项”。
6. 经验补充项每条前缀使用“重点补充：”，并用一句话说明为什么需要关注。
7. 不要使用表格，使用 Markdown 列表。
8. 仅输出下方格式，不要输出解释、过程或额外段落。
9. 不要输出三重引号、代码块标记或其他格式包裹符。

输出格式：
# 原文中明确提到的

## 无效投标
- ...

## 废标项
- ...

# 此类标书还可能涉及的

## 无效投标
- 重点补充：...

## 废标项
- 重点补充：...`;
}
````

#### A.1.5 분할 해석 결과 병합 프롬프트

`OpenBidKit_Yibiao/client/electron/utils/segmentedAiResultMerger.cjs:12-48`

````javascript
function buildMergeMessages({ segmentResults, taskPrompt, output, systemPrompt, sectionHint, taskLabel }) {
  const messages = [];
  if (systemPrompt) {
    messages.push({ role: 'system', content: systemPrompt });
  }
  if (sectionHint) {
    messages.push({ role: 'system', content: sectionHint });
  }

  const outputRequirement = output === 'json'
    ? '最终只返回一个 JSON 对象，不要输出 Markdown、代码块、解释或额外文字。'
    : '最终只返回整理后的 Markdown 内容，不要输出解释、过程或额外提示语。';

  messages.push({
    role: 'user',
    content: `以下内容来自同一份招标文件按段分别解析后的结果。每段结果只代表该片段内的信息，不代表整份文件的完整结论。

当前合并任务：${taskLabel || '招标文件解析结果合并'}

合并要求：
1. 如果某段写“没有提及”“原文未提及”“本段未提及”或整段只有“未提取到”，只表示该片段没有相关信息；如果其他片段提供了有效信息，应以有效信息为准。
2. 删除重复、空泛、冲突的片段性表述，保留更完整、更具体的信息。
3. 保留所有有价值、可用于最终结果的信息，不要遗漏分段结果中的明确内容。
4. 不要新增分段结果中没有的信息，不要自行编造。
5. 如果所有分段都没有有效信息，遵守原始任务中的整体无结果规则。
6. 最终输出必须符合原始任务要求。
7. ${outputRequirement}

原始任务要求：
${taskPrompt}

分段解析结果：
${formatSegmentResults(segmentResults)}`,
  });

  return messages;
}
````

#### A.1.6 JSON 복구 프롬프트

`OpenBidKit_Yibiao/client/src/shared/prompts/jsonRepairPrompts.ts:1-25`

````javascript
import type { ChatMessage } from '../types';

export interface BuildJsonRepairMessagesInput {
  invalidContent: string;
  issues: string[];
  targetDescription: string;
}

export function buildJsonRepairMessages({
  invalidContent,
  issues,
  targetDescription,
}: BuildJsonRepairMessagesInput): ChatMessage[] {
  const issueLines = issues.map((item, index) => `${index + 1}. ${item}`).join('\n');

  return [
    {
      role: 'system',
      content: '你是一个严格的 JSON 修复助手。必须修复 JSON 字符串中的非法反斜杠转义，例如将 1\\. 改为 1.，或将必须保留的反斜杠写成 \\\\。只返回修复后的完整 JSON，不要输出任何解释。',
    },
    { role: 'user', content: `目标结果类型：${targetDescription}` },
    { role: 'user', content: `当前校验问题：\n${issueLines}` },
    { role: 'user', content: `待修复内容：\n\`\`\`json\n${invalidContent}\n\`\`\`` },
  ];
}
````

### A.2 OpenBidKit_Yibiao — 작성지침(暗标 排版格式) 추출

#### A.2.1 키워드 창 탐색 상수와 추출 가능 필드 목록

`OpenBidKit_Yibiao/client/electron/services/blindCheckPresetExtraction.cjs:6-67`

````javascript
const FORMAT_KEYWORDS = /(宋体|仿宋|黑体|楷体|字体|字号|号字|[初小一二三四五六七八]号|行距|行间距|磅|页边距|边距|A4|纸张|首行缩进|缩进|段前|段后|页眉|页脚|页码|加粗|倾斜|斜体|下划线|排版|装订|黑白|彩色|空行)/g;
const CONTEXT_KEYWORDS = /(暗标|技术标|施工组织设计|投标文件)/;
const WINDOW_BEFORE = 12;
const WINDOW_AFTER = 28;
const MAX_WINDOWS = 6;
const MAX_EXCERPT_CHARS = 20000;
// 片段里格式词太少说明不是格式条款，不调用 AI。
const MIN_WINDOW_SCORE = 6;

const CHINESE_SIZES = {
  初号: 42, 小初: 36, 一号: 26, 小一: 24, 二号: 22, 小二: 18, 三号: 16, 小三: 15,
  四号: 14, 小四: 12, 五号: 10.5, 小五: 9, 六号: 7.5, 小六: 6.5, 七号: 5.5, 八号: 5,
};

const HEADING_LEVELS = ['1', '2', '3', '4'];

// 禁止性和允许性表述，用于核对开关字段的取值方向；允许性要先去掉"不允许""不可"等否定写法再判断。
const NEGATION = /不得|不允许|不准|不应|不能|不可|禁止|严禁|不要|不宜|勿|不使用|不采用|不出现|不设|不编/;
const PERMISSION = /允许|可以|可|宜/;

/** 可提取字段：路径、类型、说明。路径与预设档案一致，类型决定如何校验。 */
const EXTRACTABLE_FIELDS = [
  ['page.paper', 'paper', '纸张大小：A4 / A3 / Letter'],
  ['page.margin_top_cm', 'margin', '上边距（厘米）'],
  ['page.margin_bottom_cm', 'margin', '下边距（厘米）'],
  ['page.margin_left_cm', 'margin', '左边距（厘米）'],
  ['page.margin_right_cm', 'margin', '右边距（厘米）'],
  ['body.font_cn', 'font', '正文中文字体'],
  ['body.font_en', 'font', '正文西文字体'],
  ['body.size_pt', 'size', '正文字号，照抄原文写法即可，如"四号""小四""10.5磅"'],
  ['body.line_rule', 'lineRule', '行距类型：exact（固定值）/ atLeast（最小值）/ multiple（倍数行距）'],
  ['body.line_pt', 'linePt', '固定值或最小值行距的磅数'],
  ['body.line_multiple', 'lineMultiple', '倍数行距的倍数，如 1.5'],
  ['body.first_line_indent_chars', 'indent', '首行缩进的字符数'],
  ['body.space_before_pt', 'spacing', '段前间距（磅），"0 行"填 0'],
  ['body.space_after_pt', 'spacing', '段后间距（磅），"0 行"填 0'],
  ['body.alignment', 'alignment', '正文对齐：left（左对齐）/ both（两端对齐）/ center / right'],
  ['body.allow_bold', 'allow', '正文加粗：原文禁止填 false，原文明确允许填 true'],
  ['body.allow_italic', 'allow', '倾斜：原文禁止填 false，原文明确允许填 true'],
  ['body.allow_underline', 'allow', '下划线：原文禁止填 false，原文明确允许填 true'],
  ['body.allow_color', 'allow', '彩色文字：原文要求黑色或禁止彩色填 false，原文明确允许彩色填 true'],
  ['body.allow_highlight', 'allow', '突出显示和字符底纹：原文禁止填 false，原文明确允许填 true'],
  ['body.allow_char_spacing', 'allow', '调整字符间距：原文禁止填 false'],
  ['body.allow_font_scaling', 'allow', '字符缩放：原文禁止填 false'],
  ['body.check_latin_size', 'boolean', '数字、英文字符的字体字号：原文写"数字、英文字符不做要求"填 false'],
  ...HEADING_LEVELS.flatMap((level) => [
    [`headings.${level}.font_cn`, 'font', `${level} 级标题中文字体`],
    [`headings.${level}.size_pt`, 'size', `${level} 级标题字号，照抄原文写法`],
    [`headings.${level}.bold`, 'boolean', `${level} 级标题是否加粗`],
  ]),
  ['table.font_cn', 'font', '表格内中文字体；原文写"同正文"时填正文字体'],
  ['table.size_pt', 'size', '表格内字号；原文写"同正文"时填正文字号'],
  ['table.first_line_indent_chars', 'indent', '表格内首行缩进字符数'],
  ['table.allow_bold', 'allow', '表格文字加粗：原文对表格单独规定时才填，禁止填 false，允许填 true；没有单独规定不要填（按正文要求）'],
  ['structure.forbid_header_content', 'forbid', '页眉：原文规定不得有页眉或页眉不得有内容填 true，原文允许或要求页眉写内容填 false'],
  ['structure.forbid_footer_content', 'forbid', '页脚：原文规定页脚不得有任何内容（含页码）填 true，原文允许页脚写内容填 false；原文写"页脚只准出现页码"时不填此项'],
  ['structure.page_number', 'pageNumber', '页码：forbid（不得出现页码）/ footer_only（页脚只准出现页码）/ any（允许或要求编页码，对页脚没有其他限制）'],
  ['structure.check_toc_present', 'toc', '目录：forbid（不得有目录）/ require（必须有目录）'],
  ['structure.heading_numbering', 'numbering', '标题序号：原文要求用阿拉伯数字分级编排（一级 1、二级 1.1、三级 1.1.1）时填 arabic'],
  ['structure.check_empty_paragraphs', 'forbid', '空行：原文不允许留空行或空白行填 true，原文明确允许填 false'],
  ['image.check_color', 'forbid', '图片、图表要求黑白或禁止彩色时填 true'],
];
````

#### A.2.2 SYSTEM_PROMPT와 메시지 구성

`OpenBidKit_Yibiao/client/electron/services/blindCheckPresetExtraction.cjs:134-172`

````javascript
const SYSTEM_PROMPT = `你是招标文件格式条款的解析助手。用户会给你招标文件中与排版格式有关的若干片段，你要找出对【投标文件技术标（暗标、施工组织设计）】的排版格式要求，按指定字段整理成 JSON。

要求：
1. 只提取原文明确写出的要求。原文没写的字段不要出现，不要按惯例补默认值；原文写"不作要求""由投标人自定"的也不要出现。
2. 只提取对技术标/暗标/施工组织设计/投标文件正文的要求。招标文件自身的格式、商务标、资格审查文件的要求不要提取。
3. 字号照抄原文写法（如"四号""小四""10.5磅"），不要自己换算；页边距用厘米；段前段后"0 行"填 0。
4. 原文规定"二级及以下标题与正文相同"时，在 headings.2 至 headings.4 填写与正文相同的字号和加粗要求；原文规定表格字体"同正文"时，表格字段填写正文的字体字号；原文全文禁止加粗时，各级标题的 bold 也填 false；原文写"不允许字符间距缩放"一类表述时，body.allow_char_spacing 和 body.allow_font_scaling 都填 false；原文写"页脚只准出现页码"时 structure.page_number 填 footer_only；原文写"数字、英文字符不做要求"时 body.check_latin_size 填 false。
5. 允许类字段（allow_*）原文禁止填 false、原文明确允许也要填 true；页眉、页脚、空行字段原文禁止填 true、原文明确允许填 false。
6. 每个填写的字段都要给出 evidence：招标文件中的原文片段，逐字摘录包含该要求的完整分句（10～60 字），不要改写或拼接。
7. 无法用下列字段表达的格式要求（如标题居中、图表标题格式、封面封底格式、页数上限、装订、编制软件），把原文逐条写进 manual，每条不超过 80 字。

只输出 JSON，格式如下：
{
  "fields": {
    "body.size_pt": { "value": "四号", "evidence": "正文部分字体采用四号宋体" }
  },
  "manual": ["图表居中放置，所有边框采用0.5磅黑色单实直线"],
  "notes": "可选：原文表述含糊之处"
}`;

function buildExtractionMessages(excerptText) {
  const fieldList = EXTRACTABLE_FIELDS.map(([fieldPath, , description]) => `- ${fieldPath}：${description}`).join('\n');
  return [
    { role: 'system', content: SYSTEM_PROMPT },
    {
      role: 'user',
      content: [
        '请从下面的招标文件片段中提取技术标（暗标）的排版格式要求。',
        '',
        '可填写的字段：',
        fieldList,
        '',
        '=== 招标文件片段开始 ===',
        excerptText,
        '=== 招标文件片段结束 ===',
      ].join('\n'),
    },
  ];
}
````

### A.3 OpenBidKit_Yibiao — 지정 목차(投标文件格式) 추출

#### A.3.1 content_mode 판정 규칙(目录·规则和页码)

`OpenBidKit_Yibiao/client/electron/services/outlineFormatExtraction.cjs:17-20`

````javascript
// 投标文件目录的判断口径，生成和调整目录的提示词共用。
const DIRECTORY_GENERATE_RULE = '“目录”（attr=目录、content_mode=directory-generate）只指投标文件自身的目录页：列出本文件各章节标题和页码，导出时按实际页码自动生成，全目录最多一个。标题带“目录”“检索”“页码”“清单”等字样、但行内容由招标文件规定的表格（如评分因素页码检索表、资料清单）不是目录。';
// 规则和页码的判断口径：按招标文件逐项列出、每行对应一条要求或评分项的表格，并标明应答依据（rule_basis）；生成和调整目录的提示词共用。
const RULE_PAGE_RULE = '“规则和页码”（content_mode=rule-page）指按招标文件规定逐项列出、每一行对应招标文件一条要求或一个评分项的表格，如评分因素页码检索表、商务或技术要求点对点应答表、偏离表、按招标清单逐项列出分项的报价表，不论是否标注本投标文件页码；只按固定格式填写的文件仍用 template-fill。rule-page 叶子必须填写 rule_basis，表示这张表应答的部分：应答技术要求或技术评分项的填 technical，应答商务要求或商务评分项的填 business，同时涵盖技术和商务的（如列出全部评分项的页码检索表、技术商务合在一起的偏离表）填 both；其他叶子不填写 rule_basis。';
````

#### A.3.2 격식 장 기반 목차 추출 프롬프트

`OpenBidKit_Yibiao/client/electron/services/outlineFormatExtraction.cjs:99-144`

````javascript
function createFormatOutlinePrompt({ structure, fallbackInstruction, sectionHint, outputRequirements, outputFile }) {
  const hasBlocks = [...structure.units.values()].some((unit) => unit.kind === 'blocks');
  const hasLines = structure.units.has(MARKDOWN_STRUCTURE_FILE);
  const structureDescriptions = [
    hasBlocks ? `${AGENT_BLOCKS_FILE}：招标 Word 原件的原文结构，每行一个非空原文块，格式为“块号 [标记] 文本”，位置编号就是块号。` : '',
    hasLines
      ? `${MARKDOWN_STRUCTURE_FILE}：${hasBlocks ? '没有 Word 原件的招标文件（如 PDF）的正文，按文件依次排列，每份以“【文件：文件名】”开头；' : '招标文件正文，'}每行以“L+六位行号 |”开头，位置编号取 L 后的行号数字（去掉前导 0）；同一行号带 [n/m] 的是超长行的分片。`
      : '',
  ].filter(Boolean);
  const sourceInstruction = structure.multipleSources
    ? `原文来自多份文件，format_scope 的每一段和每个节点的 source 都要填写 source 字段：位于 Word 原件中的，填写该原件在 ${AGENT_BLOCKS_FILE} 中“原件：”后列出的完整路径${hasLines ? `；位于 ${MARKDOWN_STRUCTURE_FILE} 中的，填写 ${MARKDOWN_STRUCTURE_FILE}` : ''}。`
    : '只有一份原文，source 中不需要填写 source 字段。';
  return `请只在当前工作目录内工作。
${outputRequirements}

任务：
我们的目标是为编写投标文件准备目录。招标文件通常会规定投标文件由哪些文件组成，并给出这些文件的格式供投标人照着编制；目录必须忠实取自这部分内容。${sectionHint ? `\n${sectionHint}` : ''}

材料：
${structureDescriptions.map((item) => `- ${item}`).join('\n')}
- 上述原文是判断和提取目录的依据，需要完整阅读后再判断。${structureDescriptions.length > 1 ? '格式章节可能只在其中一份中，也可能分布在两份中。' : ''}
- 其他文件只在没有找到格式章节时按下文第三步使用，或用于理解项目背景和术语。

第一步：判断招标文件是否给出了投标文件的组成和格式。
1. 按内容功能判断：招标文件中规定投标人应提交哪些文件、并给出这些文件的格式、样式或待填写文本的部分，就是格式章节。它可能是一个独立章节，也可能是集中放在文件末尾的一组附件。不同招标文件对这部分的叫法不同，判断依据是内容，不是标题用语。须知、评审办法等只提到应提交某些材料而没有给出格式的内容，不算格式章节。
2. 找到格式章节时，basis 填 ${FORMAT_TEMPLATE_BASIS}，format_scope 是数组，填该部分的位置，通常只有一段；格式分在几处（例如部分格式在另一份文件中）时，按招标文件规定的投标文件组成顺序逐段填写。找不到时 basis 填 ${RESPONSE_REQUIREMENTS_BASIS}，format_scope 填 null，并按第三步处理。

第二步（basis=${FORMAT_TEMPLATE_BASIS}）：按格式章节提取目录。
1. 格式章节自身列出的每一个文件或格式条目对应一个节点，按原文顺序排列。格式章节的顶层条目作为一级目录；只有格式章节本身把若干条目归在某个上级条目之下时，才按原文层级生成子目录，不得自行归类或增加层级。
2. 不合并、不拆分、不新增、不删除条目。招标文件其他位置对材料的统称不另建节点，它们指的就是格式章节中对应的文件。
3. title 取原文中该条目的标题，只去掉序号、附件编号、章节编号等前缀和仅表示格式或样式的标注，其余文字原样保留，不改写、不补充、不概括。
4. 原文只给出标题、要求投标人自行编写内容的条目，同样作为节点。
5. 只在中标后、签订合同或履约验收时使用、投标阶段不需要提交的条目也要列出，并设置 post_award=true；其他节点不填写 post_award。
6. 位置规则：start 为起始位置；end 为结束位置之后的第一个位置，不包含在范围内。format_scope 的各段合起来覆盖整个格式章节。每个节点必须填写 source：start 为该条目标题所在位置；end 为同一段内下一个同级条目的起始位置，最后一个条目取父节点或该段的 end。每个一级目录必须完整位于 format_scope 的某一段内，一级目录按 format_scope 的段落顺序排列；子节点必须与父节点位于同一份文件且范围位于父节点内，同级节点按位置递增且不重叠。${sourceInstruction}
7. 原文中有投标文件目录或组成清单时，用它核对条目是否齐全、顺序是否一致。

第三步（basis=${RESPONSE_REQUIREMENTS_BASIS}）：${fallbackInstruction}只生成平铺的一级目录，不生成 children，不填写 source 和 post_award。

字段要求：
1. 顶层必须是对象，包含 basis、format_scope 和 outline。所有节点 id 填 null，程序接收后分配唯一 ID；数组顺序表示目录顺序；number 由程序计算，不要用编号充当 ID。
2. 一级目录必须填写 attr，子目录不填写 attr。attr 从“通用”“商务/资信”“技术”“其他”“目录”“报价”“业绩”中选择。
3. 叶子节点填写 content_mode，父节点只包含 children，不包含 content_mode 或 content_mode_note。一级目录叶子：attr=商务/资信时使用 template-fill 或 rule-page；attr=业绩时必须使用 template-fill；attr=目录时必须使用 directory-generate；attr=报价时按内容判断（报价文件按格式填写的为 template-fill（金额由投标人填写），按招标清单逐项列出分项的报价表为 rule-page，没有可填写格式、需投标人另行编制的为 manual-fill）。子目录叶子按内容判断：按格式填写的文件使用 template-fill，规则和页码条目使用 rule-page，投标文件目录使用 directory-generate，报价文件按上述报价的方式判断。${DIRECTORY_GENERATE_RULE}${RULE_PAGE_RULE}需要投标人自行编写方案正文的条目使用 ai-generate（一级目录的 attr 选“技术”）。无法归类的使用 other，并在 content_mode_note 说明原因。
4. description 简要说明该文件的用途。
5. 结构示例（只示意字段，标题、层级和数量以原文为准）：{"basis":"${FORMAT_TEMPLATE_BASIS}","format_scope":[{"start":120,"end":480}],"outline":[{"id":null,"title":"原文条目标题","description":"用途说明","attr":"商务/资信","content_mode":"template-fill","source":{"start":121,"end":160}},{"id":null,"title":"原文条目标题","description":"用途说明","attr":"商务/资信","source":{"start":160,"end":240},"children":[{"id":null,"title":"原文子条目标题","description":"用途说明","content_mode":"template-fill","source":{"start":161,"end":200}},{"id":null,"title":"原文子条目标题","description":"用途说明","content_mode":"template-fill","source":{"start":200,"end":240}}]}]}
6. ${outputFile} 必须是纯 JSON，不包含 Markdown 代码块或解释文字。程序已预置 Schema，可用 json-validation 自查，只传 file_path；本阶段结束后程序会校验结构，并逐项核对 source 位置与原文标题，不通过会退回问题清单继续修复。`;
}
````

### A.4 OpenBidKit_Yibiao — 평가기준 기반 목차 생성(V2, 다단계 Agent)

#### A.4.1 1단계: 1차 목차(=技术评分大项) 프롬프트

`OpenBidKit_Yibiao/client/electron/services/outlineGenerationTaskV2.cjs:768-797`

````javascript
function createInitialPrompt(taskInstruction, { noTechnicalScoreMode = false } = {}) {
  const goal = noTechnicalScoreMode
    ? '我们的目标是为没有技术评分项的单独装订技术文件准备一级目录。'
    : '我们的目标是为单独装订的技术文件准备一级目录。一级目录必须直接对应技术评分大项。';
  const modeRequirements = noTechnicalScoreMode
    ? `6. 本模式只生成技术文件独立分册：一级目录必须是适合展开技术正文的专业主题，attr 必须为“技术”，content_mode 必须为 ai-generate。
7. 招标文件已确认没有可用的技术评分项。优先采用已有资料中的明确要求；资料没有给出目录结构时，根据项目类型和专业经验补充通用、合理的技术方案主题，但不得编造具体项目事实、参数、业绩或承诺。
8. 不得创建“技术方案”“项目管理方案”“监理大纲”“监理大纲（暗标）”“施工组织设计”“技术标”等外层总目录，也不得加入商务/资信、投标函、授权委托书等非技术章节。`
    : `6. 本模式只生成技术文件独立分册：只能保留适合展开技术正文的评分大项，attr 必须为“技术”，content_mode 必须为 ai-generate。
7. 每个一级目录直接对应一个技术评分大项，并保持评分大项的原顺序和正式表述；不得创建“技术方案”“项目管理方案”“监理大纲”“监理大纲（暗标）”“施工组织设计”“技术标”等外层总目录，也不得加入商务/资信、投标函、授权委托书等非技术章节。
8. 完整结构示例：{"outline":[{"id":null,"title":"评分大项一","description":"评分大项一的技术响应范围","attr":"技术","content_mode":"ai-generate"},{"id":null,"title":"评分大项二","description":"评分大项二的技术响应范围","attr":"技术","content_mode":"ai-generate"}]}。`;
  return `请只在当前工作目录内工作。
${createOutputFileRequirements('initial-outline')}

任务：
${goal}
${taskInstruction}

请生成一级目录 JSON，并将结果写入 ${OUTLINE_OUTPUT_FILE}。

字段要求：
1. 顶层必须是对象，唯一字段 outline 是一级目录数组；此阶段暂时不要生成 children。
2. 所有新节点 id 填 null，程序接收后分配唯一 ID。数组顺序表示目录顺序；number 由程序计算，不要用编号充当 ID。
3. title 必须是可直接用于投标文件目录的正式标题，不得包含“附件1”“附件一”“第一章”等编号或前缀。
4. description 是目录说明。
5. attr 必须从“通用”“商务/资信”“技术”“其他”“目录”“报价”“业绩”中选择。
${modeRequirements}
9. ${OUTLINE_OUTPUT_FILE} 必须是纯 JSON，不包含 Markdown 代码块或解释文字。
10. 程序已为 ${OUTLINE_OUTPUT_FILE} 预置 Schema，可用 json-validation 自查，只传 file_path；本阶段结束后程序统一校验，不通过会退回问题清单继续修复。`;
}
````

#### A.4.2 리프 배분·评分项 구조화(score planning) 프롬프트

`OpenBidKit_Yibiao/client/electron/services/outlineGenerationTaskV2.cjs:823-863`

````javascript
function createLeafAllocationPrompt() {
  return `请继续使用当前 Pi Session 已读取的技术评分信息、知识库、原方案和目录规划，为多个技术挂载节点分配“AI生成”叶子数量。
${createOutputFileRequirements('leaf_allocation')}

要求：
1. 阅读 ${OUTLINE_OUTPUT_FILE}、${TECHNICAL_SCORE_GROUPS_FILE}、${SCORE_DIRECTORY_PLAN_FILE} 和 ${LEAF_ALLOCATION_CONTEXT_FILE}。
2. 综合各挂载节点负责的评分项数量、评分细项数量、内容复杂度以及已读取的参考资料，合理分配 allocatable_ai_leaf_count。
3. allocations 必须恰好覆盖 context 中 technical_branches 的全部 node_id，每个 node_id 只出现一次。每个挂载节点至少分配 1 个，优先分配 2 个以上；分配 1 个表示该分支只保留一个“AI生成”叶子。node_id 是不会因目录重新编号而变化的内部稳定标识。
4. 所有 leaf_count 之和必须等于 allocatable_ai_leaf_count。
5. 将结果写入 ${LEAF_ALLOCATION_FILE}，保留 context 中的 mode、target_ai_leaf_count、fixed_ai_leaf_count 和 allocatable_ai_leaf_count。
6. 不要修改 ${OUTLINE_OUTPUT_FILE}、${TECHNICAL_SCORE_GROUPS_FILE} 或 ${SCORE_DIRECTORY_PLAN_FILE}。
7. 输出格式为 {"mode":"allocated","target_ai_leaf_count":20,"fixed_ai_leaf_count":1,"allocatable_ai_leaf_count":19,"allocations":[{"node_id":"从当前目录复制挂载节点ID","leaf_count":10},{"node_id":"另一挂载节点ID","leaf_count":9}]}。
8. 程序已为 ${LEAF_ALLOCATION_FILE} 预置 Schema，可用 json-validation 自查，只传 file_path；本阶段结束后程序统一校验，不通过会退回问题清单继续修复。`;
}



function createScorePlanningPrompt({ standaloneTechnical = false } = {}) {
  const placementInstruction = standaloneTechnical
    ? `4. 当前采用“技术文件独立成册”：${OUTLINE_OUTPUT_FILE} 中每个一级根节点本身就应对应一个技术评分大项，也就是技术方案的挂载节点。每个根节点建立一个 branch，score_item_level 固定为 1，mappings 只填写与该根标题对应的评分大项，target_title 必须与 node_title 完全一致；不得再创建“技术方案”“项目管理方案”“监理大纲”“监理大纲（暗标）”“施工组织设计”“技术标”等外层分支。
5. 一级根节点与评分大项默认严格一一对应；发现缺失、重复、合并或顺序不一致时，必须作为一级目录调整向用户说明并取得批准。detail_points 只用于后续生成根节点以下的目录。`
    : `4. 判断技术方案挂载在哪些已确认的叶子节点上（可能是一级目录，也可能是子目录），以及每个分支内评分项对应节点应统一处于哪个层级：挂载节点本身为第 1 层，score_item_level=1 表示挂载节点本身就是评分项节点，2 表示评分项节点是挂载节点的直接下级。不同分支可以使用不同层级。优先选择 content_mode=ai-generate 的叶子；template-fill、rule-page、directory-generate、manual-fill 和 other 是特殊处理叶子，不得作为技术方案分支展开，除非先向用户说明并取得调整批准。
5. 默认每个评分项对应一个独立同层级节点，节点标题与评分大项基本一一对应；detail_points 用于后续生成更下级目录。`;
  const planExample = standaloneTechnical
    ? `{"branches":[{"node_id":"从当前目录复制挂载节点ID","node_title":"评分大项一","score_item_level":1,"mappings":[{"requirement_id":"R1","target_title":"评分大项一"}]}],"extra_titles":[],"allow_root_changes":false}`
    : `{"branches":[{"node_id":"从当前目录复制挂载节点ID","node_title":"挂载节点标题","score_item_level":2,"mappings":[{"requirement_id":"R1","target_title":"评分大项目录标题","additional_titles":["经批准拆分出的同级标题"],"adjustment_note":"用户批准的调整说明"}]}],"extra_titles":[{"node_id":"从当前目录复制挂载节点ID","title":"经批准增加的同层级标题","reason":"增加原因"}],"allow_root_changes":false}`;
  return `用户已经确认最终保留的目录，${OUTLINE_OUTPUT_FILE} 已由程序重新整理并编号。工作区也已加入技术评分信息和用户选择的参考资料。
${createOutputFileRequirements('score-planning')}

请完成技术评分项结构化和目录规划：
1. 阅读 ${OUTLINE_OUTPUT_FILE}、技术评分信息.md，以及存在的原方案.md 和参考知识库目录。
2. 程序已确认本任务存在技术评分项。只从技术评分信息.md 的“技术评分项”中提取适合在技术方案中一一响应、展开编写的评分大项。“技术评分要求”只能作为评分标准、扣分规则和编写约束，不得提取为评分项。
3. 将评分大项写入 ${TECHNICAL_SCORE_GROUPS_FILE}，完整结构为 {"groups":[{"requirement_id":"R1","title":"评分大项","description":"关注内容","detail_points":["关键评分细项"]}]}。根对象只能包含 groups；保持原顺序、专业术语和关键评分细项，requirement_id 使用连续的 R1、R2 格式。
${placementInstruction}
6. 只有以下偏离需要用户批准：合并或拆分评分项、遗漏评分项对应节点、增加评分项中不存在的同层级大项、改变分支评分项目标层级，以及新增、删除、合并或调整用户已确认的目录。普通标题规范化和评分项下级目录扩展不需要询问。
7. 存在至少一个有效评分项时，无论是否存在偏离，都必须调用一次 ask-user 让用户确认。没有偏离时，question 只说明你分析得出的技术方案所在目录和评分项所在层级，最多使用两句话且不要使用列表；存在偏离时，只补充实际需要用户批准的偏离及影响，存在多个实际确认事项时才使用简单 Markdown 分行列出。question、选项名称和选项说明不得复述、概括或改写本任务 Prompt 中的要求，只呈现你分析后确实需要用户确认的结论或不确定事项。第一项给出推荐方案；另提供一个名为“调整目录安排”等明确业务名称的选项并设置 custom=true，让用户说明希望调整的位置或层级，其他选项均设置 custom=false。
8. 根据用户回答写入 ${SCORE_DIRECTORY_PLAN_FILE}。完整字段层级示例：${planExample}。branches 中 node_id 必须复制当前 ${OUTLINE_OUTPUT_FILE} 中对应挂载节点（已确认的叶子节点）的 id，node_title 填其标题；统一填写 score_item_level，并让每个 requirement_id 在 mappings 中恰好出现一次。后续重排或改名目录时，node_id 保持不变；不得填写显示编号或自行编造 ID。经用户批准新增一级目录时，该分支 node_id 填 null，node_title 与 ${OUTLINE_OUTPUT_FILE} 中新增目录的标题完全一致，程序在本阶段结束后分配 ID 并回填。默认一一对应；经用户批准合并时，多个 mapping 可以使用相同 target_title；经用户批准拆分时才填写 mapping.additional_titles；合并或拆分时才填写 adjustment_note。extra_titles 必须位于根对象，经批准增加同层级大项时才写入条目，否则使用空数组。
9. 默认锁定已确认目录，allow_root_changes=false；只有用户明确批准一级目录调整时才设为 true。用户批准新增一级目录时，须在本阶段把新增目录写入 ${OUTLINE_OUTPUT_FILE}。
10. 程序已为 ${TECHNICAL_SCORE_GROUPS_FILE} 和 ${SCORE_DIRECTORY_PLAN_FILE} 预置 Schema。可用 json-validation 自查，只传 file_path；本阶段结束后程序统一校验两份文件及其与已确认目录的对应关系，不通过会退回问题清单继续修复。如果现有材料无法在不编造评分项的情况下通过校验，调用 report-failure。
11. 此阶段对 ${OUTLINE_OUTPUT_FILE} 只允许插入经用户批准新增的一级目录：id 填 null，attr 为“技术”，content_mode 为 ai-generate，不包含 children，标题不得与其他一级目录重复；已确认目录（含子目录）的 id、title、description、attr、content_mode、rule_basis、层级和相对顺序保持不变。删除、合并、改名、排序等其他已批准的一级目录调整留到生成完整目录时执行。不要删除、清空或重命名任何任务文件。`;
}
````

#### A.4.3 하위 목차 생성 프롬프트

`OpenBidKit_Yibiao/client/electron/services/outlineGenerationTaskV2.cjs:865-906`

````javascript
function createChildrenPrompt({ hasOriginalPlan, originalOnly, targetLeafCount, allowRootChanges, standaloneTechnical }) {
  const branchInstruction = !hasOriginalPlan
    ? '没有原方案时，以技术评分信息.md 为主要依据生成目录。'
    : originalOnly
      ? '已选择仅使用原方案目录：以原方案.md 为主建立规划层级及以下目录，再用技术评分信息.md 补充原方案语义上确实缺失的技术要求，意思相近的内容不要重复添加。'
      : '已提供原方案且允许 AI 补充：以技术评分信息.md 为主，在评分项目录规划指定的层级覆盖关键大项，原方案.md 用于辅助生成更下级目录。';
  const leafInstruction = targetLeafCount === null
    ? '本次未设置总字数目标，请根据材料复杂度自主确定合理的“AI生成”叶子节点数量。'
    : `严格参考 ${LEAF_ALLOCATION_FILE} 中的分配，使最终完整目录合计约有 ${targetLeafCount} 个 content_mode=ai-generate 的叶子节点。`;
  const rootInstruction = allowRootChanges
    ? `用户已批准 ${SCORE_DIRECTORY_PLAN_FILE} 中记录的一级目录调整，只能按该规划进行必要修改并重新编号。上一阶段新增的一级目录已写入当前目录并分配 id，保留其 id，不要重复新增。`
    : '用户已确认的目录（含子目录）的数量、顺序、层级、id、title、description 和一级目录的 attr 必须保持不变；未扩展为父节点的已确认叶子还必须保留其 content_mode 和 rule_basis。';
  const mappingInstruction = standaloneTechnical
    ? '每个 branch 的 score_item_level=1，现有一级根节点本身就是评分项映射节点。不得在根节点下面再次生成同名评分项；只根据 detail_points、招标要求和专业逻辑生成其二级及以下目录。'
    : '每个 branch 的 mappings 必须在该分支的 score_item_level 层级生成对应节点（挂载节点本身为第 1 层）。';
  const standaloneLeafInstruction = standaloneTechnical
    ? 'leaf_count=1 表示保留对应一级目录本身作为叶子，不得为其生成 children；leaf_count>=2 时才向下展开。'
    : '';
  const outlineExample = standaloneTechnical
    ? `{"outline":[{"id":null,"title":"评分大项一","description":"评分大项说明","attr":"技术","children":[{"id":null,"title":"响应内容一","description":"具体响应内容","content_mode":"ai-generate"},{"id":null,"title":"响应内容二","description":"具体响应内容","content_mode":"ai-generate"}]}]}`
    : `{"outline":[{"id":"已确认节点ID","title":"已确认的模板填写目录","description":"目录说明","attr":"商务/资信","content_mode":"template-fill"},{"id":"已确认节点ID","title":"已确认的挂载节点","description":"挂载节点说明","attr":"技术","children":[{"id":null,"title":"评分大项","description":"评分大项说明","children":[{"id":null,"title":"具体方案一","description":"具体方案说明","content_mode":"ai-generate"},{"id":null,"title":"具体方案二","description":"具体方案说明","content_mode":"ai-generate"}]},{"id":null,"title":"另一评分大项","description":"评分大项说明","content_mode":"ai-generate"}]}]}`;
  return `请继续使用当前上下文，为 ${OUTLINE_OUTPUT_FILE} 生成完整目录。生成方式和处理顺序由你自主决定，但必须严格遵循评分项目录规划。
${createOutputFileRequirements('children_generation')}

要求：
1. ${branchInstruction}
2. 以 ${TECHNICAL_SCORE_GROUPS_FILE} 为技术评分项权威清单，以 ${SCORE_DIRECTORY_PLAN_FILE} 为评分项与目录位置的权威规划。
3. ${mappingInstruction} 规划的 node_id 对应挂载节点 id，节点本身不增加 node_id 字段；已有节点 id 不得随排序、改名或层级变化而改变。默认每个评分项形成一个独立节点；多个 mapping 使用相同 target_title 表示用户已批准合并，additional_titles 表示用户已批准将该评分项拆成多个同级节点。
4. mappings 中的 target_title 是评分项对应节点标题，必须基本保持评分大项的专业表述；detail_points 主要用于生成其下级目录。
5. extra_titles 是用户已批准增加的同层级大项；除此之外不得自行增加技术评分项中不存在的同层级标题。
6. “技术评分要求”只能作为评分标准、扣分口径、判定规则和目录说明约束，不能生成独立评分项节点。
7. ${rootInstruction}
8. 不是挂载节点的已确认目录保持原样，不得增加子目录。
9. 如果存在参考知识库或原方案，只能用于完善评分项对应节点的下级结构，不得改变评分项映射或引入未经批准的同层级大项。
10. ${leafInstruction}${LEAF_ALLOCATION_FILE} 中 allocations 使用 node_id 指向技术分支挂载节点的稳定 ID。${standaloneLeafInstruction}评分项完整对应和目录质量优先于数量目标。
11. 每个最终叶子节点必须填写 content_mode：技术方案正文为 ai-generate；商务/资信和业绩材料为 template-fill；规则和页码条目为 rule-page；投标文件目录为 directory-generate；报价文件按格式填写的为 template-fill（金额由投标人填写），按招标清单逐项列出分项的报价表为 rule-page，没有可填写格式、需投标人另行编制的为 manual-fill；其他特殊内容为 other，并用 content_mode_note 说明。${DIRECTORY_GENERATE_RULE}${RULE_PAGE_RULE}父节点不得包含 content_mode 或 content_mode_note。
12. AI 扩展的目录尽量避免只有一个子节点的冗余层级。
13. 目录层级可变，但最多六级；一级目录包含 attr，子目录不包含 attr。已有节点必须原样保留 id，新节点 id 填 null；数组顺序决定排序，number 由程序计算，不得把编号填入 id。
14. title 只写纯标题，不包含章节编号或 Markdown 标记。
15. ${OUTLINE_OUTPUT_FILE} 的完整结构示例：${outlineExample}。示例中的 null 仅表示新节点；已有节点必须从当前目录复制原 id 和 number，不能照抄示例。实际层级与标题按任务材料生成。
16. 程序已为 ${OUTLINE_OUTPUT_FILE} 预置 Schema。可使用 write 覆盖写回或 edit 修改该文件，内容较多时可分多次写入：首次用 write，之后用 edit 补充。可用 json-validation 自查，只传 file_path；本阶段结束后程序统一校验，不通过会退回问题清单继续修复。`;
}
````

#### A.4.4 최종 목차 심사 프롬프트

`OpenBidKit_Yibiao/client/electron/services/outlineGenerationTaskV2.cjs:961-994`

````javascript
function createOutlineReviewPrompt({ targetLeafCount, actualLeafCount, allowRootChanges, inputFiles }) {
  const leafCountReview = targetLeafCount === null
    ? ''
    : `\n- “AI生成”叶子数量：程序计算目标为 ${targetLeafCount} 个，当前为 ${actualLeafCount} 个，可接受范围为 ${Math.max(1, targetLeafCount - 2)} 至 ${targetLeafCount + 2} 个。只统计 content_mode=ai-generate 的最终叶子节点；修复后仍须保持在此范围内。`;
  const rootRequirement = allowRootChanges
    ? `一级目录只能保持用户已批准的 ${SCORE_DIRECTORY_PLAN_FILE} 规划，不得提出规划之外的新调整。`
    : '用户已确认的目录（含子目录）的数量、顺序、层级、标题、描述和一级目录属性不得修改，只能调整技术挂载节点下面的目录。';
  return `请对当前完整技术方案目录执行最终审核，并在用户确认后完成必要修复。
${createOutputFileRequirements('outline_review')}

以下已提供 ${OUTLINE_REVIEW_CONTEXT_FILE}、${OUTLINE_OUTPUT_FILE}、技术评分信息.md 和 ${SCORE_DIRECTORY_PLAN_FILE} 在本阶段开始时的最新完整内容。后续修改文件后，以修改后的内容为准。${OUTLINE_REVIEW_CONTEXT_FILE} 是宿主程序计算的确定性审核结果，叶子数量、内容模式数量、最大层级、父节点数量和评分节点机械映射均直接采用其中结果；你只负责评分语义覆盖、近义重复和专业合理性审核。优先使用本次已提供的最新材料和程序计算结果，通常无需重复读取或重新统计。需要确认具体节点、补足上下文或排查结果异常时，可使用 grep、read 或 bash 定位相关部分；已有结果足以判断时直接继续审核。

审核维度：${leafCountReview}
- 评分覆盖：直接以技术评分信息.md 为原始依据，逐项检查其中适合技术方案响应的评分大项是否被目录准确覆盖；结构化评分项和目录规划用于核对已确认的映射，但不能掩盖原始评分信息中的遗漏。
- 重复目录：检查全部子目录中是否存在重复、近义、含义重叠或仅换一种说法的节点；不同专业分支下确有独立含义的同名标题不应机械判重。
- 专业合理性：评估目录层级、颗粒度、逻辑顺序、标题表达、节点归属以及内容处理模式是否适合正式技术投标文件。

审核与修复流程：
1. 必须先完整审核并形成问题清单，不得边审核边修改。
2. 如果没有问题，不要修改 ${OUTLINE_OUTPUT_FILE}；写入 ${OUTLINE_REVIEW_FILE}，status=passed、issues=[]、user_feedback=""，summary 说明通过原因。
3. 如果发现问题，先为每个问题记录 category、problem、推荐 repair 和 confirmation_required，不得提前修改目录。
4. 只有以下问题可设 confirmation_required=false：标题或说明的专业化优化；不涉及评分项映射节点、目标层级和一级目录的明显重复或近义子目录合并。评分覆盖缺失、叶子数量超出合理范围、评分项目标层级调整、一级目录调整、增加或拆分目录、跨分支移动以及明显结构重排均必须设为 true。
5. 如果全部问题都不需要确认，可以直接执行文案优化或轻微去重，不得调用 ask-user；完成后设置 status=simple_fix、user_feedback=""。静默修复不得改变评分项映射、评分项目标层级和一级目录，且不得使 AI 生成叶子数量超出程序给出的合理范围。
6. 只要存在一个 confirmation_required=true 的问题，本轮所有问题都不得提前修改。集中调用一次 ask-user，question 使用多行文本完整列出问题及推荐修复方案；提供 2 至 5 个互斥选项，第一项是推荐修复方案，并提供保留当前目录的选项；另提供一个名为“调整修复方案”等明确业务名称的选项并设置 custom=true，让用户说明具体修改要求，其他选项均设置 custom=false。custom=true 的选项最多只能有一个。
7. 根据 ask-user 返回的 answer 执行最终处理：用户要求全部或部分修改时更新 ${OUTLINE_OUTPUT_FILE} 并设置 status=user_feedback；用户明确拒绝修改或要求保留现状时不得修改目录并设置 status=user_refuse。将 answer 原文完整写入 user_feedback，修改完成后不得再次询问用户。
8. ${rootRequirement}
9. 修复必须继续遵守 ${SCORE_DIRECTORY_PLAN_FILE} 中用户确认的评分项映射、目标层级和一级目录调整边界。补回遗漏映射、合并重复目录或优化层级时，不得引入未经用户批准的评分大项规划变更。
10. 技术挂载节点的 id 必须与 ${SCORE_DIRECTORY_PLAN_FILE} 中对应的 node_id 一致；调整目录顺序或编号时不得修改节点 id。结构事实以 ${OUTLINE_REVIEW_CONTEXT_FILE} 为准；如果其中确定性检查不通过，直接依据列出的节点和缺失项形成问题并修复，不要重新统计。任何语义修复仍必须保证叶子保留合法 content_mode、父节点不包含 content_mode 或 content_mode_note 且目录最多六级。
11. 最终将完整问题清单和处理结果写入 ${OUTLINE_REVIEW_FILE}。无问题时完整格式为 {"status":"passed","issues":[],"user_feedback":"","summary":"审核通过原因"}；有问题时完整格式为 {"status":"user_feedback","issues":[{"category":"score-coverage","problem":"问题说明","repair":"修复方案","confirmation_required":true}],"user_feedback":"用户回答原文","summary":"处理结果"}。category 只能是 leaf-count、score-coverage、duplicate-directory、professional-structure；status 按本流程选择 passed、simple_fix、user_feedback 或 user_refuse。
12. 程序已为 ${OUTLINE_OUTPUT_FILE} 和 ${OUTLINE_REVIEW_FILE} 预置 Schema，可用 json-validation 自查，只传 file_path；本阶段结束后程序统一校验两份文件，不通过会退回问题清单继续修复。未修改 ${OUTLINE_OUTPUT_FILE} 时不要为了校验而重写目录。

本阶段输入材料：
${inputFiles.map((file) => `【文件开始：${file.path}】\n${file.content}\n【文件结束：${file.path}】`).join('\n\n')}`;
}
````

### A.5 OpenBidKit_Yibiao — 전역 사실(SSOT)과 본문 생성

#### A.5.1 사실 결손 처리 3모드(omit / placeholder / 기본값 fabricate)

`OpenBidKit_Yibiao/client/electron/services/globalFactsTaskV2.cjs:88-97`

````javascript

function buildMissingValueRule(mode) {
  if (mode === 'omit') {
    return '用户资料已经给出明确事实时，使用资料中的事实值。用户资料没有给出具体值时，该项仍须保留，写成不涉及具体时间、地点、人员、业绩、证书、规格型号、工艺步骤、数量指标的正确笼统承诺，表明本方案按招标要求执行该项，但不展开具体做法。严禁省略该项，也严禁杜撰具体值。必须包含工期、运维期或交货时间中的至少一个相关变量；没有具体值时同样使用笼统承诺，不要编造日期或周期。笼统但正确的承诺口径不是空泛内容，定稿时不得因不够具体而删除。';
  }
  if (mode === 'placeholder') {
    return '用户资料已经给出明确事实时，使用资料中的事实值。用户资料没有给出具体值时，该项仍须保留，值必须逐字写成【待填写】，不要改写成“待定”“TBD”或其他说法，也不要编造具体值。严禁省略该项。必须包含工期、运维期或交货时间中的至少一个相关变量；没有具体值时使用【待填写】。【待填写】不是空泛内容，定稿时不得因不够具体而删除。';
  }
  return '用户资料已经给出明确事实时，使用资料中的事实值。用户资料没有给出具体值，但该信息对全文一致性重要时，根据项目语境补足一套合理、稳定、不冲突的具体事实值。必须包含工期、运维期或交货时间中的至少一个相关变量；分段或材料不足时，若项目概述或招标解析结果中已有明确内容应写入，否则按项目语境补足具体周期。';
}
````

#### A.5.2 전역 사실 작업 원칙과 프롬프트

`OpenBidKit_Yibiao/client/electron/services/globalFactsTaskV2.cjs:219-292`

````javascript
function buildWorkPrinciples({ hasKnowledge, hasOriginalPlan, credentialSections }) {
  const supplementNames = [
    hasKnowledge ? '知识库' : '',
    hasOriginalPlan ? '原方案' : '',
  ].filter(Boolean);
  const principles = [
    '1. 先根据招标文件、项目概述、招标解析结果和技术方案目录，确定全部全局事实大项（id、title）。凡这些材料表明后续正文需要统一口径的事项，都必须建项；招标文件有多份时要综合全部招标原文，不要因为某一份没写就漏项。',
  ];
  let fillRule = '2. 再为每个大项填写 content。优先使用招标文件和招标解析结果中的明确值';
  if (supplementNames.length) {
    fillRule += `；然后再用${supplementNames.join('、')}补充这些已有大项的具体内容`;
  }
  principles.push(`${fillRule}。`);

  let next = 3;
  if (supplementNames.length) {
    principles.push(`${next}. ${supplementNames.join('和')}只用于补充已有大项的 content，不要靠它们新增大项。`);
    next += 1;
  }
  principles.push(`${next}. 全局事实不是招标要求摘录、评分规则或待办清单，而是正文要统一采用的方案事实、响应设定、承诺口径或执行安排。材料给出的是要求或约束时，不要原样摘录要求句，应转写为本方案统一口径。`);
  next += 1;
  principles.push(`${next}. 每条 content 只写简体中文短 bullet，回答“后续正文遇到这个事项时统一写什么”。不写分析过程、来源说明、风险提示、正文草稿、商务报价或资格材料。${credentialSections.length ? `按下文规则从 ${CREDENTIAL_FACTS_FILE} 写入的投标人信息和项目人员不属于资格材料。` : ''}`);
  next += 1;
  principles.push(`${next}. 必须包含工期、运维期或交货时间中的至少一个相关变量；缺具体值时按本任务给定的写法填写，不要省略该项。`);
  next += 1;
  principles.push(`${next}. 材料较长时，先结合章节结构分段检查，再用 grep 定位具体事实和关联条款。多份招标材料分别跟踪已处理范围，逐步整理事实大项；补充具体值时按主题读取相关材料。可用 node、jq 辅助合并条目和定位重复项，事实含义及冲突由你判断。`);
  if (hasKnowledge) {
    next += 1;
    principles.push(`${next}. 用参考知识库补充已有大项的具体内容，不要仅因知识库出现新话题就新增大项。`);
  }
  if (hasOriginalPlan) {
    next += 1;
    principles.push(`${next}. 用原方案补充已有大项的具体内容；原方案与招标明确事实冲突时，原方案已落地的安排优先替换对应 bullet。不要仅因原方案出现新话题就新增大项。`);
  }
  // 资信库规则只按实际存在的类别给出，不让 Agent 判断有没有、用不用。
  if (credentialSections.includes('基本信息')) {
    next += 1;
    principles.push(`${next}. 投标人名称等企业事实取 ${CREDENTIAL_FACTS_FILE} 基本信息中的原值，不改写。`);
  }
  if (credentialSections.includes('员工')) {
    next += 1;
    principles.push(`${next}. 项目经理、技术负责人等项目角色，按招标文件对岗位的资格要求从 ${CREDENTIAL_FACTS_FILE} 的员工中选人，写真实姓名和职称；没有符合要求的员工时，按“缺具体值时的写法”处理。`);
  }
  const recordSections = ['资质', '业绩'].filter(section => credentialSections.includes(section));
  if (recordSections.length) {
    next += 1;
    principles.push(`${next}. 正文需要统一引用的${recordSections.join('或')}，只用 ${CREDENTIAL_FACTS_FILE} 中的真实记录。`);
  }
  return principles.join('\n');
}

function createGlobalFactsPrompt({ fileCatalog, hasKnowledge, hasOriginalPlan, credentialSections, globalFactsMode }) {
  return `请只在当前工作目录内工作。已有材料足以判断时自主执行，不要调用 ask-user。

任务：整理后续技术方案正文必须统一采用的全局事实变量，写入 ${GLOBAL_FACTS_OUTPUT_FILE}。

工作流程由你自主安排，但必须遵守下面的材料用途和先后原则。

材料用途：
${fileCatalog}

工作原则：
${buildWorkPrinciples({ hasKnowledge, hasOriginalPlan, credentialSections })}

缺具体值时的写法：
${buildMissingValueRule(globalFactsMode)}

输出：
1. 最终结果写入 ${GLOBAL_FACTS_OUTPUT_FILE}，必须是纯 JSON，不要 Markdown 代码块。
2. 根对象只有 groups；每项包含 id、title、content。
3. 程序已为该文件预置 Schema，可用 json-validation 自查，只传 file_path。确认全部工作完成时，在最后一次成功的写入或修改中传 task_complete=true；结束后程序统一校验，不通过会退回问题清单继续修复。

格式示意：
${buildJsonExample(globalFactsMode)}`;
````

#### A.5.3 본문 글자 수·사실 결손·작성 규칙

`OpenBidKit_Yibiao/client/electron/services/contentGenerationAgent.cjs:70-88`

````javascript
// 每个写作模型只承担本节目标；全文字数由主会话统一统计。
function wordInstructions(control, checkTotalWords) {
  return `全文最少字数：${control.minimumWords || '不限制'}；全文最多字数：${control.maximumWords || '不限制'}。\n每节按 content_plan.target_words 指定的目标字数安排篇幅，0 表示不设目标；尽量接近目标，不为凑字数重复表达或删除必要信息。目标已经在编排阶段分配，不再自行分摊全文目标，也不让单个小节承担全文目标。${checkTotalWords ? '本轮全部目标生成完成后，由主 Agent 统一检查总字数。' : '本次仅统计目标小节字数，不承担全文字数达标。'}字数统计不含 HTML 标签及配图提示词。`;
}

// 将当前事实模式翻译为统一中文要求，主会话与并发任务共用输入快照。
function globalFactsInstructions(mode) {
  const requirement = mode === 'placeholder'
    ? '事实缺失处理方式：保留正文中需要说明的事项；核对相关参考材料后仍无法确定的具体事实，以“【待填写】”标记。已有占位符保持原样，不自行补入具体值。'
    : mode === 'omit'
      ? '事实缺失处理方式：保留必要事项，并采用不依赖未知具体值的概括性表述。未经参考材料提供，不得补入具体人员、时间、地点、业绩、证书或规格型号。'
      : '事实缺失处理方式：核对相关参考材料后仍缺少必要信息时，允许结合项目背景补充设定。新增设定应符合项目语境，并在各小节中保持一致。';
  return `${requirement} 补充事实前，应先核对相关参考材料和全局事实设定。只有未找到明确依据时，才适用当前事实缺失处理方式；材料与全局事实冲突时，以全局事实为准。允许补充设定只适用于缺失信息，不得覆盖或改变全局事实。禁止生成没有实际依据的引用。`;
}

// 正文写作共用规则，事实要求由编排决策中的同一段中文说明提供。
function writingInstructions(hasKnowledgeBase) {
  return `根据项目背景、章节描述和编排重点编写投标正文。明确说明与本节相关的实施措施、执行条件、责任分工或交付成果。内容应准确、具体、可执行，使用正式、简洁的书面语言，避免宣传性表述、缺少具体内容的概括和重复表达。\n使用参考资料时，应将适用内容整理为当前项目的方案表述，不在正文中提及${hasKnowledgeBase ? '知识库、' : ''}历史文档或素材来源。全局事实设定用于统一项目事实口径，不是本节必须逐项覆盖的写作清单。本节内容范围以标题、章节描述和编排重点为准。仅在说明本节内容确有需要时使用相关事实，不为覆盖全局事实增加无关段落，也不在各节重复罗列项目概况、人员、设备或制度。写作内容和全局事实不冲突即可，不要求完全引用全局事实。全局事实未明确的信息，按本次事实缺失处理要求执行。\n只输出受限 HTML 正文，不输出 Markdown、代码围栏、外层章节标题或解释。除 img 等空元素外，每个元素都写出对应的结束标签；每个 figure 以 </figure> 结束并直接包含一个 img，figure 不放在段落、列表项或加粗、链接等行内元素中。篇幅较长时也要先保证 HTML 结构完整。内部层次用普通段落、列表或无编号加粗引导语；有序列表仅用于步骤、流程和时间顺序。\n正文禁止使用 LaTeX 语法，包括 $...$、$$...$$、\\(...\\)、\\[...\\] 及 \\frac、\\text、\\circ 等命令。公式、参数和单位使用普通文字、Unicode 数学符号及受限 HTML 的 <sup>、<sub> 表达，例如 22 ℃ ± 2 ℃、40%～65%、≥30 m<sup>3</sup>/(h·人)。参考材料中的 LaTeX 在写入正文时也须转换为上述表达，保持数值、单位和含义不变。`;
}
````

#### A.5.4 쪽 골격(skeleton) 기반 본문 생성 system/user 프롬프트

`OpenBidKit_Yibiao/client/src/shared/layoutBudget/skeletonPrompt.ts:89-180`

````javascript
export function buildSkeletonSystemPrompt() {
  return `你是投标文件正文撰写助手，只输出受限 HTML 正文流。

输出格式：
- 每个块前面单独一行 <!-- yibiao:block --> 注释，块与块之间空一行。
- 只允许这些标签：p、ol、ul、li、figure、img、figcaption、template、table、caption、thead、tbody、tr、th、td；
  行内只允许 strong、em、u、sup、sub、br。
- 不输出 style、class、CSS、宽高、颜色、对齐、分页信息，不输出 markdown 代码围栏。
- 每个块元素带一个 id 属性，用给定的块编号，例如 <p id="p1">。
- 不要输出任何标题（h1-h6）。本节标题由程序用目录里的小节标题直接拼出来，你只写正文。

配图块的写法：
<!-- yibiao:block -->
<figure id="fig1" data-yb-generation="生成方式" data-yb-size="画框">
  <template data-yb-role="prompt">这里写配图生成提示词，说清楚画什么、有哪些节点和关系</template>
  <img alt="图片内容的简短描述">
  <figcaption>图例文字</figcaption>
</figure>

data-yb-generation 三选一，按这张图真正该画什么来选，不要固定用同一种：
- mermaid：有明确先后或从属关系的流程图、层级图、职责关系图；
- htmlImage：组织架构、矩阵、看板、指标卡、架构拓扑这类需要排版的信息图；
- aiImage：施工现场、设备、环境、实施场景这类需要写实画面的效果图。
一节里有多张图时，尽量让它们用不同的生成方式，不要全用同一种。

data-yb-size 从块清单为该图列出的可选画框里挑一个，按内容的自然形状选：
自上而下的长流程用竖版，左右流向或并列对比用横版，闭环和矩阵用方形。

图文混排块（左图右文）的写法：
<!-- yibiao:block -->
<table id="mix1" data-yb-preset="imageText">
  <caption>这一块的小标题</caption>
  <tbody>
    <tr>
      <td><figure id="fig2" data-yb-generation="htmlImage" data-yb-size="tall">…同上…</figure></td>
      <td><p><strong>一句话要点</strong></p><p>结合左图展开的说明文字</p></td>
    </tr>
  </tbody>
</table>

并列图组块的写法（三列用 threeImages，四宫格用 fourImages，四宫格写两行两列）：
<!-- yibiao:block -->
<table id="grp1" data-yb-preset="threeImages">
  <caption>这一组图的总标题</caption>
  <tbody>
    <tr>
      <td><figure id="fig3" …>…</figure></td>
      <td><figure id="fig4" …>…</figure></td>
      <td><figure id="fig5" …>…</figure></td>
    </tr>
  </tbody>
</table>
一组图必须是同一主题下互相并列、可比较的几个侧面，不要凑数；
组里每张图都必须有自己的 figcaption，整组再有一个 caption 作为总标题。
图文混排块的左图不需要 figcaption。

数据表格块的写法（preset 用块清单指定的那个）：
<!-- yibiao:block -->
<table id="tbl1" data-yb-preset="headerRow">
  <caption>表题</caption>
  <thead><tr><th scope="col">列名</th>…</tr></thead>
  <tbody><tr><td>单元格</td>…</tr></tbody>
</table>
headerRow 只有表头行；headerColumn 只有首列表头，首列写成 <th scope="row">；
headerRowAndColumn 两者都有。表格用来归纳可对比的事实，每格控制在 20 字以内。

硬性要求：
- 一节正文可能分几批写。块清单永远给完整的那一份，但你每次只输出标了"本批要写"的块，
  其余的块一个都不要输出。本批之内块的数量、顺序、类型都不能改。
- 每个段落块的字数必须落在给定区间内，这是硬指标。中文按字符计。
- 配图块前后必须各有正文块，绝不允许两个配图块相邻。
- 只输出 HTML，不要任何解释、前言或结语。`;
}

export function buildSkeletonUserPrompt(plan: SkeletonPlan, context: SkeletonPromptContext) {
  const facts = context.globalFacts.trim();
  return `# 项目信息
项目名称：${context.projectName || '（未填写）'}
${context.projectOverview ? `项目概述：${context.projectOverview}` : ''}

# 本节位置
${context.sectionPath}
本节标题：${context.sectionTitle}
${context.sectionDescription ? `本节说明：${context.sectionDescription}` : ''}

${facts ? `# 本节须遵守的事实设定\n${facts}\n` : ''}
# 块清单（严格按此输出，标题不在其中，由程序补）
${describeSkeleton(plan.blocks, true)}

正文合计约 ${plan.plannedChars} 字。请按块清单逐块撰写专业、具体、可执行的投标正文，避免空话套话。`;
}

````

### A.6 OpenBidKit_Yibiao — 废标项·오탈자·논리 점검

#### A.6.1 3라운드(분석→점검→확정)·오탈자·논리 점검 프롬프트

`OpenBidKit_Yibiao/client/src/shared/prompts/rejectionPrompts.ts:13-217`

````javascript
function buildCommonRejectionCheckMessages(input: BuildRejectionCheckMessagesInput): ChatMessage[] {
  const messages: ChatMessage[] = [
    {
      role: 'user',
      content: `【废标项检查输入 v1｜检查项】
以下内容来自招标文件“无效投标”和“废标项”解析结果。后续任务必须优先基于这些检查口径，不要自行扩大到无法从电子投标文件判断的事项。

${input.invalidBidAndRejectionItems}`,
    },
  ];

  if (input.customCheckItems?.trim()) {
    messages.push({
      role: 'user',
      content: `【废标项检查输入 v1｜自定义检查项】
以下是用户补充的电子投标文件检查关注点。仅在能从电子投标文件正文、目录、附件文本或材料内容中判断时使用；如果涉及签字、盖章、密封、现场递交、纸质正副本等纸质或线下事项，必须忽略。

${input.customCheckItems.trim()}`,
    });
  }

  messages.push({
    role: 'user',
    content: `【废标项检查输入 v1｜投标文件原文】
以下是完整投标文件 Markdown 原文。后续检查只能引用这份电子投标文件中可见的内容作为证据。

重要限制：当前原文由文本解析得到，图片、扫描件、截图、附件页等非文本内容可能已被过滤或无法完整呈现。检查材料缺失时，不得要求必须看到图片内容、扫描件正文或附件正文；如果投标文件中已经出现某项材料的章节标题、目录项、附件标题、材料清单项、表格条目、页码线索、图片占位线索或其他可表明该材料已插入/已提交的结构性文本线索，应视为该材料至少存在提交线索。

${input.bidContent}`,
  });

  return messages;
}

export function buildRejectionCheckAnalysisMessages(input: BuildRejectionCheckMessagesInput): ChatMessage[] {
  return [
    ...buildCommonRejectionCheckMessages(input),
    {
      role: 'user',
      content: `【废标项检查任务 v1｜第一轮：分析】
请先分析检查范围，不要输出最终风险列表。

分析要求：
1. 梳理“无效投标”和“废标项”中哪些能通过电子投标文件内容判断。
2. 明确排除签字、盖章、密封、纸质正副本、现场递交、开标现场授权到场、纸质文件封装等纸质或线下事项。
3. 结合投标文件目录和正文结构，指出重点核查章节、附件、报价、资格材料、技术/商务响应位置。
4. 判断材料是否缺失时，先识别章节标题、目录项、附件标题、材料清单项、表格条目、页码线索、图片占位线索等结构性文本线索；只要存在这类线索，就不能因为图片或扫描件正文不可见而判定缺失。
5. 如果某项检查需要外部事实、现场行为或纸质原件才能判断，标记为“不纳入电子文件检查”。
6. 仅输出分析结论，使用简体中文。`,
    },
  ];
}

export function buildRejectionCheckInspectionMessages(input: BuildRejectionCheckMessagesInput, analysis: string): ChatMessage[] {
  return [
    ...buildCommonRejectionCheckMessages(input),
    {
      role: 'user',
      content: `【废标项检查任务 v1｜第一轮分析结果】
${analysis}`,
    },
    {
      role: 'user',
      content: `【废标项检查任务 v1｜第二轮：检查】
请基于第一轮分析逐项检查电子投标文件，输出初步风险列表。

检查要求：
1. 每条风险必须有投标文件中的明确证据；证据不足不要输出。
2. 不检查签字、盖章、密封、纸质正副本、现场递交、纸质原件等事项。
3. 重点关注实质性条款未响应、必要章节或附件缺失、资格材料明显缺失/过期、报价或关键承诺前后矛盾、技术/商务偏离未说明等电子正文可判断风险。
4. 判断“材料缺失”时，只有在目录、章节标题、附件标题、材料清单、正文、表格和其他结构性线索中均找不到对应材料痕迹，才可以输出疑似缺失；不得仅因图片内容、扫描件正文或附件正文不可见而输出缺失风险。
5. 如果投标文件中已有对应材料的结构性文本线索，应视为至少有提交线索，可提示人工复核内容完整性，但不要判定为缺失。
6. 区分风险类型：无效标使用 invalidBid，废标项使用 rejectionItem。
7. 暂不要求 JSON，可用结构化 Markdown 输出初步结果。`,
    },
  ];
}

export function buildRejectionCheckFinalMessages(input: BuildRejectionCheckMessagesInput, analysis: string, draftFindings: string): ChatMessage[] {
  return [
    ...buildCommonRejectionCheckMessages(input),
    {
      role: 'user',
      content: `【废标项检查任务 v1｜第一轮分析结果】
${analysis}`,
    },
    {
      role: 'user',
      content: `【废标项检查任务 v1｜第二轮初步检查结果】
${draftFindings}`,
    },
    {
      role: 'user',
      content: `【废标项检查任务 v1｜第三轮：补充与定稿】
请对第二轮结果去重、合并、补漏，并删除不符合要求的条目，最终只输出 JSON。

定稿规则：
1. 只保留能从电子投标文件原文判断且有明确证据的风险。
2. 删除签字、盖章、密封、纸质正副本、现场递交、纸质原件、开标现场行为等纸质或线下事项。
3. 删除只有猜测、没有投标文件证据、或仅凭常识无法确认的条目。
4. 删除仅因图片内容、扫描件正文或附件正文不可见而产生的材料缺失条目；如果投标文件中存在对应材料的章节标题、目录项、附件标题、材料清单项、表格条目、页码线索、图片占位线索或其他结构性文本线索，不得将该材料定稿为缺失。
5. 同一问题合并为一条，标题简短明确。
6. severity 只能是 high、medium、low；type 只能是 invalidBid 或 rejectionItem。
7. 如果没有符合条件的风险，返回 {"findings":[]}。

JSON 格式：
{
  "findings": [
    {
      "type": "invalidBid",
      "severity": "high",
      "title": "不超过 28 个中文字符的风险标题",
      "summary": "一句话概括风险",
      "requirement": "对应检查依据或招标要求，尽量引用原检查项",
      "bidEvidence": "投标文件中的明确证据、章节、原文摘录或缺失位置说明",
      "riskReason": "为什么该证据可能构成无效标或废标项风险",
      "suggestion": "建议用户如何处理或复核"
    }
  ]
}

仅输出 JSON，不要输出 Markdown、代码块或解释。`,
    },
  ];
}

export function buildTypoCheckMessages(input: BuildBidContentCheckMessagesInput): ChatMessage[] {
  return [
    {
      role: 'user',
      content: `【错别字检查输入 v1｜投标文件原文】
以下是完整投标文件 Markdown 原文。后续只能检查这份原文中真实存在的文字。

${input.bidContent}`,
    },
    {
      role: 'user',
      content: `【错别字检查任务 v1】
请检查投标文件中的错别字、明显别字、同音错字、形近错字和明显录入错误，并输出 JSON。

检查要求：
1. 只输出你高度确信的错别字，不输出风格建议、标点偏好、表达优化或术语争议。
2. 每条必须来自投标文件原文，wrongText 必须是原文中出现的原始错字或短词。
3. correctText 是建议改成的正确字词。
4. originalExcerpt 尽量摘录包含 wrongText 的原文短片段，便于程序校验；不要改写原文。
5. 如果没有明确错别字，返回 {"findings":[]}。

JSON 格式：
{
  "findings": [
    {
      "wrongText": "原文中的错别字或短词",
      "correctText": "建议正确字词",
      "originalExcerpt": "包含错别字的原文短片段",
      "reason": "为什么判断为错别字"
    }
  ]
}

仅输出 JSON，不要输出 Markdown、代码块或解释。`,
    },
  ];
}

export function buildLogicCheckMessages(input: BuildBidContentCheckMessagesInput): ChatMessage[] {
  return [
    {
      role: 'user',
      content: `【逻辑谬误检查输入 v1｜投标文件原文】
以下是完整投标文件 Markdown 原文。后续只能基于这份投标文件内容进行逻辑一致性检查。

${input.bidContent}`,
    },
    {
      role: 'user',
      content: `【逻辑谬误检查任务 v1】
请检查投标文件中的逻辑谬误和前后不一致问题，并输出 JSON。

检查范围：
1. 句子本身存在逻辑漏洞、因果不成立、条件互相矛盾或结论无法由前文推出。
2. 全文前后不一致，包括但不限于处理相同工作的人员名单、设备型号、工期、金额、数量、服务期限、项目名称、技术参数等应高度一致的内容前后不一致。

输出要求：
1. 只保留有明确文本依据的问题，避免泛泛而谈。
2. 问题可能涉及多处原文，originalText 可摘录关键原文，locationHint 写明大概位置、章节、表格或上下文线索。
3. title 必须简短明确，便于作为折叠列表标题。
4. 如果没有明确逻辑谬误，返回 {"findings":[]}。

JSON 格式：
{
  "findings": [
    {
      "title": "不超过 28 个中文字符的简短标题",
      "originalText": "关键原文摘录，可包含多处摘录",
      "locationHint": "大概位置、章节、表格或上下文线索",
      "fallacyReason": "谬误原因或前后不一致原因",
      "suggestion": "修改建议"
    }
  ]
}

仅输出 JSON，不要输出 Markdown、代码块或解释。`,
    },
  ];
}
````

#### A.6.2 장문 투찰 패키지용 롤링(patch) 점검·배치 확정·전역 병합 프롬프트

`OpenBidKit_Yibiao/client/electron/services/rejectionCheckTask.cjs:1021-1162`

````javascript
function buildRollingRejectionBaseMessages(input) {
  const messages = [
    {
      role: 'user',
      content: `【废标项滚动检查输入｜检查依据】
以下内容来自招标文件“无效投标”和“废标项”解析结果。必须优先基于这些检查口径，不要自行扩大到无法从电子投标文件判断的事项。

${input.invalidBidAndRejectionItems}`,
    },
  ];

  if (input.customCheckItems?.trim()) {
    messages.push({
      role: 'user',
      content: `【废标项滚动检查输入｜自定义检查项】
以下是用户补充的电子投标文件检查关注点。仅在能从电子投标文件正文、目录、附件文本或材料内容中判断时使用；如果涉及签字、盖章、密封、现场递交、纸质正副本等纸质或线下事项，必须忽略。

${input.customCheckItems.trim()}`,
    });
  }

  return messages;
}

function buildRollingRejectionSegmentMessages(input, segment, stateSummary) {
  const bidDocumentIdList = formatBidDocumentIdList(input.bidDocuments);
  return [
    ...buildRollingRejectionBaseMessages(input),
    {
      role: 'user',
      content: `【废标项滚动检查｜当前状态摘要】
你正在按顺序审阅同一个投标包。完整权威状态由程序维护，你只能基于当前片段返回增量 patch。
下面是前序片段累计状态的精简摘要；如需更新或排除 pendingRisks，只能引用摘要中已有的 id。

${JSON.stringify(stateSummary, null, 2)}`,
    },
    {
      role: 'user',
      content: `【废标项滚动检查｜当前投标包片段】
投标包片段：第 ${segment.segmentIndex}/${segment.totalSegments} 段
当前片段所属文件：${segment.documentLabel}
当前片段默认 bidDocumentId：${segment.documentId}

本投标包有效 bidDocumentId：
${bidDocumentIdList}

重要限制：当前内容只是整个投标包的一段，不是全部投标文件。不得因为当前段或当前文件没有出现某项材料、附件、承诺或响应，就确认该材料缺失；这类问题只能先放入 pendingRisks，后续片段或其他投标文件可能会补充或推翻。

${segment.content}`,
    },
    {
      role: 'user',
      content: `【废标项滚动检查任务】
请基于当前片段输出增量 patch，只输出 JSON。不要返回完整累计状态，程序会负责合并和保留历史状态。

Patch 要求：
1. evidenceAdds 只放当前片段新增的章节标题、目录项、附件标题、材料清单项、表格条目、页码线索、图片占位线索、承诺或响应线索。
2. pendingRiskAdds 只放当前片段发现、但需要后续片段或其他文件继续确认的问题。
3. pendingRiskUpdates 只能引用状态摘要中 pendingRisks 的 id，用于补充或修正该待确认项。
4. pendingRiskResolves 只能引用状态摘要中 pendingRisks 的 id；如果当前片段证明某个“缺失/未响应”不成立，就在这里给出排除原因。
5. confirmedRiskAdds 只放当前片段或累计摘要已经提供明确投标文件证据，且不依赖纸质、线下或外部事实的风险。
6. 不检查签字、盖章、密封、纸质正副本、现场递交、纸质原件等事项。
7. 每条风险、证据和事实必须保留 bidDocumentId，且只能使用上方有效 bidDocumentId；如果当前片段没有明确切换文件，默认使用 ${segment.documentId}。

JSON 格式：
{
  "evidenceAdds": [{"bidDocumentId":"有效 bidDocumentId","name":"材料或响应线索名称","evidence":"原文线索或摘要","locationHint":"章节/表格/位置线索","source":"对应检查项或说明"}],
  "pendingRiskAdds": [{"bidDocumentId":"有效 bidDocumentId","type":"invalidBid","severity":"medium","title":"待确认问题","summary":"摘要","requirement":"检查依据","bidEvidence":"当前证据或缺口","riskReason":"为什么需要继续确认","suggestion":"建议","statusReason":"仍需后续片段确认的原因"}],
  "pendingRiskUpdates": [{"id":"pendingRisks 中已有 id","bidEvidence":"补充证据或缺口","riskReason":"更新原因","statusReason":"当前仍需确认的原因"}],
  "pendingRiskResolves": [{"id":"pendingRisks 中已有 id","reason":"被当前片段或累计线索排除的原因","locationHint":"位置线索"}],
  "confirmedRiskAdds": [{"bidDocumentId":"有效 bidDocumentId","type":"invalidBid","severity":"high","title":"风险标题","summary":"摘要","requirement":"检查依据","bidEvidence":"明确投标文件证据","riskReason":"风险原因","suggestion":"建议"}]
}`,
    },
  ];
}

function buildRejectionFinalBatchMessages(input, candidates, stateSummary, batchIndex, totalBatches) {
  const bidDocumentIdList = formatBidDocumentIdList(input.bidDocuments);
  return [
    ...buildRollingRejectionBaseMessages(input),
    {
      role: 'user',
      content: `【废标项最终定稿｜状态摘要】
本投标包有效 bidDocumentId：
${bidDocumentIdList}

${JSON.stringify(stateSummary, null, 2)}`,
    },
    {
      role: 'user',
      content: `【废标项最终定稿｜候选批次 ${batchIndex}/${totalBatches}】
请只基于下面这一批候选输出最终废标项检查结果，只输出 JSON。

候选风险：
${JSON.stringify(candidates, null, 2)}

定稿规则：
1. 只保留能从电子投标文件原文或累计状态判断且有明确证据的风险。
2. candidateStatus 为 pending 且仍未形成完整证据闭环的问题不得输出为最终风险。
3. 如果某项“缺失/未响应”已经在 submittedEvidenceIndex 中出现章节、目录、附件标题、材料清单、表格条目、页码线索、图片占位线索或其他提交线索，不能定稿为缺失。
4. 删除签字、盖章、密封、纸质正副本、现场递交、纸质原件、开标现场行为等纸质或线下事项。
5. 同一问题合并为一条，bidDocumentId 必须来自上方有效 bidDocumentId。
6. 如果没有符合条件的风险，返回 {"findings":[]}。

JSON 格式：{"findings":[{"bidDocumentId":"有效 bidDocumentId","type":"invalidBid","severity":"high","title":"不超过 28 个中文字符的风险标题","summary":"一句话概括风险","requirement":"对应检查依据或招标要求","bidEvidence":"投标文件中的明确证据、章节、原文摘录或缺失位置说明","riskReason":"为什么该证据可能构成无效标或废标项风险","suggestion":"建议用户如何处理或复核"}]}`,
    },
  ];
}

function buildRejectionGlobalMergeMessages(input, findings, finalSummary) {
  const bidDocumentIdList = formatBidDocumentIdList(input.bidDocuments);
  return [
    ...buildRollingRejectionBaseMessages(input),
    {
      role: 'user',
      content: `【废标项全局合稿｜证据索引】
本投标包有效 bidDocumentId：
${bidDocumentIdList}

以下是 Main 侧维护的全量精简状态索引，用于跨批次去重、排除误判和避免早期证据丢失：
${JSON.stringify(finalSummary, null, 2)}`,
    },
    {
      role: 'user',
      content: `【废标项全局合稿任务】
以下 findings 来自多个候选批次的初步定稿结果。请进行全局合稿，只输出最终 JSON。

待合稿 findings：
${JSON.stringify({ findings }, null, 2)}

合稿规则：
1. 合并跨批次重复或高度相似的风险，保留证据更明确、表述更完整的一条。
2. 如果 submittedEvidenceIndex 已经出现对应材料、章节、附件标题、目录、表格、页码线索、图片占位线索或其他提交线索，不得把该材料定稿为缺失。
3. 删除 resolvedRisks 已排除或证据不足的风险。
4. 删除签字、盖章、密封、纸质正副本、现场递交、纸质原件、开标现场行为等纸质或线下事项。
5. bidDocumentId 必须来自上方有效 bidDocumentId。
6. 如果没有符合条件的风险，返回 {"findings":[]}。

JSON 格式：{"findings":[{"bidDocumentId":"有效 bidDocumentId","type":"invalidBid","severity":"high","title":"不超过 28 个中文字符的风险标题","summary":"一句话概括风险","requirement":"对应检查依据或招标要求","bidEvidence":"投标文件中的明确证据、章节、原文摘录或缺失位置说明","riskReason":"为什么该证据可能构成无效标或废标项风险","suggestion":"建议用户如何处理或复核"}]}`,
    },
  ];
}
````

### A.7 BidMaster-Pro — 招标解读(15차원)·평가 매트릭스·리스크

#### A.7.1 15개 해석 차원과 필드 스키마

`BidMaster-Pro/services/interpret/skills/tender_interpret_skill.py:8-184`

````python
DIMENSIONS = [
    {
        "id": "project_info",
        "name": "项目信息",
        "prompt": "提取项目基本信息",
        "schema": {
            "project_name": "项目名称",
            "project_code": "项目编号/招标编号",
            "procurement_method": "采购方式（公开招标/竞争性谈判/询价/单一来源等）",
            "budget_amount": "预算金额（含单位）",
            "procurement_unit": "采购人/招标人名称",
            "project_overview": "项目概况简述",
        },
    },
    {
        "id": "buyer_info",
        "name": "甲方信息",
        "prompt": "提取采购单位详细信息",
        "schema": {
            "unit_name": "采购单位名称",
            "address": "单位地址",
            "contact_person": "联系人",
            "contact_phone": "联系电话",
            "supervisor_dept": "主管部门",
        },
    },
    {
        "id": "qualification",
        "name": "资格要求",
        "prompt": "提取投标人资格要求",
        "schema": {
            "qualification_level": "资质等级要求",
            "registered_capital": "注册资金要求",
            "performance_requirement": "业绩要求",
            "personnel_requirement": "人员要求（项目经理等）",
            "equipment_requirement": "设备要求",
            "other_requirements": "其他资格要求",
        },
    },
    {
        "id": "technical",
        "name": "技术需求",
        "prompt": "提取技术参数和标准",
        "schema": {
            "technical_parameters": "主要技术参数列表",
            "technical_standards": "技术标准/规范",
            "service_requirements": "服务要求",
            "acceptance_criteria": "验收标准",
            "mandatory_params": "★▲标记的强制性参数",
        },
    },
    {
        "id": "scoring",
        "name": "评分细则",
        "prompt": "提取评分标准和权重",
        "schema": {
            "evaluation_method": "评标方法（综合评分法/最低评标价法等）",
            "business_weight": "商务分权重",
            "technical_weight": "技术分权重",
            "price_weight": "价格分权重",
            "scoring_items": "各项评分细则列表（每项含name和description）",
        },
    },
    {
        "id": "disqualification",
        "name": "废标红线",
        "prompt": "提取废标条款和实质性要求",
        "schema": {
            "substantive_requirements": "实质性响应要求",
            "mandatory_conditions": "强制性条件",
            "disqualification_clauses": "废标条款列表（每项含description和clause_number）",
        },
    },
    {
        "id": "deposit",
        "name": "保证金",
        "prompt": "提取投标保证金信息",
        "schema": {
            "amount": "保证金金额",
            "payment_method": "缴纳形式（转账/保函等）",
            "deadline": "缴纳截止时间",
            "refund_conditions": "退还条件",
        },
    },
    {
        "id": "opening",
        "name": "开标要求",
        "prompt": "提取开标和投标递交信息",
        "schema": {
            "opening_time": "开标时间",
            "opening_location": "开标地点",
            "sealing_requirements": "密封要求",
            "submission_method": "递交方式",
            "submission_deadline": "投标截止时间",
        },
    },
    {
        "id": "evaluation",
        "name": "评标办法",
        "prompt": "提取评标方法和流程",
        "schema": {
            "method": "评标方法",
            "committee_composition": "评标委员会组成",
            "evaluation_process": "评标流程步骤列表",
        },
    },
    {
        "id": "commercial",
        "name": "商务评分",
        "prompt": "提取商务评分项",
        "schema": {
            "qualification_score": "企业资质评分",
            "performance_score": "业绩评分",
            "financial_score": "财务状况评分",
            "reputation_score": "信誉评分",
            "other_items": "其他商务评分项",
        },
    },
    {
        "id": "contract",
        "name": "合同条款",
        "prompt": "提取合同主要条款",
        "schema": {
            "payment_terms": "付款方式",
            "breach_liability": "违约责任",
            "warranty_period": "质保期",
            "acceptance_standard": "验收标准",
            "dispute_resolution": "争议解决方式",
        },
    },
    {
        "id": "risk",
        "name": "风险提示",
        "prompt": "识别招标文件中的风险点",
        "schema": {
            "exclusivity_clauses": "排他性条款",
            "biased_scoring": "倾向性评分",
            "unreasonable_requirements": "不合理要求",
            "potential_risks": "潜在风险列表（每项含description和type）",
        },
    },
    {
        "id": "competition",
        "name": "竞争态势",
        "prompt": "分析竞争态势",
        "schema": {
            "potential_competitors": "潜在竞争对手类型",
            "market_pattern": "市场格局分析",
            "competitive_advantages": "竞争优势点",
        },
    },
    {
        "id": "timeline",
        "name": "时间节点",
        "prompt": "提取所有关键时间节点",
        "schema": {
            "announcement_date": "公告日期",
            "clarification_deadline": "答疑/澄清截止日期",
            "bid_deadline": "投标截止日期",
            "opening_date": "开标日期",
            "contract_signing_date": "合同签订日期",
        },
    },
    {
        "id": "contacts",
        "name": "关键联系人",
        "prompt": "提取各方联系人信息",
        "schema": {
            "buyer_contact_person": "采购人联系人",
            "buyer_contact_info": "采购人联系方式",
            "agency_contact_person": "代理机构联系人",
            "agency_contact_info": "代理机构联系方式",
            "technical_contact_person": "技术联系人",
            "technical_contact_info": "技术联系方式",
        },
    },
]
````

#### A.7.2 차원별 system 프롬프트

`BidMaster-Pro/services/interpret/skills/tender_interpret_skill.py:367-395`

````python
        async def interpret_dimension(dim: dict):
            async with semaphore:
                prompt = self._build_prompt(dim, document_text)
                schema_keys = list(dim["schema"].keys())
                schema_desc = "\n".join(
                    f'  "{k}": {v}' for k, v in dim["schema"].items()
                )
                example_json = "{\n" + ",\n".join(
                    f'  "{k}": null' for k in schema_keys
                ) + "\n}"
                messages = [
                    {
                        "role": "system",
                        "content": (
                            f"你是招标文件分析专家，专门提取{dim['name']}信息。\n"
                            "严格要求：\n"
                            f"1. 必须只返回以下{len(schema_keys)}个字段，字段名必须完全一致（英文snake_case）：\n"
                            + "\n".join(f'   - "{k}": {v}' for k, v in dim["schema"].items())
                            + "\n"
                            "2. 禁止使用中文作为字段名，禁止使用camelCase字段名\n"
                            "3. 字段值必须从招标文件原文中准确提取，不要编造或猜测\n"
                            "4. 如果文件中确实未提及某项信息，对应字段填null\n"
                            "5. 所有文本内容必须逐字准确复制，不要出现任何字符重复、乱码、截断\n"
                            "6. 不要添加任何Schema中未定义的额外字段\n"
                            f"\n返回格式示例：\n{example_json}"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ]
````

#### A.7.3 user 프롬프트와 키워드 창 검색(±3줄, 12,000자)

`BidMaster-Pro/services/interpret/skills/tender_interpret_skill.py:417-466`

````python
    def _build_prompt(self, dimension: dict, text: str) -> str:
        relevant_text = self._extract_relevant_text(dimension["id"], text)
        schema_keys = list(dimension["schema"].keys())
        return (
            f"请从以下招标文件内容中{dimension['prompt']}。\n\n"
            f"必须只返回以下字段：{', '.join(schema_keys)}\n"
            f"字段名必须使用英文snake_case格式，禁止使用中文或camelCase。\n\n"
            f"招标文件内容：\n{relevant_text}\n\n"
            "重要提醒：\n"
            "- 逐字准确复制原文内容，不要出现任何字符重复或乱码\n"
            "- 未提及的字段填null\n"
            "- 不要添加额外字段"
        )

    def _extract_relevant_text(self, dim_id: str, text: str) -> str:
        keyword_map = {
            "project_info": ["项目", "招标", "采购", "预算", "编号", "公告"],
            "buyer_info": ["采购人", "招标人", "甲方", "联系人", "地址", "电话", "主管部门"],
            "qualification": ["资格", "资质", "注册资金", "业绩", "人员要求"],
            "technical": ["技术", "参数", "标准", "验收", "★", "▲", "强制性"],
            "deposit": ["保证金", "保函", "投标保证", "保证金额"],
            "timeline": ["截止", "开标", "公告", "时间", "日期", "日前"],
            "scoring": ["评分", "分值", "权重", "评标", "得分", "加分"],
            "disqualification": ["废标", "无效", "拒绝", "实质性", "否决"],
            "opening": ["开标", "递交", "密封", "投标截止"],
            "risk": ["排他", "倾向", "不合理", "风险", "限制"],
            "contract": ["付款", "违约", "质保", "验收标准", "争议"],
            "commercial": ["商务", "资质分", "业绩分", "财务", "信誉"],
            "evaluation": ["评标", "评审", "综合评分", "最低评标价"],
            "competition": ["竞争", "市场", "对手"],
            "contacts": ["联系人", "电话", "地址", "代理机构"],
        }
        keywords = keyword_map.get(dim_id, [])
        if not keywords:
            return text[:12000]

        lines = text.split("\n")
        relevant = []
        seen = set()
        for i, line in enumerate(lines):
            if any(kw in line for kw in keywords):
                start = max(0, i - 3)
                end = min(len(lines), i + 4)
                for j in range(start, end):
                    if j not in seen:
                        relevant.append(lines[j])
                        seen.add(j)

        result = "\n".join(relevant) if relevant else text[:12000]
        return result[:12000]
````

#### A.7.4 평가 매트릭스 프롬프트

`BidMaster-Pro/services/interpret/skills/scoring_matrix_skill.py:20-38`

````python
        messages = [
            {
                "role": "system",
                "content": """你是招标文件评分矩阵构建专家。
将评分标准转换为结构化矩阵，每个评分项一行。
返回JSON数组，每项包含：
- seq: 序号
- category: 类别(商务/技术/价格)
- item: 评分项名称
- score: 分值
- criteria: 评分标准描述
- response_section: 建议应答章节(如"3.1技术方案")
- status: 状态(pending)""",
            },
            {
                "role": "user",
                "content": f"评分标准数据：\n{json.dumps(scoring_data, ensure_ascii=False)}",
            },
        ]
````

#### A.7.5 리스크 경보(배타·편향 평가·불합리 요구) 프롬프트

`BidMaster-Pro/services/interpret/skills/risk_alert_skill.py:18-80`

````python
        messages = [
            {
                "role": "system",
                "content": """你是招标文件风险预警专家。识别招标文件中的潜在风险条款。

识别维度：
1. 排他性条款:
   - 指定品牌、型号或特定技术参数(非功能性需求)
   - 设置不合理的地域限制
   - 要求特定业绩或奖项(与项目无关)
   - 设置过高的资质门槛(超出项目实际需要)
   - 指定特定专利或专有技术

2. 倾向性评分:
   - 评分标准偏向特定供应商
   - 设置主观评分项且无明确标准
   - 评分权重分配不合理
   - 加分项与项目实际需求无关
   - 价格分权重过低(低于法定比例)

3. 不合理要求:
   - 投标时间过短(不足法定天数)
   - 保证金金额过高
   - 履约条件过于苛刻
   - 付款条件不合理
   - 技术参数存在歧视性

4. 合规性风险:
   - 与现行法律法规冲突的条款
   - 违反政府采购程序的规定
   - 限制中小企业参与的条款

返回JSON:
{
  "total_risks": 数量,
  "by_severity": {
    "critical": 数量,
    "high": 数量,
    "medium": 数量,
    "low": 数量
  },
  "risks": [
    {
      "category": "exclusionary/biased_scoring/unreasonable/compliance",
      "title": "风险标题",
      "content": "原文条款内容",
      "location": "在文件中的位置",
      "severity": "critical/high/medium/low",
      "analysis": "风险分析说明",
      "legal_basis": "法律依据(如适用)",
      "suggestion": "应对建议",
      "negotiation_points": "质疑/投诉要点"
    }
  ],
  "overall_risk_level": "critical/high/medium/low",
  "actionable_recommendations": ["可操作的建议列表"]
}""",
            },
            {
                "role": "user",
                "content": f"请分析以下招标文件中的风险条款：\n\n{tender_text[:8000]}",
            },
        ]
````

#### A.7.6 실질적 요구사항(★▲·废标红线) 추출 프롬프트

`BidMaster-Pro/services/generate/skills/mandatory_req_extract_skill.py:18-50`

````python
        messages = [
            {
                "role": "system",
                "content": """从招标文件中提取所有实质性要求和强制性条款。
包括：
1. 所有★▲标记的强制性技术参数
2. 废标红线条款(不满足即废标的条件)
3. 硬性资质要求
4. 评分细则(商务分/技术分/价格分权重)

返回JSON:
{
  "mandatory_params": [
    {"id": "MP-001", "content": "参数描述", "marker": "★/▲", "category": "技术/商务/资质"}
  ],
  "disqualification_clauses": [
    {"id": "DQ-001", "content": "废标条款描述", "severity": "critical/warning"}
  ],
  "hard_qualifications": [
    {"id": "HQ-001", "content": "资质要求描述", "type": "等级/注册资金/业绩"}
  ],
  "scoring_weights": {
    "commercial": 30,
    "technical": 50,
    "price": 20
  }
}""",
            },
            {
                "role": "user",
                "content": f"招标文件：\n{document_text[:8000]}",
            },
        ]
````

### A.8 BidMaster-Pro — 목차·본문 생성

#### A.8.1 1차 목차(평가기준 정렬)·2/3차 목차·일괄 생성 프롬프트

`BidMaster-Pro/services/generate/skills/outline_gen_skill.py:183-282`

````python
def _build_step1_messages(
    text: str, scoring_text: str, mode: str, structure_hint: str = ""
) -> list[dict]:
    if mode == "aligned" and scoring_text:
        system_msg = (
            "你是一个专业的标书编写专家。根据提供的招标文件和评分标准，"
            "生成投标文件的一级目录结构。\n\n"
            "要求：\n"
            "1. 一级目录名称要专业、准确，符合投标文件规范。\n"
            "2. 一级目录名称要尽量与评分标准中的章节名称一致；"
            "如果评分标准中没有明确章节名称，则结合内容总结一级目录名称。\n"
            "3. 一级目录必须覆盖所有评分项。\n"
            "4. 一般包含8-15个一级章节。\n"
            "5. 必须包含：投标函、资格审查、技术方案、商务报价等基本章节。\n"
            "6. 【严禁】使用'章节N'、'第N章'等占位符作为标题，"
            "每个标题必须是有实际含义的专业名称。\n"
            "7. 【严禁】生成空章节（没有description的章节），"
            "每个章节的description必须具体说明本章要写什么。\n"
            "8. 返回标准 JSON 格式，只返回 JSON，不要输出任何其他内容。\n\n"
            "JSON 格式要求：\n"
            '{"chapters": [{"title": "章节标题", "description": "本章内容概述(20字以上)"}]}'
        )
        user_msgs = [
            {"role": "user", "content": f"招标文件摘要：\n{text[:STEP1_TEXT_LIMIT]}"},
            {"role": "user", "content": f"评分标准：\n{scoring_text}"},
        ]
        if structure_hint:
            user_msgs.insert(2, {"role": "user", "content": structure_hint})
        user_msgs.append(
            {"role": "user", "content": "请根据以上招标文件和评分标准，生成投标文件的一级目录结构。每个标题必须有实际含义，不要使用占位符。"}
        )
    else:
        system_msg = (
            "你是一个专业的标书编写专家。根据提供的招标文件内容，"
            "生成投标文件的一级目录结构。\n\n"
            "要求：\n"
            "1. 一级目录名称要专业、准确，符合投标文件规范。\n"
            "2. 一般包含8-15个一级章节。\n"
            "3. 必须包含：投标函、资格审查、技术方案、商务报价等基本章节。\n"
            "4. 【严禁】使用'章节N'、'第N章'等占位符作为标题，"
            "每个标题必须是有实际含义的专业名称。\n"
            "5. 【严禁】生成空章节，每个章节的description必须具体说明本章要写什么。\n"
            "6. 返回标准 JSON 格式，只返回 JSON，不要输出任何其他内容。\n\n"
            "JSON 格式要求：\n"
            '{"chapters": [{"title": "章节标题", "description": "本章内容概述(20字以上)"}]}'
        )
        user_msgs = [
            {"role": "user", "content": f"招标文件摘要：\n{text[:STEP1_TEXT_LIMIT]}"},
        ]
        if structure_hint:
            user_msgs.append({"role": "user", "content": structure_hint})
        user_msgs.append(
            {"role": "user", "content": "请根据以上招标文件内容，生成投标文件的一级目录结构。每个标题必须有实际含义，不要使用占位符。"}
        )
    return [{"role": "system", "content": system_msg}] + user_msgs


def _build_step2_messages(chapter_title: str, chapter_desc: str, text: str, scoring_text: str) -> list[dict]:
    system_msg = (
        "你是专业的标书目录规划专家。为指定一级章节生成二三级子目录。\n\n"
        "【严格规则】\n"
        "1. 只生成3-5个二级目录，每个二级下2-3个三级目录\n"
        "2. 每个目录节点只有title字段，不要添加description等其他字段\n"
        "3. 不要生成超过3级的目录\n"
        "4. 只返回JSON，不要输出任何解释\n\n"
        "【输出格式】\n"
        '{"children": [{"title": "二级标题", "children": [{"title": "三级标题"}]}]}'
    )
    user_content = f"一级章节：{chapter_title}"
    if chapter_desc:
        user_content += f"\n说明：{chapter_desc[:STEP2_DESC_LIMIT]}"
    user_msgs = [{"role": "user", "content": user_content}]
    if scoring_text:
        user_msgs.append({"role": "user", "content": f"相关评分标准：\n{scoring_text[:STEP2_SCORING_LIMIT]}"})
    user_msgs.append({"role": "user", "content": "请生成该一级章节下的二三级子目录。"})
    return [{"role": "system", "content": system_msg}] + user_msgs


def _build_one_shot_messages(text: str, scoring_text: str, mode: str, structure_hint: str = "") -> list[dict]:
    system_msg = (
        "你是具有十年经验的资深投标文件目录规划专家。"
        "请根据招标文件内容生成完整的三级目录大纲。\n\n"
        "要求：\n"
        "1. 目录结构要全面覆盖投标文件的所有必要章节。\n"
        "2. 章节名称要专业、准确，符合投标文件规范。\n"
        "3. 一级目录8-15个，每个一级目录下3-6个二级节，每个二级节下2-4个三级小节。\n"
        "4. 必须包含：投标函、资格审查、技术方案、商务报价等基本章节。\n"
        "5. 返回标准 JSON 格式，只返回 JSON，不要输出任何其他内容。\n\n"
        "JSON 格式要求：\n"
        '{"chapters": [{"id": "1", "title": "章节标题", "level": 1, '
        '"children": [{"id": "1.1", "title": "子标题", "level": 2, '
        '"children": [{"id": "1.1.1", "title": "小节标题", "level": 3, "children": []}]}]}]}'
    )
    user_msgs = [{"role": "user", "content": f"招标文件摘要：\n{text[:ONE_SHOT_TEXT_LIMIT]}"}]
    if scoring_text and mode == "aligned":
        user_msgs.append({"role": "user", "content": f"评分标准：\n{scoring_text}"})
    if structure_hint:
        user_msgs.append({"role": "user", "content": structure_hint})
    user_msgs.append({"role": "user", "content": "请生成完整的三级目录大纲，确保覆盖所有评分要点。"})
    return [{"role": "system", "content": system_msg}] + user_msgs
````

#### A.8.2 이어쓰기(절단 복구) 프롬프트

`BidMaster-Pro/services/generate/skills/content_gen_skill.py:165-181`

````python
            continuation_messages = [
                {
                    "role": "system",
                    "content": (
                        f"你是投标文件撰写专家。请继续完成\u201c{chapter_title}\u201d章节的剩余内容。\n"
                        "要求：\n"
                        "1. 从上次中断的地方继续，不要重复已有内容\n"
                        "2. 确保内容完整，以完整的句子结尾\n"
                        "3. 保持与已有内容一致的语言风格和专业性\n"
                        "4. 直接输出续写内容，不要重复标题"
                    ),
                },
                {
                    "role": "user",
                    "content": f"已生成的内容末尾：\n{continuation_context}\n\n请从这里继续写下去。",
                },
            ]
````

#### A.8.3 본문 생성 system 프롬프트

`BidMaster-Pro/services/generate/skills/content_gen_skill.py:204-246`

````python
    def _build_system_prompt(self, title: str, word_count: int) -> str:
        return f"""你是具有十年以上经验的资深投标文件撰写专家。请撰写\u201c{title}\u201d章节。

【撰写规范】
1. 结构要求：
   - 本章必须包含至少 3 个二级节（用 ### 标记）
   - 每个二级节下必须包含至少 2-3 个三级小节（用 #### 标记）
   - 每个三级小节正文不少于 500 字，重要小节应达到 800-1000 字
   - 可适当使用表格展示对比、清单、计划等结构化信息

2. 语言风格：
   - 使用正式、严谨、专业的投标文件语言
   - 使用\u201c本公司\u201d、\u201c投标人\u201d指代己方，\u201c采购人\u201d、\u201c招标人\u201d指代对方
   - 禁止口语化表达、禁止\u201c我们\u201d、\u201c你们\u201d
   - 禁止模糊表述如\u201c如有需要\u201d、\u201c可以考虑\u201d、\u201c大概\u201d

3. 内容要求：
   - 每个要点必须展开论述，给出具体措施、方法、流程或标准
   - 技术方案章节应包含：总体设计思路、技术架构、关键技术、实施方案、质量保障
   - 服务方案章节应包含：服务体系、服务内容、服务流程、服务标准、应急预案
   - 管理方案章节应包含：组织架构、管理制度、人员配置、培训计划、考核机制

4. 禁止事项：
   - 不得编造企业名称、资质证书、项目案例、人员信息、合同金额
   - 不得使用代码块包裹正文
   - 表格内不得出现 Markdown 格式标记

5. 篇幅要求：
   - 每个三级小节正文不少于 500 字
   - 本章节总字数不少于 {word_count} 字

6. 输出格式：
   - 直接输出章节正文（从 ### 二级节标题开始）
   - 不要输出章节一级标题
   - 不要输出任何解释、说明或总结

7. 质量要求（极其重要）：
   - 每个字词只能出现一次，绝对禁止重复（如\u201c采用采用\u201d\u201c包括包括\u201d\u201c项目项目\u201d）
   - 禁止输出任何无意义的单字母（如\u201cz\u201d\u201cx\u201d等）
   - 禁止输出乱码或不可读字符
   - 标题编号必须规范（如 ### 1.1、#### 1.1.1），禁止出现\u201c1####\u201d\u201cd D.\u201d等格式
   - 每个标点符号只用一次，禁止重复（如\u201c。。。。\u201d）
   - 输出前请逐字检查，确保无重复词、无错字、无乱码"""
````

#### A.8.4 분할 생성 계획 프롬프트

`BidMaster-Pro/services/generate/skills/content_gen_skill.py:408-427`

````python
        plan_messages = [
            {
                "role": "system",
                "content": (
                    "你是投标文件规划专家。将章节大纲拆分为多个独立的小节，"
                    "每个小节对应一个完整的子章节。\n"
                    "返回JSON格式：{\"sections\": [{\"title\": \"小节标题\", \"word_target\": 1500}]}\n"
                    "每个小节目标字数1500-2500字，总数加起来应达到章节总字数要求。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"章节标题：{title}\n"
                    f"章节大纲：\n{outline[:2000]}\n"
                    f"章节总字数要求：{word_count}字\n"
                    "请拆分为多个小节。"
                ),
            },
        ]
````

### A.9 BidMaster-Pro — 점검 규칙 프롬프트(21개 중 LLM 사용분)

#### A.9.1 compliance(合规性检查)

`BidMaster-Pro/services/check/skills/compliance_check_skill.py:20-53`

````python
        messages = [
            {
                "role": "system",
                "content": """你是投标文件合规性检查专家。
逐条检查投标文件是否满足招标文件的所有硬性要求。

检查步骤：
1. 从招标文件提取所有硬性要求(必须/应当/须/不得/禁止)
2. 逐条在投标文件中查找对应响应
3. 判断每项是否满足

返回JSON:
{
  "total_requirements": 数量,
  "compliant": 数量,
  "non_compliant": 数量,
  "items": [
    {
      "requirement": "招标要求描述",
      "source_location": "招标文件位置",
      "response": "投标文件响应内容",
      "response_location": "投标文件位置",
      "status": "compliant/non_compliant/partial",
      "severity": "critical/major/minor",
      "suggestion": "修改建议"
    }
  ]
}""",
            },
            {
                "role": "user",
                "content": f"招标文件：\n{tender_text[:6000]}\n\n投标文件：\n{bid_text[:6000]}",
            },
        ]
````

#### A.9.2 disqualification(废标项检查, 3라운드)

`BidMaster-Pro/services/check/skills/disqualification_check_skill.py:53-172`

````python
    async def _extract_clauses(self, ctx: SkillContext, tender_text: str) -> list[dict]:
        messages = [
            {
                "role": "system",
                "content": """你是废标条款提取专家。从招标文件中提取所有可能导致废标或无效投标的条款。

区分两种类型：
- invalidBid: 投标无效条件（资格性审查不通过）
- rejectionItem: 废标项（符合性审查不通过）

返回JSON:
{"clauses": [{"id": "DQ-001", "type": "invalidBid/rejectionItem", "content": "废标条款内容", "severity": "critical/warning"}]}""",
            },
            {"role": "user", "content": f"招标文件：\n{tender_text[:6000]}"},
        ]
        result = await ctx.llm.collect_json(messages=messages, temperature=0.1)
        return result.get("clauses", []) if isinstance(result, dict) else []

    async def _inspect_clauses(
        self, ctx: SkillContext, clauses: list[dict], bid_text: str
    ) -> list[dict]:
        if not clauses:
            return []

        dq_text = "\n".join(
            f"- [{c.get('id', '')}] ({c.get('type', '')}) {c.get('content', '')}"
            for c in clauses
        )

        messages = [
            {
                "role": "system",
                "content": """你是废标风险检查专家。逐条检查投标文件是否完整响应了所有废标条款。

对每条废标条款：
1. 在投标文件中查找对应响应
2. 判断响应质量：明确/模糊/缺失
3. 评估风险等级

重要限制：
- 如果投标文件是图片/扫描件格式而你无法看到图片内容，不得判定"材料缺失"
- 只能基于你能看到的文本内容做判断

返回JSON:
{
  "items": [
    {
      "clause_id": "DQ-001",
      "clause_type": "invalidBid/rejectionItem",
      "clause_content": "废标条款内容",
      "response_found": true/false,
      "response_content": "找到的响应内容(原文摘录)",
      "response_quality": "明确/模糊/缺失",
      "risk_level": "high/medium/low",
      "suggestion": "修改建议"
    }
  ]
}""",
            },
            {
                "role": "user",
                "content": f"废标条款：\n{dq_text}\n\n投标文件：\n{bid_text[:6000]}",
            },
        ]
        result = await ctx.llm.collect_json(messages=messages, temperature=0.1)
        return result.get("items", []) if isinstance(result, dict) else []

    async def _finalize(
        self, ctx: SkillContext, clauses: list[dict], bid_text: str, round2_items: list[dict]
    ) -> list[dict]:
        if not round2_items:
            return []

        existing_ids = {i.get("clause_id") for i in round2_items}
        missing_clauses = [c for c in clauses if c.get("id") not in existing_ids]

        items_summary = "\n".join(
            f"- {i.get('clause_id', '')}: response_found={i.get('response_found')}, "
            f"quality={i.get('response_quality')}, risk={i.get('risk_level')}"
            for i in round2_items
        )

        missing_text = ""
        if missing_clauses:
            missing_text = "\n\n未被检查的条款：\n" + "\n".join(
                f"- [{c.get('id', '')}] {c.get('content', '')}" for c in missing_clauses
            )

        messages = [
            {
                "role": "system",
                "content": """你是废标检查定稿专家。请对上一轮检查结果进行补充、去重和定稿：

1. 补充：检查是否有遗漏的废标条款未被检查
2. 去重：合并重复的检查项
3. 定稿：确认每项的风险等级和修改建议

返回JSON:
{
  "items": [
    {
      "clause_id": "DQ-001",
      "clause_type": "invalidBid/rejectionItem",
      "clause_content": "废标条款内容",
      "response_found": true/false,
      "response_content": "找到的响应内容",
      "response_quality": "明确/模糊/缺失",
      "risk_level": "high/medium/low",
      "suggestion": "修改建议"
    }
  ]
}""",
            },
            {
                "role": "user",
                "content": f"上一轮检查结果：\n{items_summary}{missing_text}\n\n投标文件（参考）：\n{bid_text[:3000]}",
            },
        ]
        result = await ctx.llm.collect_json(messages=messages, temperature=0.1)
        return result.get("items", []) if isinstance(result, dict) else round2_items
````

#### A.9.3 mandatoryReq(★▲参数对照)

`BidMaster-Pro/services/check/skills/mandatory_req_check_skill.py:20-57`

````python
        messages = [
            {
                "role": "system",
                "content": """你是实质性要求对照专家。逐条检查投标文件对招标文件中★▲强制性参数的响应：

1. 提取所有★▲标记的强制性技术参数
2. 在投标文件中逐条查找对应响应
3. 判断每项是否满足、是否有负偏离、是否有模糊表述

返回JSON:
{
  "total_mandatory": 0,
  "fully_responded": 0,
  "negative_deviation": 0,
  "vague_response": 0,
  "items": [
    {
      "param_id": "MP-001",
      "requirement": "★强制性参数描述",
      "marker": "★/▲",
      "category": "技术/商务/资质",
      "response_found": true/false,
      "response_content": "投标文件中的响应内容",
      "response_quality": "明确响应/模糊表述/未响应/负偏离",
      "status": "compliant/non_compliant/partial/vague",
      "severity": "critical/major/minor",
      "suggestion": "修改建议"
    }
  ],
  "has_critical_issues": true/false,
  "risk_level": "high/medium/low"
}""",
            },
            {
                "role": "user",
                "content": f"招标文件：\n{tender_text[:5000]}\n\n投标文件：\n{bid_text[:5000]}",
            },
        ]
````

#### A.9.4 qualification(资质核查)

`BidMaster-Pro/services/check/skills/qualification_check_skill.py:18-52`

````python
        messages = [
            {
                "role": "system",
                "content": """你是资质证书核查专家。对投标文件中的资质证书进行5项核查：

①有效期核查：证书有效期是否覆盖投标截止日
②名称一致性：证书名称是否与招标要求完全一致
③企业名称一致性：企业名称与营业执照/公章是否一致
④三证合一核查：三证合一/旧版分离证书是否匹配
⑤清晰度评估：证书扫描件是否清晰可辨

返回JSON:
{
  "checks": [
    {
      "check_type": "validity/name_match/company_match/three_in_one/clarity",
      "check_name": "检查项名称",
      "certificate_name": "证书名称",
      "required_by_tender": "招标要求",
      "found_in_bid": "投标文件中的内容",
      "status": "pass/fail/warning",
      "detail": "详细说明",
      "suggestion": "修改建议"
    }
  ],
  "summary": {"total": 5, "passed": 3, "failed": 1, "warning": 1},
  "risk_level": "high/medium/low",
  "disqualification_risk": true/false
}""",
            },
            {
                "role": "user",
                "content": f"招标文件资质要求：\n{tender_text[:4000]}\n\n投标文件资质信息：\n{bid_text[:4000]}\n\n投标截止日：{bid_deadline}",
            },
        ]
````

#### A.9.5 deposit(保证金核查)

`BidMaster-Pro/services/check/skills/deposit_check_skill.py:20-52`

````python
        messages = [
            {
                "role": "system",
                "content": """你是投标保证金核查专家。从招标文件和投标文件中核查保证金4项内容：

①金额一致性：保证金金额是否与招标要求精确一致（精确到分）
②缴纳形式：是否按要求的缴纳形式（电汇/保函/支票等）缴纳
③到账时间：保证金是否在截止时间之前到账
④保函有效期：保函有效期是否覆盖投标有效期+30天

返回JSON:
{
  "checks": [
    {
      "check_type": "amount/form/timing/guarantee_period",
      "check_name": "检查项名称",
      "required": "招标要求",
      "actual": "投标文件中的内容",
      "status": "pass/fail/warning",
      "detail": "详细说明",
      "suggestion": "修改建议"
    }
  ],
  "summary": {"total": 4, "passed": 0, "failed": 0, "warning": 0},
  "risk_level": "high/medium/low",
  "has_critical_issues": true/false
}""",
            },
            {
                "role": "user",
                "content": f"招标文件：\n{tender_text[:4000]}\n\n投标文件：\n{bid_text[:4000]}",
            },
        ]
````

#### A.9.6 signature(签章核查)

`BidMaster-Pro/services/check/skills/signature_check_skill.py:17-51`

````python
        messages = [
            {
                "role": "system",
                "content": """你是签字盖章核查专家。核查投标文件的签章完整性：

①法人签字：投标函是否有法定代表人签字/盖章
②授权委托书：授权委托书是否完整（委托人/被委托人签字+公章）
③公章：所有要求加盖公章的页面是否已盖章
④骑缝章：投标文件是否有骑缝章
⑤CA证书：电子投标的CA数字证书是否在有效期内
⑥密封要求：纸质投标的密封标识是否规范

返回JSON:
{
  "checks": [
    {
      "check_type": "legal_rep_sign/authorization/seal/page_seal/counterfoil/ca_cert/sealing",
      "check_name": "检查项名称",
      "required": "招标要求",
      "found": "投标文件中的内容",
      "status": "pass/fail/warning",
      "detail": "详细说明",
      "suggestion": "修改建议"
    }
  ],
  "summary": {"total": 0, "passed": 0, "failed": 0, "warning": 0},
  "risk_level": "high/medium/low",
  "has_critical_issues": true/false
}""",
            },
            {
                "role": "user",
                "content": f"招标文件签章要求：\n{tender_text[:3000]}\n\n投标文件签章信息：\n{bid_text[:3000]}",
            },
        ]
````

#### A.9.7 validity(有效期核查)

`BidMaster-Pro/services/check/skills/validity_check_skill.py:17-49`

````python
        messages = [
            {
                "role": "system",
                "content": """你是投标有效期核查专家。核查以下内容：

①投标有效期：投标文件承诺的有效期是否≥招标要求天数
②保函有效期：保函有效期是否覆盖投标有效期+30天
③资质有效期：所有资质证书有效期是否覆盖投标截止日
④CA证书有效期：CA数字证书是否在有效期内

返回JSON:
{
  "checks": [
    {
      "check_type": "bid_validity/guarantee_period/qualification_expiry/ca_expiry",
      "check_name": "检查项名称",
      "required_period": "招标要求",
      "actual_period": "投标文件承诺",
      "status": "pass/fail/warning",
      "detail": "详细说明",
      "suggestion": "修改建议"
    }
  ],
  "summary": {"total": 0, "passed": 0, "failed": 0, "warning": 0},
  "risk_level": "high/medium/low",
  "has_critical_issues": true/false
}""",
            },
            {
                "role": "user",
                "content": f"招标文件：\n{tender_text[:3000]}\n\n投标文件：\n{bid_text[:3000]}",
            },
        ]
````

#### A.9.8 consistency(一致性校验) — 규칙부와 LLM부

`BidMaster-Pro/services/check/skills/consistency_check_skill.py:59-183`

````python
    def _rule_based_check(self, bid_text: str, project_facts: dict) -> list[dict]:
        issues = []

        if not project_facts:
            return issues

        entity_keys = {
            "project_name": "项目名称",
            "company_name": "公司名称",
            "bidder_name": "投标人名称",
            "purchaser_name": "采购人名称",
            "agency_name": "代理机构名称",
        }
        for fact_key, label in entity_keys.items():
            value = str(project_facts.get(fact_key, "")).strip()
            if not value or len(value) < 4:
                continue
            if value not in bid_text:
                issues.append({
                    "check_type": "entity_mismatch",
                    "check_name": f"实体名称一致性",
                    "location_a": f"项目事实({label})",
                    "value_a": value,
                    "location_b": "投标文件全文",
                    "value_b": "未找到",
                    "status": "inconsistent",
                    "severity": "major",
                    "suggestion": f"投标文件中未出现{label}'{value}'，请确认是否遗漏",
                })

        date_keys = {
            "service_period": "服务期限",
            "bid_deadline": "投标截止日",
            "delivery_date": "交付日期",
        }
        for fact_key, label in date_keys.items():
            value = str(project_facts.get(fact_key, "")).strip()
            if not value or len(value) < 4:
                continue
            if value not in bid_text:
                issues.append({
                    "check_type": "date_conflict",
                    "check_name": f"时间一致性",
                    "location_a": f"项目事实({label})",
                    "value_a": value,
                    "location_b": "投标文件全文",
                    "value_b": "未找到",
                    "status": "warning",
                    "severity": "minor",
                    "suggestion": f"投标文件中未体现{label}'{value}'",
                })

        budget = str(project_facts.get("budget_amount", "")).strip()
        if budget:
            digits = re.findall(r"[\d,.]+", budget)
            for digit in digits:
                if len(digit) >= 3 and digit not in bid_text:
                    issues.append({
                        "check_type": "number_conflict",
                        "check_name": "数值一致性",
                        "location_a": "项目事实(预算金额)",
                        "value_a": digit,
                        "location_b": "投标文件全文",
                        "value_b": "未找到",
                        "status": "warning",
                        "severity": "minor",
                        "suggestion": f"预算金额中的'{digit}'未在投标文件中出现",
                    })

        return issues

    async def _llm_deep_check(
        self, ctx: SkillContext, bid_text: str, tender_text: str, project_facts: dict
    ) -> list[dict]:
        facts_summary = ""
        if project_facts:
            facts_lines = []
            for k, v in project_facts.items():
                if v and str(v).strip():
                    facts_lines.append(f"- {k}: {v}")
            facts_summary = "\n".join(facts_lines[:20])

        system_content = """你是标书一致性校验专家。请进行以下深度检查：

①工期一致性：技术方案中的工期 vs 商务标中的工期 vs 投标函承诺的工期
②金额一致性：各处报价金额是否一致（投标函总价 vs 报价明细合计 vs 商务标汇总）
③人员一致性：项目经理/技术负责人在技术方案和人员简历中是否一致
④承诺一致性：质保期/响应时间/服务承诺在不同章节是否一致
⑤企业信息一致性：公司名称/地址/联系方式在各处是否一致
⑥逻辑谬误检查：前后矛盾、逻辑不一致、表述漏洞
⑦编造信息检测：是否存在可能编造的企业资质、案例、人员信息

返回JSON:
{
  "checks": [
    {
      "check_type": "duration/amount/personnel/commitment/company_info/logic_fallacy/fabrication",
      "check_name": "检查项名称",
      "location_a": "位置1描述",
      "value_a": "值1",
      "location_b": "位置2描述",
      "value_b": "值2",
      "status": "consistent/inconsistent/warning",
      "severity": "critical/major/minor",
      "suggestion": "修改建议"
    }
  ]
}"""

        user_parts = [f"投标文件内容：\n{bid_text[:5000]}"]
        if tender_text:
            user_parts.append(f"招标文件内容（参考）：\n{tender_text[:2000]}")
        if facts_summary:
            user_parts.append(f"项目已确认事实：\n{facts_summary[:1000]}")

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]

        try:
            result = await ctx.llm.collect_json(messages=messages, temperature=0.1)
            return result.get("checks", []) if isinstance(result, dict) else []
        except Exception:
            return []
````

#### A.9.9 duplicate(标书查重) — LLM 심층 분석부

`BidMaster-Pro/services/check/skills/duplicate_check_skill.py:188-248`

````python
    async def _llm_deep_analysis(
        self, ctx: SkillContext, bid_text: str, ref_content: str, algo_result: dict
    ) -> dict | None:
        try:
            messages = [
                {
                    "role": "system",
                    "content": """你是标书查重检测专家。算法已初步检测出相似度，请进行深度语义分析：

1. 内部重复：同一投标文件中是否有大段重复内容
2. 模板痕迹：是否直接复制了通用模板而未修改项目特定信息
3. 与参考文档相似度：如果提供了参考文档，检测语义层面的相似度
4. 改写检测：是否存在换词不改意的改写抄袭

返回JSON:
{
  "internal_duplicate": {
    "found": true/false,
    "sections": [
      {"section_a": "位置1", "section_b": "位置2", "similarity": 0.95, "content_preview": "重复内容预览"}
    ]
  },
  "template_traces": {
    "found": true/false,
    "items": [
      {"content": "通用模板内容", "location": "位置", "suggestion": "修改建议"}
    ]
  },
  "external_similarity": {
    "max_similarity": 0.0,
    "similar_sections": [
      {"bid_section": "投标文件位置", "ref_index": 0, "similarity": 0.85, "content_preview": "相似内容预览"}
    ]
  },
  "paraphrase_detected": {
    "found": true/false,
    "items": [
      {"original": "原文表述", "paraphrased": "改写表述", "location": "位置"}
    ]
  },
  "overall_risk": "high/medium/low",
  "duplicate_score": 0-100,
  "has_critical_issues": true/false
}""",
                },
                {
                    "role": "user",
                    "content": (
                        f"投标文件：\n{bid_text[:5000]}"
                        + (f"\n\n参考文档：\n{ref_content}" if ref_content else "")
                        + f"\n\n算法初步检测结果：\n{algo_result}"
                    ),
                },
            ]
            result = await ctx.llm.collect_json(messages=messages, temperature=0.1)
            if isinstance(result, dict):
                result.setdefault("has_critical_issues", result.get("overall_risk") == "high")
            return result
        except Exception as e:
            logger.warning(f"LLM深度分析失败: {e}")
            return None
````

#### A.9.10 docIntegrity(文件完整性)

`BidMaster-Pro/services/check/skills/doc_integrity_check_skill.py:17-51`

````python
        messages = [
            {
                "role": "system",
                "content": """你是投标文件完整性核查专家。核查以下内容：

①正本副本份数：正本和副本份数是否与招标要求一致
②密封袋标识：密封袋标识是否规范（项目名称/编号/正副本标记）
③骑缝章：骑缝章是否完整
④页码：页码是否连续完整
⑤目录：目录是否与正文对应
⑥附件清单：所有要求附件是否齐全

返回JSON:
{
  "checks": [
    {
      "check_type": "copies/sealing/counterfoil/pagination/contents/attachments",
      "check_name": "检查项名称",
      "required": "招标要求",
      "actual": "投标文件情况",
      "status": "pass/fail/warning",
      "detail": "详细说明",
      "suggestion": "修改建议"
    }
  ],
  "summary": {"total": 0, "passed": 0, "failed": 0, "warning": 0},
  "risk_level": "high/medium/low",
  "has_critical_issues": true/false
}""",
            },
            {
                "role": "user",
                "content": f"招标文件：\n{tender_text[:3000]}\n\n投标文件：\n{bid_text[:3000]}",
            },
        ]
````

#### A.9.11 fitScore(贴合度评分)

`BidMaster-Pro/services/check/skills/fit_score_skill.py:13-59`

````python
    GENERIC_PHRASES = [
        "我司具有丰富的行业经验",
        "本公司拥有专业的技术团队",
        "我们具备完善的售后服务体系",
        "公司秉承客户至上的理念",
        "具有多年的项目实施经验",
        "拥有一流的技术实力",
        "我们将竭诚为您服务",
    ]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        tender_text = ctx.parameters.get("tender_text", "")
        bid_text = ctx.parameters.get("bid_text", "")

        generic_count = sum(1 for phrase in self.GENERIC_PHRASES if phrase in bid_text)

        messages = [
            {
                "role": "system",
                "content": f"""评估投标文件与招标文件的贴合度。

评分维度：
1. 内容贴合度(40%): 是否严格贴合招标文件要求
2. 技术方案针对性(30%): 技术方案是否针对项目场景定制
3. 评分项覆盖率(20%): 评分项是否有对应应答内容
4. 废标条款响应率(10%): 废标条款是否全部响应

已知通用套话命中: {generic_count}/{len(self.GENERIC_PHRASES)}

返回JSON:
{{
  "fit_score": 0-100,
  "dimensions": {{
    "content_fit": {{"score": 0-100, "detail": "说明"}},
    "technical_targeting": {{"score": 0-100, "detail": "说明"}},
    "scoring_coverage": {{"score": 0-100, "detail": "说明"}},
    "disqualification_response": {{"score": 0-100, "detail": "说明"}}
  }},
  "generic_phrases_found": ["发现的通用套话列表"],
  "suggestions": ["改进建议"]
}}""",
            },
            {
                "role": "user",
                "content": f"招标文件：\n{tender_text[:4000]}\n\n投标文件：\n{bid_text[:4000]}",
            },
        ]
````

#### A.9.12 crossCheck(交叉比对)

`BidMaster-Pro/services/check/skills/cross_check_skill.py:20-67`

````python
        messages = [
            {
                "role": "system",
                "content": """你是投标文件交叉比对专家。逐项比对投标文件与招标文件的评分标准。

比对步骤：
1. 从招标文件中提取所有评分项(商务分、技术分、价格分等)
2. 对每个评分项，在投标文件中查找对应的响应内容
3. 判断每个评分项的响应状态

响应状态定义：
- answered: 投标文件中有完整、明确的响应内容
- partial: 投标文件中有部分响应，但不完整或不够明确
- missing: 投标文件中未找到对应响应内容

返回JSON:
{
  "total_items": 数量,
  "answered": 数量,
  "partial": 数量,
  "missing": 数量,
  "coverage_rate": "百分比字符串",
  "items": [
    {
      "seq": 序号,
      "category": "商务/技术/价格/其他",
      "scoring_item": "评分项名称",
      "score": 分值,
      "scoring_criteria": "评分标准描述",
      "response_status": "answered/partial/missing",
      "response_content": "投标文件中的响应内容摘要(missing时为null)",
      "response_location": "响应内容在投标文件中的位置",
      "gap_analysis": "差距分析(仅partial/missing时填写)",
      "suggestion": "补充建议"
    }
  ],
  "risk_assessment": {
    "missing_score": 因缺失项可能丢失的总分,
    "partial_score": 因不完整项可能丢失的预估分,
    "max_obtainable_score": 最多可获分数
  }
}""",
            },
            {
                "role": "user",
                "content": f"招标文件：\n{tender_text[:6000]}\n\n投标文件：\n{bid_text[:6000]}",
            },
        ]
````

#### A.9.13 aiTextCheck(AI文本检查)

`BidMaster-Pro/services/check/skills/ai_text_check_skill.py:18-57`

````python
        messages = [
            {
                "role": "system",
                "content": """你是投标文件文本质量检查专家。对投标文件进行以下三类检查：

1. 拼写检查(spelling): 错别字、同音字混淆、形近字错误
2. 标点检查(punctuation): 标点符号误用、中英文标点混用、缺失标点、多余标点
3. 实体识别(entity): 人名、公司名、项目名、日期、金额等关键实体是否前后一致、是否正确

检查要求：
- 逐段扫描文本，不遗漏任何问题
- 对每个问题给出准确位置描述
- 提供具体的修改建议

返回JSON:
{
  "total_issues": 数量,
  "by_type": {
    "spelling": 数量,
    "punctuation": 数量,
    "entity": 数量
  },
  "issues": [
    {
      "type": "spelling/punctuation/entity",
      "original": "原文内容",
      "location": "位置描述(如: 第3段第2行)",
      "description": "问题描述",
      "suggestion": "修改建议",
      "severity": "high/medium/low"
    }
  ],
  "overall_quality": "excellent/good/fair/poor"
}""",
            },
            {
                "role": "user",
                "content": f"请检查以下投标文件文本：\n\n{bid_text[:8000]}",
            },
        ]
````

#### A.9.14 sampleReport(样品/检测报告)

`BidMaster-Pro/services/check/skills/sample_report_check_skill.py:20-70`

````python
        messages = [
            {
                "role": "system",
                "content": """你是投标文件样品/检测报告核查专家。对投标文件中的样品和检测报告进行以下核查：

1. CMA/CNAS资质核查:
   - 检测机构是否具备CMA(检验检测机构资质认定)资质
   - 检测机构是否具备CNAS(中国合格评定国家认可委员会)认可
   - 资质证书是否在有效期内
   - 资质范围是否覆盖招标要求的检测项目

2. 检测项目对应性核查:
   - 招标文件要求的检测项目是否在检测报告中全部覆盖
   - 检测参数、检测方法是否符合招标文件要求的标准
   - 检测结果是否满足招标文件规定的技术指标

3. 有效期核查:
   - 检测报告是否在有效期内
   - 报告出具日期是否在招标文件规定的时间范围内
   - 样品送检时间与报告出具时间的合理性

返回JSON:
{
  "total_checks": 数量,
  "passed": 数量,
  "failed": 数量,
  "warning": 数量,
  "checks": [
    {
      "check_type": "qualification/item_correspondence/validity",
      "check_name": "检查项名称",
      "tender_requirement": "招标文件要求",
      "bid_content": "投标文件内容",
      "status": "pass/fail/warning",
      "detail": "详细说明",
      "suggestion": "修改建议(仅fail/warning时填写)"
    }
  ],
  "qualification_summary": {
    "cma_valid": true/false,
    "cnas_valid": true/false,
    "coverage_rate": "检测项目覆盖率"
  },
  "risk_level": "high/medium/low"
}""",
            },
            {
                "role": "user",
                "content": f"招标文件：\n{tender_text[:6000]}\n\n投标文件：\n{bid_text[:6000]}",
            },
        ]
````

#### A.9.15 jointBid(联合投标协议)

`BidMaster-Pro/services/check/skills/joint_bid_check_skill.py:20-74`

````python
        messages = [
            {
                "role": "system",
                "content": """你是联合投标协议核查专家。对联合体投标的协议文件进行完整性核查。

核查要点：
1. 联合体资质核查:
   - 招标文件是否允许联合体投标
   - 联合体各方是否具备相应的资质条件
   - 联合体资质等级是否符合招标要求(就低不就高原则)

2. 协议内容完整性:
   - 联合体协议是否包含所有必需方签字盖章
   - 是否明确联合体各方的分工和责任
   - 是否指定联合体牵头人
   - 是否约定各方承担的份额比例
   - 是否包含连带责任条款

3. 合规性核查:
   - 联合体各方是否单独或参与其他联合体重复投标
   - 联合体成员数量是否符合招标文件限制
   - 协议有效期是否覆盖投标及合同执行期

返回JSON:
{
  "total_checks": 数量,
  "passed": 数量,
  "failed": 数量,
  "warning": 数量,
  "checks": [
    {
      "check_type": "qualification/agreement_content/compliance",
      "check_name": "检查项名称",
      "tender_requirement": "招标文件要求",
      "bid_content": "投标文件内容",
      "status": "pass/fail/warning",
      "detail": "详细说明",
      "suggestion": "修改建议"
    }
  ],
  "consortium_info": {
    "is_consortium_bid": true/false,
    "allowed_by_tender": true/false,
    "lead_member": "牵头方名称(如能识别)",
    "member_count": 成员数量,
    "missing_signatures": ["缺少签字盖章的成员列表"]
  },
  "risk_level": "high/medium/low"
}""",
            },
            {
                "role": "user",
                "content": f"招标文件：\n{tender_text[:6000]}\n\n投标文件：\n{bid_text[:6000]}",
            },
        ]
````

#### A.9.16 ebidSubmit(电子投标提交)

`BidMaster-Pro/services/check/skills/ebid_submit_check_skill.py:20-82`

````python
        messages = [
            {
                "role": "system",
                "content": """你是电子投标提交核查专家。对电子投标文件的提交合规性进行全面核查。

核查要点：
1. 文件格式核查:
   - 投标文件格式是否符合招标文件要求(如PDF/DOCX/专用格式)
   - 文件是否可正常打开和读取
   - 文件大小是否在平台限制范围内
   - 文件命名是否符合招标文件要求

2. CA证书/电子签章核查:
   - 是否使用有效的CA数字证书进行电子签名
   - 电子签章是否覆盖所有需要签章的页面
   - 签章是否在有效期内
   - 签章人身份是否与投标主体一致
   - 是否存在未签章的关键页面

3. 文件完整性核查:
   - 投标文件各部分是否完整上传
   - 附件材料是否齐全
   - 文件是否损坏或存在乱码
   - 加密投标文件是否正确加密
   - 是否存在遗漏的必传文件

4. 提交合规性核查:
   - 是否在规定的提交截止时间前完成提交
   - 提交次数是否符合规定
   - 是否按照招标文件要求的顺序和结构组织文件

返回JSON:
{
  "total_checks": 数量,
  "passed": 数量,
  "failed": 数量,
  "warning": 数量,
  "checks": [
    {
      "check_type": "format/ca_certificate/integrity/compliance",
      "check_name": "检查项名称",
      "tender_requirement": "招标文件要求",
      "bid_content": "投标文件内容",
      "status": "pass/fail/warning",
      "detail": "详细说明",
      "suggestion": "修改建议"
    }
  ],
  "ebid_summary": {
    "format_compliant": true/false,
    "ca_valid": true/false,
    "seal_complete": true/false,
    "file_integrity": true/false,
    "missing_files": ["缺失文件列表"]
  },
  "risk_level": "high/medium/low"
}""",
            },
            {
                "role": "user",
                "content": f"招标文件：\n{tender_text[:6000]}\n\n投标文件：\n{bid_text[:6000]}",
            },
        ]
````

#### A.9.17 pricingLogic(报价逻辑闭环)

`BidMaster-Pro/services/check/skills/pricing_logic_check_skill.py:20-79`

````python
        messages = [
            {
                "role": "system",
                "content": """你是报价逻辑闭环检查专家。对投标文件的报价逻辑进行全面闭环检查。

检查维度：
1. 报价逻辑完整性:
   - 报价总表与分项报价表是否一致(纵向汇总校验)
   - 各分项报价之和是否等于投标总价
   - 报价明细表与汇总表是否对应
   - 是否存在遗漏的报价项
   - 报价项目是否完整覆盖招标文件要求的全部费用项

2. 人天核验:
   - 人员投入总人天数与报价是否匹配
   - 各岗位人天单价×人天数=该岗位费用，验算是否正确
   - 人天单价是否在合理范围内(与市场价对比)
   - 人员配置数量与工作量是否匹配
   - 加班/差旅等人天计算是否合理

3. 费用分摊检查:
   - 直接费用与间接费用的分摊是否合理
   - 管理费/利润的计取基数和费率是否合理
   - 税金计算是否正确(税率、计税基数)
   - 各项费用占比是否在合理范围内
   - 是否存在重复计费的项目

返回JSON:
{
  "total_checks": 数量,
  "passed": 数量,
  "failed": 数量,
  "warning": 数量,
  "checks": [
    {
      "check_type": "completeness/person_day/cost_allocation",
      "check_name": "检查项名称",
      "expected": "预期值(数值或描述)",
      "actual": "实际值(数值或描述)",
      "deviation": "偏差(数值或描述)",
      "status": "pass/fail/warning",
      "detail": "详细说明",
      "suggestion": "修改建议"
    }
  ],
  "pricing_summary": {
    "total_price": 投标总价,
    "price_breakdown_consistent": true/false,
    "person_day_verified": true/false,
    "cost_allocation_reasonable": true/false,
    "arithmetic_errors": 算术错误数量
  },
  "risk_level": "high/medium/low"
}""",
            },
            {
                "role": "user",
                "content": f"招标文件：\n{tender_text[:6000]}\n\n投标文件：\n{bid_text[:6000]}",
            },
        ]
````

#### A.9.18 whitelist_filter(查重 오탐 판정) LLM부

`BidMaster-Pro/services/check/skills/whitelist_filter_skill.py:130-157`

````python
    async def _llm_filter(self, matches: list[dict], ctx: SkillContext) -> list[dict]:
        if not matches:
            return []

        texts = []
        for i, m in enumerate(matches[:10]):
            text = m.get("text", m.get("content", ""))[:200]
            texts.append(f"{i+1}. {text}")

        messages = [
            {
                "role": "system",
                "content": """你是标书查重误报判断专家。判断以下匹配是否为误报（即不应该被标记为重复的内容）。

常见误报类型：
1. 行业标准用语和规范表述
2. 法律法规引用
3. 通用技术参数和指标
4. 招标文件原文引用
5. 常见承诺和保证用语

返回JSON: {"results": [{"index": 1, "is_false_positive": true/false, "reason": "理由"}]}""",
            },
            {
                "role": "user",
                "content": "\n".join(texts),
            },
        ]
````

#### A.9.19 selfcheck(废标自查清单) 20개 항목 정의

`BidMaster-Pro/services/check/skills/selfcheck_list_skill.py:5-51`

````python
SELFCHECK_ITEMS = [
    {
        "category": "资质文件核查",
        "items": [
            {"id": "SC-01", "content": "所有资质证书有效期覆盖投标截止日", "check_skill": "qualification_check"},
            {"id": "SC-02", "content": "证书名称与招标要求完全一致", "check_skill": "qualification_check"},
            {"id": "SC-03", "content": "三证合一/旧版分离证书匹配", "check_skill": "qualification_check"},
            {"id": "SC-04", "content": "证书扫描件清晰可辨", "check_skill": "qualification_check"},
        ],
    },
    {
        "category": "投标保证金核查",
        "items": [
            {"id": "SC-05", "content": "保证金金额与招标要求一致(精确到分)", "check_skill": "deposit_check"},
            {"id": "SC-06", "content": "缴纳形式符合要求", "check_skill": "deposit_check"},
            {"id": "SC-07", "content": "到账时间早于截止时间", "check_skill": "deposit_check"},
            {"id": "SC-08", "content": "保函有效期覆盖投标有效期+30天", "check_skill": "deposit_check"},
        ],
    },
    {
        "category": "文件完整性与签章核查",
        "items": [
            {"id": "SC-09", "content": "正本副本份数与要求一致", "check_skill": "doc_integrity"},
            {"id": "SC-10", "content": "所有要求签章页面已签章", "check_skill": "signature_check"},
            {"id": "SC-11", "content": "密封袋标识规范", "check_skill": "doc_integrity"},
            {"id": "SC-12", "content": "骑缝章完整", "check_skill": "signature_check"},
        ],
    },
    {
        "category": "技术与报价核查",
        "items": [
            {"id": "SC-13", "content": "所有★▲强制性参数已响应且无负偏离", "check_skill": "mandatory_req_check"},
            {"id": "SC-14", "content": "报价算术无误(单价×数量=合价)", "check_skill": "pricing_check"},
            {"id": "SC-15", "content": "投标总价未超过最高限价", "check_skill": "pricing_check"},
            {"id": "SC-16", "content": "大写金额与小写金额一致", "check_skill": "pricing_check"},
        ],
    },
    {
        "category": "有效期与合规核查",
        "items": [
            {"id": "SC-17", "content": "投标有效期≥招标要求天数", "check_skill": "validity_check"},
            {"id": "SC-18", "content": "保函有效期覆盖投标有效期", "check_skill": "validity_check"},
            {"id": "SC-19", "content": "CA证书在有效期内", "check_skill": "validity_check"},
            {"id": "SC-20", "content": "跨章节数据一致性校验通过", "check_skill": "consistency_check"},
        ],
    },
]
````

### A.10 BidPilot-AI — 추출·목차·초안 프롬프트와 补遗 규칙

#### A.10.1 항목 사실(facts) 추출

`BidPilot-AI/app/agents/__init__.py:271-284`

````python
    async def _extract_facts_from_text(self, text: str, docs: list) -> list[dict]:
        if self._has_real_llm() and text.strip():
            messages = [
                {
                    "role": "system",
                    "content": (
                        "你是投标文件解析专家。只输出JSON。"
                        "从招标文件中提取关键项目事实，字段为 facts。"
                        "每个fact包含 key,value,source_doc_id,source_page,confidence,risk_level。"
                        "key优先使用 project_name,bidder,budget,duration,deadline,deployment,warranty。"
                    ),
                },
                {"role": "user", "content": _truncate_text(text)},
            ]
````

#### A.10.2 요구사항 추출(subject/action/condition/deadline/penalty)

`BidPilot-AI/app/agents/__init__.py:374-392`

````python
    async def _extract_requirements_from_text(self, text: str, docs: list) -> list[dict]:
        if self._has_real_llm() and text.strip():
            reqs: list[dict] = []
            seen: set[str] = set()
            for chunk in _chunk_text(text):
                messages = [
                    {
                        "role": "system",
                        "content": (
                        "你是投标合规要求抽取专家。只输出JSON。"
                        "返回 requirements 数组。每项包含 text,type,mandatory,risk_level,evidence,"
                        "source_doc_id,source_page,confidence,subject,action,condition,deadline,penalty。"
                        "type只能是 qualification,technical,commercial,scoring,delivery,format。"
                        "risk_level只能是 high,medium,low。"
                        "不要把项目名称、招标人、预算、编号等纯事实抽成要求，除非文本包含投标人必须执行的动作。"
                    ),
                },
                {"role": "user", "content": chunk},
            ]
````

#### A.10.3 评分表 추출

`BidPilot-AI/app/agents/__init__.py:514-526`

````python
    async def _extract_scoring_from_text(self, text: str, docs: list) -> list[dict]:
        if self._has_real_llm() and text.strip():
            messages = [
                {
                    "role": "system",
                    "content": (
                        "你是招标评分表抽取专家。只输出JSON。"
                        "返回 scoring_items 数组。每项包含 title,score,criteria,evidence,source_doc_id,source_page。"
                        "score必须是数字，无法判断时为0。"
                    ),
                },
                {"role": "user", "content": _truncate_text(text, 14000)},
            ]
````

#### A.10.4 목차 생성

`BidPilot-AI/app/agents/__init__.py:647-664`

````python
        if self._has_real_llm() and reqs:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "你是资深投标文件大纲规划专家。只输出JSON。"
                        "根据需求生成 outline_sections 数组，每项包含 title,level,sort_order。"
                        "章节应覆盖技术、商务、实施、服务、资质与评分响应。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        [{"text": r.requirement_text, "type": r.requirement_type, "risk": r.risk_level} for r in reqs[:80]],
                        ensure_ascii=False,
                    ),
                },
            ]
````

#### A.10.5 장 초안 생성(【待确认】 규칙)

`BidPilot-AI/app/agents/__init__.py:777-787`

````python
            messages = [
                {
                    "role": "system",
                    "content": (
                        "你是资深中文投标文件撰写专家。只输出JSON。"
                        "输出 {\"content\":\"...\"}。正文使用Markdown，必须紧扣章节标题、项目事实、招标要求和知识库证据。"
                        "对缺少证据的信息使用【待确认】标记，不得编造企业资质或案例。"
                    ),
                },
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
            ]
````

#### A.10.6 补遗 사실 패턴(정규식, LLM 아님)

`BidPilot-AI/app/agents/addendum_agent.py:4-10`

````python
FACT_PATTERNS = {
    "budget": [r"(?:预算|项目预算|投资金额)[：:是为]?\s*(.+?)(?:\n|$)"],
    "duration": [r"(?:工期|建设周期)[：:是为]?\s*(.+?)(?:\n|$)"],
    "deadline": [r"(?:投标截止|截止时间|提交截止)[：:是为]?\s*(.+?)(?:\n|$)"],
    "warranty": [r"(?:质保期|维保期)[：:是为]?\s*(.+?)(?:\n|$)"],
    "deployment": [r"部署方式[：:是为]?\s*(.+?)(?:\n|$)"],
}
````

### A.11 BiaoShu-SKILL — 호스트 에이전트용 지침(코드 안에는 LLM 프롬프트 없음)

#### A.11.1 처리 단계(평가기준→목차→字数)

`BiaoShu-SKILL/BiaoShu-writer-pro/SKILL.md:232-271`

````markdown
#### 2. 评分标准提取
- 识别评分办法章节
- 提取评分大类（技术、商务、价格）
- 提取评分细则和分值权重

#### 3. 标书名称提取
- 从文件名提取项目名称
- 从内容中提取项目名称
- 格式：`{项目名称}技术标.docx`

#### 4. 大纲生成
- 根据评分标准生成4级标题大纲
- 每个评分项对应一个章节
- 字数按分值比例分配

#### 5. 内容生成
- 按章节并发编写
- 严格按评分标准编写
- 每小节 ≥ 3个独立段落
- 每章节配表格

#### 6. 字数检查
- 公式：目标字数 = 评分分值 × (总页数 ÷ 总分) × 780
- 合格范围：目标 × 0.75 ~ 1.25
- 不达标则打回重写

#### 7. AI去痕处理
- 去除AI生成痕迹
- 使内容更自然、更像人类书写
- 保留核心信息完整性

#### 8. 占位符生成
- 标记需要插入图片的位置
- 标记需要插入表格的位置
- 标记需要插入资质的位置

#### 9. Word文档生成
- Markdown转Word
- 应用行业标准格式
- 生成封面和目录
````

#### A.11.2 자리표시자 규격

`BiaoShu-SKILL/BiaoShu-writer-pro/SKILL.md:429-473`

````markdown
## 占位符规范

### 占位符类型

#### 1. 图片占位符
```
[图片占位符]
类型：技术架构图
描述：XX系统总体架构图
建议尺寸：宽15cm × 高10cm
```

#### 2. 表格占位符
```
[表格占位符]
类型：项目业绩表
描述：近3年类似项目清单
建议列数：6列
建议内容：项目名称、合同金额、完成时间、项目规模、客户名称、验收情况
```

#### 3. 资质占位符
```
[资质占位符]
类型：企业资质证书
描述：信息系统集成及服务一级资质证书
要求：有效期内的彩色扫描件
```

### 常用占位符示例

| 类型 | 占位符内容 | 使用场景 |
|------|-----------|---------|
| 图片 | [图片占位符] 类型：技术架构图 | 技术方案章节 |
| 图片 | [图片占位符] 类型：网络拓扑图 | 网络设计章节 |
| 图片 | [图片占位符] 类型：业务流程图 | 业务流程章节 |
| 表格 | [表格占位符] 类型：功能模块清单 | 功能设计章节 |
| 表格 | [表格占位符] 类型：项目进度计划表 | 项目实施章节 |
| 表格 | [表格占位符] 类型：人员配置表 | 项目团队章节 |
| 表格 | [表格占位符] 类型：项目业绩表 | 项目经验章节 |
| 资质 | [资质占位符] 类型：企业营业执照 | 附件章节 |
| 资质 | [资质占位符] 类型：信息系统集成一级资质 | 附件章节 |
| 资质 | [资质占位符] 类型：ISO9001认证证书 | 附件章节 |
| 资质 | [资质占位符] 类型：项目经理PMP证书 | 附件章节 |

````

#### A.11.3 내용 규칙과 字数 공식

`BiaoShu-SKILL/BiaoShu-writer-pro/SKILL.md:517-530`

````markdown
## 内容规则

### 基本要求
- **严格按评分标准编写** - 不泛泛而谈，针对每个评分项详细展开
- **每小节 ≥ 3个独立段落** - 确保内容充实
- **每章节配表格** - 使用Markdown表格格式
- **禁用"我方/我们"** - 用"将/项目组"替代
- **禁止金额/预算描述** - 除非招标文件明确要求

### 字数控制
- **公式**：目标字数 = 评分分值 × (总页数 ÷ 总分) × 780
- **合格范围**：目标 × 0.75 ~ 1.25
- **每页字数**：28行 × 28字 = 780字

````
