"""분석 결과 XLSX: 추적표(설계서 6.4절 열 순서) + 평가표·요구사항·목차·작성지침·질의서·점검결과."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from ..schemas.common import Locator
from ..schemas.plan import Outline, PageBudget, Trace
from ..schemas.rfp import ExtractionReport, Rfp

TRACE_COLUMNS = ["요구사항 ID", "명칭", "분류", "연결 평가항목", "제안 요약", "수용 여부", "제안서 쪽", "RFP 원문 위치",
                 "연결 목차", "연결 근거", "상태"]

_HEAD_FILL = PatternFill("solid", fgColor="DCE6F1")
_HEAD_FONT = Font(bold=True)
_WRAP = Alignment(wrap_text=True, vertical="top")


def _loc_text(locs: list[Locator]) -> str:
    out = []
    for lc in locs[:2]:
        page = f"p.{lc.page}" if lc.page else ""
        out.append(f"{lc.doc_id} {page} {lc.block_id}".strip())
    return "; ".join(out)


def _sheet(wb: Workbook, title: str, header: list[str], rows: list[list[object]], widths: list[int]) -> None:
    ws = wb.create_sheet(title)
    ws.append(header)
    for c in range(1, len(header) + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill, cell.font, cell.alignment = _HEAD_FILL, _HEAD_FONT, _WRAP
    for r in rows:
        ws.append(r)
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = _WRAP
    ws.freeze_panes = "A2"
    if rows:
        ws.auto_filter.ref = ws.dimensions


def write_workbook(path: Path, rfp: Rfp, outline: Outline, budget: PageBudget, trace: Trace,
                   report: ExtractionReport) -> None:
    wb = Workbook()
    wb.remove(wb.active)
    titles = {n.id: f"{n.number} {n.title}" for n in outline.walk()}

    _sheet(wb, "추적표", TRACE_COLUMNS, [
        [r.req_id, r.req_name, r.category, r.eval_item or "", r.summary, r.acceptance,
         ", ".join(str(p) for p in r.pages), _loc_text(r.rfp_locators),
         "\n".join(titles.get(s, s) for s in r.sections), r.mapping_reason, r.status]
        for r in trace.rows
    ], [16, 32, 16, 20, 30, 10, 10, 22, 28, 36, 10])

    _sheet(wb, "평가표", ["부문", "구분", "부문 배점", "항목", "항목 배점", "평가 질문(체크리스트)", "RFP 원문 위치"], [
        [a.name, a.kind, a.points, it.name, it.points, "\n".join(it.criteria), _loc_text(it.locators)]
        for a in rfp.evaluation.areas for it in a.items
    ], [20, 8, 10, 26, 10, 70, 22])

    _sheet(wb, "요구사항", ["ID", "접두어", "분류", "명칭", "정의", "세부내용", "산출정보", "관련 요구사항",
                          "상세화 등급(추정)", "모호 표현", "추출 원천", "신뢰도", "RFP 원문 위치"], [
        [r.id, r.prefix, r.category, r.name, r.definition, "\n".join(r.details), "\n".join(r.outputs),
         ", ".join(r.related), r.detail_grade, ", ".join(r.ambiguities), r.origin, r.confidence, _loc_text(r.locators)]
        for r in rfp.requirements
    ], [16, 8, 14, 30, 40, 70, 24, 18, 10, 20, 12, 8, 22])

    targets = {line.node_id: line.target_chars for line in budget.lines}
    _sheet(wb, "목차·쪽수", ["번호", "제목", "수준", "연결 평가항목", "배점", "쪽수 예산", "목표 글자 수", "요구사항 수",
                           "체크리스트", "출처"], [
        [n.number, n.title, n.level, ", ".join(n.eval_items), round(n.points, 2), n.page_budget,
         f"{targets[n.id][0]:,}~{targets[n.id][1]:,}" if targets.get(n.id) else "",
         len(n.requirements), "\n".join(n.checklist), n.origin]
        for n in outline.walk()
    ], [10, 34, 6, 16, 8, 10, 16, 10, 70, 14])

    g = rfp.guideline
    guide_rows: list[list[object]] = []
    for label, ex in [
        ("본문 분량(쪽)", g.main_page_limit), ("요약본 분량(쪽)", g.summary_page_limit),
        ("발표자료 분량(쪽)", g.presentation_page_limit), ("쪽수 제외 항목", g.count_exclusions),
        ("용지", g.paper), ("방향", g.orientation), ("본문 최소 글자(pt)", g.min_font_pt),
        ("표 최소 글자(pt)", g.table_min_font_pt), ("편집 프로그램", g.editor), ("제출 형식", g.file_format),
        ("총 용량 상한(MB)", g.total_size_limit_mb), ("블라인드", g.blind), ("발표", g.presentation),
    ]:
        value = "" if ex is None else (ex.value.model_dump() if hasattr(ex.value, "model_dump") else ex.value)
        guide_rows.append([label, str(value) if ex is not None else "(찾지 못함)",
                           ex.locators[0].quote if ex is not None and ex.locators else "",
                           _loc_text(ex.locators) if ex is not None else "",
                           ex.method if ex is not None else ""])
    guide_rows.append(["본문 쪽수 예산 기준", f"{budget.main_page_limit}쪽", budget.main_page_limit_source, "", ""])
    for d in g.required_documents:
        guide_rows.append([d.form_no or "별지", d.name, "", _loc_text(d.locators), "rule"])
    _sheet(wb, "작성지침", ["항목", "값", "원문", "RFP 원문 위치", "추출 방법"], guide_rows, [20, 30, 60, 22, 10])

    _sheet(wb, "무효·감점 사유", ["구분", "내용", "관련 점검", "출처", "추출 방법", "신뢰도", "상태", "RFP 원문 위치"], [
        [c.kind, c.text, c.related_check or "", "원문 명시" if c.origin == "stated" else "권고(원문 없음)",
         c.method, c.confidence, c.status, _loc_text(c.locators)] for c in rfp.compliance
    ] + [["참가자격", e.value, "", "원문 명시", e.method, e.confidence, e.status, _loc_text(e.locators)]
         for e in rfp.eligibility],
        [10, 80, 10, 14, 10, 8, 10, 22])

    items = {it.id: it.name for it in rfp.evaluation.items()}
    _sheet(wb, "평가규칙", ["종류", "내용", "적용 항목", "RFP 원문 위치"], [
        [r.kind, r.text, items.get(r.item_id or "", ""), _loc_text(r.locators)] for r in rfp.evaluation.rules
    ], [10, 80, 24, 22])

    _sheet(wb, "질의서 후보", ["대상", "쟁점", "질의(초안)", "RFP 원문 위치"], [
        [q.target, q.issue, q.question, _loc_text(q.locators)] for q in rfp.questions
    ], [18, 26, 80, 22])

    _sheet(wb, "점검 결과", ["코드", "심각도", "내용", "RFP 원문 위치"], [
        [f.code, f.severity, f.message, _loc_text(f.locators)] for f in report.findings
    ], [24, 10, 90, 22])

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def write_trace_workbook(path: Path, outline: Outline, trace: Trace, data_requests: list | None = None) -> None:
    """초안 단계의 추적표(제안 요약·수용 여부·상태가 채워진 것)와 자료 요청서."""
    wb = Workbook()
    wb.remove(wb.active)
    titles = {n.id: f"{n.number} {n.title}" for n in outline.walk()}
    _sheet(wb, "추적표", TRACE_COLUMNS, [
        [r.req_id, r.req_name, r.category, r.eval_item or "", r.summary, r.acceptance,
         ", ".join(str(p) for p in r.pages), _loc_text(r.rfp_locators),
         "\n".join(titles.get(s, s) for s in r.sections), r.mapping_reason, r.status]
        for r in trace.rows
    ], [16, 32, 16, 20, 40, 10, 10, 22, 28, 36, 10])
    if data_requests is not None:
        _sheet(wb, "자료 요청서", ["분류", "필요한 근거", "요청한 절", "사유", "담당자", "기한"], [
            [getattr(d, "category", ""), d.need, d.section_title, d.reason, d.owner, d.due] for d in data_requests
        ], [10, 50, 36, 30, 12, 12])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
