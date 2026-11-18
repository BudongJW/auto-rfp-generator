"""제출 전 점검(설계서 7.8절) — M2 범위의 결정적 규칙.

렌더 쪽수(PAGE-001)는 M3의 PDF 렌더 뒤에 정확히 잰다. M2에서는 글자 수로 추정하고 그 사실을 표시한다.
기준값이 원문 미대조(provisional) 프로필 값에만 의존하면 심각도를 한 단계 낮춘다(blocker→major).
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from ..diagram.build import project_months
from ..draft.tokens import PLACEHOLDER, numbers, open_items
from ..profile import Profile
from ..schemas.draft import CheckFinding, CheckReport, SectionDraft
from ..schemas.kb import CompanyKB
from ..schemas.plan import Outline, PageBudget, Trace
from ..schemas.rfp import Rfp

_DOWNGRADE = {"blocker": "major", "major": "minor", "minor": "minor", "info": "info"}
_TEXT_H_MM = 247.0      # A4 세로 본문 높이 어림(위 20·아래 15·머리말·꼬리말 제외)
_DISPARAGE = re.compile(r"타사|경쟁사|[A-Z가-힣]사\s*대비|기존\s*업체의?\s*(?:문제|한계|실패)|타\s*업체")
_SUPERLATIVE = re.compile(r"최고|최초|유일|완벽|100\s*%\s*(?:보장|만족|달성)|무결점|절대")


def _f(report: CheckReport, rule: str, severity: str, message: str, *, section: str | None = None,
       basis: str = "", provisional: bool = False) -> None:
    sev = _DOWNGRADE[severity] if provisional else severity
    report.findings.append(CheckFinding(rule=rule, severity=sev, message=message, section_id=section,  # type: ignore[arg-type]
                                        basis=basis, provisional=provisional))


def supported(token: str, corpus: str) -> bool:
    """수치 표현(예: '5건')이 근거 글에 같은 수·단위로 있는지. '15건'의 '5건', '6개월'의 '6개'는 근거가 아니다."""
    tok = re.sub(r"\s+", "", token)
    m = re.match(r"([\d,.]*\d)(.*)", tok)
    if m is None:
        return tok in corpus
    num, unit = m.group(1), m.group(2)
    tail = r"(?!월)" if unit == "개" else ""
    return re.search(r"(?<![\d.,])" + re.escape(num) + r"\s*" + re.escape(unit) + tail, corpus) is not None


def _number_part(token: str) -> str:
    m = re.match(r"\s*([\d,]*\d(?:\.\d+)?)", token)
    return m.group(1).replace(",", "") if m else ""


def rfp_number_sources(rfp: Rfp) -> str:
    """본문 수치의 근거로 인정할 RFP 글: 추출한 값과 원문 인용 전부, 그리고 RFP에서 바로 셀 수 있는 값
    (요구사항 건수, 평가 부문·항목 배점, 사업예산의 억 단위 표기)."""
    parts = [rfp.model_dump_json()]
    by_prefix: dict[str, int] = {}
    for r in rfp.requirements:
        by_prefix[r.prefix or "?"] = by_prefix.get(r.prefix or "?", 0) + 1
    parts += [f"{n}건" for n in {len(rfp.requirements), *by_prefix.values()}]
    for a in rfp.evaluation.areas:
        pts = [a.points] + [it.points for it in a.items]
        parts += [f"{p:g}점" for p in pts if p is not None]
    total = sum(a.points or 0 for a in rfp.evaluation.areas)
    if total:
        parts.append(f"{total:g}점")
    if rfp.notice.budget_krw:
        won = rfp.notice.budget_krw.value
        parts += [f"{won:,}원", f"{won / 1e8:g}억", f"{won / 1e6:g}백만"]
    if rfp.notice.period:                    # 사업기간 안의 개월 수(일정표 '3~6개월')는 계획 값이지 사실 주장이 아니다
        months, assumed = project_months(rfp)
        if assumed is None:
            parts += [f"{m}개월" for m in range(1, months + 1)]
    return " ".join(parts)


def run_checks(*, rfp: Rfp, outline: Outline, budget: PageBudget, trace: Trace, drafts: list[SectionDraft],
               kb: CompanyKB, profile: Profile, blind: bool, hwpx_path: Path | None, run_id: str,
               figures: dict | None = None, source_text: str = "") -> CheckReport:
    """figures: 도식 렌더 결과(diagram.FigureResult, id별). 쪽수 추정과 FIG-* 점검에 쓴다.
    source_text: RFP 원문 발췌(사업 개요 등). 본문 수치의 근거(FACT-002)로 함께 본다."""
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
        for b in d.blocks:                                   # 도식: 실제 높이(없으면 쪽의 1/3)
            if b.kind == "figure" and b.figure is not None:
                fr = (figures or {}).get(b.figure.id)
                est += (fr.height_mm * getattr(fr, "scale", 1.0) + 12) / _TEXT_H_MM if fr else 0.35
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
            items = open_items(d.placeholders)
            _f(rep, "FACT-001", "blocker", f"{d.number} {d.title}: [확인 필요] 자리표시자 {len(d.placeholders)}개"
               + (f"(확인할 내용 {len(items)}가지)" if 0 < len(items) < len(d.placeholders) else ""),
               section=d.section_id, basis="허위 기재 방지(원칙 P2)")
        if d.unresolved_tokens:
            _f(rep, "FACT-001", "blocker", f"{d.number} {d.title}: KB에 없는 토큰 {', '.join(d.unresolved_tokens)}",
               section=d.section_id, basis="KB")
    rfp_text = rfp_number_sources(rfp) + " " + source_text
    kb_values = " ".join(kb.resolve(x) or "" for x in [f.id for f in kb.facts]
                         + [f"{p.id}.{fld}" for p in kb.projects for fld in ("amount_krw", "start", "end")]
                         + [f"{h.id}.years" for h in kb.people])
    allowed = rfp_text + " " + kb_values
    # KB 값은 단위 없이 적힌 것이 있다(인력 경력 '18' → 본문 '{{kb:H-001.years}}년' = '18년'): 수가 같으면 근거로 본다
    kb_numbers = {x.replace(",", "") for x in re.findall(r"\d[\d,]*(?:\.\d+)?", kb_values)}
    for d in drafts:
        if d.origin == "skeleton":
            continue
        unsupported = sorted({n for n in numbers(d.all_text(figures=False))
                              if not supported(n, allowed) and _number_part(n) not in kb_numbers})
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

    # FIG-001·002·003: 도식 렌더·가정·축소
    for fr in (figures or {}).values():
        if fr.png is None:
            _f(rep, "FIG-001", "major",
               f"도식 '{fr.title}'({fr.id})을 그림으로 바꾸지 못해 자리표시 상자를 넣었습니다 — {fr.error[:120]}",
               section=fr.section_id, basis="출력 품질")
        for a in fr.assumptions:
            _f(rep, "FIG-002", "minor", f"도식 '{fr.title}': {a}", section=fr.section_id, basis="원칙 P2")
        if getattr(fr, "scale", 1.0) < 0.98:
            _f(rep, "FIG-003", "major", f"도식 '{fr.title}'이 쪽보다 커서 {fr.scale:.0%}로 줄였습니다 — 그림 속 글자가 "
               "최소 글자 크기보다 작아질 수 있습니다. 스펙을 나누거나 줄이세요", section=fr.section_id, basis="RFP 작성지침")

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
