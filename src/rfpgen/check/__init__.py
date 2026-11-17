"""제출 전 점검(설계서 7.8절) — M2 범위의 결정적 규칙.

렌더 쪽수(PAGE-001)는 M3의 PDF 렌더 뒤에 정확히 잰다. M2에서는 글자 수로 추정하고 그 사실을 표시한다.
기준값이 원문 미대조(provisional) 프로필 값에만 의존하면 심각도를 한 단계 낮춘다(blocker→major).
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from ..draft.tokens import PLACEHOLDER, numbers
from ..profile import Profile
from ..schemas.draft import CheckFinding, CheckReport, SectionDraft
from ..schemas.kb import CompanyKB
from ..schemas.plan import Outline, PageBudget, Trace
from ..schemas.rfp import Rfp

_DOWNGRADE = {"blocker": "major", "major": "minor", "minor": "minor", "info": "info"}
_DISPARAGE = re.compile(r"타사|경쟁사|[A-Z가-힣]사\s*대비|기존\s*업체의?\s*(?:문제|한계|실패)|타\s*업체")
_SUPERLATIVE = re.compile(r"최고|최초|유일|완벽|100\s*%\s*(?:보장|만족|달성)|무결점|절대")


def _f(report: CheckReport, rule: str, severity: str, message: str, *, section: str | None = None,
       basis: str = "", provisional: bool = False) -> None:
    sev = _DOWNGRADE[severity] if provisional else severity
    report.findings.append(CheckFinding(rule=rule, severity=sev, message=message, section_id=section,  # type: ignore[arg-type]
                                        basis=basis, provisional=provisional))


def run_checks(*, rfp: Rfp, outline: Outline, budget: PageBudget, trace: Trace, drafts: list[SectionDraft],
               kb: CompanyKB, profile: Profile, blind: bool, hwpx_path: Path | None, run_id: str) -> CheckReport:
    rep = CheckReport(run_id=run_id)
    by_id = {d.section_id: d for d in drafts}
    nodes = {n.id: n for n in outline.walk()}

    # COV-001: 요구사항마다 비어 있지 않은 대응 방안
    responded = {r.req_id for d in drafts for r in d.responses if r.response and not PLACEHOLDER.search(r.response)}
    mapped = [row for row in trace.rows if row.status != "unmapped"]
    missing = [row.req_id for row in trace.rows if row.req_id not in responded]
    if missing:
        _f(rep, "COV-001", "blocker", f"대응 방안이 없거나 [확인 필요]인 요구사항 {len(missing)}건: {', '.join(missing[:15])}"
           + (" …" if len(missing) > 15 else ""), basis="추적표 커버리지 100% 게이트(설계서 D2)")
    unmapped = [row.req_id for row in trace.rows if row.status == "unmapped"]
    if unmapped:
        _f(rep, "COV-001", "blocker", f"목차에 연결되지 않은 요구사항 {len(unmapped)}건: {', '.join(unmapped[:15])}",
           basis="추적표")
    rep.stats["requirements"] = len(trace.rows)
    rep.stats["requirements_responded"] = len([r for r in mapped if r.req_id in responded])

    # COV-002: 정성 평가항목마다 초안이 있는 절
    for item in rfp.evaluation.qualitative_items():
        holders = [n for n in nodes.values() if item.id in n.eval_items]
        drafted = [n for n in holders if n.id in by_id or any(c.id in by_id for c in n.children)]
        if not drafted:
            _f(rep, "COV-002", "blocker", f"평가항목 '{item.name}'에 대응하는 초안 절이 없습니다", basis="평가표")

    # TOC-001: 지정 목차와 출력 장 제목 일치
    toc = rfp.guideline.prescribed_toc
    if toc is not None and outline.origin == "prescribed":
        want = [f"{c.number}.{c.title}".replace(" ", "") for c in toc.value]
        got = [f"{c.number}{c.title}".replace(" ", "") for c in outline.chapters]
        if want != got:
            _f(rep, "TOC-001", "blocker", "지정 목차와 장 번호·제목이 다릅니다", basis="RFP 작성지침")

    # PAGE-003·PAGE-001(추정): 절별 목표 글자 수와 전체 쪽수
    eff = max(budget.effective_chars_per_page, 1)
    targets = {ln.node_id: ln.target_chars for ln in budget.lines}
    est_pages = 0.0
    for d in drafts:
        tgt = targets.get(d.section_id)
        n_tables = sum(1 for b in d.blocks if b.kind == "table") + (1 if d.responses else 0)
        est = d.est_chars / eff + 0.25 * n_tables + 0.2
        est_pages += est
        if tgt and d.origin != "skeleton":
            if d.est_chars < tgt[0]:
                _f(rep, "PAGE-003", "minor", f"{d.number} {d.title}: {d.est_chars:,}자 — 목표 {tgt[0]:,}~{tgt[1]:,}자보다 적음",
                   section=d.section_id, basis="쪽수 예산")
            elif d.est_chars > tgt[1]:
                _f(rep, "PAGE-003", "minor", f"{d.number} {d.title}: {d.est_chars:,}자 — 목표 {tgt[0]:,}~{tgt[1]:,}자보다 많음",
                   section=d.section_id, basis="쪽수 예산")
    est_pages += 2  # 표지·장 구분
    rep.stats["estimated_pages"] = round(est_pages, 1)
    limit = budget.main_page_limit
    provisional_limit = budget.main_page_limit_source.startswith("프로필")
    if est_pages > limit:
        _f(rep, "PAGE-001", "blocker", f"추정 쪽수 {est_pages:.0f}쪽이 본문 상한 {limit}쪽을 넘습니다(글자 수 기반 추정 — M3 렌더로 확정)",
           basis=budget.main_page_limit_source, provisional=provisional_limit)

    # FACT-001·002·003
    for d in drafts:
        if d.placeholders:
            _f(rep, "FACT-001", "blocker", f"{d.number} {d.title}: [확인 필요] 자리표시자 {len(d.placeholders)}개", section=d.section_id,
               basis="허위 기재 방지(원칙 P2)")
        if d.unresolved_tokens:
            _f(rep, "FACT-001", "blocker", f"{d.number} {d.title}: KB에 없는 토큰 {', '.join(d.unresolved_tokens)}",
               section=d.section_id, basis="KB")
    rfp_text = " ".join([r.definition + " " + " ".join(r.details) for r in rfp.requirements]
                        + [c for it in rfp.evaluation.items() for c in it.criteria]
                        + [rfp.notice.period.value if rfp.notice.period else ""])
    kb_values = " ".join(kb.resolve(x) or "" for x in [f.id for f in kb.facts]
                         + [f"{p.id}.{fld}" for p in kb.projects for fld in ("amount_krw", "start", "end")]
                         + [f"{h.id}.years" for h in kb.people])
    allowed = re.sub(r"\s+", "", rfp_text + " " + kb_values)
    for d in drafts:
        if d.origin == "skeleton":
            continue
        unsupported = sorted({n for n in numbers(d.all_text()) if re.sub(r"\s+", "", n) not in allowed})
        if unsupported:
            _f(rep, "FACT-002", "major", f"{d.number} {d.title}: 근거(KB·RFP)를 찾지 못한 수치 {', '.join(unsupported[:8])}",
               section=d.section_id, basis="원칙 P2")
    expired = kb.expired()
    if expired:
        _f(rep, "FACT-003", "major", f"유효기간이 지난 KB 항목: {', '.join(expired)}", basis="KB")

    # BLD-001·003: 회사 식별어(블라인드면 blocker, 아니어도 정보)
    terms = kb.identity.terms()
    if terms:
        for d in drafts:
            hits = sorted({t for t in terms if t.lower() in d.all_text().lower()})
            if hits:
                _f(rep, "BLD-001", "blocker" if blind else "info",
                   f"{d.number} {d.title}: 회사 식별 표기 {', '.join(hits)}", section=d.section_id, basis="블라인드 평가")
        if hwpx_path is not None and hwpx_path.exists():
            with zipfile.ZipFile(hwpx_path) as zf:
                for name in zf.namelist():
                    if not name.endswith((".xml", ".hpf", ".rdf")) or name.startswith("Contents/section"):
                        continue
                    data = zf.read(name).decode("utf-8", errors="ignore").lower()
                    found = sorted({t for t in terms if t.lower() in data})
                    if found:
                        _f(rep, "BLD-003", "blocker" if blind else "info", f"파일 정보({name})에 회사 식별 표기 {', '.join(found)}",
                           basis="블라인드 평가")
            if any(t.lower() in hwpx_path.stem.lower() for t in terms):
                _f(rep, "BLD-003", "blocker" if blind else "info", f"파일 이름에 회사 식별 표기: {hwpx_path.name}", basis="블라인드 평가")
    elif blind:
        _f(rep, "BLD-001", "major", "KB identity(회사명 등)가 비어 있어 블라인드 점검을 할 수 없습니다", basis="KB")

    # LANG-001·003
    for d in drafts:
        text = d.all_text()
        m = _DISPARAGE.search(text)
        if m:
            _f(rep, "LANG-001", "major", f"{d.number} {d.title}: 타사 비방·비교로 읽힐 수 있는 표현 '{m.group(0)}'",
               section=d.section_id, basis="조달청 세부기준(비방 불이익)")
        s = sorted(set(_SUPERLATIVE.findall(text)))
        if s:
            _f(rep, "LANG-003", "minor", f"{d.number} {d.title}: 근거 없는 단정 표현 {', '.join(s)}", section=d.section_id,
               basis="허위 기재 위험")

    # HWPX-001: 패키지·구조 검증(python-hwpx)
    if hwpx_path is not None and hwpx_path.exists():
        try:
            from hwpx import HwpxDocument
            from hwpx.tools.package_validator import validate_package

            issues = list(HwpxDocument.open(str(hwpx_path)).validate().issues)
            pkg = validate_package(hwpx_path)
            errors = issues + list(getattr(pkg, "errors", []) or [])
            warnings = list(getattr(pkg, "warnings", []) or [])
            if errors:
                _f(rep, "HWPX-001", "blocker", f"HWPX 검증 오류 {len(errors)}건: "
                   + "; ".join(str(i)[:80] for i in errors[:5]), basis="출력 품질")
            if warnings:
                _f(rep, "HWPX-001", "info", f"HWPX 검증 경고 {len(warnings)}건(python-hwpx 기본 문서에도 있는 경고 포함): "
                   + "; ".join(str(i)[:80] for i in warnings[:3]), basis="출력 품질")
        except Exception as exc:  # 검증기 자체 오류는 정보로만 남긴다
            _f(rep, "HWPX-001", "info", f"HWPX 검증을 실행하지 못했습니다: {exc}", basis="출력 품질")

    del profile
    rep.stats.update({"blocker": rep.count("blocker"), "major": rep.count("major"), "minor": rep.count("minor")})
    return rep


def report_markdown(rep: CheckReport) -> str:
    icon = {"blocker": "🔴 blocker", "major": "🟠 major", "minor": "🟡 minor", "info": "ℹ️ info"}
    lines = [f"# 제출 전 점검 — {rep.run_id}", "",
             f"blocker {rep.count('blocker')} · major {rep.count('major')} · minor {rep.count('minor')} · "
             f"추정 쪽수 {rep.stats.get('estimated_pages', '?')}쪽", "",
             "> blocker가 0이어야 제출 승인(G5)을 할 수 있습니다. 쪽수는 M2에서 글자 수로 추정한 값입니다.", ""]
    order = ["blocker", "major", "minor", "info"]
    for f in sorted(rep.findings, key=lambda f: order.index(f.severity)):
        prov = " _(기준 원문 미대조로 한 단계 낮춤)_" if f.provisional else ""
        lines.append(f"- {icon[f.severity]} `{f.rule}` {f.message}{prov}")
    if not rep.findings:
        lines.append("- 점검 항목 없음")
    lines.append("")
    return "\n".join(lines)


__all__ = ["report_markdown", "run_checks"]
