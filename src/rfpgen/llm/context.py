"""LLM에 보낼 RFP 발췌(키워드 창).

수백 쪽 RFP 전체를 매 과제에 보내지 않고, 과제 키워드가 걸린 블록과 그 앞뒤 블록만 모아
'[블록ID] (p.쪽) 텍스트' 줄로 만든다(OpenBidKit의 키워드 창 탐색 방식). 보낸 블록 ID 집합을
함께 돌려줘, 응답의 근거가 보낸 범위 안에 있는지 검증할 수 있게 한다.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from ..schemas.docir import Block, Document


@dataclass
class Excerpt:
    text: str
    block_ids: set[str] = field(default_factory=set)
    truncated: bool = False
    hits: int = 0


def render_block(b: Block) -> str:
    where = []
    if b.page:
        where.append(f"p.{b.page}")
    if b.kind == "cell" and b.cell is not None:
        where.append(f"표 {b.cell.table_id} r{b.cell.row}c{b.cell.col}")
    head = f"[{b.id}]" + (f" ({', '.join(where)})" if where else "")
    return f"{head} {b.text.replace(chr(10), ' / ')}"


def keyword_excerpt(docs: list[Document], pattern: re.Pattern[str] | Callable[[Block], bool], *, radius: int = 2,
                    max_chars: int = 60000, skip_tables: set[str] | None = None) -> Excerpt:
    """pattern은 정규식(블록 텍스트 검색) 또는 블록을 받는 판정 함수다."""
    skip = skip_tables or set()
    matches: Callable[[Block], bool] = (lambda b: bool(pattern.search(b.text))) if isinstance(pattern, re.Pattern) \
        else pattern
    parts: list[str] = []
    ids: set[str] = set()
    total = 0
    hits = 0
    truncated = False
    for doc in docs:
        blocks = [b for b in doc.blocks if b.kind != "table" and not (b.kind == "cell" and b.parent in skip)]
        chosen: set[int] = set()
        for i, b in enumerate(blocks):
            if matches(b):
                hits += 1
                chosen.update(range(max(0, i - radius), min(len(blocks), i + radius + 1)))
        if not chosen:
            continue
        lines = [f'<document doc_id="{doc.doc_id}" filename="{doc.filename}">']
        prev = -2
        for i in sorted(chosen):
            if i != prev + 1 and prev >= 0:
                lines.append("…")
            line = render_block(blocks[i])
            if total + len(line) > max_chars:
                truncated = True
                break
            lines.append(line)
            ids.add(blocks[i].id)
            total += len(line) + 1
            prev = i
        lines.append("</document>")
        parts.append("\n".join(lines))
        if truncated:
            break
    return Excerpt(text="\n".join(parts), block_ids=ids, truncated=truncated, hits=hits)
