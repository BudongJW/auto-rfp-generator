# 나라장터/조달청 공공입찰 제안서 자동화: 상용 제품·서비스 및 정부 AI 정책 조사 (2026-11 기준)

> 조사 방법 메모: 이 세션에서는 다수 한국 사이트(jodaleconomy.com, news.nate.com, cliwant.ai 등)에 대한 WebFetch가 네트워크 정책으로 차단되어(host 해석 실패) 본문을 직접 열람하지 못했다. 아래 내용은 대부분 웹검색 결과의 스니펫과 요약에서 가져온 것이다. 수치와 날짜는 원문으로 재확인해야 하며, 업체 자사 블로그에서 나온 성능 수치("90% 단축" 등)는 마케팅 주장으로 취급했다. 오픈소스 GitHub 프로젝트는 범위에서 제외했다.

---

## Q1. AI 기반 공공입찰 제안서 작성 또는 RFP 분석을 제공하는 한국 기업·제품 (카탈로그)

### Takeaway
나라장터 공급자(입찰 참가 기업) 쪽에서 "RFP 분석부터 제안서 초안(PPT)까지"를 내세우며 실제로 움직이는 제품은 다음 정도다.
- 클라이원트(Cliwant)의 Contrl: 2026-03 클로즈 베타 시작
- SK AX의 제안서 AI: 대기업 SI용
- MyBidWise: 소상공인·중소기업용, HWP/HWPX 서류 생성을 주장
- 웍스AI, 인라인AI, 프리세일즈 CheckAI: 범용 AI 포털이나 도구 안에 나라장터·RFP 기능을 포함

대부분은 아직 베타이거나 업체 자체 주장 단계다. 기존 입찰정보 업체(인포21C, 비드큐, 고비드 등)는 공고 추천과 투찰가 예측이 중심이며, 제안서 생성 기능은 확인되지 않았다.

### Cited Findings

#### A. 제안서 작성·RFP 분석 특화 (공급자용)

**1) 클라이원트(CLIWANT): 입찰 검색 AI, "AI 조달 비서", 제안서 자동화 "Contrl(컨트롤)"**
- 회사:
  - 2023-09 설립 비상장 스타트업, 입찰 분석 AI 분야 — [THE VC](https://thevc.kr/cliwant)
  - 조준호 대표는 15년 글로벌 조달 경력의 공동창업자 — [THE VC](https://thevc.kr/cliwant)
  - 임직원 12명(THE VC, 2026-09 기준) — [THE VC](https://thevc.kr/cliwant)
- 투자:
  - 2023-09 시드(본엔젤스벤처파트너스)
  - 2024-07~08 프리A(본엔젤스, 블루코너). "설립 9개월 만에 20억 원"이라는 보도가 있으나 금액 비공개라는 보도도 있어 엇갈림 — [플래텀](https://platum.kr/archives/232160), [이데일리](https://www.edaily.co.kr/News/Read?newsId=03145526638960096&mediaCodeNo=257), [인베스트뉴스(자사 블로그 전재)](https://blog.cliwant.com/investmentnews/), [THE VC 펀딩](https://thevc.kr/cliwant/fundings)
- 기타 이력:
  - "2024년 OpenAI 공식 협력 스타트업 선정"이라는 서술이 있으나, 나무위키 문서에는 MOU는 체결되지 않았다는 기술이 있음 — [나무위키](https://namu.wiki/w/%ED%81%B4%EB%9D%BC%EC%9D%B4%EC%9B%90%ED%8A%B8(CLIWANT)), [머니투데이 전재 "오픈AI도 반했다"](https://blog.cliwant.com/kdb/)
- 제품:
  - 클라이원트(입찰 검색·RFP 분석): 나라장터 공고를 연 약 44만 건 분석, RFP를 AI와 프롬프트 엔지니어링으로 분석해 기업별 입찰 매칭, 리스크 분석, 제안 전략 제공 — [머니투데이 전재](https://blog.cliwant.com/kdb/)
  - AI 조달 비서(cliwant.ai): 채팅으로 공고를 분석하는 서비스. "빠른 시일 안에 제안서 작성까지 확장할 계획" — [클라이원트 블로그](https://blog.cliwant.com/ibcaleul-jedaero-ihaehaneun-ai-keulraiweonteu-ai-jodal-biseoreul-sijaghabnida/), [cliwant.ai](https://www.cliwant.ai/)
  - Contrl(contrl.ai): 2026-03-26 클로즈 베타 시작 발표. RFP를 업로드하면 목차 구성부터 PPT 초안까지 자동 생성 — [네이트뉴스 2026-03-26](https://m.news.nate.com/view/20260326n28698), [Contrl 소개](https://www.cliwant.com/blog/contrl-closed-beta), [contrl.ai/llms.txt](https://contrl.ai/llms.txt)
- Contrl 기능:
  - Win Theme Engine: RFP 분석 결과로 "왜 우리가 이 사업을 해야 하는가"라는 전략 방향을 제안
  - Template Intelligence: 회사 고유 PPT 템플릿을 학습하고 디자인 시스템을 유지한 채 슬라이드별 레이아웃을 자동 매칭
  - 출처: [Contrl 핵심 기능 5가지](https://www.cliwant.com/blog/contrl-rfp-proposal-ai-automation), [PPT 제안서 자동화 (2026)](https://blog.cliwant.com/ppt-proposal-automation-ai-contrl/)
- Contrl 효과 (자사 베타 수치): RFP 분석이 반나절에서 약 30분 또는 "3분"으로 줄고, 초안 작성 시간이 50% 이상 단축 — [Contrl 클로즈베타 후기](https://blog.cliwant.com/contrl-closed-beta-day1-rfp-ai-proposal/), [PPT 제안서 자동화](https://blog.cliwant.com/ppt-proposal-automation-ai-contrl/)
- 베타 사용자 불만:
  - "제안서는 보통 PPT인데 PDF만 인식된다"
  - "단계별 AI 추론 시간이 너무 길다"
  - 회사는 PPT 템플릿 호환성과 지원 포맷을 확대 중이라고 밝힘 — [베타 피드백 업데이트](https://blog.cliwant.com/contrl-beta-user-feedback-update/)
  - 2차 베타도 언급됨 — [클라이원트 블로그](https://www.cliwant.com/blog/ibcal-damdangjaga-jaggu-toesahaeyo-iyureul-alryeodeurilggayo)
- 사업 모델:
  - 입찰 컨설팅 파트너 모집. 컨설팅 계약 기간에는 Cliwant MCP와 Contrl을 무료 제공 — [파트너 모집](https://blog.cliwant.com/cliwant-bidding-partner-recruitment/)
  - 2026-02 "엔터프라이즈 AX 사업" 진출. 2026년 AI 에이전트·멀티에이전트·공공조달 관련 국가 R&D 수행 — [THE VC](https://thevc.kr/cliwant)
- 트랙션 (출처별로 시점이 다름):
  - 약 130개 국내 기업이 B2B SaaS 이용 — [혁신의숲](https://www.innoforest.co.kr/company/CP00016087/%ED%81%B4%EB%9D%BC%EC%9D%B4%EC%9B%90%ED%8A%B8)
  - 고객사 60여 곳 — [더벨 전재](https://blog.cliwant.com/thebell_3/)
  - 고객사 50여 곳 — [지디넷 전재](https://blog.cliwant.com/cdo_interview/)
  - 첫해 유료 구독 매출 약 10억 원 — [채용 페이지](https://blog.cliwant.com/careers/)
  - 2026년 목표 매출 100억 원 — [더벨 전재](https://blog.cliwant.com/thebell_3/)
- 가격: 공개된 요금표를 찾지 못함.
- 참고: 과제에서 언급한 "클라이원(Cliwon?)"의 정확한 명칭은 클라이원트(CLIWANT)다.

**2) SK AX(구 SK C&C): "제안서 AI", "RFP 인사이트 AI", "AiPMO"**
- 제안서 AI의 흐름: RFP 자동 분석 → 회사 제안 표준과 과거 Best Practice를 반영한 초안 자동 생성 → AI 품질검토. 품질검토는 완성본과 RFP 원문을 Cross Check해 요구사항 누락과 불일치를 실시간 검출 — [SK AX 제안서 AI](https://www.skax.co.kr/ax-services/proposal-ai)
- SK AX 페이지는 기존 제안서 작업(RFP 분석·전략회의·초안·검토)에 5~15일이 걸린다고 설명 — [SK AX](https://www.skax.co.kr/ax-services/proposal-ai)
- RFP 인사이트 AI: AWS AI-DLC 방법론과 Kiro로 구현. 최대 200쪽 RFP에서 요구사항과 위험요소를 분석하고 WBS, 사업 일정, 투입 인력 구성안을 생성. 초기 분석은 약 20분 — [디지털데일리 2026-07-22](https://www.ddaily.co.kr/page/view/2026072208113286029)
- AiPMO: 제안·수행 단계 AI 에이전트. 반복 검토는 AI가 맡고 최종 판단은 전문가가 하는 Human-in-the-loop 구조 — [SK AX AiPMO](https://www.skax.co.kr/ax-services/aipmo)
- 출시일, 가격, 고객: 확인하지 못함.

**3) MyBidWise (mybidwise.com)**
- 기능 (자사 설명):
  - 나라장터, 기업마당, K-Startup 등 7개 기관의 공고와 지원사업을 통합 검색
  - AI 적합도 분석
  - HWP/HWPX 입찰서류 자동 생성
  - 공고 첨부 HWP에서 평가기준 추출, RFP 분석 기반 제안서 초안 생성
  - 출처: [MyBidWise 블로그](https://mybidwise.com/blog/ai-bid-document-automation)
- 요금 (블로그 구조화 데이터, 약 220일 전 기준): Free 0원 / Basic 월 14,900원(AI 적합도 10회, AI 서류 작성 3건) / Pro 월 49,900원(30회 / 10건, 자연어 검색, 매일 추천 공고) — [MyBidWise](https://mybidwise.com/blog/ai-bid-document-automation)
- "작성 시간 90% 단축"은 근거가 불명확한 자사 주장이다. 블로그 스스로도 AI 초안을 그대로 제출하지 말라고 권고 — [MyBidWise](https://mybidwise.com/blog/ai-bid-document-automation)
- 운영사, 투자, 출시일: 확인하지 못함.

**4) 웍스AI (WrksAI, AI3): 사내 AI 포털 + 나라장터 에이전트 도구**
- 나라장터 도구가 제공하는 기능:
  - 진행 중 공고, 사전규격, 발주계획 검색
  - RFP 자동 분석
  - 적격심사 예측, 투찰 시뮬레이션
  - 낙찰 이력·기관 분석
  - 출처: [웍스AI 가이드](https://docs.wrks.ai/user-guide/undefined-1), [조달청 나라장터 도구](https://docs.wrks.ai/user-guide/undefined-1/undefined-1)
- 공공용 페이지(gov.wrks.ai)가 있고, 요청과 로그를 국내에서만 처리한다고 주장 — [gov.wrks.ai](https://gov.wrks.ai/ko/agent), [wrks.ai](https://wrks.ai/en), [AI3 제품 소개](https://ai3.kr/products/wrks?lang=en)
- 제안서 본문 생성 기능이 별도로 있는지, 그리고 가격은 확인하지 못함.

**5) 인라인 AI (엘리먼츠)**
- 지시 한 줄로 NAS, 클라우드, 그룹웨어 데이터를 모아 문서를 쓰는 "완전 자율형 문서작성 AI"로 출시 — [스타트업엔](https://www.startupn.kr/news/articleView.html?idxno=53237)
- 나라장터 제안서 가이드에서 내세우는 점:
  - RFP 요구사항 추출
  - 한글(hwp/hwpx), 워드, PDF, 엑셀, PPT, 이미지 입력
  - 평가기준별 항목 생성
  - 공공기관 온프레미스 설치형
  - 출처: [inline-ai.com 가이드](https://www.inline-ai.com/blog/complete-guide-to-g2b-bidding-proposals/)
- 실제 공공 도입 사례와 출력 포맷(HWP 출력 여부)은 확인하지 못함.

**6) 프리세일즈(PRESALES, presales.co.kr) + 체크아이(CheckAI)**
- 나라장터·조달청 입찰용 기술제안서, 가격제안서, 발표PT 템플릿 마켓에 전문가 컨설팅을 함께 제공 — [presales.co.kr](https://presales.co.kr/)
- CheckAI: 공고 URL이나 RFP PDF를 입력하면 참가자격, 제출물, 평가항목, 질문 후보를 체크리스트로 정리하고 제안서 목차와 요구사항 대응표로 연결 — [AI 제안서 작성법](https://presales.co.kr/ai-proposal-guide), [나라장터 공고 확인법](https://presales.co.kr/ai-proposal-guide/narajangteo-notice-check)
- 템플릿 가격: 목차·일정 XLSX 무료, 시스템 구축 공공 제안서 PDF 49,000원 — [스토어 53](https://presales.co.kr/store/53), [스토어 79](https://presales.co.kr/store/79)
- CheckAI 자체 가격은 확인하지 못함.

**7) 한국조달AI연구소 (govt.ai.kr)**
- 그린다에이아이, 한국AI랩, 조달법인 강산, 코드데이원 컨소시엄이 만든 "공공조달 전문 AI" — [govt.ai.kr](https://govt.ai.kr/)
- 기능:
  - 수백 쪽 제안서에서 평가항목별 핵심을 추출하고, 유사사업 평가 이력으로 점수 분포를 예측 (평가 측)
  - 유사 RFP 기반 RFP 초안 생성, 법규·기술표준 반영 (발주 측)
  - 출처: [govt.ai.kr](https://govt.ai.kr/)
- "제안서 평가 70% 시간 단축"은 자사 주장. 가격과 도입 사례는 확인하지 못함.

**8) 랩큐(LabQ): PROP(프랍), prop-ai.kr**
- 생성형 AI 사업 제안서 작성 서비스로 출시, 당시 무료 베타 — [인공지능신문](https://www.aitimes.kr/news/articleView.html?idxno=30326)
- 동작 방식:
  - RFP를 기반으로 목차와 본문 생성
  - 유사사업 자료와 기술자료를 업로드하면 벡터DB로 RAG 적용, 참조 문서를 함께 제시
  - 연구개발계획서와 자유형식 제안서 지원
  - 출처: [인공지능신문](https://www.aitimes.kr/news/articleView.html?idxno=30326), [prop-ai.kr](https://www.prop-ai.kr/)
- 기사는 약 2~3년 전 것이다. 현재 랩큐 사이트는 제조·건설·공공 AI 에이전트 플랫폼이 주력이라 PROP은 우선순위가 낮아졌거나 중단되었을 가능성이 있다 — [labq.kr](https://www.labq.kr/). (운영 상태 확인 필요)

**9) 비즈폼(bizforms) AI 문서 생성**
- 문서 종류에서 "제안서"를 고르고 RFP 등 참고파일을 최대 6개 첨부한 뒤 텍스트와 어조를 설정하는 방식 — [비즈폼 AI 생성](https://www.bizforms.co.kr/ai/generate/index.html)
- 입찰 제안서 장표 작성 가이드 시리즈를 운영 — [비즈폼 AI 제안서 가이드](https://www.bizforms.co.kr/guide/hub/aiproposal.asp), [입찰 제안서 PPT 가이드](https://www.bizforms.co.kr/guide/list/aiproposal/aiproposal009.asp)
- 프리미엄 멤버십 월 9,000원 표기 (시점 불명).

#### B. 범용·엔터프라이즈 LLM 벤더의 RFP 관련 기능

- **업스테이지 Studio**:
  - 라이브러리에 "RFP 제안서류 적격판정·대응표 생성 에이전트"가 있음
  - RFP, 요구사항정의서, 평가배점표를 자사 역량과 비교해 대응 가능 여부를 판정하고 제안 작성 지시서를 생성
  - 출처: [Upstage Studio](https://studio.upstage.ai/library/agt_o3iS9mNzhFfsMjkeLeC7aU)
- **올거나이즈 Alli Deep Research**:
  - RFP 문서를 분석해 제안 전략 리포트를 생성
  - Alli 플랫폼은 MCP 기반 에이전트 빌더와 온프레미스 LLM을 제공
  - 출처: [Alli Deep Research](https://www.allganize.ai/ko/products/alli-deep-research), [인공지능신문](https://www.aitimes.kr/news/articleView.html?idxno=35942)
- **한컴어시스턴트 / 한컴독스 AI**:
  - 주제를 입력하면 계획서, 사업보고서, 공문서 등 공공 서식 초안과 목차·소제목 디자인을 생성
  - 폐쇄망 특화 sLLM 탑재
  - 출처: [한컴 FAQ](https://www.hancom.com/support/faqCenter/faq/detail/2977), [어시스턴트 가이드](https://assistant-c.stg.cloud.hancom.com/help/ko-kr/assistant_faq.html), [ZDNet 2024-06](https://zdnet.co.kr/view/?no=20240628113608)
  - 한컴독스 AI는 HWP 포맷 기반 6개 서식을 제공 — [바이라인네트워크 2024-10](https://byline.network/2024/10/241014_004/)
  - "기획서·제안서 자동 초안"은 리셀러 페이지에서만 확인됨 — [한국인프라](https://lnsit.co.kr/hancom)
  - 나라장터 제안서 전용 기능은 확인하지 못함.
- **뤼튼 도큐먼트**:
  - 2023-03 출시. 사업계획서와 보고서용이며 GPT-3.5, HyperCLOVA, 자체 모델 기반
  - 데이터바우처 등 정부지원사업 템플릿 제공
  - 공공입찰 제안서 특화 기능은 확인되지 않음
  - 출처: [ZDNet 2023-03](https://zdnet.co.kr/view/?no=20230303091012), [유니콘팩토리](https://www.unicornfactory.co.kr/article/2023030215573263503)
- **네이버 하이퍼클로바X**:
  - 기업용 "프로젝트 커넥트X"는 보고서 초안 생성 기능, 고객 데이터센터 설치형 패키지를 제공
  - 공공입찰 전용 솔루션은 확인하지 못함
  - 출처: [전자신문 2023-08](https://www.etnews.com/20230824000256)
- **삼성SDS**:
  - RFP 분석, 스펙인·스펙아웃 판단, 제안서 초안 작성을 개별 AI 에이전트로 분리해 자동화한다고 보도됨. 다만 제조업 고객 대상 AX 맥락이라 공공 SI 제안서용 제품인지는 불명확 — [한국아이닷컴](https://www.hankooki.com/news/articleView.html?idxno=297721)
  - 브리티 코파일럿은 메일, 회의, 요약 중심이며 제안서 전용 기능은 확인되지 않음 — [ZDNet 2025-10](https://zdnet.co.kr/view/?no=20251001151603)
- **LG CNS**:
  - 사내 KM(Azure OpenAI GPT-4 기반)과 M365 Copilot 기반 제안서·보고서 작성 데모 정도만 확인됨
  - 출처: [인공지능신문](https://www.aitimes.kr/news/articleView.html?idxno=29193), [ZDNet 2025-03](https://zdnet.co.kr/view/?no=20250326151846)
- **금융권 자체 구축**:
  - 2026-03-27 기사에 따르면 나라장터 공고를 AI가 수집·분석해 참여 가능 사업을 추리고 제안서 초안까지 만드는 시스템이 신한은행(기관고객부 사례)에 도입된다고 보도됨
  - 기사는 도입 방향을 서술한 수준이며 성과 수치는 없음
  - 출처: [다음/원문 기사 2026-03-27](https://v.daum.net/v/20260327174806717?f=p), [네이트뉴스](https://news.nate.com/view/20260327n27891)

#### C. 입찰정보·투찰가 분석 (기존 사업자, 제안서 생성 기능 없음)

| 서비스 | 주요 기능 | 출처 |
|---|---|---|
| 인포21C | 누적 1,600만 건 이상 입·낙찰 데이터, AI 공고 핵심정보 추출, 발주처·경쟁사 투찰 성향 분석(특허 주장), 적격심사 계산기. "2025 한국고객만족도 1위" 광고성 기사 | [한경매거진 2025-09](https://magazine.hankyung.com/business/article/202509154550b), [info21c](https://web.info21c.net/customer/serviceinfo/info) |
| 비드큐(BIDQ) | 시설·용역·구매 맞춤정보, 사정율·낙찰가 예측, 경쟁사 분석, 모바일 앱 | [App Store](https://apps.apple.com/kr/app/%EB%B9%84%EB%93%9C%ED%81%90-%EC%9E%85%EC%B0%B0%EC%A0%95%EB%B3%B4-bidq/id1634371433) |
| 고비드(GoBID, 헬로에이아이시스템즈) | 건설 투찰가 AI 제안, 9년 개발, 백테스트 기반. 기사가 약 3~4년 전이라 현재 운영 여부 불명 | [gobid.kr](https://gobid.kr/), [테크42](https://www.tech42.co.kr/ai%EB%A1%9C-%EB%82%98%EB%9D%BC%EC%9E%A5%ED%84%B0-%EC%9E%85%EC%B0%B0-%EB%8D%B0%EC%9D%B4%ED%84%B0%EB%A5%BC-%EB%B6%84%EC%84%9D%ED%96%88%EB%8D%94%EB%8B%88-%EB%82%99%EC%B0%B0%EB%A5%A0-%EA%BB%91/) |
| 지투비플러스, 비딩톰, 모두입찰 | AI 공고 추천, 모니터링 | [지투비플러스](https://www.g2bplus.kr/), [비딩톰](http://biddingtom.co.kr/index), [모두입찰](https://www.modoobid.co.kr/) |
| 일타비드, 낙비, 라플라스(디마툴즈), AI 비딩이 | 공사 투찰가 예측. 낙비는 추천가 적중률 약 30%를 자체 주장 | [ilta.kr](https://ilta.kr/), [naktal.me](https://naktal.me/), [g2b.dima.tools](https://g2b.dima.tools/), [bidding2.kr](https://bidding2.kr/bid/) |
| 비드프로(bidpro.co.kr) | 입찰공고 정보 사이트. AI 제안서 기능은 확인되지 않음 | [bidpro 공고 예시](https://www.bidpro.co.kr/n0_ipchal/konggo/svc/konggo_view.asp?num=3157246) |

#### D. 제안서 디자인·템플릿·대행 (사람 중심)
- **도큐멘토**:
  - 나라장터 입찰용 PPT 제안서 템플릿 약 99,000원, 45억 규모 고품질 PPT 392,000원 판매
  - 제안서 작성 지원(상주/비상주)은 비용 협의
  - "프리세일즈 원본" 상품명이 있어 프리세일즈와의 관계가 의심되나 확인하지 못함
  - 출처: [documento.co.kr](https://www.documento.co.kr/), [30억 시스템구축 제안서](https://www.documento.co.kr/42/?idx=104), [프리세일즈 원본](https://www.documento.co.kr/36)
- **크몽 외주 시장**:
  - 제안서·사업계획서 대행은 1만 원대부터 시작하며 평균 3만 원대
  - 디자인과 발표대본을 포함한 고급 패키지는 20만 원 이상
  - 공공 IT RFP 분석·기술제안서 검토, 나라장터 공고 분석 후 AI 초안을 만드는 상품도 존재
  - 출처: [크몽 가격 가이드](https://kmong.com/prices/%EA%B8%B0%EC%97%85-%EB%AC%B8%EC%84%9C-%EC%9E%91%EC%84%B1-%EB%8C%80%ED%96%89), [크몽 815031](https://kmong.com/gig/815031), [크몽 752993](https://kmong.com/gig/752993), [크몽 공공 제안서 PPT 포트폴리오](https://kmong.com/portfolio/view/192947)

### Inferences
- 한국 시장은 다섯 층으로 나뉘어 있다.
  - ① 입찰정보·투찰가 예측: 성숙한 시장. 인포21C, 비드큐 등
  - ② LLM 기반 RFP 분석·제안서 초안 신생 제품: 클라이원트/Contrl, MyBidWise, 웍스AI, 인라인AI, CheckAI
  - ③ 대기업 SI의 엔터프라이즈 제안서 AI: SK AX
  - ④ 발주자용 RFP 작성 AI: 조달청, 파수, govt.ai.kr
  - ⑤ 사람 중심 디자인·템플릿 대행
- "RFP 분석 → 평가항목 매핑 → 목차 → 본문 → 한국형 PPT 장표 또는 HWP → 정량서류"를 끝까지 한 제품으로 처리하는 상용 서비스는 확인되지 않았다. 가장 근접한 것은 Contrl(PPT 중심)과 SK AX 제안서 AI(대기업용)다.
- 클라이원트는 컨설팅 계약에 도구를 무료로 붙이는 방식이다. 순수 SaaS 과금만으로는 아직 지불의사를 확보하기 어렵다는 신호로 읽힌다.

### Gaps
- 포티투마루와 마인즈랩의 공공입찰 제안서 또는 RFP 제품은 검색으로 확인되지 않았다. 존재하지 않거나 공개 자료가 없다.
- 과제에서 거론된 "입찰나라", "지투비"(지투비플러스 외)는 별도로 확인하지 못했다.
- 다음 항목의 가격은 공개되어 있지 않거나 찾지 못했다: 클라이원트, Contrl, SK AX, 웍스AI, 인라인AI, govt.ai.kr, CheckAI.
- 다음 항목의 현재(2026-11) 상태는 확인되지 않았다: Contrl 정식 출시 여부, 랩큐 PROP 서비스 지속 여부, 고비드 운영 여부.
- 독립적인 제3자 리뷰(G2 같은 한국판 리뷰나 커뮤니티 평가)는 거의 찾지 못했다.

---

## Q2. HWP/HWPX 출력 또는 한국형 PPT 장표를 기본 지원하는 도구가 있는가

### Takeaway
HWP/HWPX 생성을 명시한 곳은 다음 셋이다. MyBidWise(입찰서류), 한컴 제품군(공공서식 문서, 나라장터 특화 아님), 행정안전부 온AI(공무원 보고서, 2026-12 시험운영 예정). 회사 PPT 템플릿을 학습해 장표를 만드는 공공입찰 특화 제품은 Contrl이 사실상 유일하게 확인됐다. 글로벌 RFP 도구는 Word/Excel 중심이라 HWP 지원은 없다.

### Cited Findings
- **MyBidWise**: "HWP/HWPX 입찰서류 자동 생성", 공고 첨부 HWP에서 평가기준 추출 (자사 주장) — [MyBidWise](https://mybidwise.com/blog/ai-bid-document-automation)
- **인라인AI**: hwp/hwpx를 입력으로 지원한다고 명시. 출력 포맷은 불명 — [inline-ai.com](https://www.inline-ai.com/blog/complete-guide-to-g2b-bidding-proposals/)
- **한컴어시스턴트·한컴독스 AI**:
  - 한글 문서 안에서 공공서식(계획서, 사업보고서, 공문서) 초안 생성
  - 한컴독스 AI는 HWP 기반 6개 서식 제공
  - 출처: [한컴 FAQ](https://www.hancom.com/support/faqCenter/faq/detail/2977), [바이라인네트워크](https://byline.network/2024/10/241014_004/)
- **행정안전부 온AI**:
  - 2026-12 "온AI 협업" 시험운영 예정. 기존 자료와 서식을 바탕으로 한글(HWPX) 보고서 초안을 작성하고 웹 편집기에서 수정·공유
  - 출처: [ZDNet 2026-11-01](https://zdnet.co.kr/view/?no=20261101130513), [아시아투데이](https://www.asiatoday.co.kr/kn/view.php?key=20261101010000248)
- **Contrl (PPT)**:
  - 회사 고유 PPT 템플릿을 학습하고 디자인 시스템을 유지한 채 레이아웃을 자동 매칭
  - 베타 시점에는 입력으로 PDF만 인식했고 PPT 입력은 미지원이라는 사용자 불만이 있었음
  - 출처: [Contrl 기능](https://www.cliwant.com/blog/contrl-rfp-proposal-ai-automation), [베타 피드백](https://blog.cliwant.com/contrl-beta-user-feedback-update/)
- **HWP 처리의 기술적 난점**: 개발자 사례에 따르면 구형 .hwp 바이너리는 파싱이 어려워 한글에서 HWPX로 다시 저장해야 하고, 글꼴과 표 스타일은 마지막에 수작업으로 다듬어야 함 — [GPTers 사례](https://www.gpters.org/nocode/post/more-more-challenge-automation-Jr7DsqFnKJANwqb)
- **제출 형식 관행**:
  - 나라장터 협상계약 공고는 제안서를 PDF로 제출하고 총용량 상한(예: 300MB)을 두는 경우가 많음
  - 기술평가가 기준점(예: 배점의 85%)을 넘어야 가격평가로 넘어가는 구조가 흔함
  - 출처: [비드프로 공고 예시](https://www.bidpro.co.kr/n0_ipchal/konggo/svc/konggo_view.asp?num=3157246), [비즈폼 가이드](https://www.bizforms.co.kr/guide/list/aiproposal/aiproposal009.asp)
- **범용·B2B PPT 생성 도구**:
  - 빅시프트 AI PPT Generator: B2B 영업용, 제작 85% 단축 주장
  - MOVO AI: Pro $19.99, Max $99.99
  - Presentations.AI
  - 이들은 공공입찰 양식이나 평가기준에 대응하지 않음
  - 출처: [빅시프트](https://www.bigshift.kr/case-studies/b2b-sales-ai-ppt-generator), [MOVO](https://www.movoai.app/ko/blog/ai-ppt-for-agencies), [Presentations.AI](https://www.presentations.ai/)

### Inferences
- 실제 나라장터 제출본은 대개 PDF다. 다만 작성 과정에서는 회사 PPT 템플릿(가로형 장표)이나 HWP(요약서, 정량서류, 발주처 지정 양식)가 함께 쓰인다. 그래서 "PPT 장표 + HWPX 서식 동시 출력"이 차별화 포인트가 될 수 있다.
- HWP 바이너리 입력 처리와 HWPX 출력 품질(표, 글꼴)은 상용 제품들도 아직 완전히 해결하지 못한 것으로 보인다.

### Gaps
- MyBidWise가 생성하는 HWP/HWPX 결과물의 실제 품질(표 서식, 발주처 양식 재현도)을 검증한 자료는 없다.
- Contrl이 2026-11 기준 PPT 입력이나 HWP 출력을 지원하는지는 확인하지 못했다.

---

## Q3. 조달청·행정안전부·과학기술정보통신부(NIA)의 AI 조달 관련 발표 (2021–2026)

### Takeaway
발주 측 RFP 작성 지원은 2022년부터 실제로 운영되고 있다(e-제안요청 도움). 이후 2026년에 다음 조치가 이어졌다.
- 3월 「공공조달 AI 전환 기본계획」: 5단계 전 과정에 AI 도입, AI Agent로 RFP 자동작성과 입찰 제안서 요약
- 5월 공공SW AI 책임형 발주관리 플랫폼 추진 (17.8억)
- 8월 AI 기술평가 지원시스템 실증, 인공지능조달혁신과 신설
- 11월 지능형 예정가격 작성지원시스템 전 기관 개방

정부는 발주·평가 측 AI화를 빠르게 진행하고 있다. 공급자 측 제안서 작성은 민간 시장의 몫으로 남아 있다.

### Cited Findings
**조달청: 발주 측 RFP 작성 지원**
- 2021-06: 과기정통부 디지털 공공서비스 혁신 프로젝트로 "AI 기반 발주지원시스템" 구축 착수. 약 17억 원 규모
  - 구성: 제안요청서 자동생성, 자가진단(법령 준수, 요구사항 적정성, 작성가이드 위반 검출), 정책지원서비스
  - 출처: [인공지능신문](https://www.aitimes.kr/news/articleView.html?idxno=21276), [조달청 보도자료](https://www.pps.go.kr/kor/bbs/view.do?bbsSn=2106080004&key=00634&pageIndex=1&orderBy=bbsOrdr+desc), [PPTA 웹진](https://ppta.or.kr/webzine/2021_07/c1.html)
- 2022-08-01: "e-제안요청 도움" 개통
  - 사업유형, 적용법령, 평가항목 등 기본정보만 입력하면 표준 RFP를 자동 생성
  - 자동진단과 수정 기능
  - 나라장터 과거 RFP 중 유형과 예산이 유사한 사례를 지능형으로 검색
  - 출처: [ZDNet 2022-08-02](https://zdnet.co.kr/view/?no=20220802085019), [전자신문 2022-08-01](https://www.etnews.com/20220801000123), [조달청](https://www.pps.go.kr/kor/bbs/view.do?bbsSn=2208010006&key=00318), [KDI 경제정보센터](https://eiec.kdi.re.kr/policy/materialView.do?num=228650)
  - 아이브릭스 사이트에도 소개되어 있으나 구축 참여 여부는 확인 필요 — [i-bricks](https://www.i-bricks.co.kr/company/news/580)

**조달청: 차세대 나라장터**
- 2025-01-06 개통 (예산 955억 원)
  - 2023년 보도 기준으로는 2024-06 개통 목표였으므로 지연됨
  - 개통 직후 인증·조회 장애로 민원 3.2만 건 발생
  - 출처: [한국경제 2025-01-13](https://www.hankyung.com/article/2025011332791), [디지털타임스 2023-08](https://dt.co.kr/contents.html?article_no=2023082902101831731001)
- 계획된 AI 기능: 빅데이터 기반 "조달비서(가칭)" 맞춤 추천, 자연어 기반 "나라장터 AI챗봇" — [디지털타임스 2023-08](https://dt.co.kr/contents.html?article_no=2023082902101831731001), [뉴스핌](https://newspim.com/news/view/20241230000772)
- 2025-11: 인천공항공사 등 12개 기관의 자체 전자조달시스템이 차세대 나라장터로 통합 — [보안뉴스](https://m.boannews.com/html/detail.html?idx=140366)

**조달청: 2025년 논의와 기반 조성**
- 2025-04 "공공조달 AI 혁신포럼"에서 LLM 기반 RFP 작성 지원, AI 평가위원 추천 플랫폼, 차세대 나라장터 AI 챗봇 등을 논의 (검색 요약 기준) — [조달청 보도자료](https://www.pps.go.kr/kor/bbs/view.do?key=00634&bbsSn=2504250009)
- 조달청 AI 공모전 수상작으로 "AI 기반 범정부 평가위원 통합 플랫폼"(평가위원 추천 및 평가 보조)이 선정 (검색 요약 기준이며 어느 기사에서 나온 내용인지는 특정하지 못함, 공모전 개최 시점도 미확인) — [쿠키뉴스](https://www.kukinews.com/article/view/kuk202509030244), [보안뉴스 공모전 개최](https://m.boannews.com/html/detail.html?idx=138443)
- 2025-09: 공공기관 업무망에서 보고서 작성, 문서 초안 등을 지원하는 생성형 AI 서비스 카탈로그 입찰 공고 — [조달청 보도자료](https://www.pps.go.kr/kor/bbs/view.do?key=00634&bbsSn=2509080008)

**조달청: 2026년 「공공조달 AI 전환 기본계획」과 후속 조치**
- 2026-02-25: 조달청과 SK AX가 생성형 AI 역량인증 업무협약 체결 (공공기관 최초 직원 AI 역량인증) — [정책브리핑](https://www.korea.kr/briefing/pressReleaseView.do?newsId=156746144), [조달청](https://www.pps.go.kr/kor/bbs/view.do?key=00634&bbsSn=2602260010)
- 2026-03-19 전후: 「공공조달 AI 전환 기본계획」 확정
  - 공공조달 5단계 전 과정에 AI 서비스 도입
  - 공공조달 AI Agent: RFP 자동 작성, 가격 비교 분석, 입찰 제안서 요약
  - 발주 단계: 경험이 적은 수요기관의 RFP 자동 작성 지원
  - 심사·평가 단계: 제안서 요약과 규격서 비교자료를 심사위원에게 제공
  - 전사 "공공조달 AI TF" 운영
  - 4대 축: 조달특화 AI 기반, 서비스 확산, AX 실행체계, AI 산업 활성화
  - 출처: [전자신문 2026-03-19](https://www.etnews.com/20260319000156), [헤럴드경제](https://biz.heraldcorp.com/article/10698056), [인공지능신문](https://www.aitimes.kr/news/articleView.html?idxno=38479), [이투데이](https://www.etoday.co.kr/news/view/2552707), [조달경제신문](https://www.jodaleconomy.com/news/articleView.html?idxno=2220)
  - 날짜는 18일 또는 19일로 보도가 엇갈림.
- AI 소프트웨어 판로 지원:
  - 실적 없는 AI SW도 계약할 수 있도록 쇼핑몰 등록 요건 완화, 계약 기간을 2개월에서 1개월 이내로 단축
  - AI소프트웨어 품목(세부품명번호 4323269801) MAS 신규 공고
  - 출처: [조달경제신문](https://www.jodaleconomy.com/news/articleView.html?idxno=2334), [이투데이](https://www.etoday.co.kr/news/view/2552707), [다음 2026-05-01 "공공 AI MAS 실효성"](https://v.daum.net/v/20260501150219680)
- 조달청 자체 sLLM과 범정부 LLM을 결합한 "하이브리드 AI 플랫폼"을 계획. sLLM이 RFP, 입찰 제안서 같은 민감 데이터로 평가 지원 (검색 요약 기준, 원문 확인 필요) — [쿠키뉴스 2026-03-19](https://www.kukinews.com/article/view/kuk202603190086)
- 2026-05-26: 조달청과 NIA가 17.8억 원 규모 "공공SW AI 책임형 발주관리 플랫폼" 구축 추진
  - 대화형 입력으로 사업유형별 RFP 초안 생성
  - SW사업 대가산정 가이드 기준 기능점수(FP)와 M/M 자동 산출
  - 유사사업 추천, 과업심의 전자화
  - SW진흥법·국가계약법 위반 조항 검출과 수정 문구 제안
  - 출처: [디지털데일리 2026-05-26](https://www.ddaily.co.kr/page/view/2026052614231514644)
- 2026-08-21: 전담 조직 "인공지능조달혁신과" 신설 — [KDI 경제정보센터](https://eiec.kdi.re.kr/policy/materialView.do?num=289122)
- 2026-08-26: "AI 기반 기술평가 지원시스템" 실증
  - 협상계약 제안서 평가: AI가 RFP 주요 기술·요구사항을 추출한 뒤 제안서별 요구사항 충족 여부, 강점, 핵심기술을 정리해 평가위원에게 제공
  - 9월 중 정보화사업 협상계약 평가 5건 이상에 적용 예정
  - 제3회 우수제품 지정심사 11개 품목에는 기술·성능 비교분석표를 제공
  - 원문 위치 확인 기능을 두고 "평가 참고용 보조자료"로 표시. 최종 판단은 평가위원
  - 출처: [머니투데이 2026-08-26](https://www.mt.co.kr/policy/2026/08/26/2026082610593294860), [아주경제](https://www.ajunews.com/view/20260826113355167), [더테크](https://www.the-tech.co.kr/news/article.html?no=41862)
- 2026-10-26: 2027년부터 나라장터 쇼핑몰 물품 가격 적정성을 점검하는 "AI 기반 가격관리시스템" 가동 예정 — [머니투데이 2026-10-26](https://www.mt.co.kr/policy/2026/10/26/2026102613312099320)
- 2026-11-05: "지능형 예정가격 작성지원시스템"을 모든 공공기관에 개방
  - 규격서 분석, 유사사업 검색, 낙찰이력 기반 견적업체 추천과 요청메일 발송
  - 5개월 내부 운영 후 개방
  - 출처: [KDI 경제정보센터](https://eiec.kdi.re.kr/policy/materialView.do?num=289122)

**행정안전부·과기정통부(NIA): 공공 AI 공통기반**
- 범정부 초거대AI 공통기반 구현사업(2025)
  - 삼성SDS, LG CNS, KT 컨소시엄이 수주 경쟁
  - 공무원용 문서 초안 서비스(기획, 요약, 상황, 회의결과 보고서 등 6종)를 개발 중이었음
  - 출처: [전자신문 2025-05-09](https://www.etnews.com/20250509000251), [디지털데일리 2025-11-12](https://www.ddaily.co.kr/page/view/2025111215142078532), [NIA 입찰공고](https://www.nia.or.kr/site/nia_kor/ex/bbs/View.do?cbIdx=78336&bcIdx=27879&parentSeq=27879)
- 행안부 "AI시대 행정문서 작성 가이드라인"
  - 2026-03-24 공개
  - 주어·서술어 명확화, 복잡한 표 병합 금지 등 AI 친화 원칙
  - 이후 공공부문 보고서 전반으로 확대 보도
  - 출처: [네이트뉴스 2026-03-24](https://news.nate.com/view/20260324n25724), [네이트뉴스 2026-08-23](https://m.news.nate.com/view/20260823n07378)
- 행안부 온AI
  - 2026-10 업무망 AI 웹검색 도입
  - 2026-12 HWPX 보고서 초안·협업 시험운영
  - 2027년 기관 간 AI 에이전트 공유 계획
  - 출처: [ZDNet 2026-11-01](https://zdnet.co.kr/view/?no=20261101130513), [퍼블릭타임스](https://www.public25.com/news/articleView.html?idxno=57610)

**기타 공공기관**
- 한국농어촌공사가 AI 기반 RFP 자동생성과 제안서 평가 시스템화를 추진한다고 보도됨 (2026-09-17) — [녹색경제신문](https://www.greened.kr/news/articleView.html?idxno=350299), [한국영농신문](https://www.youngnong.co.kr/news/articleView.html?idxno=70639), [핀포인트뉴스](https://www.pinpointnews.co.kr/news/articleView.html?idxno=488080)
- 입찰정보 사이트에는 농어촌공사 "제안서 평가시스템 구축 용역"(217,454,545원, 2026-06-10 공고)이 등재되어 있음 — [sankun](https://www.sankun.com/bid-institution/bC-C0ZfN0p26RNNz1_IBZ-xZzcAwcXVnWw4Gc4SwXBU)
- **파수(Fasoo) "RFP Write ACE"** (발주기관용, 민간 제품)
  - 온프레미스 LLM "Ellm" 기반. 기관이 과거에 발주한 RFP와 내부 지침을 학습해 기능, 성능, 보안, 산출물 요구사항을 구조화
  - 요구사항과 평가항목의 연결을 정리하고 누락·모호한 표현을 점검
  - Ellm은 GS인증 1등급 획득
  - 출처: [파수 블로그 2026-10-28](https://www.fasoo.ai/blog/20261028/rfp-%EC%9E%91%EC%84%B1-%EC%97%90%EC%9D%B4%EC%A0%84%ED%8A%B8-%EC%95%84%EC%A7%81%EB%8F%84-%EC%9E%91%EB%85%84-rfp-%EB%B3%B5%EC%82%AC%ED%95%B4%EC%84%9C-%EA%B3%A0%EC%B3%90-%EC%93%B0%EA%B3%A0), [파수 보도자료](https://www.fasoo.ai/press-release/20251104)
- **AI 기본법 관련**: 국가기관이 AI 제품 구매를 "우선 고려"하도록 하는 조항 해설이 있음 (법률 블로그, 원 법령 확인 필요) — [datalaw.kr](https://datalaw.kr/posts/ai-basic-law-procurement/)

### Inferences
- 정부의 AI화는 "발주(RFP 생성) → 평가(제안서 요약·요구사항 충족 분석)" 순으로 진행되고 있다. 평가위원이 AI가 만든 "요구사항 충족 여부 표"를 보게 되면, 공급자 제안서도 요구사항 ID와 평가항목에 대한 추적성(대응표)을 명시적으로 갖추는 것이 유리해진다.
- 조달청과 NIA 플랫폼이 RFP를 표준화하고 구조화하면, 공급자 측 자동 파싱 정확도가 높아질 수 있다. 이는 자동생성기 프로젝트에 기회 요인이다.
- 조달청이 "AI Agent의 입찰 제안서 요약"을 공식화하면서, 제안서 품질 판단도 AI가 읽기 쉬운 구조 쪽으로 이동할 가능성이 있다. 행안부의 "AI 친화 문서 가이드라인"(표 병합 금지 등)도 같은 흐름이다.

### Gaps
- 2025-04 혁신포럼의 원문 세부와 2026-09 기술평가 실증 결과(정확도 등)는 확인하지 못했다.
- 공급자(입찰기업)에게 제안서 작성 AI를 직접 제공하는 조달청 서비스는 찾지 못했다. 생성형 AI로 작성한 제안서에 대한 감점이나 표절 규정도 검색으로는 확인되지 않았다. 「조달청 협상에 의한 계약 제안서평가 세부기준」 최신 개정본의 원문 확인이 필요하다 — [세부기준 참고](https://www.ulex.co.kr/%EB%B2%95%EB%A5%A0/2100000172690-2040266-%EC%A1%B0%EB%8B%AC)
- 과기정통부 "AX-Sprint(11개 부처, 7,540억 원)"는 조달경제신문 요약으로만 확인했다 — [조달경제신문](https://www.jodaleconomy.com/news/articleView.html?idxno=2220)

---

## Q4. 글로벌 RFP·제안서 대응 소프트웨어 비교 (간결)

### Takeaway
글로벌 시장은 두 갈래다. 하나는 콘텐츠 라이브러리와 RAG로 과거 답변을 재사용하는 "RFP/보안설문 응답형"(Loopio, Responsive, AutoRFP.ai, Arphie, Inventive)이다. 다른 하나는 RFP를 분해(shred)해 컴플라이언스 매트릭스를 만들고 컬러팀 리뷰를 돌리는 "미국 연방조달(GovCon) 제안서형"(GovDash, Vultron, Awarded AI, Unanet ProposalAI, DeepRFP)이다. 과금은 좌석제, 프로젝트제, 사용자 월정액이 섞여 있다. 한국 나라장터 협상계약 제안서는 구조상 GovCon형(평가기준 기반 작성)에 더 가깝다.

### Cited Findings
| 제품 (국가) | 핵심 기능·워크플로 | 가격·투자 | 출처 |
|---|---|---|---|
| Loopio (CA) | 콘텐츠 라이브러리 중심, 80+ 콘텐츠 소스 연동, 중견기업 대상 | 10석 약 $20k/년 (2026-08 공개 하한 삭제 주장). Vendr 중앙값 $24,318/년 | [knowlee](https://www.knowlee.ai/blog/rfp-software-comparison), [Arphie 비교](https://www.arphie.ai/blog/loopio-vs-responsive-comparing-legacy-rfp-software-tools), [rfpaihub](https://www.rfpaihub.com/compare/loopio-vs-responsive) |
| Responsive (구 RFPIO, US) | 인용 포함 Ask 챗, TRACE Score 답변 검증, 노코드 Agent Studio, ChatGPT·Copilot·Claude용 MCP 서버(2026-05) | Lite $5,000/년(5명)부터. Vendr 중앙값 $14,750/년 | [rfpaihub](https://www.rfpaihub.com/compare/loopio-vs-responsive), [Inventive 가격 글](https://www.inventive.ai/blog-posts/rfp-software-pricing) |
| AutoRFP.ai (AU/US) | AI 초안 속도 중심, 사용자 수 무제한 | Scale $899/월(24 프로젝트), Accelerate $1,299/월(50 프로젝트), 연간 결제 | [Inventive 리뷰](https://www.inventive.ai/blog-posts/autorfp-ai-pricing-features-reviews), [rfpaihub 가격](https://www.rfpaihub.com/pricing) |
| Inventive AI (US) | AI RFP 에이전트 | $4M 시드(2024-09, Sierra Ventures 리드, YC·General Catalyst 등). 약 $10K/년부터 | [Pulse 2.0](https://pulse2.com/inventive-ai-rfp-optimization-platform-raises-4-million-seed), [sifthub](https://www.sifthub.io/best-ai-rfp-software) |
| Arphie (US) | 에이전트형 RFP 응답, 동시 프로젝트 수 기반 과금, 사용자 무제한 | $2.9M 시드(2024-11). 견적제 | [Axios](https://www.axios.com/pro/fintech-deals/2024/11/14/ai-driven-rfp-startup-arphie-seed), [AutoRFP 비교](https://autorfp.ai/blog/arphie-pricing) |
| GovDash (US) | Capture, Proposal, Contract Cloud. 전체 공고 패키지(L&M 외 포함)로 컴플라이언스 매트릭스 자동 생성, 공고 정정 시 재생성, 컬러 리뷰 내장 | $30M 시리즈B(2026-01, Mucker·BCI 리드, Northzone·YC). 매출 16배 성장 주장. Full/Flex 좌석제 | [GovDash 보도자료](https://www.govdash.com/blog/press-govdash-raises-30m-series-b-to-help-companies-win-and-manage-government-contracts-with-ai), [Compliance Matrix](https://www.govdash.com/features/compliance-matrix), [GovDash](https://www.govdash.com/) |
| Procurement Sciences / Awarded AI (US) | GovCon 전주기 AI. Rogue AI(2026-02)와 HigherGov(2026-05) 인수, FedRAMP Moderate(2026-03) 주장 (경쟁사 블로그 출처) | $30M 시리즈B(Catalyst Investors 리드, Battery·Bosch Ventures·Citi). 2025-11설이 있으나 시점 불명확 | [ExecutiveBiz](https://www.executivebiz.com/articles/procurement-sciences-funding-govcon-ai-platform), [GovDash 비교](https://www.govdash.com/blog/procurement-sciences-vs-govdash) |
| Vultron (US) | 내장 루브릭으로 섹션 채점, 갭 표시, 컴플라이언스 매핑. 400+ 고객, 초안 8배 속도 주장 | 비공개. $200~800/사용자/월은 제3자 추정 | [Rework](https://resources.rework.com/tools/ai-tools/best-ai-tools-for-government-contractors-2026), [fitgap](https://us.fitgap.com/products/060225/vultron) |
| Unanet ProposalAI (US) | RFP shredder, 컴플라이언스 매트릭스, 아웃라인, 생성, Bid/No-bid | 견적제 (약 $10K+/년 추정) | [Capterra](https://www.capterra.com/p/10028521/Unanet-ProposalAI/), [GovCon Digest](https://govcondigest.com/top-proposal-writing-software-2026/) |
| DeepRFP (US) | shred 결과를 XLSX 매트릭스로 출력, 제출 전 컴플라이언스·명료성 리뷰("가상 컬러팀") | Pro $89, Elite $149 (사용자/월). 7일 무료체험 | [rfpaihub](https://www.rfpaihub.com/deeprfp), [DeepRFP](https://deeprfp.com/deeprfp-reviews-pricing-evaluation/) |
| AutogenAI (UK) | 공공 입찰(tender) 작성 특화. 초안 시간 70% 단축 주장, 영국 정부 전략공급사 과반 사용 주장 | $39.5M 시리즈B(2023-12, Salesforce Ventures·Spark Capital), 누적 약 $65M. 좌석 견적제(약 $30K+/년 추정) | [VentureBeat](https://venturebeat.com/ai/automated-proposal-writing-startup-autogenai-raises-39-5m-from-salesforce-ventures-and-others), [Inventive 가격 추정](https://www.inventive.ai/blog-posts/autogen-ai-pricing) |
| Altura (NL) | 입찰 발굴과 제안 작성, 초안·리스크 표시 자율 에이전트. 베를린 Tendara 인수(2025-07) | €8M 시리즈A(2025-06, Octopus Ventures), €3M(2024-03, Curiosity VC) | [Altura 발표](https://altura.io/en/blog/series-a-announcement), [EU-Startups](https://www.eu-startups.com/2024/03/utrecht-based-altura-raises-e3-million-to-disrupt-the-bid-management-process-with-ai/), [Silicon Canals](https://siliconcanals.com/amsterdams-altura-bags-e8m/) |
| Tendium (SE) | 2018 스톡홀름 설립, 입찰 모니터링과 입찰관리 | 투자자 8곳 (금액 미확인) | [Tracxn](https://tracxn.com/d/companies/tendium-systems/__BsrP7S5x_x5W2KWASCmblYfoODglBnCZO3H4uadjo5k) |

- 가격 비교 자료 대부분은 경쟁사 블로그(Inventive, Arphie, AutoRFP, GovDash 등)가 작성한 것이라 편향 가능성이 있다 — [knowlee](https://www.knowlee.ai/blog/rfp-software-comparison), [bidara](https://www.bidara.ai/comparison/top-ai-rfp-software-2026)

### Inferences
- 나라장터 제안서 자동생성기는 두 방식을 모두 참고할 수 있다.
  - GovCon형에서: RFP shred → 요구사항·평가항목 매트릭스 → 아웃라인 → 섹션 초안 → 루브릭 기반 자가평가(컬러팀)
  - 응답형에서: 회사 과거 제안서·실적 라이브러리 + RAG
- 이 조합에 HWP/HWPX와 한국형 PPT 출력을 더하면 글로벌 도구가 대응하지 못하는 현지화 영역이 된다.

### Gaps
- Arphie의 2025년 이후 후속 투자는 이번 검색으로 확인되지 않았다.
- Tendium의 AI 작성 기능도 확인하지 못했다.
- G2와 Capterra 평점을 직접 수집하지는 못했다.

---

## Q5. 한국 사용자가 보고하는 페인포인트와 시장 공백

### Takeaway
반복적으로 언급되는 페인포인트는 다음과 같다.
- 제안서 작성 부담과 인력 이탈
- 평가표 기반의 논리 구조 설계
- 범용 챗봇의 한계
- HWP 처리
- 보안(망분리, 공고 전 정보 유출)
- AI 요약의 자격요건 오독
- 사람의 최종 검수 필요

다만 자료 대부분이 도구를 판매하는 업체의 글이라 독립적인 사용자 목소리는 부족하다.

### Cited Findings
**작업 부담과 인력**
- 기술력은 있어도 제안서 서식으로 역량을 옮기지 못해 수주에 어려움을 겪는 중소기업이 많다 — [인공지능신문(랩큐 인터뷰)](https://www.aitimes.kr/news/articleView.html?idxno=30326)
- 제안서 작성의 누적 피로가 실무자 이탈의 원인이 된다는 주장이 있다 (업체 블로그) — [클라이원트 블로그](https://www.cliwant.com/blog/ibcal-damdangjaga-jaggu-toesahaeyo-iyureul-alryeodeurilggayo)
- 대기업은 전담 인력과 템플릿이 있지만, 중소기업은 사업 수행과 제안서 작성을 동시에 떠안는다 — [그로블](https://www.groble.im/products/HjjMrP)
- 기존 제안서 프로세스(RFP 분석부터 검토까지)는 5~15일이 걸린다 (SK AX 설명) — [SK AX](https://www.skax.co.kr/ax-services/proposal-ai)
- 기술제안서 초안 작성에 16~24시간이 든다는 수치가 있으나 출처 신뢰도는 낮다 — [MyBidWise](https://mybidwise.com/blog/ai-bid-document-automation)

**범용 AI의 한계와 구조 설계**
- 범용 챗봇은 프롬프트에 따라 품질 편차가 크고, 제안서 전체 구성을 지도하지 못한다 — [인공지능신문](https://www.aitimes.kr/news/articleView.html?idxno=30326)
- 핵심은 평가표를 다시 읽고 논리 비약을 줄이는 것이다. AI를 단순 자동작성 도구로만 보면 공공입찰의 본질을 놓친다는 칼럼이 있다 — [투데이신문 칼럼](https://www.ntoday.co.kr/news/articleView.html?idxno=126630)
- AI 요약은 참가자격 문구를 잘못 읽을 수 있으므로 공고 원문, 나라장터 화면과 대조해야 한다 — [프리세일즈](https://presales.co.kr/ai-proposal-guide/narajangteo-notice-check)
- 배점표 숫자는 사람이 원문과 한 항목씩 맞춰봐야 한다 — [프리세일즈](https://presales.co.kr/ai-proposal-guide/proposal-evaluation-score)
- RFP가 있으면 요구사항과 평가항목의 순서를 목차로 그대로 옮기라는 실무 조언 — [비즈폼 가이드](https://www.bizforms.co.kr/guide/list/aiproposal/aiproposal004.asp)

**품질·규칙 관련 위험**
- AI 초안을 그대로 제출하면 다른 제안서와 유사해질 위험이 있다. 방법론과 차별화 부분은 직접 작성하라는 권고 — [MyBidWise](https://mybidwise.com/blog/ai-bid-document-automation)
- 타사 비방 내용은 감점(0.1점) 가능, 제출 용량은 300MB 이하 — [비즈폼](https://www.bizforms.co.kr/guide/list/aiproposal/aiproposal009.asp)

**보안과 RFP 품질**
- 공고 전 사업계획이나 예산 정보를 외부 범용 AI에 넣으면 보안과 공정성 문제가 생긴다 — [파수 블로그](https://www.fasoo.ai/blog/20261028/rfp-%EC%9E%91%EC%84%B1-%EC%97%90%EC%9D%B4%EC%A0%84%ED%8A%B8-%EC%95%84%EC%A7%81%EB%8F%84-%EC%9E%91%EB%85%84-rfp-%EB%B3%B5%EC%82%AC%ED%95%B4%EC%84%9C-%EA%B3%A0%EC%B3%90-%EC%93%B0%EA%B3%A0)
- 발주처가 "작년 RFP를 복사해서 고쳐 쓰는" 관행 때문에 RFP가 모호하다는 문제 (SW진흥법은 상세 요구사항 작성을 의무화하고 있음) — [파수 블로그](https://www.fasoo.ai/blog/20261028/rfp-%EC%9E%91%EC%84%B1-%EC%97%90%EC%9D%B4%EC%A0%84%ED%8A%B8-%EC%95%84%EC%A7%81%EB%8F%84-%EC%9E%91%EB%85%84-rfp-%EB%B3%B5%EC%82%AC%ED%95%B4%EC%84%9C-%EA%B3%A0%EC%B3%90-%EC%93%B0%EA%B3%A0)

**도구 사용성 문제**
- 상용 AI 도구 베타 사용자 불만: PPT 입력 미지원(PDF만 인식), 단계별 추론 지연 — [Contrl 베타 피드백](https://blog.cliwant.com/contrl-beta-user-feedback-update/)
- HWP 문제: 구형 .hwp 파싱 불가로 HWPX 재저장이 필요하고, 글꼴과 표 스타일은 수작업으로 마무리 — [GPTers](https://www.gpters.org/nocode/post/more-more-challenge-automation-Jr7DsqFnKJANwqb)
- 차세대 나라장터 개통 초기에 인증·조회 장애로 민원 3.2만 건이 나와 이용자 신뢰가 흔들림 — [한국경제](https://www.hankyung.com/article/2025011332791)

### Inferences
확인된 시장 공백(자동생성기 프로젝트의 기회)은 다음과 같다.
1. **평가항목 ↔ 목차 ↔ 요구사항 대응표의 자동 일관성.** 정부 평가 측 AI가 "요구사항 충족 여부"를 분석하기 시작했으므로 수요가 커질 것이다.
2. **HWPX와 한국형 가로 PPT 장표의 고품질 동시 출력.** 표와 글꼴 재현이 핵심이다.
3. **망분리·온프레미스 또는 국내 처리.** 공공·SI 고객의 보안 요구 때문이다.
4. **정량평가 서류(실적, 인력, 인증) 자동 정리.** 언급은 있으나 구현한 제품은 확인되지 않았다.
5. **중소기업이 쓸 수 있는 가격대.** MyBidWise는 월 1.5만~5만 원인 반면 SK AX와 글로벌 도구는 연 수천만 원 수준이다.

현재 상용 제품은 위 다섯 가지 중 일부만 다룬다.

### Gaps
- 디시인사이드, 블라인드, 네이버 카페(입찰 커뮤니티) 같은 독립 사용자 커뮤니티의 후기는 이번 세션에서 직접 열람하지 못했다. WebFetch가 차단됐고 검색에도 거의 노출되지 않았다.
- 상용 도구를 써서 실제로 수주율이 개선됐다는 검증 사례나 수치는 찾지 못했다. 공개된 수치는 모두 업체 자체 주장이다.
