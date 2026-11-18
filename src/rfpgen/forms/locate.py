"""공고 첨부(HWPX·HWP)에서 별지 서식 영역을 찾는다.

서식은 보통 "[별지 제1호서식]" 같은 표지 줄로 시작해 다음 표지 줄 앞에서 끝난다. 표지 줄은 최상위 문단이거나
쪽 테두리용 1칸 표 안의 첫 문단이다. 다음은 서식 시작으로 보지 않는다.
- 본문 문장 속 언급("별지 제3호 서식에 따라 작성") — 표지 뒤에 조사·동사가 오거나 줄이 길다
- 서식 목록(표지 줄만 연달아 있는 목차) — 내용(표·문단)이 없는 영역은 버리고, 같은 번호는 내용이 많은 쪽을 쓴다
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from lxml import etree

from .oxml import HP, lead_text, p_text

_OPEN = r"[\[〔【<〈《(（]?"
_CLOSE = r"[\]〕】>〉》)）]?"
MARKER = re.compile(
    rf"^\s*{_OPEN}\s*(?:별지|별첨|붙임)?\s*(?:제\s*)?(?:서식\s*)?(?:제\s*)?"
    rf"(?P<no>\d{{1,2}})(?:\s*[-－의]\s*(?P<sub>\d{{1,2}}))?\s*(?:호)?\s*(?:서식|양식)?\s*{_CLOSE}"
)
_HAS_FORM_WORD = re.compile(r"별지|서식|양식")
_REFERENCE_TAIL = re.compile(r"^\s*(?:에|을|를|의|과|와|로|으로|및|은|는|이|가|,|참조|참고|따라|에\s*따라|에\s*의)")
_TITLE_TRIM = re.compile(r"^[\s:：\-–—·.]+|[\s:：\-–—·.]+$")


@dataclass
class FormRegion:
    key: str               # "1", "4-2"
    title: str
    section: int
    start: int             # 최상위 문단 순번(포함)
    end: int               # (제외)
    tables: int
    paragraphs: int        # 비어 있지 않은 문단 수

    @property
    def form_no(self) -> str:
        return f"별지 제{self.key}호"

    @property
    def weight(self) -> int:
        return self.tables * 10 + self.paragraphs


def unspace(title: str) -> str:
    """'입 찰 참 가 신 청 서' 같은 자간 띄우기를 붙인다."""
    parts = title.split()
    if len(parts) >= 3 and sum(len(p) == 1 for p in parts) >= len(parts) - 1:
        return "".join(parts)
    return re.sub(r"\s+", " ", title).strip()


def match_marker(text: str) -> tuple[str, str] | None:
    """표지 줄이면 (번호 키, 줄의 나머지)를 돌려준다."""
    m = MARKER.match(text)
    if not m or not _HAS_FORM_WORD.search(m.group(0)) or len(text) > 60:
        return None
    rest = text[m.end():]
    if _REFERENCE_TAIL.match(rest):
        return None
    key = m.group("no").lstrip("0") or "0"
    if m.group("sub"):
        key += f"-{int(m.group('sub'))}"
    return key, _TITLE_TRIM.sub("", rest)


def _content(paras: list[etree._Element]) -> tuple[int, int]:
    tables = sum(len(p.findall(f".//{HP}tbl")) for p in paras)
    texts = sum(1 for p in paras for q in p.iter(f"{HP}p") if lead_text(q, 0))
    return tables, texts


def find_regions(section_elements: list[etree._Element]) -> list[FormRegion]:
    found: list[FormRegion] = []
    for s_i, sec in enumerate(section_elements):
        paras = [p for p in sec if p.tag == f"{HP}p"]
        starts: list[tuple[int, str, str]] = []
        for i, p in enumerate(paras):
            hit = match_marker(lead_text(p))
            if hit:
                starts.append((i, *hit))
        for n, (i, key, rest) in enumerate(starts):
            end = starts[n + 1][0] if n + 1 < len(starts) else len(paras)
            body = paras[i:end]
            tables, texts = _content(body)
            if tables == 0 and texts < 3:        # 서식 목록의 한 줄
                continue
            title = rest
            if not title:                        # 표지 줄 다음의 짧은 줄(쪽 테두리 표 안이어도)
                lines = [t for q in body[:6] for inner in q.iter(f"{HP}p") if (t := p_text(inner).strip())]
                title = next((t for t in lines[1:4] if len(t) <= 40 and not t.startswith("※")), "")
            found.append(FormRegion(key, unspace(title)[:40] or f"별지 제{key}호", s_i, i, end, tables, texts))
    best: dict[str, FormRegion] = {}
    for r in found:
        if r.key not in best or r.weight >= best[r.key].weight:
            best[r.key] = r
    return sorted(best.values(), key=lambda r: (r.section, r.start))
