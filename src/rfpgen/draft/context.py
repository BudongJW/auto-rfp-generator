"""초안 작성에 쓰는 입력 묶음과 LLM 문맥(설계서 7.6절 컨텍스트 순서).

순서를 고정해 프롬프트 캐싱에 유리하게 만든다:
[전역 고정] 작성자 지침 → [프로젝트 고정] RFP 요약·평가표·win theme·KB 카탈로그 → [절 가변] 절 정보.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..schemas.docir import Block, Document
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
    overview: str = ""                                  # RFP 사업 개요·배경·현황 발췌(overview_excerpt)
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


# ---- RFP 사업 개요 발췌 ------------------------------------------------------------------------
# 개요 절(사업 이해도·제안 배경·추진 전략)은 연결 요구사항이 없어, 이 발췌가 없으면 LLM이 RFP에 있는 내용까지
# [확인 필요]로 남긴다(2026-11-18 예제 실측: 사업 이해도 23곳).

OVERVIEW_TITLE = re.compile(r"사업\s*개요|추진\s*(배경|목적|경과|방안|방향|전략|범위)|사업\s*(배경|목적|범위|내용)|필요성"
                            r"|현\s*황|기대\s*효과")
NOT_OVERVIEW = re.compile(r"요구\s*사항|제안\s*(요청|서|안내)|작성|평가|서식|구매|입찰|계약|자격|제출")
CHAPTER_NUM = re.compile(r"^\s*(?:[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]|[IVX]{1,4}|제\s*\d{1,2}\s*장)\s*[.)]?\s*\S")
TOC_LEADER = re.compile(r"[·.…]{4,}|\s\d{1,3}\s*$")
PRIVATE_USE = re.compile(r"[\ue000-\uf8ff\U000f0000-\U0010ffff]")


def _chapters(doc: Document) -> list[int]:
    """장(가장 높은 단계 제목) 블록의 위치. 제목 판별이 없으면 'Ⅰ. …' 꼴의 짧은 문단을 장으로 본다."""
    heads = [(i, b) for i, b in enumerate(doc.blocks) if b.kind == "heading" and not TOC_LEADER.search(b.text)]
    numbered = [(i, b) for i, b in heads if CHAPTER_NUM.match(b.text)]
    if numbered:
        top = min((b.level or 1) for _, b in numbered)
        return [i for i, b in numbered if (b.level or 1) == top]
    return [i for i, b in enumerate(doc.blocks)
            if b.kind == "para" and len(b.text) < 40 and CHAPTER_NUM.match(b.text) and not TOC_LEADER.search(b.text)]


def _render(blocks: list[Block]) -> list[str]:
    """문단은 그대로, 표 칸은 행마다 ' | '로 이어 한 줄로."""
    lines: list[str] = []
    row_key, row = None, []
    for b in blocks:
        if b.kind == "cell" and b.cell is not None:
            key = (b.cell.table_id, b.cell.row)
            if key != row_key and row:
                lines.append(" | ".join(row))
                row = []
            row_key = key
            text = " ".join(b.text.split())
            if text:
                row.append(text)
            continue
        if row:
            lines.append(" | ".join(row))
            row, row_key = [], None
        if b.kind in ("heading", "para"):
            lines.append(" ".join(b.text.split()))
    if row:
        lines.append(" | ".join(row))
    return lines


def overview_excerpt(docs: list[Document], *, per_part: int = 3000, total: int = 9000) -> str:
    """제안요청서의 사업 개요·추진 배경·목적·현황·추진 방향 장을 발췌한다(공개 RFP 원문이므로 LLM에 보내도 된다)."""
    parts: list[str] = []
    used = 0
    for doc in docs:
        if doc.role in ("별지서식", "평가기준"):
            continue
        idx = _chapters(doc)
        for k, start in enumerate(idx):
            title = " ".join(doc.blocks[start].text.split())
            if not OVERVIEW_TITLE.search(title) or NOT_OVERVIEW.search(title):
                continue
            end = idx[k + 1] if k + 1 < len(idx) else len(doc.blocks)
            seen: set[str] = set()
            body: list[str] = []
            size = 0
            for line in _render(doc.blocks[start + 1:end]):
                line = PRIVATE_USE.sub("", line).strip()
                if not line or line in seen:
                    continue
                seen.add(line)
                body.append(line)
                size += len(line) + 1
                if size >= per_part:
                    body.append("…(이하 생략)")
                    break
            if body:
                part = f"[{title}]\n" + "\n".join(body)
                parts.append(part)
                used += len(part)
            if used >= total:
                break
        if used >= total:
            break
    if not parts:
        return ""
    return "<rfp_overview>\n" + "\n\n".join(parts) + "\n</rfp_overview>"


def load_overview(project: Path) -> str:
    docs = []
    for f in sorted((Path(project) / "docir").glob("*.json")):
        try:
            docs.append(Document.model_validate_json(f.read_text(encoding="utf-8")))
        except ValueError:
            continue
    return overview_excerpt(docs)


# ---- LLM 문맥 -----------------------------------------------------------------------------------


def rfp_brief(inp: DraftInputs) -> str:
    rfp = inp.rfp
    lines = ["<rfp_brief>", f"사업명: {inp.title}"]
    if rfp.notice.agency:
        lines.append(f"발주기관: {rfp.notice.agency.value}")
    if rfp.notice.budget_krw:
        lines.append(f"사업예산: {rfp.notice.budget_krw.value:,}원")
    if rfp.notice.period:
        lines.append(f"사업기간: {rfp.notice.period.value}")
    if rfp.notice.contract_method:
        lines.append(f"계약방법: {rfp.notice.contract_method.value}")
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
    lines.append(f"요구사항 수: 총 {len(rfp.requirements)}건(" + ", ".join(f"{k} {v}건" for k, v in sorted(by_prefix.items()))
                 + ")")
    if rfp.requirements:
        lines.append("요구사항 목록(ID 이름):")
        groups: dict[str, list[str]] = {}
        for r in rfp.requirements[:400]:
            groups.setdefault(r.prefix or "?", []).append(f"{r.id} {r.name[:30]}")
        lines += [f"- {k}: " + "; ".join(v) for k, v in groups.items()]
        if len(rfp.requirements) > 400:
            lines.append(f"- … 외 {len(rfp.requirements) - 400}건")
    if inp.storyboard and inp.storyboard.win_themes:
        lines.append("차별화 메시지(win theme): " + " / ".join(inp.storyboard.win_themes))
    lines.append("</rfp_brief>")
    if inp.overview:
        lines.append(inp.overview)
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
