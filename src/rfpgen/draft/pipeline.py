"""M2 파이프라인: 계획(outline·budget·trace) + KB → 스토리보드 → 절 초안 → HWPX → 제출 전 점검."""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..check import report_markdown, run_checks
from ..kb import load_kb
from ..llm import LLMError, LLMGateway
from ..profile import Profile
from ..render.hwpx_writer import load_style, render_proposal
from ..report.xlsx import write_trace_workbook
from ..schemas.draft import CheckReport, SectionDraft, Storyboard
from ..schemas.kb import CompanyKB
from ..schemas.plan import Outline, PageBudget, Trace
from ..schemas.rfp import Rfp
from .context import DraftInputs
from .tokens import PLACEHOLDER
from .write import data_requests, llm_storyboard, skeleton_storyboard, write_sections


@dataclass
class DraftResult:
    project: Path
    storyboard: Storyboard
    drafts: list[SectionDraft]
    check: CheckReport
    outputs: dict[str, Path] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    llm_usage: dict[str, int] = field(default_factory=dict)


def _latest(project: Path, pattern: str) -> Path:
    found = sorted(project.glob(pattern), key=lambda p: int(re.search(r"v(\d+)", p.name).group(1)))  # type: ignore[union-attr]
    if not found:
        raise FileNotFoundError(f"{project}: {pattern}가 없습니다 — 먼저 `rfpgen analyze`를 실행하세요")
    return found[-1]


def storyboard_markdown(sb: Storyboard) -> str:
    lines = ["# 스토리보드(G3 검토용)", "",
             f"> 생성: {sb.origin}. `storyboard.json`을 고친 뒤 `rfpgen draft`를 다시 실행하면 고친 내용으로 초안을 씁니다.", "",
             "## 차별화 메시지(win theme)", ""]
    lines += [f"{i}. {w}" for i, w in enumerate(sb.win_themes, start=1)] or ["- (없음)"]
    lines.append("")
    for p in sb.sections:
        lines += [f"## {p.number} {p.title} ({p.page_budget}쪽" + (f", 목표 {p.target_chars[0]:,}~{p.target_chars[1]:,}자)" if p.target_chars else ")"), ""]
        lines.append(f"- 거버닝 메시지: {p.head_message or '[작성 필요]'}")
        if p.key_points:
            lines.append("- 핵심 내용: " + " / ".join(p.key_points))
        if p.needed_facts:
            lines.append("- 필요 근거: " + ", ".join(p.needed_facts))
        if p.requirements:
            lines.append(f"- 요구사항 {len(p.requirements)}건: " + ", ".join(p.requirements[:12]) + (" …" if len(p.requirements) > 12 else ""))
        lines.append("")
    if sb.data_requests:
        lines += ["## 자료 요청", ""]
        lines += [f"- [{d.section_title}] {d.need}" for d in sb.data_requests]
        lines.append("")
    return "\n".join(lines)


def run_draft(project: Path, profile: Profile, *, kb_dir: Path | None = None, provider=None, share_kb: bool = False,
              sections: set[str] | None = None, refresh_storyboard: bool = False, style_path: Path | None = None) -> DraftResult:
    project = Path(project)
    rfp = Rfp.model_validate_json(_latest(project, "rfp/rfp.v*.json").read_text(encoding="utf-8"))
    outline = Outline.model_validate_json((project / "plan" / "outline.json").read_text(encoding="utf-8"))
    budget = PageBudget.model_validate_json((project / "plan" / "budget.json").read_text(encoding="utf-8"))
    trace = Trace.model_validate_json((project / "plan" / "trace.json").read_text(encoding="utf-8"))
    kb = load_kb(kb_dir) if kb_dir else CompanyKB()
    title = rfp.notice.title.value if rfp.notice.title else project.name
    blind = bool(rfp.guideline.blind and rfp.guideline.blind.value)
    inp = DraftInputs(rfp=rfp, outline=outline, budget=budget, trace=trace, kb=kb, title=title, blind=blind)
    notes: list[str] = []
    gateway = LLMGateway(provider, audit_path=project / "audit" / "llm_calls.jsonl") if provider is not None else None

    # 스토리보드(G3): 사람이 고친 파일이 있으면 그대로 쓴다
    sb_path = project / "strategy" / "storyboard.json"
    if sb_path.exists() and not refresh_storyboard:
        sb = Storyboard.model_validate_json(sb_path.read_text(encoding="utf-8"))
        notes.append("기존 스토리보드(storyboard.json)를 사용했습니다")
    elif gateway is not None:
        try:
            sb = llm_storyboard(inp, gateway, profile, share_kb)
        except LLMError as exc:
            notes.append(f"LLM 스토리보드 실패 — 골격으로 대신함: {exc}")
            sb = skeleton_storyboard(inp)
            if "인증" in str(exc) or "모델을 정하지 못했" in str(exc):
                gateway = None
    else:
        sb = skeleton_storyboard(inp)
    sb.data_requests = data_requests(sb, kb)
    inp.storyboard = sb
    sb_path.parent.mkdir(parents=True, exist_ok=True)
    sb_path.write_text(sb.model_dump_json(indent=2), encoding="utf-8")
    (project / "strategy" / "storyboard.md").write_text(storyboard_markdown(sb), encoding="utf-8")

    # 절 초안(G4)
    errors: list[str] = []
    drafts = write_sections(inp, gateway, profile, share_kb, sections, errors)
    notes += [f"LLM 절 생성 실패 — 골격으로 대신함: {e}" for e in errors]
    sec_dir = project / "sections"
    sec_dir.mkdir(parents=True, exist_ok=True)
    for d in drafts:
        prev = [int(m.group(1)) for p in sec_dir.glob(f"{d.section_id}.v*.json") if (m := re.search(r"\.v(\d+)\.json$", p.name))]
        d.version = max(prev, default=0) + 1
        (sec_dir / f"{d.section_id}.v{d.version}.json").write_text(d.model_dump_json(indent=2), encoding="utf-8")
    # 일부 절만 다시 쓴 경우 나머지는 최신 저장본을 쓴다
    if sections is not None:
        have = {d.section_id for d in drafts}
        for p in sorted(sec_dir.glob("*.v*.json")):
            sid = p.name.split(".v")[0]
            if sid in have:
                continue
            latest = _latest(sec_dir, f"{sid}.v*.json")
            drafts.append(SectionDraft.model_validate_json(latest.read_text(encoding="utf-8")))
            have.add(sid)
        order = {n.id: i for i, n in enumerate(outline.walk())}
        drafts.sort(key=lambda d: order.get(d.section_id, 10**6))

    # 추적표 갱신: 대응 방안과 상태
    responses = {r.req_id: r for d in drafts for r in d.responses}
    for row in trace.rows:
        r = responses.get(row.req_id)
        if r is None:
            continue
        row.summary = r.response
        row.acceptance = r.acceptance
        if not PLACEHOLDER.search(r.response) and row.status in ("mapped", "drafted"):
            row.status = "drafted"
    (project / "plan" / "trace.json").write_text(trace.model_dump_json(indent=2), encoding="utf-8")

    # 렌더: 파일 이름에 회사명을 쓰지 않는다
    style = load_style(style_path)
    out_path = project / "out" / "proposal.hwpx"
    g = rfp.guideline
    render_proposal(out_path, outline, drafts, title=title, blind=blind, style=style,
                    min_body_pt=g.min_font_pt.value if g.min_font_pt else None,
                    min_table_pt=g.table_min_font_pt.value if g.table_min_font_pt else None,
                    requirement_names={r.id: r.name for r in rfp.requirements})
    trace_xlsx = project / "out" / "trace_draft.xlsx"
    write_trace_workbook(trace_xlsx, outline, trace, sb.data_requests)

    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = run_checks(rfp=rfp, outline=outline, budget=budget, trace=trace, drafts=drafts, kb=kb, profile=profile,
                        blind=blind, hwpx_path=out_path, run_id=run_id)
    check_dir = project / "checks"
    check_dir.mkdir(parents=True, exist_ok=True)
    (check_dir / f"{run_id}.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (check_dir / f"{run_id}.md").write_text(report_markdown(report), encoding="utf-8")

    usage = {}
    if gateway is not None or provider is not None:
        u = (gateway.usage if gateway is not None else None)
        if u is not None:
            usage = {"calls": u.calls, "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                     "cache_read_input_tokens": u.cache_read_input_tokens}
    return DraftResult(project=project, storyboard=sb, drafts=drafts, check=report, notes=notes, llm_usage=usage, outputs={
        "proposal": out_path, "storyboard": sb_path, "storyboard_md": project / "strategy" / "storyboard.md",
        "trace_xlsx": trace_xlsx, "check_md": check_dir / f"{run_id}.md", "check_json": check_dir / f"{run_id}.json",
    })
