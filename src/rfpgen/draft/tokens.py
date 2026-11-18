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


def placeholder_topic(placeholder: str) -> str:
    """'[확인 필요: 첨부 용량 기준(SFR-001)]' → '첨부 용량 기준'(괄호 꼬리 뺌)."""
    inner = placeholder.strip("[]").split(":", 1)[-1].strip()
    return re.sub(r"\s*\([^)]*\)\s*$", "", inner).strip()


def similar_topic(a: str, b: str, threshold: float = 0.5) -> bool:
    """확인할 내용이 같은지: 한쪽이 다른 쪽을 품거나 문자 2-gram 유사도가 기준 이상."""
    from ..plan.outline import similarity

    a, b = placeholder_topic(f"[{a}]"), placeholder_topic(f"[{b}]")
    return bool(a and b) and similarity(a, b) >= threshold


_Q_STOP = {"및", "등", "여부", "자료", "목록", "정의", "관련", "대한", "위한"}
_Q_PARTICLE = re.compile(r"(의|과|와|을|를|은|는|이|가|에|로|으로)$")


def _question_grams(text: str) -> set[str]:
    text = re.sub(r"\([^)]*\)", " ", text)                  # 괄호 속 보충 설명
    text = re.sub(r"[A-Z]{2,4}-\d{2,4}", " ", text)          # 요구사항 ID
    words = [_Q_PARTICLE.sub("", w) if len(w) > 2 else w for w in re.split(r"[\s·,/]+", text) if w]
    out: set[str] = set()
    for w in (w for w in words if w and w not in _Q_STOP):
        out |= {w[i:i + 2] for i in range(max(1, len(w) - 1))}
    return out


def same_question(a: str, b: str, threshold: float = 0.6) -> bool:
    """발주기관에 물을 내용이 같은지(질의서 묶기용): 괄호·요구사항 ID·군말을 빼고, 짧은 쪽 기준 낱말 2-gram 겹침.
    회사 쪽 확인 사항(인력별 경력 등)에는 쓰지 않는다 — 'PM 경력'과 '개발 리더 경력'을 같다고 볼 수 있다."""
    ga, gb = _question_grams(a), _question_grams(b)
    return bool(ga and gb) and len(ga & gb) / min(len(ga), len(gb)) >= threshold


def open_items(placeholders: list[str]) -> list[str]:
    """자리표시자를 확인할 내용별로 묶은 대표 목록(표현만 다른 것은 하나로)."""
    reps: list[str] = []
    for p in placeholders:
        topic = placeholder_topic(p)
        if not topic or any(similar_topic(topic, r) for r in reps):
            continue
        reps.append(topic)
    return reps


def numbers(text: str) -> list[str]:
    """단위가 붙은 숫자 표현(실적·인원·성능 등 근거가 필요한 수치)."""
    return [m.group(0).strip() for m in NUMBER.finditer(text or "")]
