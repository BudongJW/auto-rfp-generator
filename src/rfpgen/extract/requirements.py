"""요구사항 추출(설계서 7.3절 A·C 패스, 결정적).

세 가지 원천을 대조한다.
1. 상세 정의서 표(항목명-값 쌍): "요구사항 분류 | 기능 | 요구사항 ID | SFR-001" 처럼 한 행에
   쌍이 여러 개 있거나, "요구사항 상세설명 > 정의/세부내용"처럼 하위 항목명이 있는 형식
2. 요구사항 총괄표(목록형): 머리행에 고유번호·명칭 열이 있는 표
3. 본문 줄 머리의 ID(표에서 쓰인 접두어만 인정)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..schemas.common import Locator
from ..schemas.docir import Document
from ..schemas.rfp import ExtractionReport, Requirement
from .common import Grid, build_grids, fix_dashes, loc, norm

FIELD_LABELS: dict[str, set[str]] = {
    "id": {"요구사항고유번호", "고유번호", "요구사항id", "요구사항번호", "요구사항식별번호", "요구사항식별자", "id", "요구사항코드"},
    "category": {"요구사항분류", "요구사항구분", "요구사항유형", "분류", "구분"},
    "name": {"요구사항명칭", "요구사항명", "명칭", "요구사항제목"},
    "definition": {"정의", "요구사항정의", "개요"},
    "details": {"세부내용", "세부요구사항", "상세내용", "요구사항상세설명", "상세설명", "세부설명", "요구사항상세내용", "내용"},
    "outputs": {"산출정보", "산출물", "산출물정보"},
    "related": {"관련요구사항", "연관요구사항"},
    "source": {"요구사항출처", "출처"},
}
_LABEL_OF = {label: f for f, labels in FIELD_LABELS.items() for label in labels}

SUMMARY_ID_HEADERS = {"고유번호", "요구사항고유번호", "요구사항id", "id", "요구사항번호", "요구사항식별번호"}
SUMMARY_NAME_HEADERS = {"요구사항명칭", "명칭", "요구사항명", "요구사항"}
SUMMARY_CATEGORY_HEADERS = {"분류", "구분", "요구사항분류", "대분류", "중분류", "유형"}


def compile_id_regex(pattern: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9])({pattern})(?![0-9])")


def _label_field(text: str) -> str | None:
    key = norm(text).lower().rstrip(":：")
    return _LABEL_OF.get(key)


@dataclass
class _Partial:
    fields: dict[str, str] = field(default_factory=dict)
    locators: list[Locator] = field(default_factory=list)
    table_id: str = ""
    origin: str = "detail_table"

    def set(self, name: str, value: str, locator: Locator) -> None:
        value = value.strip()
        if not value:
            return
        if name in self.fields and name in ("details", "definition", "outputs"):
            self.fields[name] += "\n" + value
        elif name not in self.fields:
            self.fields[name] = value
        self.locators.append(locator)


_ITEM_START = re.compile(r"^(?:[□■○●◦◎◇◆▶▷►•·\-–※*ㅇ>]|\(?\d{1,2}[.)]|[가-하][.)]|\[)")


def _split_items(text: str) -> list[str]:
    """세부내용을 항목 단위로 나눈다. 글머리 기호 없이 시작하는 줄은 앞 항목의 줄바꿈으로 보고 잇는다."""
    items: list[str] = []
    for line in (ln.strip() for ln in text.split("\n")):
        if not line:
            continue
        if items and not _ITEM_START.match(line):
            items[-1] += " " + line
        else:
            items.append(line)
    return items


_COUNT_HEADER = {"요구사항수", "요구사항개수", "개수", "건수"}
_PREFIX_CELL = re.compile(r"\b([A-Z]{3})\s*-")


def declared_counts(docs: list[Document]) -> dict[str, int]:
    """RFP가 선언한 접두어별 요구사항 수("ID 부여규칙 | 요구사항수" 표)."""
    out: dict[str, int] = {}
    for doc in docs:
        for grid in build_grids(doc):
            heads = [norm(grid.text(0, c)) for c in range(grid.n_cols)]
            count_cols = [c for c, h in enumerate(heads) if h in _COUNT_HEADER]
            if not count_cols:
                continue
            cc = count_cols[0]
            for r in range(1, grid.n_rows):
                count_m = re.search(r"(\d+)", grid.text(r, cc).replace(",", ""))
                if not count_m:
                    continue
                for c in range(grid.n_cols):
                    if c == cc:
                        continue
                    m = _PREFIX_CELL.search(grid.text(r, c))
                    if m:
                        out[m.group(1)] = out.get(m.group(1), 0) + int(count_m.group(1))
                        break
    return out


def _edit_distance_le1(a: str, b: str) -> bool:
    if a == b:
        return True
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        if len(diff) == 1:
            return True
        return len(diff) == 2 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]]  # 인접 전치
    return False


def _prefix(req_id: str) -> str:
    return req_id.split("-", 1)[0]


class RequirementExtractor:
    def __init__(self, id_pattern: str) -> None:
        self.id_re = compile_id_regex(id_pattern)

    def find_ids(self, text: str) -> list[str]:
        return [m.group(1) for m in self.id_re.finditer(fix_dashes(text))]

    # ---- 1. 상세 정의서 표 -------------------------------------------------
    def _detail_records(self, grid: Grid) -> list[_Partial]:
        """항목명 셀 오른쪽의 값 셀을 읽는다. 가장 안쪽 항목명이 값의 필드를 정한다."""
        doc = grid.doc
        records: list[_Partial] = []
        current: _Partial | None = None
        pending_category: tuple[str, Locator] | None = None
        has_id_label = False
        for r in range(grid.n_rows):
            label: str | None = None
            for cell in grid.row_cells(r):
                f = _label_field(cell.text)
                if f is not None and len(norm(cell.text)) <= 12:
                    # 행을 덮는 상위 항목명(세로 병합)은 하위 항목명이 없을 때만 쓰인다.
                    label = f
                    if f == "id":
                        has_id_label = True
                    continue
                if label is None or cell.cell is None or cell.cell.row != r:
                    continue
                value = cell.text
                locator = loc(doc, cell)
                if label == "id":
                    ids = self.find_ids(value)
                    if not ids:
                        label = None
                        continue
                    current = _Partial(table_id=grid.table.id)
                    records.append(current)
                    current.set("id", ids[0], locator)
                    if pending_category:
                        current.set("category", *pending_category)
                        pending_category = None
                elif label == "category" and (current is None or "category" in current.fields):
                    pending_category = (value, locator)
                elif current is not None:
                    current.set(label, value, locator)
                label = None
        if not has_id_label:
            return []
        if pending_category and records and "category" not in records[-1].fields:
            records[-1].set("category", *pending_category)
        return records

    def _continuation_text(self, grid: Grid) -> str | None:
        """앞 표에서 이어진(쪽 넘김) 세부내용 표면 그 텍스트를 돌려준다."""
        labels = [c for c in grid.cells if _label_field(c.text)]
        if labels or self.find_ids(grid.all_text()):
            return None
        text = "\n".join(c.text for c in grid.cells if c.text.strip())
        return text or None

    # ---- 2. 총괄표(목록형) --------------------------------------------------
    def _summary_records(self, grid: Grid) -> list[_Partial]:
        doc = grid.doc
        header_row = None
        id_col = name_col = None
        cat_cols: list[int] = []
        for r in range(min(grid.n_rows, 3)):
            heads = [norm(grid.text(r, c)).lower() for c in range(grid.n_cols)]
            ids = [c for c, h in enumerate(heads) if h in SUMMARY_ID_HEADERS]
            names = [c for c, h in enumerate(heads) if h in SUMMARY_NAME_HEADERS]
            if ids and names:
                header_row, id_col, name_col = r, ids[0], names[0]
                cat_cols = [c for c, h in enumerate(heads) if h in SUMMARY_CATEGORY_HEADERS]
                break
        if header_row is None or id_col is None or name_col is None:
            return []
        out: list[_Partial] = []
        for r in range(header_row + 1, grid.n_rows):
            id_cell = grid.cell(r, id_col)
            if id_cell is None:
                continue
            ids = self.find_ids(id_cell.text)
            if not ids:
                continue
            p = _Partial(table_id=grid.table.id, origin="summary_table")
            p.set("id", ids[0], loc(doc, id_cell))
            name_cell = grid.cell(r, name_col)
            if name_cell is not None and name_cell is not id_cell:
                p.set("name", name_cell.text.replace("\n", " "), loc(doc, name_cell))
            cats: list[str] = []
            for c in cat_cols:
                cell = grid.cell(r, c)
                if cell is not None and cell.text.strip() and cell.text.replace("\n", " ") not in cats:
                    cats.append(cell.text.replace("\n", " "))
            if cats:
                p.fields["category"] = " > ".join(cats)
            out.append(p)
        return out

    # ---- 전체 ------------------------------------------------------------
    def extract(self, docs: list[Document], report: ExtractionReport) -> list[Requirement]:
        details: dict[str, list[_Partial]] = {}
        summary: dict[str, _Partial] = {}
        summary_order: list[str] = []
        detail_order: list[str] = []
        for doc in docs:
            last_detail: _Partial | None = None
            last_detail_index = -1
            index = {b.id: i for i, b in enumerate(doc.blocks)}
            heading_idx = [i for i, b in enumerate(doc.blocks) if b.kind == "heading"]
            first_table_of_page: dict[int | None, str] = {}
            for b in doc.blocks:
                if b.kind == "table" and b.parent is None:
                    first_table_of_page.setdefault(b.page, b.id)
            for grid in build_grids(doc):
                if grid.table.parent is not None:
                    continue
                t_index = index[grid.table.id]
                recs = self._detail_records(grid)
                if recs:
                    for p in recs:
                        rid = p.fields["id"]
                        if rid not in details:
                            detail_order.append(rid)
                        details.setdefault(rid, []).append(p)
                    last_detail, last_detail_index = recs[-1], t_index
                    continue
                srecs = self._summary_records(grid)
                if srecs:
                    for p in srecs:
                        rid = p.fields["id"]
                        if rid not in summary:
                            summary[rid] = p
                            summary_order.append(rid)
                    last_detail = None
                    continue
                # 쪽 넘김으로 잘린 상세 정의서: 다음 쪽 첫 표이고 사이에 제목이 없으면 이어 붙인다.
                if (
                    last_detail is not None
                    and grid.table.page is not None
                    and first_table_of_page.get(grid.table.page) == grid.table.id
                    and not any(last_detail_index < h < t_index for h in heading_idx)
                ):
                    cont = self._continuation_text(grid)
                    if cont:
                        last_detail.set("details", cont, loc(doc, grid.table, ""))
                        last_detail_index = t_index
                        continue
                last_detail = None

        requirements: list[Requirement] = []
        for rid in detail_order + [r for r in summary_order if r not in details]:
            parts = details.get(rid)
            if parts and len(parts) > 1:
                report.add("REQ-DUP", "warning", f"{rid}: 상세 정의서가 {len(parts)}번 나옵니다 — 첫 번째를 사용합니다",
                           [lc for p in parts for lc in p.locators[:1]])
            base = parts[0] if parts else summary[rid]
            s = summary.get(rid)
            f = dict(base.fields)
            if s is not None:
                for k in ("name", "category"):
                    f.setdefault(k, s.fields.get(k, ""))
            requirements.append(Requirement(
                id=rid,
                prefix=_prefix(rid),
                category=f.get("category", "").replace("\n", " "),
                name=f.get("name", "").replace("\n", " "),
                definition=f.get("definition", ""),
                details=_split_items(f.get("details", "")),
                outputs=_split_items(f.get("outputs", "")),
                related=self.find_ids(f.get("related", "")),
                source=f.get("source", ""),
                origin="detail_table" if parts else "summary_table",  # type: ignore[arg-type]
                locators=base.locators + (s.locators[:1] if s is not None and parts else []),
            ))

        # 총괄표와 상세 정의서 대조
        if summary and details:
            only_summary = [r for r in summary_order if r not in details]
            only_detail = [r for r in detail_order if r not in summary]
            if only_summary:
                report.add("REQ-NO-DETAIL", "warning",
                           f"총괄표에만 있고 상세 정의서가 없는 요구사항 {len(only_summary)}건: {', '.join(only_summary[:20])}")
            if only_detail:
                report.add("REQ-NOT-IN-SUMMARY", "warning",
                           f"상세 정의서에만 있고 총괄표에 없는 요구사항 {len(only_detail)}건: {', '.join(only_detail[:20])}")

        # 3. 본문 줄 머리의 ID(표에서 확인된 접두어만)
        known = {r.prefix for r in requirements}
        have = {r.id for r in requirements}
        for doc in docs:
            for b in doc.blocks:
                if b.kind not in ("para", "heading"):
                    continue
                for line in b.text.split("\n"):
                    fixed = fix_dashes(line.strip())
                    m = self.id_re.match(fixed)
                    if not m:
                        continue
                    rid = m.group(1)
                    if rid in have or _prefix(rid) not in known:
                        continue
                    have.add(rid)
                    name = fixed[m.end():].strip(" :：.-)")
                    requirements.append(Requirement(
                        id=rid, prefix=_prefix(rid), name=name[:80], origin="text_rule",
                        locators=[loc(doc, b, line.strip())],
                    ))
                    report.add("REQ-TEXT-ONLY", "warning", f"{rid}: 표가 아닌 본문에서만 발견됐습니다 — 확인 필요",
                               [loc(doc, b, line.strip())])

        if not requirements:
            report.add("REQ-NONE", "error", "요구사항을 하나도 찾지 못했습니다 — 요구사항 표 형식 또는 ID 규칙을 확인하세요")
        missing_name = [r.id for r in requirements if not r.name]
        if missing_name:
            report.add("REQ-NO-NAME", "info", f"명칭이 비어 있는 요구사항 {len(missing_name)}건: {', '.join(missing_name[:15])}")

        self._check_declared_counts(docs, requirements, report)
        self._check_suspicious_ids(docs, requirements, report)
        return requirements

    def _check_declared_counts(self, docs: list[Document], reqs: list[Requirement],
                               report: ExtractionReport) -> None:
        declared = declared_counts(docs)
        if not declared:
            return
        found: dict[str, int] = {}
        for r in reqs:
            found[r.prefix or ""] = found.get(r.prefix or "", 0) + 1
        for prefix, n in sorted(declared.items()):
            got = found.get(prefix, 0)
            if got != n:
                report.add("REQ-COUNT-MISMATCH", "error" if got < n else "warning",
                           f"{prefix}: RFP가 선언한 요구사항 수 {n}건, 추출 {got}건 — "
                           + ("누락 가능성(이미지·도형 글자, 다른 표 형식). 원문 확인 필요" if got < n else "선언보다 많음"))
        extra = sorted(set(found) - set(declared))
        if extra:
            report.add("REQ-COUNT-UNDECLARED", "info", f"선언표에 없는 접두어: {', '.join(extra)}")
        report.stats["declared_requirements"] = sum(declared.values())

    def _check_suspicious_ids(self, docs: list[Document], reqs: list[Requirement],
                              report: ExtractionReport) -> None:
        """표에 없는 ID 언급 중 알려진 접두어와 한 글자 차이인 것은 RFP 오타로 의심한다."""
        known = {r.prefix for r in reqs if r.prefix}
        have = {r.id for r in reqs}
        for doc in docs:
            for b in doc.blocks:
                for rid in self.find_ids(b.text):
                    p = _prefix(rid)
                    if rid in have or p in known:
                        if p in known and rid not in have and b.kind == "cell":
                            report.add("REQ-UNKNOWN-REF", "info", f"{rid}: 다른 곳에서 참조되지만 정의되지 않은 ID",
                                       [loc(doc, b, rid)])
                            have.add(rid)
                        continue
                    near = [k for k in known if _edit_distance_le1(p, k)]
                    if near:
                        report.add("REQ-ID-TYPO", "warning",
                                   f"{rid}: 정의되지 않은 접두어 '{p}' — '{near[0]}'의 오타로 보입니다(발주기관 질의 후보)",
                                   [loc(doc, b, rid)])
                        have.add(rid)
