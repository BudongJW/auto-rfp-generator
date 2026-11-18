# 나라장터(조달청) 제안서 및 제안서 자동작성 관련 학술·연구기관 문헌 조사 (주석 서지 + 종합)

> 작성일: 2026-11-16 · 범위: 2001–2026 (2015년 이후 중심) · 총 49건 (국내 33, 해외 16). 이 중 45건은 서지를 직접 검증했고, 4건은 `[P]`(부분 검증)이다.
>
> **검증 표기**: 각 항목 끝에 표기한다.
> - `[V-RISS]` RISS 서지 레코드와 초록을 직접 조회해 제목·저자·학술지·권호를 확인함
> - `[V-CR]` Crossref DOI 메타데이터로 확인함 · `[V-arXiv]` arXiv API로 확인함 · `[V-DBpia]` DBpia 메타태그로 확인함 · `[V-SPRi]` SPRi 원문 페이지·PDF를 직접 확인함
> - `[P]` 검색엔진 결과(레코드 페이지 URL·스니펫)로만 확인함. 서지는 실재하지만 세부 수치는 원문으로 확인하지 못함
>
> **접근 제약**: 이 세션에서 kci.go.kr, koreascience.kr, scienceon.kisti.re.kr, kdi.re.kr은 직접 열 수 없었다(DNS 차단). 그래서 RISS(riss.kr), Crossref, arXiv, DBpia, SPRi 원문으로 교차검증했다. Semantic Scholar와 OpenAlex API는 요청 한도 초과로 쓰지 못했다.

---

## 핵심 질문 1. 협상에 의한 계약에서 제안서 평가 결과를 결정하는 요인은 무엇인가? (기술점수 분산, 평가위원 효과, 정량·정성 비중)

### Takeaway
제도상 기술 배점은 80~90%로 높다. 그런데 국내 문헌은 업체 간 기술점수 차이가 작아 **가격이 사실상 당락을 가르고**, 정성평가는 **평가위원 개인 차이와 관계(학연·공동연구 이력)에 크게 좌우된다**고 일관되게 보고한다. 다만 나라장터 협상계약 데이터를 써서 기술점수 분산이나 평가위원 효과를 계량 분석한 동료심사 논문은 찾지 못했다. 근거는 실태분석, R&D 제안서 평가 연구, 해외 동료평가 연구에서 빌려온 것이다.

### Cited Findings

#### (1) 협상계약 제도·낙찰 구조 연구
- **김대식·김재현·백용선 (2020).** 「협상에 의한 계약제도의 효율화 방안 연구 - 문화산업 및 관련 공공사업을 중심으로 -」. *지방계약연구*, 11(1). 한국지방계약학회. `[V-RISS]`
  — 문화산업 공공사업의 입찰·낙찰 실태를 분석했다. 그 결과 현행 협상계약 기준이 "기술경쟁을 유도하지 못하고 기술력이 높은 업체조차도 기존보다 더 저가입찰을 하게 되는 문제"가 있다고 보고하고, 제안서 평가의 **변별력 확보**와 과도한 저가입찰 방지가 필요하다고 결론지었다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=623cba2cd91961d37ecd42904f0c5d65)
- **이윤선 (2017).** 「지방 공공SW의 낙찰자 선정방식의 문제점과 개선방안」. SPRi 이슈리포트 2017-002 (2017.02.23). 소프트웨어정책연구소. `[V-SPRi]`
  — 공공SW 협상계약의 기술:가격 비중은 9:1이다. 그런데 지방계약에서는 ① 예정가격을 넘겨 입찰하면 기술점수와 상관없이 협상적격에서 제외되고, ② '14년 최저입찰가격 기준을 60%에서 80%로 올리면서 가격점수 하한도 함께 올라 **80% 수준에 맞추는 전략적 저가입찰**을 유도하며, ③ 동점이면 추첨으로 순위를 정한다. 이 세 가지 때문에 가격이 과대 반영된다고 분석했다. (참고: SPRi 사이트에는 「공공SW사업 발주관리…」도 같은 '2017-002'번으로 올라 있다. 시리즈가 달라 번호가 겹친 것으로 보인다.) — [SPRi](https://spri.kr/posts/view/21700)
- **김정욱 (2012).** 「공공투자사업 입찰에서의 낙찰자 결정요인 분석」(Analysis on Determinants of Winner in Public Procurement Auction). KDI 정책연구시리즈 2012-08. 한국개발연구원. `[P]`
  — 검색 요약에 따르면 적격심사제에서는 가격이 낙찰자를 결정하는 주요 요인이고 비가격 요소는 변별력이 낮다. 턴키에서는 설계점수가 가격점수보다 낙찰 확률에 조금 더 크게 영향을 주지만 차이는 크지 않았다. 또 가격 배점을 높이는 것이 평가 주관성 문제를 줄인다는 제언이 있다고 한다. 원문은 확인하지 못했다(kdi.re.kr 접근 불가). 협상계약 자체가 아니라 공사 입찰 연구라는 점에 유의해야 한다. — [KDI](https://www.kdi.re.kr/research/reportView?pub_no=12787)
- **임강희·강경환 (2023).** 「전력지원체계 연구개발 사업 비용평가 개선 방안에 대한 연구」. *한국산학기술학회논문지*, 24(6). `[V-RISS]`
  — 방위사업청 무기체계 제안서 평가의 비용평가 방식과 기재부 「협상에 의한 계약체결기준」의 비용평가 산식을 비교했다. 2단계 경쟁입찰은 저가업체에 유리해 기술 수준이 낮은 업체가 낙찰될 위험이 있다고 지적한다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=5d584e4aec4443396aae8a972f9116fb)
- (맥락, 비학술) 업계 기고에 따르면 협상계약에서 업체 간 기술점수 차이는 보통 1~2점이다. 반면 가격점수는 예정가격의 60%를 써내면 최대 6점까지 벌어질 수 있다. 조달청은 2021년 기술 1순위에 배점한도를 주고 차순위부터 감점하는 차등점수(3점 이내)를 도입했다. — [넥스트데일리](http://www.nextdaily.co.kr/news/articleView.html?idxno=60621); [정책브리핑](https://www.korea.kr/briefing/pressReleaseView.do?newsId=156264702) (언론·보도자료이며 학술 검증은 아님)

#### (2) 평가위원 편향·점수 분산 연구
- **김훈희·이원천·오연칠·양인학 (2016).** 「IT제안서에 대한 평가위원의 불공정 예측 신경망 모델」. *한국지능시스템학회 학술발표논문집*, 26(1), 201–202. `[V-RISS]`
  — IT 제안서 평가위원의 불공정 평가를 신경망으로 예측하려 한 2쪽짜리 학술대회 논문이다. RISS에 초록이 없어 데이터와 성능은 확인하지 못했다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=2b4f7718aa9f4748b36097776a77e665)
- **김홍삼·김종수 (2017).** 「A Study on Feasibility of Evaluating IT Project Proposals based on Big Data Analysis」. *한국산업경영시스템학회 학술대회* 2017 추계, p.24 (초록). `[V-RISS]`
  — 정부 정보화사업(연 3조원 규모)의 제안서 평가에서 평가위원이 실제로 무엇에 주목하는지 분석했다. 평가위원 명단이 비공개라 설문이 어려워서 **온라인 평가시스템에 등록된 평가의견 텍스트**를 대상으로 R 형태소 분석과 극성 사전을 적용했다. 그 결과 평가 요인을 **이해력·수행력·관리력** 3개 차원으로 분류하고, 평가 점수와의 회귀분석을 계획했다. 초록 단계 연구라 최종 결과는 확인하지 못했다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=4a33b07f76cda0a7b7998d826d417196)
- **윤석민·이영훈·김영준 (2021).** 「연구제안서 평가의 정확성에 관한 연구: 평가위원의 전문성과 평가자-피평가자 간 지인관계를 중심으로」. *기술혁신학회지*, 24(5). `[V-RISS]`
  — 한국산업기술평가관리원(KEIT)이 10년간 선정평가에 올린 **19,447개 과제**를 분석했다. 평가위원 전문성(Technology Evaluator Fit)이 높을수록 과소평가 편향이 줄어 정확성이 높아졌다. 반면 평가자와 피평가자의 과거 공동수행 같은 **지인관계는 과제의 실제 품질과 무관하게 선정 가능성을 높였다.** — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=890d4275830d1c93b7998d826d417196)
- **장덕희·강길모·도수관·한동성·양정모 (2014).** 「연구제안서 동료평가에서 학연이 평가결과에 미치는 영향 분석: 한국의 사례를 대상으로」. *한국정책학회 춘계학술발표논문집* 2014, 87–100. `[V-RISS]`
  — 한국연구재단 일반연구자지원사업(2006~2012)의 연구제안서 **약 10만 건**을 분석했다. 각 과제를 평가자 3인이 평가했고, 그중 약 17%가 동일대학 출신 평가자에게 평가받았다. 평가자는 동일대학 출신자의 제안서에 상대적으로 높은 점수를 줬고, 동문이 평가자에 포함되면 선정 비율도 높았다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=d1659969bab1a156ffe0bdc3ef48d419)
- **정호용 (Jung, Hoyong) (2026).** 「공정성 외주화의 역설: 공공기관 평가위원 중개시장의 형성과 지대추구」(The Paradox of Outsourcing Fairness: Intermediation and Rent-Seeking in the Market for Public-Sector Evaluators). *산업조직연구*, 34(3), 1–41. DOI: 10.36354/kjio.34.3.1. `[V-CR][V-RISS]`
  — 공공기관이 외부 평가위원을 직접 고르는 대신 중개기관 인력풀을 쓰는 구조를 이론 모형으로 분석했다. 중개기관이 풀 등록을 유료 교육과 연계하면 전문가 참여가 줄고 풀이 축소되어 매칭 품질이 떨어진다. 그래도 기관은 감사·징계·평판 비용을 피하려고 사회후생이 더 낮은 중개 방식을 계속 택할 수 있다. — [DOI](https://doi.org/10.36354/kjio.34.3.1); [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=4c09b07e93d84ceed18150b21a227875)
- **Song, Bang-weon; Kim, Won-sik; Kang, Seok-joong (2015).** 「우선순위를 이용한 점수 표준화 방법 연구」(A Study on Standardization Methods Using the Order of Priorities). *한국정보통신학회논문지(JKIICE)*, 19(10), 2500–2506. DOI: 10.6109/jkiice.2015.19.10.2500. `[V-CR]`
  — 무기체계 제안서평가처럼 대상이 2~5개뿐인 주관적 평가에서는 평균편차일치법이 잘 맞지 않는다. 그래서 평가자 성향을 보정하되 '평균±표준편차'를 벗어난 점수만 조정하는 **편차한계적용법**을 제안했다. 이 내용 요약은 검색 스니펫을 근거로 한다. — [DOI](https://doi.org/10.6109/jkiice.2015.19.10.2500)
- (참고) 「국방 연구개발 제안서평가의 가중치 산정과 점수 표준화 방법 연구」. 학위논문(ScienceON DIKO0014435095). 저자와 연도는 확인하지 못했다. `[P]` — [ScienceON](https://scienceon.kisti.re.kr/srch/selectPORSrchArticle.do?cn=DIKO0014435095)
- **김정규·김상일·류성열 (2011).** 「공공IT제안서 기술 평가지표의 추출 및 검증 기법」. *한국컴퓨터정보학회 학술발표논문집*, 19(1). `[V-RISS]`
  — 「소프트웨어 기술성 평가기준 적용 가이드」는 평가 부문별 항목·기준이 구체적이지 않아 정확하고 공정한 평가가 어렵다고 보았다. 그래서 기술 평가요소를 평가지표로 뽑고 통계 기법으로 검증하는 방법을 제시했다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=871699ae1e591a7b4884a65323211ff0)

#### (3) 해외 유사 근거 (평가자 간 불일치)
- **Pier, E. L., Brauer, M., Filut, A., Kaatz, A., Raclaw, J., Nathan, M. J., Ford, C. E., & Carnes, M. (2018).** "Low agreement among reviewers evaluating the same NIH grant applications." *PNAS*, 115(12), 2952–2957. DOI: 10.1073/pnas.1714379115. `[V-CR]`
  — 평가위원 43명이 동일한 NIH 신청서 25건을 평가하게 해서 실제 심사를 재현했다. 그 결과 **정성·정량 평가 모두에서 평가자 간 합의가 없었고**, 강점·약점 개수를 점수로 '번역'하는 방식도 일치하지 않았다. 저자들은 결과가 "연구 내용보다 어떤 평가자에게 배정되었는지에 더 좌우되었다"고 결론지었다. — [DOI](https://doi.org/10.1073/pnas.1714379115) (초록은 Europe PMC에서 확인)

### Inferences
- 기술점수 차이가 1~2점 수준으로 작고, 정성평가는 평가자 개인 차이와 관계 편향이 크다(Pier 2018; 윤석민 외 2021; 장덕희 외 2014). 따라서 자동생성기가 기여할 수 있는 부분은 '평가위원을 설득하는 미문(美文)'보다는 다음 세 가지일 가능성이 크다. ① 정량·형식 요건 누락에 따른 감점과 실격을 막는 것, ② 평가항목과 제안 내용을 1:1로 대응시켜 평가자가 근거를 빨리 찾게 하는 것, ③ 평가자 간 분산을 줄이는 명확한 근거 제시.
- 김홍삼·김종수(2017)가 평가의견에서 도출한 **이해력·수행력·관리력** 3차원은 자동생성 결과를 자체 점검할 때 루브릭 축으로 쓸 수 있다. 단, 이 연구는 초록 단계라 최종 검증이 없다.
- 가격 요인이 당락에 큰 영향을 주므로(김대식 외 2020; 이윤선 2017), 제안서 '품질' 개선만으로 수주율이 크게 오른다고 주장하기는 어렵다. 프로젝트 목표는 '작성 시간 단축과 요건 누락 방지'로 잡는 것이 근거와 더 잘 맞는다.

### Gaps
- 나라장터 협상계약 건의 **평가위원별 기술점수 원자료로 분산, 평가자 효과, 정량·정성 비중의 영향을 계량 분석한 동료심사 논문**은 찾지 못했다. 근거는 R&D 제안서(KEIT, NRF)와 해외 NIH 연구에서 빌려왔다.
- 김훈희 외(2016)의 데이터와 결과, 김홍삼·김종수(2017)의 최종 회귀 결과는 확인하지 못했다.
- 감사원 감사보고서, 한국행정연구원(KIPA)·조세재정연구원(KIPF)의 협상계약 평가 관련 보고서는 이번에 확보하지 못했다(사이트 접근 제약, 검색 결과 없음).
- 「정부조달연구」, 「한국조달연구원」 같은 이름의 학술지나 기관은 검색으로 확인되지 않았다. 국내 조달 학술지로는 「지방계약연구」(한국지방계약학회)와 「한국구매조달학회지」가 확인되었다.

---

## 핵심 질문 2. 공공SW사업 RFP·요구사항 품질에 어떤 문제가 보고되었고, 어떤 표준화가 제안되었는가?

### Takeaway
RFP의 요구사항 상세화 수준이 낮은 것이 과업변경, 대가 없는 재작업, 수익성 악화의 핵심 원인으로 거듭 지목된다. SPRi는 '15년 기준 B등급(간이법 FP 산정 가능) 이상인 RFP가 4%에 불과하다고 보고했다. 217건의 RFP를 표본으로 한 학술연구도 '시스템 운영개념' 기술 수준이 매우 낮다고 밝혔다. 제안된 개선책은 상세화 등급 기준(B등급) 법제화, SRS 기반 과업확정과 과업심의위원회, ISMP·RFI 활용, ISO/IEC/IEEE 29148 기반 품질평가 모델이다.

### Cited Findings

#### (1) 연구기관 보고서 (SPRi)
- **이현승·이윤선 (2017).** 「공공SW사업 발주관리의 현황, 문제점, 개선방안」(The Current Status, Problems, and Ways of Improving the Management of Public SW Project Contracting). SPRi 이슈리포트 제2017-002호 (2017.9.20). `[V-SPRi]`
  — 2017년 공공SW사업 규모는 약 4조 757억원이다. 2016년 발주관리제도 준수율은 96.6%지만 발주기관과 수행기업 모두 '과업명확화'를 최우선 과제로 꼽는다. '10년 RFP 50개와 '15년 RFP 500개를 **S(5)~D(1) 5단계**로 분석한 결과, 상세화 수준이 "요구사항 이해는 가능하나 사업규모의 대략적 산정은 어려운 수준"에 머물렀다(등급 정의: B = 간이법 FP 산정 가능, A = 정통법 FP 산정 가능). 과업변경심의위원회는 법제화되었지만 발주기관 재량이라 거의 쓰이지 않는다. 개선안으로 상세화 기준을 **B등급으로 상향해 법제화**할 것을 제안했고, "현재 B등급 이상 4% → 5년 후 80%"를 목표로 제시했다. 이 밖에 RFI 참여 인센티브, ISMP·발주준비 PMO, 분석설계 종료 시점의 과업구체화 절차, 낙찰차액을 활용한 과업변경 보상을 제안했다. — [SPRi 페이지](https://spri.kr/posts/view/21871); [PDF](https://spri.kr/download/21738)
- **이현승·이윤선 (2018).** 「공공SI 및 클라우드 발주제도 개선방안 연구」(연구보고서 2017-003, 2018.05.02). SPRi (참여기관: 레달코리아). `[V-SPRi]`
  — 사업자들은 수익성 악화의 주된 원인으로 **과업범위 변경**을 꼽았다. 그 원인으로는 ① 예산편성 전 기획이 충분히 상세하지 않은 점, ② **RFP가 불명확해 계약 시 과업범위가 합의되지 않는 점**, ③ 설계 이후에도 대가 없는 과업이 계속 추가되는 점을 들었다. ISP는 범위 구체화에 한계가 있고, ISMP는 정책 지원이 없어 확산되지 못했다. 미국·핀란드·일본 벤치마킹을 통해 요구사항 상세화, 사업자 초기 참여, 전담팀 구성을 시사점으로 제시했다. — [SPRi](https://spri.kr/posts/view/22057)
- **유호석·강송희·이종주 (2018).** 「요구명세(SRS)의 중요성과 제도화 방향」. SPRi 2018-001 (2018.08.01). `[V-SPRi]`
  — 국내 SI는 "애매한 요구사항으로 RFP를 공고한 후 … 구현산출물을 보면서 명세를 거꾸로 확정해 나가는 주먹구구식 관행"이 일반적이었다고 진단했다. 2018년 SW진흥법 전부개정안에 맞춰 다음을 제안했다. FP를 가늠할 수 있는 상세 RFP 공고, 착수회의까지 과업내용 합의, 과업심의위원회 심사, SW기업의 변경영향도 분석에 근거한 심의 요청권, 초기 SRS 기준의 검수. — [SPRi](https://spri.kr/posts/view/22234)
- **김준연·심기보 (2014).** 「국가 조달체계 개선 연구: 공공SW 분할발주를 중심으로」. SPRi 연구보고서 2014-001. `[V-SPRi]`
  — 2012년 KOSA 조사를 인용해 "공공 SW 사업을 수행한 111개사의 **50%가 RFP가 불명확하여 대가없는 재작업, 과업추가를 경험**"했다고 적었다. 또 일본 발주자협의회 조사를 인용해, 기본설계 수준까지 기획하면 재작업 비율이 40.3%에서 2.2%로, 공기준수율이 65.8%에서 81%로, 품질만족도가 44%에서 70%로 개선된다고 소개한다. 둘 다 2차 인용이다. — [PDF](https://spri.kr/download/5378)

#### (2) 학술 논문
- **박상휘·김병초 (2019).** 「공공정보화사업 제안요청서 품질분석 : 시스템 운영 개념을 중심으로」. *한국IT서비스학회지*, 18(2), 37–54. DOI: 10.9716/KITS.2019.18.2.037 (KCI 등재). `[V-RISS]`
  — ISO/IEC/IEEE 29148의 시스템 운영개념(OpsCon) 문서를 바탕으로 **'조직 현황·원하는 변화·운영 제약'** 3개 항목의 RFP 품질평가 모델을 만들었다. 국가종합전자조달시스템에서 **RFP 217건**을 추출해 적용한 결과 모델의 타당성과 내적 일관성이 확인되었다. 시스템 운영개념 기술 수준은 매우 낮았고, 이것이 시스템 요구사항 품질에도 영향을 줬다. 저자들은 기능 요구사항보다 이해관계자 요구사항을 명확히 쓰는 것이 더 중요하다고 결론지었다. (영문 초록 끝에 관계없는 문장 한 줄이 섞여 있는데, 원 레코드의 오류로 보인다.) — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=7c498a2a61de755bb7998d826d417196)
- **김홍섭·박소현·이국희 (2013).** 「우정사업본부의 상세 제안요청서(RFP) 수행사례 연구」. *Entrue Journal of Information Technology*, 12(2). LG CNS. `[V-RISS]`
  — 상세 RFP 방식이 "모든 공공 IS 사업에서 법적으로 공식 RFP 작성 방법"이 된 뒤의 첫 사례(우정사업본부)를 다룬다. 요구사항 수집, 상세수준 조기검증, 명세서 작성, 요구사항 검증의 4단계 프로세스와 성공요인을 분석했다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=892436b83382d3d3d18150b21a227875)
- **박소현·이국희·구본재·김민석 (2012).** 「정보시스템 마스터플랜(ISMP) 수행 성과와 성공요인에 관한 사례연구」. *경영정보학연구*, 14(1). `[V-RISS]`
  — 요구사항을 구체화한 RFP는 업체 간 공정한 평가를 돕고 요구사항 변경과 갈등을 줄인다. ISMP 성공요인으로 사전 공감대 형성, CEO·CIO의 자원 지원, **상세화 수준의 일관된 적용**을 꼽았다. 내용 요약은 검색 스니펫을 근거로 한다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=507e9ef9258d6db2ffe0bdc3ef48d419)
- **정재봉·이석주·강재우 (2010).** 「공공 SI 프로젝트의 성공적인 수행을 위한 RFP 적합성에 관한 연구」. *한국정보처리학회 학술대회논문집*, 17(1), 973–976. `[V-RISS]`
  — 2005~2009년 공공 SI RFP를 PMBOK 지식영역에 대응시켜 분석했다. 범위·일정·비용 항목에서 뚜렷한 부족이 확인되어 보완이 필요하다고 보았다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=af071182187d58e17f7a54760bb41745)
- **송형민 (2020).** 「AHP 기법을 적용한 부품국산화 제안요청서 정교화 연구」. *한국산학기술학회논문지*, 21(1). `[V-RISS]`
  — 국방기술품질원의 부품국산화 사업 RFP를 AHP로 정교화했다. RFP를 공고, 개발자 선정, 설계, 시험 전 과정을 관통하는 핵심 문서로 본다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=2993131df87d23bd7f7a54760bb41745)
- **윤영진·조일형·유태종 (2022).** 「공공 서비스의 기술 요구사항 도출 방법론 제안: 대한민국 우편 배달 서비스의 전기차 도입 사례」. *서비스경영학회지*, 23(3). `[V-RISS]`
  — 일반 공공서비스 RFP의 기술 요구사항을 도출하는 4단계 프로세스를 제안했다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=09b84baaa037acfed18150b21a227875)
- **Song, Hyo-Jung & Kim, Taeha (2023).** 「AHP Survey on the Priority of Risk Factors in Public IT Software Projects」. *한국산학기술학회논문지*, 24(11), 682–690. DOI: 10.5762/kais.2023.24.11.682. `[V-CR]` (서지만 확인, 초록 미확인) — [DOI](https://doi.org/10.5762/kais.2023.24.11.682)

#### (3) 해외: RFP 요구사항 품질·응답 과정
- **Saito, Y., Monden, A., & Matsumoto, K. (2012).** "Evaluation of Non Functional Requirements in a Request for Proposal (RFP)." *IWSM-MENSURA 2012*, pp. 106–111. DOI: 10.1109/IWSM-MENSURA.2012.23. `[V-CR]` (서지만 확인) — [DOI](https://doi.org/10.1109/iwsm-mensura.2012.23)
- **Paech, B., Heinrich, R., Zorn-Pauli, G., & Jung, A. (2012).** "Answering a Request for Proposal – Challenges and Proposed Solutions." *REFSQ 2012*, LNCS, pp. 16–29. DOI: 10.1007/978-3-642-28714-5_2. `[V-CR]` (서지만 확인. 공급자 관점에서 RFP 응답 시 요구공학상의 문제를 다룬 연구) — [DOI](https://doi.org/10.1007/978-3-642-28714-5_2)

### Inferences
- 자동생성기는 '모호한 RFP'를 기본 입력으로 가정해야 한다. 요구사항 ID 단위로 추출하고, 상세화 등급(S~D)을 추정하고, 모호한 항목을 표시하고, 질의서 초안을 만드는 기능은 이 문헌들이 문제로 꼽은 지점에 직접 대응한다. (기능 설계 쪽 추론이며 실험 근거는 없다.)
- 박상휘·김병초(2019)의 3항목(조직 현황·원하는 변화·운영 제약)은 제안서의 '사업 이해' 장을 구성하는 틀로 그대로 쓸 수 있다. RFP에 이 정보가 빠져 있다는 결과는, 생성기가 이 부분을 공고문, 기관 홈페이지, 이전 사업 RFP 같은 외부 자료로 채워야 한다는 뜻이다.

### Gaps
- NIPA와 과기정통부의 「요구사항 상세화 실무가이드」, 조달청의 「공공정보화사업 유형별 제안요청서 작성 가이드」(2024)는 다른 조사 영역(규정)과 겹쳐 원문을 확인하지 않았다.
- B등급 이상 4% 수치는 '15년 RFP 기준이다. 그 이후 개선 추세를 실측한 최신 연구는 찾지 못했다.

---

## 핵심 질문 3. RFP 분석과 제안서 작성에 어떤 AI/NLP 접근이 시도되었으며, 데이터셋과 결과는 어떠한가? 한국어 데이터셋이나 벤치마크가 있는가?

### Takeaway
**국내에서는 RFP를 입력으로 받아 제안서를 생성하는 LLM 연구를 동료심사 문헌에서 한 건도 찾지 못했다.** 국내 연구는 나라장터 공고 검색(BERT 재순위화), RFP 토픽모델링(BERTopic), 입찰가격 예측(트리 앙상블) 수준에 머문다. 해외에서는 2024년 이후 RAG 기반 입찰문서 생성(Zhao & Li 2024)과 실제 배치된 입찰응답 다중에이전트 시스템 평가(Yu et al. 2026)가 나왔다. 그 이전에는 RFP 응답 자동채점(Maji et al. 2020)과 CPV 분류(Moiraghi et al. 2024)가 있다. 공개된 한국어 RFP-제안서-점수 데이터셋이나 벤치마크는 확인되지 않았다.

### Cited Findings

#### (1) 국내: RFP·입찰공고 NLP
- **이선표·현철호·장수현·지학수·박승범 (2022).** 「나라장터 입찰공고 인공지능 검색모델 개발에 관한 연구」. *정보기술아키텍처연구*, 19(3), 183–196. 한국엔터프라이즈아키텍처학회 (KCI 등재, KCI ART002883147). `[V-RISS][V-DBpia]`
  — 나라장터 검색이 매우 부정확하다는 문제의식에서 출발했다. 공고를 구절로 나누고 키워드를 뽑아 의사질의를 만든 뒤, Elasticsearch BM25로 의사레이블(q-d pair)을 생성해 약지도학습을 했다. 이 데이터로 **BERT(CEDR) 재순위화** IR 모델을 학습했고, "현행 나라장터보다 훨씬 정확한 검색결과"를 얻었다고 보고한다. 초록에는 정량 지표가 나오지 않는다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=401ba3f92a9aee3fb36097776a77e665); [DBpia](https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE11284112)
- **임찬호·권헌영 (2024).** 「토픽모델링을 활용한 공공기관 정보화 사업 RFP 현황 분석: 보안 요구사항을 중심으로」. *한국IT서비스학회지*, 23(6), 39–51 (KCI 등재). `[V-RISS]`
  — 2019~2023년 5년치 공공기관 정보화사업 RFP의 보안 요구사항을 **BERTopic**으로 분석해 8개 토픽을 도출하고 2개 그룹으로 해석했다. 이어 토픽별 시계열 추세를 분석했다. 2013년 1월 1일부터 정보화사업 RFP 공개가 의무화되었다는 점도 명시하는데, 이는 공개 RFP 코퍼스를 만들 수 있는 근거가 된다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=897f690733024a1dd18150b21a227875)
- **권석훈·나재열·유정연·이강찬·이규철 (2001).** 「XML 기반의 제안서 접수 및 평가 시스템의 설계 및 구현」. *한국정보과학회 학술발표논문집*, 28(1B). `[V-RISS]` (오래된 연구)
  — 제안서 접수와 평가의 수작업을 웹으로 자동화하려고 **HWP 문서 구조를 XML로 변환**하는 방식을 썼다. HWP 처리 자동화의 초기 사례다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=b331e922ce6ae65effe0bdc3ef48d419)
- **문형남 (2025).** 「인공지능(AI)의 조달 적용 현황과 사례 분석」. *한국구매조달학회지*, 24(1). `[V-RISS]`
  — 국내외 AI 조달 적용 사례를 정리한 리뷰다. 효율성, 비용절감, 투명성 효과가 있지만 기술적 한계, 법제도 미비, 조직 저항이 과제로 남아 있다고 정리했다. 실험 연구는 아니다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=25949c9dac7215494884a65323211ff0)

#### (2) 해외: RFP·입찰문서 생성, 응답, 채점
- **Yu, C., Mathew, N., & Wang, Z. (2026).** "Structure for Reading, Prose for Writing: Asymmetric Structural Conditioning in Multi-Agent Document Authoring." arXiv:2608.20786. `[V-arXiv]`
  — 오픈웨이트 모델로 **실제 배치된 입찰응답(tender-response) 다중에이전트 시스템**을 같은 조직이 실제로 제출한 인간 작성 입찰서와 블라인드로 비교했다. 결과는 다음과 같다.
  - LLM 판정 기준 55개 섹션 중 40개에서 인간 답변과 동등 이상, 4개에서 더 나음, 누락은 0개, 근거 없는 주장 지적은 1건이었다.
  - 불리한 판정 15건 중 68%는 **시스템 소스에 없던 정보** 때문이었고, 시스템이 피할 수 있었던 결함은 6건뿐이었다.
  - 구조화 마크업은 읽기(추출)에는 도움이 되지만, 지시문을 산문에서 중첩 XML로 바꾸자 답변 품질이 **74%에서 48%로 하락**했다.
  - 프롬프트에서 금지 표현을 명시하면 결함이 오히려 그 표현에 집중되었다(잔존 결함의 96%).
  - 확률적 주석과 결정적 윈도잉을 결합하자 동일한 파일에서 추출된 요구사항 수가 68개에서 51개로 변했다. 요구사항 추출이 불안정하다는 뜻이다.
  — [arXiv](https://arxiv.org/abs/2608.20786)
- **Zhao, Y., & Li, D. (2024).** "A Large Language Model-based Framework for Semi-Structured Tender Document Retrieval-Augmented Generation." arXiv:2410.09077. `[V-arXiv]`
  — 범용 LLM에는 조달 전문지식이 없다는 점에서 출발해, RAG로 **반정형 입찰문서(발주 측 문서) 생성**의 정확성과 관련성을 높이는 프레임워크를 제안했다. 과거 입찰문서를 템플릿으로 쓴다는 설명은 검색 요약에만 있고 초록에는 없다. — [arXiv](https://arxiv.org/abs/2410.09077)
- **Maji, S., Appe, A. S., Bali, R., Chikka, V. R., Chowdhury, A. G., & Bhandaru, V. M. (2020/2021).** "An Interpretable Deep Learning System for Automatically Scoring Request for Proposals." arXiv:2008.02347; *IEEE ICTAI 2021*. `[V-arXiv]`
  — 미국 Medicaid Managed Care의 RFP **응답서(수백 쪽)**를 에세이 자동채점 문제로 정식화하고, **Bi-LSTM 회귀 모델**로 점수를 예측하면서 점수에 영향을 주는 구절을 해석했다. 검색 요약에 따르면 응답 약 1,300건과 BERT 임베딩, 보조 특징을 썼다고 하지만 초록에서는 확인하지 못했다(`[P]`). — [arXiv](https://arxiv.org/abs/2008.02347)
- **Rahman, M. M., & Finin, T. (2018).** "Understanding and representing the semantics of large structured documents." *Semantic Deep Learning Workshop at ISWC 2018*; arXiv:1807.09842. `[V-arXiv]`
  — 학술논문과 **RFP 문서** 같은 대형 구조문서의 섹션 기능과 의미를 딥러닝 기반 문서 온톨로지로 표현하고, arXiv 논문과 RFP 데이터셋으로 평가했다. — [arXiv](https://arxiv.org/abs/1807.09842)
- **Moiraghi, F., Palmonari, M., Allavena, D., & Morando, F. (2024).** "Zero-Shot Hierarchical Classification on the Common Procurement Vocabulary Taxonomy." *COMPSAC 2024*; arXiv:2405.09983. `[V-arXiv]`
  — EU 공공입찰을 CPV 분류체계에 분류할 때 생기는 희소·불균형 문제를 라벨 설명 기반 **제로샷** 사전학습 언어모델로 해결했다. 나라장터의 물품분류번호·세부품명 분류에 비슷하게 적용할 수 있다. — [arXiv](https://arxiv.org/abs/2405.09983)
- **Gao, Y., Matoshi, V., Rolshoven, L., Ellendorff, T., Binder, J., Jann, J. A., Schneider, G., & Stürmer, M. (2026).** "Generating and Evaluating Sustainable Procurement Criteria for the Swiss Public Sector using In-Context Prompting with Large Language Models." arXiv:2603.22513. `[V-arXiv]`
  — 스위스 법이 요구하는 지속가능성 요건을 구체적인 선정·낙찰 기준과 기술규격으로 바꾸는 **LLM 기반 생성·평가 파이프라인**을 제시했다. 발주 측의 평가기준 생성 연구다. — [arXiv](https://arxiv.org/abs/2603.22513)
- **Mokhtari, Y., Pukhkoy, V., & Smits, G. (2026).** "TenderKG." arXiv:2608.14066. `[V-arXiv]`
  — 2021~2023년 프랑스 공공조달 데이터로 만든 대규모 **지식그래프 데이터셋**이다. 기업, 입찰, 로트, 분야 분류를 연결하며 입찰 추천 연구용으로 공개되었다. 낙찰 기업만 관측되어 신호가 희소하다는 점이 특징이다. — [arXiv](https://arxiv.org/abs/2608.14066)
- **Zahid, E., Ong, Y. J., Megahed, A., & Nakamura, T. (2021).** "Predicting Loss Risks for B2B Tendering Processes." arXiv:2109.06815. `[V-arXiv]`
  — 수주 예측을 이진 분류에서 다중 클래스(수주, 미응찰, 고객 미추진, 경쟁 패배)로 확장해 패배 사유를 설명하도록 했다. — [arXiv](https://arxiv.org/abs/2109.06815)
- **Ren, J., & Wang, W. (2025).** "Assisting Research Proposal Writing with Large Language Models: Evaluation and Refinement." arXiv:2509.09709. `[V-arXiv]`
  — 연구제안서 작성에 쓰는 ChatGPT를 **내용 품질과 참고문헌 타당성** 두 지표로 정량 평가하고, 이 점수를 피드백으로 쓰는 반복 프롬프팅을 적용했다. 그 결과 내용 품질이 높아지고 허위 인용이 줄었다. — [arXiv](https://arxiv.org/abs/2509.09709)

#### (3) LLM을 평가자로 쓰는 문제
- **Sandström, U., & Thelwall, M. (2026).** "Can Large Language Models Evaluate Grant Proposal Quality? Revisiting the Wennerås and Wold Peer Review Data." *Journal of Data and Information Science*, DOI: 10.1515/jdis-2026-0048; arXiv:2603.14565. `[V-CR][V-arXiv]`
  — 중형 오픈웨이트 LLM의 점수와 전문가 점수의 상관은 **평균 Spearman 0.22**로 약했다. LLM끼리의 상관은 평균 0.34였고, 최고치는 Gemma 3 27B의 0.33으로 평가자 간 상관의 56% 수준이었다. 저자들은 LLM 점수를 1차 선별(triage)이나 동점 처리 정도에 쓸 수 있다고 본다. — [arXiv](https://arxiv.org/abs/2603.14565)
- **Karp, M., Kubaszewska, A., Król, M., Król, R., Smywiński-Pohl, A., Szymański, M., & Wydmański, W. (2025).** "LLM-as-a-Judge is Bad, Based on AI Attempting the Exam Qualifying for the Member of the Polish National Board of Appeal." arXiv:2511.04205. `[V-arXiv]`
  — 폴란드 공공조달 심판위원 자격시험에서 GPT-4.1, Claude 4 Sonnet, Bielik 등은 지식시험을 만족스럽게 통과했다. 그러나 판결문 작성과 'LLM-as-a-judge' 자동평가는 신뢰하기 어려웠다. 조달 법리 영역에서 LLM 판정을 쓸 때의 위험을 보여준다. — [arXiv](https://arxiv.org/abs/2511.04205)

#### (4) 나라장터 데이터 활용 연구 (데이터 기반 기능의 맥락)
- **최태홍·이경희·조완섭 (2018).** 「빅데이터를 활용한 공공계약의 입찰참가자수 영향요인 분석」. *한국빅데이터학회지*, 3(2), 87–99. DOI: 10.36498/kbigdt.2018.3.2.87. `[V-CR][V-RISS]`
  — 나라장터 계약 **약 435만 건**(공공기관 5만여 곳, 사업자 30만여 곳)을 분석했다. 예산이 클수록 참가자 수가 적었고, 제한경쟁이 일반경쟁보다 참가자가 많았다. 공고일수는 유의하지 않았다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=cda289a2c31a7e767ecd42904f0c5d65)
- **이동근·김건우·최근호 (2026).** 「인공지능 기반 공공조달 적격심사 1순위 투찰금액 예측 모델 연구: 공종별 변수 영향력 분석을 중심으로」. *경영정보학연구*, 28(3) (KCI 등재). `[V-RISS]`
  — **조달데이터허브**의 2020.1~2025.7 전기·토목·건축 공사입찰 데이터에 RF, LightGBM, XGBoost, CatBoost를 비교했다. 랜덤포레스트가 MAPE 약 0.7%로 가장 좋았고, SHAP 분석에서는 금액 변수가 지배적이었다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=34e9279b47858a07b36097776a77e665)
- **엄상훈·조인휘 (2022).** 「국가종합전자조달시스템 복수예비가격에서 다중선형회귀 및 정규화 모델 기반의 예정가격 예측」. *한국통신학회논문지*, 47(10). `[V-RISS]`
  — KONEPS 연 거래액은 64조원, 2021년 조달업체는 약 66.9만 개다. 복수예비가격 방식의 예정가격을 회귀와 정규화 모델로 예측해 R² 99% 이상을 보고했다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=348a609919f353d17f7a54760bb41745)
- **김정욱 (2010).** 「공공투자사업의 입·낙찰 분석」. *KDI Journal of Economic Policy*, 32(2), 144–170. `[P]`
  — 조달청 온라인 입찰자료를 분석했다. 응찰자 수가 늘수록 낙찰률이 감소하고, PQ 결과와 현장설명회는 낙찰률을 잘 설명하지 못했다(검색 요약 기준). — [KoreaScience](https://www.koreascience.or.kr/article/JAKO201024236535502.page)
- **Huber, M., & Imhof, D. (2021).** "Deep learning for detecting bid rigging: Flagging cartel participants based on convolutional neural networks." arXiv:2104.11142. `[V-arXiv]`
  — 일본과 스위스 조달 데이터에서 기업 쌍의 정규화 입찰가를 그래프 이미지로 만들고, CNN으로 담합 참여자를 판별했다. 나라장터 데이터로 담합을 머신러닝 탐지한 국내 동료심사 논문은 이번 검색에서 찾지 못했다. — [arXiv](https://arxiv.org/abs/2104.11142)

### Inferences
- Yu et al.(2026)은 이 프로젝트에 가장 직접 참고할 만한 실증 근거다. 이를 바탕으로 한 설계 시사점은 다음과 같다.
  - 생성 품질의 병목은 문장력보다 **회사 실적·인력·기술 같은 사내 근거자료를 얼마나 갖췄는지**에 있다. 자체 지식베이스(실적DB, 인력DB)를 1급 입력으로 설계해야 한다.
  - RFP 파싱에는 구조화(표, 마크업)를 쓰고, 생성 지시는 산문으로 주는 비대칭 설계가 낫다.
  - 요구사항 추출은 확률적이라 결과 개수가 흔들린다. 결정적 파서(요구사항 ID 정규식, 표 파싱)를 함께 써야 한다.
- 한국어 RFP 코퍼스는 '13년 이후 정보화사업 RFP 공개 의무화(임찬호·권헌영 2024), 나라장터 공고 첨부파일, 조달데이터허브(이동근 외 2026)로 구축할 수 있어 보인다. 그러나 **제안서 본문과 평가점수**는 공개되지 않아, Maji et al.(2020)처럼 점수 예측 모델을 학습하기는 어렵다고 판단된다.
- LLM-as-judge로 자동 품질평가를 할 수는 있다. 하지만 전문가 점수와의 상관이 약하므로(Sandström & Thelwall 2026; Karp et al. 2025), 체크리스트형 결정적 검증(요건 충족, 분량, 필수 서식)을 주 평가로 두고 LLM 판정은 보조로 쓰는 편이 근거에 부합한다.

### Gaps
- **한국어로 'RFP → 제안서 생성'이나 'RFP 요구사항 자동추출'을 다룬 동료심사 논문은 RISS, KCI, DBpia 검색에서 찾지 못했다.** 검색어는 "제안서 자동 생성", "제안서 생성형 AI", "제안요청서 LLM", "제안요청서 BERT", "제안서 RAG", "공공문서 생성 LLM" 등이었다. KCC, KSC, ACK, HCLT 2024~2026 논문집 전체를 직접 열람하지는 못했으므로 학술대회 단편 논문이 있을 수는 있다. 상용 서비스(예: SK AX '제안서 AI', 클라이원트 'Contrl')는 있지만 성능 검증 문헌이 없다.
- 공개된 한국어 RFP-제안서-점수 데이터셋이나 벤치마크는 확인되지 않았다.
- ResearchGate에서 "Retrieval augmented generation with LLMs for enterprise proposal automation"과 "AI-Driven RFP Document Intelligence and Question-Answering Pipeline" 두 편이 보였지만, 게재처와 저자를 확인하지 못해 **미검증**으로 서지에서 제외했다.
- 김훈희 외(2016)의 신경망 모델 데이터와 성능은 확인하지 못했다.

---

## 핵심 질문 4. 제안서 작성 전략, 성공요인, 문서 가독성·디자인이 평가 점수에 미치는 영향에 대한 연구가 있는가?

### Takeaway
공공 제안서의 가독성이나 디자인이 평가점수에 미치는 영향을 실증한 **국내 연구는 찾지 못했다.** 가장 가까운 근거는 연구비 제안서 연구다. NSF 초록의 문체(길이, 흔치 않은 단어, 확신 표현)가 지원 금액과 상관된다는 연구(Markowitz 2019)와 평가자 간 불일치 연구(Pier 2018)가 있다. 국내 '수주 성공요인' 연구는 대부분 수주 이후 프로젝트 성과나 RFP 측면을 다루고, 제안서 작성 단계의 성공요인을 실증한 연구는 드물다.

### Cited Findings
- **Markowitz, D. M. (2019).** "What Words Are Worth: National Science Foundation Grant Abstracts Indicate Award Funding." *Journal of Language and Social Psychology*, 38(3), 264–282. DOI: 10.1177/0261927X18824859. `[V-CR]`
  — NSF 제안서 **19,569건**의 초록 740만 단어를 분석했다. 평균보다 길고, 흔한 단어가 적고, **확신 표현(verbal certainty)**이 많은 초록일수록 지원 금액이 컸다(한 단어 늘 때마다 약 $372). 이는 NSF가 권고하는 '평이한 글쓰기'와 반대 방향이다. 다만 선정 여부가 아니라 금액과의 상관이다. — [DOI](https://doi.org/10.1177/0261927x18824859)
- **Pier et al. (2018)** — 핵심 질문 1에 서지 있음. 같은 신청서를 두고 평가자 간 합의가 없었으므로, '문서 품질 → 점수'의 신호 자체가 평가자 잡음에 크게 희석된다. — [DOI](https://doi.org/10.1073/pnas.1714379115)
- **김홍삼·김종수 (2017)** — 핵심 질문 1에 서지 있음. 평가의견 텍스트에서 이해력·수행력·관리력 3개 차원을 도출했다. 국내 IT 제안서에서 평가자가 주목하는 요소를 다룬 유일한 텍스트 기반 시도다. — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=4a33b07f76cda0a7b7998d826d417196)
- **Ham, Young-woo; Hong, Ah-reum; Li, Yan-nan (2025).** 「A Study on the Determinants of SMEs' Participation in Public IT Project Bidding Using the AHP Method」. *Korean Review of Corporation Management*, 16(3), 53–73. DOI: 10.20434/kricm.2025.8.16.3.53. `[V-CR]` (서지만 확인, 초록 미확인. 중소기업의 공공 IT 입찰 참여 결정요인 연구) — [DOI](https://doi.org/10.20434/kricm.2025.8.16.3.53)
- (참고, 성공요인 인접 연구) 국내 IT서비스 기업의 프로젝트 273개를 분석한 연구는 일정관리, 유사 프로젝트 경험, PL 리더십, 팀 역량, 고객관계가 이익개선율에 영향을 준다고 보고했다(이경배·오재인, 「IT서비스 프로젝트의 이익개선율 영향요인에 관한 연구」). 수주 이후 성과에 관한 연구이고, 검색 스니펫만 확인했다(`[P]`). — [KoreaScience PDF](https://koreascience.kr/article/JAKO201014348975244.pdf)

### Inferences
- 문체 효과는 NSF 지원금액과의 상관 수준(Markowitz 2019)에 그친다. 평가자 잡음도 크다(Pier 2018). 따라서 '가독성을 높이면 점수가 오른다'는 주장을 근거로 기능 우선순위를 정하기는 어렵다. 다만 평가자가 근거를 빨리 찾게 하는 구조(평가항목별 목차 대응, 요약표)는 정성평가 분산을 줄이는 방향으로 합리적이다. 이는 검증되지 않은 추론이다.

### Gaps
- 한국 공공 제안서의 분량, 도식 비율, 요약표, 발표자료 디자인이 기술평가 점수에 미치는 영향을 다룬 실증 연구는 찾지 못했다(RISS "제안서 가독성" 검색 결과 0건).
- '제안 프로세스(컬러팀 리뷰, 스토리보드 등)와 수주율'에 관한 국내 학술 실증도 찾지 못했다. 서적과 실무서 수준 자료만 있는 것으로 보인다.

---

## 핵심 질문 5. 제안서 자동생성 프로젝트가 다룰 수 있는 열린 연구 공백은 무엇인가?

### Takeaway
문헌을 종합하면 다섯 가지 공백이 뚜렷하다. ① 한국어 RFP→제안서 생성의 동료심사 연구 부재, ② 한국어 RFP 요구사항 추출, 상세화 등급 판정 데이터셋 부재, ③ 협상계약 평가점수와 제안서 특성을 연결한 실증 부재, ④ LLM 판정과 공공 평가위원 점수의 정합성 미검증, ⑤ HWP 등 한국 특화 문서 파이프라인 연구의 공백(2001년 XML 변환 연구 이후 거의 없음).

### Cited Findings
- 국내 AI 조달 연구는 검색(이선표 외 2022), 토픽모델링(임찬호·권헌영 2024), 가격예측(이동근 외 2026; 엄상훈·조인휘 2022), 리뷰(문형남 2025)에 집중되어 있다. 생성 연구는 발견되지 않았다. — [RISS 이선표 외](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=401ba3f92a9aee3fb36097776a77e665); [RISS 임찬호·권헌영](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=897f690733024a1dd18150b21a227875); [RISS 이동근 외](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=34e9279b47858a07b36097776a77e665)
- RFP 상세화 수준을 S~D 5단계로 판정하는 기준이 이미 있다(SPRi 2017). ISO/IEC/IEEE 29148 기반 3항목 평가모델도 있다(박상휘·김병초 2019). 이 둘을 **자동 판정 과제**로 바꾼 연구는 없다. — [SPRi PDF](https://spri.kr/download/21738); [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=7c498a2a61de755bb7998d826d417196)
- 해외 배치 시스템 평가에서는 실패의 68%가 정보 부재에서 비롯되었다. 또 요구사항 추출 개수가 68개에서 51개로 흔들렸다(Yu et al. 2026). 근거자료 관리와 요구사항 추적이 핵심 연구 과제라는 뜻이다. — [arXiv](https://arxiv.org/abs/2608.20786)
- 평가의견 텍스트를 점수로 수치화하려는 시도가 있었지만 초록 단계에 그쳤다(김홍삼·김종수 2017). 평가자 편향 연구는 R&D 제안서에만 있다(윤석민 외 2021; 장덕희 외 2014). — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=4a33b07f76cda0a7b7998d826d417196)
- LLM 점수와 전문가 점수의 상관은 약하다(ρ≈0.22). LLM-as-judge는 조달 법리 평가에서 신뢰하기 어렵다. — [arXiv 2603.14565](https://arxiv.org/abs/2603.14565); [arXiv 2511.04205](https://arxiv.org/abs/2511.04205)
- HWP 문서 구조를 XML로 바꿔 제안서 접수와 평가를 자동화한 연구는 2001년 것만 확인되었다(권석훈 외 2001). — [RISS](https://www.riss.kr/search/detail/DetailView.do?p_mat_type=1a0202e37d52c72d&control_no=b331e922ce6ae65effe0bdc3ef48d419)

### Inferences
- 프로젝트가 논문이나 공개 산출물로 기여할 수 있는 지점은 다음과 같다.
  - (a) 공개 RFP로 만든 **한국어 요구사항 추출, 상세화 등급 분류 벤치마크**
  - (b) RFP 요구사항 ID와 제안서 섹션을 잇는 **추적성(traceability) 자동 점검**
  - (c) 사내 근거 KB를 활용한 RAG 생성과 '정보 부재'·'작성 품질'을 구분하는 평가 프로토콜(Yu et al. 2026의 방법론 차용)
  - (d) 결정적 체크리스트 검증과 LLM 판정을 결합한 하이브리드 품질평가
- 실제 평가점수와 연결하려면 협력사가 과거 제안서와 평가결과(기술점수, 순위)를 제공해야 한다. 공개 데이터만으로는 '점수 향상' 효과를 검증할 수 없다.

### Gaps
- 나라장터에서 공개되는 제안서 평가결과의 범위(업체별 기술점수, 평가위원별 점수 공개 여부)는 이번 학술 문헌 조사로 확인하지 못했다. 제도 담당 조사와 교차확인이 필요하다.
- 한국정보과학회(KCC/KSC), 한국정보처리학회(ACK/ASK), HCLT의 2024~2026 논문집은 전수 열람하지 못했다. manuscriptlink와 DBpia 개별 열람으로 후속 확인할 것을 권장한다.

---

### 부록: 전체 서지 목록 (주제별 빠른 참조, 49건)

**주제 1 – 평가 제도·평가위원 (13건: 국내 12, 해외 1)**: 김대식 외 2020 · 이윤선 2017(SPRi) · 김정욱 2012(KDI, `[P]`) · 임강희·강경환 2023 · 김훈희 외 2016 · 김홍삼·김종수 2017 · 윤석민 외 2021 · 장덕희 외 2014 · 정호용 2026 · Song et al. 2015 · 국방 R&D 제안서평가 학위논문(저자 미상, `[P]`) · 김정규 외 2011 · Pier et al. 2018

**주제 2 – RFP·요구사항 품질 (13건: 국내 11, 해외 2)**: 이현승·이윤선 2017(SPRi) · 이현승·이윤선 2018(SPRi) · 유호석 외 2018(SPRi) · 김준연·심기보 2014(SPRi) · 박상휘·김병초 2019 · 김홍섭 외 2013 · 박소현 외 2012 · 정재봉 외 2010 · 송형민 2020 · 윤영진 외 2022 · Song & Kim 2023 · Saito et al. 2012 · Paech et al. 2012

**주제 3 – 작성 전략·성공요인·가독성 (3건: 국내 2, 해외 1)**: Markowitz 2019 · Ham et al. 2025 · 이경배·오재인(`[P]`)

**주제 4 – AI/NLP (15건: 국내 4, 해외 11)**: 이선표 외 2022 · 임찬호·권헌영 2024 · 권석훈 외 2001 · 문형남 2025 · Yu et al. 2026 · Zhao & Li 2024 · Maji et al. 2020 · Rahman & Finin 2018 · Moiraghi et al. 2024 · Gao et al. 2026 · Mokhtari et al. 2026 · Zahid et al. 2021 · Ren & Wang 2025 · Sandström & Thelwall 2026 · Karp et al. 2025

**주제 5 – 나라장터 데이터 (5건: 국내 4, 해외 1)**: 최태홍 외 2018 · 이동근 외 2026 · 엄상훈·조인휘 2022 · 김정욱 2010(`[P]`) · Huber & Imhof 2021
