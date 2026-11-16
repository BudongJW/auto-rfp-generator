"""HWPX(OWPML, KS X 6101) 파서.

`Contents/section*.xml`의 문단(hp:p)과 표(hp:tbl)를 문서 순서대로 DocIR 블록으로 바꾼다.
표 셀은 `hp:cellAddr`(rowAddr, colAddr)와 `hp:cellSpan`(rowSpan, colSpan)으로 위치와
병합을 보존한다. 셀 안의 중첩 표는 parent가 셀인 별도 표 블록이 된다.
"""

from __future__ import annotations

import re

from lxml import etree

from ..schemas.docir import Block, Document
from .builder import DocBuilder
from .safety import UnsafeInputError, open_zip, parse_xml, read_member

HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HH = "http://www.hancom.co.kr/hwpml/2011/head"
_P = f"{{{HP}}}p"
_RUN = f"{{{HP}}}run"
_T = f"{{{HP}}}t"
_TBL = f"{{{HP}}}tbl"
_TR = f"{{{HP}}}tr"
_TC = f"{{{HP}}}tc"
_SUBLIST = f"{{{HP}}}subList"
_CELLADDR = f"{{{HP}}}cellAddr"
_CELLSPAN = f"{{{HP}}}cellSpan"

_SECTION_RE = re.compile(r"^Contents/section(\d+)\.xml$")


def _style_names(zf) -> dict[str, str]:
    try:
        root = parse_xml(read_member(zf, "Contents/header.xml"))
    except KeyError:
        return {}
    names: dict[str, str] = {}
    for st in root.iter(f"{{{HH}}}style"):
        sid = st.get("id")
        if sid is not None:
            names[sid] = st.get("name") or ""
    return names


def _t_text(t: etree._Element) -> str:
    parts: list[str] = [t.text or ""]
    for child in t:
        local = etree.QName(child).localname
        if local == "lineBreak":
            parts.append("\n")
        elif local == "tab":
            parts.append("\t")
        parts.append(child.tail or "")
    return "".join(parts)


def _paragraph_text(p: etree._Element) -> str:
    """문단의 직속 run에 있는 글자만 모은다(중첩 표·글상자 내용은 제외)."""
    out: list[str] = []
    for run in p.findall(_RUN):
        for child in run:
            if child.tag == _T:
                out.append(_t_text(child))
    return "".join(out)


class _HwpxWalker:
    def __init__(self, builder: DocBuilder, styles: dict[str, str]) -> None:
        self.b = builder
        self.styles = styles

    def container(self, elem: etree._Element, parent: str | None = None) -> list[str]:
        """hs:sec 또는 hp:subList 안의 문단을 차례로 처리하고, 문단 텍스트 목록을 돌려준다."""
        texts: list[str] = []
        for p in elem.findall(_P):
            text = _paragraph_text(p)
            if text.strip():
                texts.append(text)
                if parent is None:
                    style = self.styles.get(p.get("styleIDRef", ""))
                    self.b.text(text, style=style)
            for run in p.findall(_RUN):
                for child in run:
                    if child.tag == _TBL:
                        self.table(child, parent)
                    elif child.tag != _T:
                        # 글상자 등 그리기 개체 안의 문단. 머리말·꼬리말·각주는 건너뛴다.
                        for sub in child.iter(_SUBLIST):
                            owner = sub.getparent()
                            if owner is not None and etree.QName(owner).localname == "drawText":
                                inner = self.container(sub, parent)
                                if parent is not None:
                                    texts.extend(inner)
        return texts

    def table(self, tbl: etree._Element, parent: str | None) -> None:
        rows = int(tbl.get("rowCnt", "0") or 0)
        cols = int(tbl.get("colCnt", "0") or 0)
        table = self.b.table(rows, cols, parent=parent)
        cells: list[Block] = []
        for r_index, tr in enumerate(tbl.findall(_TR)):
            for c_index, tc in enumerate(tr.findall(_TC)):
                addr = tc.find(_CELLADDR)
                span = tc.find(_CELLSPAN)
                row = int(addr.get("rowAddr", r_index)) if addr is not None else r_index
                col = int(addr.get("colAddr", c_index)) if addr is not None else c_index
                rowspan = int(span.get("rowSpan", 1)) if span is not None else 1
                colspan = int(span.get("colSpan", 1)) if span is not None else 1
                cell = self.b.cell(table, "", row, col, rowspan, colspan)
                sub = tc.find(_SUBLIST)
                texts = self.container(sub, parent=cell.id) if sub is not None else []
                cell.text = "\n".join(t.strip() for t in texts if t.strip())
                cells.append(cell)
        self.b.finish_table(table, cells)


def parse_hwpx_bytes(data: bytes, doc: Document) -> Document:
    zf = open_zip(data, doc.filename)
    names = zf.namelist()
    sections = sorted(
        (int(m.group(1)), n) for n in names if (m := _SECTION_RE.match(n))
    )
    if not sections:
        raise UnsafeInputError(f"{doc.filename}: HWPX 본문(Contents/section*.xml)이 없습니다")
    builder = DocBuilder(doc)
    walker = _HwpxWalker(builder, _style_names(zf))
    for _, name in sections:
        root = parse_xml(read_member(zf, name))
        walker.container(root)
    return doc
