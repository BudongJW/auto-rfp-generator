"""LLM 응답의 근거 검증(설계서 7.3절 C, 원칙 P2·P3).

- 인용문이 지정한 블록 텍스트에 실제로 있는지(공백·문장부호를 지운 뒤 부분 문자열) 확인한다.
- 숫자 값은 그 숫자가 인용문에 실제로 적혀 있어야 받아들인다. 숫자가 도형 글자라 원문에서
  읽히지 않는 PDF에서 LLM이 '관행 값'을 채워 넣는 것을 막는다.
OpenBidKit_Yibiao(AGPL-3.0, 77a38f0)의 normalizeForMatch·valueIssue 검증 방식을 재구현했다.
"""

from __future__ import annotations

import re

from ..schemas.common import Locator
from ..schemas.docir import Block, Document

_STRIP = re.compile(r"[\s 　.,，、·ㆍ:：;；'\"‘’“”()（）\[\]「」『』<>〈〉《》\-–—_~!?/※*○◦□■●•]+")


def normalize_for_match(text: str) -> str:
    return _STRIP.sub("", text or "").lower()


class BlockIndex:
    """여러 문서의 블록을 ID로 찾는다."""

    def __init__(self, docs: list[Document]) -> None:
        self.blocks: dict[str, tuple[Document, Block]] = {}
        for d in docs:
            for b in d.blocks:
                self.blocks[b.id] = (d, b)

    def get(self, block_id: str) -> tuple[Document, Block] | None:
        return self.blocks.get(block_id.strip().strip("[]"))


def verify_evidence(index: BlockIndex, block_id: str, quote: str, allowed: set[str] | None = None) -> Locator | None:
    """근거가 유효하면 Locator를, 아니면 None을 돌려준다.

    allowed가 주어지면 그 블록들(LLM에 실제로 보여 준 블록) 안에서만 인정한다.
    """
    found = index.get(block_id)
    if found is None:
        return None
    doc, block = found
    if allowed is not None and block.id not in allowed:
        return None
    q = normalize_for_match(quote)
    if len(q) < 2 or q not in normalize_for_match(block.text):
        return None
    start = block.text.find(quote.strip())
    return Locator(
        doc_id=doc.doc_id,
        block_id=block.id,
        page=block.page,
        char_start=start if start >= 0 else None,
        char_end=start + len(quote.strip()) if start >= 0 else None,
        quote=quote.strip()[:300],
    )


_DIGITS = re.compile(r"\d+(?:\.\d+)?")


def number_in_quote(value: float, quote: str) -> bool:
    """값의 숫자가 인용문에 아라비아 숫자로 적혀 있는지."""
    for m in _DIGITS.finditer((quote or "").replace(",", "")):
        if abs(float(m.group(0)) - value) < 1e-9:
            return True
    return False
