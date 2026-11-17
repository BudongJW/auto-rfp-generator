"""테스트 픽스처: 표준 RFP 형식을 흉내 낸 합성 문서를 만든다(실제 RFP 원문은 저장소에 넣지 않는다)."""

from __future__ import annotations

from pathlib import Path

import pytest

from rfpgen.parse.builder import DocBuilder
from rfpgen.profile import load_profile
from rfpgen.schemas.docir import Document

# ---- DocIR을 직접 만드는 도우미(추출기 단위 테스트용) ------------------------------


class DocMaker:
    def __init__(self, doc_id: str = "d01", filename: str = "rfp.hwpx") -> None:
        self.doc = Document(doc_id=doc_id, filename=filename, format="hwpx", sha256="0" * 64, role="제안요청서")
        self.b = DocBuilder(self.doc)

    def p(self, text: str, page: int | None = None) -> DocMaker:
        self.b.text(text, page=page)
        return self

    def table(self, rows: list[list[str | None]], spans: dict[tuple[int, int], tuple[int, int]] | None = None,
              page: int | None = None) -> DocMaker:
        """rows의 None은 병합으로 덮인 칸. spans[(r, c)] = (rowspan, colspan)."""
        spans = spans or {}
        t = self.b.table(len(rows), max(len(r) for r in rows), page=page)
        made = []
        for r, row in enumerate(rows):
            for c, text in enumerate(row):
                if text is None:
                    continue
                rs, cs = spans.get((r, c), (1, 1))
                made.append(self.b.cell(t, text, r, c, rs, cs, page=page))
        self.b.finish_table(t, made)
        return self


@pytest.fixture
def maker() -> type[DocMaker]:
    return DocMaker


@pytest.fixture(scope="session")
def profile():
    return load_profile()


# ---- 표준 형식 RFP 본문(파일 픽스처와 단위 테스트가 공유) ---------------------------

from rfpgen.sample import (  # noqa: E402  체험용 가상 RFP와 같은 데이터
    DECLARED_TABLE,
    DETAILS,
    EVAL_QUAL,
    EVAL_QUAL_SPANS,
    EVAL_QUANT,
    EVAL_QUANT_SPANS,
    GUIDE_LINES,
    SUMMARY_SPANS,
    SUMMARY_TABLE,
    detail_table,
)
from rfpgen.sample import add_table as _hwpx_table  # noqa: E402


def standard_rfp(maker_cls: type[DocMaker]) -> Document:
    m = maker_cls()
    m.p("Ⅰ. 사업 개요")
    m.p("Ⅳ. 제안 요청 내용")
    m.p("1. 요구사항 총괄표")
    m.table(DECLARED_TABLE)
    m.table(SUMMARY_TABLE, SUMMARY_SPANS)
    m.p("2. 상세 요구사항")
    for d in DETAILS:
        rows, spans = detail_table(*d)
        m.table(rows, spans)
    m.p("- 관련: SRF-002 항목 참조")
    for line in GUIDE_LINES:
        m.p(line)
    m.p("2. 제안서 평가")
    m.p("가. 정량적 평가(20점)")
    m.table(EVAL_QUANT, EVAL_QUANT_SPANS)
    m.p("나. 정성적 평가(70점)")
    m.table(EVAL_QUAL, EVAL_QUAL_SPANS)
    return m.doc


@pytest.fixture
def rfp_doc(maker) -> Document:
    return standard_rfp(maker)


# ---- 실제 파일 픽스처 ---------------------------------------------------------------


@pytest.fixture
def hwpx_file(tmp_path: Path) -> Path:
    from hwpx import HwpxDocument

    doc = HwpxDocument.new()
    doc.add_paragraph("Ⅳ. 제안 요청 내용")
    doc.add_paragraph("1. 요구사항 총괄표")
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
    path = tmp_path / "제안요청서_통합민원.hwpx"
    doc.save_to_path(str(path))
    return path


_KOREAN_FONT = Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")


@pytest.fixture
def pdf_file(tmp_path: Path) -> Path:
    pytest.importorskip("reportlab")
    if not _KOREAN_FONT.exists():
        pytest.skip("한글 글꼴이 없어 PDF 픽스처를 만들 수 없습니다")
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    pdfmetrics.registerFont(TTFont("KR", str(_KOREAN_FONT), subfontIndex=0))
    style = ParagraphStyle("kr", fontName="KR", fontSize=10, leading=14)
    story = [Paragraph("Ⅴ. 제안서 작성 안내", style), Spacer(1, 6)]
    for line in GUIDE_LINES[7:11]:
        story.append(Paragraph(line, style))
    story.append(Spacer(1, 10))
    data = [[c or "" for c in row] for row in EVAL_QUAL]
    table = Table(data, colWidths=[80, 110, 230, 50])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "KR"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("SPAN", (0, 1), (0, 3)),
        ("SPAN", (0, 4), (0, 6)),
        ("SPAN", (0, 10), (2, 10)),
    ]))
    story.append(table)
    path = tmp_path / "rfp.pdf"
    SimpleDocTemplate(str(path), pagesize=A4).build(story)
    return path


@pytest.fixture
def docx_file(tmp_path: Path) -> Path:
    import docx

    d = docx.Document()
    d.add_paragraph("1. 요구사항 총괄표")
    rows = SUMMARY_TABLE
    t = d.add_table(rows=len(rows), cols=3)
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            if text:
                t.cell(r, c).text = text
    t.cell(1, 0).merge(t.cell(2, 0))
    path = tmp_path / "rfp.docx"
    d.save(str(path))
    return path
