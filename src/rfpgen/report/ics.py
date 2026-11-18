"""공고 일정을 캘린더 파일(iCalendar, RFC 5545)로 내보낸다: out/일정.ics.

한국 시각(UTC+9, 일광절약 없음)을 UTC로 바꿔 적어 VTIMEZONE 없이도 어느 캘린더에서나 같은 시각이 된다.
날짜만 있는 일정은 종일 일정으로 둔다. 질의·제출·평가 일정에는 하루 전 알림을 단다.
"""

from __future__ import annotations

import datetime as dt
import hashlib

from ..extract.schedule import span_text
from ..schemas.rfp import Rfp, ScheduleItem

KST = dt.timezone(dt.timedelta(hours=9))
_ALARM = {"질의", "제안서 제출", "입찰 마감", "제안서 평가"}
_TITLE = {"질의": "질의 마감", "제안서 제출": "제안서 제출 마감", "입찰 마감": "입찰 마감", "참가 등록": "참가 등록 마감"}


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> list[str]:
    """한 줄 75바이트 안으로 접는다(이어지는 줄은 공백 하나로 시작). 한글이 바이트 중간에서 끊기지 않게."""
    out: list[str] = []
    cur = ""
    for ch in line:
        limit = 75 if not out else 74
        if len((cur + ch).encode("utf-8")) > limit:
            out.append(cur)
            cur = ch
        else:
            cur += ch
    out.append(cur)
    return [out[0], *(" " + x for x in out[1:])]


def _event(item: ScheduleItem, title: str, stamp: str) -> list[str]:
    due = item.due or ""
    uid = hashlib.sha1(f"{title}|{item.kind}|{due}".encode()).hexdigest()[:20]
    lines = ["BEGIN:VEVENT", f"UID:{uid}@rfpgen", f"DTSTAMP:{stamp}",
             f"SUMMARY:{_esc(f'[{_TITLE.get(item.kind, item.kind)}] {title}')}"]
    if len(due) > 10:
        at = dt.datetime.fromisoformat(due).replace(tzinfo=KST).astimezone(dt.timezone.utc)
        lines += [f"DTSTART:{at:%Y%m%dT%H%M%SZ}", f"DTEND:{at + dt.timedelta(minutes=30):%Y%m%dT%H%M%SZ}"]
    else:
        day = dt.date.fromisoformat(due)
        lines += [f"DTSTART;VALUE=DATE:{day:%Y%m%d}", f"DTEND;VALUE=DATE:{day + dt.timedelta(days=1):%Y%m%d}"]
    where = item.locators[0].block_id if item.locators else ""
    desc = f"{item.label}: {span_text(item)}\n원문: {item.text}" + (f"\n위치: {where}" if where else "")
    desc += "\n정정공고로 바뀔 수 있습니다 — 나라장터 공고를 기준으로 하세요."
    lines.append(f"DESCRIPTION:{_esc(desc)}")
    if item.kind in _ALARM:
        lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_esc(_TITLE.get(item.kind, item.kind))} 하루 전",
                  "TRIGGER:-P1D", "END:VALARM"]
    lines.append("END:VEVENT")
    return lines


def schedule_ics(rfp: Rfp, *, now: dt.datetime | None = None) -> str | None:
    """일정이 없으면 None."""
    items = [x for x in rfp.notice.schedule if x.due]
    if not items:
        return None
    title = rfp.notice.title.value if rfp.notice.title else "제안서"
    stamp = f"{(now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc):%Y%m%dT%H%M%SZ}"
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//rfpgen//proposal schedule//KO", "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH", f"X-WR-CALNAME:{_esc(title)}"]
    for it in items:
        lines += _event(it, title, stamp)
    lines.append("END:VCALENDAR")
    return "\r\n".join(x for line in lines for x in _fold(line)) + "\r\n"


__all__ = ["schedule_ics"]
