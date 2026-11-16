"""DOCX 파서(python-docx, MIT).

본문의 문단(w:p)과 표(w:tbl)를 순서대로 읽는다. 셀 병합은 w:gridSpan(가로)과
w:vMerge(세로)로 복원한다.
"""

from __future__ import annotations

import io

from ..schemas.docir import Block, Document
from .builder import DocBuilder
from .safety import UnsafeInputError, open_zip

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_P, _TBL, _TR, _TC = (f"{{{W}}}{n}" for n in ("p", "tbl", "tr", "tc"))
_VAL = f"{{{W}}}val"


def _tc_props(tc) -> tuple[int, str | None]:
    pr = tc.find(f"{{{W}}}tcPr")
    span, vmerge = 1, None
    if pr is not None:
        gs = pr.find(f"{{{W}}}gridSpan")
        if gs is not None:
            span = int(gs.get(_VAL, "1"))
        vm = pr.find(f"{{{W}}}vMerge")
        if vm is not None:
            vmerge = vm.get(_VAL, "continue")
    return span, vmerge


class _DocxWalker:
    def __init__(self, builder: DocBuilder, document) -> None:
        self.b = builder
        self.document = document

    def _para(self, p):
        from docx.text.paragraph import Paragraph

        para = Paragraph(p, self.document)
        style = para.style.name if para.style is not None else None
        return para.text, style

    def body(self, parent_el, parent: str | None = None) -> list[str]:
        texts: list[str] = []
        for child in parent_el:
            if child.tag == _P:
                text, style = self._para(child)
                if text.strip():
                    texts.append(text)
                    if parent is None:
                        self.b.text(text, style=style)
            elif child.tag == _TBL:
                self.table(child, parent)
        return texts

    def table(self, tbl, parent: str | None) -> None:
        rows = tbl.findall(_TR)
        table = self.b.table(len(rows), 0, parent=parent)
        cells: list[Block] = []
        origin: dict[tuple[int, int], Block] = {}  # (row, col) → 그 위치를 덮는 셀
        for r, tr in enumerate(rows):
            col = 0
            for tc in tr.findall(_TC):
                span, vmerge = _tc_props(tc)
                if vmerge == "continue":
                    above = origin.get((r - 1, col))
                    if above is not None and above.cell is not None:
                        above.cell.rowspan += 1
                        for k in range(span):
                            origin[(r, col + k)] = above
                    col += span
                    continue
                cell = self.b.cell(table, "", r, col, 1, span)
                cell.text = "\n".join(t.strip() for t in self.body(tc, parent=cell.id) if t.strip())
                cells.append(cell)
                for k in range(span):
                    origin[(r, col + k)] = cell
                col += span
        self.b.finish_table(table, cells)


def parse_docx_bytes(data: bytes, doc: Document) -> Document:
    open_zip(data, doc.filename)  # 크기·ZIP 폭탄 점검
    try:
        import docx
    except ImportError as exc:  # pragma: no cover
        raise UnsafeInputError("python-docx가 설치되지 않았습니다") from exc
    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:
        raise UnsafeInputError(f"{doc.filename}: DOCX를 열 수 없습니다 — {exc}") from exc
    _DocxWalker(DocBuilder(doc), document).body(document.element.body)
    return doc
