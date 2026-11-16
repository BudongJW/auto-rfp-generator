# 나라장터(조달청) SW·IT·용역 제안서의 양식·문서 형식·글꼴·시각 디자인 관행 (자동 생성기 기본값용)

> 조사 기준일: 2026-11-16. 조사 방법과 한계: 이 세션에서는 `law.go.kr`, `syu.ac.kr` 등 일부 호스트가 네트워크 정책으로 차단되어(WebFetch DNS 실패) 원문 PDF·HWP를 직접 열지 못했다. 아래 인용의 대부분은 **검색엔진이 해당 URL 본문에서 뽑아 준 요약·발췌**에 기반한다. 수치는 해당 URL에 있다고 보고된 값이지만 원문 대조는 하지 못했으므로, 생성기에 하드코딩하기 전에 원문 확인을 권한다. 예외로 HWPX 구조(6번 섹션)는 공개 패키지(python-hwpx)에 들어 있는 HWPX 템플릿을 직접 풀어 확인했다.

## 1. 공식 서식과 배포처, 표준 제안서 목차

### Takeaway
SW사업 제안서 목차의 "표준"은 정부 별지 서식 **[별지 제5호서식] 제안서 서식(예시: 소프트웨어개발, 유지관리사업)**이다. 구성은 Ⅰ.일반현황, Ⅱ.전략 및 방법론, Ⅲ.기술 및 기능, Ⅳ.성능 및 품질, Ⅴ.프로젝트 관리, Ⅵ.프로젝트 지원, Ⅶ.그 밖의 사항이다. 실제 RFP는 이를 변형한 "Ⅰ.제안 개요, Ⅱ.제안업체 일반, Ⅲ.기술·기능(수행부문), …, 관리부문, 지원부문" 형태를 많이 쓴다. 입찰 부속 서식(입찰참가신청서, 청렴계약이행서약서, 보안서약서, 개인정보 동의서, 하도급 계획서 등)은 표준 패키지가 없다. 대부분 **나라장터 공고 첨부 HWP/PDF의 "별지 서식"**으로 공고마다 배포되고 번호도 공고마다 다르다.

### Cited Findings
**A. 표준 제안서 목차(별지 제5호서식, 국가법령정보센터 행정규칙 별지)**
- 법제처 국가법령정보센터에 "[별지 제5호서식] 제안서 서식(예시: 소프트웨어개발, 유지관리사업) Ⅰ. 일반현황"이라는 제목의 별지 파일이 있다. 대분류는 Ⅰ 일반현황 → Ⅱ 전략 및 방법론 → Ⅲ 기술 및 기능 → Ⅳ 성능 및 품질 → Ⅴ 프로젝트 관리 → Ⅵ 프로젝트지원 → Ⅶ 그 밖의 사항 순이다 — [law.go.kr 별지5 제안서 서식](https://www.law.go.kr/LSW/flDownload.do?flSeq=153606573&flNm=%5B%EB%B3%84%EC%A7%80+5%5D+%EC%A0%9C%EC%95%88%EC%84%9C+%EC%84%9C%EC%8B%9D%28%EC%98%88%EC%8B%9C%3A+%EC%86%8C%ED%94%84%ED%8A%B8%EC%9B%A8%EC%96%B4%EA%B0%9C%EB%B0%9C%2C+%EC%9C%A0%EC%A7%80%EA%B4%80%EB%A6%AC%EC%82%AC%EC%97%85%29&bylClsCd=200203)
  - Ⅱ. 전략 및 방법론: 1.사업 이해도, 2.추진전략, 3.적용기술, 4.표준 프레임워크 적용, 5.개발 방법론 — (동일 출처)
  - Ⅲ. 기술 및 기능: 시스템 장비구성 요구사항, 기능 요구사항, 보안 요구사항(3번), 데이터 요구사항, 운영 요구사항, 6.제약사항 — (동일 출처)
  - Ⅳ. 성능 및 품질: 성능, 품질, 인터페이스, 테스트 요구사항 — (동일 출처)
  - Ⅴ. 프로젝트 관리: 관리방법론, 관리역량, 일정계획, 개발장비 — (동일 출처)
  - Ⅵ. 프로젝트 지원: 1.품질보증, 2.시험운영, 3.교육훈련, 4.유지보수, 5.기밀보안, 6.비상대책 — (동일 출처)
- 한국소프트웨어산업협회 「소프트웨어 사업 가이드북 ver 3.0」은 제안서 목차 예시를 **제안개요 → 제안업체 일반 → 관리부문 → 기술부문 → 지원부문 → 기타 → 첨부** 순으로 제시한다 — [KOSA SW사업 가이드북 v3.0 PDF](https://www.sw.or.kr/upload/common/027d281c-2a7a-4886-b96b-e9ad04c7a309.pdf)
- 대학 RFP 작성방법 문서의 "작성 항목" 표는 "Ⅰ. 제안개요 / Ⅱ. 제안업체 일반: 1.일반현황 2.조직 및 인원 3.주요사업내용 4.주요사업실적"으로 시작한다(검색 결과 문서 제목에서 확인) — [삼육대 제안요청서 작성방법 PDF](https://www.syu.ac.kr/wp-content/uploads/2020/01/%EC%A0%9C%EC%95%88%EC%9A%94%EC%B2%AD%EC%84%9C-%EC%9E%91%EC%84%B1%EB%B0%A9%EB%B2%95.pdf)
- 민간 PMS 구축 RFP의 목차 1번 "제안 개요"는 제안 배경·목적, 제안 범위, 사업 추진 전략, 기대효과로 구성된다. 이 RFP는 제안사가 목차 순서를 바꿀 수 있다고 허용한다 — [티시스 PMS 구축 RFP](https://www.tsis.co.kr/download/PMS_RFP_20180112.pdf)
- 공공기관 RFP는 일반현황 항목으로 "제안사의 일반현황 및 주요 연혁", "조직 및 인원현황", "최근 3년간 자본금 및 부문별 매출액"을 요구한다. 관리부문으로는 추진일정, 보고·검토계획, 수행조직·업무분장, 작업 단위별 참여인력·이력사항을 요구한다(SPRI RFP 다수) — [SPRI SW산업 동향 용역 RFP(2015)](https://spri.kr/download/6770), [SPRI 홈페이지 유지보수 RFP(2018)](https://spri.kr/download/21868)
- 같은 SPRI 계열 RFP 작성지침은 번호 체계 **Ⅰ → 1 → 가 → o**를 쓴다. 영문 약어는 약어표를 함께 쓰게 하고, 해당 내용이 없으면 "해당사항 없음"으로 적게 한다 — [SPRI RFP](https://spri.kr/download/21868), [SPRI 월간SW중심사회 RFP(2017)](https://www.spri.kr/download/21616)

**B. SW사업 관련 정부 지침·가이드와 그 서식**
- 「소프트웨어사업 계약 및 관리감독에 관한 지침」 최근 확인본은 2023.5.15 시행 과학기술정보통신부고시 제2023-15호다 — [law.go.kr 행정규칙](https://www.law.go.kr/LSW//admRulInfoP.do?admRulSeq=2100000207648&chrClsCd=010201), [ulex 사본](https://www.ulex.co.kr/%EB%B2%95%EB%A5%A0/2100000223356-33440-%EC%86%8C%ED%94%84%ED%8A%B8%EC%9B%A8%EC%96%B4)
  - 확인된 서식: 소프트웨어사업 영향평가 결과서(제5조), 소프트웨어사업 하도급 계획서, 하도급계약의 적정성 판단 자기평가표(별지 제8호), 과업내용(확정/변경) 종합심의 결과서(별지 제11호, 제25·26조), 과업내용 사전검토 요청서, 과업변경요청서(제26조), 과업내용변경 관리내역서(제28조), 서약서(별지 제5호). 별표 2는 "소프트웨어사업 상세 요구사항 분석·적용기준(제11조)"이다 — [law.go.kr 별지 제11호서식](https://www.law.go.kr/LSW//flDownload.do?flSeq=128124963&flNm=%5B%EB%B3%84%EC%A7%80+11%5D+%EA%B3%BC%EC%97%85%EB%82%B4%EC%9A%A9%28%ED%99%95%EC%A0%95%2F%EB%B3%80%EA%B2%BD%29+%EC%A2%85%ED%95%A9+%EC%8B%AC%EC%9D%98+%EA%B2%B0%EA%B3%BC%EC%84%9C%28%EC%A0%9C25%EC%A1%B0+%EB%B0%8F+%EC%A0%9C26%EC%A1%B0+%EA%B4%80%EB%A0%A8%29&bylClsCd=200203), [law.go.kr 별표·서식](https://www.law.go.kr/LSW//admRulBylInfoP.do?bylSeq=2597963&admRulSeq=2100000223356&directYn=Y)
  - 이 지침의 별지 목록에서는 "제안서 서식", "요구사항 추적표", "보안각서"를 확인하지 못했다(검색 요약 기준) — (동일 출처)
- 과기정통부 「공공SW사업 제안요청서 작성 예시」(2022.07, 「공공SW사업 법제도 관리감독 및 지원 가이드」 부록)에는 RFP에 넣어야 할 SW 법·제도 **18개 항목**의 작성 예시가 있다. 함께 실린 내용은 제안서 목차 가이드, 제안서 세부작성 가이드, 서식 목록(예: 서식1 과업변경요청서, 서식2 SW 하도급 계획서 적정성 확인서)이다 — [작성 예시 PDF(smallake 사본)](https://smallake.kr/wp-content/uploads/2023/03/%EB%B6%99%EC%9E%84%EA%B3%B5%EA%B3%B5SW%EC%82%AC%EC%97%85-%EC%A0%9C%EC%95%88%EC%9A%94%EC%B2%AD%EC%84%9C-%EC%9E%91%EC%84%B1-%EC%98%88%EC%8B%9C.pdf), [정보통신신문 보도](https://www.koit.co.kr/news/articleView.html?idxno=99922), [상명대 게시 부록 HTML](https://www.smuc.ac.kr/flexer/out/_attach/file/2022/06//yGLIkXhXNUGhqwpjOVnp.hwp.files/Sections1.html)
- NIPA 「공공SW사업 제안요청서 작성 매뉴얼」 2010.12 재개정판이 NIPA 게시판에 있다(오래된 자료) — [NIPA 게시물](https://www.nipa.kr/home/2-8/5419)
- 2021 「공공SW사업 제안요청서 작성을 위한 요구사항 실무 가이드」(SW진흥법 제44조, 계약·관리감독 지침 제11조 근거)는 기능, 성능, 시스템 장비구성, 인터페이스, 데이터 요구사항의 상세화 방법과 사례를 담고 있으며 SW산업종합정보시스템에 게시되어 있다 — [swit.or.kr 자료실](https://www.swit.or.kr/IS/web/isCbmRefView.jsp?ref_sq=1104&schCode=13)
- 「행정기관 및 공공기관 정보시스템 구축·운영 지침」 제16조는 제안서의 규격, 제출방법, 제본형태를 제안요청서에 명시하도록 한다 — [lbox 행정규칙](https://lbox.kr/statute-admin/%ED%96%89%EC%A0%95%EA%B8%B0%EA%B4%80%EB%B0%8F%EA%B3%B5%EA%B3%B5%EA%B8%B0%EA%B4%80%EC%A0%95%EB%B3%B4%EC%8B%9C%EC%8A%A4%ED%85%9C%EA%B5%AC%EC%B6%95%E3%86%8D%EC%9A%B4%EC%98%81%EC%A7%80%EC%B9%A8)

**C. 요구사항 ID 체계(요구사항 대비표·추적표 매핑의 키)**
- 공공 RFP는 요구사항에 고유번호를 붙이고, 제안자는 그 번호에 맞춰 제안서를 쓴다. 분류 예: SFR(System Function Requirement, 기능), PER(Performance, 성능), INR(Interface, 인터페이스·웹 접근성) — [한국어 위키백과 '요구사항'](https://ko.wikipedia.org/wiki/%EC%9A%94%EA%B5%AC%EC%82%AC%ED%95%AD), [IT위키 '제안요청서'](https://itwiki.kr/w/%EC%A0%9C%EC%95%88%EC%9A%94%EC%B2%AD%EC%84%9C)
- 실제 RFP에도 ECR(Equipment Composition Requirement, 시스템 장비구성), DAR(Data Requirement), INR, SIR(System Interface Requirement) 같은 코드가 쓰인다 — [한국예탁결제원 차세대 RFP(2024.11)](https://smallake.kr/wp-content/uploads/2024/01/%EC%98%88%ED%83%81%EC%B0%A8%EC%84%B8%EB%8C%80%EC%A0%9C%EC%95%88%EC%9A%94%EC%B2%AD%EC%84%9C.pdf), [한국투자공사 AI 플랫폼 RFP(2025.9, 나라장터)](https://www.g2b.go.kr/pn/pnp/pnpe/UntyAtchFile/downloadFile.do?bidPbancNo=R25BK01077222&bidPbancOrd=000&fileType=&fileSeq=4)

**D. 입찰·제안 부속 서식(나라장터 공고 첨부에서 확인된 예)**
- 공고 첨부 "입찰제출 서류 자가체크"와 서식 예: 입찰참가신청서(한 공고에서는 별지 6호, "입찰 조건을 모두 승낙하고 입찰공고사항을 모두 준수합니다"), 청렴계약 이행서약서(별지서식 15), 개인정보 수집·이용 동의서(참여인원 전원, 서식14), 보안서약서 및 보안확약서(서식16), (재)하도급 금지 확약서 1부(원본) — [나라장터 공고 첨부(R25BK00907452)](https://www.g2b.go.kr/pn/pnp/pnpe/UntyAtchFile/downloadFile.do?bidPbancNo=R25BK00907452&bidPbancOrd=000&fileType=&fileSeq=2), [나라장터 용역 입찰공고(2025.3.19)](https://www.g2b.go.kr/fs/fsc/fsca/fileUpload.do?k00=a2MMYzianzwExorC2swMQwxC2sxMgwLazI2DC9kYXRhL0F0dGFjaGZpbGVzL3BucGUvMjAyNS8wMy8xOS9jOTNlNTk4NzkwMzE0MmEzYWNkYmU4NDMwZDhkMGJkZS5wZGYLazMxDCVFQyU5RSU4NSVFQyVCMCVCMCVFQSVCMyVCNSVFQSVCMyVBMCVFQiVBQyVCOF8lRUMlODglOTglRUIlQTYlQUMlRUElQjMlQkMlRUQlOTUlOTkrJUVDJTk3JUIwJUVBJUI1JUFDJUVBJUIzJUJDJUVDJUEwJTlDKyVFQSVCNCU4MCVFQiVBNiVBQyVFQyU4QiU5QyVFQyU4QSVBNCVFRCU4NSU5QyslRUElQjMlQTAlRUIlOEYlODQlRUQlOTklOTQrJUVDJTgyJUFDJUVDJTk3JTg1LnBkZgtrMjEMNjE1NTFiNjMtMjhiNS00YjI3LWEzMWItMjZlMGY0MmQ2YjQ2LDEL)
- 나라장터 제출 화면에서 문서마다 **문서구분(정성제안서, 정량제안서, 발표자료, 제안요약서, 하도급 계획서, 기타문서 등)**을 지정해 올린다 — (위 두 나라장터 첨부 중 하나. 검색 요약상 출처가 어느 쪽인지 특정하지 못함)
- 같은 계열 공고는 "업체정보 삭제본"이면 표지와 내지에서 회사명, CI, 대표자 등 제안업체를 알 수 있는 부분을 모두 지우게 한다 — (동일 출처)
- 연구기관 입찰 사례는 "입찰 및 제안평가 안내서"와 "제출서류 기본양식.hwp"를 별도 HWP로 배포한다 — [nnfc 제출서류 기본양식.hwp 뷰어](https://www.nnfc.re.kr/thumbnail/viewer/1790846091559/index.html), [nnfc 입찰 및 제안평가 안내서.hwp 뷰어](https://www.nnfc.re.kr/thumbnail/viewer/1792336647386/index.html)
- 같은 "별지 제5호"라도 RFP마다 내용이 다르다(예: SPRI RFP는 별지 제5호를 참여인력 이력사항 서식으로 씀) — [SPRI 홈페이지 유지보수 RFP](https://spri.kr/download/21868)
- 나라장터는 2025.1.6 새 시스템으로 개편되었으므로 그 이전 매뉴얼·양식은 최신 공고와 다를 수 있다 — [나라장터 공고 첨부(R25BK00907452)](https://www.g2b.go.kr/pn/pnp/pnpe/UntyAtchFile/downloadFile.do?bidPbancNo=R25BK00907452&bidPbancOrd=000&fileType=&fileSeq=2)
- 국립국어원 2026 공고는 "목차/평가조견표"를 요구하면 나라장터 해당 화면에서 조견표를 작성·제출하도록 안내한다 — [국립국어원 입찰공고](https://www.korean.go.kr/front/board/boardStandardView.do;front=F36CEF34D1A4633ACD6711EAAABBDD21?board_id=5&b_seq=2635&mn_id=183)

### Inferences
- 별지 제5호서식은 「소프트웨어사업 계약 및 관리감독에 관한 지침」 소속이 아닐 가능성이 크다. 그 지침에서 별지 제5호는 "서약서"로 확인되기 때문이다. 다른 행정규칙(예: 「행정기관 및 공공기관 정보시스템 구축·운영 지침」)의 별지로 추정되지만 원문으로 확인하지 못했다.
- 생성기 기본 목차는 아래 하이브리드를 권장한다. 별지5의 Ⅱ~Ⅵ(평가표의 "기술·기능/성능·품질/관리/지원"에 대응)에 RFP 관행의 "제안 개요·제안업체 일반"을 앞에 붙인 형태다. RFP가 목차를 지정하면 그 목차를 1순위로 덮어쓴다.
  - Ⅰ. 제안 개요(1.제안 목적·범위 2.제안의 특징 및 장점 3.사업 이해도/추진전략)
  - Ⅱ. 제안업체 일반(1.일반현황 2.조직 및 인원 3.주요 사업내용 4.주요 사업실적·유사실적)
  - Ⅲ. 전략 및 방법론(사업 이해도, 추진전략, 적용기술, 표준프레임워크, 개발방법론)
  - Ⅳ. 기술 및 기능(ECR, SFR, SER, DAR, 운영, COR)
  - Ⅴ. 성능 및 품질(PER, QUR, INR, TER)
  - Ⅵ. 프로젝트 관리(관리방법론, 관리역량, 일정계획, 개발장비)
  - Ⅶ. 프로젝트 지원(품질보증, 시험운영, 교육훈련, 유지보수, 기밀보안, 비상대책)
  - Ⅷ. 기타(하도급 계획, 약어표, 별첨 서식)
- 요구사항 대비표(추적표)의 표준 열 구성(공식 서식)은 찾지 못했다. 업계 관행으로는 [요구사항 ID | 요구사항 명칭 | 분류 | 제안 내용 요약 | 수용 여부(수용/부분/대안) | 제안서 페이지] 형태가 흔한 것으로 보이며, 이는 추정이다. ptlink·velog가 말하는 "요구사항→목차→페이지 매핑"(4번 섹션)과도 맞는다.
- 부속 서식은 공고마다 번호와 양식이 다르다. 그래서 생성기는 "공고 첨부 HWP 별지 서식을 파싱해 채우는" 방식이 맞고, 자체 고정 양식을 만들면 맞지 않는다.

### Gaps
- 별지 제5호서식 원문(law.go.kr)을 직접 열지 못했다. Ⅰ 일반현황과 Ⅶ 그 밖의 사항의 하위 항목, 표 열 구성(참여인력·수행실적 표)은 확인하지 못했다.
- 「소프트웨어사업 계약 및 관리감독에 관한 지침」의 2023년 이후 개정 여부(2024~2026)와 최신 별지 전체 목록은 확인하지 못했다.
- 조달청 홈페이지 "서식자료실"에 SW사업 제안서용 표준 서식 묶음이 있는지는 검색으로 찾지 못했다.
- 요구사항 분류 코드 중 TER(테스트), SER(보안), QUR(품질), COR(제약사항), PMR(프로젝트관리), PSR(프로젝트지원)은 업계에서 널리 쓰인다고 알려져 있지만, 이번 검색에서 출처로 확인하지 못했다.
- 제안서 표지, 제안서 요약서, 가격제안서의 표준 서식 원문을 확보하지 못했다.

## 2. 문서 형식 관행: HWP·PPT, 용지 방향, 분량, 제출 형식, 블라인드

### Takeaway
나라장터 전자제출은 **"제안서류 일체 PDF, 총 300MB 이하"**가 공통 문구다. 편집 프로그램과 용지 방향은 RFP가 대부분 자유롭게 두고 **A4**만 원칙으로 정한다. 분량은 본문 50~200쪽(가장 흔한 값은 100쪽 이내), 요약본 20~50쪽(흔히 30쪽 이내, 발표본으로 대체 가능)으로 공고마다 다르다. 블라인드 평가가 적용되면 제안서·요약본·발표자료 전부에서 회사명, 로고, CI, 대표자명을 지워야 하고, 어기면 감점이다.

### Cited Findings
**제출 형식·용량**
- "국가종합전자조달시스템(나라장터)을 통해 제출하는 제안서류 일체는 PDF 파일 형식으로 제출하여야 하며, 총 용량은 300MB를 초과할 수 없습니다." 제출 경로: 나라장터 > 입찰 > 입찰진행/참가 > 투찰 → "입찰서류제출현황" 팝업 → "제안서제출바로가기" — [나라장터 입찰공고문 작성시 이용안내(2025.4.2 첨부 PDF)](https://www.g2b.go.kr/fs/fsc/fsca/fileUpload.do?k00=a2MMYzianzwExorC2swMQwxC2swNQwwC2syNgwvZGF0YS9BdHRhY2hmaWxlcy9wbnBlLzIwMjUvMDQvMDIvYTFhN2VkYjQxMjkzNGNmZGFhMjllNjE3NDI0YzhmZWIucGRmC2szMQzrgpjrnbzsnqXthLAg7J6F7LCw6rO16rOg66y4IOyekeyEseyLnCDsnbTsmqnslYjrgrQucGRmC2syMQxmNjg5NjNmMi00YjI1LTRjZDktYmY2NS05ZTAyYmIxNTk3MDksMQ%3D%3D), 같은 문구가 [국립국어원 2026 입찰공고](https://www.korean.go.kr/front/board/boardStandardView.do;front=F36CEF34D1A4633ACD6711EAAABBDD21?board_id=5&b_seq=2635&mn_id=183)에도 있음
- 연구과제 제안서 양식은 "한글 자체 PDF 변환하여 제출"하게 한다 — [질병관리청 제안서 양식](https://www.kdca.go.kr/bbs/kdca/51/255153/download.do)

**분량·용지 규정 예(2025~2026 나라장터 첨부 RFP 중심)**
| 공고 | 본문 분량 | 요약본/발표 | 기타 | 출처 |
|---|---|---|---|---|
| 대학 AI 서비스 플랫폼 구축(2025.07) | A4, 가급적 100쪽 이내 | A4 단면, 가급적 30쪽 이내(발표본으로 대체 가능) | — | [g2b 첨부](https://www.g2b.go.kr/fs/fsc/fsca/fileUpload.do?k00=a2MMYzianzwExorC2swMQwxC2sxMgwLazI2DC9kYXRhL0F0dGFjaGZpbGVzL3BucGUvMjAyNS8wNy8wOS81ZDM3NmY3ZmJmODQ0Yzg1YjcyODE1MmRmMmJmMzVlMC5wZGYLazMxDCVFQyVBMCU5QyVFQyU5NSU4OCVFQyU5QSU5NCVFQyVCMiVBRCVFQyU4NCU5QyUyNiUyMzQwJTNCJUVEJTk1JTlDJUVBJUI1JUFEJUVDJTk3JUI0JUVCJUE2JUIwJUVDJTgyJUFDJUVDJTlEJUI0JUVCJUIyJTg0JUVCJThDJTgwJUVEJTk1JTk5JUVBJUI1JTkwK0FJKyVFQSVCOCVCMCVFQiVCMCU5OCslRUQlOTUlOTklRUMlOEElQjUlRUMlQTclODAlRUMlOUIlOTArJUVEJTk0JThDJUVCJTlFJUFCJUVEJThGJUJDKyVFQSVCNSVBQyVFQyVCNiU5NSUyNiUyMzQxJTNCLnBkZgtrMjEMYTAxMTJmZWEtYjJlNi00YzM4LThhNjQtNWUxN2VhNmVkNTFiLDIL) |
| 서울디자인재단·DDP 홈페이지 기능 개선(2025.6) | **200쪽(100장) 이내** | — | A4, PDF로 나라장터 제출 | [g2b R25BK00989759](https://www.g2b.go.kr/pn/pnp/pnpe/UntyAtchFile/downloadFile.do?bidPbancNo=R25BK00989759&bidPbancOrd=000&fileType=&fileSeq=2) |
| 디지털콘텐츠 표준약관 개정(2025.4) | A4, 본문 50쪽 이내 | — | — | [g2b R25BK00803531](https://www.g2b.go.kr/pn/pnp/pnpe/UntyAtchFile/downloadFile.do?bidPbancNo=R25BK00803531&bidPbancOrd=000&fileType=&fileSeq=1) |
| 우수 디자인상품 마케팅 운영(2025) | — | PT 발표본 **A4 가로**, 총 50쪽 이내 | — | [g2b R25BK00822111](https://www.g2b.go.kr/pn/pnp/pnpe/UntyAtchFile/downloadFile.do?bidPbancNo=R25BK00822111&bidPbancOrd=000&fileType=&fileSeq=2) |
| 충북 수출상품 가이드 제작(2025.04) | A4 20쪽 이내, "제안서 목차" 순서대로 | — | — | [청주상의 RFP](https://cheongjucci.korcham.net/file/dext5uploaddata/2025/%5B%EC%9C%A0%EC%B2%A8%202%5D%20%EC%A0%9C%EC%95%88%EC%9A%94%EC%B2%AD%EC%84%9C.pdf) |
| 한국투자공사 인사시스템 운영(2026.6) | A4 원칙, **편집프로그램·분량 제한 없음**, 표준어 | — | — | [KIC RFP](https://www.kic.kr/api/medias/download?key=ol5n23) |
| 한국해외인프라도시개발지원공사 용역(2023.10) | A4 20쪽 내외(표지·목차 제외) | — | **본문 13pt, 표 안 12pt 가능, 아래한글 작성 권장** | [KIND RFP](https://www.kindkorea.or.kr/api/v1/attachment/9752e2c2-c190-4d99-af2b-536dcd6ed5c2/download) |
| 한국공인회계사회 | A4 100쪽 이내(자유 양식) | 요약서 별도 | — | [KICPA](https://www.kicpa.or.kr/board/read.brd?boardId=stable&bltnNo=11650274117987&cmd=READ) |
| 코레일유통 사업제안 | A4 기본, 매수 제한 없음 | 항목별 1~2쪽 요약 권장 | — | [코레일유통](https://www.korailretail.com/files/sample01.pdf) |
| (민간) 롯데손보 그룹웨어 고도화(2025.07) | 제안서 5부 | 요약서(발표본) 10부 | 인쇄본 부수 지정 | [롯데손보 RFP](https://www.lotteins.co.kr/upload/C/board/2025/07/7/LOTTEINS%20Groupware%20System%20RFP.pdf) |

- 실무 블로그에 따르면 정성 제안서는 보통 100쪽 이내이고, "50페이지 정도로 요약한 정성적 제안서와 30페이지 정도의 발표본"을 별도로 명시하는 공고가 많다 — [documento FAQ](https://www.documento.co.kr/87/?bmode=view&idx=60062037)
- 같은 실무 자료는 공고에 없는 사항은 발주처 담당 주무관에게 문의하라고 하고, 제공된 목차를 임의로 바꾸면 불리하다고 본다 — [documento FAQ](https://www.documento.co.kr/87/?bmode=view&idx=60062037)

**HWP(세로) vs PPT(가로)**
- 템플릿 판매자들의 설명: 제안서는 "일반적으로 A4 세로 형태이며 최근에는 가로 형태도 사용"한다. 가로형을 권하는 근거로는 인쇄물 제출 지양과 비대면·화면 평가 증가를 든다. 공공기관 입찰용 "세로형 PPT" 템플릿도 따로 판매된다 — [크몽 리마스터링 세로/가로](https://kmong.com/gig/558647), [크몽 가로형 템플릿](https://kmong.com/gig/593259), [크몽 공공기관 세로형 PPT](https://kmong.com/gig/731092)
- 같은 45억 규모 시스템 구축 제안서가 "A4 세로형 제안서"와 "A3 가로형 제안서(떡제본)" 두 형태로 공개된 사례가 있다. 정성/정량/A3 가로형으로 파일을 나누어 구성한다 — [documento 입찰 제안서 PPT 원본](https://www.documento.co.kr/36), [documento A3 사이즈 제안서](https://www.documento.co.kr/notice/?idx=18952054&bmode=view)
- 목차는 엑셀로 관리하고, A3 페이지가 섞이면 최종 쪽번호를 반드시 다시 확인하라는 실무 권고가 있다 — [documento 제안 목차 만들기](https://www.documento.co.kr/notice/?idx=15972385&bmode=view)

**발표**
- 제안발표는 보통 발표 20분, Q&A 10분이다. 발표와 질의응답이 각각 10분인 사례도 있다 — [클리앙 '나는 PM이다 - 제안발표'](https://www.clien.net/service/board/lecture/11882827), [AI허브 Q&A](https://aihub.or.kr/community/question/6913)
- 장수 권장: 20분 발표에 20~25장(장당 1~2분). "20분이면 30장을 넘지 않아야 한다"는 의견도 있다. 사전 등록 자료 외 배포물은 인정되지 않는 경우가 많다 — [파란디자인 발표자료 구성](https://parancompany.co.kr/blog/%ED%96%89%EC%82%AC-%EB%B0%9C%ED%91%9C-%EC%9E%90%EB%A3%8C-%ED%94%84%EB%A0%88%EC%A0%A0%ED%85%8C%EC%9D%B4%EC%85%98-%EA%B5%AC%EC%84%B1-%EA%B0%80%EC%9D%B4%EB%93%9C), [클리앙 20분 발표 분량](https://www.clien.net/service/board/park/14394670)

**블라인드(업체명 비식별) 규정**
- 공공기관 평가위원회 지침의 예(제9조의3): 블라인드 평가를 하면 "평가위원에게 배부하는 제안서, 요약본, 발표자료 및 기타 제출자료 일체에 회사명, 로고 및 특정 제안업체를 식별할 수 있는 모든 표시를 할 수 없으며, 이를 위반할 경우 감점처리"한다. 발표자가 회사명을 언급하는 것도 금지된다. 접수 방법과 감점 기준은 RFP에 명시한다. 단 "조달청에 제안서 평가를 의뢰하는 경우는 제외"된다 — [한국폴리텍대학 규정 사본](https://rule.kopo.ac.kr/service/law/detailArticlePrint.do?seq=100&historySeq=899&contentSeq=64090)
- 나라장터 공고 예: "업체정보 삭제본의 경우 표지 및 내지에 제안업체를 알 수 있는 부분(회사명, CI, 대표자 등)은 표기 불가하므로 모두 삭제하여 제출" — [나라장터 공고 첨부(R25BK00907452)](https://www.g2b.go.kr/pn/pnp/pnpe/UntyAtchFile/downloadFile.do?bidPbancNo=R25BK00907452&bidPbancOrd=000&fileType=&fileSeq=2)
- 조달청 협상계약 평가기준 개정(2024.9.13 시행): 제안서나 발표에 타 업체 비방 내용을 넣으면 불이익을 받을 수 있고, 허위 내용 판단 절차가 명확해졌다 — [조달청 보도자료](https://www.pps.go.kr/kor/bbs/view.do?key=00634&bbsSn=2409110017)

### Inferences
- 생성기의 최종 산출물은 PDF여야 하며, 공고 단위로 "총 용량 300MB 이하" 검증을 넣어야 한다. 원본 편집 포맷(HWPX 또는 PPTX)은 내부 중간물로만 쓴다.
- 기본 레이아웃 프로필은 두 가지다. ① **본 제안서(정성제안서): A4 세로, HWPX → PDF**(KIND·KDCA·KICPA처럼 "아래한글 작성 권장"·"한글 자체 PDF 변환" 사례가 있음). ② **요약본·발표자료: A4 가로(또는 16:9) PPTX → PDF**. SI 대형 사업에서는 본문까지 PPT 가로형 장표로 쓰는 관행도 있으므로(크몽, documento) 출력 모드를 둘 다 지원하는 편이 안전하다.
- 분량 기본값: 본문 100쪽, 요약본 30쪽, 발표 25장(20분 기준). 실제 값은 RFP 파싱 결과로 덮어쓴다. 쪽수를 셀 때 표지·목차·간지를 빼는지("표지·목차 제외")도 파싱 대상이다.
- 블라인드 모드 플래그가 켜지면 회사명, 로고, CI 색상 패턴, 대표자명, 자사 솔루션 상표, 머리말·꼬리말의 업체 표기, PDF 메타데이터(Author/Producer/Title)를 모두 일괄 마스킹해야 한다. 마지막 항목(메타데이터)은 블라인드 위반 검사에서 놓치기 쉽다는 점에서 나온 추론이다.

### Gaps
- 조달청에 평가를 의뢰한 SW사업(조달청 "협상에 의한 계약 제안서평가 세부기준")에도 블라인드 의무가 있는지, 그 감점 수치는 원문으로 확인하지 못했다(law.go.kr 접근 불가).
- 쪽번호·머리말 규칙(예: "하단 중앙 쪽번호", "머리말에 사업명")을 명문화한 RFP 원문 문구는 찾지 못했다.
- 인쇄본 부수·제본 방식(공공 SW사업에서 현재도 인쇄본을 요구하는 비율)은 공공 RFP 근거를 확보하지 못했다(민간 롯데손보 사례만 확인).
- 공통 "글자 크기 최소 pt" 규정은 없고 공고마다 다르다. SW사업 RFP에서 최소 글자 크기를 명시한 사례는 이번 검색에서 KIND(13pt) 1건뿐이었다.

## 3. 글꼴: 정부 보고서 관행, 제안서 글꼴, 라이선스

### Takeaway
공문서 관련 법령과 편람은 본문 글꼴·크기를 강제하지 않는다. 다만 정부 보고서체 관행은 매우 강하다. 제목은 **HY헤드라인M**(약 20~22pt), 본문은 **휴먼명조 15pt**(14~15pt), 참조·주석은 **중고딕 13pt**, 줄간격은 **160%**이고, 기호는 □ → ○ → - → ※ 순서로 쓴다. 그러나 이 글꼴들은 한컴오피스 번들 글꼴이라 한컴오피스 밖(자동 생성 파이프라인의 PDF 렌더링 등)에서 쓰면 라이선스 문제가 생길 수 있다. 자동화 기본값은 OFL·KOGL 글꼴(나눔, Noto Sans/Serif KR, Pretendard(GOV), KoPub World)로 잡는 것이 안전하다.

### Cited Findings
**정부 보고서·공문 관행**
- 행정안전부 주무관(방송 인터뷰): 문서 제목은 **HY헤드라인M 22pt**, 소제목은 **16pt**, 본문은 **휴먼명조 15pt**, 참조 사항은 **중고딕 13pt**, **줄간격 160%**다. 한글 문서의 좌우 여백은 20, 20으로 맞추고 머리말·꼬리말은 10, 15, 10, 10을 지킨다 — [허프포스트코리아](https://www.huffingtonpost.kr/news/articleView.html?idxno=108786), [허프포스트 동일기사](https://huffingtonpost.kr/entry/yoo-quiz_kr_6077a1e2e4b020e576c0718f)
- 공무원 보고서 관행: 휴먼명조에 14~15pt가 기본이고, 줄간격은 150~160%까지 줄일 수 있으며, 중요 부분은 볼드로 처리한다(2014) — [머니투데이](https://news.mt.co.kr/mtview.php?no=2014071513235523905)
- 개인 정리 문서(kordoc): 편람과 시행규칙은 본문 글꼴과 크기를 정하지 않으며, 줄간격도 단일 표준이 없고 160%는 관행이다. 기호별 관행은 □는 HY견고딕 또는 HY헤드라인M, ○는 한컴돋움 굵게, -는 휴먼명조 본문이다. 일반 기안문은 명조 14~15pt 또는 맑은고딕 11.5pt를 쓴다 — [GitHub chrisryugj/kordoc gongmunseo-reference.md](https://github.com/chrisryugj/kordoc/blob/main/docs/gongmunseo-reference.md)
- 「행정업무운영 편람」(2020)은 민원서식 등 "큰 글자 서식"의 설계기준으로 **글자크기 13pt 확대, 맑은고딕으로 글자체 변경, 작성란 확대**를 제시한다 — [행정업무운영 편람 2020 PDF 사본](https://shortudy.s3.ap-northeast-2.amazonaws.com/notice/16245045071352020+%E1%84%92%E1%85%A2%E1%86%BC%E1%84%8C%E1%85%A5%E1%86%BC%E1%84%8B%E1%85%A5%E1%86%B8%E1%84%86%E1%85%AE%E1%84%8B%E1%85%AE%E1%86%AB%E1%84%8B%E1%85%A7%E1%86%BC%E1%84%91%E1%85%A7%E1%86%AB%E1%84%85%E1%85%A1%E1%86%B7.pdf)
- 편람 기반 공문 작성 자료에는 "기본 줄 간격 123%" 언급이 있다고 검색 요약에 나온다. 원문은 미확인 — [경기도교육청 '한 곳에 정리한 공문서 작성법'](https://www.goe.go.kr/resource/old/BBSMSTR_000000000028/BBS_202410150153084250.pdf)
- 실제 기관 문서의 HTML 변환 스타일시트에서 한글 본문은 휴먼명조 15pt, 제목 계열은 HY헤드라인M 16pt로 지정된 것이 확인된다 — [ETRI 문서 미리보기 styles.css](https://www.etri.re.kr/preview/1686116956082/styles.css)

**제안서·연구계획서 양식에 명시된 글꼴 예**
- 질병관리청 연구 제안서 양식: 본문 굴림체 11pt·줄간격 160%, 제목 신명조 12pt, A4 — [KDCA 양식](https://www.kdca.go.kr/bbs/kdca/51/255153/download.do)
- KIND 용역 RFP: 본문 13pt, 표 안 12pt, 아래한글 권장 — [KIND RFP](https://www.kindkorea.or.kr/api/v1/attachment/9752e2c2-c190-4d99-af2b-536dcd6ed5c2/download)
- 삼성미래기술육성재단 Proposal Guide(연구계획서, 조달 아님): A4 1단, 상하 여백 25mm, 좌우 20mm, 폰트 11 이상, 줄간격은 MS-Word 1.5 이상 또는 한글 150% 이상, 국문은 돋움 또는 바탕 — [Samsung STF Proposal Guide](https://www.samsungstf.org/webfile2/programAttach/202407261418394__Full_Proposal_Guide_t.pdf)
- 공모전 아이디어 제안서(참고): 본문 맑은고딕 12pt, 줄간격 160% — [linkareer 양식](https://media-cdn.linkareer.com/activity_manager/applications/278333)
- PPT 제안서 템플릿에는 무료 글꼴인 에스코어드림이 많이 쓰이고, 대안으로 Noto Sans KR, KoPub 돋움, Pretendard가 언급된다 — [파란디자인 PPT 가이드](https://parancompany.co.kr/blog/ppt-design-guide), [디자인킵 템플릿](https://designkeep.co.kr/28/?idx=315)

**라이선스**
- 한컴 서체 라이선스 페이지(한컴 산스 등 한컴 자체 서체): 인쇄물, 광고, 온라인 등 상업적 사용이 가능하고, 사용범위 표에 "인쇄 및 문서 공유를 위한 PDF 파일 제작"과 "폰트파일 임베이딩"이 허용 항목으로 있다. 글꼴 판매, 수정, 재배포는 금지된다 — [한컴 서체 라이센스](https://font.hancom.com/pc/sub/sub3_1.php)
- 한컴 측 설명(2016 보도): 한컴오피스 안에서 만든 결과물을 이미지나 PDF로 저장해 상업적으로 쓰는 것은 허용된다. 그러나 번들 글꼴을 한컴오피스 밖의 다른 프로그램에서 쓰면 라이선스 위반이 될 수 있다 — [한국경제 '폰트에도 저작권'](https://plus.hankyung.com/apps/newsinside.view?aid=201607195492A&category=AA010&sns=y)
- 함초롬체(한컴 기본 글꼴)의 라이선스는 출처마다 다르다. 나무위키는 "임베딩 포함 자유 사용 가능한 상업용 무료"라고 쓰고, 글꼴마루는 임베딩에 사전 동의가 필요하다고 쓰며, typedia는 "상업적 목적으로 배포 및 수정 불가"라고 쓴다 — [나무위키 함초롬체](https://namu.wiki/w/%ED%95%A8%EC%B4%88%EB%A1%AC%EC%B2%B4), [글꼴마루 함초롬돋움](https://fonts.asamaru.net/fonts/%ED%95%A8%EC%B4%88%EB%A1%AC%EB%8F%8B%EC%9B%80%EC%B2%B4/), [typedia 함초롬돋움](https://typedia.kr/font/hcrdotum/)
- 문체부 "안심글꼴": 공공누리 제1유형(출처표시) 조건으로 상업적 이용, 변경, 2차 저작물 작성이 가능하다. 문체부 누리집, 공공누리, 공유마당에서 받을 수 있다. 한컴오피스 2018/2020 글꼴 목록의 "공공 안심글꼴"에서도 내려받을 수 있다 — [문체부 안심글꼴](https://www.mcst.go.kr/kor/s_policy/subPolicy/contents/contents09.jsp), [korea.kr 정책뉴스](https://www.korea.kr/news/policyNewsView.do?newsId=148878538)
- 공유마당 한글폰트 수: 71종(KOGL 41 + OFL 30)이라는 집계와 KOGL 133종 + OFL 46종이라는 집계가 공존한다. 집계 시점 차이로 보이며, 문체부·한국출판인회의 **KoPub World 바탕체·돋움체**가 포함된다 — [GeekNews 안심 글꼴파일 서비스](https://news.hada.io/topic?id=1806), [korea.kr 카드뉴스](https://www.korea.kr/news/visualNewsView.do?newsId=148899052)
- Noto Sans KR은 SIL OFL 1.1로 임베딩·인쇄·웹 등 대부분 용도가 허용되고 글꼴 판매만 금지된다. 나눔고딕은 OFL로 판매 외 상업 사용과 임베딩이 가능하다. KoPub 돋움은 상업 사용은 가능하나 사전승인 없는 수정·변형과 판매는 금지된다 — [산돌구름 Noto Sans KR](https://www.sandollcloud.com/free-font/15882/Noto-Sans-KR), [산돌구름 나눔고딕에코(나눔 계열)](https://www.sandollcloud.com/free-font/16067/NanumGothicEco)
- OFL 글꼴을 전자 문서에 포함(임베딩)해도 문서 자체의 라이선스는 바뀌지 않는다 — [더위키 OFL](https://thewiki.kr/w/OFL)
- KRDS(정부 디자인 시스템) 디자인 자산은 **Pretendard GOV** 서체를 요구한다 — [KRDS Resource](https://krds.go.kr/html/eng/resource/resource.html), [Pretendard README](https://cdn.jsdelivr.net/npm/pretendard@1.3.9/docs/en/README.md)

### Inferences
- **HWPX 출력(한글에서 열어 PDF로 저장하는 경로)**: 정부 보고서체(HY헤드라인M, 휴먼명조, 중고딕, 한컴돋움)를 글꼴 "이름"으로만 참조하면 된다. 렌더링과 PDF 변환을 사용자의 한컴오피스가 하므로 한경 기사에서 한컴이 말한 "한컴오피스 내 결과물 PDF 상업 사용" 범위에 든다고 볼 수 있다.
- **서버 측 PDF 렌더링(LibreOffice, Chromium, reportlab 등)**에서는 한컴 번들 글꼴 파일을 쓰지 말아야 한다. 대체 매핑 기본값을 권장한다: 명조 계열 → KoPub World 바탕 / 나눔명조 / Noto Serif KR, 고딕·헤드라인 계열 → KoPub World 돋움 Bold / 나눔스퀘어(또는 나눔고딕) ExtraBold / Pretendard(GOV) Bold, 본문 고딕 → Pretendard 또는 Noto Sans KR. 이 매핑은 시각적 유사성에 따른 추론이다.
- 생성기 기본 타이포 스케일 제안(A4 세로 HWPX, 근거 혼합):
  - 표지 사업명 24~28pt / 장 제목(Ⅰ.) HY헤드라인M 20~22pt / 절 제목(1.) 16pt / 항 제목(가.) 14~15pt 굵게
  - 본문: 보고서체 휴먼명조 15pt를 따른다. 단, 분량 제약이 큰 제안서 본문은 11~13pt가 현실적이다(KIND 13pt, KDCA 11pt, STF 11pt 이상 사례)
  - 표 안 10~12pt / 주석·출처 중고딕 9~11pt / 줄간격 160%(표 안 130%)
- 개조식 기호 기본값: □(1수준) → ○(2수준) → -(3수준) → ·(4수준) → ※(참고)이고, 각 수준 들여쓰기는 1~2자다(kordoc, 허프포스트 사례 종합).

### Gaps
- HY헤드라인M, HY견고딕(한양정보통신 계열)과 휴먼명조(휴먼 계열)의 독립 라이선스 원문(임베딩·한컴오피스 외 사용)은 찾지 못했다.
- 함초롬체의 현행 공식 라이선스 문구를 한컴 원문으로 확인하지 못했다(위키·글꼴 사이트 간 충돌).
- Pretendard·Pretendard GOV와 에스코어드림의 라이선스 원문은 이번 검색으로 확인하지 못했다. 학습 지식으로는 Pretendard가 SIL OFL 1.1이지만, README로 확인할 필요가 있다.
- 「행정업무의 운영 및 혁신에 관한 규정」 시행규칙의 용지 규격(A4)·여백 조항 원문은 확인하지 못했다.

## 4. PPT형 제안서 장표의 디자인 관행

### Takeaway
제안 컨설턴트와 디자인 대행사의 공통 권고는 다섯 가지다. ① 장표 상단에 결론형 **헤드메시지(거버닝 메시지)** 한 줄을 둔다. ② **한 장에 한 메시지**를 담는다. ③ 목차를 **평가항목 순서**로 짜고 배점에 비례해 분량을 배분한다. ④ **요구사항 ID → 목차 → 페이지** 매핑을 명시한다. ⑤ 블루 계열 메인 컬러를 쓰되 3색 이내, 6:3:1 비율, 글꼴은 2~3종 이내로 제한한다. 요구사항 ID 표기 위치 같은 세부 규칙의 공식 표준은 없다.

### Cited Findings
- 슬라이드 상단 한 줄만 읽어도 그 페이지의 결론을 알 수 있어야 하며, 이 한 줄이 거버닝 메시지다. 평가표가 있으면 목차를 평가 항목 순서로 짜고, 배점이 높은 항목에 분량을 더 준다 — [리더스에듀 '한국 공공·대학 제안서 다섯 가지 원칙'](https://www.leadersedu.net/insights/korean-proposal-five-principles)
- 페이지 제목에는 주제명 대신 결론을 쓴다. 요구사항 → 목차 → 근거 → 해당 페이지를 연결하는 매핑 방식을 쓴다 — [PTLink 사업제안서 PPT 구성](https://www.ptlink.co.kr/guide/proposal-ppt-structure.html)
- 한 장에 여러 주제를 섞지 않는다. 상단에 핵심 메시지를 크게 두고 아래에 근거 데이터를 배치한다 — [파란디자인 제안서 디자인 가이드](https://parancompany.co.kr/blog/proposal-design-guide)
- 실무 메모: 스토리보드에 요구사항 ID가 있으면 그 ID에 대응하는 내용을 장표에 넣는다. ID가 없으면 작성지침을, 그것도 없으면 평가기준을 넣는다 — [velog 제안서 작성 팁](https://velog.io/@lee_yesol421/%EC%A0%9C%EC%95%88%EC%84%9C-%EC%9E%91%EC%84%B1-%ED%8C%81-%EC%A0%95%EB%A6%AC)
- 표지, 목차, 간지, 본문(거버닝 메시지 자리 포함)을 마스터 템플릿으로 미리 만들어 두면 작업 속도가 빨라진다. 제안요청서의 기본 목차와 요구사항 목록표를 기준으로 목차를 잡는다 — [documento 나라장터 제안서 작성법](https://www.documento.co.kr/notice/?bmode=view&idx=15866267)
- 배점이 큰 항목은 목차 앞쪽과 요약서에 배치하고, 정량 증빙은 별도 목차로 두며, 요약서 흐름을 정성제안서와 맞춘다 — [presales.co.kr 목차 설계](https://presales.co.kr/ai-proposal-guide/proposal-outline)
- 공공 SI 제안서의 필수 시각 요소로는 시스템 구성도, 추진전략, 추진일정이 꼽힌다 — [크몽 공공기관 세로형 PPT](https://kmong.com/gig/731092)
- 색상: 공공기관 자료는 블루 그라데이션 조합을 쓰고, 블루가 "가장 무난"하다. 색은 미리 정한 3색 이내(메인 1~2, 서브 2~3)로 쓰고, 배경·본문·강조를 60:30:10으로 나누며, 공공기관 대상이면 기관 CI 컬러를 강조색으로 쓰고 나머지는 무채색으로 정리한다 — [디자인킵 관공서 PPT](https://designkeep.co.kr/53/?bmode=view&idx=10400416), [디자인킵 제안서 PPT](https://designkeep.co.kr/28/?idx=315), [파란디자인 PPT 가이드](https://parancompany.co.kr/blog/ppt-guide)
- 발표용 PPT 글자 크기 가이드(두 출처의 수치가 다름): ① 제목 28~36pt 굵게, 소제목 20~24pt, 본문 16~20pt, 캡션·출처 10~12pt, 차트 라벨 12~14pt ② 제목 32pt 이상, 부제목 24~28pt, 본문 18~20pt. 글꼴은 2~3종 이내 — [파란디자인 PPT 만드는 법](https://parancompany.co.kr/blog/ppt-guide), [파란디자인 PPT 디자인 잘하는 법](https://parancompany.co.kr/blog/ppt-design-guide)
- 크몽 제안 PM 상품 소개처럼 대행 시장에서는 "나라장터 표준제안서 목차에 의거한 템플릿"을 판매한다(방향·편집 프로그램을 규정하지는 않음) — [크몽 나라장터 제안서 PM](https://kmong.com/gig/137279), [크몽 공공 홈페이지 구축 제안서 4종](https://kmong.com/gig/542024)

### Inferences
- 장표 그리드 기본값 제안(A4 가로 297×210mm, 출처 종합 추론):
  - 상단 띠: 좌측 장·절 번호와 목차 경로(breadcrumb), 우측 **평가항목 태그**(예: "기술·기능 | 배점 10")와 **요구사항 ID 칩**(예: `SFR-003`, `SER-001`)
  - 헤드메시지: 1~2줄, 18~22pt 굵게, 메인 컬러
  - 본문 영역: 2~3단 그리드, 개념도·표 중심, 본문 10~12pt(인쇄·화면 열람용 장표 기준. 발표용 16pt 이상 가이드는 발표 전용 장표에만 적용)
  - 하단: 요약 박스(핵심 효과·차별점 1줄), 쪽번호, (블라인드가 아니면) 사업명, 블라인드면 업체 표기 없음
- 다이어그램 라이브러리 우선순위: 추진전략 체계도(비전-목표-전략-과제), 목표 시스템 구성도(개념도·아키텍처), 추진 조직도, WBS 표, 간트 차트(월 단위, 마일스톤 ◆), 요구사항 대비표, 품질·보안 관리 프로세스 흐름도.
- 기본 팔레트 제안: 메인 네이비/블루(예: #003B71, #0055A5 계열), 서브 하늘색과 회색 2~3단, 강조 1색(오렌지 또는 발주기관 CI색 중 1). 블라인드 모드에서는 자사 CI색이 업체를 식별하게 할 수 있으므로 중립 블루를 쓴다(추론).

### Gaps
- 제안서 장표의 "읽는 문서용" 본문 글자 크기(10~12pt)를 명시한 공식·대행사 출처는 찾지 못했다. 위 값은 HWP 제안서 규정(11~13pt)에서 유추한 것이다.
- 요구사항 ID 표기 위치·형식, 평가항목 태그의 표준 디자인은 공식 출처가 없다(검색 요약도 같은 결론).
- 접근성·가독성(색 대비, 색약 고려)에 관한 제안서 전용 가이드는 찾지 못했다.

## 5. 정부 디자인 시스템(KRDS)·정부상징과 제안서의 관련성

### Takeaway
KRDS(대한민국 정부 UI/UX 디자인 시스템)는 정부 웹·앱 서비스용이므로 제안서 문서 디자인에 직접 적용할 의무는 없다. 다만 KRDS는 **Pretendard GOV** 글꼴과 공식 색상 토큰을 제공하므로, 웹·앱 구축 사업 제안서의 화면 설계(UI 시안) 장표에서 "KRDS 준수"를 보여 주는 요소로 쓸 수 있다. 정부상징 가이드는 정부기관용 규정이므로 제안사 문서에서 정부상징을 쓰는 것은 피하는 편이 안전하다.

### Cited Findings
- KRDS 디자인 자산은 Pretendard GOV 서체를 요구하고, Pretendard GitHub에서 PretendardGOV.zip을 받도록 안내한다 — [KRDS Resource](https://krds.go.kr/html/eng/resource/resource.html)
- KRDS는 2024년 공개 이후 2025년 1월 정부 UI/UX 디자인 시스템으로 본격 개시되었다 — [디자인컴퍼스 KRDS(2024.4.17)](https://designcompass.org/2024/04/17/krds/), [디자인컴퍼스 KRDS 개시(2025.1.22)](https://designcompass.org/2025/01/22/krds-start/), [KRDS outline](https://www.krds.go.kr/html/eng/outline/outline_02.html)
- 제3자 정리: 정부24의 색 램프는 KRDS 공식 토큰과 같고, Pretendard GOV는 숫자 고정폭을 쓰며 'I'와 'l'의 구분을 강화했다 — [oppadu KRDS 갤러리](https://www.oppadu.com/tools/design-systems-site/brand/krds.html), [oppadu 정부24](https://www.oppadu.com/tools/design-systems-site/brand/gov24.html)
- 정부상징(정부 로고) 사용은 「정부상징디자인가이드」(2017)가 규정한다 — [정부상징디자인가이드 2017 PDF](https://fhi.forest.go.kr/file_down/정부상징디자인가이드_2017.pdf)

### Inferences
- 공공 웹·앱 구축 제안서라면 생성기에 "KRDS 준수 UI 시안 장표" 템플릿(Pretendard GOV, KRDS 컬러 토큰, 컴포넌트 명칭)을 넣는 것이 평가상 유리할 수 있다(추론).
- 제안서 본문 디자인에서는 KRDS 컬러를 강제할 필요가 없다. 다만 KRDS 블루 계열을 중립 메인 컬러로 쓰면 블라인드 모드에 무난하다(추론).

### Gaps
- KRDS 공식 색상 HEX 값과 타이포 스케일을 원문으로 확인하지 못했다(krds.go.kr 직접 열람 불가).
- 제안서 표지에 발주기관 로고나 정부상징을 넣는 것이 허용되는지에 대한 규정은 찾지 못했다.

## 6. 기술: HWPX(OWPML, KS X 6101) 구조와 PDF 제출 요건

### Takeaway
HWPX는 KS X 6101(OWPML) 기반의 **ZIP + XML** 패키지다. `Contents/header.xml`에 글꼴, 글자 모양(charPr), 문단 모양(paraPr), 스타일, 번호 매기기를 ID로 정의하고, `Contents/section0.xml` 본문은 그 ID를 참조한다. 용지 크기와 여백은 첫 문단의 `secPr/pagePr`에 HWPUNIT(1/7200인치)으로 들어간다. 전자제출은 PDF(총 300MB)만 요구되며, PDF/A 요구 사례는 찾지 못했다.

### Cited Findings
- HWPX는 KS X 6101 산업표준인 OWPML을 따른다. 물리적으로는 XML 문서를 담은 ZIP 아카이브로 ODF·OOXML과 같은 방식이며, 한컴이 구조와 규격 문서를 공개했다 — [다음 '기계도, 사람도 읽을 수 있는 문서는?②'](https://v.daum.net/v/EdWbqlVyYL), [아주경제(2021)](https://www.ajunews.com/view/20210427190629821), [python-hwpx GitHub](https://github.com/airmang/python-hwpx)
- `Contents/header.xml`은 스타일, 폰트, 용지 등 문서 설정을, `section0.xml`은 문단, 표, 이미지를 담는다. `section0.xml`의 `charPrIDRef`·`paraPrIDRef`는 header의 정의와 일치해야 한다. `charProperties`·`paraProperties`·`borderFills`의 `itemCnt`는 실제 자식 수와 같아야 한다. 첫 문단 첫 run에는 `secPr`와 `colPr`가 있어야 한다. `hp:`/`hs:`/`hh:`/`hc:` 접두사를 유지하고, `mimetype`은 ZIP 첫 엔트리로 무압축 저장한다. 스타일 ID 번호는 문서마다 다르므로 고정값으로 가정하면 안 된다 — [GitHub Canine89/hwpxskill](https://github.com/Canine89/hwpxskill), [hwpxskill SKILL.md](https://github.com/Canine89/hwpxskill/blob/main/SKILL.md)
- **직접 확인(python-hwpx 6.12.0 wheel의 `hwpx/data/Skeleton.hwpx`를 압축 해제)** — [PyPI python-hwpx](https://pypi.org/project/python-hwpx/):
  - 파일 구성: `mimetype`, `version.xml`, `settings.xml`, `META-INF/container.xml`, `META-INF/container.rdf`, `META-INF/manifest.xml`, `Contents/content.hpf`, `Contents/header.xml`, `Contents/section0.xml`, `Preview/PrvText.txt`, `Preview/PrvImage.png`(이미지가 있으면 `BinData/`가 추가될 것으로 예상되나 이 스켈레톤에는 없음)
  - `mimetype` 내용: `application/hwp+zip`. `container.xml`의 rootfile은 `Contents/content.hpf`(media-type `application/hwpml-package+xml`)
  - 네임스페이스(2011): `hh`=…/hwpml/2011/head, `hp`=…/2011/paragraph, `hs`=…/2011/section, `hc`=…/2011/core, `ha`=…/2011/app, `hpf`=…/schema/2011/hpf (도메인 `http://www.hancom.co.kr`)
  - 기본 글꼴: `hh:fontface`가 HANGUL/LATIN/HANJA/JAPANESE/OTHER/SYMBOL/USER 7개 언어별로 있고, 각각 `함초롬돋움`(id 0)과 `함초롬바탕`(id 1)을 담는다
  - 기본 글자 모양 `charPr id=0`: `height="1000"`(=10pt, 1pt=100), fontRef가 모두 1(함초롬바탕)이다. 기본 문단 줄간격은 `lineSpacing type="PERCENT" value="160"`이다
  - 기본 스타일: 바탕글(0), 본문(1), 개요 1~10(2~11), 쪽 번호(12, CHAR), 줄 번호(13), 머리말(14), 각주(15), 미주(16), 메모(17), 차례 제목(18), 차례 1~3(19~21), 캡션(22)
  - 번호 매기기: 1수준 `^1.`(DIGIT), 2수준 HANGUL_SYLLABLE(가.) 등
  - 용지: `pagePr width="59528" height="84186"`(=210×297mm, A4), `landscape="WIDELY"`(세로)
  - 여백: `margin left=8504 right=8504 top=5668 bottom=4252 header=4252 footer=4252`, 즉 좌우 30mm, 위 20mm, 아래 15mm, 머리말·꼬리말 15mm(한글 기본 쪽 설정)
- Pandoc에 HWPX writer를 추가하자는 제안이 논의 중이다("Korea's Public Document Standard") — [pandoc Discussion #11569](https://github.com/jgm/pandoc/discussions/11569)
- 한컴은 HWPX 포맷 전환을 촉진하고 있다(KCSF2025) — [아이뉴스24](https://www.inews24.com/view/1892549)
- PDF 제출: 나라장터 제안서류 일체는 PDF, 총 300MB 이하 — [나라장터 이용안내 PDF(2025.4)](https://www.g2b.go.kr/fs/fsc/fsca/fileUpload.do?k00=a2MMYzianzwExorC2swMQwxC2swNQwwC2syNgwvZGF0YS9BdHRhY2hmaWxlcy9wbnBlLzIwMjUvMDQvMDIvYTFhN2VkYjQxMjkzNGNmZGFhMjllNjE3NDI0YzhmZWIucGRmC2szMQzrgpjrnbzsnqXthLAg7J6F7LCw6rO16rOg66y4IOyekeyEseyLnCDsnbTsmqnslYjrgrQucGRmC2syMQxmNjg5NjNmMi00YjI1LTRjZDktYmY2NS05ZTAyYmIxNTk3MDksMQ%3D%3D)

### Inferences
- 단위 환산(Skeleton 값으로 검증): 1mm ≈ 283.46 HWPUNIT, 1pt = 100 HWPUNIT(charPr height), 1inch = 7200.
- 생성기 구현 지침:
  1. 한글에서 "정부 보고서체" 스타일을 저장한 템플릿 HWPX를 하나 만든다.
  2. header.xml의 charPr/paraPr/style ID를 이름으로 조회하는 매퍼를 둔다(ID는 문서마다 다르므로).
  3. section0.xml에는 스타일 이름 기반으로 문단을 넣는다.
  4. 표는 `hp:tbl`에 borderFill ID를 참조한다.
  5. 머리말·꼬리말과 쪽번호는 secPr 아래 header/footer 컨트롤과 "쪽 번호" 스타일을 쓴다.
- 여백 기본값 후보는 두 가지다. ① 한글 기본(위20/아래15/좌우30/머리말·꼬리말15)은 그대로 둘 수 있다. ② 정부 보고서 관행(좌우 20, 머리말·꼬리말 10~15)을 쓰면 본문 폭이 넓어져 분량 제한에 유리하다. 제안서 기본값으로는 ②(위20/아래15/좌우20/머리말10/꼬리말10)를 권장한다(추론).
- PDF 생성 시 글꼴 임베딩(서브셋)과 메타데이터 정리(블라인드)를 하고, 300MB 제한을 고려해 이미지 압축(예: 150~200dpi)을 넣는 것이 바람직하다(추론).

### Gaps
- KS X 6101 표준 원문과 한컴 공식 HWPX 개발자 문서는 직접 확인하지 못했다(위 구조는 오픈소스 템플릿을 실측한 결과).
- 나라장터 전자제출에서 PDF/A, 암호화 금지, 파일당 용량, 파일명 규칙 같은 추가 요건은 찾지 못했다. 총 300MB만 확인했다.
- 한글 프로그램 없이 HWPX를 PDF로 충실하게 변환하는 방법(서버 측 렌더링 품질)은 이번 범위에서 검증하지 못했다.

## 7. 종합: 자동 생성기 기본값 프로필(위 근거의 요약)

### Takeaway
RFP 파싱 값이 항상 우선한다. 파싱 실패 시 쓸 기본값은 아래와 같고, 각 값의 근거는 1~6번 섹션의 인용이다.

### Cited Findings
- 제출: PDF, 총 300MB 이하, 나라장터 문서구분(정성제안서/정량제안서/발표자료/제안요약서/하도급 계획서/기타) — [나라장터 이용안내](https://www.g2b.go.kr/fs/fsc/fsca/fileUpload.do?k00=a2MMYzianzwExorC2swMQwxC2swNQwwC2syNgwvZGF0YS9BdHRhY2hmaWxlcy9wbnBlLzIwMjUvMDQvMDIvYTFhN2VkYjQxMjkzNGNmZGFhMjllNjE3NDI0YzhmZWIucGRmC2szMQzrgpjrnbzsnqXthLAg7J6F7LCw6rO16rOg66y4IOyekeyEseyLnCDsnbTsmqnslYjrgrQucGRmC2syMQxmNjg5NjNmMi00YjI1LTRjZDktYmY2NS05ZTAyYmIxNTk3MDksMQ%3D%3D), [나라장터 공고 첨부(R25BK00907452)](https://www.g2b.go.kr/pn/pnp/pnpe/UntyAtchFile/downloadFile.do?bidPbancNo=R25BK00907452&bidPbancOrd=000&fileType=&fileSeq=2)
- 분량: 본문 100쪽, 요약 30쪽(발표본 대체 가능), 발표 20분/Q&A 10분 — [AI 플랫폼 RFP](https://www.g2b.go.kr/fs/fsc/fsca/fileUpload.do?k00=a2MMYzianzwExorC2swMQwxC2sxMgwLazI2DC9kYXRhL0F0dGFjaGZpbGVzL3BucGUvMjAyNS8wNy8wOS81ZDM3NmY3ZmJmODQ0Yzg1YjcyODE1MmRmMmJmMzVlMC5wZGYLazMxDCVFQyVBMCU5QyVFQyU5NSU4OCVFQyU5QSU5NCVFQyVCMiVBRCVFQyU4NCU5QyUyNiUyMzQwJTNCJUVEJTk1JTlDJUVBJUI1JUFEJUVDJTk3JUI0JUVCJUE2JUIwJUVDJTgyJUFDJUVDJTlEJUI0JUVCJUIyJTg0JUVCJThDJTgwJUVEJTk1JTk5JUVBJUI1JTkwK0FJKyVFQSVCOCVCMCVFQiVCMCU5OCslRUQlOTUlOTklRUMlOEElQjUlRUMlQTclODAlRUMlOUIlOTArJUVEJTk0JThDJUVCJTlFJUFCJUVEJThGJUJDKyVFQSVCNSVBQyVFQyVCNiU5NSUyNiUyMzQxJTNCLnBkZgtrMjEMYTAxMTJmZWEtYjJlNi00YzM4LThhNjQtNWUxN2VhNmVkNTFiLDIL), [클리앙 제안발표](https://www.clien.net/service/board/lecture/11882827)
- 보고서체: HY헤드라인M 22 / 소제목 16 / 휴먼명조 15 / 중고딕 13 / 줄간격 160% — [허프포스트코리아](https://www.huffingtonpost.kr/news/articleView.html?idxno=108786)

### Inferences
```yaml
# 근거 기반 기본값(추론 포함). RFP 파싱 값이 있으면 덮어씀
submission:
  format: pdf
  total_size_limit_mb: 300
  doc_types: [정성제안서, 정량제안서, 발표자료, 제안요약서, 하도급계획서, 기타문서]
  blind_mode: auto   # RFP에 '블라인드/업체정보 삭제본' 문구 있으면 true
page_limits:
  main_pages: 100        # 관측 범위 20~200
  summary_pages: 30      # 관측 범위 20~50, '발표본 대체 가능' 흔함
  presentation: {minutes: 20, qa_minutes: 10, slides: 25}
  exclude_from_count: [표지, 목차, 간지]   # RFP 확인 필요
main_doc_hwpx:          # A4 세로
  page: {size: A4, orientation: portrait}
  margin_mm: {top: 20, bottom: 15, left: 20, right: 20, header: 10, footer: 10}
  fonts:   # 한컴오피스 렌더 경로
    title: {face: HY헤드라인M, pt: 22}
    h1: {face: HY헤드라인M, pt: 18}
    h2: {face: HY헤드라인M, pt: 16}
    h3: {face: 휴먼명조, pt: 14, bold: true}
    body: {face: 휴먼명조, pt: 13}   # 보고서체 15pt, 분량 압박 시 11~13
    table: {face: 한컴돋움, pt: 10.5}
    note: {face: 중고딕, pt: 11}      # 보고서 관행 13pt
  fonts_license_safe:  # 서버 렌더 경로 대체
    headline: [KoPubWorld돋움 Bold, NanumSquare ExtraBold, Pretendard Bold]
    serif_body: [KoPubWorld바탕, NanumMyeongjo, Noto Serif KR]
    sans_body: [Pretendard, Noto Sans KR, NanumGothic]
  line_spacing_pct: {body: 160, table: 130}
  bullets: ["□", "○", "-", "·", "※"]
  numbering: ["Ⅰ.", "1.", "가.", "1)", "가)"]
  header_text: "{사업명}"            # blind면 업체명 금지
  footer: "- {page} -"               # 하단 중앙(관행 추정)
slides_pptx:            # 요약본·발표·가로형 제안서
  page: {size: A4, orientation: landscape}   # 발표 전용은 16:9
  layout: [breadcrumb, eval_item_tag, req_id_chips, head_message, body_grid, bottom_summary_box, page_no]
  head_message_pt: 20
  body_pt: 11            # 열람용. 발표 전용은 16~20
  palette: {main: "#0055A5", dark: "#003B71", sub: ["#E8F1FA", "#8C8C8C"], accent: "#F28C28"}
  max_fonts: 2
```
- 위 YAML 수치 중 출처로 직접 뒷받침되는 것은 300MB, PDF, 100/30쪽, 20/10분, 22/16/15/13pt, 160%, 좌우 20mm, □○-※ 체계뿐이다. 나머지(팔레트 HEX, 장표 본문 11pt, 표 10.5pt, 꼬리말 형식)는 생성기용 제안값이다.

### Gaps
- 생성기 기본값을 실제 낙찰 제안서 샘플로 검증하지 못했다. 공개된 낙찰 제안서 원본은 대부분 비공개다.
- 하단 중앙 쪽번호("- n -") 관행은 출처로 확인하지 못한 추정이다.
