"""쪽수 예산(설계서 7.4절).

절 i의 쪽수 = (본문 상한 − 고정 장 쪽수) × (절 i의 정성 배점 / 정성 배점 합계)
정수화는 최대잉여법, 배점이 있는 절은 최소 1쪽. 이 식은 '배점 비례 분량' 실무 원칙을
계량화한 제안이며 검증된 최적식이 아니다.
"""

from __future__ import annotations

import math

from ..profile import Profile
from ..schemas.plan import BudgetLine, Outline, OutlineNode, PageBudget
from ..schemas.rfp import ExtractionReport, Rfp

_FIXED_KEYS = {"제안개요", "제안업체일반"}


def largest_remainder(weights: list[float], total: int, minimum: int = 1) -> list[int]:
    """가중치에 비례해 total을 정수로 나눈다. 각 몫은 minimum 이상."""
    if not weights:
        return []
    w_sum = sum(weights)
    if w_sum <= 0:
        return [minimum] * len(weights)
    raw = [total * w / w_sum for w in weights]
    alloc = [max(minimum, math.floor(r)) for r in raw]
    diff = total - sum(alloc)
    # 잉여는 배정값 기준으로 잰다(최소값으로 올린 몫은 잉여가 음수가 되어 뒤로 밀린다).
    order = sorted(range(len(raw)), key=lambda i: raw[i] - alloc[i], reverse=True)
    i = 0
    while diff > 0 and order:
        alloc[order[i % len(order)]] += 1
        diff -= 1
        i += 1
    # 최소값 때문에 넘친 경우: 배정이 원래 몫보다 가장 많이 큰 것부터 줄인다
    shrink = sorted(range(len(raw)), key=lambda i: raw[i] - alloc[i])
    while diff < 0:
        changed = False
        for j in shrink:
            if diff >= 0:
                break
            if alloc[j] > minimum:
                alloc[j] -= 1
                diff += 1
                changed = True
        if not changed:
            break
    return alloc


def _assign_points(outline: Outline, rfp: Rfp) -> None:
    """정성 항목 배점을 연결된 절에 나눠 준다(한 항목이 여러 절에 걸치면 균등 분할)."""
    items = {it.id: it for it in rfp.evaluation.qualitative_items()}
    holders: dict[str, list[OutlineNode]] = {}
    for node in outline.walk():
        for iid in node.eval_items:
            if iid in items:
                holders.setdefault(iid, []).append(node)
    for iid, nodes in holders.items():
        share = (items[iid].points or 0) / len(nodes)
        for n in nodes:
            n.points += share
    for ch in outline.chapters:
        if ch.children:
            ch.points = sum(c.points for c in ch.children) + (ch.points if not ch.children else 0)


_PT_MM = 0.3528  # 1pt = 0.3528mm


def chars_per_page(profile: Profile, rfp: Rfp) -> tuple[int, int]:
    """쪽당 글자 수(이론 상한, 실효값). OpenBidKit_Yibiao pageMetrics(AGPL-3.0)의 계산법을 재구현.

    한글은 전각이라 글자 폭 ≈ 글자 크기. 한 줄 = ⌊본문 폭 ÷ 글자 폭⌋, 한 쪽 = ⌊본문 높이 ÷ (글자 크기 × 줄간격)⌋.
    """
    pt = float(profile.value("page_metrics.font_pt"))
    if rfp.guideline.min_font_pt is not None:
        pt = max(pt, float(rfp.guideline.min_font_pt.value))
    width = float(profile.value("page_metrics.body_width_mm"))
    height = float(profile.value("page_metrics.body_height_mm"))
    spacing = float(profile.value("page_metrics.line_spacing_pct")) / 100
    per_line = math.floor(width / (pt * _PT_MM))
    lines = math.floor(height / (pt * _PT_MM * spacing))
    theoretical = per_line * lines
    return theoretical, int(theoretical * float(profile.value("page_metrics.effective_ratio")))


def build_budget(outline: Outline, rfp: Rfp, profile: Profile, report: ExtractionReport) -> PageBudget:
    _assign_points(outline, rfp)
    g = rfp.guideline
    if g.main_page_limit is not None:
        limit, source = g.main_page_limit.value, "RFP 작성지침"
    else:
        pv = profile.get("page_limits.main_pages")
        limit, source = int(pv.value), f"프로필 기본값({pv.status})"
    fixed_specs = {spec["key"]: int(spec.get("pages", 0)) for spec in profile.value("outline.fixed_chapters")}
    excluded = set(g.count_exclusions.value) if g.count_exclusions else set(profile.value("page_limits.exclude_from_count"))

    fixed_pages = 0
    scored: list[OutlineNode] = []
    for ch in outline.chapters:
        if ch.canonical in _FIXED_KEYS:
            ch.page_budget = fixed_specs.get(ch.canonical or "", 2)
            _spread(ch, ch.page_budget)
            fixed_pages += ch.page_budget
        elif ch.points <= 0:
            is_excluded = ch.canonical == "증빙자료" and any("증빙" in e for e in excluded)
            ch.page_budget = 0 if is_excluded else 1
            _spread(ch, ch.page_budget)
            fixed_pages += ch.page_budget
        else:
            secs = [s for s in ch.children if s.points > 0] if ch.children else [ch]
            scored.extend(secs)
            # 배점 없는 절도 지정 목차에서는 지워선 안 되므로 1쪽을 고정으로 준다
            for s in ch.children:
                if s.points <= 0:
                    s.page_budget = 1
                    fixed_pages += 1

    distributable = max(limit - fixed_pages, 0)
    total_points = sum(s.points for s in scored)
    alloc = largest_remainder([s.points for s in scored], distributable)
    if scored and sum(alloc) > distributable:
        report.add("PLAN-BUDGET-OVER", "warning",
                   f"절마다 최소 1쪽을 주면 상한을 {sum(alloc) - distributable}쪽 넘습니다 — 상한 또는 고정 장 쪽수를 조정하세요")
    for s, pages in zip(scored, alloc):
        s.page_budget = pages
    for ch in outline.chapters:
        if ch.children and ch.points > 0:
            ch.page_budget = sum(s.page_budget for s in ch.children)

    theoretical, effective = chars_per_page(profile, rfp)
    lines = [
        BudgetLine(node_id=s.id, number=s.number, title=s.title, points=round(s.points, 2),
                   raw=round(distributable * s.points / total_points, 2) if total_points else 0.0,
                   pages=s.page_budget,
                   target_chars=[int(s.page_budget * effective * 0.8), int(s.page_budget * effective * 1.2)])
        for s in scored
    ]
    dense = [(s, len(s.requirements) / max(s.page_budget, 1)) for s in outline.walk()
             if s.requirements and len(s.requirements) / max(s.page_budget, 1) > 10]
    for s, ratio in dense:
        report.add("PLAN-DENSITY", "info",
                   f"'{s.title}' 절은 {s.page_budget}쪽에 요구사항 {len(s.requirements)}건(쪽당 {ratio:.0f}건)입니다 — "
                   "요구사항별 상세는 부록·추적표로 돌리고 본문은 대표 방안 중심으로 쓰는 것을 검토하세요")
    unbudgeted = [s.title for ch in outline.chapters if ch.points > 0 for s in ch.children if s.points <= 0]
    if unbudgeted:
        report.add("PLAN-SECTION-NO-POINTS", "info",
                   f"배점이 연결되지 않은 절 {len(unbudgeted)}개는 1쪽으로 두었습니다: {', '.join(unbudgeted[:8])}")
    return PageBudget(
        main_page_limit=limit,
        main_page_limit_source=source,
        fixed_pages=fixed_pages,
        distributable_pages=distributable,
        qualitative_points=round(total_points, 2),
        chars_per_page=theoretical,
        effective_chars_per_page=effective,
        lines=lines,
    )


def _spread(ch: OutlineNode, pages: int) -> None:
    if not ch.children:
        return
    alloc = largest_remainder([1.0] * len(ch.children), pages, minimum=0)
    for s, p in zip(ch.children, alloc):
        s.page_budget = p
