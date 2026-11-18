"""RFP 버전 비교(정정공고·사전규격→본공고·질의회신 반영, 설계서 7.11절).

안정 키로 항목 단위 diff를 만들고, 현재 목차·추적표를 역참조해 영향받는 절을 알려 준다.
배점·분량·마감·실격사유처럼 위험이 큰 변경은 사람이 확인할 작업으로 표시한다.

BidPilot-AI(AGPL-3.0, cd91f83)의 '변경 신호 → 재실행 단계' 표와 '재실행 전 영향 미리보기',
'옛값/새값 확인 작업'을 참고해 항목 단위로 재구현했다(docs/analysis/chinese-bid-generators.md 5.8절).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .schemas.common import Locator
from .schemas.plan import Outline, Trace
from .schemas.rfp import Rfp

ChangeKind = Literal["added", "removed", "changed"]

# 변경 대상 → 다시 돌려야 하는 단계(BidPilot의 invalidated_by 표에 해당)
RERUN: dict[str, list[str]] = {
    "requirement": ["plan.trace", "strategy", "generate(연결 절)"],
    "eval_item": ["plan.outline", "plan.budget", "plan.trace", "strategy", "generate(연결 절)"],
    "eval_rule": ["plan.outline(체크리스트)", "check"],
    "guideline": ["plan.budget", "render", "check"],
    "notice": ["project 메타데이터"],
    "compliance": ["check"],
}
HIGH_RISK_FIELDS = {"main_page_limit", "summary_page_limit", "total_size_limit_mb", "blind", "min_font_pt",
                    "file_format", "paper", "orientation", "budget_krw", "contract_method"}


class Change(BaseModel):
    target: str                  # requirement | eval_item | eval_rule | guideline | notice | compliance
    key: str
    kind: ChangeKind
    field: str | None = None
    old: str | None = None
    new: str | None = None
    high_risk: bool = False
    affected_sections: list[str] = Field(default_factory=list)
    old_locators: list[Locator] = Field(default_factory=list)
    new_locators: list[Locator] = Field(default_factory=list)


class RfpDiff(BaseModel):
    schema_version: str = "1"
    from_version: int
    to_version: int
    changes: list[Change] = Field(default_factory=list)
    rerun: list[str] = Field(default_factory=list)

    def confirmations(self) -> list[Change]:
        return [c for c in self.changes if c.high_risk]


def _s(v) -> str:
    if v is None:
        return ""
    if hasattr(v, "model_dump"):
        v = v.model_dump()
    if isinstance(v, list):
        return "\n".join(_s(x) for x in v)
    return str(v)


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def diff_rfp(old: Rfp, new: Rfp, from_version: int, to_version: int,
             outline: Outline | None = None, trace: Trace | None = None) -> RfpDiff:
    d = RfpDiff(from_version=from_version, to_version=to_version)
    req_sections: dict[str, list[str]] = {}
    item_sections: dict[str, list[str]] = {}
    titles: dict[str, str] = {}
    if outline is not None:
        for n in outline.walk():
            titles[n.id] = f"{n.number} {n.title}"
            for iid in n.eval_items:
                item_sections.setdefault(iid, []).append(n.id)
    if trace is not None:
        for row in trace.rows:
            req_sections[row.req_id] = row.sections

    def sections(ids: list[str]) -> list[str]:
        return [titles.get(i, i) for i in ids]

    # 요구사항: ID가 안정 키
    o_req = {r.id: r for r in old.requirements}
    n_req = {r.id: r for r in new.requirements}
    for rid in sorted(set(o_req) | set(n_req)):
        a, b = o_req.get(rid), n_req.get(rid)
        if a is None:
            d.changes.append(Change(target="requirement", key=rid, kind="added", new=b.name,  # type: ignore[union-attr]
                                    new_locators=b.locators[:1]))  # type: ignore[union-attr]
            continue
        if b is None:
            d.changes.append(Change(target="requirement", key=rid, kind="removed", old=a.name, high_risk=True,
                                    affected_sections=sections(req_sections.get(rid, [])), old_locators=a.locators[:1]))
            continue
        for field in ("name", "category", "definition", "details", "outputs"):
            va, vb = _s(getattr(a, field)), _s(getattr(b, field))
            if _norm(va) != _norm(vb):
                d.changes.append(Change(target="requirement", key=rid, kind="changed", field=field, old=va, new=vb,
                                        affected_sections=sections(req_sections.get(rid, [])),
                                        old_locators=a.locators[:1], new_locators=b.locators[:1]))

    # 평가항목: (부문, 정규화 항목명)이 안정 키. 내부 ID(A01-02)는 버전마다 달라질 수 있다.
    def items(r: Rfp):
        return {(_norm(a.name), _norm(i.name)): (a, i) for a in r.evaluation.areas for i in a.items}

    o_it, n_it = items(old), items(new)
    for key in sorted(set(o_it) | set(n_it)):
        a, b = o_it.get(key), n_it.get(key)
        label = f"{(a or b)[0].name} > {(a or b)[1].name}"  # type: ignore[index]
        if a is None:
            d.changes.append(Change(target="eval_item", key=label, kind="added", new=f"{b[1].points}점", high_risk=True,  # type: ignore[index]
                                    new_locators=b[1].locators[:1]))  # type: ignore[index]
        elif b is None:
            d.changes.append(Change(target="eval_item", key=label, kind="removed", old=f"{a[1].points}점", high_risk=True,
                                    affected_sections=sections(item_sections.get(a[1].id, [])), old_locators=a[1].locators[:1]))
        else:
            if a[1].points != b[1].points or a[1].kind != b[1].kind:
                d.changes.append(Change(target="eval_item", key=label, kind="changed", field="points",
                                        old=f"{a[1].kind} {a[1].points}점", new=f"{b[1].kind} {b[1].points}점", high_risk=True,
                                        affected_sections=sections(item_sections.get(a[1].id, [])),
                                        old_locators=a[1].locators[:1], new_locators=b[1].locators[:1]))
            if [_norm(c) for c in a[1].criteria] != [_norm(c) for c in b[1].criteria]:
                d.changes.append(Change(target="eval_item", key=label, kind="changed", field="criteria",
                                        old=_s(a[1].criteria), new=_s(b[1].criteria),
                                        affected_sections=sections(item_sections.get(a[1].id, []))))

    o_rules = {_norm(r.text) for r in old.evaluation.rules}
    n_rules = {_norm(r.text): r for r in new.evaluation.rules}
    for key, r in n_rules.items():
        if key not in o_rules:
            d.changes.append(Change(target="eval_rule", key=r.kind, kind="added", new=r.text, high_risk=r.kind == "감점",
                                    new_locators=r.locators[:1]))
    for r in old.evaluation.rules:
        if _norm(r.text) not in n_rules:
            d.changes.append(Change(target="eval_rule", key=r.kind, kind="removed", old=r.text))

    # 작성지침·공고 정보: 필드 단위
    for field in type(old.guideline).model_fields:
        if field in ("required_documents", "prescribed_toc"):
            continue
        a, b = getattr(old.guideline, field), getattr(new.guideline, field)
        va, vb = _s(a.value if a is not None else None), _s(b.value if b is not None else None)
        if _norm(va) != _norm(vb):
            d.changes.append(Change(target="guideline", key=field, kind="changed", field=field, old=va or None, new=vb or None,
                                    high_risk=field in HIGH_RISK_FIELDS,
                                    old_locators=a.locators[:1] if a else [], new_locators=b.locators[:1] if b else []))
    o_toc = _s(old.guideline.prescribed_toc.value if old.guideline.prescribed_toc else None)
    n_toc = _s(new.guideline.prescribed_toc.value if new.guideline.prescribed_toc else None)
    if _norm(o_toc) != _norm(n_toc):
        d.changes.append(Change(target="guideline", key="prescribed_toc", kind="changed", field="prescribed_toc",
                                old=o_toc or None, new=n_toc or None, high_risk=True))
    for field in ("title", "budget_krw", "period", "bid_no", "contract_method"):
        a, b = getattr(old.notice, field), getattr(new.notice, field)
        va, vb = _s(a.value if a is not None else None), _s(b.value if b is not None else None)
        if _norm(va) != _norm(vb):
            d.changes.append(Change(target="notice", key=field, kind="changed", field=field, old=va or None, new=vb or None,
                                    high_risk=field in HIGH_RISK_FIELDS))
    # 일정: 정정공고는 제출 마감·질의 기간을 자주 옮긴다 — 종류별로 맞대 본다
    from .extract.schedule import span_text

    o_s = {x.kind: x for x in old.notice.schedule}
    n_s = {x.kind: x for x in new.notice.schedule}
    for kind in dict.fromkeys([*o_s, *n_s]):
        a, b = o_s.get(kind), n_s.get(kind)
        if a is not None and b is not None and (a.start, a.end) == (b.start, b.end):
            continue
        d.changes.append(Change(target="notice", key=f"schedule.{kind}",
                                kind="changed" if a and b else ("added" if b else "removed"), field="schedule",
                                old=span_text(a) if a else None, new=span_text(b) if b else None,
                                high_risk=kind in ("제안서 제출", "입찰 마감", "질의", "제안서 평가"),
                                old_locators=a.locators[:1] if a else [], new_locators=b.locators[:1] if b else []))

    o_c = {_norm(c.text) for c in old.compliance if c.origin == "stated"}
    for c in new.compliance:
        if c.origin == "stated" and _norm(c.text) not in o_c:
            d.changes.append(Change(target="compliance", key=c.kind, kind="added", new=c.text, high_risk=True,
                                    new_locators=c.locators[:1]))

    targets = {c.target for c in d.changes}
    d.rerun = sorted({step for t in targets for step in RERUN.get(t, [])})
    return d


def diff_markdown(d: RfpDiff) -> str:
    lines = [f"# RFP 변경 비교 — v{d.from_version} → v{d.to_version}", ""]
    if not d.changes:
        return "\n".join(lines + ["변경 사항이 없습니다.", ""])
    names = {"requirement": "요구사항", "eval_item": "평가항목", "eval_rule": "평가규칙",
             "guideline": "작성지침", "notice": "공고 정보", "compliance": "무효·제외·감점 사유"}
    kinds = {"added": "추가", "removed": "삭제", "changed": "변경"}
    lines += [f"변경 {len(d.changes)}건, 그중 확인 필요 {len(d.confirmations())}건.", "",
              "## 다시 돌려야 할 단계(영향 미리보기)", ""]
    lines += [f"- {s}" for s in d.rerun] + [""]
    if d.confirmations():
        lines += ["## 사람 확인 필요(고위험 변경)", "", "| 대상 | 항목 | 변경 | 이전 | 이후 |", "|---|---|---|---|---|"]
        for c in d.confirmations():
            lines.append(f"| {names[c.target]} | {c.key}{f' · {c.field}' if c.field and c.field != c.key else ''} | "
                         f"{kinds[c.kind]} | {(c.old or '').replace(chr(10), ' ')[:60]} | {(c.new or '').replace(chr(10), ' ')[:60]} |")
        lines.append("")
    lines += ["## 전체 변경", ""]
    for target in names:
        group = [c for c in d.changes if c.target == target]
        if not group:
            continue
        lines += [f"### {names[target]} ({len(group)}건)", ""]
        for c in group:
            head = f"- **{kinds[c.kind]}** {c.key}" + (f" · `{c.field}`" if c.field and c.field != c.key else "")
            lines.append(head)
            if c.old:
                lines.append(f"  - 이전: {c.old.replace(chr(10), ' / ')[:200]}")
            if c.new:
                lines.append(f"  - 이후: {c.new.replace(chr(10), ' / ')[:200]}")
            if c.affected_sections:
                lines.append(f"  - 영향 절: {', '.join(c.affected_sections)}")
        lines.append("")
    return "\n".join(lines)


def load_versions(project: Path) -> list[int]:
    return sorted(int(m.group(1)) for p in (project / "rfp").glob("rfp.v*.json")
                  if (m := re.match(r"rfp\.v(\d+)\.json$", p.name)))


def diff_project(project: Path, from_version: int | None = None, to_version: int | None = None) -> tuple[RfpDiff, Path, Path]:
    versions = load_versions(project)
    if len(versions) < 2 and (from_version is None or to_version is None):
        raise ValueError("비교할 RFP 버전이 두 개 이상 있어야 합니다(analyze를 다시 실행해 새 버전을 만드세요)")
    to_v = to_version or versions[-1]
    from_v = from_version or max(v for v in versions if v < to_v)
    old = Rfp.model_validate_json((project / "rfp" / f"rfp.v{from_v}.json").read_text(encoding="utf-8"))
    new = Rfp.model_validate_json((project / "rfp" / f"rfp.v{to_v}.json").read_text(encoding="utf-8"))
    outline = trace = None
    plan_dir = project / "plan"
    # 영향 절은 옛 버전 기준 계획으로 계산한다(가장 최근 계획이 옛 버전에서 나왔다면 그대로 맞다)
    old_plan = plan_dir / f"v{from_v}"
    for base in (old_plan, plan_dir):
        if (base / "outline.json").exists() and (base / "trace.json").exists():
            outline = Outline.model_validate_json((base / "outline.json").read_text(encoding="utf-8"))
            trace = Trace.model_validate_json((base / "trace.json").read_text(encoding="utf-8"))
            break
    d = diff_rfp(old, new, from_v, to_v, outline, trace)
    json_path = project / "rfp" / f"diff_v{from_v}_v{to_v}.json"
    json_path.write_text(d.model_dump_json(indent=2), encoding="utf-8")
    md_path = project / "out" / f"diff_v{from_v}_v{to_v}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(diff_markdown(d), encoding="utf-8")
    return d, json_path, md_path
