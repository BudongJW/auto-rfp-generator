"""평가표 추출(설계서 7.3절 A 패스, 결정적).

머리행에 '배점'과 평가 관련 열(부문·항목·요소·기준)이 있는 표를 평가표로 본다.
부문 열은 세로 병합을 펼쳐 읽고, 항목이 빈 행의 배점은 부문 배점, '소계·합계' 행은 선언 합계로 처리한다.
정량/정성은 표 앞의 문단('계량평가', '비계량평가', '정량', '정성')이나 '구분' 열 값으로 정한다.
"""

from __future__ import annotations

import re

from ..schemas.common import Extracted
from ..schemas.docir import Document
from ..schemas.rfp import EvalArea, EvalItem, EvalRule, EvaluationTable, ExtractionReport
from .common import Grid, build_grids, iter_lines, loc, norm, parse_number

_POINTS = ("배점", "배점한도", "점수", "배점(점)", "평가배점")
_AREA = ("평가부문", "부문", "평가분야", "분야", "대분류", "평가영역")
_ITEM = ("평가항목", "세부평가항목", "세부항목", "중분류", "평가지표", "항목")
_CRIT = ("평가요소", "평가기준", "평가내용", "세부평가내용", "평가방법", "주요평가내용", "세부내용", "평가착안사항", "착안사항")
_KIND_COL = ("구분",)
_TOTAL = {"소계", "합계", "계", "총계", "총점", "합", "총배점"}


def _kind_of(text: str) -> str | None:
    t = norm(text)
    if "비계량" in t or "정성" in t:
        return "정성"
    if "계량" in t or "정량" in t:
        return "정량"
    return None


def _roles(heads: list[str]) -> dict[str, int]:
    roles: dict[str, int] = {}
    for c, h in enumerate(heads):
        if not h:
            continue
        if "points" not in roles and any(h.startswith(p) for p in _POINTS):
            roles["points"] = c
        elif "area" not in roles and h in _AREA:
            roles["area"] = c
        elif h in _ITEM:
            # '평가항목'과 '세부평가항목'이 함께 있으면 앞의 것이 부문 역할을 한다.
            if "item" in roles and "area" not in roles:
                roles["area"] = roles["item"]
            roles["item"] = c
        elif "crit" not in roles and h in _CRIT:
            roles["crit"] = c
        elif "kind" not in roles and h in _KIND_COL:
            roles["kind"] = c
    if "item" not in roles and "area" in roles and "crit" in roles:
        roles["item"] = roles["area"]
    return roles


def _find_header(grid: Grid) -> tuple[int, dict[str, int]] | None:
    for r in range(min(grid.n_rows, 3)):
        heads = [norm(grid.text(r, c)) for c in range(grid.n_cols)]
        roles = _roles(heads)
        if "points" in roles and ("item" in roles or "area" in roles):
            return r, roles
    return None


def _context_kind(doc: Document, table_index: int, lookback: int = 6) -> str | None:
    n = 0
    for b in reversed(doc.blocks[:table_index]):
        if b.kind in ("para", "heading"):
            k = _kind_of(b.text) if len(b.text) < 80 else None
            if k:
                return k
            n += 1
            if n >= lookback:
                break
    return None


# 평가 '규칙'(점수를 매기는 방법) 판별. 제안서가 답할 '평가 질문'과 분리한다.
# OpenBidKit_Yibiao(AGPL-3.0, 77a38f0)의 评分项/评分要求 분리 기준을 한국 평가표 표현으로 재구현.
_RULE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("감점", re.compile(r"감점")),
    ("가점", re.compile(r"가점")),
    ("산식", re.compile(r"\d+\s*점\s*(?:부여|배점|만점)|\d+\s*(?:억|백만|천만)?\s*원?\s*이상\s*[:：]|[×÷]|산식|평점|구간별|비율에\s*따라|환산")),
]
# 등급 정의: '수(10)·우(8)…', 'A등급', '매우 우수 … 보통', '우수: 8점'처럼 등급 이름과 점수가 함께 있어야 한다.
# '참가(', '평가('처럼 '가·미·수'로 끝나는 낱말 뒤 괄호를 등급으로 오인하지 않도록 낱말 경계를 요구한다.
_GRADE_MARK = re.compile(r"(?:^|[\s,/·:])(?:수|우|미|양|가)\s*[:(（]\s*\d")
_GRADE_OTHER = re.compile(r"[A-E]\s*등급|등급\s*(?:별|기준|적용)|(?:매우\s*우수|탁월).{0,30}(?:우수|보통)|(?:우수|보통|미흡)\s*[:：]\s*\d")
_QUESTION_END = re.compile(r"(?:는가|는지|인가|평가|평가함|평가한다)\s*[.?]?$")


def classify_criterion(text: str) -> str | None:
    """평가 규칙이면 종류를, 평가 질문이면 None을 돌려준다."""
    if _QUESTION_END.search(text) and not re.search(r"감점|가점", text):
        return None
    for kind, pat in _RULE_PATTERNS[:2]:
        if pat.search(text):
            return kind
    if len(_GRADE_MARK.findall(text)) >= 2 or _GRADE_OTHER.search(text):
        return "등급"
    if _RULE_PATTERNS[2][1].search(text):
        return "산식"
    return None


def _split_criteria(text: str) -> list[str]:
    items: list[str] = []
    for line in (ln.strip() for ln in text.split("\n")):
        if not line:
            continue
        if items and not re.match(r"^[-–•·○◦□※*ㅇ]|^\(?\d{1,2}[.)]", line):
            items[-1] += " " + line
        else:
            items.append(line.lstrip("-–•·○◦□※*ㅇ ").strip())
    return [i for i in items if i]


class _Builder:
    def __init__(self) -> None:
        self.areas: list[EvalArea] = []
        self._n_area = 0
        self._n_item = 0

    def area(self, name: str, kind: str) -> EvalArea:
        key = (kind, norm(name))
        for a in self.areas:
            if (a.kind, norm(a.name)) == key:
                return a
        self._n_area += 1
        a = EvalArea(id=f"A{self._n_area:02d}", name=name, kind=kind)  # type: ignore[arg-type]
        self.areas.append(a)
        return a

    def item(self, area: EvalArea, name: str) -> EvalItem:
        for it in area.items:
            if norm(it.name) == norm(name):
                return it
        self._n_item += 1
        it = EvalItem(id=f"{area.id}-{len(area.items) + 1:02d}", name=name, kind=area.kind)
        area.items.append(it)
        return it


def extract_evaluation(docs: list[Document], report: ExtractionReport) -> EvaluationTable:
    table = EvaluationTable()
    builder = _Builder()
    for doc in docs:
        index = {b.id: i for i, b in enumerate(doc.blocks)}
        carry: EvalArea | None = None
        for grid in build_grids(doc):
            header = _find_header(grid)
            if header is None:
                continue
            h_row, roles = header
            table.source_tables.append(grid.table.id)
            ctx_kind = _context_kind(doc, index[grid.table.id])
            area_col = roles.get("area")
            item_col = roles.get("item", area_col)
            has_item_col = item_col is not None and item_col != area_col
            for r in range(h_row + 1, grid.n_rows):
                one_line = lambda s: s.replace("\n", " ").strip()  # noqa: E731
                area_text = one_line(grid.text(r, area_col)) if area_col is not None else ""
                if has_item_col:
                    item_cell = grid.origin_in_row(r, item_col)  # type: ignore[arg-type]
                    item_text = one_line(item_cell.text) if item_cell is not None else ""
                else:
                    # 항목 열만 있거나(부문=항목) 부문 열만 있는 표: 한 행이 한 항목이다.
                    item_cell = grid.cell(r, item_col) if item_col is not None else None  # type: ignore[arg-type]
                    item_text = one_line(item_cell.text) if item_cell is not None else ""
                    area_text = area_text or item_text
                pts_cell = grid.origin_in_row(r, roles["points"])
                pts = parse_number(pts_cell.text) if pts_cell is not None else None
                if norm(area_text) in _TOTAL or norm(item_text) in _TOTAL:
                    if pts is not None:
                        table.declared_totals.append(pts)
                    continue
                if not area_text and not item_text:
                    continue
                kind = _kind_of(grid.text(r, roles["kind"])) if "kind" in roles else None
                kind = kind or _kind_of(area_text) or ctx_kind or "미정"
                if has_item_col and not area_text and carry is not None and carry.kind == kind:
                    area = carry  # 쪽 넘김으로 부문 칸이 빈 행: 앞 부문을 이어받는다
                else:
                    area = builder.area(area_text or item_text, kind)
                carry = area
                area_cell = grid.cell(r, area_col) if area_col is not None else None
                if area_cell is not None and not area.locators:
                    area.locators.append(loc(doc, area_cell))
                if has_item_col and not item_text:
                    if pts is not None:
                        area.points = pts  # 항목이 빈 행의 배점은 부문 배점
                    continue
                it = builder.item(area, item_text)
                if pts is not None:
                    if has_item_col:
                        it.points = it.points if it.points is not None else pts
                    else:
                        it.points = (it.points or 0) + pts  # 같은 부문의 여러 행은 합산
                if item_cell is not None and not it.locators:
                    it.locators.append(loc(doc, item_cell))
                crit_col = roles.get("crit")
                if crit_col is not None:
                    crit_cell = grid.origin_in_row(r, crit_col)
                    if crit_cell is not None and crit_cell.text.strip():
                        for c in _split_criteria(crit_cell.text):
                            kind = classify_criterion(c)
                            if kind is not None:
                                table.rules.append(EvalRule(kind=kind, text=c, item_id=it.id,  # type: ignore[arg-type]
                                                            locators=[loc(doc, crit_cell, c)]))
                            elif c not in it.criteria:
                                it.criteria.append(c)
                        it.locators.append(loc(doc, crit_cell))
    table.areas = [a for a in builder.areas if a.items or a.points]
    _fill_and_validate(table, report)
    table.tech_price_ratio = _tech_price_ratio(docs)
    if table.tech_price_ratio is None:
        report.add("EVAL-RATIO-MISSING", "warning", "기술:가격 배점 비율을 찾지 못했습니다 — 프로필 기본값을 씁니다")
    return table


def _fill_and_validate(table: EvaluationTable, report: ExtractionReport) -> None:
    if not table.areas:
        report.add("EVAL-NONE", "error", "평가표를 찾지 못했습니다 — 기본 목차 템플릿을 씁니다")
        return
    for a in table.areas:
        item_sum = sum(it.points or 0 for it in a.items)
        if a.points is None:
            a.points = item_sum or None
        elif item_sum and abs(item_sum - a.points) > 0.01:
            report.add("EVAL-AREA-SUM", "warning",
                       f"'{a.name}' 부문 배점 {a.points:g}점 ≠ 항목 합계 {item_sum:g}점", a.locators[:1])
        missing = [it.name for it in a.items if it.points is None]
        if missing:
            report.add("EVAL-ITEM-NO-POINTS", "warning", f"'{a.name}' 부문에서 배점을 읽지 못한 항목: {', '.join(missing)}",
                       a.locators[:1])
        if a.kind == "미정":
            report.add("EVAL-KIND-UNKNOWN", "warning", f"'{a.name}' 부문의 정량/정성 구분을 찾지 못했습니다", a.locators[:1])
    total = sum(a.points or 0 for a in table.areas)
    if table.declared_totals:
        declared = sum(table.declared_totals)
        if abs(declared - total) > 0.01:
            report.add("EVAL-TOTAL", "info", f"소계·합계 행 합 {declared:g}점, 부문 배점 합 {total:g}점 — 표가 나뉘어 있으면 정상일 수 있습니다")
    report.stats["eval_rules"] = len(table.rules)
    report.stats["eval_areas"] = len(table.areas)
    report.stats["eval_items"] = len(table.items())
    report.stats["eval_total_points"] = total


_RATIO_PATTERNS = [
    re.compile(r"기술[가-힣\s]*평가\s*[(\[（]?\s*(\d{1,3})\s*(?:%|점|％)[^가-힣]{0,6}.{0,40}?가격[가-힣\s]*평가\s*[(\[（]?\s*(\d{1,3})\s*(?:%|점|％)"),
    re.compile(r"기술\s*[:：]\s*가격\s*[=＝]?\s*(\d{1,3})\s*[:：]\s*(\d{1,3})"),
]


def _tech_price_ratio(docs: list[Document]) -> Extracted[list[int]] | None:
    for doc in docs:
        for block, line in iter_lines(doc, include_cells=False):
            for pat in _RATIO_PATTERNS:
                m = pat.search(line)
                if m:
                    tech, price = int(m.group(1)), int(m.group(2))
                    if tech + price == 100:
                        return Extracted[list[int]](value=[tech, price], locators=[loc(doc, block, m.group(0))])
        # 표 형식: '기술능력 평가(90%)' | '입찰가격 평가(10%)'
        for grid in build_grids(doc):
            for r in range(min(grid.n_rows, 3)):
                tech = price = None
                tech_cell = None
                for c in range(grid.n_cols):
                    t = grid.text(r, c)
                    mt = re.search(r"기술[가-힣\s]*평가\s*[(（]\s*(\d{1,3})\s*[%점％]", t)
                    mp = re.search(r"가격[가-힣\s]*평가\s*[(（]\s*(\d{1,3})\s*[%점％]", t)
                    if mt:
                        tech, tech_cell = int(mt.group(1)), grid.cell(r, c)
                    if mp:
                        price = int(mp.group(1))
                if tech is not None and price is not None and tech + price == 100 and tech_cell is not None:
                    return Extracted[list[int]](value=[tech, price], locators=[loc(doc, tech_cell)])
    return None
