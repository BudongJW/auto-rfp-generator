"""KB 토큰 치환과 자리표시자·숫자 근거 판정(원칙 P2: 숫자는 코드가)."""

from __future__ import annotations

import re

from ..schemas.draft import SectionDraft
from ..schemas.kb import CompanyKB

TOKEN = re.compile(r"\{\{\s*(fact|kb)\s*:\s*([A-Za-z0-9_\-]+(?:\.[A-Za-z_]+)?)\s*\}\}")
PLACEHOLDER = re.compile(r"\[(?:확인\s*필요|작성\s*필요|검토\s*필요)[^\]]*\]")
_UNITS = ["%", "퍼센트", "건", "명", "개월", "개", "회", "억", "만", "천", "원", "년", "일", "시간", "초", "분", "배",
          "TPS", "tps", "ms", "GB", "TB", "MB", "대", "식", "종", "점"]
# 단위는 긴 것부터 맞춘다('2개월'을 '2개'로 읽지 않게)
# 숫자 중간('SFR-001'의 '01')에서 시작하지 않고, 줄을 넘어 단위를 붙이지 않는다('SFR-001\n개선' → '01 개' 아님)
NUMBER = re.compile(r"(?<![\dA-Za-z가-힣\-:.,])(\d[\d,]*(?:\.\d+)?)[ \t]*("
                    + "|".join(re.escape(u) for u in sorted(_UNITS, key=len, reverse=True)) + ")")


def substitute(text: str, kb: CompanyKB, unresolved: list[str]) -> str:
    def repl(m: re.Match[str]) -> str:
        key = m.group(2)
        value = kb.resolve(key)
        if value is None:
            unresolved.append(key)
            return f"[확인 필요: KB에 {key} 없음]"
        return value
    return TOKEN.sub(repl, text or "")


def apply_tokens(draft: SectionDraft, kb: CompanyKB) -> None:
    """초안의 모든 글자 칸에서 토큰을 값으로 바꾸고, 남은 자리표시자를 모은다."""
    unresolved: list[str] = []
    draft.head_message = substitute(draft.head_message, kb, unresolved)
    for b in draft.blocks:
        b.text = substitute(b.text, kb, unresolved)
        b.items = [substitute(x, kb, unresolved) for x in b.items]
        if b.table:
            b.table.header = [substitute(x, kb, unresolved) for x in b.table.header]
            b.table.rows = [[substitute(x, kb, unresolved) for x in row] for row in b.table.rows]
        b.fact_refs = sorted(set(b.fact_refs))
    for r in draft.responses:
        r.response = substitute(r.response, kb, unresolved)
    draft.unresolved_tokens = sorted(set(draft.unresolved_tokens + unresolved))
    draft.placeholders = sorted(set(PLACEHOLDER.findall(draft.all_text())))
    draft.est_chars = len(re.sub(r"\s+", "", draft.all_text(figures=False)))  # 도식 면적은 점검에서 따로 센다


def numbers(text: str) -> list[str]:
    """단위가 붙은 숫자 표현(실적·인원·성능 등 근거가 필요한 수치)."""
    return [m.group(0).strip() for m in NUMBER.finditer(text or "")]
