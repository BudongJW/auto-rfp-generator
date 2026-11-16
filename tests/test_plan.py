from __future__ import annotations

from rfpgen.extract import extract_rfp
from rfpgen.plan import largest_remainder, plan_proposal, similarity
from rfpgen.schemas import Extracted, TocNode


def test_largest_remainder_design_example():
    # 설계서 7.4절 예시: 90쪽을 20·20·10·10·5·5점에 배분
    assert largest_remainder([20, 20, 10, 10, 5, 5], 90) == [26, 26, 13, 13, 6, 6]


def test_largest_remainder_minimum_and_total():
    alloc = largest_remainder([50, 1, 1, 1], 10)
    assert sum(alloc) == 10 and min(alloc) >= 1
    alloc = largest_remainder([1, 1, 1, 1, 1], 3)  # 최소 1쪽씩이면 넘칠 수밖에 없다
    assert alloc == [1, 1, 1, 1, 1]


def test_similarity():
    assert similarity("기능 요구사항", "기능요구사항") == 1.0
    assert similarity("사업이해도", "1. 사업 이해도 및 추진 전략") >= 0.9
    assert similarity("보안", "교육 훈련") < 0.2


def test_outline_from_evaluation_table(rfp_doc, profile):
    rfp, report = extract_rfp([rfp_doc], profile)
    outline, budget, trace = plan_proposal(rfp, profile, report)
    assert outline.origin == "eval_table"
    titles = [c.title for c in outline.chapters]
    # 고정 장 2개 + 정성 부문 5개(정량 부문은 본문 장이 아니다)
    assert titles == ["제안 개요", "제안업체 일반", "전략 및 방법론", "기술 및 기능", "성능 및 품질", "프로젝트 관리", "상생협력"]
    assert [c.number for c in outline.chapters][:3] == ["Ⅰ.", "Ⅱ.", "Ⅲ."]
    # 상생협력 부문이 평가표에 있으므로 필수 장을 따로 넣지 않는다
    assert sum(1 for c in outline.chapters if c.canonical == "상생협력하도급") == 1
    # 평가 질문이 절 체크리스트로 내려간다
    sec = outline.chapters[2].children[0]
    assert sec.title == "사업 이해도" and sec.checklist == ["사업의 목표와 범위를 정확히 이해하고 있는가"]

    # 쪽수: 100쪽 - 고정 10쪽 = 90쪽을 정성 70점에 비례 배분
    assert budget.main_page_limit == 100 and budget.main_page_limit_source == "RFP 작성지침"
    assert budget.fixed_pages == 10 and budget.distributable_pages == 90
    assert sum(c.page_budget for c in outline.chapters) == 100
    pages = {line.title: line.pages for line in budget.lines}
    assert pages["기능 요구사항"] == 19  # 15/70 × 90 = 19.3

    # 추적표: 모든 요구사항이 절에 연결된다
    assert trace.coverage() == 1.0
    rows = {r.req_id: r for r in trace.rows}
    assert outline.node(rows["SFR-001"].sections[0]).title == "기능 요구사항"
    assert outline.node(rows["SER-001"].sections[0]).title == "보안 요구사항"
    assert outline.node(rows["PER-001"].sections[0]).title == "성능 요구사항"
    assert rows["SFR-001"].eval_item == "기능 요구사항"


def test_prescribed_toc_wins_and_mandatory_warning(rfp_doc, profile):
    rfp, report = extract_rfp([rfp_doc], profile)
    rfp.guideline.prescribed_toc = Extracted[list[TocNode]](value=[
        TocNode(number="Ⅰ", title="제안 개요", level=1),
        TocNode(number="Ⅱ", title="수행 계획", level=1, children=[
            TocNode(number="1", title="사업 이해도", level=2),
            TocNode(number="2", title="기능 요구사항", level=2),
            TocNode(number="3", title="보안 요구사항", level=2),
        ]),
    ])
    outline, budget, trace = plan_proposal(rfp, profile, report)
    assert outline.origin == "prescribed"
    assert [c.title for c in outline.chapters] == ["제안 개요", "수행 계획"]  # 지정 목차는 바꾸지 않는다
    assert any(f.code == "PLAN-MANDATORY-MISSING" for f in report.findings)
    sec = outline.chapters[1].children[1]
    assert sec.title == "기능 요구사항" and sec.eval_items


def test_template_outline_without_evaluation(maker, profile):
    m = maker()
    m.table([["요구사항 고유번호", "SFR-001"], ["요구사항 분류", "기능 요구사항"], ["요구사항 명칭", "가"]])
    rfp, report = extract_rfp([m.doc], profile)
    outline, budget, trace = plan_proposal(rfp, profile, report)
    assert outline.origin == "default_template"
    assert any(c.canonical == "상생협력하도급" for c in outline.chapters)
    assert budget.main_page_limit_source.startswith("프로필 기본값")
    assert trace.rows[0].status == "mapped"
