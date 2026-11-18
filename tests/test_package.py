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
