from __future__ import annotations

from rfpgen.extract import extract_rfp
from rfpgen.extract.ambiguity import find_vague, grade
from rfpgen.extract.common import parse_krw
from rfpgen.extract.evaluation import extract_evaluation
from rfpgen.extract.guideline import extract_guideline
from rfpgen.extract.requirements import RequirementExtractor
from rfpgen.schemas import ExtractionReport, Requirement


def _codes(report: ExtractionReport) -> set[str]:
    return {f.code for f in report.findings}


# ---- 요구사항 ---------------------------------------------------------------------


def test_requirements_from_detail_and_summary(rfp_doc, profile):
    report = ExtractionReport()
    reqs = RequirementExtractor(profile.value("requirements.id_regex")).extract([rfp_doc], report)
    ids = [r.id for r in reqs]
    assert ids == ["SFR-001", "SFR-002", "SER-001", "PER-001", "PMR-001"]
    sfr = reqs[0]
    assert sfr.category == "기능 요구사항"
    assert sfr.name == "민원 신청 관리"
    assert sfr.definition == "온라인 민원 신청 기능을 구축한다"
    assert sfr.details[0] == "□ 민원 신청" and len(sfr.details) == 5
    assert sfr.outputs == ["요구사항 정의서, 화면 설계서"]
    assert all(r.origin == "detail_table" for r in reqs)
    # 모든 값에 원문 위치가 붙는다
    assert all(lc.block_id.startswith("d01:") for r in reqs for lc in r.locators)
    assert "REQ-COUNT-MISMATCH" not in _codes(report)
    # 본문의 'SRF-002'는 'SFR'의 오타로 의심된다
    typo = [f for f in report.findings if f.code == "REQ-ID-TYPO"]
    assert typo and "SRF-002" in typo[0].message


def test_layout_with_two_label_pairs_per_row(maker, profile):
    """실제 RFP 형식: '요구사항 분류 | 값 | 요구사항 ID | 값' 이 한 행에 있다."""
    m = maker()
    m.table([
        ["요구사항 분류", None, "기능요구사항", "요구사항 ID", "SFR-BIM-001"],
        ["요구사항 명칭", None, "글로벌 독립형 시스템 구축", None, None],
        ["요구\n사항\n상세\n설명", "정의", "기존 시스템에서 분리", None, None],
        [None, "세부\n내용", "□ 독립시스템 구축\n◦ 서버 분리\n- DB서버, WAS서버 등의 분리를 고려한\n설계", None, None],
    ], {(0, 0): (1, 2), (1, 0): (1, 2), (1, 2): (1, 3), (2, 0): (2, 1), (2, 2): (1, 3), (3, 2): (1, 3)})
    reqs = RequirementExtractor(profile.value("requirements.id_regex")).extract([m.doc], ExtractionReport())
    assert len(reqs) == 1
    r = reqs[0]
    assert (r.id, r.prefix, r.category, r.name) == ("SFR-BIM-001", "SFR", "기능요구사항", "글로벌 독립형 시스템 구축")
    assert r.definition == "기존 시스템에서 분리"
    # 글머리 없는 줄('설계')은 앞 항목에 이어 붙는다
    assert r.details[-1] == "- DB서버, WAS서버 등의 분리를 고려한 설계"


def test_declared_count_mismatch_and_undefined_reference(maker, profile):
    m = maker()
    m.table([["분류", "ID 부여규칙", "요구사항수"], ["기능", "SFR-요구사항ID", "2개"], ["장비", "ECR-요구사항ID", "3개"]])
    m.table([["요구사항 고유번호", "SFR-001"], ["요구사항 명칭", "가"], ["관련 요구사항", "SFR-009"]])
    m.table([["요구사항 고유번호", "SFR-002"], ["요구사항 명칭", "나"]])
    report = ExtractionReport()
    reqs = RequirementExtractor(profile.value("requirements.id_regex")).extract([m.doc], report)
    assert [r.id for r in reqs] == ["SFR-001", "SFR-002"]
    assert reqs[0].related == ["SFR-009"]
    mismatch = [f for f in report.findings if f.code == "REQ-COUNT-MISMATCH"]
    assert len(mismatch) == 1 and mismatch[0].severity == "error" and "ECR" in mismatch[0].message
    assert any(f.code == "REQ-UNKNOWN-REF" and "SFR-009" in f.message for f in report.findings)


def test_id_normalization_and_false_positives(profile):
    ex = RequirementExtractor(profile.value("requirements.id_regex"))
    assert ex.find_ids("SFR – 001, SER－002, SFR-CA-0003") == ["SFR-001", "SER-002", "SFR-CA-0003"]
    assert ex.find_ids("XSFR-001A") == []


# ---- 평가표 -----------------------------------------------------------------------


def test_evaluation_table(rfp_doc):
    report = ExtractionReport()
    ev = extract_evaluation([rfp_doc], report)
    assert ev.tech_price_ratio is not None and ev.tech_price_ratio.value == [90, 10]
    kinds = {a.name: a.kind for a in ev.areas}
    assert kinds["수행능력"] == "정량" and kinds["전략 및 방법론"] == "정성"
    strategy = next(a for a in ev.areas if a.name == "전략 및 방법론")
    assert strategy.points == 20 and [(i.name, i.points) for i in strategy.items] == [("사업 이해도", 10), ("추진 전략", 10)]
    assert strategy.items[0].criteria == ["사업의 목표와 범위를 정확히 이해하고 있는가"]
    assert sum(a.points for a in ev.areas if a.kind == "정성") == 70
    assert sum(a.points for a in ev.areas if a.kind == "정량") == 20
    assert 70 in ev.declared_totals and 20 in ev.declared_totals
    assert "EVAL-AREA-SUM" not in _codes(report)


def test_evaluation_continues_across_page_break(maker):
    m = maker()
    m.p("ㅇ 비계량평가 점", page=1)
    m.table([
        ["평가부문", "평가항목", "평가요소", "배점한도"],
        ["수행\n기반", "", "", "15"],
        [None, "보안 요구사항", "- 보안", "12"],
    ], {(1, 0): (2, 1)}, page=1)
    m.table([
        ["평가부문", "평가항목", "평가요소", "배점한도"],
        ["", "제약 사항", "- 제약", "3"],
        ["프로젝트\n관리", "사업관리", "- 관리", "20"],
    ], page=2)
    report = ExtractionReport()
    ev = extract_evaluation([m.doc], report)
    names = [(a.name, a.points, [i.name for i in a.items]) for a in ev.areas]
    assert names == [("수행 기반", 15, ["보안 요구사항", "제약 사항"]), ("프로젝트 관리", 20, ["사업관리"])]
    assert all(a.kind == "정성" for a in ev.areas)
    assert "EVAL-AREA-SUM" not in _codes(report)


# ---- 작성지침 ----------------------------------------------------------------------


def test_guideline_values(rfp_doc):
    report = ExtractionReport()
    g = extract_guideline([rfp_doc], report)
    assert g.main_page_limit.value == 100
    assert g.summary_page_limit.value == 30
    assert g.count_exclusions.value == ["표지", "목차", "간지"]
    assert g.paper.value == "A4" and g.orientation.value == "portrait"
    assert g.min_font_pt.value == 13 and g.table_min_font_pt.value == 12
    assert g.file_format.value == "PDF" and g.total_size_limit_mb.value == 300
    assert g.blind.value is True
    p = g.presentation.value
    assert (p.minutes, p.qa_minutes, p.pm_must_present) == (20, 10, True)
    # 근거 위치의 인용문은 블록 텍스트에 실제로 들어 있다
    block = rfp_doc.block(g.main_page_limit.locators[0].block_id)
    assert g.main_page_limit.locators[0].quote in block.text


def test_unreadable_page_limit_is_reported(maker):
    m = maker()
    m.p("ㅇ 제안서 지 규격의 전자문서(pdf)로 작성하며 페이지 (단면기준) 이내로 작성(표지, 간지 제외)")
    report = ExtractionReport()
    g = extract_guideline([m.doc], report)
    assert g.main_page_limit is None
    assert "GUIDE-PAGE-UNREADABLE" in _codes(report)
    assert g.count_exclusions.value == ["표지", "간지"]


def test_prescribed_toc_table_and_forms(maker):
    m = maker()
    m.p("□ 제안서 목차")
    m.table([
        ["작성 항목", None, "세부 목차", "비 고"],
        ["표지", None, "제안서 표지", "별지 제1호"],
        ["Ⅰ. 제안개요", None, "1. 제안배경 및 목표\n2. 제안범위", "자유서식"],
        ["Ⅱ. 제안업체 일반", None, "1. 일반현황\n2. 유사사업 수행실적", "자유서식"],
        ["Ⅲ. 전략 및 방법론", None, "1. 사업이해도\n2. 추진전략", "자유서식"],
        ["Ⅳ. 하도급 계획", None, "1. 하도급 계획", "자유서식"],
        ["Ⅴ.\n증빙\n자료", "서약서", "• 입찰 참가 관련 준수 사항 서약", "별지 제9호"],
    ], {(0, 0): (1, 2), (1, 0): (1, 2), (2, 0): (1, 2), (3, 0): (1, 2), (4, 0): (1, 2), (5, 0): (1, 2)})
    g = extract_guideline([m.doc], ExtractionReport())
    toc = g.prescribed_toc.value
    assert [(c.number, c.title) for c in toc][:4] == [("Ⅰ", "제안개요"), ("Ⅱ", "제안업체 일반"), ("Ⅲ", "전략 및 방법론"), ("Ⅳ", "하도급 계획")]
    assert [s.title for s in toc[2].children] == ["사업이해도", "추진전략"]
    forms = {d.form_no: d.name for d in g.required_documents}
    assert forms["별지 제1호"] == "표지 — 제안서 표지"
    assert forms["별지 제9호"].startswith("서약서")


# ---- 공고 정보·모호성 ------------------------------------------------------------------


def test_parse_krw():
    assert parse_krw("금 1,250,000,000원(부가세 포함)") == 1_250_000_000
    assert parse_krw("12.5억원") == 1_250_000_000
    assert parse_krw("123억 4,500만원") == 12_345_000_000
    assert parse_krw("1,234백만원") == 1_234_000_000
    assert parse_krw("원 포함") is None


def test_full_extraction(rfp_doc, profile):
    rfp, report = extract_rfp([rfp_doc], profile)
    assert rfp.notice.title.value == "2026년 통합민원시스템 고도화 사업"
    assert rfp.notice.budget_krw.value == 1_250_000_000
    assert rfp.notice.period.value == "계약일로부터 8개월"
    assert rfp.notice.contract_method.value == "협상계약"
    assert report.stats["requirements"] == 5
    pmr = rfp.requirement("PMR-001")
    assert {"원활", "필요시"} <= set(pmr.ambiguities)
    assert any(q.target == "SFR-002" for q in rfp.questions)  # 세부내용이 빈약한 요구사항
    assert any(q.issue == "ID 오타 의심" for q in rfp.questions)


def test_grade_and_vague_terms():
    rich = Requirement(id="SFR-001", definition="정의", details=["a", "b", "c", "d", "3초 이내 응답", "e"],
                       outputs=["설계서"])
    assert grade(rich) == "S"
    assert grade(Requirement(id="SFR-002")) == "D"
    vocab = {"quantity": ["등"], "quality": ["원활"]}
    assert find_vague("서버 등의 분리, 원활한 운영", vocab) == [("quantity", "등"), ("quality", "원활")]
    assert find_vague("등급 관리", vocab) == []


# ---- 중국 입찰서 생성기 분석에서 이식한 결정적 점검 ------------------------------------------


def test_evaluation_rules_are_split_from_questions(maker):
    from rfpgen.extract.evaluation import classify_criterion

    m = maker()
    m.p("정성평가")
    m.table([
        ["평가항목", "평가기준", "배점"],
        ["개발 방법론", "- 단계별 산출물을 제시하였는가\n- 매우 우수: 10점, 우수: 8점, 보통: 6점\n- 분량 초과 시 1점 감점", "10"],
    ])
    ev = extract_evaluation([m.doc], ExtractionReport())
    item = ev.items()[0]
    assert item.criteria == ["단계별 산출물을 제시하였는가"]
    assert [(r.kind, r.item_id) for r in ev.rules] == [("등급", item.id), ("감점", item.id)]
    assert classify_criterion("최근 3년 실적 20억원 이상: 10점") == "산식"
    assert classify_criterion("보안 대책의 적정성을 평가") is None


def test_compliance_and_eligibility(maker, profile):
    m = maker()
    m.p("1. 입찰참가자격")
    m.p("○ 소프트웨어사업자(컴퓨터관련서비스사업)로 신고한 자")
    m.p("○ 중소기업기본법에 따른 중소기업으로 직접생산확인을 받은 자")
    m.p("2. 유의사항")
    m.p("○ 제출서류를 기한 내 제출하지 않은 경우 입찰은 무효로 한다")
    m.p("○ 허위 사실이 발견될 경우 협상대상자에서 제외")
    m.p("○ 제안서 분량을 초과한 경우 초과 1쪽당 0.5점 감점")
    m.p("○ 제안서에 업체명을 표기한 경우 평가 대상에서 제외한다(블라인드 평가)")
    m.p("○ 제안서 본문은 50쪽 이내")
    rfp, report = extract_rfp([m.doc], profile)
    stated = [(c.kind, c.related_check) for c in rfp.compliance if c.origin == "stated"]
    assert ("입찰무효", "SUB") in stated
    assert ("평가제외", "FACT") in stated
    assert ("감점", "PAGE") in stated
    assert ("평가제외", "BLD") in stated
    suggested = [c for c in rfp.compliance if c.origin == "suggested"]
    assert len(suggested) == 5 and all(c.status == "proposed" for c in suggested)
    assert [e.value for e in rfp.eligibility][:2] == ["소프트웨어사업자(컴퓨터관련서비스사업)로 신고한 자",
                                                     "중소기업기본법에 따른 중소기업으로 직접생산확인을 받은 자"]
    # 블라인드 위반이 '평가 제외'로 규정되면 작성지침 값에 그 근거가 메모된다(BLD 점검을 blocker로)
    assert rfp.guideline.blind.value is True and "평가제외" in (rfp.guideline.blind.note or "")


def test_blind_negation_and_omissions(maker):
    m = maker()
    m.p("○ 본 사업은 블라인드 평가를 실시하지 않음")
    m.p("○ 제안서 글자 크기는 별도 기준에 따름")
    m.p("○ 제안서 본문은 40쪽 이내")
    report = ExtractionReport()
    g = extract_guideline([m.doc], report)
    assert g.blind.value is False and g.blind.confidence == 1.0
    omissions = [f.message for f in report.findings if f.code == "GUIDE-OMISSION"]
    assert any("글자 크기" in msg for msg in omissions)


def test_prescribed_toc_production_tags(maker):
    m = maker()
    m.p("□ 제안서 목차")
    m.table([
        ["작성 항목", "세부 목차", "비 고"],
        ["Ⅰ. 제안개요", "1. 제안배경", "자유서식"],
        ["Ⅱ. 제안업체 일반", "1. 일반현황", "별지 제2호, 별지 제3호"],
        ["Ⅲ. 요구사항 대비표", "1. 수용여부", "조견표 및 참조표"],
    ])
    toc = extract_guideline([m.doc], ExtractionReport()).prescribed_toc.value
    assert [(c.title, c.production) for c in toc] == [("제안개요", "자유서식"), ("제안업체 일반", "별지서식"),
                                                      ("요구사항 대비표", "대응표")]
    assert toc[1].form_refs == ["별지 제2호", "별지 제3호"]
