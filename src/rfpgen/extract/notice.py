"""공고 기본정보 추출: 사업명, 예산, 기간, 발주기관, 공고번호, 계약방법."""

from __future__ import annotations

import re

from ..schemas.common import Extracted
from ..schemas.docir import Document
from ..schemas.rfp import ExtractionReport, Notice
from .common import build_grids, iter_lines, loc, norm, parse_krw

_LABELS = {
    "title": {"사업명", "용역명", "과업명", "사업명칭", "건명", "공고명"},
    "budget": {"사업예산", "사업금액", "추정가격", "배정예산", "소요예산", "사업비", "예산", "추정금액", "기초금액"},
    "period": {"사업기간", "용역기간", "계약기간", "수행기간", "과업기간"},
    "agency": {"발주기관", "수요기관", "발주처", "주관기관", "공고기관"},
}
# 값 칸에 머리글이 온 표('발주기관 | 비고')에서 머리글을 값으로 읽지 않는다
HEADER_WORDS = {"비고", "구분", "내용", "항목", "세부내용", "주요내용", "기타", "해당없음", "-"}
_LINE = re.compile(r"^[○◦ㅇ\-□•·▪■◎*]?\s*(?:\d+\.\s*)?(사업명|용역명|과업명|사업\s*예산|사업\s*금액|추정\s*가격|배정\s*예산|소요\s*예산|사업비|사업\s*기간|용역\s*기간|계약\s*기간|수행\s*기간|발주\s*기관|수요\s*기관)\s*[:：]?\s*(.+)$")
_BID_NO = re.compile(r"\b(R\d{2}[A-Z]{2}\d{8})(?:-?(\d{2,3}))?\b|\b(20\d{9})\s*-\s*(\d{2})\b")
_METHODS = [
    ("경쟁적대화", re.compile(r"경쟁적\s*대화")),
    ("규격가격동시", re.compile(r"규격\s*[·ㆍ,및]?\s*가격\s*(?:분리\s*)?동시|2단계\s*경쟁")),
    ("디지털서비스카탈로그", re.compile(r"디지털\s*서비스\s*(?:전문)?\s*계약|카탈로그\s*계약")),
    ("협상계약", re.compile(r"협상에\s*의한\s*계약|협상에\s*의한\s*계약체결")),
]


def _field_of(label: str) -> str | None:
    key = norm(label).strip(":：")
    for f, labels in _LABELS.items():
        if key in labels:
            return f
    return None


def extract_notice(docs: list[Document], report: ExtractionReport) -> Notice:
    notice = Notice()
    found: dict[str, Extracted] = {}

    def put(field: str, value: str, doc: Document, block, quote: str) -> None:
        value = value.strip(" :：")
        if not value or field in found or _field_of(value) is not None or norm(value) in HEADER_WORDS:
            return  # 값 칸에 다른 항목명이나 머리글이 온 머리행은 건너뛴다
        if field == "period" and not re.search(r"\d", value):
            return  # 숫자 없는 기간(도형 글자로 숫자가 빠진 경우)은 쓸모가 없다
        if field == "title" and len(norm(value)) < 4:
            return
        if field == "budget":
            amount = parse_krw(value)
            if amount is None:
                return
            found[field] = Extracted(value=amount, locators=[loc(doc, block, quote)])
        else:
            found[field] = Extracted(value=value[:120], locators=[loc(doc, block, quote)])

    for doc in docs:
        # 표의 '사업명 | 값' 쌍
        for grid in build_grids(doc):
            for r in range(grid.n_rows):
                row = grid.row_cells(r)
                for i, cell in enumerate(row[:-1]):
                    f = _field_of(cell.text)
                    if f:
                        nxt = row[i + 1]
                        put(f, nxt.text.replace("\n", " "), doc, nxt, nxt.text)
        # 본문의 '○ 사업명 : 값'
        for block, line in iter_lines(doc, include_cells=False):
            m = _LINE.match(line)
            if m:
                f = _field_of(m.group(1))
                if f:
                    put(f, m.group(2), doc, block, line)
            if "bid_no" not in found and "공고" in line and (bm := _BID_NO.search(line)):
                found["bid_no"] = Extracted(value=bm.group(0), locators=[loc(doc, block, bm.group(0))])

    notice.title = found.get("title")
    notice.budget_krw = found.get("budget")
    notice.period = found.get("period")
    notice.agency = found.get("agency")
    notice.bid_no = found.get("bid_no")

    for doc in docs:
        for block, line in iter_lines(doc):
            for method, pat in _METHODS:
                if (m := pat.search(line)):
                    notice.contract_method = Extracted(value=method, locators=[loc(doc, block, m.group(0))])  # type: ignore[arg-type]
                    break
            if notice.contract_method.value != "미확인":
                break
        if notice.contract_method.value != "미확인":
            break

    if notice.title is None:
        report.add("NOTICE-TITLE", "warning", "사업명을 찾지 못했습니다")
    if notice.budget_krw is None:
        report.add("NOTICE-BUDGET", "info", "사업예산을 찾지 못했습니다(금액이 이미지이거나 공고문에만 있을 수 있음)")
    if notice.contract_method.value == "미확인":
        report.add("NOTICE-METHOD", "warning", "계약방법을 판별하지 못했습니다 — 협상계약 프로필을 기본으로 씁니다")
    return notice
