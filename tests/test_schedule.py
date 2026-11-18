"""공고 일정 추출과 남은 날(D-day) 안내."""

from __future__ import annotations

import datetime as dt

from rfpgen.extract.schedule import (
    d_day,
    deadline,
    extract_schedule,
    parse_span,
    span_text,
    when,
)
from rfpgen.pipeline import analyze
from rfpgen.profile import load_profile
from rfpgen.sample import build_sample_rfp
from rfpgen.schemas.docir import Block, Document
from rfpgen.schemas.rfp import ExtractionReport

DAY = dt.date(2026, 11, 18)          # 수요일


def _doc(lines: list[str]) -> Document:
    return Document(doc_id="d1", filename="공고.hwpx", format="hwpx", role="입찰공고", sha256="0" * 64,
                    blocks=[Block(id=f"d1:b{i}", kind="para", text=t) for i, t in enumerate(lines)])


def test_parse_span_formats():
    assert parse_span("2026. 11. 20.(금) ~ 2026. 11. 26.(목) 18:00")[:2] == ("2026-11-20", "2026-11-26T18:00")
    assert parse_span("2026/12/01 10:00")[:2] == ("2026-12-01T10:00", None)
    assert parse_span("2026년 12월 1일(화) 오후 2시")[:2] == ("2026-12-01T14:00", None)
    assert parse_span("2026. 11. 20. 09:00 ~ 11. 26. 18:00")[:2] == ("2026-11-20T09:00", "2026-11-26T18:00")
    assert parse_span("2026-12-01 10:00 ~ 18:00")[:2] == ("2026-12-01T10:00", "2026-12-01T18:00")
    assert parse_span("2025.     .     .") == (None, None, -1)                  # 서식의 빈 날짜 칸
    assert parse_span("2026. 2. 30.")[0] is None                                 # 없는 날짜


def test_extract_schedule_lines():
    rep = ExtractionReport()
    items = extract_schedule([_doc([
        "가. 입찰서 제출 개시일시: 2026/11/23 09:00",
        "나. 입찰서 제출 마감일시: 2026/11/30 10:00",
        "다. 개찰일시: 2026/11/30 11:00",
        "○ 제안서 제출기간: 2026. 11. 23.(월) 09:00 ~ 2026. 11. 30.(월) 10:00",
        "○ 질의 및 회신: 공고일 ~ 2026. 11. 24.(화) 18:00까지",
        "○ 제안서 평가 일시: 추후 통보",
        "제안서는 2026. 11. 30.(월) 10:00까지 국가종합전자조달시스템으로 제출하여야 한다.",
        "○ 제안요청 설명회: 2026. 11. 20.(금) 14:00, 본청 대회의실",
        "※ 산출물 제출 기한: 2027. 3. 1.",                                          # 사업 수행 중 일정 — 아니다
        "○ 2024. 3. 1. 개정된 소프트웨어 진흥법을 따른다",
        "○ 중간 평가 일정: 2027. 4. 1.",
    ])], rep)
    got = [(x.kind, x.label, x.start, x.end) for x in items]
    assert got == [
        ("설명회", "제안요청 설명회", "2026-11-20T14:00", None),
        ("질의", "질의 및 회신", "2026-11-24T18:00", None),
        ("제안서 제출", "제안서 제출기간", "2026-11-23T09:00", "2026-11-30T10:00"),
        ("입찰 마감", "입찰서 제출 마감일시", "2026-11-23T09:00", "2026-11-30T10:00"),     # 개시·마감을 한 기간으로
        ("개찰", "개찰일시", "2026-11-30T11:00", None),
    ]
    assert len(items[2].locators) == 2                         # '제안서는 … 까지 제출' 문장도 같은 마감
    assert deadline(items).kind == "제안서 제출"
    assert not rep.findings


def test_missing_deadline_is_reported():
    rep = ExtractionReport()
    assert extract_schedule([_doc(["○ 사업기간: 계약일로부터 8개월"])], rep) == []
    assert [f.code for f in rep.findings] == ["NOTICE-DEADLINE"]


def test_d_day_and_when():
    assert when("2026-11-30T10:00") == "2026-11-30(월) 10:00" and when("2026-11-30") == "2026-11-30(월)"
    assert d_day("2026-11-30T10:00", DAY) == "D-12" and d_day("2026-11-18", DAY) == "D-day"
    assert d_day("2026-11-16", DAY) == "2일 지남"


def test_sample_schedule_flows_to_outputs(tmp_path):
    src = build_sample_rfp(tmp_path / "예제.hwpx", today=DAY)
    project = tmp_path / "proj"
    analyze([src], project, load_profile())
    from rfpgen.forms import _latest_rfp

    rfp = _latest_rfp(project)
    assert [x.kind for x in rfp.notice.schedule] == ["설명회", "질의", "제안서 제출", "제안서 평가"]
    assert rfp.notice.schedule[0].start == "2026-11-23T14:00"            # 토요일(21일)이면 월요일로 옮긴다
    dl = deadline(rfp.notice.schedule)
    assert dl is not None and dl.due == "2026-11-30T10:00"                 # 18일 + 12일, 주말 아님
    analysis = (project / "out" / "analysis.md").read_text(encoding="utf-8")
    assert "## 일정" in analysis and "제안서 제출 마감" in analysis
    assert "BEGIN:VEVENT" in (project / "out" / "일정.ics").read_text(encoding="utf-8")
    import openpyxl

    sheet = openpyxl.load_workbook(project / "out" / "analysis.xlsx")["일정"]
    assert [c.value for c in sheet[1]][:2] == ["종류", "원문 이름표"] and sheet.max_row == 5
    questions = (project / "out" / "questions.md").read_text(encoding="utf-8")
    assert "> 질의 기간: 2026-11-19(목) 09:00 ~ 2026-11-24(화) 18:00" in questions
    assert span_text(dl) == "2026-11-30(월) 10:00"

    from rfpgen.workflow import project_status

    stages, todo = project_status(project, today=DAY)
    sched = next(s for s in stages if s.key == "schedule")
    assert sched.done and sched.detail == "설명회 11-23 D-5 · 질의 마감 11-24 D-6 · 제출 마감 11-30 D-12"
    assert any(t.startswith("질의 마감 D-6") and "questions.md" in t for t in todo)
    assert "rfpgen kb init" in todo[0]                                     # 급하지 않으면 원래 첫 할 일
    _, late = project_status(project, today=dt.date(2026, 11, 28))
    assert late[0].startswith("제출 마감 D-2") and not any(t.startswith("질의 마감") for t in late)
    after, _ = project_status(project, today=dt.date(2026, 12, 10))
    assert next(s for s in after if s.key == "schedule").detail == "제출 마감 11-30 10일 지남"


def test_checklist_shows_deadline():
    from rfpgen.package import _checklist
    from rfpgen.schemas.draft import CheckReport
    from rfpgen.schemas.rfp import ScheduleItem

    items = [ScheduleItem(kind="제안서 제출", label="제안서 제출 마감", start="2026-11-30T10:00"),
             ScheduleItem(kind="제안서 평가", label="제안서 평가(발표)", start="2026-12-03")]
    text = _checklist("사업", [], CheckReport(run_id="r"), 300, True, schedule=items, today=DAY)
    assert "- 제출 마감: 2026-11-30(월) 10:00 — 오늘(2026-11-18) 기준 D-12" in text
    assert "- 제안서 평가(발표): 2026-12-03(목)" in text and "마감(2026-11-30(월) 10:00) 전에" in text
    assert "찾지 못함" in _checklist("사업", [], CheckReport(run_id="r"), 300, True, schedule=[], today=DAY)


def test_diff_flags_moved_deadline():
    from rfpgen.diff import diff_rfp
    from rfpgen.schemas.rfp import Rfp, ScheduleItem

    old, new = Rfp(), Rfp()
    old.notice.schedule = [ScheduleItem(kind="제안서 제출", label="제안서 제출 마감", start="2026-11-30T10:00"),
                           ScheduleItem(kind="설명회", label="설명회", start="2026-11-20T14:00")]
    new.notice.schedule = [ScheduleItem(kind="제안서 제출", label="제안서 제출 마감", start="2026-12-07T10:00"),
                           ScheduleItem(kind="설명회", label="설명회", start="2026-11-20T14:00")]
    changes = diff_rfp(old, new, 1, 2).changes
    assert [(c.key, c.old, c.new, c.high_risk) for c in changes] == [
        ("schedule.제안서 제출", "2026-11-30(월) 10:00", "2026-12-07(월) 10:00", True)]


def test_schedule_ics():
    from rfpgen.report.ics import schedule_ics
    from rfpgen.schemas.common import Extracted
    from rfpgen.schemas.rfp import Rfp, ScheduleItem

    rfp = Rfp()
    rfp.notice.title = Extracted(value="2026년 통합민원시스템 고도화 사업 — 아주 긴 사업명으로 접기를 확인합니다")
    assert schedule_ics(rfp) is None
    rfp.notice.schedule = [
        ScheduleItem(kind="질의", label="질의 기간", start="2026-11-19T09:00", end="2026-11-24T18:00", text="질의, 회신; 기간"),
        ScheduleItem(kind="제안서 제출", label="제안서 제출 마감", start="2026-11-30T10:00"),
        ScheduleItem(kind="제안서 평가", label="제안서 평가(발표)", start="2026-12-03"),
    ]
    cal = schedule_ics(rfp, now=dt.datetime(2026, 11, 18, tzinfo=dt.timezone.utc))
    assert cal.startswith("BEGIN:VCALENDAR\r\n") and cal.endswith("END:VCALENDAR\r\n")
    lines = cal.split("\r\n")[:-1]
    assert all(len(x.encode("utf-8")) <= 75 for x in lines)                    # RFC 5545 줄 접기
    unfolded = cal.replace("\r\n ", "")
    assert unfolded.count("BEGIN:VEVENT") == 3 and unfolded.count("BEGIN:VALARM") == 3
    assert "DTSTART:20261124T090000Z" in unfolded                                # 질의 마감 18:00 KST
    assert "DTSTART:20261130T010000Z" in unfolded                                # 제출 마감 10:00 KST
    assert "DTSTART;VALUE=DATE:20261203" in unfolded and "DTEND;VALUE=DATE:20261204" in unfolded
    assert r"질의\, 회신\; 기간" in unfolded                                       # 쉼표·쌍반점 이스케이프


def test_suggest_due():
    from rfpgen.draft.write import suggest_due
    from rfpgen.schemas.draft import DataRequest
    from rfpgen.schemas.rfp import ScheduleItem

    sched = [ScheduleItem(kind="질의", label="질의 기간", start="2026-11-19T09:00", end="2026-11-24T18:00"),
             ScheduleItem(kind="제안서 제출", label="제안서 제출 마감", start="2026-11-30T10:00")]
    reqs = [DataRequest(section_id="s", section_title="t", need="실적 증빙", category="실적"),
            DataRequest(section_id="s", section_title="t", need="연계 규격", category="발주기관 확인"),
            DataRequest(section_id="s", section_title="t", need="이미 정함", category="인력", due="2026-11-20")]
    suggest_due(reqs, sched, today=DAY)
    assert [r.due for r in reqs] == ["2026-11-23", "2026-11-24", "2026-11-20"]
    late = [DataRequest(section_id="s", section_title="t", need="x", category="실적"),
            DataRequest(section_id="s", section_title="t", need="y", category="발주기관 확인")]
    suggest_due(late, sched, today=dt.date(2026, 11, 26))                       # 질의 마감이 지났다
    assert [r.due for r in late] == ["2026-11-26", ""]
    weekend = [DataRequest(section_id="s", section_title="t", need="x", category="실적")]
    suggest_due(weekend, [ScheduleItem(kind="제안서 제출", label="마감", start="2026-12-07T10:00")], today=DAY)
    assert weekend[0].due == "2026-11-30"                                        # 7일 전 월요일 그대로
    sun = [DataRequest(section_id="s", section_title="t", need="x", category="실적")]
    suggest_due(sun, [ScheduleItem(kind="제안서 제출", label="마감", start="2026-12-06")], today=DAY)
    assert sun[0].due == "2026-11-27"                                            # 11-29(일) → 앞 금요일
