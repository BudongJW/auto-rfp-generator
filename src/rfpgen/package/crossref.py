"""조견표(평가항목별 해당 쪽수표): 조달청 협상에 의한 계약 제안서평가 세부기준 제6조의2③.

입찰자는 제출기한까지 "제안서의 목차 및 평가항목별 해당 쪽수가 명기된 조견표"를 시스템에 등록해야 한다.
목차(plan/outline.json)의 평가항목 연결과, 제출용 본문 PDF에서 찾은 장·절 시작 쪽(책갈피)으로 만든다.

쪽 번호는 본문에 찍힌 쪽 번호(표지를 1쪽으로 세고 표지 번호는 숨김 = PDF 쪽 순서 + 1)다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..render.pdf import Bookmark
from ..schemas.plan import Outline, OutlineNode
from ..schemas.rfp import Rfp


@dataclass
class TocRow:
    number: str
    title: str
    level: int
    first: int | None          # 찍힌 쪽 번호(없으면 본문에서 찾지 못함)
    last: int | None


@dataclass
class CrossRefRow:
    area: str
    item: str
    points: float | None
    sections: list[TocRow]


def _heading(node: OutlineNode, chapter: bool) -> str:
    from ..render.hwpx_writer import _section_number

    return f"{node.number} {node.title}" if chapter else f"{_section_number(node)} {node.title}"


def _pages_label(first: int | None, last: int | None) -> str:
    if first is None:
        return "[확인 필요: 쪽 없음]"
    return f"{first}" if last is None or last == first else f"{first}~{last}"


def build_toc(outline: Outline, marks: list[Bookmark], total_pages: int) -> list[TocRow]:
    """장·절마다 시작·끝 쪽. 끝 쪽은 같은 단계 이상(절이면 다음 절·장, 장이면 다음 장)의 다음 책갈피 바로 앞 쪽이고,
    다음 것이 같은 쪽에서 시작하면 시작 쪽과 같다. marks는 문서 순서(find_heading_pages 결과)."""
    index = {(m.level, " ".join(m.title.split())): i for i, m in enumerate(marks)}
    rows: list[TocRow] = []
    for ch in outline.chapters:
        for node, level in [(ch, 0)] + [(c, 1) for c in ch.children]:
            i = index.get((level, " ".join(_heading(node, level == 0).split())))
            if i is None:
                rows.append(TocRow(node.number, node.title, level, None, None))
                continue
            page = marks[i].page
            nxt = next((m.page for m in marks[i + 1:] if m.level <= level), total_pages)
            rows.append(TocRow(node.number, node.title, level, page + 1, max(page, nxt - 1) + 1))
    return rows


def build_crossref(outline: Outline, rfp: Rfp, toc: list[TocRow]) -> list[CrossRefRow]:
    """정성 평가항목마다 연결된 절과 쪽. 연결된 절이 없으면 빈 목록(사람이 채울 자리)."""
    by_number = {r.number: r for r in toc}
    linked: dict[str, list[TocRow]] = {}
    for node in outline.walk():
        row = by_number.get(node.number)
        for item_id in node.eval_items:
            if row is not None and row not in linked.setdefault(item_id, []):
                linked[item_id].append(row)
    out: list[CrossRefRow] = []
    for area in rfp.evaluation.areas:
        if area.kind != "정성":
            continue
        for it in area.items:
            out.append(CrossRefRow(area=area.name, item=it.name, points=it.points, sections=linked.get(it.id, [])))
    return out


def crossref_markdown(title: str, toc: list[TocRow], rows: list[CrossRefRow]) -> str:
    lines = [f"# 조견표 — {title}", "",
             "조달청 협상에 의한 계약 제안서평가 세부기준 제6조의2③: 제출기한까지 제안서의 목차와 평가항목별 해당 쪽수를 "
             "적은 조견표를 시스템에 등록해야 합니다. 쪽은 본문(01_정성제안서.pdf)에 찍힌 쪽 번호입니다.", "",
             "## 평가항목별 해당 쪽", "", "| 평가부문 | 평가항목 | 배점 | 해당 목차 | 쪽 |", "|---|---|---|---|---|"]
    for r in rows:
        pts = f"{r.points:g}" if r.points is not None else ""
        if not r.sections:
            lines.append(f"| {r.area} | {r.item} | {pts} | [확인 필요: 연결된 목차 없음] | |")
            continue
        sec = "<br>".join(f"{s.number} {s.title}" for s in r.sections)
        pages = ", ".join(_pages_label(s.first, s.last) for s in r.sections)
        lines.append(f"| {r.area} | {r.item} | {pts} | {sec} | {pages} |")
    lines += ["", "## 목차", "", "| 목차 | 쪽 |", "|---|---|"]
    for t in toc:
        indent = "　" if t.level else ""
        lines.append(f"| {indent}{t.number} {t.title} | {_pages_label(t.first, t.last)} |")
    lines.append("")
    return "\n".join(lines)


def write_crossref_xlsx(path: Path, toc: list[TocRow], rows: list[CrossRefRow]) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    wb = Workbook()
    ws = wb.active
    ws.title = "평가항목별 쪽수"
    ws.append(["평가부문", "평가항목", "배점", "해당 목차", "쪽"])
    for r in rows:
        ws.append([r.area, r.item, r.points,
                   "\n".join(f"{s.number} {s.title}" for s in r.sections) or "[확인 필요: 연결된 목차 없음]",
                   ", ".join(_pages_label(s.first, s.last) for s in r.sections)])
    toc_ws = wb.create_sheet("목차")
    toc_ws.append(["목차", "시작 쪽", "끝 쪽"])
    for t in toc:
        toc_ws.append([("    " if t.level else "") + f"{t.number} {t.title}", t.first, t.last])
    for sheet, widths in ((ws, [16, 24, 8, 36, 14]), (toc_ws, [44, 10, 10])):
        for i, w in enumerate(widths):
            sheet.column_dimensions[chr(65 + i)].width = w
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


__all__ = ["CrossRefRow", "TocRow", "build_crossref", "build_toc", "crossref_markdown", "write_crossref_xlsx"]
