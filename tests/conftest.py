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

GUIDE_LINES = [
    "Ⅴ. 제안서 작성 안내",
    "1. 제안서 작성 지침",
    "○ 사업명: 2026년 통합민원시스템 고도화 사업",
    "○ 사업예산: 금 1,250,000,000원(부가가치세 포함)",
    "○ 사업기간: 계약일로부터 8개월",
    "○ 본 사업은 「국가를 당사자로 하는 계약에 관한 법률 시행령」 제43조에 따른 협상에 의한 계약으로 진행",
    "○ 기술능력평가(90%)와 입찰가격평가(10%)를 합산하여 종합평가점수를 산정",
    "○ 제안서는 A4 용지 세로 방향으로 작성하며, 제안서 본문은 100쪽 이내로 작성(표지, 목차, 간지 제외)",
    "○ 요약 제안서는 30페이지 이내로 작성",
    "○ 제안서 본문 글자 크기는 13pt 이상, 표 안의 글자는 12pt 이상으로 작성",
    "○ 제안서류 일체는 PDF 파일 형식으로 제출하여야 하며, 총 용량은 300MB를 초과할 수 없음",
    "○ 제안서에는 업체명, 로고 등 제안사를 식별할 수 있는 표시를 하여서는 안 됨(블라인드 평가)",
    "○ 제안 발표 시간은 20분, 질의응답 10분으로 하며 사업수행책임자(PM)가 직접 발표",
]

SUMMARY_TABLE = [
    ["구분", "요구사항 고유번호", "요구사항 명칭"],
    ["기능", "SFR-001", "민원 신청 관리"],
    [None, "SFR-002", "민원 처리 현황 조회"],
    ["보안", "SER-001", "개인정보 암호화"],
    ["성능", "PER-001", "응답 시간"],
    ["관리", "PMR-001", "사업 관리"],
]
SUMMARY_SPANS = {(1, 0): (2, 1)}

DECLARED_TABLE = [
    ["분류", "ID 부여규칙", "요구사항수"],
    ["기능 요구사항", "SFR-요구사항ID", "2개"],
    ["보안 요구사항", "SER-요구사항ID", "1개"],
    ["성능 요구사항", "PER-요구사항ID", "1개"],
    ["프로젝트 관리 요구사항", "PMR-요구사항ID", "1개"],
]


def detail_table(cat: str, rid: str, name: str, definition: str, details: str) -> tuple[list, dict]:
    rows = [
        ["요구사항 분류", None, cat],
        ["요구사항 고유번호", None, rid],
        ["요구사항 명칭", None, name],
        ["요구사항 상세설명", "정의", definition],
        [None, "세부내용", details],
        ["산출정보", None, "요구사항 정의서, 화면 설계서"],
    ]
    spans = {(0, 0): (1, 2), (1, 0): (1, 2), (2, 0): (1, 2), (3, 0): (2, 1), (5, 0): (1, 2)}
    return rows, spans


DETAILS = [
    ("기능 요구사항", "SFR-001", "민원 신청 관리", "온라인 민원 신청 기능을 구축한다",
     "□ 민원 신청\n- 민원 유형별 신청서 작성 기능\n- 첨부파일 업로드(최대 100MB)\n- 신청 결과 알림(문자, 이메일)\n- 임시저장 기능"),
    ("기능 요구사항", "SFR-002", "민원 처리 현황 조회", "민원 처리 현황을 조회한다", "- 처리 단계 조회 등"),
    ("보안 요구사항", "SER-001", "개인정보 암호화", "개인정보를 암호화한다",
     "- 주민등록번호 등 고유식별정보 암호화\n- 전송 구간 암호화(TLS 1.2 이상)"),
    ("성능 요구사항", "PER-001", "응답 시간", "주요 화면 응답 시간 기준",
     "- 주요 화면 3초 이내 응답\n- 동시 사용자 500명 이상 처리"),
    ("프로젝트 관리 요구사항", "PMR-001", "사업 관리", "사업 관리 방안을 제시한다",
     "- 원활한 사업 관리 방안 제시\n- 필요시 주간 보고"),
]

EVAL_QUANT = [
    ["평가부문", "평가항목", "평가요소", "배점한도"],
    ["수행능력", "유사사업 수행실적", "- 최근 3년 유사사업 실적", "10"],
    [None, "참여인력", "- 투입인력 등급과 경력", "10"],
    ["소계", None, None, "20"],
]
EVAL_QUANT_SPANS = {(1, 0): (2, 1), (3, 0): (1, 3)}

EVAL_QUAL = [
    ["평가부문", "평가항목", "평가요소", "배점한도"],
    ["전략 및 방법론", "", "", "20"],
    [None, "사업 이해도", "- 사업의 목표와 범위를 정확히 이해하고 있는가", "10"],
    [None, "추진 전략", "- 사업 특성을 고려한 추진 전략을 제시하였는가", "10"],
    ["기술 및 기능", "", "", "25"],
    [None, "기능 요구사항", "- 기능 요구사항 구현 방안이 구체적인가", "15"],
    [None, "보안 요구사항", "- 보안 요구사항 이행 방안이 적절한가", "10"],
    ["성능 및 품질", "성능 요구사항", "- 성능 목표 달성 방안", "10"],
    ["프로젝트 관리", "사업 관리", "- 일정·위험 관리 방안", "10"],
    ["상생협력", "상생협력 및 하도급", "- 중소기업 참여 및 하도급 계획", "5"],
    ["소계", None, None, "70"],
]
EVAL_QUAL_SPANS = {(1, 0): (3, 1), (4, 0): (3, 1), (10, 0): (1, 3)}


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


def _hwpx_table(doc, rows: list[list[str | None]], spans: dict[tuple[int, int], tuple[int, int]]) -> None:
    n_rows, n_cols = len(rows), max(len(r) for r in rows)
    t = doc.add_table(n_rows, n_cols)
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            if text:
                t.cell(r, c).text = text
    # 병합은 오른쪽·아래쪽부터 해야 앞쪽 셀 좌표가 흔들리지 않는다
    for (r, c), (rs, cs) in sorted(spans.items(), reverse=True):
        if rs > 1 or cs > 1:
            t.merge_cells(r, c, r + rs - 1, c + cs - 1)


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
