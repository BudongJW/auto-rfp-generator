# 나라장터/조달청 사업 제안서 자동생성기 관련 오픈소스·공개 코드 프로젝트 조사 (2026-11-16 기준)

> 조사 방법: GitHub Search API(저장소 검색 약 60개 키워드 조합, 코드 검색 6건)로 메타데이터(★, 최근 push일, 언어, 라이선스)를 수집하고, 주요 저장소 약 100개는 raw.githubusercontent.com에서 README 원문을 받아 읽었다. 이 세션에서는 GitHub 저장소 상세 API와 github.com HTML, www.data.go.kr 접근이 막혀 있었다. 그래서 "최근 push"는 검색 API의 `pushed_at` 값이다. 커밋 수, 이슈 수, 기여자 수는 확인하지 못했다. ★ 수와 날짜는 모두 2026-11-16에 조회한 값이다. PyPI·npm·Hugging Face는 각 레지스트리 API로 확인했다.

## Q1. 나라장터·조달청·공공입찰 제안서 생성이나 제안요청서(RFP) 분석을 직접 겨냥한 저장소 (분류 a)

### Takeaway
나라장터·공공입찰 제안서를 직접 다루는 공개 저장소는 2026년에 수십 개로 늘었다. 하지만 전부 ★0~2의 개인 PoC, 포트폴리오, 부트캠프 과제, Claude Code 스킬이다. 제안요청서(RFP) 분석부터 평가표 매핑, 목차·분량 설계, 섹션 초안, 발주처 양식(HWPX/PPTX) 출력, 평가 시뮬레이션까지 한 번에 하는 성숙한 오픈소스는 없다. 설계 참고 가치가 높은 저장소는 다음과 같다.
- nara-detector: 코드 검증과 LLM 사실성 검증을 이중으로 둔다.
- g2b-proposal-automation: 평가기준표로 레드팀 시각 검토를 한다.
- qwen-proposal-agent: 공식목차를 지키며 페이지를 설계하고 로컬 LLM으로 돌린다.
- dsi: 양식 빈칸만 채우고 PPTX 템플릿을 LLM vision으로 온보딩한다.
- bid-deep-agent, rfp-lens: 원문 근거(인용·위치)를 강제한다.

### Cited Findings

#### a-1. 나라장터·공공입찰 제안서 "초안 생성"까지 수행하는 저장소

| 프로젝트 | 스택 / 라이선스 | 최근 push / ★ | 하는 일 | LLM | 성숙도 |
|---|---|---|---|---|---|
| [nasaon/g2b-proposal-automation](https://github.com/nasaon/g2b-proposal-automation) | Python / 명시 없음 | 2026-11-10 / ★0 | 나라장터 공고 모니터링 → 참여 판단(Go/No-Go: 추정금액 상한·컨소시엄 필수·투입인력 등 하드 규칙 → 참가자격(업종코드·지역) → 적합도 점수) → 과업지시서(RFP)를 넣으면 목차·요구사항을 맞춰 섹션별 초안 생성(7단계) → .md→.docx 변환, 한컴 COM으로 .hwp/.pdf 변환 → 페이지를 PNG로 렌더해 "채점 기준표로 시각 검토(평가기준 레드팀)". 첨부(HWP/PDF)에서 배점·제출양식을 읽어 엑셀·구글시트에 정리한다. | Gemini(무료 쿼터, 건당 약 40회 호출 예산, "고배점 섹션 우선" ADR) | 개인 학습 프로젝트. "실제 입찰에 쓰이지 않았"고 심사 점수는 미확인이라고 README에 적혀 있다. 테스트 196개. |
| [realCCC/Nara-AI-Bid](https://github.com/realCCC/Nara-AI-Bid) | Python / 명시 없음 | 2026-11-14 / ★0 | 업체 프로필 인터뷰 → 수집 공고에서 참가자격 필터 → 의미 검색·리랭크·공고서 PDF RAG 근거 순위·추천 검증 → 근거·출처를 붙여 추천 → 담당자 확정 후 업체 문서 기반 제안서 초안. 전 과정 HITL. 자체 KPI는 Hit Rate@3 90%(잠정), Precision@3 0.633. | README 키워드: OpenAI/Azure OpenAI·GPT, Claude, LangGraph, pgvector, bge-m3 | PoC(KPI 측정 중) |
| [yooseungmin9/nara-detector](https://github.com/yooseungmin9/nara-detector) | Python / 명시 없음 | 2026-07-26 / ★0 | 나라장터 API 수집 → 첨부 다운로드 → HWP→PDF → 텍스트 파서와 로컬 vision LLM 두 경로로 독립 추출 → 필드 대조 → API 메타데이터 교차검증 → 사내 솔루션 매칭 → 제안서 초안 → 규칙 검증(코드) → LLM 사실성 검증(실패 시 최대 2회 재작성) → 담당자 승인 → DOCX → 이메일. 원칙은 "숫자는 코드가 계산한다", "사람 승인 없이는 아무것도 밖으로 나가지 않는다". | 이중 모델: 로컬 Ollama(대량 읽기·추출) + 클라우드 LLM(OpenAI/Claude 키워드) | PoC지만 설계가 견고하다 |
| [road2east-git/Report-Agent_00](https://github.com/road2east-git/Report-Agent_00) | Python / 명시 없음 | 2026-03-01 / ★0 | RFP PDF를 넣으면 40~80장 PPTX 입찰 제안서를 만든다. "Impact-8 Framework"(수주 제안서에서 도출한 8-Phase 구조), Win Theme 3개 전달 체인, C-E-I(주장-근거-영향) 설득 구조, Action Title, 자체 `slide_kit.py` PPTX 엔진(2,270줄, 20가지 레이아웃, 네이티브 차트) | Claude Code(Claude Pro 구독, API 키 불필요) + python-pptx | 개인 프로젝트 |
| [kyuhyoung/dsi](https://github.com/kyuhyoung/dsi) | Python / 명시 없음 | 2026-06-11 / ★0 | 다비오 사내 AI 공모전 산출물. RFP(.pdf/.docx/.hwp/.hwpx)를 넣으면 제안서(.docx/.hwpx)와 발표자료(.pptx)를 만든다. 웹앱은 "양식은 건드리지 않고 빈 셀만 채움". subagent는 rfp-analyst·proposal-writer·ppt-designer. `/onboard-template`는 LLM vision으로 회사 표준 PPTX를 분석해 `style.yaml`(표지/목차/간지/본문 매핑, 슬롯 좌표)을 자동 작성한다. | claude-agent-sdk(Claude Max 구독) | 사내 실사용 지향 공모전 산출물 |
| [iplip85-create/qwen-proposal-agent](https://github.com/iplip85-create/qwen-proposal-agent) | Jupyter/Python / 명시 없음 | 2026-08-21 / ★0 | RFP PDF → `rfp_analysis.json` → "공식목차 준수 섹션/페이지 설계"(`section_plan.json`, `slide_plan.json`) → 과거 제안서 RAG(ChromaDB) → 페이지별 내용 생성 → PPTX. 58페이지 분량을 페이지 단위로 만들고, 끊겨도 이어서 생성한다. 이유는 "공공사업 제안서는 … 클라우드 LLM에 올릴 수 없다". | 온프레미스 Ollama + Qwen(qwen2.5:3b-instruct, qwen3:8b), qwen3-embedding:0.6b | PoC |
| [jhhyun4u/-agent](https://github.com/jhhyun4u/-agent) | Python(FastAPI, uv) / 명시 없음 | 2026-04-28 / ★0 | RFP(PDF/DOCX) 업로드 또는 직접 입력 → 섹션 구조화된 용역 제안서 DOCX와 PPTX 요약본. REST API: `/api/proposals/from-rfp`, `/from-input` | Anthropic API | 최소 기능 |
| [minjisea/bidwin](https://github.com/minjisea/bidwin) | Python / 명시 없음 | 2026-05-26 / ★0 | 설명에 따르면 "낙찰률 예측 및 생성형 AI 기반의 제안서 자동 생성 end-to-end 파이프라인"이다. README가 없다. | 미확인 | 문서 없음 |
| [wgowgo/BidMate-AI](https://github.com/wgowgo/BidMate-AI) | Python / 명시 없음 | 2026-07-01 / ★0 | 중소기업용. 회사 프로필 → G2B 공공데이터 API 공고 수집 → 추천 점수 → 자격·서류·리스크·마감 요약 → 준비 체크리스트 → 제안서 개요·섹션 초안 | OpenAI GPT-4o | PoC |
| [DejaView7/korean-proposal-writer](https://github.com/DejaView7/korean-proposal-writer) | Python(스킬) / MIT | 2026-10-22 / ★0 | 공공·민간 제안서 작성 스킬. RFP 요구사항·평가항목·제출규격을 분석해 본문에 대응시키고, 제안전략·스토리보드, 약점 피드백(질문 최대 3개), 평가항목 중심 요약을 만든다. 기본 출력은 Word. 『사업 수주를 부르는 제안 필승 가이드』 발췌를 재구성했고 "확인되지 않은 실적·인증·성능"은 만들지 않는다. | 범용 에이전트용(OpenAI 언급) | 스킬 문서 위주 |
| [KAIST-Mobility-AX-Institute/Proposal_Writer](https://github.com/KAIST-Mobility-AX-Institute/Proposal_Writer) | 스킬 / 명시 없음 | 2026-07-29 / ★0 | 한글(HWP/HWPX) 양식에 맞춰 제안서·보고서·예산근거를 쓴다. 에이전트 5개가 이어 받는다: ①양식 분석가(제목·본문·표 스타일 읽기, 내어쓰기·표 음영·글자 깨짐 사전 수정) → ②조사원 → ③검증관(수치·출처·계산 반박) → ④조립공(hwpx 스킬로 양식 서식 그대로 조립) → ⑤서식 검사관(원본 양식 대조 품질 게이트) | Claude | 연구소 공개 스킬 |
| [DinN0000/bid-marketplace](https://github.com/DinN0000/bid-marketplace) (BidKit) | Claude Code 플러그인 / 명시 없음 | 2026-06-12 / ★0 | 100쪽 이상 금융 IT 기술제안서. 전략 → 목차 → 섹션 병렬 작성 → 교차 검증 → 포맷 출력을 에이전트 5개가 분업한다. "제안서 = 확정된 섹션들의 조립": 섹션마다 SSOT 파일로 상태·버전·검증 이력을 관리해 H/W 수량과 비용표 불일치 같은 섹션 간 오류를 막는다. | Claude | 플러그인 |
| [leedonwoo2827-ship-it/bid-pilot](https://github.com/leedonwoo2827-ship-it/bid-pilot) | Claude Code 플러그인 / 명시 없음 | 2026-04-14 / ★0 | 스킬 8개: analyze-rfp(요구사항·배점·자격요건 추출과 회사 데이터 대조), competitor-mapping, consortium-strategy, bid-scoring(근거 연결 자가채점·Gap·Go/No-Go), procurement-monitor, export-deliverables(마크다운 → HWP/PPT, MCP 연동) | Claude + MCP | 플러그인 |
| [delightflow/claude-codex-proposal-pingpong](https://github.com/delightflow/claude-codex-proposal-pingpong) | 스킬 / MIT | 2026-04-13 / ★0 | 한국 공공 공모전·RFP·정부 R&D 공모용. Claude↔Codex 다회차 협업 생성·평가: Gate → 10-sketch → 교차 리뷰 → 종합 → 외부 R5 리뷰, 4축 채점(문제해결·실현가능성·독창성·활용성) | Claude + OpenAI Codex | 프로토콜 문서 |

#### a-2. RFP(제안요청서) 분석, 요구사항·컴플라이언스 추출, Go/No-Go 판단

| 프로젝트 | 스택 / 라이선스 | 최근 push / ★ | 하는 일 | LLM |
|---|---|---|---|---|
| [jechoiyyy/bid-deep-agent](https://github.com/jechoiyyy/bid-deep-agent) (`bidops`) | Python / 명시 없음 | 2026-11-02 / ★0 | 공공입찰 RFP의 HWP 변환, HWPX 텍스트·표 파싱, PDF 보조 추출 → 사실 추출 → 참가자격 게이트·정량점수 → 요구사항과 역량 매핑 → 종합 권고(map-reduce 지원). 원문 인용과 위치를 추적한다. 출력은 Markdown/HTML. 인터페이스는 CLI, 대화형, A2A, 비동기 Worker. 포트폴리오용 공개 사본이다. | Anthropic |
| [Edell1/rfp-lens](https://github.com/Edell1/rfp-lens) | Python + React + Celery / 명시 없음 | 2026-08-27 / ★0 | 정부 R&D 공고문(PDF/HWPX) → 원문 근거(evidence quote + locator)가 붙은 요구사항 추출 → 사람 검토 → 컴플라이언스 매트릭스 XLSX. 검증되지 않은 근거는 자동 확정되지 않는다. ZIP 폭탄, 경로 탐색, XML 엔티티 공격을 막는다. | OpenAI API 또는 OpenAI 호환 로컬 모델(vLLM/Ollama) |
| [hskim-solv/BidMate-DocAgent](https://github.com/hskim-solv/BidMate-DocAgent) | Python / MIT | 2026-07-15 / ★1 | 한국 공공·B2B RFP용 citation-grounded **추출형** Agentic RAG. 외부 LLM 호출 없이 근거에서 claim을 추출하고 citation을 잠근다. 메타데이터 우선 검색, 비교 질의 균형 top-k, bootstrap-CI 평가, ADR 기반 | (외부 LLM 미사용 설계) |
| [Hadol2/Radar](https://github.com/Hadol2/Radar) (RFP Radar) | TypeScript / 명시 없음 | 2026-10-04 / ★0 | RFP를 붙여넣거나 업로드하면 탭 4개를 만든다: Executive Summary(범위·산출물·일정·평가기준·제출 체크리스트), Clarifying Questions(섹션 인용), Proposal Outline(RFP 요구 구조 반영), Go/No-Go | `LLM_PROVIDER=anthropic` 또는 openai |
| [mimo626/g2b-itcen-bid-crawler](https://github.com/mimo626/g2b-itcen-bid-crawler) | Jupyter / 명시 없음 | 2026-06-24 / ★2 | 조달청 API로 IT/SI 공고를 수집한다. 8자리 세부품명 분류로 계열사별 필터링을 하고, 첨부에 '입찰공고문'과 '제안요청서'가 둘 다 있는 공고(협상에 의한 계약 등 대형 사업)만 추출해 다운로드 링크와 함께 엑셀로 낸다. | 없음 |
| [malkang92/gov-bid-rfp-topic-modeling](https://github.com/malkang92/gov-bid-rfp-topic-modeling) | – / 명시 없음 | 2025-12-25 / ★0 | 조달청 나라장터 API로 차세대 구축사업 RFP 요구사항을 추출하고 LDA 토픽 모델링을 한다. README가 없다. | 없음(LDA) |
| [jskim3889/rfp-bid-review](https://github.com/jskim3889/rfp-bid-review) | HTML + SKILL.md | 2026-10-29 / ★0 | KAIST ITM.690 과제. 입찰 공고·RFP 유불리 분석 스킬이며, `olefile`로 HWP·HWPX 텍스트를 추출한다. | 에이전트 스킬 |
| [chrismarspink/rfp-finder](https://github.com/chrismarspink/rfp-finder) | Python / 명시 없음 | 2026-05-27 / ★0 | 나라장터(G2B)·NTIS·IITP·KISA 공고 수집 → 규칙 점수와 로컬 LLM 요약·적합성 판단 → XLSX(통계)와 PPTX(경영진 보고) → 사내 SMTP 발송. 전부 사내(self-hosted)에서 돈다. | Ollama(Qwen 등), bge-m3 |
| [seojihan/Autonomous-Public-Procurement-Intelligence-Agent](https://github.com/seojihan/Autonomous-Public-Procurement-Intelligence-Agent) (BidRadar AI) | n8n 워크플로 | 2026-09-01 / ★0 | KONEPS 공고 수집 → 원문 RFP와 교차검증 → 일일 전략 리포트 메일. 고등학생 개인 프로젝트다. | Google Gemini, LangChain |
| 코드잇 AI 10기 '입찰메이트' 시나리오 RAG 과제군: [Daybreak53/RFP-RAG-Assistant](https://github.com/Daybreak53/RFP-RAG-Assistant), [wjdtmdgh87-lgtm/its-mine-rfp-rag](https://github.com/wjdtmdgh87-lgtm/its-mine-rfp-rag)(원본 [Codeit-Part3-6Team/Codeit-Part3-6Team-Project](https://github.com/Codeit-Part3-6Team/Codeit-Part3-6Team-Project)), [Codeit-AI10-Part3-4Team/intermediate-project](https://github.com/Codeit-AI10-Part3-4Team/intermediate-project)(MIT), [kwmin122/RAG_RFX](https://github.com/kwmin122/RAG_RFX)(MIT) | Python | 2025-11~2026-10 / ★0 | 시나리오는 "공공입찰 컨설팅 스타트업 '입찰메이트'"의 사내 RAG다. 나라장터 RFP(PDF·HWP)와 CSV 메타데이터를 매칭하고, 청킹 3종(Recursive/Semantic/Sentence), Qdrant Dense+Sparse 하이브리드, HWP5 파싱·BM25·RRF, citation 답변을 구현했다. | GPT, EXAONE·Llama(Ollama), bge-m3, LangChain, Chroma/Qdrant |

#### a-3. 제안서 "서식·템플릿 반영" 특화 (공공 전용은 아님)
- [Kevinatkorea/ai_pptx](https://github.com/Kevinatkorea/ai_pptx) "Proposal Factory"(★0, 2026-10-10, NOASSERTION): 고객 초안을 사내 표준 PPTX 템플릿에 반영하고 페이지 레이아웃 결함을 누적 학습한다. 학습 공장(AI, 비보안망)과 현장 엔진(결정론, 보안망, 런타임 AI 호출 0)을 분리했다. 지능은 3단(결정론 → 로컬 Ollama → Claude API 월 예산 상한)이다. 입력은 PDF·HWP·HWPX.
- [chatdaeri/k-proposal-pptx](https://github.com/chatdaeri/k-proposal-pptx)(★0, 2026-04-29): "한국식 제안서 문법" PPT를 12~18장, 슬라이드 템플릿 39개, Pretendard 폰트로 만드는 Claude Code 플러그인이다. 국내 B2B 영업용이며 공공입찰 전용은 아니다.

#### 검색 규모 (2026-11-16 GitHub 저장소 검색 total_count)
- "나라장터" 195, "입찰공고" 60, "조달청" 48, "narajangteo" 41, "koneps" 26, "제안요청서" 15, "RFP 분석" 11, "공공입찰" 9, "나라장터 제안서" 3, "제안서 자동생성" 4, "입찰 제안서" 3. — [GitHub 검색: 나라장터](https://github.com/search?q=%EB%82%98%EB%9D%BC%EC%9E%A5%ED%84%B0&type=repositories), [GitHub 검색: 제안요청서](https://github.com/search?q=%EC%A0%9C%EC%95%88%EC%9A%94%EC%B2%AD%EC%84%9C&type=repositories)
- 정부지원사업 사업계획서 자동생성기(예비/초기창업패키지, Claude API·Streamlit/Flask)도 있다: [chewni33-ship-it/startup-business-plan-generator](https://github.com/chewni33-ship-it/startup-business-plan-generator), [daniel8824-del/bizplan-generator](https://github.com/daniel8824-del/bizplan-generator)(MIT), [moodmaker1/bizplan-ai](https://github.com/moodmaker1/bizplan-ai). 모두 ★0이고 2026년 생성이다.
- 정부 R&D 제안서 보조: [cozy104-glitch/claude-RnD](https://github.com/cozy104-glitch/claude-RnD)(Next.js 16 + Claude API), [gisbi-kim/research-proposal-compass](https://github.com/gisbi-kim/research-proposal-compass)(가이드).

### Inferences
- 나라장터 제안서 자동화 오픈소스는 2026년에 Claude Code·에이전트 스킬 붐과 함께 폭발적으로 생겼다. 그러나 커뮤니티 검증(★, 포크, 이슈)이 된 레퍼런스 구현은 없다. 그대로 쓸 수 있는 라이브러리보다 아키텍처 아이디어를 가져올 원천으로 보는 편이 맞다.
- 반복해서 나타나는 설계 패턴은 다음과 같다.
  - (1) 공고 수집 → 자격 게이트 → 적합도 → 초안의 깔때기 구조
  - (2) 수치·날짜는 코드가 판정하고 LLM은 서술만 맡기는 분리(nara-detector)
  - (3) 원문 인용·위치 강제(rfp-lens, bid-deep-agent, BidMate-DocAgent)
  - (4) 공식목차·페이지 예산을 먼저 설계(qwen-proposal-agent)
  - (5) 양식 보존형 "빈칸 채우기"(dsi, Proposal_Writer)
  - (6) 평가기준표 기반 레드팀 검토(g2b-proposal-automation)
  - (7) 보안 때문에 로컬 LLM을 쓰거나 혼합(qwen-proposal-agent, ai_pptx, rfp-finder)
- 출력 포맷은 둘로 갈린다. 기술제안서 본문은 PPTX(40~80장), 서식·별지·요약서는 HWP/HWPX/DOCX다. 둘을 모두 발주처 양식에 맞춰 내는 프로젝트는 dsi 정도뿐이다.

### Gaps
- 저장소 상세 API가 막혀 있어 커밋 수, 기여자 수, 이슈 활동을 확인하지 못했다. 활동성은 `pushed_at`만으로 판단했다.
- 이 저장소들의 산출물이 실제 조달청 기술평가에서 받은 점수를 공개한 사례는 찾지 못했다. g2b-proposal-automation은 점수를 "확인하지 못했다"고 명시한다.
- README가 없는 저장소(bidwin, BudongJW/proposal-helper, malkang92, jeonck/it-audit-proposal)는 코드를 직접 보지 않아 기능을 확인하지 못했다.

## Q2. 나라장터 입찰공고·사전규격 수집기와 공공데이터포털 조달청 OpenAPI 래퍼 (분류 b)

### Takeaway
차세대 나라장터 전환 이후의 신규 OpenAPI 경로(`apis.data.go.kr/1230000/ad|ao|as/...`)는 이미 공개 코드에 널리 퍼져 있다. 2026년에는 MCP 서버 형태(로컬, 원격, 무키)가 표준 패턴이 됐다. 이 중 조달청 14개 서비스 156개 오퍼레이션을 감싼 mcp-kr-g2b가 커버리지가 가장 넓고, 첨부(제안요청서) 다운로드·본문 추출까지 하는 narajangteo-bid-mcp와 narajangteo_mcp_server가 제안서 생성기의 입력단으로 가장 쓸모 있다. 2017~2023년의 화면 스크래핑 크롤러(★ 상위권)는 구 나라장터 기준이라 사실상 폐기 상태다.

### Cited Findings

#### b-1. 조달청 OpenAPI 서비스명·엔드포인트 (공개 코드·README에서 확인)

| 서비스(공공데이터포털 명칭) | 신규 엔드포인트(차세대) | 근거 |
|---|---|---|
| 조달청_나라장터 입찰공고정보서비스 (`BidPublicInfoService`, 데이터번호 15129394) | `https://apis.data.go.kr/1230000/ad/BidPublicInfoService` (예: `getBidPblancListInfoServcPPSSrch` = 용역 공고 PPS 검색) | [yonghwan86/narajangteo-searcher](https://github.com/yonghwan86/narajangteo-searcher), [opendata-kr/narajangteo-bid-mcp](https://github.com/opendata-kr/narajangteo-bid-mcp), [Datajang/narajangteo_mcp_server](https://github.com/Datajang/narajangteo_mcp_server) |
| 조달청_나라장터 사전규격정보서비스 (`HrcspSsstndrdInfoService`) | `https://apis.data.go.kr/1230000/ao/HrcspSsstndrdInfoService` (예: `getPublicPrcureThngInfoServcPPSSrch`). 입찰공고와 별도로 활용신청해야 한다. | [Datajang/narajangteo_mcp_server](https://github.com/Datajang/narajangteo_mcp_server) |
| 조달청_나라장터 낙찰정보서비스 (`ScsbidInfoService`, 데이터번호 15129397) | `.../1230000/as/ScsbidInfoService`. 공고당 개찰 1순위 1개사만 준다. | [yonghwan86/narajangteo-searcher](https://github.com/yonghwan86/narajangteo-searcher); 코드 검색 결과 81건 |
| 조달청_나라장터 공공데이터개방표준서비스 (`PubDataOpnStdService`) | `.../1230000/ao/PubDataOpnStdService` | [ChloePark85/g2b-cli](https://github.com/ChloePark85/g2b-cli), [TaeyanG4/koneps-procurement-intelligence](https://github.com/TaeyanG4/koneps-procurement-intelligence); 코드 검색 결과 66건 |
| 계약정보서비스 (`CntrctInfoService`) | (경로 미확인) | [ChloePark85/g2b-cli](https://github.com/ChloePark85/g2b-cli) |

- GitHub 코드 검색(2026-11-16) 히트 수:
  - `"1230000/ad/BidPublicInfoService"` 241건
  - `"1230000/ao/HrcspSsstndrdInfoService"` 144건
  - `"1230000/as/ScsbidInfoService"` 81건
  - `"1230000/ao/PubDataOpnStdService"` 66건
  - 구형 `"1230000/BidPublicInfoService04"` 36건(예: 2023년 [tobornot2b/Narabot](https://github.com/tobornot2b/Narabot), [kwmin122/M-S-Dataworks](https://github.com/kwmin122/M-S-Dataworks))
  - — [GitHub 코드 검색](https://github.com/search?q=%221230000%2Fad%2FBidPublicInfoService%22&type=code)
- opendata-kr/narajangteo-bid-mcp는 기본 URL을 `https://apis.data.go.kr/1230000/ad/BidPublicInfoService`로 두고 도구 10개를 제공한다. 공사·용역·물품·외자 4구분을 병렬 검색하고, 첨부 ZIP을 펼쳐 HWPX·구형 HWP·구형 DOC 본문을 읽는다. 기초금액·예비가격범위율·낙찰가 산식A·평가주력분야도 조회한다. — [opendata-kr/narajangteo-bid-mcp](https://github.com/opendata-kr/narajangteo-bid-mcp)
- 차세대 나라장터 일정: 2024-12-30 기사는 "20년 된 나라장터, 상반기 차세대 시스템으로 새단장"이라고 예고했다 — [뉴스핌](https://newspim.com/news/view/20241230000772). 이후 12개 기관 자체 전자조달시스템을 차세대 나라장터로 통합 완료했다는 보도가 있다 — [보안뉴스](https://m.boannews.com/html/detail.html?idx=140366). 이 기사들은 웹 검색 요약으로만 확인했고 원문은 열지 않았다.

#### b-2. 수집기·API 래퍼·MCP 서버 카탈로그

| 프로젝트 | 스택 / 라이선스 | 최근 push / ★ | 범위·특징 | 차세대 API |
|---|---|---|---|---|
| [ChangooLee/mcp-kr-g2b](https://github.com/ChangooLee/mcp-kr-g2b) | (Python 추정) / NOASSERTION | 2026-06-20 / ★1 | 나라장터와 누리장터(민간조달) OpenAPI MCP. **조달청 14개 서비스·156개 오퍼레이션**: 입찰공고·사전규격·낙찰·계약·발주계획·가격정보·공공조달통계 | `HrcspSsstndrdInfoService` 사용 확인(코드 검색) |
| [opendata-kr/narajangteo-bid-mcp](https://github.com/opendata-kr/narajangteo-bid-mcp) (+ [narajangteo-opening-mcp](https://github.com/opendata-kr/narajangteo-opening-mcp): 낙찰정보) | TypeScript / MIT | 2026-10-11 / ★0, npm `@opendata-kr/narajangteo-bid-mcp` 0.6.0(2026-07-14) | 위 b-1 참조. 첨부 다운로드·본문 읽기 도구가 있다. | `/ad/` 사용 |
| [Datajang/narajangteo_mcp_server](https://github.com/Datajang/narajangteo_mcp_server) | Python / NOASSERTION | 2026-05-12 / ★5 | 용역 입찰공고와 사전규격을 통합 검색한다. 예산·마감 상태를 표시하고, RFP를 자동 다운로드해 텍스트를 추출한다(HWP/HWPX/PDF/DOCX/XLSX/ZIP). 제안요청서·과업지시서만 걸러 내고, 부서 프로필 기반으로 추천한다. | `/ad/`, `/ao/` 사용 |
| [alphago2580/naramarketmcp](https://github.com/alphago2580/naramarketmcp) | Python(FastMCP 2.0) / Apache-2.0 | 2026-02-09 / ★5 | 도구 15~16개: 입찰공고, 낙찰, 계약, 조달통계, 물품목록, 종합쇼핑몰, 공공데이터개방표준 API. Smithery 배포 | 개방표준 사용 |
| [nine-hundred/naramarket-mcp](https://github.com/nine-hundred/naramarket-mcp) | Go(mcp-go) / 명시 없음 | 2025-05-11 / ★5 | 입찰공고 기간·키워드 검색 MCP | `PubDataOpnStdService` 사용(코드 검색) |
| [Jaem-Shin/bid-radar](https://github.com/Jaem-Shin/bid-radar) | JavaScript / NOASSERTION | 2026-10-15 / ★0 | **G2B**(입찰공고·낙찰·사전규격·사용자정보)와 **D2B 국방전자조달**(방위사업청 시설 공사·용역: 조달계획·입찰공고·입찰결과·계약정보) MCP 2종. 개찰 순위표, 복수예비가격, [NOT_FOUND]·불일치 표시 | 본인 data.go.kr 키 |
| [donghyeon01/kr-public-mcp](https://github.com/donghyeon01/kr-public-mcp) | TypeScript(Cloudflare Workers) / MIT | 2026-10-22 / ★0 | 원격 MCP(설치·키 불필요). 입찰공고·사전규격·낙찰정보, 응답마다 원문 링크 | – |
| [00data-kr/narajangteo-mcp](https://github.com/00data-kr/narajangteo-mcp) (공공일감) | 호스팅 원격 MCP / MIT(문서) | 2026-10-24 / ★1 | 나라장터·누리장터·국방전자조달·LH·K-water·한전·가스공사 공고. 지역·업종 제한을 대조하고, HWP·PDF 제안요청서에서 과업·배점을 읽는다. 저장소는 README뿐이고 서버 코드는 비공개로 보인다. | – |
| [pipeworx-io/mcp-korea-tenders](https://github.com/pipeworx-io/mcp-korea-tenders) | JavaScript / MIT | 2026-11-09 / ★0 | KONEPS·국방전자조달·LH·K-water·누리장터. BOIM(boim.io) 수집 데이터 경유 | `/ad/` 사용 |
| [yonghwan86/narajangteo-searcher](https://github.com/yonghwan86/narajangteo-searcher) | TypeScript / MIT | 2026-06-22 / ★1 | Windows EXE와 MCP 서버. IT 공고 필터, 적합도 점수, 개찰결과 전체 투찰자 조회(나라장터 화면 경유, 실패 시 OpenAPI 폴백), 9섹션 입찰 검토 메모 | 15129394/15129397 |
| [ChloePark85/g2b-cli](https://github.com/ChloePark85/g2b-cli) | Shell / MIT | 2026-04-30 / ★0 | 입찰공고·계약·개방표준 통합 JSONL CLI | ✓ |
| [solid-hwan/nara-data-collector](https://github.com/solid-hwan/nara-data-collector) | Python / MIT | 2026-10-26 / ★0 | v0.5.1. 공고·**발주계획** 검색과 기간별 수집, Excel/CSV, MCP 겸용. 첨부 HWP/PDF 분석과 추천 점수는 제공하지 않는다. | – |
| [jacking7/G2B-BID-REPORT](https://github.com/jacking7/G2B-BID-REPORT) | TypeScript(Node ≥20) / MIT | 2026-06-24 / ★1 | 셀프호스팅 웹 콘솔. 키워드 필터, Excel, 이메일 리포트 | `/ao/HrcspSsstndrd...` 사용(코드 검색) |
| [SSEUNGSSEUNGWOO/g2b-monitor](https://github.com/SSEUNGSSEUNGWOO/g2b-monitor) | Next.js + Python / 명시 없음 | 2026-05-04 / ★0 | 입찰공고·사전규격·발주계획 → PostgreSQL(Neon) 모니터링 | ✓ |
| [CloudCorpRecords/procureport](https://github.com/CloudCorpRecords/procureport) | TypeScript / MIT | 2026-11-02 / ★0 | 단일 바이너리 CLI와 stdio MCP. 공고·낙찰·계약·통계·물품·쇼핑몰 | base URL 설정형 |
| [han-nakta/g2b-mcp](https://github.com/han-nakta/g2b-mcp) | Python / MIT | 2026-11-10 / ★0 | v0.3.4 alpha. G2B OpenAPI 카탈로그·관계 그래프·온톨로지 MCP | – |
| [Koomook/data-go-mcp-servers](https://github.com/Koomook/data-go-mcp-servers) | Python / Apache-2.0 | 2025-09-16 / ★392 | data.go.kr API MCP 서버 모음(조달 개방표준 포함, 코드 검색 기준) | 개방표준 |
| [leokim90/gov-data-mcp](https://github.com/leokim90/gov-data-mcp) | JavaScript / MIT | 2026-09-17 / ★3 | 중기부·정부24·기업마당·나라장터·중소벤처24, 5종 통합 MCP | – |
| [TaeyanG4/koneps-procurement-intelligence](https://github.com/TaeyanG4/koneps-procurement-intelligence) | Python / 명시 없음 | 2026-10-01 / ★0 | Kaggle 공개용 KONEPS 재현 ETL | 개방표준 |
| [iltabid/g2b-bid-calculator](https://github.com/iltabid/g2b-bid-calculator) | Python / MIT | 2026-09-07 / ★0 | 적격심사 투찰하한가·복수예가(4/15 평균)·적격점수 계산. README는 `pip install g2b-bid-calculator`를 안내하지만 PyPI에서는 404였다([PyPI](https://pypi.org/project/g2b-bid-calculator/)). | – |

- 오래된 화면 스크래핑 크롤러는 구 나라장터 URL 기반이라 지금은 쓸 수 없을 가능성이 높다.
  - [seoweon/narajangteo](https://github.com/seoweon/narajangteo): ★16으로 나라장터 키워드 최다지만 마지막 push가 2018-11이다.
  - [pgs2285/g2b_webcrawling](https://github.com/pgs2285/g2b_webcrawling): ★5, BeautifulSoup+PyQt5, 2024-01.
  - [tobornot2b/Narabot](https://github.com/tobornot2b/Narabot): ★4, 텔레그램 알림, 2023-08.
  - [medAndro/KONEPS-Info-Crawler](https://github.com/medAndro/KONEPS-Info-Crawler): 품명설명, 2022.
  - [starrything/koneps-api](https://github.com/starrything/koneps-api): 2022.
  - [whan1569/nara](https://github.com/whan1569/nara): Selenium·PyAutoGUI·Google Vision OCR.
- 입찰 추천·낙찰 분석:
  - [DrunkJin/bidmate](https://github.com/DrunkJin/bidmate): 소규모 사업자 맞춤 추천, ★1
  - [SimGGG/bid-pattern-analyzer](https://github.com/SimGGG/bid-pattern-analyzer): 낙찰정보 API로 경쟁사 투찰패턴 분석
  - [code920309/g2b-bid-strategy-ml](https://github.com/code920309/g2b-bid-strategy-ml): IT 사업 낙찰 확률·투찰가 예측, MIT
  - [kimminkyung05/koneps-fraud-detection](https://github.com/kimminkyung05/koneps-fraud-detection): 불공정 조달행위 탐지
- 공고 법령 위반 탐지: 2026년 DACON "나라장터 자체입찰 공고 법령 위반사항 모니터링 AI 경진대회"(행정안전부·NIA 주최, 조달청 참여, 2026-08-26~09-30, 총상금 4,200만원)의 참가 저장소들이 있다 — [PyTorchKR 공지](https://discuss.pytorch.kr/t/ai-9-30/11663).
  - [Hangi-n42/g2b-bid-monitoring-ai](https://github.com/Hangi-n42/g2b-bid-monitoring-ai): MIT. 공고·첨부·등록 메타데이터로 "24개 항목 위반 여부와 원문 근거"를 출력하는 Gemma(vLLM) 추론 파이프라인
  - [ClearSky001/KONEPS_Legal_Violation_Monitoring_AI_Competition](https://github.com/ClearSky001/KONEPS_Legal_Violation_Monitoring_AI_Competition): MIT
  - [stevenkim18/dacon_koneps](https://github.com/stevenkim18/dacon_koneps)
  - [jwj51720/pps-bid-compliance-ai](https://github.com/jwj51720/pps-bid-compliance-ai)
- 누리장터 수집기: [froggy-hyun/nuri_crawler](https://github.com/froggy-hyun/nuri_crawler), [hskhsmm/reco-bid-collector](https://github.com/hskhsmm/reco-bid-collector)(Spring Boot + Selenium).

### Inferences
- 차세대 경로(`/ad/`, `/ao/`, `/as/`) 사용 코드는 구형 `BidPublicInfoService04`보다 6배 이상 많다(241 대 36). 활발한 2026년 프로젝트는 대부분 차세대 API에 대응했다고 볼 수 있다. ★가 높은 구형 크롤러는 참고하지 말아야 한다.
- 입찰공고와 사전규격이 별도 서비스로 나뉘어 있어 활용신청을 따로 해야 한다(Datajang README). 그래서 생성기는 사전규격 단계에서 RFP 초안을 미리 받아 제안 준비를 앞당기는 기능을 차별점으로 삼을 수 있다.
- 제안서 생성기의 입력 파이프라인(공고 → 첨부 ZIP → HWP/HWPX 본문)은 opendata-kr/narajangteo-bid-mcp(TypeScript, MIT)와 Datajang 서버(Python)를 참고하거나 재사용하면 빠르게 만들 수 있다. 라이선스 면에서는 MIT·Apache-2.0 프로젝트가 안전하다.

### Gaps
- www.data.go.kr이 이 세션 네트워크에서 차단돼 공공데이터포털 원문(서비스명, 오퍼레이션 목록, 트래픽 한도, 구 API 폐기일)은 직접 확인하지 못했다. 위 서비스명과 데이터번호는 공개 저장소 README를 근거로 했다. 원문 확인이 필요하면 세션 네트워크 설정에서 www.data.go.kr을 허용해야 한다.
- 차세대 나라장터 정확한 개통일과 구 OpenAPI 폐기일은 1차 자료로 확인하지 못했다. 과제 설명에는 "2024년 개통"으로 되어 있지만, 검색된 2024-12-30 기사는 2025년 상반기 전환을 예고하고 있어 원문 확인이 필요하다.
- 첨부파일(제안요청서) 다운로드 URL이 OpenAPI 응답 필드로 안정적으로 제공되는지, 로그인이 필요한지는 프로젝트마다 다르게 처리하고 있다. 공식 명세는 확인하지 못했다.
- 국방전자조달(D2B) 전용 오픈소스는 bid-radar 외에는 거의 없다(GitHub "국방전자조달" 검색 결과 1건).

## Q3. HWP/HWPX 생성·파싱 오픈소스 현황, 한컴 공식 스펙·SDK·MCP, PPTX/DOCX 생성 (분류 c)

### Takeaway
2026년 들어 HWPX 쓰기 지원은 크게 성숙했다. Python만으로 스타일, 개요 번호, 표(병합), 머리말·꼬리말, 각주, 목차를 가진 HWPX를 만들 수 있다(python-hwpx 6.12.0, 2026-11-11 릴리스). Rust/WASM 계열(rhwp ★4,138, HwpForge, auto-hwp)과 TypeScript 계열(kordoc ★3,000)은 HWP5까지 저장·변환한다. 다만 "한컴오피스에서 연 결과와 픽셀 수준으로 같다"는 보장은 각 프로젝트의 자체 검증뿐이다. 한컴의 공식 오픈소스는 OWPML 모델과 DVC(2023년 정체), PDF용 OpenDataLoader에 그친다. HWPX 공식 SDK나 MCP는 찾지 못했다.

### Cited Findings

#### c-1. HWPX/HWP 쓰기(생성·편집) 가능 라이브러리

| 프로젝트 | 스택 / 라이선스 | 최근 push / ★ / 배포 | 쓰기 기능 요약 | 한컴오피스 필요 |
|---|---|---|---|---|
| [airmang/python-hwpx](https://github.com/airmang/python-hwpx) | Python(의존성 `lxml` 하나) / Apache-2.0 | 2026-11-16 / ★125 / [PyPI python-hwpx 6.12.0](https://pypi.org/project/python-hwpx/)(2026-11-11, 릴리스 80회) | `HwpxDocument.new()`, `add_heading`, `add_paragraph(style="개요 2")`(한/글이 "가." 번호 부여), `add_table` / 셀 병합·분할, 머리말·꼬리말·각주·메모, 줄 간격·여백·쪽 번호, 목차·상호 참조, 문서 비교, 변경 추적. HWP 5.0도 같은 API로 열어 HWPX로 변환한다. 생성 문서를 "한컴오피스 2024에서 직접 열어 보고" 날짜와 함께 기록한다. | 불필요(Win/Mac/Linux/CI) |
| [airmang/python-hwpx-automation](https://github.com/airmang/python-hwpx-automation) | Python / Apache-2.0 | 2026-11-16 / ★69 / [PyPI hwpx-mcp-server 7.5.0](https://pypi.org/project/hwpx-mcp-server/)(2026-11-11, 96 릴리스) | python-hwpx 위의 저작·양식 채움(`fill_by_path` 이름표 기반 칸 찾기)·MCP 서버 | 불필요 |
| [edwardkim/rhwp](https://github.com/edwardkim/rhwp) | Rust + WASM / MIT | 2026-11-16 / ★4,138(2026-03-27 생성) / npm [@rhwp/core 0.9.0](https://www.npmjs.com/package/@rhwp/core)(2026-11-08) | HWP 5.0/HWPX 파서·렌더러·웹 에디터. 문단·표·수식·이미지·차트, 페이지네이션(다단, 표 행 분할), 머리말·꼬리말·바탕쪽·각주, 표 생성·행열 삽입·셀 수식, HML 가져오기, loss-safe HWP/HWPX 저장, PDF 내보내기, **hwpctl 호환 API(한컴 웹기안기 호환, 30 Actions, Field API)**, VS Code 확장. README의 이정표는 "역공학 완성, 읽기/쓰기 기반 구축"이다. | 불필요 |
| [chrisryugj/kordoc](https://github.com/chrisryugj/kordoc) | TypeScript / MIT | 2026-11-16 / ★3,000 / npm [kordoc 4.24.81](https://www.npmjs.com/package/kordoc)(2026-11-16), PyPI kordoc 0.2.1 | HWP3~5·HWPX·PDF·오피스·OCR → Markdown. **Markdown → HWPX·HWP 작성**(공문서 프리셋, `--template` 부서 서식 견본, 표·수식·차트), HWP→HWPX 서식 보존 변환, 누름틀 양식 채우기, 표기법·공공언어·AI 문체·예산 산출근거 검산 검수. 라이브러리·CLI·MCP(공식 MCP 레지스트리 등록). 자체 벤치마크는 "HWPX 2,424문서·10,342표 구조 일치 100%". | 불필요(HWP 출력은 @rhwp/core 사용) |
| [ai-screams/HwpForge](https://github.com/ai-screams/HwpForge) | Rust(+Python 바인딩) / Apache-2.0 | 2026-11-16 / ★20 / [PyPI hwpforge 0.20.0](https://pypi.org/project/hwpforge/)(2026-11-07) | 한글 2014~2025+ HWPX 읽기·쓰기, 스타일 세트(Classic 18 / Modern 22 / Latest 23), GFM Markdown↔HWPX 양방향, YAML 스타일 템플릿(폰트·크기·색), JSON 라운드트립, MCP(베타, `hwpforge_restyle` 등) | 불필요 |
| [neolord0/hwplib](https://github.com/neolord0/hwplib) / [hwpxlib](https://github.com/neolord0/hwpxlib) / [hwp2hwpx](https://github.com/neolord0/hwp2hwpx) | Java / Apache-2.0 | 2026-09-11 / 2026-08-31 / 2026-10-26; ★587 / 187 / 61 | 가장 오래된 HWP·HWPX 읽기·쓰기 라이브러리. 한컴 공개 '한글 문서 파일 구조 5.0'과 OWPML 문서를 기반으로 한다. 이를 기반으로 한 상용 제품도 있다고 README에 적혀 있다. | 불필요 |
| [msjang/pypandoc-hwpx](https://github.com/msjang/pypandoc-hwpx) | Python(Pandoc AST) / MIT | 2025-12-18 / ★187 / PyPI 0.1.1 | md·html·docx → hwpx. 셀 병합 표와 이미지를 지원하고, 참조용 `blank.hwpx`의 스타일·여백을 복제한다. | 불필요 |
| [UpstageAI/korean-report-hwpx](https://github.com/UpstageAI/korean-report-hwpx) | Python / MIT | 2026-11-14 / ★23 | 공문서 MCP. **52개 중앙행정기관 보도자료 서식**, 42개 기관 보고서 규칙(□→ㅇ→- 개조식, 표 스타일, 붙임), 기안문(행정업무규정 별지 제1호서식). 구조 JSON → HWPX. 분량(`target_pages`)을 점검한다. 로컬 실행, 외부 호출 없음. | 불필요 |
| [jkf87/hwpx-skill](https://github.com/jkf87/hwpx-skill) | Python / 명시 없음 | 2026-10-31 / ★309 | 에이전트 스킬. 버전 있는 JSON 명세로 공문·요약보고·기본계획을 생성하고 검증한다(바이트 재현성). Windows에서는 설치된 한컴 엔진으로 HWP→HWPX 변환 | 선택 |
| [Canine89/hwpxskill](https://github.com/Canine89/hwpxskill) | Python / 명시 없음 | 2026-06-27 / ★337 | OWPML XML을 직접 다뤄 원본 서식·표 구조·셀 병합·여백을 보존하고 내용만 교체한다. `page_guard.py`가 원본 대비 페이지 수 변화를 감지한다. charPr/paraPr 단위로 제어 | 불필요 |
| [BlackBuddle/hwpx-docs](https://github.com/BlackBuddle/hwpx-docs) | Python 표준 라이브러리만 / AGPL-3.0 | 2026-11-15 / ★15 | JSON 스펙 하나로 글자·문단 모양, 사용자 스타일, 셀 병합·셀별 선·채움 표, 도형, 글상자, 수식, 한글 차트, 머리말·꼬리말, 쪽 번호, 각주, 차례, 누름틀, 변경 추적을 생성한다. HWPX → 스펙 역변환 | 불필요 |
| [kist-aix/hwpx](https://github.com/kist-aix/hwpx) | Python / MIT | 2026-07-01 / ★20 | 공공기관 보고서 양식(머리말·제목 도형·□ 항목) 스킬. 표 5종(일반·현황·예산·일정·점검) | 불필요 |
| [kwakseongjae/auto-hwp](https://github.com/kwakseongjae/auto-hwp) | Rust/wasm + React / Apache-2.0 | 2026-11-16 / ★42 | 브라우저·셀프호스팅 HWP·HWPX 편집, PDF/HWPX 내보내기, 양식 일괄 작성, CLI·MCP | 불필요 |
| [ohah/hwpjs](https://github.com/ohah/hwpjs) | JS/WASM / MIT | 2026-11-15 / ★159 / npm @ohah/hwpjs 0.1.1(2026-11-08) | HWP5·HWPX 읽기·편집·저장 ESM, 저수준 CFB 읽기·쓰기 | 불필요 |
| MCP 서버: [treesoop/hwp-mcp](https://github.com/treesoop/hwp-mcp)(MIT, ★107, rhwp WASM 기반, 도구 34개, Mac/Linux 가능), [Dayoooun/hwpx-mcp](https://github.com/Dayoooun/hwpx-mcp)(MIT, ★36, 도구 125개, npm @kimdayoun/hwpx-mcp 0.3.7), [DoHyun468/claw-hwp](https://github.com/DoHyun468/claw-hwp)(MIT, ★223) | – | 2026-11 | AI 에이전트에서 HWP/HWPX 읽기·수정·생성 | 대부분 불필요(PDF 내보내기는 일부 한컴 엔진 필요) |
| Windows COM 자동화: [martiniifun/pyhwpx](https://github.com/martiniifun/pyhwpx)(MIT, ★60, [PyPI 1.7.2](https://pypi.org/project/pyhwpx/) 2026-03-19, 릴리스 464회), [JunDamin/hwpapi](https://github.com/JunDamin/hwpapi)(MIT, ★36, PyPI 3.0.0 2026-04-29), [jkf87/hwp-mcp](https://github.com/jkf87/hwp-mcp)(★270, Windows + 한글 필수) | Python(pywin32, `HWPFrame.HwpObject`) | – | 한글 프로그램을 원격 조종한다. 가장 정확한 렌더링을 얻지만 Windows와 라이선스가 필요하다. | **필요** |

#### c-2. 읽기·변환 전용 (RFP 파싱용)
- [hahnlee/hwp.js](https://github.com/hahnlee/hwp.js)(Apache-2.0, ★1,306): 마지막 push 2025-01-10이고 npm 최신 0.0.3은 2020-10에 나왔다. 뷰어·파서만 있어 사실상 정체 상태다.
- [mete0r/pyhwp](https://github.com/mete0r/pyhwp)(★303): PyPI 최신 0.1b15가 2020-05-30이다 — [PyPI](https://pypi.org/project/pyhwp/). HWP v5 파서이며 릴리스가 정체됐다.
- [Indosaram/hwpers](https://github.com/Indosaram/hwpers)(Rust, MIT, ★191)와 [openhwp/openhwp](https://github.com/openhwp/openhwp)(Rust, MIT, ★93, 2025-12): HWP5 파서, HWPX 읽기·쓰기 crate.
- [roboco-io/hwp2md](https://github.com/roboco-io/hwp2md)(Go, MIT, ★118): HWP/HWPX → Markdown. 2단계에서 LLM(OpenAI·Claude·Gemini·Ollama·Upstage 등)으로 정리할 수 있다.
- [iyulab/unhwp](https://github.com/iyulab/unhwp)(Rust, MIT, PyPI 0.24.0 2026-11-10), [hwp-hwpx-parser](https://pypi.org/project/hwp-hwpx-parser/)(순수 Python, JVM 불필요, 1.0.0), [DanMeon/rhwp-python](https://github.com/DanMeon/rhwp-python)(PyO3 바인딩).
- [ebandal/H2Orestart](https://github.com/ebandal/H2Orestart)(Java, GPL-3.0, ★203, 2026-11-13): LibreOffice 확장. `soffice --headless --infilter="Hwp2002_File" --convert-to pdf`로 HWP/HWPX를 PDF로 바꿀 수 있어 서버 측 미리보기·검증에 쓸 수 있다. 저장은 ODT만 된다.
- [PolarisOffice/polaris_dvc](https://github.com/PolarisOffice/polaris_dvc)(Rust, Apache-2.0, ★16): 한컴 DVC를 Rust로 이식한 HWPX 형식·스키마·무결성 검증 도구. README는 "HWPX는 공개 명세가 있지만 … 판정해주는 공개 레퍼런스 구현은 아직 없"다고 지적한다. 생성기 출력 검증 단계에 쓸 수 있다.

#### c-3. 한글과컴퓨터 공식 스펙·저장소
- HWPX는 ZIP 안에 OWPML XML을 담은 형식이다 — [python-hwpx README](https://github.com/airmang/python-hwpx). OWPML은 국가표준 KS X 6101이다 — [HwpForge README](https://github.com/ai-screams/HwpForge), [hwpx-docs README](https://github.com/BlackBuddle/hwpx-docs). 한컴은 '한글 문서 파일 구조 5.0'과 OWPML 문서를 hancom.com 자료실에 공개한다 — [hwpxlib README](https://github.com/neolord0/hwpxlib), [hwpx-owpml-model README](https://github.com/hancom-io/hwpx-owpml-model).
- 한컴 GitHub 조직 hancom-io의 공개 저장소:
  - [hwpx-owpml-model](https://github.com/hancom-io/hwpx-owpml-model): C++, Apache-2.0, ★40, 마지막 push 2023-10-24. OWPML 필터 모델이며 예제는 첫 섹션 텍스트 추출뿐이다.
  - [dvc](https://github.com/hancom-io/dvc): HWPX Document Validation Checker, ★9, 2023-09.
  - [metatag-ex](https://github.com/hancom-io/metatag-ex)
  - [oss-notice](https://github.com/hancom-io/oss-notice)
  - [devcenter-archive](https://github.com/hancom-io/devcenter-archive)
- 한컴은 오픈소스 PDF 데이터 추출기 '오픈데이터로더 v2.0'을 공개했다 — [바이라인네트워크](https://byline.network/2026/03/12-553/). GitHub [opendataloader-project/opendataloader-pdf](https://github.com/opendataloader-project/opendataloader-pdf)는 Apache-2.0, ★30,311, 2026-11-16 push다. LangChain·LlamaIndex 어댑터도 있다.
- 한컴이 직접 공개한 HWPX MCP 서버나 HWPX 생성 SDK는 검색에서 확인되지 않았다. 확인된 HWPX MCP는 모두 커뮤니티 개발이다 — [웹 검색 결과(glama.ai Dayoooun/hwpx-mcp, PyPI hwpx-mcp-server)](https://pypi.org/project/hwpx-mcp-server/).

#### c-4. PPTX/DOCX 생성
- [python-pptx](https://pypi.org/project/python-pptx/) 최신 1.0.2(2024-08-07)과 [python-docx](https://pypi.org/project/python-docx/) 1.2.0(2025-06-16)이 한국 제안서 프로젝트의 사실상 표준이다. 예: [road2east-git/Report-Agent_00](https://github.com/road2east-git/Report-Agent_00)의 2,270줄 python-pptx 엔진, [iplip85-create/qwen-proposal-agent](https://github.com/iplip85-create/qwen-proposal-agent), [kyuhyoung/dsi](https://github.com/kyuhyoung/dsi)의 `yaml_to_pptx.py`, 중국 [guangshu100/BidMaster-Pro](https://github.com/guangshu100/BidMaster-Pro)의 python-docx.
- 기업 표준 PPTX 템플릿 자동 온보딩(LLM vision으로 레이아웃·슬롯 좌표 추출)은 [kyuhyoung/dsi](https://github.com/kyuhyoung/dsi)와 [Kevinatkorea/ai_pptx](https://github.com/Kevinatkorea/ai_pptx)에서만 확인됐다.

### Inferences
- 질문 "Python/JS로 표·폰트·머리말이 있는 스타일 HWPX를 만들 수 있나?"의 답은 2026-11 기준 "예"다. 생성기에는 다음 조합이 현실적이다.
  - 신규 생성: python-hwpx(Apache-2.0, 순수 Python) 또는 HwpForge(Apache-2.0)
  - 양식 보존 채우기: python-hwpx-automation, hwpxskill 방식(OWPML 직접 조작)
  - 검증: polaris_dvc(형식), H2Orestart+LibreOffice 또는 rhwp(렌더 → PDF/PNG 시각 검증)
- AGPL-3.0(hwpx-docs)과 GPL-3.0(H2Orestart)은 SaaS나 배포형 생성기에 링크하면 라이선스 의무가 생긴다. 별도 프로세스로 호출하는 구조로 격리하는 편이 안전하다.
- rhwp(★4,138, 2026-03 생성)와 kordoc(★3,000)이 짧은 기간에 대형 커뮤니티를 모았다. HWP 생태계는 Rust/WASM 엔진을 중심으로 재편되고 있으며, 2026년 하반기 이후 사실상 표준이 될 가능성이 높다.
- 한컴 COM 자동화(pyhwpx, hwpapi)는 렌더링 정확도가 가장 높다. 하지만 Windows와 한글 라이선스가 필요해 클라우드 생성기에는 부적합하다. 최종 품질 확인용 선택 경로로 두는 것이 맞다.

### Gaps
- 각 라이브러리가 만든 HWPX를 한컴오피스에서 열었을 때 레이아웃이 얼마나 같은지(쪽 나눔, 표 높이)를 독립적으로 벤치마크한 자료는 찾지 못했다. 각 프로젝트의 자체 주장뿐이다.
- 한컴의 공식 HWPX SDK·MCP 로드맵은 보도자료 원문으로 확인하지 못했다.
- PPTX 쪽에서 한국 공공 제안서 특유의 가로형 레이아웃(장표 상단 헤드메시지, 좌측 목차 인덱스, 쪽번호·사업명 푸터)을 템플릿화한 오픈소스 라이브러리는 찾지 못했다(디자인 측면은 다른 연구자 담당).

## Q4. 한국어 RFP·제안서 텍스트용 Hugging Face 모델·데이터셋과 AI Hub 데이터

### Takeaway
2026-11 기준으로 Hugging Face에는 한국어 제안요청서·제안서·나라장터 데이터셋이 사실상 없다. 공개 학습 자원은 Kaggle용 KONEPS ETL, 2026 DACON 공고 법령위반 대회 데이터, 부트캠프 내부 RFP 코퍼스 정도다. 제안서 생성기는 공개 RFP를 직접 수집해 평가용 코퍼스를 만들어야 한다.

### Cited Findings
- Hugging Face 데이터셋 API 검색(downloads 정렬)에서 "제안요청서", "proposal korean", "korean public document", "koneps", "입찰"은 0건이었다. "rfp"로는 영문 RFP 데이터셋만 나왔다(예: `thamercoe/RFP-dataset`, `essentialdesigns/canadian-software-rfp-readiness-dataset`, `Legola/RFP_Categorization`). "procurement"로는 EU TED·일본·그리스·미국 DC 조달 데이터만 나왔다. — [HF datasets 검색: rfp](https://huggingface.co/datasets?search=rfp), [HF datasets 검색: procurement](https://huggingface.co/datasets?search=procurement)
- HF 모델 검색 "rfp"에서 한국어 관련으로 보이는 것은 `Dongjin1203/RFP_Documents_chatbot`(다운로드 13) 하나였고 내용은 확인하지 못했다. 나머지는 `MaziyarPanahi/rfp_instruct_model-Mistral-7B-...` 등 영문이다. — [HF models 검색: rfp](https://huggingface.co/models?search=rfp)
- [TaeyanG4/koneps-procurement-intelligence](https://github.com/TaeyanG4/koneps-procurement-intelligence)는 "South Korea Public Procurement Intelligence — KONEPS" 캐글 공개용 데이터셋을 목표로 하는 재현 가능한 ETL이다(공공데이터개방표준 API 기반). 공고 메타데이터 위주이고 RFP 본문은 아니다.
- 2026 DACON 나라장터 자체입찰 공고 법령위반 대회는 공고문·첨부·나라장터 메타데이터로 24개 검토항목을 판정하는 과제였다 — [PyTorchKR 공지](https://discuss.pytorch.kr/t/ai-9-30/11663), [Hangi-n42/g2b-bid-monitoring-ai](https://github.com/Hangi-n42/g2b-bid-monitoring-ai). 대회 데이터 재배포 허용 여부는 확인하지 못했다.
- 코드잇 AI 10기 '입찰메이트' 과제는 나라장터 RFP(PDF·HWP)와 CSV 메타데이터를 쓰지만, README상 코퍼스는 공개 저장소에 포함돼 있지 않다 — [Daybreak53/RFP-RAG-Assistant](https://github.com/Daybreak53/RFP-RAG-Assistant), [wjdtmdgh87-lgtm/its-mine-rfp-rag](https://github.com/wjdtmdgh87-lgtm/its-mine-rfp-rag).
- AI Hub: 웹 검색에서 제안요청서·제안서 전용 AI Hub 데이터셋은 찾지 못했다. 조달청과 NIA가 약 17억8천만원을 들여 RFP 자동 작성, 기능점수 산출, 과업심의 전자화, 법제도 위반 검토를 AI로 처리하는 "공공SW 발주 AI 플랫폼"을 구축한다는 2026-05 보도가 있다. 이 플랫폼은 발주자 측 시스템이며 오픈소스 여부는 미확인이고, 기사 내용은 검색 요약 기준이다 — [디지털데일리](https://m.ddaily.co.kr/page/view/2026052614231514644).

### Inferences
- 한국어 RFP→제안서 쌍 데이터가 공개돼 있지 않아 파인튜닝보다 RAG와 프롬프트·스킬 설계가 현실적이다. 실제로 공개 프로젝트 전부가 이 방식을 쓴다.
- 조달청·NIA의 발주자 측 RFP 자동작성 플랫폼이 도입되면 RFP 구조가 표준화될 가능성이 있다. 그러면 응답 측 생성기의 RFP 파싱 정확도가 오를 수 있다(추정).

### Gaps
- aihub.or.kr을 직접 열어 보지 못해 "공공 행정문서 OCR", "문서 요약" 같은 인접 데이터셋 목록과 라이선스는 확인하지 못했다.
- 나라장터 첨부 제안요청서를 대량 재배포해도 되는지(저작권, 공공누리 유형)는 확인하지 못했다.

## Q5. 범용(영문·중문) 오픈소스 RFP 응답·제안서 생성 프로젝트와 아키텍처 (분류 d)

### Takeaway
영문 RFP 응답 오픈소스는 대부분 보안설문형 Q&A다. 구조는 "질문 추출 → 지식베이스 RAG → 인용 포함 답변 → 사람 검토 → 원 양식 export"이고, 대표작(LlamaIndex auto_rfp, Microsoft accelerator)은 이미 아카이브됐다. 한국 공공 "기술제안서"에 가장 가까운 것은 중국의 标书(입찰서) 생성기다. 易标 OpenBidKit(★3,338)과 BidMaster-Pro(★455)는 요구사항·평가기준 해석 → 목차 → 장절 대량 생성 → 废标(실격) 항목 점검 → 문서 서식까지 갖췄다. 한국형 생성기의 1순위 벤치마크로 삼을 만하다.

### Cited Findings

#### d-1. 중문 标书(입찰서) 생성기: 한국 공공 제안서와 구조가 가장 유사

| 프로젝트 | 스택 / 라이선스 | 최근 push / ★ | 기능 | LLM |
|---|---|---|---|---|
| [FB208/OpenBidKit_Yibiao](https://github.com/FB208/OpenBidKit_Yibiao) (易标) | JavaScript / AGPL-3.0 | 2026-11-15 / ★3,338 | AI 기술방안 생성, 도문(그림) 생성, 상무표(商务标), 기업 지식베이스, 标书 중복검사, 废标项(실격사유) 검사, 입찰정보. README는 "11만 자 标书에 2,187,250 토큰, 1.03위안"이라고 주장한다. 온라인 버전 yibiao.pro | OpenAI 호환 전 API, ollama·LM Studio 로컬 |
| [guangshu100/BidMaster-Pro](https://github.com/guangshu100/BidMaster-Pro) | Python / AGPL-3.0 | 2026-09-03 / ★455 | 4단계 파이프라인(招标解读 / 投标生成 / 投标检查 / 文档排版), 합규 검사 규칙 21개, 멀티 에이전트와 편성 가능한 워크플로, Skill 엔진, 의미 재순위와 회사 프로필 필터 RAG, MinerU OCR, 商机(기회) 모니터링. 출력은 docx. | DeepSeek·OpenAI·Qwen 등 전환, LangGraph, Chroma |
| [Get00/BiaoShu-SKILL](https://github.com/Get00/BiaoShu-SKILL) | Python / Apache-2.0 | 2026-09-24 / ★215 | 14단계 자동 흐름. 8개 업종(IT·건설·의료·교육 등)을 자동 판별하고 **평분표준(평가기준) 해석**, 업종 가이드 자기 확장, 이미지·표·자격 위치 플레이스홀더 | 에이전트 스킬 |
| [ImGoodBai/good-autobid](https://github.com/ImGoodBai/good-autobid) | Python / 명시 없음 | 2025-03-19 / ★155 | 기술요구와 평분표준 입력 → 대강(목차) 생성 → 확인 → 종고(최종본) 생성. 20만 자. 정체 | DeepSeek V3, Gemini(OpenRouter) |
| [Router0824/BidPilot-AI](https://github.com/Router0824/BidPilot-AI) | Python(FastAPI+Vue) / AGPL-3.0 | 2026-10-03 / ★107 | 招标 파일 해석, **补遗(보완공고) 영향 분석**, 장절 작성, 기업 자료 재사용, 증거 추적, 검토 확인, Word 내보내기, 사람 수정 이력 버전 관리, Mock 모드 | OpenAI 호환, DeepSeek |
| [yanhaoluo0/technical-proposal-expert-writing-skill](https://github.com/yanhaoluo0/technical-proposal-expert-writing-skill) | Python(Claude Skill) / 명시 없음 | 2026-08-28 / ★93 | GB/T 8567-2006 준수 기술标书. 기술 카드 지식베이스를 선택적으로 검색하고, "深度写作六问"(문제/선택 이유/메커니즘/공학 구현/검증/리스크·대체안), 금지어표, "待确认" 미날조, 교부 전 체크리스트 | Claude |
| 그 외: [NewbieCoderLab/ai_bidding](https://github.com/NewbieCoderLab/ai_bidding)(MIT, ★64), [sanwudazhiyuan/-bid-analysis](https://github.com/sanwudazhiyuan/-bid-analysis)(Apache-2.0, ★40, 투표 파일 자동 심사), [RudyJunyu/Bid_Agent](https://github.com/RudyJunyu/Bid_Agent)(★40, 고정 템플릿 생성), [hello-fengsir/godbiao](https://github.com/hello-fengsir/godbiao)(MIT, ★31, 투표 파일과 招标 요구를 조항별로 대조), [mag05270/BidAgents](https://github.com/mag05270/BidAgents)(★10, LightRAG + RAG-Anything 유사 과거 标书 검색) | – | – | – | – |

#### d-2. 영문 RFP 응답·제안서 생성

| 프로젝트 | 스택 / 라이선스 | 최근 push / ★ | 아키텍처·기능 | LLM |
|---|---|---|---|---|
| [run-llama/auto_rfp](https://github.com/run-llama/auto_rfp) | TypeScript(Next.js 15) / MIT | **archived**, 2026-01-09 / ★226 | RFP 문서에서 질문을 구조화해 자동 추출하고, 지식베이스(LlamaIndex/LlamaCloud) 기반 맥락 답변을 생성한다. | OpenAI GPT-4o |
| [microsoft/agent-for-rfp-response-solution-accelerator](https://github.com/microsoft/agent-for-rfp-response-solution-accelerator) | – / MIT | **archived**, 2025-11-01 / ★58 | "no longer maintained". 이메일 파싱 → 요약·분석 → RFP 응답 초안(Azure 기반 deep reasoning 에이전트) | Azure OpenAI |
| [dboudreau00/Countersign-RFP-RFI-RFQ-Studio-for-AI-assisted-Workflows](https://github.com/dboudreau00/Countersign-RFP-RFI-RFQ-Studio-for-AI-assisted-Workflows) | JavaScript 단일 파일 + PHP 프록시 / AGPL-3.0 | 2026-11-14 / ★88 | 지식베이스 소스 최대 500개, RFP(PDF/DOCX/XLSX/CSV)의 모든 질문 추출, 질문별 인용·커버리지 점수, DOCX/XLSX/CSV 내보내기, **발주자 원본 스프레드시트에 답을 되쓰기** | OpenAI·Claude·Gemini |
| [jordanhenning32/rfp-factory](https://github.com/jordanhenning32/rfp-factory) | Python / NOASSERTION | 2026-07-22 / ★2 | 미 연방 RFP → 요구사항 원문 추출 → 컴플라이언스 매트릭스 → 역량 Gap 분석·완화책 → 가격(원가) 볼륨 → 서술 초안 → **적대적 리뷰** → DOCX. 역할 분리 멀티에이전트, FAR 가드레일, 최종 패스 사람 체크포인트 | OpenAI·Claude·Gemini |
| [PatelDeepB/open-rfp](https://github.com/PatelDeepB/open-rfp) | Python / MIT | 2026-11-02 / ★1 | solicitation shredding, 컴플라이언스 매트릭스 추출, 의미 KB 검색, 맥락 인식 초안, Gap 분석, 다중 포맷 출력 | – |
| [crawde/rfp-requirements-mcp](https://github.com/crawde/rfp-requirements-mcp) | JavaScript / 명시 없음 | 2026-04-23 / ★1 | MCP 도구: `extract_requirements`(필수/희망/정보, 마감, 평가 가중치), `generate_compliance_matrix`, `bid_no_bid_analysis` | Claude(MCP) |
| [steveh250/MAF-RFP-Factory](https://github.com/steveh250/MAF-RFP-Factory) | Python / 명시 없음 | 2026-04-12 / ★12 | Microsoft Agent Framework 오프라인 실행: Ollama Qwen3:8b + Docling MCP(PDF 파싱) + ChromaDB. RFP 발주·응답 양측 PoC | Ollama |
| [amgdy/rfp-analyzer](https://github.com/amgdy/rfp-analyzer) | Python / MIT | 2026-05-05 / ★6 | **평가자 측**: RFP 평가기준 추출 → 벤더 제안서 채점(멀티에이전트, Azure Document Intelligence) | Azure OpenAI |
| [degerahmet/q-flow](https://github.com/degerahmet/q-flow) | TypeScript / MIT | 2026-02-11 / ★3 | 보안설문·RFP. pgvector RAG + Gemini, 신뢰도 점수, 저신뢰 답변은 사람 검토 필수, Excel 서식 보존 export | Gemini |
| [aniket-work/autonomous-rfp-agent](https://github.com/aniket-work/autonomous-rfp-agent) | Python / 명시 없음 | 2026-01-01 / ★14 | 분석·검색·초안 다중 에이전트 PoC | OpenAI |

- 기타 국가별 조달 특화 사례:
  - [AnhTuan2111/vina-me](https://github.com/AnhTuan2111/vina-me): 베트남 E-HSMT(입찰서류) → E-HSDT(입찰응답) 기술부문 작성 스킬, MIT
  - [App-arently/biedkracht](https://github.com/App-arently/biedkracht): 네덜란드 TenderNed
  - [teamtalenttalk/govproposal-ai](https://github.com/teamtalenttalk/govproposal-ai): 미국 SAM.gov + Gemini

### Inferences
- 공통 아키텍처는 (1) 문서 파싱·청킹(Docling/MinerU/LlamaParse), (2) 요구사항·질문 추출과 분류(필수/희망, 평가 가중치), (3) 컴플라이언스 매트릭스, (4) 회사 지식베이스 RAG(과거 제안서·실적·인력), (5) 섹션·질문 단위 초안과 인용, (6) 신뢰도 기반 HITL 검토, (7) 적대적·평가자 관점 리뷰, (8) 원 양식 export다. 한국형 생성기에는 여기에 (9) 평가표 배점 기반 분량 배분, (10) HWPX/PPTX 양식 충실도 검증, (11) 사전규격·보완공고 변경 추적을 더해야 한다.
- 중국 标书 생성기의 "废标项 검사"(실격 요건 점검)와 "补遗 영향 분석"(보완공고 반영)은 한국 나라장터의 제안서 작성지침 위반, 정정공고 반영과 직접 대응한다. 영문 도구에는 거의 없는 기능이라 차별화 포인트가 된다.
- 상위 중문 프로젝트는 AGPL-3.0이 많다. 코드를 재사용하면 서비스 공개 의무가 생기므로 아이디어만 참고하는 편이 안전하다. Apache-2.0인 BiaoShu-SKILL은 예외다.

### Gaps
- 중문 프로젝트의 실제 생성 품질(중국 평가에서의 통과율)을 보여주는 공개 데이터는 찾지 못했다.
- 상용 SaaS(AutoRFP.ai, Loopio, Responsive 등)의 오픈소스 컴포넌트는 범위 밖이라 조사하지 않았다(다른 연구자 담당).

## Q6. 공백(Gap) — 누구도 잘 하지 못하는 것, 이 프로젝트가 채울 수 있는 것

### Takeaway
공개 코드의 공백은 "나라장터 RFP·제안서 작성지침·평가표를 구조화해 발주처 양식(HWPX/PPTX)에 맞는 고배점 제안서를 만들고, 그 결과를 평가위원 관점에서 검증하는 end-to-end 오픈소스"다. 구성 요소(공고 수집 MCP, HWPX 엔진, RAG, 한국형 설득 프레임)는 2026년에 대부분 공개됐지만 이를 엮은 성숙한 구현은 없다.

### Cited Findings
- 나라장터 제안서 생성을 직접 다루는 저장소는 모두 ★0~2이고 대부분 2026년에 생성됐다. 개인 학습, 포트폴리오, 공모전 산출물이라고 스스로 밝힌 경우가 많다 — [nasaon/g2b-proposal-automation](https://github.com/nasaon/g2b-proposal-automation)("개인 학습 프로젝트… 실제 입찰에 쓰이지 않았습니다"), [jechoiyyy/bid-deep-agent](https://github.com/jechoiyyy/bid-deep-agent)("공개 포트폴리오용 사본"), [kyuhyoung/dsi](https://github.com/kyuhyoung/dsi)("사내 AI 활용 공모전 산출물").
- 평가기준(배점)을 이용한 검토는 부분적으로만 구현돼 있다.
  - g2b-proposal-automation: 렌더 이미지를 채점기준표로 시각 검토 — [링크](https://github.com/nasaon/g2b-proposal-automation)
  - bid-pilot: 배점 추출과 근거 연결 자가채점 — [링크](https://github.com/leedonwoo2827-ship-it/bid-pilot)
  - 중국 BiaoShu-SKILL: 평분표준 해석 — [링크](https://github.com/Get00/BiaoShu-SKILL)
  - 영문 amgdy/rfp-analyzer: 평가자 측 채점 — [링크](https://github.com/amgdy/rfp-analyzer)
- "공식목차 준수 + 페이지 예산 설계"를 명시적으로 구현한 것은 [iplip85-create/qwen-proposal-agent](https://github.com/iplip85-create/qwen-proposal-agent) 하나다.
- 양식 보존형 HWPX 채우기는 별지·신청서 수준으로 확인된다 — [kyuhyoung/dsi](https://github.com/kyuhyoung/dsi)("빈 셀만 채움"), [KAIST-Mobility-AX-Institute/Proposal_Writer](https://github.com/KAIST-Mobility-AX-Institute/Proposal_Writer). 공문서 서식 규칙 DB는 [UpstageAI/korean-report-hwpx](https://github.com/UpstageAI/korean-report-hwpx)(52개 기관 보도자료 등)에 있지만 제안서 서식은 다루지 않는다.
- 섹션 간 수치·용어 일관성(SSOT) 관리를 명시한 것은 금융 IT 특화 [DinN0000/bid-marketplace](https://github.com/DinN0000/bid-marketplace)뿐이다.
- 한국어 RFP·제안서 공개 데이터셋은 없다(Q4 참조) — [HF datasets 검색](https://huggingface.co/datasets?search=rfp).
- HWPX 출력이 명세를 얼마나 따르는지 판정하는 공개 레퍼런스 구현이 아직 없다는 지적이 있다 — [PolarisOffice/polaris_dvc](https://github.com/PolarisOffice/polaris_dvc).

### Inferences
이 프로젝트가 채울 수 있는 공백을 우선순위 순으로 적는다.
1. **제안요청서 → 구조화 스키마**: 사업개요, 과업범위, 요구사항 ID(SFR/PER/SER 등), 제안서 작성지침(목차·쪽수·글꼴·용지), 기술평가표 배점, 참가자격, 정정공고 반영을 HWP/HWPX/PDF에서 근거 위치와 함께 추출한다. 이 오픈소스 스키마와 파서가 아직 없다.
2. **평가표 기반 목차·분량 배분기**: 배점 비례로 페이지 예산을 정하고, 요구사항↔목차↔평가항목 추적표(컴플라이언스 매트릭스)를 자동 생성한다. 지금은 부분 구현만 있다.
3. **이중 출력 + 양식 충실도 검증**: HWPX(python-hwpx/HwpForge)와 PPTX(python-pptx)를 동시에 지원하고, polaris_dvc 형식 검증과 rhwp·H2Orestart 렌더 기반 쪽수·서식 검사를 묶는다.
4. **평가위원 시뮬레이터**: 배점표로 LLM 채점, 적대적 리뷰, 실격(작성지침 위반) 점검을 한다. 중국 废标项 검사, 영문 rfp-factory 적대적 리뷰와 비슷하다.
5. **보안 배포 옵션**: 로컬 LLM이나 혼합 경로로 돌리고, 숫자·일정은 코드가 판정한다. 여러 프로젝트가 공공사업 문서를 클라우드 LLM에 올리기 어렵다는 점을 공통 요구로 들고 있다.
6. **사전규격 단계 조기 착수**: 사전규격정보서비스 공고를 받아 초안을 미리 만들고, 본공고와의 diff를 자동 반영한다. 수집기는 많지만 생성기와 연결한 사례는 없다.
7. **한국어 RFP 평가 벤치마크 공개**: 공개 RFP와 메타데이터 기반 평가셋이 생기면 생태계 기여도가 크다. 단, 재배포 라이선스 확인이 필요하다.

### Gaps
- 실제 조달청 기술평가 점수와 연결된 공개 사례가 없어, 어떤 기능이 수주율에 기여하는지 정량 근거는 찾지 못했다.
- 국방전자조달(d2b)과 공공기관 자체 조달(LH·한전 등) 제안서 양식 차이를 다루는 오픈소스는 수집기(bid-radar, 00data-kr, pipeworx) 외에 확인하지 못했다.
