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
