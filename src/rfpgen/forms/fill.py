"""별지 서식 빈칸 채우기(설계서 7.9절).

세 가지 모양을 채운다(docs/analysis/hwpx-rendering-tools.md 6장의 양식 채우기 규칙을 다시 구현).
1. 이름표 칸: 짧은 이름표(상호·대표자·사업자등록번호 …) 오른쪽 칸이 비었으면 그 칸, 아니면 아래 칸
2. 목록 표: 머리글 행(사업명·발주기관·계약금액 / 성명·등급·경력 / 인증명·인증번호)을 보고 빈 행에
   KB 실적·인력·인증을 한 줄씩 넣는다. 행이 모자라면 마지막 빈 행을 복제해 늘린다.
3. 문단: "상    호 :", "대 표 자 :          (인)" 같은 이름표-쌍점 빈칸과 "2025.   .   ." 같은 날짜 칸

채우지 않는 것: 서명·날인, 선택 칸(□), 모르는 이름표 — 모두 점검 결과로 남겨 사람이 처리한다.
블라인드 서식(지정 목차가 가리키는 서식)에는 회사 식별 정보와 실명을 넣지 않는다.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from lxml import etree

from ..schemas.draft import CheckFinding
from ..schemas.forms import FormFill, FormResult
from ..schemas.kb import CompanyKB, _krw
from ..schemas.rfp import Rfp
from .oxml import HP, Cell, Grid, build_grid, p_text, replace_span, set_cell_value

# ---------------------------------------------------------------- 빈칸·이름표 판별

_BLANK = re.compile(r"^[\s○◯●◎□_＿·•.\-－:：…~∼/]*$")
SEAL = re.compile(r"\(\s*(?:인|직인|서명|날인|인감|사용인감|서명\s*또는\s*(?:인|날인))\s*\)\s*$")
_UNIT = re.compile(r"(원|천원|백만원|억원|명|년|개월|건|%)\s*$")
DATE_SKEL = re.compile(
    r"^\s*(?P<y>20\d{2}|20)?\s*(?P<ys>년|\.)\s*(?P<m>\d{1,2})?\s*(?P<ms>월|\.)\s*(?P<d>\d{1,2})?\s*(?P<ds>일|\.)?\s*$")
PLACEHOLDER = re.compile(r"○{2,}|◯{2,}|X{3,}|x{3,}|_{3,}|＿{2,}|\{\{[^}]*\}\}")
_LEAD_MARK = re.compile(r"^[\s○◯●□■▪◦\-·※*]+|^(?:\d{1,2}|[가-하])[.)]\s*")
_LABEL_COLON = re.compile(r"(?P<label>[가-힣A-Za-z](?:[가-힣A-Za-z()·]|[ \t]+(?=[가-힣A-Za-z(]))*)\s*[:：]")
_INDEX_TEXT = re.compile(r"^\s*\d{1,3}\s*\.?\s*$")


def norm(label: str) -> str:
    s = _LEAD_MARK.sub("", label.strip())
    return re.sub(r"\s+", "", s).rstrip(":：").lower()


def label_variants(label: str) -> list[str]:
    n = norm(label)
    out = [n, re.sub(r"\(.*?\)", "", n)]
    out += [x for x in re.findall(r"\(([^)]*)\)", n) if x]
    return [x for i, x in enumerate(out) if x and x not in out[:i]]


def is_blank(text: str) -> bool:
    return bool(_BLANK.match(text))


def fillable(text: str) -> tuple[bool, int, int]:
    """칸·구간 글자가 채울 수 있는 빈칸인지와, 바꿀 구간(서명 표시·단위는 남긴다)."""
    t = text.rstrip()
    end = len(t)
    if (m := SEAL.search(t)) and is_blank(t[:m.start()]):
        return True, 0, m.start()
    if DATE_SKEL.match(t):
        return True, 0, end
    if (m := _UNIT.search(t)) and m.start() > 0 and is_blank(t[:m.start()]):
        return True, 0, m.start()
    return is_blank(t), 0, end


def label_like(text: str) -> bool:
    n = norm(text)
    return (1 <= len(n) <= 20 and bool(re.search(r"[가-힣a-z]", n)) and not is_blank(text)
            and not n.endswith("다.") and "\n" not in text.strip() and not PLACEHOLDER.search(text))


def _before_suffix(value: str, suffix: str) -> str:
    """빈칸 뒤에 남는 서명 표시·단위와 값을 잇는다: '홍길동 (인)', '120' + '명'."""
    tail = suffix.strip()
    if not tail:
        return value
    if SEAL.match(tail):
        return f"{value} "
    if value.endswith(tail):
        return value[: -len(tail)]
    return f"{value} "


def fmt_date(d: dt.date, skeleton: str = "") -> str:
    if "년" in skeleton:
        return f"{d.year}년 {d.month}월 {d.day}일"
    return f"{d.year}. {d.month}. {d.day}."


def _parse_date(v: str) -> dt.date | None:
    m = re.match(r"^\s*(\d{4})[-./]\s*(\d{1,2})[-./]\s*(\d{1,2})", v or "")
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


# ---------------------------------------------------------------- 값 사전

@dataclass
class FieldDef:
    key: str
    labels: list[str]
    identifying: bool = False        # 블라인드 서식에는 넣지 않는다
    date: bool = False


FIELDS: list[FieldDef] = [
    FieldDef("identity.name", ["상호", "업체명", "회사명", "법인명", "기업명", "상호명", "제안사", "제안사명", "제안업체",
                               "제안업체명", "입찰자", "입찰자명", "업체", "법인명칭", "상호또는법인명칭", "수급인",
                               "계약상대자"],
             identifying=True),
    FieldDef("identity.ceo", ["대표자", "대표자명", "대표자성명", "대표이사", "대표"], identifying=True),
    FieldDef("company.biz_no", ["사업자등록번호", "사업자번호", "사업자등록번호(법인)"], identifying=True),
    FieldDef("company.corp_no", ["법인등록번호", "법인번호"], identifying=True),
    FieldDef("company.address", ["주소", "소재지", "본사소재지", "사업장소재지", "본점소재지", "사업장주소", "본사주소",
                                 "주소지", "영업소소재지"], identifying=True),
    FieldDef("company.phone", ["전화번호", "전화", "연락처", "대표전화", "대표번호"], identifying=True),
    FieldDef("company.fax", ["팩스", "팩스번호", "fax", "팩시밀리", "전송"], identifying=True),
    FieldDef("company.email", ["이메일", "전자우편", "e-mail", "email", "이메일주소", "전자우편주소"], identifying=True),
    FieldDef("company.homepage", ["홈페이지", "웹사이트"], identifying=True),
    FieldDef("company.established", ["설립일", "설립일자", "설립연월일", "개업일", "개업연월일", "창립일"],
             identifying=True, date=True),
    FieldDef("company.capital", ["자본금", "납입자본금"], identifying=True),
    FieldDef("company.employees", ["종업원수", "임직원수", "직원수", "상시종업원수", "총인원", "종업원"], identifying=True),
    FieldDef("rfp.title", ["사업명", "용역명", "건명", "입찰건명", "계약건명", "과업명", "공고명", "입찰명", "사업명칭"]),
    FieldDef("rfp.bid_no", ["공고번호", "입찰공고번호", "입찰번호"]),
    FieldDef("rfp.agency", ["발주기관", "수요기관", "발주처", "발주기관명"]),
    FieldDef("date", ["제출일", "제출일자", "작성일", "작성일자", "신청일", "신청일자", "일자", "제출연월일", "작성연월일"],
             date=True),
]
_BY_LABEL = {lab: f for f in FIELDS for lab in f.labels}
_ROLE_PREFIX = {"신청인", "제출자", "입찰자", "제안자", "제안사", "신청자", "입찰참가자", "수급인", "계약자", "회사", "본사",
                "업체", "제출인", "신청업체", "제안업체", "서약자", "확약자", "신고인", "제출업체", "서약인"}


@dataclass
class Resolved:
    field: str
    source: str
    value: str
    identifying: bool
    date: bool


@dataclass
class FillContext:
    rfp: Rfp
    kb: CompanyKB | None = None
    names: dict[str, str] = field(default_factory=dict)        # private/people.csv — 서식에만
    overrides: dict[str, str] = field(default_factory=dict)    # private/forms.yaml values — 정규화한 이름표 → 값
    date: dt.date = field(default_factory=dt.date.today)
    max_add_rows: int = 20

    def field_value(self, key: str) -> tuple[str, str]:
        if key == "date":
            return fmt_date(self.date), "date"
        if key.startswith("rfp."):
            ex = getattr(self.rfp.notice, key.split(".", 1)[1], None)
            return (str(ex.value) if ex is not None and ex.value else ""), "rfp"
        if self.kb is None:
            return "", "kb"
        part, attr = key.split(".", 1)
        obj = self.kb.identity if part == "identity" else self.kb.company
        return str(getattr(obj, attr, "") or ""), "kb"

    def resolve(self, label: str) -> Resolved | None:
        """이름표 → 값. 사람이 준 값(private/forms.yaml)이 먼저다. 모르는 이름표면 None.

        "신청인  상    호"처럼 앞에 제출자 역할어가 붙으면 떼고 찾는다. 그 밖의 앞말("하도급 업체")은 떼지 않는다 —
        다른 회사 칸에 우리 회사 값을 넣으면 안 되기 때문이다.
        """
        words = _LEAD_MARK.sub("", label.strip()).split()
        cands = label_variants(label)
        for k in range(1, len(words)):
            if all(w in _ROLE_PREFIX for w in words[:k]):
                cands += label_variants("".join(words[k:]))
        for c in cands:
            if c in self.overrides:
                f = _BY_LABEL.get(c)
                return Resolved(f"user:{c}", "user", self.overrides[c], bool(f and f.identifying), bool(f and f.date))
        for c in cands:
            f = _BY_LABEL.get(c)
            if f is not None:
                value, source = self.field_value(f.key)
                return Resolved(f.key, source, value, f.identifying, f.date)
        return None


# ---------------------------------------------------------------- 목록 표 머리글

COLUMNS: dict[str, dict[str, list[str]]] = {
    "projects": {
        "name": ["사업명", "용역명", "과업명", "건명", "프로젝트명", "계약명", "계약건명", "사업명칭", "수행사업명"],
        "client": ["발주기관", "발주처", "수요기관", "발주자", "발주기관명", "고객사", "발주청"],
        "period": ["사업기간", "수행기간", "계약기간", "기간", "용역기간"],
        "start": ["착수일", "시작일", "착수", "시작", "개시일"],
        "end": ["종료일", "완료일", "준공일", "종료", "완료"],
        "amount": ["계약금액", "사업금액", "금액", "수주금액", "사업비", "계약액", "용역금액", "총사업비"],
        "role": ["역할", "참여형태", "수행형태", "주관여부", "참여구분", "수행역할", "참여방식"],
        "tech": ["적용기술", "주요기술", "사용기술"],
        "evidence": ["증빙", "증빙서류", "증빙자료"],
    },
    "people": {
        "name": ["성명", "이름"],
        "role": ["역할", "담당업무", "담당분야", "수행업무", "투입분야", "담당", "직무"],
        "grade": ["등급", "기술등급", "기술자등급", "sw기술자등급"],
        "years": ["경력", "경력년수", "총경력", "경력연수", "관련경력", "해당분야경력"],
        "skills": ["보유기술", "전문분야", "주요기술", "기술분야"],
        "certs": ["자격증", "보유자격", "자격", "자격사항", "보유자격증", "자격증명"],
    },
    "certifications": {
        "name": ["인증명", "인증서명", "인증종류", "인증내용", "인증제품"],
        "number": ["인증번호", "인증서번호", "등록번호"],
        "valid_until": ["유효기간", "유효일", "만료일", "인증기간", "유효기한"],
    },
}
_STRONG = {"projects": {"name", "client", "amount"}, "people": {"name", "grade", "years", "certs"},
           "certifications": {"name", "number"}}
_INDEX = {"순번", "번호", "연번", "no", "no.", "순위"}
_TOTAL = {"합계", "계", "소계", "총계", "합"}
KIND_KO = {"projects": "유사사업 실적", "people": "참여 인력", "certifications": "인증"}


def match_column(text: str, kind: str) -> str | None:
    n = norm(text)
    base = re.sub(r"\(.*?\)", "", n)
    if n in _INDEX or base in _INDEX:
        return "index"
    vocab = COLUMNS[kind]
    for fld, terms in vocab.items():
        if n in terms or base in terms:
            return fld
    best: tuple[int, str] | None = None
    for fld, terms in vocab.items():
        for t in terms:
            if len(t) >= 3 and t in base and (best is None or len(t) > best[0]):
                best = (len(t), fld)
    return best[1] if best else None


@dataclass
class ListPlan:
    kind: str
    header_rows: list[int]
    columns: dict[int, tuple[str, str]]       # 격자 열 → (필드, 머리글 글자)
    data_rows: list[int]
    total_row: int | None = None              # 빈 행 바로 아래 '합계' 행


def _is_data_row(grid: Grid, r: int) -> bool:
    cells = grid.row_cells(r)
    return bool(cells) and all(fillable(c.text)[0] or _INDEX_TEXT.match(c.text) for c in cells)


def plan_list(grid: Grid, r: int) -> ListPlan | None:
    row = grid.row_cells(r)
    if len(row) < 2 or not all(label_like(c.text) or is_blank(c.text) for c in row):
        return None
    best: tuple[int, str] | None = None
    for kind in COLUMNS:
        hits = {match_column(c.text, kind) for c in row} - {None, "index"}
        if len(hits) >= 2 and hits & _STRONG[kind] and (best is None or len(hits) > best[0]):
            best = (len(hits), kind)
    if best is None:
        return None
    hits_n, kind = best
    header_rows = [r]
    sub = r + 1
    if any(c.colspan > 1 and c.rowspan == 1 for c in row) and sub < grid.rows:
        sub_cells = grid.row_cells(sub)
        if sub_cells and all(label_like(c.text) for c in sub_cells):
            header_rows.append(sub)
    columns: dict[int, tuple[str, str]] = {}
    for col in range(grid.cols):
        top = grid.owner(r, col)
        if top is None:
            continue
        chosen = None
        if len(header_rows) == 2 and top.rowspan == 1:
            low = grid.owner(sub, col)
            if low is not None and (f := match_column(low.text, kind)):
                chosen = (f, f"{top.text} {low.text}")
        if chosen is None and (f := match_column(top.text, kind)):
            chosen = (f, top.text)
        if chosen:
            columns[col] = chosen
    start = header_rows[-1] + 1
    data: list[int] = []
    for rr in range(start, grid.rows):
        if not _is_data_row(grid, rr):
            break
        data.append(rr)
    if hits_n < 3 and len(data) < 2:      # [사업명|발주기관] 아래 빈칸 한 줄은 목록이 아니라 이번 사업 정보 칸이다
        return None
    nxt = (data[-1] if data else header_rows[-1]) + 1
    first = grid.owner(nxt, 0) if nxt < grid.rows else None
    total = nxt if first is not None and first.row == nxt and norm(first.text) in _TOTAL else None
    return ListPlan(kind, header_rows, columns, data, total)


# ---------------------------------------------------------------- 채우기

@dataclass
class _Filler:
    ctx: FillContext
    result: FormResult
    section: object                           # python-hwpx 구역(행 추가에 씀)
    top_paragraphs: list                      # python-hwpx 최상위 문단 객체
    touched: set[int] = field(default_factory=set)       # 이미 보고·채운 문단 id(lxml 요소 id)
    reported_cells: set[int] = field(default_factory=set)

    # 보고 ---------------------------------------------------------------
    def find(self, rule: str, severity: str, message: str) -> None:
        if not any(f.rule == rule and f.message == message for f in self.result.findings):
            self.result.findings.append(CheckFinding(rule=rule, severity=severity, message=message,  # type: ignore[arg-type]
                                                     section_id=self.result.form_no, basis="별지 서식"))

    def record(self, where: str, label: str, field_key: str, source: str, value: str, private: bool = False) -> None:
        shown = "(실명 — private/people.csv)" if private else value
        self.result.fills.append(FormFill(where=where, label=label.strip()[:30], field=field_key,
                                          source=source, value=shown))  # type: ignore[arg-type]

    # 값 결정 --------------------------------------------------------------
    def _value_for(self, label: str, skeleton: str) -> tuple[Resolved | None, str]:
        res = self.ctx.resolve(label)
        if res is None:
            return None, ""
        value = res.value
        if res.date and value:
            d = self.ctx.date if res.field == "date" else _parse_date(value)
            if d is not None:
                value = fmt_date(d, skeleton)
        return res, value

    def _try_fill(self, label: str, where: str, apply: Callable[[str], None], skeleton: str) -> bool:
        res, value = self._value_for(label, skeleton)
        clean = label.strip().rstrip(":：").strip()
        if res is None:
            self.find("FORM-UNFILLED", "major", f"'{clean}' 칸을 채우지 못했습니다(모르는 이름표) — "
                                                "private/forms.yaml의 values에 값을 주거나 직접 쓰세요")
            return False
        if self.result.blind and res.identifying:
            self.find("FORM-BLIND", "info", f"블라인드 서식이라 '{clean}'에 회사 식별 정보를 넣지 않았습니다")
            return False
        if not value:
            hint = {"kb": "KB(company.yaml)에", "rfp": "RFP 분석 결과에"}.get(res.source, "")
            self.find("FORM-UNFILLED", "major", f"'{clean}' 값이 {hint} 없습니다({res.field}) — 채운 뒤 다시 실행하세요")
            return False
        apply(value)
        self.record(where, clean, res.field, res.source, value)
        if res.field == "date":
            self.find("FORM-DATE", "info", f"날짜 칸에 {fmt_date(self.ctx.date)}를 넣었습니다 — 실제 제출일과 맞추세요(--date)")
        return True

    # 1. 이름표 칸 --------------------------------------------------------
    def fill_key_values(self, t_no: int, grid: Grid, skip_rows: set[int]) -> None:
        for cell in sorted(grid.cells, key=lambda c: (c.row, c.col)):
            text = cell.text.strip()
            if (cell.row in skip_rows or cell.nested or not label_like(text)
                    or re.search(r"[:：]", text.rstrip(":： "))):       # "상호 : ○○" 한 칸 안 쌍은 문단 단계에서
                continue
            target: Cell | None = None
            right = grid.right(cell)
            if right is not None and right is not cell and not right.nested and fillable(right.text)[0]:
                target = right
            else:
                below = grid.below(cell)
                if (below is not None and below is not cell and below.row not in skip_rows and not below.nested
                        and fillable(below.text)[0] and (right is None or label_like(right.text))
                        and self.ctx.resolve(text) is not None):
                    target = below
            if target is None or id(target.el) in self.reported_cells:
                continue
            self.reported_cells.add(id(target.el))
            for p in cell.paragraphs:                    # 이름표 칸은 문단 단계에서 다시 보지 않는다
                self.touched.add(id(p))
            first = p_text(target.paragraphs[0]) if target.paragraphs else ""
            ok, a, b = fillable(first)
            if not ok:
                continue

            def _apply(v: str, target=target, a=a, b=b, first=first) -> None:
                set_cell_value(target, a, b, _before_suffix(v, first[b:]))

            self._try_fill(text, f"표{t_no} r{target.row}c{target.col}", _apply, first)
            for p in target.paragraphs:
                self.touched.add(id(p))

    # 2. 목록 표 ----------------------------------------------------------
    def _records(self, kind: str) -> list:
        kb = self.ctx.kb
        if kb is None:
            return []
        if kind == "projects":
            return sorted(kb.projects, key=lambda p: p.end or "", reverse=True)
        if kind == "people":
            return list(kb.people)
        today = self.ctx.date
        valid = [c for c in kb.certifications if not (c.valid_until and c.valid_until < today)]
        if len(valid) < len(kb.certifications):
            self.find("FORM-LIST", "info", f"유효기간이 지난 인증 {len(kb.certifications) - len(valid)}건은 넣지 않았습니다")
        return valid

    def _cell_value(self, kind: str, rec, fld: str, header: str, index: int) -> tuple[str, bool]:
        """(값, 실명 여부)."""
        if fld == "index":
            return str(index), False
        if kind == "projects":
            if fld == "period":
                a, b = (rec.start or "").replace("-", "."), (rec.end or "").replace("-", ".")
                return (f"{a} ~ {b}" if a and b else a or b), False
            if fld in ("start", "end"):
                return (getattr(rec, fld) or "").replace("-", "."), False
            if fld == "amount":
                v = rec.amount_krw
                if v is None:
                    return "", False
                h = norm(header)
                if "백만원" in h:
                    return f"{v / 10**6:,.0f}", False
                if "천원" in h:
                    return f"{v / 10**3:,.0f}", False
                if "억원" in h:
                    return f"{v / 10**8:,.1f}", False
                if h.endswith("(원)") or h.endswith("원)"):
                    return f"{v:,}", False
                return _krw(v), False
            if fld == "tech":
                return ", ".join(rec.tech), False
            return str(getattr(rec, fld, "") or ""), False
        if kind == "people":
            if fld == "name":
                if self.result.blind:
                    return "", False
                return self.ctx.names.get(rec.id, ""), True
            if fld == "years":
                if rec.years is None:
                    return "", False
                return (f"{rec.years:g}" if "(년)" in norm(header) else f"{rec.years:g}년"), False
            if fld in ("skills", "certs"):
                return ", ".join(getattr(rec, fld)), False
            return str(getattr(rec, fld, "") or ""), False
        if fld == "valid_until":
            return (fmt_date(rec.valid_until) if rec.valid_until else ""), False
        return str(getattr(rec, fld, "") or ""), False

    def _grow(self, tbl: etree._Element, grid: Grid, after_row: int, count: int) -> bool:
        from hwpx.oxml.table import HwpxOxmlTable

        top = tbl
        for anc in tbl.iterancestors(f"{HP}p"):
            top = anc
        wrapper = next((p for p in self.top_paragraphs if p.element is top), None)
        if wrapper is None:
            return False
        try:
            HwpxOxmlTable(tbl, wrapper).insert_rows(grid.physical_row(after_row), count, side="below", blank=True)
        except Exception as exc:  # noqa: BLE001 — 병합이 얽힌 표 등
            self.find("FORM-LIST", "major", f"표 행을 늘리지 못했습니다({exc}) — 직접 행을 추가하세요")
            return False
        self.section.mark_dirty()
        return True

    def fill_list(self, t_no: int, tbl: etree._Element, grid: Grid, plan: ListPlan) -> tuple[Grid, set[int]]:
        what = KIND_KO[plan.kind]
        records = self._records(plan.kind)
        unmapped = sorted({norm(c.text) for r in plan.header_rows for c in grid.row_cells(r)
                           if label_like(c.text) and c.col not in plan.columns and norm(c.text) not in ("비고", "구분")})
        if not records:
            self.find("FORM-LIST", "major", f"표{t_no}({what}): KB에 넣을 {what} 자료가 없습니다 — 직접 쓰거나 KB를 채우세요")
            return grid, set(plan.header_rows) | set(plan.data_rows)
        if not plan.data_rows:
            self.find("FORM-LIST", "major",
                      f"표{t_no}({what}): 빈 행이 없어 채우지 못했습니다 — 예시 행을 지우고 다시 실행하세요")
            return grid, set(plan.header_rows)
        need = len(records) - len(plan.data_rows)
        if need > 0:
            add = min(need, self.ctx.max_add_rows)
            if self._grow(tbl, grid, plan.data_rows[-1], add):
                self.result.added_rows += add
                grid = build_grid(tbl)
                plan = plan_list(grid, plan.header_rows[0]) or plan
            if need > self.ctx.max_add_rows:
                self.find("FORM-LIST", "major",
                          f"표{t_no}({what}): {len(records)}건 중 일부만 넣었습니다 — 나머지는 직접 추가하세요")
        covered = set(plan.header_rows) | set(plan.data_rows)
        if plan.total_row is not None:
            covered.add(plan.total_row)
        names_missing = False
        for i, (r, rec) in enumerate(zip(plan.data_rows, records, strict=False), start=1):
            for cell in grid.row_cells(r):
                fld_header = plan.columns.get(cell.col)
                if fld_header is None:
                    continue
                fld, header = fld_header
                value, private = self._cell_value(plan.kind, rec, fld, header, i)
                if not value:
                    if plan.kind == "people" and fld == "name":
                        names_missing = True
                    continue
                ok, a, b = fillable(cell.text)
                if not ok and not (fld == "index" and _INDEX_TEXT.match(cell.text)):
                    continue
                if fld == "index" and _INDEX_TEXT.match(cell.text):
                    continue                      # 이미 번호가 있다
                first = p_text(cell.paragraphs[0]) if cell.paragraphs else ""
                ok1, a, b = fillable(first)
                if not ok1:
                    continue
                set_cell_value(cell, a, b, value)
                for p in cell.paragraphs:
                    self.touched.add(id(p))
                self.record(f"표{t_no} 행{r}", header, f"{plan.kind}[{rec.id}].{fld}",
                            "private" if private else "kb", value, private=private)
        used = min(len(records), len(plan.data_rows))
        if plan.total_row is not None and plan.kind == "projects":
            self._fill_total(t_no, grid, plan, records[:used])
        self.find("FORM-LIST", "info", f"표{t_no}({what}): {used}건을 넣었습니다 — 서식이 정한 기간·건수·인정 기준에 맞는지 "
                                       f"확인하고 고르세요")
        if unmapped:
            self.find("FORM-LIST", "minor", f"표{t_no}({what}): 채우지 못한 열 — {', '.join(unmapped)}")
        if names_missing:
            why = "블라인드 서식이라" if self.result.blind else "private/people.csv에 실명이 없어"
            self.find("FORM-NAMES", "minor", f"표{t_no}: {why} 성명 칸을 비워 두었습니다")
        return grid, covered

    def _fill_total(self, t_no: int, grid: Grid, plan: ListPlan, records: list) -> None:
        amounts = [r.amount_krw for r in records if r.amount_krw is not None]
        for cell in grid.row_cells(plan.total_row):  # type: ignore[arg-type]
            fld = plan.columns.get(cell.col)
            if fld is None or fld[0] != "amount" or not amounts or not cell.paragraphs:
                continue
            first = p_text(cell.paragraphs[0])
            ok, a, b = fillable(first)
            if not ok:
                continue

            class _Sum:                                   # _cell_value가 쓰는 모양만 흉내 낸다
                amount_krw = sum(amounts)

            value, _ = self._cell_value("projects", _Sum, "amount", fld[1], 0)
            set_cell_value(cell, a, b, value)
            self.record(f"표{t_no} 행{plan.total_row}", f"합계 {fld[1]}", "projects[*].amount_krw(합계)", "kb", value)

    def report_unknown_list(self, t_no: int, grid: Grid, r: int) -> bool:
        row = grid.row_cells(r)
        if len(row) < 2 or not all(label_like(c.text) for c in row) or r + 1 >= grid.rows:
            return False
        if not _is_data_row(grid, r + 1):
            return False
        heads = ", ".join(norm(c.text) for c in row[:6])
        self.find("FORM-LIST", "major", f"표{t_no}: 머리글({heads})의 목록 표를 채우지 못했습니다 — 직접 쓰세요")
        return True

    # 3. 문단 -------------------------------------------------------------
    def fill_paragraph(self, p: etree._Element, where: str, allow_date_line: bool) -> None:
        if id(p) in self.touched:
            return
        text = p_text(p)
        if not text.strip():
            return
        if allow_date_line and (m := DATE_SKEL.match(text)) and (m.group("m") is None or m.group("d") is None):
            lead = len(text) - len(text.lstrip())
            value = fmt_date(self.ctx.date, text)
            replace_span(p, lead, len(text.rstrip()), value)
            self.touched.add(id(p))
            self.record(where, "날짜", "date", "date", value)
            self.find("FORM-DATE", "info", f"날짜 칸에 {fmt_date(self.ctx.date)}를 넣었습니다 — 실제 제출일과 맞추세요(--date)")
            return
        matches = list(_LABEL_COLON.finditer(text))
        edits: list[tuple[int, int, str]] = []
        for i, m in enumerate(matches):
            label = m.group("label")
            if len(norm(label)) > 15:
                continue
            stop = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            seg = text[m.end():stop]
            seal = SEAL.search(seg.rstrip())
            body = seg[:seal.start()] if seal else seg
            if not (is_blank(body) or DATE_SKEL.match(body)):
                continue
            gap = " " if seal else ("  " if i + 1 < len(matches) else "")
            span = (m.end(), m.end() + len(body))

            def _apply(v: str, span=span, gap=gap) -> None:
                edits.append((*span, f" {v}{gap}"))

            self._try_fill(label, where, _apply, body)
        for s, e, v in sorted(edits, reverse=True):   # 뒤에서부터 바꿔야 앞 구간 위치가 그대로다
            replace_span(p, s, e, v)
        if edits:
            self.touched.add(id(p))


def _table_number(tables: list[etree._Element], tbl: etree._Element) -> int:
    for i, t in enumerate(tables, start=1):
        if t is tbl:
            return i
    return 0


def fill_region(section, ctx: FillContext, result: FormResult) -> None:
    """구역(서식 하나만 남긴 문서)의 빈칸을 채우고 result에 기록한다."""
    sec_el = section.element
    filler = _Filler(ctx, result, section, list(section.paragraphs))
    tables = list(sec_el.iter(f"{HP}tbl"))
    for tbl in tables:
        t_no = _table_number(tables, tbl)
        grid = build_grid(tbl)
        if len(grid.cells) <= 1:
            continue
        list_rows: set[int] = set()
        r = 0
        while r < grid.rows:
            plan = plan_list(grid, r)
            if plan is not None:
                grid, covered = filler.fill_list(t_no, tbl, grid, plan)
                list_rows |= covered
                r = max(covered) + 1
                continue
            r += 1
        for r in range(grid.rows):
            if r not in list_rows and filler.report_unknown_list(t_no, grid, r):
                list_rows |= {r} | {rr for rr in range(r + 1, grid.rows) if _is_data_row(grid, rr)}
        filler.fill_key_values(t_no, grid, list_rows)
    # 문단: 최상위 문단과 1~2칸짜리 표(쪽 테두리·서명란) 안 문단만 날짜 줄을 채운다
    for i, p in enumerate(sec_el.iter(f"{HP}p")):
        tc = next(p.iterancestors(f"{HP}tc"), None)
        small = True
        if tc is not None:
            tbl = next(tc.iterancestors(f"{HP}tbl"))
            small = len(tbl.findall(f".//{HP}tc")) <= 2
        filler.fill_paragraph(p, f"문단 {i}", allow_date_line=small)
    _final_checks(filler, sec_el)
    section.mark_dirty()


def _final_checks(filler: _Filler, sec_el: etree._Element) -> None:
    texts = [p_text(p) for p in sec_el.iter(f"{HP}p")]
    joined = "\n".join(texts)
    left = [t.strip() for t in texts if PLACEHOLDER.search(t)]
    if left:
        sample = "; ".join(dict.fromkeys(x[:30] for x in left[:5]))
        filler.find("FORM-PLACEHOLDER", "minor", f"자리표시자가 {len(left)}곳 남았습니다 — {sample}")
    if re.search(r"\(\s*(?:인|직인|서명|날인|인감)", joined) or re.search(r"직인|날인|서명", joined):
        filler.find("FORM-SEAL", "info", "서명·날인 칸이 있습니다 — 인쇄해 날인하거나 전자서명하세요(생성기는 넣지 않음)")
    boxes = sum(1 for t in texts if t.count("□") >= 2 or ("□" in t and not t.lstrip().startswith("□")))
    if boxes:
        filler.find("FORM-CHECKBOX", "minor", f"선택 칸(□)이 {boxes}줄 있습니다 — 해당 항목에 표시하세요(■ 또는 V)")
    kb = filler.ctx.kb
    if filler.result.blind and kb is not None:
        hits = [t for t in kb.identity.terms() if t in joined]
        if hits:
            filler.find("FORM-BLIND-LEAK", "blocker", f"블라인드 서식에 회사 식별 표기가 있습니다: {', '.join(hits[:5])}")


__all__ = ["FIELDS", "FillContext", "fill_region", "fmt_date", "fillable", "label_like", "plan_list"]
