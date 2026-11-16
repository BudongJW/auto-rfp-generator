"""계획(plan) 단계: Rfp → 목차·쪽수 예산·추적표."""

from __future__ import annotations

from ..profile import Profile
from ..schemas.plan import Outline, PageBudget, Trace
from ..schemas.rfp import ExtractionReport, Rfp
from .budget import build_budget, largest_remainder
from .outline import build_outline, canonical, similarity
from .trace import build_trace


def plan_proposal(rfp: Rfp, profile: Profile, report: ExtractionReport) -> tuple[Outline, PageBudget, Trace]:
    outline = build_outline(rfp, profile, report)
    trace = build_trace(rfp, outline, profile, report)
    budget = build_budget(outline, rfp, profile, report)
    return outline, budget, trace


__all__ = ["build_budget", "build_outline", "build_trace", "canonical", "largest_remainder", "plan_proposal", "similarity"]
