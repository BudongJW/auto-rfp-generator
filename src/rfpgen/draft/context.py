"""초안 작성에 쓰는 입력 묶음과 LLM 문맥(설계서 7.6절 컨텍스트 순서).

순서를 고정해 프롬프트 캐싱에 유리하게 만든다:
[전역 고정] 작성자 지침 → [프로젝트 고정] RFP 요약·평가표·win theme·KB 카탈로그 → [절 가변] 절 정보.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..schemas.draft import Storyboard
from ..schemas.kb import CompanyKB
from ..schemas.plan import Outline, OutlineNode, PageBudget, Trace
from ..schemas.rfp import Requirement, Rfp


@dataclass
class DraftInputs:
    rfp: Rfp
    outline: Outline
    budget: PageBudget
    trace: Trace
    kb: CompanyKB
    title: str
    blind: bool
    storyboard: Storyboard | None = None
    requirement_index: dict[str, Requirement] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.requirement_index = {r.id: r for r in self.rfp.requirements}


def leaf_sections(outline: Outline) -> list[OutlineNode]:
    """초안을 쓸 단위: 절이 있는 장은 절, 없는 장은 장 자신. 쪽수 0인 장(증빙 등)은 뺀다."""
    out: list[OutlineNode] = []
    for ch in outline.chapters:
        if ch.page_budget <= 0 and not ch.children:
            continue
        out.extend(ch.children if ch.children else [ch])
    return [n for n in out if n.page_budget > 0 or n.requirements]


def chapter_of(outline: Outline, node_id: str) -> OutlineNode | None:
    for ch in outline.chapters:
        if ch.id == node_id or any(c.id == node_id for c in ch.children):
            return ch
    return None


def rfp_brief(inp: DraftInputs) -> str:
    rfp = inp.rfp
    lines = ["<rfp_brief>", f"사업명: {inp.title}"]
    if rfp.notice.period:
        lines.append(f"사업기간: {rfp.notice.period.value}")
    lines.append(f"블라인드 평가: {'예' if inp.blind else '아니오(그래도 회사명은 쓰지 않는다)'}")
    lines.append("평가표(정성):")
    for a in rfp.evaluation.areas:
        if a.kind != "정성":
            continue
        lines.append(f"- {a.name} {a.points:g}점" if a.points is not None else f"- {a.name}")
        for it in a.items:
            q = " / ".join(it.criteria[:3])
            lines.append(f"  - {it.name}({it.points:g}점){': ' + q if q else ''}" if it.points is not None
                         else f"  - {it.name}{': ' + q if q else ''}")
    if rfp.evaluation.rules:
        lines.append("평가규칙: " + " / ".join(r.text[:80] for r in rfp.evaluation.rules[:8]))
    stated = [c for c in rfp.compliance if c.origin == "stated"][:10]
    if stated:
        lines.append("무효·감점 사유: " + " / ".join(f"[{c.kind}] {c.text[:70]}" for c in stated))
    by_prefix: dict[str, int] = {}
    for r in rfp.requirements:
        by_prefix[r.prefix or "?"] = by_prefix.get(r.prefix or "?", 0) + 1
    lines.append("요구사항 수: " + ", ".join(f"{k} {v}건" for k, v in sorted(by_prefix.items())))
    if inp.storyboard and inp.storyboard.win_themes:
        lines.append("차별화 메시지(win theme): " + " / ".join(inp.storyboard.win_themes))
    lines.append("</rfp_brief>")
    return "\n".join(lines)


def outline_text(inp: DraftInputs) -> str:
    lines = ["<outline>"]
    titles = {n.id: n for n in inp.outline.walk()}
    for n in leaf_sections(inp.outline):
        ch = chapter_of(inp.outline, n.id)
        head = f"{ch.number} {ch.title} > " if ch is not None and ch is not n else ""
        reqs = ", ".join(f"{r}({inp.requirement_index[r].name[:20]})" for r in n.requirements[:12] if r in inp.requirement_index)
        more = f" 외 {len(n.requirements) - 12}건" if len(n.requirements) > 12 else ""
        lines.append(f"- section_id={n.id} | {head}{n.number} {n.title} | {n.page_budget}쪽 | 평가 질문: "
                     f"{' / '.join(n.checklist[:3]) or '-'} | 요구사항: {reqs or '-'}{more}")
    del titles
    lines.append("</outline>")
    return "\n".join(lines)


def kb_catalog(kb: CompanyKB) -> str:
    """LLM에 보이는 KB 목록: ID와 설명만. 값(금액·건수·연수)은 넣지 않는다."""
    lines = ["<kb_catalog>", "토큰 형식: {{fact:ID}} 또는 {{kb:ID.필드}}"]
    for f in kb.facts:
        lines.append(f"- fact {f.id}: {f.label}")
    for p in kb.projects:
        lines.append(f"- 실적 {p.id}: {p.name} / 발주 {p.client} / {p.role} / 기술 {', '.join(p.tech)} "
                     f"(필드: amount_krw, start, end)")
    for h in kb.people:
        lines.append(f"- 인력 {h.id}: {h.role} {h.grade} / 기술 {', '.join(h.skills)} / 자격 {', '.join(h.certs)} (필드: years)")
    for c in kb.certifications:
        lines.append(f"- 인증 {c.id}: {c.name} (필드: number, valid_until)")
    for k in kb.content:
        lines.append(f"- 재사용 문단 {k.id}: {k.title} [{', '.join(k.tags)}]")
    lines.append("</kb_catalog>")
    return "\n".join(lines)


def section_text(inp: DraftInputs, node: OutlineNode, include_kb_content: bool) -> str:
    plan = inp.storyboard.plan(node.id) if inp.storyboard else None
    target = next((ln.target_chars for ln in inp.budget.lines if ln.node_id == node.id), [])
    lines = ["<section>", f"section_id: {node.id}", f"번호·제목: {node.number} {node.title}",
             f"쪽수 예산: {node.page_budget}쪽"]
    if target:
        lines.append(f"목표 글자 수: {target[0]:,}~{target[1]:,}자")
    if node.checklist:
        lines.append("평가 질문:")
        lines += [f"- {q}" for q in node.checklist]
    if plan is not None:
        if plan.head_message:
            lines.append(f"거버닝 메시지(스토리보드): {plan.head_message}")
        if plan.key_points:
            lines.append("핵심 내용(스토리보드): " + " / ".join(plan.key_points))
    if node.requirements:
        lines.append("연결 요구사항:")
        for rid in node.requirements[:80]:
            r = inp.requirement_index.get(rid)
            if r is None:
                continue
            detail = " / ".join(r.details[:6])
            lines.append(f"- {r.id} {r.name}: {r.definition[:200]}{' | 세부: ' + detail[:400] if detail else ''}")
        if len(node.requirements) > 80:
            lines.append(f"- … 외 {len(node.requirements) - 80}건(대응 방안은 모두 responses에 적을 것)")
    if include_kb_content:
        hits = relevant_content(inp.kb, node)
        for k in hits[:2]:
            lines.append(f"<kb_content id=\"{k.id}\" title=\"{k.title}\">\n{k.text[:3000]}\n</kb_content>")
    lines.append("</section>")
    return "\n".join(lines)


def relevant_content(kb: CompanyKB, node: OutlineNode):
    from ..plan.outline import similarity

    scored = []
    for k in kb.content:
        score = max([similarity(t, node.title) for t in k.tags] + [similarity(k.title, node.title)] or [0])
        if score >= 0.5:
            scored.append((score, k))
    return [k for _, k in sorted(scored, key=lambda t: -t[0])]
