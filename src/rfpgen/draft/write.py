"""스토리보드(설계서 7.5절)와 절 초안(7.6절).

두 모드가 있다.
- 골격(skeleton): LLM 없이 평가 질문·요구사항·필요 근거를 자리표시자와 함께 배치한다. 작성자가 채울 틀이다.
- LLM: 스토리보드와 절 본문을 생성한다. 회사 수치는 토큰으로만 쓰게 하고 값은 코드가 채운다.
  KB 설명·과거 문단은 사용자가 허용할 때만(data_class=internal) 보낸다.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from ..diagram.build import plan_figures
from ..llm import LLMCall, LLMError, LLMGateway
from ..llm.prompts import EXPAND_INSTRUCTION, SECTION_INSTRUCTION, STORYBOARD_INSTRUCTION, SYSTEM_WRITER
from ..plan.outline import similarity
from ..profile import Profile
from ..schemas.draft import (
    DataRequest,
    DraftBlock,
    RequirementResponse,
    SectionDraft,
    SectionPlan,
    Storyboard,
    TableSpec,
)
from ..schemas.kb import CompanyKB
from ..schemas.plan import OutlineNode
from .context import DraftInputs, kb_catalog, leaf_sections, outline_text, relevant_content, rfp_brief, section_text
from .tokens import PLACEHOLDER, apply_tokens, open_items, placeholder_topic, similar_topic

_NEEDS_BY_CANONICAL = {
    "제안업체일반": ["회사 일반현황(설립·인원·매출)", "유사사업 수행 실적", "보유 인증"],
    "프로젝트관리": ["투입 인력(PM 등급·경력)", "사업관리 방법론·도구"],
    "전략및방법론": ["유사사업 수행 실적", "적용 방법론 적용 사례"],
    "프로젝트지원": ["교육·기술이전 실적", "유지보수 체계"],
    "상생협력하도급": ["하도급 계획(대상·비율)", "중소기업 참여 계획"],
}


# ---- 스토리보드 -----------------------------------------------------------------------------


class SectionPlanOut(BaseModel):
    section_id: str
    head_message: str
    key_points: list[str]
    needed_facts: list[str]


class StoryboardOut(BaseModel):
    win_themes: list[str]
    sections: list[SectionPlanOut]


def _budget_target(inp: DraftInputs, node: OutlineNode) -> list[int]:
    return next((ln.target_chars for ln in inp.budget.lines if ln.node_id == node.id), [])


def skeleton_storyboard(inp: DraftInputs) -> Storyboard:
    sb = Storyboard(origin="skeleton")
    top = sorted((a for a in inp.rfp.evaluation.areas if a.kind == "정성"), key=lambda a: -(a.points or 0))[:3]
    sb.win_themes = [f"[확인 필요: '{a.name}'({a.points:g}점) 부문의 차별화 메시지]" if a.points is not None
                     else f"[확인 필요: '{a.name}' 부문의 차별화 메시지]" for a in top]
    figures = plan_figures(inp.outline, inp.rfp)
    for node in leaf_sections(inp.outline):
        ch_key = next((c.canonical for c in inp.outline.chapters if c is node or node in c.children), None)
        sb.sections.append(SectionPlan(
            section_id=node.id, number=node.number, title=node.title,
            head_message="", key_points=list(node.checklist[:5]), eval_items=list(node.eval_items),
            requirements=list(node.requirements), needed_facts=list(_NEEDS_BY_CANONICAL.get(ch_key or "", [])),
            page_budget=node.page_budget, target_chars=_budget_target(inp, node),
            figures=figures.get(node.id, [])))  # type: ignore[arg-type]
    return sb


def llm_storyboard(inp: DraftInputs, gateway: LLMGateway, profile: Profile, share_kb: bool) -> Storyboard:
    spec = profile.value("llm.tasks")["storyboard"]
    context = rfp_brief(inp) + "\n" + outline_text(inp) + ("\n" + kb_catalog(inp.kb) if share_kb else "")
    out, _ = gateway.run(LLMCall(task="draft.storyboard", system=SYSTEM_WRITER, context=context,
                                 instruction=STORYBOARD_INSTRUCTION, schema=StoryboardOut, effort=spec["effort"],
                                 max_tokens=int(spec["max_tokens"]), data_class="internal" if share_kb else "public"),
                         StoryboardOut)
    base = skeleton_storyboard(inp)
    by_id = {p.section_id: p for p in out.sections}
    for plan in base.sections:
        o = by_id.get(plan.section_id)
        if o is None:
            continue
        plan.head_message = o.head_message.strip()
        plan.key_points = [k.strip() for k in o.key_points if k.strip()] or plan.key_points
        plan.needed_facts = [n.strip() for n in o.needed_facts if n.strip()] or plan.needed_facts
    base.win_themes = [w.strip() for w in out.win_themes if w.strip()][:5] or base.win_themes
    base.origin = "llm"
    return base


_GENERIC_WORDS = {"유사사업", "유사", "사업", "수행", "실적", "보유", "투입", "인력", "인증", "등급", "경력", "현황",
                  "등", "및", "의", "관련", "자료", "근거", "건수", "목록"}


def _specific_terms(need: str) -> list[str]:
    words = re.findall(r"[가-힣A-Za-z0-9]+", need)
    return [w for w in words if w not in _GENERIC_WORDS and len(w) >= 2]


def data_requests(sb: Storyboard, kb: CompanyKB) -> list[DataRequest]:
    """스토리보드가 요구하는 근거 중 KB에서 찾지 못한 것(설계서 7.5절 자료 요청서).

    KB ID로 적힌 근거, KB 설명과 비슷한 근거는 있는 것으로 본다. '실적·인력·인증' 근거는 그 종류의 KB 항목에
    근거의 고유한 낱말(예: '클라우드 전환 실적'의 '클라우드')이 나와야 있는 것으로 본다.
    """
    known_ids = {e.id for coll in (kb.facts, kb.projects, kb.people, kb.certifications, kb.content) for e in coll}
    labels = [f.label for f in kb.facts] + [k.title for k in kb.content]
    by_kind = {
        "실적": " ".join(f"{p.name} {p.client} {' '.join(p.tech)}" for p in kb.projects) if kb.projects else None,
        "인력": " ".join(f"{h.role} {h.grade} {' '.join(h.skills)} {' '.join(h.certs)}" for h in kb.people) if kb.people else None,
        "인증": " ".join(c.name for c in kb.certifications) if kb.certifications else None,
    }
    out: list[DataRequest] = []
    for plan in sb.sections:
        for need in plan.needed_facts:
            token = need.split()[0].strip("()[],")
            if token in known_ids:
                continue
            if any(similarity(need, label) >= 0.5 for label in labels):
                continue
            satisfied = False
            for kind, corpus in by_kind.items():
                if kind in need and corpus is not None:
                    terms = _specific_terms(need)
                    satisfied = not terms or any(t in corpus for t in terms)
                    break
            if satisfied:
                continue
            out.append(DataRequest(section_id=plan.section_id, section_title=f"{plan.number} {plan.title}", need=need,
                                   reason="스토리보드가 요구하지만 KB에 없음"))
    return merge_requests(out)


# RFP에 있는 내용(원문·요구사항 목록·규격)은 회사에 요청할 자료가 아니다: 생성기가 RFP를 갖고 있다
_RFP_NEED = re.compile(r"RFP|원문|제안\s*요청서|과업\s*지시서|[A-Z]{3}-\d{2,4}|\b[A-Z]{3}\s*\d+\s*건")
# 분류는 위에서부터 맞춘다('투입 인력의 수행 경험'은 인력). '발주기관 확인'은 회사 자료가 아니라 질의·설명회로 확인할 것
_CATEGORIES = [
    ("발주기관 확인", re.compile(r"발주\s*기관|현행|대상\s*(기관|인원|산출물)|연계\s*대상|제공\s*자원|오픈\s*(목표\s*)?일|범위\s*구분|제외\s*범위|로드맵"
                              r"|보안\s*지침|개발\s*표준|설명회|인계")),
    ("인력", re.compile(r"인력|PM|PL|전문가|경력|투입|이력")),
    ("실적", re.compile(r"실적|수행\s*경험|사례|레퍼런스|유사\s*사업")),
    ("인증", re.compile(r"인증|GS|CC|ISMS|ISO|CMMI|특허")),
    ("재무", re.compile(r"매출|자본금|신용|재무")),
    ("회사", re.compile(r"설립|연혁|조직도|일반\s*현황|공동\s*수급|지분|중소기업|하도급")),
    ("기술", re.compile(r"방법론|도구|솔루션|제품|규격|프레임워크|아키텍처|플랫폼")),
]
_CATEGORY_ORDER = ["실적", "인력", "인증", "재무", "회사", "기술", "기타", "발주기관 확인"]


# 초안의 [확인 필요] 중 발주기관만 답할 수 있는 것(목표치·기준·범위·현황·용량·연계 규격 등). 회사 쪽 내용은 뺀다.
_COMPANY_TOPIC = re.compile(r"당사|제안사|인력|PM|PL|경력|실적|인증|자격|투입|이력|조직|매출|차별화|win\s*theme")
_AGENCY_TOPIC = re.compile(r"발주\s*기관|현행|목표\s*(치|값|수준)?|측정\s*(기준|조건)|기준|범위|규격|한도|보관\s*기간|대상|연계"
                           r"|일정|기간|현황|용량|형식|지침|표준")


def is_agency_topic(topic: str) -> bool:
    return not _COMPANY_TOPIC.search(topic) and bool(_AGENCY_TOPIC.search(topic))


def draft_questions(drafts: list[SectionDraft], sb: Storyboard | None) -> list[tuple[str, str]]:
    """(절, 확인할 내용): LLM 절 초안의 [확인 필요] 중 발주기관에 물을 것과 스토리보드의 '발주기관 확인' 자료 요청.
    표현만 다른 것은 하나로 묶는다."""
    out: list[tuple[str, str]] = []

    def add(where: str, topic: str) -> None:
        if topic and not any(similar_topic(topic, t) for _, t in out):
            out.append((where, topic))

    for d in drafts:
        if d.origin != "llm":
            continue
        for topic in open_items(d.placeholders):
            if is_agency_topic(topic):
                add(f"{d.number} {d.title}", topic)
    for r in (sb.data_requests if sb else []):
        if r.category == "발주기관 확인":
            add(r.section_title, r.need)
    return out


def _category(need: str) -> str:
    return next((c for c, pat in _CATEGORIES if pat.search(need)), "기타")


def merge_requests(requests: list[DataRequest], threshold: float = 0.35) -> list[DataRequest]:
    """자료 요청을 정리한다: RFP에 있는 내용은 빼고, 같은 분류에서 비슷한 요청(문자 2-gram 유사도)을 한 줄로 묶어
    요청한 절을 함께 적는다. 분류 순서, 같은 분류 안에서는 여러 절이 요청한 것부터."""
    merged: list[DataRequest] = []
    for r in requests:
        need = re.sub(r"\s*\[확인 필요[^\]]*\]\s*", " ", r.need).strip()
        if not need or _RFP_NEED.search(need):
            continue
        cat = _category(need)
        hit = next((m for m in merged if m.category == cat and similarity(m.need, need) >= threshold), None)
        if hit is None:
            merged.append(r.model_copy(update={"need": need, "category": cat, "sections": [r.section_title]}))
        elif r.section_title not in hit.sections:
            hit.sections.append(r.section_title)
    for m in merged:
        m.section_title = ", ".join(m.sections)
        if m.category == "발주기관 확인":
            m.reason = "회사 자료가 아님 — 발주기관 질의·제안요청 설명회로 확인"
        if len(m.sections) > 1:
            m.reason += f"(절 {len(m.sections)}곳)"
    return sorted(merged, key=lambda m: (_CATEGORY_ORDER.index(m.category), -len(m.sections)))


# ---- 절 초안 ---------------------------------------------------------------------------------


class BlockOut(BaseModel):
    kind: Literal["para", "bullets", "table", "callout", "note"]
    text: str
    level: int
    items: list[str]
    table_header: list[str]
    table_rows: list[list[str]]
    req_refs: list[str]


class ResponseOut(BaseModel):
    req_id: str
    response: str
    acceptance: Literal["수용", "부분수용", "대안제시", "미정"]


class SectionOut(BaseModel):
    head_message: str
    blocks: list[BlockOut]
    responses: list[ResponseOut]
    missing_info: list[str]


def skeleton_section(inp: DraftInputs, node: OutlineNode) -> SectionDraft:
    plan = inp.storyboard.plan(node.id) if inp.storyboard else None
    d = SectionDraft(section_id=node.id, number=node.number, title=node.title, origin="skeleton")
    d.head_message = (plan.head_message if plan and plan.head_message
                      else "[확인 필요: 이 절의 결론 한 문장(거버닝 메시지)]")
    for q in node.checklist or (plan.key_points if plan else []):
        d.blocks.append(DraftBlock(kind="bullets", level=0, items=[q]))
        d.blocks.append(DraftBlock(kind="bullets", level=1, items=["[확인 필요: 위 평가 질문에 대한 대응 내용]"]))
    if plan and plan.key_points and node.checklist:
        d.blocks.append(DraftBlock(kind="bullets", level=0, items=["핵심 내용(스토리보드)"]))
        d.blocks.append(DraftBlock(kind="bullets", level=1, items=list(plan.key_points)))
    if plan and plan.needed_facts:
        d.blocks.append(DraftBlock(kind="note", text="필요 근거: " + ", ".join(plan.needed_facts)))
    reuse = relevant_content(inp.kb, node)
    if reuse:
        d.blocks.append(DraftBlock(kind="note", text="[검토 필요: 재사용 후보 — "
                                   + "; ".join(f"{k.title}({k.source})" for k in reuse[:3]) + "]"))
    for rid in node.requirements:
        r = inp.requirement_index.get(rid)
        name = r.name if r else rid
        d.responses.append(RequirementResponse(req_id=rid, response=f"[확인 필요: {name} 대응 방안]", acceptance="미정"))
    if not d.blocks and not d.responses:
        d.blocks.append(DraftBlock(kind="para", text="[확인 필요: 본문]"))
    apply_tokens(d, inp.kb)
    return d


def _section_from(inp: DraftInputs, node: OutlineNode, out: SectionOut, request_id: str | None) -> SectionDraft:
    d = SectionDraft(section_id=node.id, number=node.number, title=node.title, origin="llm",
                     head_message=out.head_message.strip())
    for b in out.blocks:
        if b.kind == "table" and b.table_header:
            width = len(b.table_header)
            rows = [(r + [""] * width)[:width] for r in b.table_rows]
            d.blocks.append(DraftBlock(kind="table", table=TableSpec(header=b.table_header, rows=rows), req_refs=b.req_refs))
        elif b.kind == "bullets":
            items = [i.lstrip("□○◦-·•※ ").strip() for i in b.items if i.strip()] or ([b.text] if b.text else [])
            d.blocks.append(DraftBlock(kind="bullets", level=max(0, min(b.level, 3)), items=items, req_refs=b.req_refs))
        elif b.text.strip():
            d.blocks.append(DraftBlock(kind=b.kind if b.kind != "table" else "para", text=b.text.strip(), req_refs=b.req_refs))
    got = {r.req_id: r for r in out.responses}
    for rid in node.requirements:
        r = got.get(rid)
        if r is not None and r.response.strip():
            d.responses.append(RequirementResponse(req_id=rid, response=r.response.strip(), acceptance=r.acceptance))
        else:
            name = inp.requirement_index[rid].name if rid in inp.requirement_index else rid
            d.responses.append(RequirementResponse(req_id=rid, response=f"[확인 필요: {name} 대응 방안]", acceptance="미정"))
    # missing_info는 본문에 이미 [확인 필요: …]로 적은 것을 표현만 바꿔 되풀이하는 경우가 많다(예제 실측: 절당 최대
    # 11곳 중 5곳이 중복). 본문 자리표시와 비슷하면 다시 넣지 않는다.
    present = [placeholder_topic(x) for x in PLACEHOLDER.findall(d.all_text())]
    for m in out.missing_info:
        m = m.strip()
        if not m or any(similar_topic(m, t) for t in present):
            continue
        d.blocks.append(DraftBlock(kind="note", text=f"[확인 필요: {m}]"))
        present.append(m)
    if request_id:
        d.llm_call_ids.append(request_id)
    apply_tokens(d, inp.kb)
    return d


@dataclass
class _FirstPass:
    """절 초안 1차 호출 결과(분량 보강에 다시 쓴다)."""

    draft: SectionDraft
    out: SectionOut
    context: str
    section: str


def _section_call(inp: DraftInputs, node: OutlineNode, gateway: LLMGateway, profile: Profile,
                  share_kb: bool) -> _FirstPass:
    spec = profile.value("llm.tasks")["section"]
    # 고정 접두부(캐시): RFP 요약(+ KB 카탈로그). 가변부: 이 절의 정보와 작업 지시.
    context = rfp_brief(inp) + ("\n" + kb_catalog(inp.kb) if share_kb else "")
    section = section_text(inp, node, include_kb_content=share_kb)
    # 사고 토큰도 상한에 들어간다: 요구사항 수로 줄이면 잘린다(2026-11-17 실측, 8K에서 3절 중 2절 잘림)
    out, reply = gateway.run(LLMCall(task="draft.section", system=SYSTEM_WRITER, context=context,
                                     instruction=section + "\n\n" + SECTION_INSTRUCTION, schema=SectionOut,
                                     effort=spec["effort"], max_tokens=int(spec["max_tokens"]),
                                     data_class="internal" if share_kb else "public"), SectionOut)
    return _FirstPass(_section_from(inp, node, out, reply.request_id), out, context, section)


def _maybe_expand(inp: DraftInputs, node: OutlineNode, gateway: LLMGateway, profile: Profile, share_kb: bool,
                  fp: _FirstPass) -> SectionDraft:
    """분량 보강: 목표 최소 글자 수의 expand_below 배보다 짧으면 1차 초안을 주고 한 번 더 쓰게 한다
    (2026-11-18 예제 실측: 목표 글자 수를 줘도 65%에 그친 절이 있었다). 길어졌을 때만 바꾸고, 실패하면 1차 초안."""
    spec = profile.value("llm.tasks")["section"]
    d = fp.draft
    target = next((ln.target_chars for ln in inp.budget.lines if ln.node_id == node.id), [])
    ratio = float(spec.get("expand_below", 0) or 0)
    if not (target and ratio and d.est_chars < target[0] * ratio):
        return d
    instruction = (fp.section + f"\n\n<draft>\n{fp.out.model_dump_json()}\n</draft>\n\n"
                   + EXPAND_INSTRUCTION.format(current=d.est_chars, minimum=target[0], maximum=target[1]))
    try:
        out2, reply2 = gateway.run(LLMCall(task="draft.section.expand", system=SYSTEM_WRITER, context=fp.context,
                                           instruction=instruction, schema=SectionOut, effort=spec["effort"],
                                           max_tokens=int(spec["max_tokens"]),
                                           data_class="internal" if share_kb else "public"), SectionOut)
    except LLMError:
        return d
    d2 = _section_from(inp, node, out2, reply2.request_id)
    if d2.est_chars > d.est_chars:
        d2.llm_call_ids = d.llm_call_ids + d2.llm_call_ids
        return d2
    return d


def llm_section(inp: DraftInputs, node: OutlineNode, gateway: LLMGateway, profile: Profile, share_kb: bool) -> SectionDraft:
    return _maybe_expand(inp, node, gateway, profile, share_kb, _section_call(inp, node, gateway, profile, share_kb))


def write_sections(inp: DraftInputs, gateway: LLMGateway | None, profile: Profile, share_kb: bool,
                   only: set[str] | None, errors: list[str]) -> list[SectionDraft]:
    """배점이 큰 절부터 쓴다. LLM이면 첫 절의 1차 호출만 혼자 보내 공통 접두부(RFP 요약) 캐시를 만들고 인증·모델
    문제를 먼저 드러낸 뒤, 그 절의 분량 보강과 나머지 절은 llm.tasks.section.parallel 개씩 동시에 보낸다
    (2026-11-18 예제 실측: 첫 절 보강까지 혼자 기다리면 동시 실행이 6분 늦게 시작됐다). 결과·오류 순서는 고정."""
    nodes = [n for n in leaf_sections(inp.outline) if only is None or n.id in only]
    order = sorted(nodes, key=lambda n: -n.points)
    if gateway is None or not order:
        return [skeleton_section(inp, n) for n in nodes]
    llm = gateway

    def one(node: OutlineNode) -> tuple[SectionDraft, LLMError | None]:
        try:
            return llm_section(inp, node, llm, profile, share_kb), None
        except LLMError as exc:
            return skeleton_section(inp, node), exc

    drafts: dict[str, SectionDraft] = {}
    first, rest = order[0], order[1:]
    jobs: list[tuple[OutlineNode, object]] = []
    try:
        fp = _section_call(inp, first, llm, profile, share_kb)
        jobs.append((first, lambda: (_maybe_expand(inp, first, llm, profile, share_kb, fp), None)))
    except LLMError as exc:
        drafts[first.id] = skeleton_section(inp, first)
        errors.append(f"{first.number} {first.title}: {exc}")
        if "인증" in str(exc) or "모델을 정하지 못했" in str(exc):
            for n in rest:                                       # 남은 절은 골격으로
                drafts[n.id] = skeleton_section(inp, n)
            return [drafts[n.id] for n in nodes]
    jobs += [(n, (lambda n=n: one(n))) for n in rest]
    workers = max(1, int(profile.value("llm.tasks")["section"].get("parallel", 1) or 1))
    if workers == 1:
        results = [job() for _, job in jobs]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(job) for _, job in jobs]
            results = [f.result() for f in futures]
    for (node, _), (draft, err) in zip(jobs, results, strict=True):
        drafts[node.id] = draft
        if err is not None:
            errors.append(f"{node.number} {node.title}: {err}")
    return [drafts[n.id] for n in nodes]

