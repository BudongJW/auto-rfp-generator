"""LLM 비용 추정: 감사 기록(audit/llm_calls.jsonl)의 모델·토큰과 프로필 단가로 계산한다.

실제 청구액이 아니라 추정이다(단가는 프로필 llm.pricing_usd_per_mtok, 바뀔 수 있음).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CostEstimate:
    usd: float = 0.0
    calls: int = 0
    by_model: dict[str, float] = field(default_factory=dict)
    unpriced: list[str] = field(default_factory=list)     # 단가를 모르는 모델


def _price(model: str, pricing: dict[str, dict[str, float]]) -> dict[str, float] | None:
    if model in pricing:
        return pricing[model]
    keys = [k for k in pricing if model.startswith(k)]
    return pricing[max(keys, key=len)] if keys else None


def estimate(audit_path: Path, pricing: dict[str, dict[str, float]], *, since_line: int = 0) -> CostEstimate:
    """감사 기록의 since_line번째 줄부터 비용을 더한다(이번 실행분만 보려면 실행 전 줄 수를 넘긴다)."""
    est = CostEstimate()
    path = Path(audit_path)
    if not path.exists():
        return est
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if i < since_line or not line.strip():
            continue
        rec = json.loads(line)
        usage, model = rec.get("usage") or {}, str(rec.get("model") or "")
        if not usage:
            continue
        est.calls += 1
        p = _price(model, pricing)
        if p is None:
            if model and model not in est.unpriced:
                est.unpriced.append(model)
            continue
        usd = (int(usage.get("input_tokens") or 0) * p["input"] + int(usage.get("output_tokens") or 0) * p["output"]
               + int(usage.get("cache_read_input_tokens") or 0) * p["cache_read"]
               + int(usage.get("cache_creation_input_tokens") or 0) * p["cache_write"]) / 1_000_000
        est.usd += usd
        est.by_model[model] = est.by_model.get(model, 0.0) + usd
    return est


def audit_lines(audit_path: Path) -> int:
    path = Path(audit_path)
    return len(path.read_text(encoding="utf-8").splitlines()) if path.exists() else 0


__all__ = ["CostEstimate", "audit_lines", "estimate"]
