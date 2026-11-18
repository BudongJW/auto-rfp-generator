"""HWPX(OWPML) 저수준 조작: 문단 글자 읽기·구간 바꾸기, 표 격자, 서식 영역 잘라내기.

python-hwpx(Apache-2.0)의 문서 객체 위에서 lxml 요소를 직접 다룬다. 원본 서식의 글자 모양(charPr)을
지키려고 문단 전체를 다시 쓰지 않고, 빈칸 구간의 글자만 바꾼다.

줄 배치 캐시(linesegarray): 내용이 바뀐 문단의 원래 캐시는 python-hwpx가 저장할 때 지운다(구역을 dirty로
표시해야 한다). 다만 캐시가 없는 문단을 rhwp가 다시 배치하면 짧은 줄이 넘친 것처럼 꺾여 양쪽으로 벌어지는
일이 있어(조달청 별지 제21호 '수 요 기 관:' 줄), 한 줄이던 문단이 채운 뒤에도 한 줄에 넉넉히 들어가면
같은 줄 정보로 캐시를 새로 써 둔다(refit_line_cache). 줄 수가 같으니 한글에서도 맞는 캐시다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from lxml import etree

HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HP = f"{{{HP_NS}}}"
_VIRTUAL = {f"{HP}tab": "\t", f"{HP}lineBreak": "\n"}


# ---------------------------------------------------------------- 문단 글자

@dataclass
class _Seg:
    """문단 글자의 한 조각: hp:t의 text, 또는 hp:t 안 자식 요소(탭·줄바꿈 등)와 그 tail."""

    owner: etree._Element
    attr: str                    # "text" | "tail" | "elem"
    start: int
    text: str


def _segments(p: etree._Element) -> list[_Seg]:
    segs: list[_Seg] = []
    pos = 0
    for run in p.findall(f"{HP}run"):
        for t in run.findall(f"{HP}t"):
            if t.text:
                segs.append(_Seg(t, "text", pos, t.text))
                pos += len(t.text)
            for child in t:
                v = _VIRTUAL.get(child.tag, "")
                if v:
                    segs.append(_Seg(child, "elem", pos, v))
                    pos += len(v)
                if child.tail:
                    segs.append(_Seg(child, "tail", pos, child.tail))
                    pos += len(child.tail)
    return segs


def p_text(p: etree._Element) -> str:
    """문단 자신의 글자(안에 든 표·그림의 글자는 빼고)."""
    return "".join(s.text for s in _segments(p))


def lead_text(p: etree._Element, limit: int = 40) -> str:
    """문단의 첫 글자들: 자기 글자가 없으면 안에 든 표의 첫 비어 있지 않은 문단(쪽 테두리용 1칸 표 대응)."""
    own = p_text(p).strip()
    if own:
        return own
    for i, inner in enumerate(p.iter(f"{HP}p")):
        if inner is p:
            continue
        if i > limit:
            break
        t = p_text(inner).strip()
        if t:
            return t
    return ""


def _ensure_t(p: etree._Element) -> etree._Element:
    runs = p.findall(f"{HP}run")
    run = runs[0] if runs else None
    if run is None:
        run = etree.Element(f"{HP}run", charPrIDRef="0")
        p.insert(0, run)
    t = run.find(f"{HP}t")
    if t is None:
        t = etree.SubElement(run, f"{HP}t")
    return t


_WIDE = re.compile(r"[\u1100-\u11ff\u2e80-\ua4cf\uac00-\ud7a3\uf900-\ufaff\ufe30-\ufe4f\uff00-\uffef]")


def text_em(text: str) -> float:
    """글자 폭 어림(전각=1em). 넘치지 않는 쪽으로 넉넉히 잡는다 — 반각 글자는 0.6em, 띄어쓰기 0.5em."""
    w = 0.0
    for ch in text:
        if ch == " ":
            w += 0.5
        elif _WIDE.match(ch) or ord(ch) >= 0x2000:
            w += 1.0
        else:
            w += 0.6
    return w


def refit_line_cache(p: etree._Element) -> None:
    """글자를 바꾼 문단의 줄 배치 캐시를 다시 정한다: 한 줄 캐시였고 새 글자도 한 줄에 들어가면 새로 쓰고, 아니면 지운다."""
    arr = p.find(f"{HP}linesegarray")
    if arr is None:
        return
    segs = arr.findall(f"{HP}lineseg")
    at = list(p).index(arr)
    p.remove(arr)
    if len(segs) != 1:
        return
    seg = segs[0]
    try:
        em = int(seg.get("textheight") or seg.get("vertsize") or 0)
        width = int(seg.get("horzsize") or 0)
    except ValueError:
        return
    text = p_text(p)
    if em <= 0 or width <= 0 or "\n" in text or "\t" in text or text_em(text) * em > width * 0.9:
        return
    fresh = etree.Element(f"{HP}linesegarray")
    line = etree.SubElement(fresh, f"{HP}lineseg", dict(seg.attrib))
    line.set("textpos", "0")
    p.insert(at, fresh)


def replace_span(p: etree._Element, start: int, end: int, value: str) -> None:
    """문단 글자 [start, end)를 value로 바꾼다. value는 start가 걸린 조각의 글자 모양을 따른다."""
    segs = _segments(p)
    texts = [s for s in segs if s.attr != "elem"]

    def _end(s: _Seg) -> int:
        return s.start + len(s.text)

    # 값은 빈칸과 실제로 겹치는 첫 조각(대개 빈칸용 글자 모양)에 넣고, 없으면 start에 닿는 마지막 조각에 넣는다
    target = next((s for s in texts if max(start, s.start) < min(end, _end(s))), None)
    if target is None:
        target = next((s for s in reversed(texts) if s.start <= start <= _end(s)), None)
    drop = [s.owner for s in segs if s.attr == "elem" and start <= s.start and _end(s) <= end]
    for s in texts:
        lo, hi = max(start, s.start), min(end, _end(s))
        a = lo - s.start
        b = max(hi - s.start, a)
        if s is target:
            setattr(s.owner, s.attr, s.text[:a] + value + s.text[b:])
        elif lo < hi:
            setattr(s.owner, s.attr, s.text[:a] + s.text[b:])
    if target is None:
        t = _ensure_t(p)
        t.text = value + (t.text or "")
    for el in drop:
        parent = el.getparent()
        if parent is None:
            continue
        if el.tail:
            prev = el.getprevious()
            if prev is not None:
                prev.tail = (prev.tail or "") + el.tail
            else:
                parent.text = (parent.text or "") + el.tail
        parent.remove(el)
    refit_line_cache(p)


# ---------------------------------------------------------------- 표 격자

@dataclass
class Cell:
    el: etree._Element
    row: int
    col: int
    rowspan: int
    colspan: int
    paragraphs: list[etree._Element]
    nested: bool

    @property
    def text(self) -> str:
        return "\n".join(p_text(p) for p in self.paragraphs).strip()


@dataclass
class Grid:
    tbl: etree._Element
    cells: list[Cell]
    rows: int
    cols: int
    at: dict[tuple[int, int], Cell] = field(default_factory=dict)

    def owner(self, r: int, c: int) -> Cell | None:
        return self.at.get((r, c))

    def right(self, cell: Cell) -> Cell | None:
        return self.owner(cell.row, cell.col + cell.colspan)

    def below(self, cell: Cell) -> Cell | None:
        return self.owner(cell.row + cell.rowspan, cell.col)

    def row_cells(self, r: int) -> list[Cell]:
        return sorted((c for c in self.cells if c.row == r), key=lambda c: c.col)

    def physical_row(self, r: int) -> int:
        """논리 행 r이 시작하는 hp:tr의 순번(병합 행이 있으면 다를 수 있다)."""
        trs = self.tbl.findall(f"{HP}tr")
        for i, tr in enumerate(trs):
            for tc in tr.findall(f"{HP}tc"):
                addr = tc.find(f"{HP}cellAddr")
                if addr is not None and int(addr.get("rowAddr", "-1")) == r:
                    return i
        return min(r, len(trs) - 1)


def build_grid(tbl: etree._Element) -> Grid:
    cells: list[Cell] = []
    for r_i, tr in enumerate(tbl.findall(f"{HP}tr")):
        for c_i, tc in enumerate(tr.findall(f"{HP}tc")):
            addr, span = tc.find(f"{HP}cellAddr"), tc.find(f"{HP}cellSpan")
            row = int(addr.get("rowAddr", r_i)) if addr is not None else r_i
            col = int(addr.get("colAddr", c_i)) if addr is not None else c_i
            rs = int(span.get("rowSpan", 1)) if span is not None else 1
            cs = int(span.get("colSpan", 1)) if span is not None else 1
            sub = tc.find(f"{HP}subList")
            paras = sub.findall(f"{HP}p") if sub is not None else []
            cells.append(Cell(tc, row, col, max(rs, 1), max(cs, 1), paras, tc.find(f".//{HP}tbl") is not None))
    grid = Grid(tbl, cells, rows=max((c.row + c.rowspan for c in cells), default=0),
                cols=max((c.col + c.colspan for c in cells), default=0))
    for c in cells:
        for r in range(c.row, c.row + c.rowspan):
            for k in range(c.col, c.col + c.colspan):
                grid.at.setdefault((r, k), c)
    return grid


def set_cell_value(cell: Cell, start: int, end: int, value: str) -> None:
    """칸 첫 문단의 [start, end)를 값으로 바꾼다. 문단이 없으면 만든다."""
    if not cell.paragraphs:
        sub = cell.el.find(f"{HP}subList")
        if sub is None:
            sub = etree.SubElement(cell.el, f"{HP}subList")
            cell.el.insert(0, sub)
        p = etree.SubElement(sub, f"{HP}p", paraPrIDRef="0", styleIDRef="0", pageBreak="0", columnBreak="0", merged="0")
        cell.paragraphs.append(p)
    replace_span(cell.paragraphs[0], start, end, value)


# ---------------------------------------------------------------- 서식 영역 잘라내기

_KEEP_IN_FIRST = {f"{HP}secPr", f"{HP}ctrl"}


def keep_region(section_el: etree._Element, start: int, end: int) -> None:
    """구역의 최상위 문단 중 [start, end)만 남긴다. 구역 설정(secPr)·단 설정은 남는 첫 문단으로 옮긴다."""
    paras = [p for p in section_el if p.tag == f"{HP}p"]
    if not paras or (start == 0 and end >= len(paras)):
        return
    first, head = paras[0], paras[start]
    if start > 0:
        moved: list[etree._Element] = []
        char_ref = "0"
        for run in first.findall(f"{HP}run"):
            kept = [c for c in run if c.tag in _KEEP_IN_FIRST]
            if kept and not moved:
                char_ref = run.get("charPrIDRef", "0")
            moved.extend(kept)
        if moved:
            new_run = etree.Element(f"{HP}run", charPrIDRef=char_ref)
            for c in moved:
                c.tail = None
                new_run.append(c)          # lxml append는 원래 위치에서 옮긴다
            head.insert(0, new_run)
        head.set("pageBreak", "0")
    for i, p in enumerate(paras):
        if not (start <= i < end):
            section_el.remove(p)
