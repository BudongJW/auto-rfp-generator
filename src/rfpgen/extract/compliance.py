"""입찰무효·평가(협상) 제외·감점·불이익 사유와 입찰참가자격 추출(결정적).

OpenBidKit_Yibiao(AGPL-3.0, 77a38f0)의 无效投标/废标项 추출과 '원문 명시 vs 경험상 권고' 분리를
한국 조달 용어로 재구현했다(docs/analysis/chinese-bid-generators.md 5.3절). 원문에 적힌 사유는
origin=stated, 프로필의 권고 목록은 origin=suggested로 두고 G1에서 사람이 채택한다.
"""

from __future__ import annotations

import re

from ..profile import Profile
from ..schemas.common import Extracted
from ..schemas.docir import Document
from ..schemas.rfp import ComplianceItem, ExtractionReport, Rfp
from .common import iter_lines, loc, norm

_KIND_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("입찰무효", re.compile(r"입찰\s*(?:을|은|이)?\s*무효|무효\s*(?:로\s*)?(?:처리|입찰|로\s*한다|로\s*함|임)|무효로\s*(?:한다|함|처리)")),
    ("평가제외", re.compile(r"(?:평가|협상)\s*(?:대상|대상자)?\s*(?:에서|으로부터)?\s*제외|실격|탈락\s*(?:처리|시킴|됨)|부적격\s*(?:처리|으로|자로)|협상\s*적격자?\s*(?:에서|로)?\s*(?:선정\s*)?(?:하지|제외)")),
    ("감점", re.compile(r"감점")),
    ("불이익", re.compile(r"불이익")),
]
_RELATED: list[tuple[str, re.Pattern[str]]] = [
    ("BLD", re.compile(r"블라인드|업체\s*명|회사\s*명|로고|\bCI\b|식별")),
    ("PAGE", re.compile(r"분량|쪽\s*수|페이지|매수|초과\s*(?:한|하는)?\s*(?:쪽|페이지)")),
    ("FMT", re.compile(r"글자|글씨|폰트|서체|크기|용지|규격")),
    ("FACT", re.compile(r"허위|사실과\s*다른|위조|변조")),
    ("LANG", re.compile(r"비방|비교\s*광고")),
    ("SUB", re.compile(r"제출|서류|누락|기한|마감|용량|파일|서약|확약|미제출")),
]
_ELIG_TITLE = re.compile(r"(?:입찰\s*)?참가\s*자격|입찰\s*자격|참여\s*자격|자격\s*요건")


def _related(text: str) -> str | None:
    for code, pat in _RELATED:
        if pat.search(text):
            return code
    return None


def extract_compliance(docs: list[Document], profile: Profile, report: ExtractionReport,
                       skip_tables: set[str] | None = None) -> list[ComplianceItem]:
    skip = skip_tables or set()
    items: list[ComplianceItem] = []
    seen: set[str] = set()
    for doc in docs:
        for block, line in iter_lines(doc):
            if block.kind == "cell" and block.parent in skip:
                continue
            if len(norm(line)) < 12:
                continue  # '감점' 같은 표 머리글·단어 하나짜리 칸은 사유 문장이 아니다
            for kind, pat in _KIND_PATTERNS:
                m = pat.search(line)
                if not m:
                    continue
                key = norm(line)[:80]
                if key in seen:
                    break
                seen.add(key)
                text = line.strip(" -–•·○◦□ㅇ※*")
                items.append(ComplianceItem(
                    kind=kind,  # type: ignore[arg-type]
                    text=text[:240],
                    related_check=_related(text),
                    origin="stated",
                    locators=[loc(doc, block, line)],
                ))
                break
    for spec in profile.value("compliance.suggested") or []:
        items.append(ComplianceItem(
            kind=spec["kind"], text=spec["text"], related_check=spec.get("related_check"),
            origin="suggested", method="profile", note="RFP 원문에 근거가 없는 권고 — G1에서 채택 여부를 정하세요",
        ))
    stated = [i for i in items if i.origin == "stated"]
    report.stats["compliance_stated"] = len(stated)
    if not stated:
        report.add("COMPLIANCE-NONE", "warning", "입찰무효·평가제외·감점 사유를 원문에서 찾지 못했습니다 — 공고문을 함께 넣었는지 확인하세요")
    return items


def extract_eligibility(docs: list[Document], report: ExtractionReport) -> list[Extracted[str]]:
    """'입찰참가자격' 제목 아래의 조건 줄을 모은다(다음 제목 전까지, 최대 15줄)."""
    out: list[Extracted[str]] = []
    for doc in docs:
        blocks = doc.blocks
        for i, b in enumerate(blocks):
            if b.kind not in ("heading", "para") or len(b.text) > 40 or not _ELIG_TITLE.search(b.text):
                continue
            n = 0
            for x in blocks[i + 1:]:
                if x.kind == "heading":
                    break
                if x.kind != "para" or x.parent is not None:
                    continue
                for line in x.text.split("\n"):
                    line = line.strip()
                    if len(line) >= 8:
                        out.append(Extracted[str](value=line.strip(" -–•·○◦□ㅇ*"), locators=[loc(doc, x, line)]))
                        n += 1
                if n >= 15:
                    break
            if out:
                report.stats["eligibility_lines"] = len(out)
                return out
    report.add("ELIGIBILITY-NONE", "info", "입찰참가자격 조항을 찾지 못했습니다(공고문에 있는 경우가 많습니다)")
    return out


def link_compliance_severity(rfp: Rfp) -> None:
    """작성지침 위반이 '제외·무효'로 규정되면 그 사실을 작성지침 값의 메모로 남긴다(점검 심각도 근거)."""
    g = rfp.guideline
    targets = {"PAGE": g.main_page_limit, "FMT": g.min_font_pt, "BLD": g.blind, "SUB": g.total_size_limit_mb}
    for item in rfp.compliance:
        if item.origin != "stated" or item.kind not in ("입찰무효", "평가제외") or item.related_check not in targets:
            continue
        ex = targets[item.related_check]
        if ex is not None:
            note = f"위반 시 {item.kind}: {item.text[:80]}"
            if note in (ex.note or ""):
                continue
            ex.note = f"{ex.note}; {note}" if ex.note else note
