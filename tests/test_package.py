"""M3 장표·PDF·제출 패키지 테스트."""

from __future__ import annotations

import json
import re
import zipfile

import pytest
from typer.testing import CliRunner

from rfpgen.cli import app
from rfpgen.draft.pipeline import run_draft
from rfpgen.kb import init_kb
from rfpgen.package import build_package, make_slides
from rfpgen.pipeline import analyze
from rfpgen.render.pdf import clean_pdf, converters_available, inspect_pdf

needs_converters = pytest.mark.skipif(not all(converters_available().values()),
                                      reason="HWPX(rhwp 사이드카)·PPTX(LibreOffice) 변환기가 없습니다")


@pytest.fixture(scope="module")
def drafted(tmp_path_factory, request):
    from conftest import (
        DECLARED_TABLE,
        DETAILS,
        EVAL_QUAL,
        EVAL_QUAL_SPANS,
        EVAL_QUANT,
        EVAL_QUANT_SPANS,
        GUIDE_LINES,
        SUMMARY_SPANS,
        SUMMARY_TABLE,
        _hwpx_table,
        detail_table,
    )
    from hwpx import HwpxDocument

    from rfpgen.profile import load_profile

    base = tmp_path_factory.mktemp("m3")
    doc = HwpxDocument.new()
    _hwpx_table(doc, DECLARED_TABLE, {})
    _hwpx_table(doc, SUMMARY_TABLE, SUMMARY_SPANS)
    for d in DETAILS:
        rows, spans = detail_table(*d)
        _hwpx_table(doc, rows, spans)
    for line in GUIDE_LINES:
        doc.add_paragraph(line)
    doc.add_paragraph("가. 정량적 평가(20점)")
    _hwpx_table(doc, EVAL_QUANT, EVAL_QUANT_SPANS)
    doc.add_paragraph("나. 정성적 평가(70점)")
    _hwpx_table(doc, EVAL_QUAL, EVAL_QUAL_SPANS)
    src = base / "제안요청서.hwpx"
    doc.save_to_path(str(src))
    profile = load_profile()
    project = base / "proj"
    analyze([src], project, profile)
    kb = base / "kb"
    init_kb(kb)
    run_draft(project, profile, kb_dir=kb)
    return project, kb, profile


def test_slides_layout_and_privacy(drafted):
    from pptx import Presentation
    from pptx.util import Mm

    project, kb, profile = drafted
    res = make_slides(project, profile)
    summary = Presentation(str(res.summary))
    pres = Presentation(str(res.presentation))
    assert (round(summary.slide_width / Mm(1)), round(summary.slide_height / Mm(1))) == (297, 210)   # A4 가로
    assert round(pres.slide_width / pres.slide_height, 2) == 1.78                                    # 16:9
    assert res.summary_slides == len(summary.slides) <= 30          # 요약본 상한(RFP 30쪽)
    texts = [[sh.text_frame.text for sh in s.shapes if sh.has_text_frame] for s in summary.slides]
    func = next(t for t in texts if any("기능 요구사항" in x and ">" in x for x in t))
    assert "SFR-001" in func and "SFR-002" in func                  # 요구사항 칩
    assert any(x.startswith("평가: 기능 요구사항") for x in func)     # 평가항목 태그
    assert all(s.has_notes_slide and s.notes_slide.notes_text_frame.text for s in pres.slides)  # 대본(발표자 노트)
    assert summary.core_properties.author == "" and summary.core_properties.last_modified_by == ""
    with zipfile.ZipFile(res.summary) as zf:
        blob = " ".join(zf.read(n).decode("utf-8", "ignore") for n in zf.namelist() if n.endswith(".xml"))
    assert "예시정보" not in blob and "python-pptx" not in blob
    script = res.script.read_text(encoding="utf-8")
    assert "# 예상 질문" in script and "사업의 목표와 범위를 정확히 이해하고 있는가" in script


def test_slide_head_fits_box():
    from rfpgen.render.slides import LINE_EM, PT_MM, fit_text

    assert fit_text("[확인 필요]", 271, 14, 18, 10) == ("[확인 필요]", 18.0)
    long = ("당사는 민원 유형별 동적 신청서, 최대 100MB 분할·이어올리기 첨부, 문자·이메일 알림, 수동·자동 임시저장, "
            "처리 단계 이력 기반 현황 조회를 공통 모듈로 구축하여 SFR-001과 SFR-002를 빠짐없이 구현함")
    text, pt = fit_text(long, 271, 14, 18, 10)
    assert text == long and 10 <= pt < 18                     # 줄이면 들어간다(두 줄)
    assert 2 * pt * PT_MM * LINE_EM <= 14
    text, pt = fit_text(long * 3, 271, 14, 18, 10)           # 가장 작은 크기로도 넘치면 줄여 쓴다
    assert pt == 10 and text.endswith("…") and len(text) < len(long * 3)


def test_heading_bookmarks_prefer_whole_line(tmp_path):
    """본문 속 '1. Background details' 줄보다 제목 줄 '1. Background'를 고르고, 단계별로 책갈피를 넣는다."""
    pytest.importorskip("reportlab")
    from reportlab.pdfgen import canvas

    from rfpgen.render.pdf import find_heading_pages, read_bookmarks

    src = tmp_path / "doc.pdf"
    c = canvas.Canvas(str(src))
    for lines in (["Cover"], ["I. Overview", "1. Background details are in the next page"], ["1. Background", "body"],
                  ["II. Plan", "1. Schedule"]):
        for k, line in enumerate(lines):
            c.drawString(72, 760 - 20 * k, line)
        c.showPage()
    c.save()
    marks = find_heading_pages(src, [("I. Overview", 0), ("1. Background", 1), ("II. Plan", 0), ("1. Schedule", 1),
                                     ("III. Missing", 0)])
    assert [(m.title, m.page, m.level) for m in marks] == [("I. Overview", 1, 0), ("1. Background", 2, 1),
                                                           ("II. Plan", 3, 0), ("1. Schedule", 3, 1)]
    clean_pdf(src, tmp_path / "out.pdf", title="t", bookmarks=marks)
    assert read_bookmarks(tmp_path / "out.pdf") == [(0, "I. Overview", 1), (1, "1. Background", 2), (0, "II. Plan", 3),
                                                     (1, "1. Schedule", 3)]


def test_crossref_pages_per_eval_item():
    """조견표: 절 시작·끝 쪽(다음 같은 단계 책갈피 앞 쪽, 찍힌 번호 = PDF 순서 + 1)과 평가항목별 해당 절."""
    from rfpgen.package.crossref import build_crossref, build_toc, crossref_markdown
    from rfpgen.render.pdf import Bookmark
    from rfpgen.schemas.plan import Outline, OutlineNode
    from rfpgen.schemas.rfp import EvalArea, EvalItem, Rfp

    def node(id_, number, title, level, items=(), children=()):
        return OutlineNode(id=id_, number=number, title=title, level=level, eval_items=list(items), children=list(children))

    outline = Outline(origin="default_template", chapters=[
        node("C1", "Ⅰ.", "제안 개요", 1, children=[node("S-1-1", "Ⅰ.1", "제안 배경", 2)]),
        node("C3", "Ⅲ.", "전략 및 방법론", 1, children=[node("S-3-1", "Ⅲ.1", "사업 이해도", 2, ["A02-01"]),
                                                    node("S-3-2", "Ⅲ.2", "추진 전략", 2, ["A02-02"])]),
    ])
    marks = [Bookmark("Ⅰ. 제안 개요", 1, 0), Bookmark("1. 제안 배경", 1, 1), Bookmark("Ⅲ. 전략 및 방법론", 3, 0),
             Bookmark("1. 사업 이해도", 3, 1), Bookmark("2. 추진 전략", 7, 1)]
    toc = build_toc(outline, marks, total_pages=10)
    assert [(t.number, t.first, t.last) for t in toc] == [("Ⅰ.", 2, 3), ("Ⅰ.1", 2, 3), ("Ⅲ.", 4, 10), ("Ⅲ.1", 4, 7),
                                                         ("Ⅲ.2", 8, 10)]
    rfp = Rfp()
    rfp.evaluation.areas = [EvalArea(id="A01", name="수행능력", kind="정량", points=20,
                                     items=[EvalItem(id="A01-01", name="유사사업 수행실적", points=10)]),
                            EvalArea(id="A02", name="전략 및 방법론", kind="정성", points=20,
                                     items=[EvalItem(id="A02-01", name="사업 이해도", points=10),
                                            EvalItem(id="A02-02", name="추진 전략", points=10),
                                            EvalItem(id="A02-03", name="위험 관리", points=5)])]
    rows = build_crossref(outline, rfp, toc)
    assert [(r.item, [s.number for s in r.sections]) for r in rows] == [
        ("사업 이해도", ["Ⅲ.1"]), ("추진 전략", ["Ⅲ.2"]), ("위험 관리", [])]          # 정성 항목만
    md = crossref_markdown("사업", toc, rows)
    assert "| 전략 및 방법론 | 사업 이해도 | 10 | Ⅲ.1 사업 이해도 | 4~7 |" in md
    assert "| 전략 및 방법론 | 위험 관리 | 5 | [확인 필요: 연결된 목차 없음] | |" in md


def test_clean_pdf_strips_metadata(tmp_path):
    pytest.importorskip("reportlab")
    from reportlab.pdfgen import canvas

    src = tmp_path / "in.pdf"
    c = canvas.Canvas(str(src))
    c.setAuthor("(주)예시정보 홍길동")
    c.setCreator("YesiFlow")
    c.drawString(100, 750, "hello")
    c.save()
    assert "예시정보" in " ".join(inspect_pdf(src).metadata.values())
    info = clean_pdf(src, tmp_path / "out.pdf", title="사업명 정성제안서")
    assert info.metadata == {"/Title": "사업명 정성제안서"} and info.pages == 1


@pytest.mark.skipif(not converters_available()["hwpx"], reason="HWPX 변환기(rhwp 사이드카)가 없습니다")
def test_hwpx_pdf_keeps_each_page_clip(tmp_path):
    """쪽 SVG의 id가 겹쳐도 앞쪽의 잘라내기 영역이 뒤쪽 표 칸에 적용되지 않는다(긴 상자 글이 다 보인다)."""
    import logging

    import pdfplumber

    from rfpgen.render.hwpx_writer import ProposalWriter, load_style
    from rfpgen.render.pdf import hwpx_to_pdf

    long = ("본 사업은 운영 중인 통합민원시스템을 계약일로부터 8개월 안에 서비스 중단 없이 고도화하여 민원인 편의, "
            "처리 효율, 개인정보 보호, 안정적 성능을 함께 확보하는 사업이며 마지막낱말확인")
    w = ProposalWriter(load_style())
    w.para("Ⅰ. 첫 장", "chapter")
    w.para("1. 첫 절", "section")
    w.message_box("[짧은 상자]")                     # 1쪽: 한 줄 높이 칸
    w.para("Ⅱ. 둘째 장", "chapter", page_break=True)
    w.para("1. 둘째 절", "section")
    w.message_box(long)                              # 2쪽: 같은 자리, 여러 줄 칸
    w.page_setup("")
    src = tmp_path / "boxes.hwpx"
    w.save(src)
    pdf = tmp_path / "boxes.pdf"
    hwpx_to_pdf(src, pdf)
    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    with pdfplumber.open(pdf) as doc:
        assert len(doc.pages) == 2
        text = (doc.pages[1].extract_text() or "").replace(" ", "")
    assert "마지막낱말확인" in text


@needs_converters
def test_package_end_to_end_and_checks(drafted):
    project, kb, profile = drafted
    make_slides(project, profile)
    res = build_package(project, profile, kb_dir=kb)
    names = [d.pdf.name for d in res.docs]
    assert names == ["01_정성제안서.pdf", "02_제안요약서.pdf", "03_발표자료.pdf"]
    for d in res.docs:
        info = inspect_pdf(d.pdf)
        assert info.pages == d.pages > 0
        assert set(info.metadata) == {"/Title"}                      # 작성자·제작 도구 없음
        assert not info.unembedded_fonts
    from rfpgen.render.pdf import read_bookmarks

    marks = read_bookmarks(res.docs[0].pdf)                             # 본문: 장·절 책갈피, 쪽 순서
    chapters = [t for lv, t, _ in marks if lv == 0]
    assert chapters[:2] == ["Ⅰ. 제안 개요", "Ⅱ. 제안업체 일반"] and any(lv == 1 for lv, _, _ in marks)
    pages = [pg for _, _, pg in marks]
    assert pages == sorted(pages) and pages[0] >= 1                     # 표지 다음부터
    manifest = json.loads((project / "submission" / "manifest.json").read_text(encoding="utf-8"))
    assert [m["doc_type"] for m in manifest] == ["정성제안서", "제안요약서", "발표자료"]
    rules = {f.rule for f in res.check.findings}
    assert "PAGE-001" not in rules and "SUB-001" not in rules
    assert "FACT-001" in rules                                        # 초안 단계 점검을 이어 붙였다
    checklist = res.checklist.read_text(encoding="utf-8")
    assert "가격입찰서를 따로 제출했다" in checklist and "01_정성제안서.pdf" in checklist
    assert res.crossref is not None and res.crossref.exists() and "submission/조견표.xlsx" in checklist   # 조견표
    xref = (project / "submission" / "조견표.md").read_text(encoding="utf-8")
    assert "| 기술 및 기능 | 기능 요구사항 | 15 | Ⅳ.1 기능 요구사항 |" in xref and "[확인 필요: 쪽 없음]" not in xref

    # RFP 상한을 줄이면 정확한 쪽수·용량으로 막힌다
    rfp_path = sorted(project.glob("rfp/rfp.v*.json"))[-1]
    data = json.loads(rfp_path.read_text(encoding="utf-8"))
    data["guideline"]["main_page_limit"]["value"] = 2
    data["guideline"]["total_size_limit_mb"]["value"] = 0
    rfp_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    res2 = build_package(project, profile, kb_dir=kb)
    msgs = {f.rule: f for f in res2.check.findings if f.severity == "blocker"}
    assert "PAGE-001" in msgs and re.search(r"\d+쪽\(표지 제외\) — 상한 2쪽 초과", msgs["PAGE-001"].message)
    assert "SUB-001" in msgs


@needs_converters
def test_cli_slides_and_package(drafted):
    project, kb, _ = drafted
    r = CliRunner().invoke(app, ["slides", str(project)])
    assert r.exit_code == 0, r.output
    r = CliRunner().invoke(app, ["package", str(project), "--kb", str(kb)])
    assert r.exit_code == 0, r.output
    assert "01_정성제안서.pdf" in r.output and "제출 전 점검표" in r.output


class ScriptFake:
    """발표 대본 과제: 장마다 대본, 예상 질문 둘(KB 토큰 포함)."""

    name = "fake"

    def __init__(self, allowed=("public", "internal")) -> None:
        self.allowed_data_classes = set(allowed)
        self.calls = []

    def complete(self, call, json_schema):
        from rfpgen.llm import ProviderReply

        self.calls.append(call)
        n = len(re.findall(r"^\[(\d+)\] ", call.instruction, re.M))
        data = {"slides": [{"index": i, "script": f"{i}번 장 대본입니다."} for i in range(1, n + 1)],
                "qa": [{"question": "투입 인력 규모는?", "answer": "정규직 개발 인력 {{fact:F-002}}을 확보하고 있습니다.",
                        "basis": "Ⅱ.3"},
                       {"question": "응답 시간 목표는?", "answer": "[확인 필요: 목표 응답 시간]", "basis": "Ⅴ.1"}]}
        return ProviderReply(text=json.dumps(data, ensure_ascii=False), model="fake", stop_reason="end_turn",
                             usage={"input_tokens": 10, "output_tokens": 10})


def test_llm_script_masks_kb_values_and_needs_share(drafted, tmp_path):
    import shutil

    from pptx import Presentation

    project, kb, profile = drafted
    proj = tmp_path / "proj"
    shutil.copytree(project, proj)
    # 절 초안에 KB 값이 들어간 문장을 넣는다(실제 LLM 초안은 토큰이 값으로 바뀌어 저장된다)
    sec = sorted(proj.glob("sections/S-4-1.v*.json"))[-1]
    data = json.loads(sec.read_text(encoding="utf-8"))
    data["head_message"] = "정규직 개발 인력 85명과 PM 경력 18년으로 기능 요구사항을 수행함"
    sec.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    fake = ScriptFake(allowed=("public",))
    res = make_slides(proj, profile, provider=fake, share_kb=False, kb_dir=kb)    # 공유 허용 없이는 보내지 않는다
    assert not res.script_llm and not fake.calls and "--llm-share-kb" in res.notes[0]

    fake = ScriptFake()
    res = make_slides(proj, profile, provider=fake, share_kb=True, kb_dir=kb)
    assert res.script_llm and len(fake.calls) == 1 and fake.calls[0].data_class == "internal"
    sent = fake.calls[0].context + fake.calls[0].instruction
    assert "85명" not in sent and "18년" not in sent                      # KB 값은 토큰으로 가려 보낸다
    assert "{{fact:F-002}}" in sent and "{{kb:H-001.years}}년" in sent
    script = res.script.read_text(encoding="utf-8")
    assert "정규직 개발 인력 85명을 확보하고 있습니다." in script            # 받은 토큰은 값으로 바꾼다
    assert "[확인 필요: 목표 응답 시간]" in script and "_(근거: Ⅱ.3)_" in script
    pres = Presentation(str(res.presentation))
    assert pres.slides[1].notes_slide.notes_text_frame.text == "2번 장 대본입니다."   # 발표자 노트에도
