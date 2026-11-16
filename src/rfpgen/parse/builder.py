"""포맷별 파서가 공통으로 쓰는 DocIR 블록 생성기와 제목 판별 규칙."""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..schemas.docir import Block, Document, TableInfo, TableRef

# 한국 공공문서의 번호 체계: Ⅰ. → 1. → 가. → 1) → 가)
_ROMAN = "ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ"
_HEADING_PATTERNS: list[tuple[int, re.Pattern[str]]] = [
    (1, re.compile(rf"^\s*([{_ROMAN}]|(?=[IVX])X{{0,3}}(?:IX|IV|V?I{{0,3}}))\s*[.．]\s*\S")),
    (1, re.compile(r"^\s*제\s*\d+\s*[장편]\s*\S")),
    (2, re.compile(r"^\s*(\d{1,2})\s*[.．]\s*(?!\d)\S")),
    (3, re.compile(r"^\s*([가-하])\s*[.．]\s*\S")),
]
_NUMBERING = re.compile(rf"^\s*([{_ROMAN}]|[IVX]+|\d{{1,2}}|[가-하]|\d{{1,2}}\)|[가-하]\))\s*[.．)]?\s*")
_MAX_HEADING_LEN = 60


def guess_heading(text: str, style: str | None = None) -> tuple[int | None, str | None]:
    """문단이 제목이면 (수준, 번호)를 돌려준다. 아니면 (None, None)."""
    stripped = text.strip()
    if not stripped or len(stripped) > _MAX_HEADING_LEN or stripped.endswith(("다.", "함.", "음.", "요.")):
        return None, None
    if style:
        m = re.match(r"^(?:개요|Heading|제목)\s*(\d+)$", style.strip())
        if m:
            return int(m.group(1)), _numbering(stripped)
    for level, pattern in _HEADING_PATTERNS:
        if pattern.match(stripped):
            return level, _numbering(stripped)
    return None, None


def _numbering(text: str) -> str | None:
    m = _NUMBERING.match(text)
    return m.group(1) if m else None


def normalize_space(text: str) -> str:
    text = text.replace(" ", " ").replace("　", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    return text.strip()


class DocBuilder:
    """블록 ID를 순서대로 발급하며 Document를 만든다."""

    def __init__(self, doc: Document) -> None:
        self.doc = doc
        self._n = 0
        self._t = 0

    def _next_id(self) -> str:
        self._n += 1
        return f"{self.doc.doc_id}:b{self._n:05d}"

    def text(self, text: str, *, page: int | None = None, style: str | None = None,
             parent: str | None = None, force_heading_level: int | None = None) -> Block | None:
        text = normalize_space(text)
        if not text:
            return None
        if force_heading_level is not None:
            level, numbering = force_heading_level, _numbering(text)
        else:
            level, numbering = guess_heading(text, style)
        block = Block(
            id=self._next_id(),
            kind="heading" if level else "para",
            text=text,
            level=level,
            numbering=numbering,
            page=page,
            style=style,
            parent=parent,
        )
        self.doc.blocks.append(block)
        return block

    def table(self, rows: int, cols: int, *, page: int | None = None, parent: str | None = None) -> Block:
        self._t += 1
        block = Block(
            id=self._next_id(),
            kind="table",
            table=TableInfo(rows=rows, cols=cols),
            page=page,
            parent=parent,
        )
        self.doc.blocks.append(block)
        return block

    def cell(self, table: Block, text: str, row: int, col: int, rowspan: int = 1, colspan: int = 1,
             *, page: int | None = None) -> Block:
        block = Block(
            id=self._next_id(),
            kind="cell",
            text=normalize_space(text),
            page=page,
            parent=table.id,
            cell=TableRef(table_id=table.id, row=row, col=col, rowspan=max(rowspan, 1), colspan=max(colspan, 1)),
        )
        self.doc.blocks.append(block)
        return block

    def finish_table(self, table: Block, cells: Iterable[Block]) -> None:
        """셀 위치로 표 크기를 보정한다."""
        rows = cols = 0
        for c in cells:
            assert c.cell is not None
            rows = max(rows, c.cell.row + c.cell.rowspan)
            cols = max(cols, c.cell.col + c.cell.colspan)
        assert table.table is not None
        table.table.rows = max(table.table.rows, rows)
        table.table.cols = max(table.table.cols, cols)
