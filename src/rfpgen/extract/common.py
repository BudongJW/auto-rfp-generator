"""추출기가 공유하는 도구: 표 격자, 텍스트 정규화, 근거 위치, 금액·숫자 파싱."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field

from ..schemas.common import Locator
from ..schemas.docir import Block, Document

_DASHES = re.compile(r"\s*[‐‑‒–—―－−]\s*|\s+-\s*|\s*-\s+")


def norm(text: str) -> str:
    """비교용 정규화: 공백·줄바꿈·가운뎃점 제거."""
    return re.sub(r"[\s·ㆍ・]+", "", text or "")


def fix_dashes(text: str) -> str:
    """요구사항 ID 주변의 여러 대시 문자와 공백을 '-'로 통일한다."""
    return _DASHES.sub("-", text)


def loc(doc: Document, block: Block, quote: str | None = None) -> Locator:
    text = block.text
    q = (quote if quote is not None else text).strip()
    start = text.find(q) if q else -1
    return Locator(
        doc_id=doc.doc_id,
        block_id=block.id,
        page=block.page,
        char_start=start if start >= 0 else None,
        char_end=start + len(q) if start >= 0 else None,
        quote=q[:300],
    )


@dataclass
class Grid:
    """병합 셀을 펼친 표 격자. at[r][c]는 그 칸을 덮는 원본 셀 블록."""

    doc: Document
    table: Block
    cells: list[Block]
    at: list[list[Block | None]] = field(default_factory=list)

    @property
    def n_rows(self) -> int:
        return len(self.at)

    @property
    def n_cols(self) -> int:
        return len(self.at[0]) if self.at else 0

    def text(self, r: int, c: int) -> str:
        if 0 <= r < self.n_rows and 0 <= c < self.n_cols and self.at[r][c] is not None:
            return self.at[r][c].text  # type: ignore[union-attr]
        return ""

    def cell(self, r: int, c: int) -> Block | None:
        if 0 <= r < self.n_rows and 0 <= c < self.n_cols:
            return self.at[r][c]
        return None

    def origin_in_row(self, r: int, c: int) -> Block | None:
        """(r, c) 칸의 셀이 이 행에서 시작하면 그 셀, 아니면 None(위에서 내려온 병합 셀)."""
        b = self.cell(r, c)
        if b is not None and b.cell is not None and b.cell.row == r:
            return b
        return None

    def row_origins(self, r: int) -> list[Block]:
        out = [b for b in self.cells if b.cell is not None and b.cell.row == r]
        return sorted(out, key=lambda b: b.cell.col)  # type: ignore[union-attr]

    def row_cells(self, r: int) -> list[Block]:
        """행 r을 덮는 서로 다른 셀(왼쪽부터)."""
        seen: list[Block] = []
        for c in range(self.n_cols):
            b = self.at[r][c]
            if b is not None and b not in seen:
                seen.append(b)
        return seen

    def all_text(self) -> str:
        return " ".join(c.text for c in self.cells)


def build_grids(doc: Document) -> list[Grid]:
    by_table: dict[str, list[Block]] = {}
    for b in doc.blocks:
        if b.kind == "cell" and b.cell is not None:
            by_table.setdefault(b.cell.table_id, []).append(b)
    grids: list[Grid] = []
    for t in doc.tables():
        cells = by_table.get(t.id, [])
        if not cells:
            continue
        rows = max(c.cell.row + c.cell.rowspan for c in cells)  # type: ignore[union-attr]
        cols = max(c.cell.col + c.cell.colspan for c in cells)  # type: ignore[union-attr]
        at: list[list[Block | None]] = [[None] * cols for _ in range(rows)]
        for c in cells:
            ref = c.cell
            assert ref is not None
            for r in range(ref.row, min(ref.row + ref.rowspan, rows)):
                for k in range(ref.col, min(ref.col + ref.colspan, cols)):
                    if at[r][k] is None:
                        at[r][k] = c
        grids.append(Grid(doc=doc, table=t, cells=cells, at=at))
    return grids


def iter_lines(doc: Document, include_cells: bool = True) -> Iterator[tuple[Block, str]]:
    """본문 블록(과 선택적으로 셀)의 줄을 (블록, 줄) 쌍으로 돌려준다."""
    for b in doc.blocks:
        if b.kind in ("heading", "para") or (include_cells and b.kind == "cell"):
            for line in b.text.split("\n"):
                if line.strip():
                    yield b, line.strip()


_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def parse_number(text: str) -> float | None:
    m = _NUM.search((text or "").replace(",", ""))
    return float(m.group(0)) if m else None


_KRW_UNITS = [("조", 10**12), ("억", 10**8), ("천만", 10**7), ("백만", 10**6), ("만", 10**4), ("천", 10**3)]


def parse_krw(text: str) -> int | None:
    """'금 1,234,000,000원', '12.5억원', '123억 4,500만원', '1,234백만원'을 원 단위 정수로."""
    t = (text or "").replace(",", "").replace(" ", "")
    m = re.search(r"((?:\d+(?:\.\d+)?(?:조|억|천만|백만|만|천)?)+)원", t)
    if not m:
        return None
    expr = m.group(1)
    total = 0.0
    rest = expr
    for unit, mult in _KRW_UNITS:
        um = re.match(rf"^(.*?)(\d+(?:\.\d+)?){unit}(.*)$", rest)
        if um and not um.group(1):
            total += float(um.group(2)) * mult
            rest = um.group(3)
    if rest:
        if re.fullmatch(r"\d+(?:\.\d+)?", rest):
            total += float(rest)
        elif total == 0:
            return None
    value = int(round(total))
    return value if value > 0 else None
