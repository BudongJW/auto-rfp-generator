"""공고 일정 추출: 참가 등록·질의·설명회·제안서 제출·입찰 마감·개찰·제안서 평가.

공고문·제안요청서의 '○ 제안서 제출 마감: 2026. 12. 1.(화) 10:00', '질의 기간 : 2026.11.20 ~ 11.26 18:00',
'제안서 평가 | 2026년 12월 4일(금) 예정 | 개별 통보' 같은 줄과 표 행에서 날짜를 읽는다. 날짜 앞(이름표)에서 일정
종류를 고르고, 이름표에 없으면 '제안서는 … 까지 제출'처럼 문장 뒤를 본다. 날짜는 ISO 문자열(YYYY-MM-DD 또는
YYYY-MM-DDTHH:MM)로 남긴다. 남은 날(D-day)은 읽는 날 기준으로 status·점검표에서 셈한다.
"""

from __future__ import annotations

import datetime as dt
import re

from ..schemas.docir import Document
from ..schemas.rfp import ExtractionReport, ScheduleItem, ScheduleKind
from .common import build_grids, iter_lines, loc

_DOW = r"(?:\s*\(\s*[월화수목금토일]\s*\))?"
_TIME = r"(?:(?:\s*,)?\s*(?P<ap{n}>오전|오후)?\s*(?P<h{n}>\d{{1,2}})\s*(?::|시)\s*(?P<mi{n}>\d{{2}})?\s*(?:분)?)?"  # '(금), 11:00'도
_FULL = (r"(?P<y{n}>20\d{{2}})\s*(?:년|[.\-/])\s*(?P<m{n}>\d{{1,2}})\s*(?:월|[.\-/])\s*(?P<d{n}>\d{{1,2}})\s*(?:일|\.)?"
         + _DOW + _TIME)
_PART = r"(?P<m{n}>\d{{1,2}})\s*(?:월|[.\-/])\s*(?P<d{n}>\d{{1,2}})\s*(?:일|\.)?" + _DOW + _TIME
_ONLY_TIME = r"(?P<ap{n}>오전|오후)?\s*(?P<h{n}>\d{{1,2}})\s*(?::|시)\s*(?P<mi{n}>\d{{2}})?\s*(?:분)?"

DATE = re.compile(r"(?<!\d)" + _FULL.format(n=1))
_SEP = r"\s*(?:부터)?\s*[~∼～\-–]\s*"
END = re.compile(_SEP + r"(?:" + _FULL.format(n=2) + r"|" + _PART.format(n=3) + r"|" + _ONLY_TIME.format(n=4) + r")")

# 이름표 → 종류. 위에서부터 고른다('제안서 평가(발표·질의응답)'은 평가, '입찰서 제출 마감'은 입찰 마감)
_KINDS: list[tuple[ScheduleKind, re.Pattern[str]]] = [
    ("설명회", re.compile(r"설명회")),
    ("제안서 평가", re.compile(r"제안서?\s*(?:설명\s*(?:및|·|,)?\s*)?(?:평가|발표)|발표\s*(?:평가|일|일시|일정)|기술\s*(?:능력\s*)?평가"
                           r"|^[\W\d]*평가\s*(?:일시|일정|예정)")),
    ("질의", re.compile(r"질의|질문|이의\s*(?:신청|제기)")),
    ("개찰", re.compile(r"개찰")),
    ("참가 등록", re.compile(r"참가\s*(?:자격\s*)?(?:등록|신청)")),
    ("제안서 제출", re.compile(r"제안서\s*(?:등\s*|및\s*\S{1,10}\s*)?(?:제출|접수|마감)"
                           r"|(?:입찰|참가|제안)[^:：]{0,12}?서류[^:：]{0,16}?(?:제출|접수)\s*(?:마감|기한|일시)"
                           r"|^[\W\d]*(?:서류\s*)?제출\s*(?:마감|기한|일시|기간)")),     # '산출물 제출 기한'은 아니다
    ("입찰 마감", re.compile(r"입찰\s*(?:서\s*)?(?:제출\s*)?마감|투찰|가격\s*(?:입찰|제안)\s*서?\s*(?:제출|마감)"
                         r"|입찰\s*서\s*(?:제출|접수)")),
]
_SENTENCE_SUBMIT = re.compile(r"제안서.{0,40}?까지.{0,30}?제출")
_LEAD = re.compile(r"^(?:[\s○◦ㅇ〇❍\-□•·▪■◎※*\u2460-\u2473]+|(?:\d{1,2}|[가-하])[.)]\s*)+")
# 날짜 앞이 법령·고시 인용이면 일정이 아니다: '고시(제2021-98호, 2021. 12. 30)', '예규 제198호, 2022.01.11.'
_CITE = re.compile(r"고시|예규|훈령|지침|규정|법률|시행령|시행규칙|개정|제\s*\d{2,4}(?:\s*-\s*\d+)?\s*호")
ORDER: list[ScheduleKind] = ["참가 등록", "설명회", "질의", "제안서 제출", "입찰 마감", "개찰", "제안서 평가"]


def _kind(label: str) -> ScheduleKind | None:
    """이름표의 일정 종류. 앞 기호·번호('가.')를 떼고, 괄호 안을 뺀 글자('입찰서(가격) 마감일시')로도 본다."""
    label = _LEAD.sub("", label.replace("\n", " ").strip())
    flat = re.sub(r"\([^)]*\)", " ", label)
    for kind, pat in _KINDS:
        if pat.search(label) or pat.search(flat):
            return kind
    return None


def _iso(y: int, m: int, d: int, ap: str | None, h: str | None, mi: str | None) -> str | None:
    try:
        day = dt.date(y, m, d)
    except ValueError:
        return None
    if h is None:
        return day.isoformat()
    hour = int(h) + (12 if ap == "오후" and int(h) < 12 else 0)
    minute = int(mi or 0)
    if not (0 <= hour <= 24 and 0 <= minute < 60):
        return day.isoformat()
    if hour == 24:                                   # '24:00'은 그날 끝
        hour, minute = 23, 59
    return f"{day.isoformat()}T{hour:02d}:{minute:02d}"


def parse_span(text: str) -> tuple[str | None, str | None, int]:
    """(시작, 끝, 첫 날짜 위치). 날짜가 없으면 (None, None, -1). 끝이 없으면 끝은 None."""
    m = DATE.search(text)
    if not m:
        return None, None, -1
    y = int(m.group("y1"))
    start = _iso(y, int(m.group("m1")), int(m.group("d1")), m.group("ap1"), m.group("h1"), m.group("mi1"))
    end = None
    if (e := END.match(text, m.end())) is not None:
        if e.group("y2"):
            end = _iso(int(e.group("y2")), int(e.group("m2")), int(e.group("d2")), e.group("ap2"), e.group("h2"),
                       e.group("mi2"))
        elif e.group("m3"):
            end = _iso(y, int(e.group("m3")), int(e.group("d3")), e.group("ap3"), e.group("h3"), e.group("mi3"))
        elif e.group("h4") and start:
            end = _iso(y, int(m.group("m1")), int(m.group("d1")), e.group("ap4"), e.group("h4"), e.group("mi4"))
    return start, end, m.start()


def _candidates(doc: Document):
    """(블록, 글자, 이름표 후보) — 본문 줄과 표 행('구분 | 일시 | 장소')."""
    for block, line in iter_lines(doc):                    # 칸 안 '제안서 제출 마감: …' 줄도 본다
        yield block, line, None
    for grid in build_grids(doc):
        for r in range(grid.n_rows):
            cells = grid.row_cells(r)
            for i, cell in enumerate(cells):
                if not DATE.search(cell.text):
                    continue
                # 이름표: 바로 왼쪽 칸('… 개시일시 | 날짜 | … 마감일시 | 날짜'처럼 한 행에 둘일 수 있다),
                # 왼쪽도 날짜면 같은 열의 머리글(첫 행)
                label = cells[i - 1].text if i > 0 and not DATE.search(cells[i - 1].text) else ""
                if not label and r > 0 and cell.cell is not None:
                    head = grid.text(0, cell.cell.col)
                    label = head if not DATE.search(head) else ""
                if label.strip():
                    yield cell, cell.text.replace("\n", " "), label.replace("\n", " ")


def extract_schedule(docs: list[Document], report: ExtractionReport) -> list[ScheduleItem]:
    items: list[ScheduleItem] = []
    for doc in docs:
        for block, text, label in _candidates(doc):
            start, end, at = parse_span(text)
            if start is None:
                continue
            head = label if label is not None else text[:at]
            body = _LEAD.sub("", re.sub(r"[\s~∼～]+$", "", head))
            # 본문 줄은 '이름표: 날짜' 꼴이거나 짧은 이름표만 받는다(긴 문장 속 날짜는 일정이 아니다)
            labelled = label is not None or body.endswith((":", "：")) or len(body) <= 30
            kind = _kind(head) if labelled and len(head) <= 60 and not _CITE.search(head) else None
            if kind is None and label is None and _SENTENCE_SUBMIT.search(text):
                kind = "제안서 제출"
            if kind is None:
                continue
            name = _LEAD.sub("", re.split(r"[:：|]", head)[0]).strip() or kind
            item = ScheduleItem(kind=kind, label=name[:40], start=start, end=end, text=text.strip()[:160],
                                locators=[loc(doc, block, text)])
            same = next((x for x in items if x.kind == kind and x.due == item.due), None)
            if same is not None:
                if len(same.locators) < 3:
                    same.locators.append(item.locators[0])
                continue
            items.append(item)
    items = _merge_open_close(items)
    items.sort(key=lambda x: (x.due or "", ORDER.index(x.kind)))
    kinds = {x.kind for x in items}
    if "제안서 제출" not in kinds and "입찰 마감" not in kinds:
        report.add("NOTICE-DEADLINE", "info", "제안서 제출 마감 일시를 찾지 못했습니다 — 입찰공고문을 함께 넣거나 "
                                              "나라장터 공고에서 확인하세요")
    return items


_OPEN = re.compile(r"개시|시작")


def _merge_open_close(items: list[ScheduleItem]) -> list[ScheduleItem]:
    """'입찰서 제출 개시일시'와 '입찰서 제출 마감일시'처럼 따로 적힌 시작·끝을 한 기간으로 묶는다."""
    out: list[ScheduleItem] = []
    for it in items:
        if _OPEN.search(it.label) and it.end is None:
            close = next((x for x in items if x.kind == it.kind and not _OPEN.search(x.label) and x.end is None
                          and (x.start or "") > (it.start or "")), None)
            if close is not None:
                close.end, close.start = close.start, it.start
                close.locators += it.locators[:1]
                continue
        out.append(it)
    return out


def deadline(items: list[ScheduleItem]) -> ScheduleItem | None:
    """제출 마감: 제안서 제출이 있으면 그것, 없으면 입찰 마감."""
    for kind in ("제안서 제출", "입찰 마감"):
        found = [x for x in items if x.kind == kind and x.due]
        if found:
            return max(found, key=lambda x: x.due or "")
    return None


def when(iso: str | None) -> str:
    """'2026-12-01T10:00' → '2026-12-01(화) 10:00'."""
    if not iso:
        return "?"
    day = dt.date.fromisoformat(iso[:10])
    dow = "월화수목금토일"[day.weekday()]
    return f"{day.isoformat()}({dow})" + (f" {iso[11:16]}" if len(iso) > 10 else "")


def span_text(item: ScheduleItem) -> str:
    if item.end and item.start and item.end != item.start:
        same_day = item.end[:10] == item.start[:10]
        return f"{when(item.start)} ~ {item.end[11:16] if same_day and len(item.end) > 10 else when(item.end)}"
    return when(item.due)


def d_day(iso: str | None, today: dt.date) -> str:
    """남은 날: 'D-3', 'D-day', '2일 지남'."""
    if not iso:
        return ""
    n = (dt.date.fromisoformat(iso[:10]) - today).days
    if n == 0:
        return "D-day"
    return f"D-{n}" if n > 0 else f"{-n}일 지남"


__all__ = ["ORDER", "d_day", "deadline", "extract_schedule", "parse_span", "span_text", "when"]
