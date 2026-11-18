"""요구사항 → 목차 절 매핑과 추적표(설계서 7.4절 3, 6.4절).

1) 요구사항 분류명과 절 제목의 유사도 2) 접두어 키워드가 절 제목에 있는지
3) 접두어 → 표준 장 기본 맵 순으로 찾는다. 결과는 사람이 G2에서 확정한다.
"""

from __future__ import annotations

import re

from ..profile import Profile
from ..schemas.plan import Outline, OutlineNode, Trace, TraceRow
from ..schemas.rfp import ExtractionReport, Requirement, Rfp
from .outline import similarity

_CATEGORY_SUFFIX = re.compile(r"\s*(요구\s*사항|요건)\s*$")


def _section_candidates(outline: Outline) -> list[tuple[OutlineNode, OutlineNode]]:
    """(장, 절) 목록. 절이 없는 장은 장 자신을 절로 쓴다."""
    out = []
    for ch in outline.chapters:
        if ch.children:
            out.extend((ch, s) for s in ch.children)
        else:
            out.append((ch, ch))
    return out


def _map_one(req: Requirement, cands, chapter_map: dict[str, str],
             keywords: dict[str, list[str]]) -> tuple[list[OutlineNode], str]:
    # 1) 분류명(예: '아키텍처 요구사항')과 절 제목 유사도
    cat = req.category.split(">")[-1].strip() if req.category else ""
    if cat:
        scored = sorted(((max(similarity(cat, s.title), similarity(_CATEGORY_SUFFIX.sub("", cat), s.title)), s)
                         for _, s in cands), key=lambda t: -t[0])
        if scored and scored[0][0] >= 0.6:
            return [scored[0][1]], f"분류 '{cat}' ≈ 절 '{scored[0][1].title}' (유사도 {scored[0][0]:.2f})"
    prefix = req.prefix or ""
    target = chapter_map.get(prefix)
    # 2) 접두어 키워드가 절 제목에 있는 절(기본 장 안을 먼저)
    kws = keywords.get(prefix, [])
    if kws:
        hits = [(ch, s) for ch, s in cands if any(k in s.title for k in kws)]
        preferred = [s for ch, s in hits if ch.canonical == target] or [s for _, s in hits]
        if preferred:
            return [preferred[0]], f"접두어 {prefix} 키워드 {kws} → 절 '{preferred[0].title}'"
    # 3) 접두어 → 표준 장
    if target:
        chapters = [ch for ch, _ in cands if ch.canonical == target]
        if chapters:
            return [chapters[0]], f"접두어 {prefix} → 표준 장 '{target}' (장 단위 연결)"
    return [], "연결할 절을 찾지 못함"


def build_trace(rfp: Rfp, outline: Outline, profile: Profile, report: ExtractionReport) -> Trace:
    chapter_map = profile.value("requirements.prefix_chapter_map")
    keywords = profile.value("requirements.prefix_section_keywords")
    items = {it.id: it for it in rfp.evaluation.items()}
    cands = _section_candidates(outline)
    trace = Trace()
    for req in rfp.requirements:
        nodes, reason = _map_one(req, cands, chapter_map, keywords)
        eval_item = None
        for n in nodes:
            if req.id not in n.requirements:
                n.requirements.append(req.id)
            if eval_item is None and n.eval_items:
                eval_item = items[n.eval_items[0]].name if n.eval_items[0] in items else None
        trace.rows.append(TraceRow(
            req_id=req.id,
            req_name=req.name,
            category=req.category,
            eval_item=eval_item,
            sections=[n.id for n in nodes],
            rfp_locators=req.locators[:2],
            status="mapped" if nodes else "unmapped",
            mapping_reason=reason,
        ))
    unmapped = [r.req_id for r in trace.rows if r.status == "unmapped"]
    if unmapped:
        report.add("PLAN-REQ-UNMAPPED", "error",
                   f"목차 절에 연결되지 않은 요구사항 {len(unmapped)}건 — G2에서 수동 연결 필요: {', '.join(unmapped[:20])}")
    report.stats["trace_coverage"] = round(trace.coverage(), 4)
    return trace
