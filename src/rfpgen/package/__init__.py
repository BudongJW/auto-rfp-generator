"""장표 생성(derive)과 제출 패키지(package) — 설계서 7.7절, 7.10절, M3.

slides : 최신 절 초안·스토리보드 → out/summary.pptx(요약본, A4 가로), out/presentation.pptx(발표자료, 16:9), out/script.md
package: HWPX·PPTX → PDF → 메타데이터 정리 → submission/(문서구분별, 회사명 없는 파일명) + 정확한 쪽수·용량·글꼴 점검
         + 제출 전 점검표. `rfpgen forms`로 채운 별지 서식(out/forms/)은 문서구분별로 묶어 PDF 하나씩 만든다.
         나라장터 업로드는 사람이 한다.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..check import report_markdown
from ..kb import load_kb
from ..profile import Profile
from ..render.hwpx_writer import load_style
from ..render.pdf import (
    Bookmark,
    RenderError,
    clean_pdf,
    converters_available,
    find_heading_pages,
    hwpx_to_pdf,
    inspect_pdf,
    pptx_to_pdf,
)
from ..render.slides import build_specs, render_deck, script_markdown
from ..schemas.draft import CheckFinding, CheckReport, SectionDraft, Storyboard
from ..schemas.kb import CompanyKB
from ..schemas.plan import Outline
from ..schemas.rfp import Rfp

_DOWNGRADE = {"blocker": "major", "major": "minor", "minor": "minor", "info": "info"}


def _latest_rfp(project: Path) -> Rfp:
    found = sorted(project.glob("rfp/rfp.v*.json"), key=lambda p: int(re.search(r"v(\d+)", p.name).group(1)))  # type: ignore[union-attr]
    if not found:
        raise FileNotFoundError(f"{project}: rfp.json이 없습니다 — 먼저 `rfpgen analyze`를 실행하세요")
    return Rfp.model_validate_json(found[-1].read_text(encoding="utf-8"))


def latest_drafts(project: Path, outline: Outline) -> list[SectionDraft]:
    latest: dict[str, tuple[int, Path]] = {}
    for p in (project / "sections").glob("*.v*.json"):
        m = re.match(r"(.+)\.v(\d+)\.json$", p.name)
        if m and (m.group(1) not in latest or int(m.group(2)) > latest[m.group(1)][0]):
            latest[m.group(1)] = (int(m.group(2)), p)
    if not latest:
        raise FileNotFoundError(f"{project}: 절 초안이 없습니다 — 먼저 `rfpgen draft`를 실행하세요")
    order = {n.id: i for i, n in enumerate(outline.walk())}
    drafts = [SectionDraft.model_validate_json(p.read_text(encoding="utf-8")) for _, p in latest.values()]
    return sorted(drafts, key=lambda d: order.get(d.section_id, 10**6))


@dataclass
class SlidesResult:
    summary: Path
    presentation: Path
    script: Path
    summary_slides: int
    presentation_slides: int


def make_slides(project: Path, profile: Profile, *, style_path: Path | None = None) -> SlidesResult:
    rfp = _latest_rfp(project)
    outline = Outline.model_validate_json((project / "plan" / "outline.json").read_text(encoding="utf-8"))
    sb_path = project / "strategy" / "storyboard.json"
    storyboard = Storyboard.model_validate_json(sb_path.read_text(encoding="utf-8")) if sb_path.exists() else None
    drafts = latest_drafts(project, outline)
    title = rfp.notice.title.value if rfp.notice.title else project.name
    style = load_style(style_path)
    g = rfp.guideline
    summary_max = g.summary_page_limit.value if g.summary_page_limit else int(profile.value("page_limits.summary_pages"))
    minutes = g.presentation.value.minutes if g.presentation and g.presentation.value.minutes else None
    pres_max = (g.presentation_page_limit.value if g.presentation_page_limit
                else int(minutes * 1.2) if minutes else 25)
    out = project / "out"
    fig_dir = project / "out" / "figures"
    s_specs = build_specs(rfp, outline, drafts, storyboard, title=title, mode="summary", max_slides=summary_max,
                          figure_dir=fig_dir)
    p_specs = build_specs(rfp, outline, drafts, storyboard, title=title, mode="presentation", max_slides=pres_max,
                          figure_dir=fig_dir)
    n_s = render_deck(out / "summary.pptx", s_specs, style=style, mode="summary", title=title)
    n_p = render_deck(out / "presentation.pptx", p_specs, style=style, mode="presentation", title=title)
    (out / "script.md").write_text(script_markdown(p_specs, rfp, drafts, minutes=minutes, title=title), encoding="utf-8")
    return SlidesResult(out / "summary.pptx", out / "presentation.pptx", out / "script.md", n_s, n_p)


@dataclass
class PackagedDoc:
    doc_type: str
    source: Path
    pdf: Path
    pages: int
    size_bytes: int
    fonts: dict[str, str] = field(default_factory=dict)


@dataclass
class PackageResult:
    docs: list[PackagedDoc]
    check: CheckReport
    checklist: Path
    notes: list[str] = field(default_factory=list)
    crossref: Path | None = None          # 조견표(평가항목별 해당 쪽수) XLSX


def _f(rep: CheckReport, rule: str, severity: str, message: str, *, basis: str = "", provisional: bool = False) -> None:
    rep.findings.append(CheckFinding(rule=rule, severity=_DOWNGRADE[severity] if provisional else severity,  # type: ignore[arg-type]
                                     message=message, basis=basis, provisional=provisional))


def build_package(project: Path, profile: Profile, *, kb_dir: Path | None = None) -> PackageResult:
    project = Path(project)
    rfp = _latest_rfp(project)
    title = rfp.notice.title.value if rfp.notice.title else project.name
    g = rfp.guideline
    blind = bool(g.blind and g.blind.value)
    kb = load_kb(kb_dir) if kb_dir else CompanyKB()
    sources = [("정성제안서", project / "out" / "proposal.hwpx"), ("제안요약서", project / "out" / "summary.pptx"),
               ("발표자료", project / "out" / "presentation.pptx")]
    avail = converters_available()
    sub = project / "submission"
    raw_pdf = project / "out" / "pdf"
    sub.mkdir(parents=True, exist_ok=True)
    for old in sub.glob("*.pdf"):
        old.unlink()
    docs: list[PackagedDoc] = []
    notes: list[str] = []
    crossref: Path | None = None
    for old in sub.glob("조견표.*"):
        old.unlink()
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rep = CheckReport(run_id=f"package-{run_id}")
    for i, (doc_type, src) in enumerate(sources, start=1):
        if not src.exists():
            continue
        raw = raw_pdf / f"{src.stem}.pdf"
        try:
            if src.suffix == ".hwpx":
                hwpx_to_pdf(src, raw)
            else:
                pptx_to_pdf(src, raw)
        except RenderError as exc:
            notes.append(f"{doc_type}: {exc}")
            _f(rep, "SUB-002", "blocker", f"{doc_type} PDF를 만들지 못했습니다 — {exc}", basis="제출 형식")
            continue
        dst = sub / f"{i:02d}_{doc_type}.pdf"   # 파일 이름에 회사명을 넣지 않는다
        marks = _proposal_bookmarks(project, raw) if src.suffix == ".hwpx" else None
        info = clean_pdf(raw, dst, title=f"{title} {doc_type}", bookmarks=marks)
        if src.suffix == ".hwpx":
            crossref = _write_crossref(project, rfp, marks or [], info.pages, sub, title)
        docs.append(PackagedDoc(doc_type, src, dst, info.pages, info.size_bytes, info.fonts))
    del avail
    form_docs = _package_forms(project, sub, raw_pdf, title, rep, notes)
    docs += form_docs

    by_type: dict[str, PackagedDoc] = {}
    for d in docs:
        by_type.setdefault(d.doc_type, d)          # 정성제안서는 본문이 먼저다(별지 묶음은 따로 센다)
    # SUB-002: 필수 문서구분
    needed = ["정성제안서"]
    if g.summary_page_limit is not None:
        needed.append("제안요약서")
    if g.presentation is not None or g.presentation_page_limit is not None:
        needed.append("발표자료")
    for t in needed:
        if t not in by_type:
            _f(rep, "SUB-002", "blocker", f"필수 제출 문서 '{t}'가 없습니다", basis="RFP 작성지침")
    if form_docs:
        _f(rep, "SUB-002", "info", f"별지 서식 묶음 {len(form_docs)}개를 넣었습니다 — 서명·날인이 필요한 서식은 날인본으로 바꾸고, "
           "증빙(실적증명서·재무제표 등)은 따로 붙이세요", basis="나라장터 문서구분")
    else:
        _f(rep, "SUB-002", "info", "별지 서식이 없습니다 — `rfpgen forms`로 채우거나 공고 서식으로 따로 준비해 함께 올리세요",
           basis="나라장터 문서구분")

    # PAGE-001·002: 정확한 쪽수
    excluded = set(g.count_exclusions.value) if g.count_exclusions else set(profile.value("page_limits.exclude_from_count"))
    main = by_type.get("정성제안서")
    if main is not None:
        counted = main.pages - (1 if "표지" in excluded else 0)
        if g.main_page_limit is not None:
            limit, prov, basis = g.main_page_limit.value, False, "RFP 작성지침"
        else:
            pv = profile.get("page_limits.main_pages")
            limit, prov, basis = int(pv.value), pv.status != "verified", f"프로필 기본값({pv.status})"
        rep.stats["main_pages"] = counted
        if counted > limit:
            _f(rep, "PAGE-001", "blocker", f"정성제안서 {counted}쪽(표지 제외) — 상한 {limit}쪽 초과", basis=basis, provisional=prov)
    for t, ex in (("제안요약서", g.summary_page_limit), ("발표자료", g.presentation_page_limit)):
        d = by_type.get(t)
        if d is not None and ex is not None and d.pages > ex.value:
            _f(rep, "PAGE-002", "blocker", f"{t} {d.pages}쪽 — 상한 {ex.value}쪽 초과", basis="RFP 작성지침")

    # SUB-001: 형식·용량
    total = sum(d.size_bytes for d in docs)
    rep.stats["total_mb"] = round(total / 1024 / 1024, 2)
    if g.total_size_limit_mb is not None:
        lim_mb, prov, basis = g.total_size_limit_mb.value, False, "RFP 작성지침"
    else:
        pv = profile.get("submission.total_size_limit_mb")
        lim_mb, prov, basis = int(pv.value), pv.status != "verified", f"프로필 기본값({pv.status})"
    if total > lim_mb * 1024 * 1024:
        _f(rep, "SUB-001", "blocker", f"제출 파일 총 {total / 1024 / 1024:.1f}MB — 상한 {lim_mb}MB 초과", basis=basis,
           provisional=prov)

    # FMT-003: 글꼴 임베딩
    for d in docs:
        missing = [n for n, s in d.fonts.items() if s == "not-embedded"]
        if missing:
            _f(rep, "FMT-003", "major", f"{d.doc_type}: 임베딩되지 않은 글꼴 {', '.join(missing[:5])}", basis="스타일 정책")

    # BLD-003: 파일 정보·파일 이름
    terms = kb.identity.terms()
    for d in docs:
        meta = " ".join(inspect_pdf(d.pdf).metadata.values()).lower()
        hits = [t for t in terms if t.lower() in meta or t.lower() in d.pdf.name.lower()]
        if hits:
            _f(rep, "BLD-003", "blocker" if blind else "info", f"{d.doc_type}: 파일 정보·이름에 회사 식별 표기 {', '.join(hits)}",
               basis="블라인드 평가")

    # 초안 단계 점검을 이어 붙인다(쪽수 추정은 위의 정확한 쪽수로 대체)
    checks = sorted((project / "checks").glob("2*.json"))
    if checks:
        prev = CheckReport.model_validate_json(checks[-1].read_text(encoding="utf-8"))
        for f in prev.findings:
            if f.rule != "PAGE-001":
                rep.findings.append(f)
    # GATE-001: 사람 승인 게이트(G1~G4). G5는 이 점검을 보고 사람이 승인한다
    from ..gates import STATUS_KO, GateError, gate_status

    try:
        gates = gate_status(project)
    except GateError:
        gates = []
    for gs in gates:
        if gs.gate != "G5" and gs.status != "approved":
            _f(rep, "GATE-001", "major", f"{gs.gate} {gs.name}: {STATUS_KO[gs.status]} — `rfpgen gate {project.name} {gs.gate} --by 이름`",
               basis="설계서 3장 게이트(P5)")
    rep.stats["gates"] = ", ".join(f"{gs.gate}:{gs.status}" for gs in gates)
    form_checks = sorted((project / "checks").glob("forms-*.json"))
    if form_docs and form_checks:
        rep.findings += CheckReport.model_validate_json(form_checks[-1].read_text(encoding="utf-8")).findings
    rep.stats.update({"blocker": rep.count("blocker"), "major": rep.count("major"), "minor": rep.count("minor")})
    check_dir = project / "checks"
    check_dir.mkdir(exist_ok=True)
    (check_dir / f"{rep.run_id}.json").write_text(rep.model_dump_json(indent=2), encoding="utf-8")
    (check_dir / f"{rep.run_id}.md").write_text(report_markdown(rep), encoding="utf-8")

    checklist = sub / "제출전점검표.md"
    checklist.write_text(_checklist(title, docs, rep, lim_mb, blind, bool(form_docs), crossref), encoding="utf-8")
    (sub / "manifest.json").write_text(json.dumps([
        {"doc_type": d.doc_type, "file": d.pdf.name, "pages": d.pages, "bytes": d.size_bytes, "source": str(d.source.name)}
        for d in docs], ensure_ascii=False, indent=2), encoding="utf-8")
    return PackageResult(docs=docs, check=rep, checklist=checklist, notes=notes, crossref=crossref)


def _write_crossref(project: Path, rfp, marks: list[Bookmark], pages: int, sub: Path, title: str) -> Path | None:
    """조견표(조달청 세부기준 제6조의2③): 평가항목별 해당 목차·쪽. submission/조견표.xlsx·.md"""
    from .crossref import build_crossref, build_toc, crossref_markdown, write_crossref_xlsx

    path = project / "plan" / "outline.json"
    if not path.exists():
        return None
    outline = Outline.model_validate_json(path.read_text(encoding="utf-8"))
    toc = build_toc(outline, marks, pages)
    rows = build_crossref(outline, rfp, toc)
    xlsx = sub / "조견표.xlsx"
    write_crossref_xlsx(xlsx, toc, rows)
    (sub / "조견표.md").write_text(crossref_markdown(title, toc, rows), encoding="utf-8")
    return xlsx


def _proposal_bookmarks(project: Path, pdf: Path) -> list[Bookmark]:
    """본문 PDF의 장·절 책갈피. 목차(plan/outline.json)의 장·절 제목을 렌더된 쪽에서 찾는다."""
    from ..render.hwpx_writer import _section_number

    path = project / "plan" / "outline.json"
    if not path.exists():
        return []
    outline = Outline.model_validate_json(path.read_text(encoding="utf-8"))
    heads: list[tuple[str, int]] = []
    for ch in outline.chapters:
        heads.append((f"{ch.number} {ch.title}", 0))
        heads += [(f"{_section_number(n)} {n.title}", 1) for n in ch.children]
    return find_heading_pages(pdf, heads)


_FORM_FILES = {"정성제안서": "01-1_정성제안서_별지.pdf", "정량제안서": "04_정량제안서.pdf",
               "하도급계획서": "05_하도급계획서.pdf", "기타문서": "06_기타문서.pdf"}


def _package_forms(project: Path, sub: Path, raw_pdf: Path, title: str, rep: CheckReport,
                   notes: list[str]) -> list[PackagedDoc]:
    """out/forms/의 채운 서식을 PDF로 바꿔 문서구분별로 하나씩 묶는다."""
    import pikepdf

    from ..forms import load_forms_report

    report = load_forms_report(project)
    if report is None or not report.forms:
        return []
    groups: dict[str, list[tuple[Path, str]]] = {}
    for f in report.forms:
        src = project / f.output
        if not f.output or not src.exists():
            continue
        pdf = raw_pdf / "forms" / f"{src.stem}.pdf"
        try:
            hwpx_to_pdf(src, pdf)
        except RenderError as exc:
            notes.append(f"{f.form_no}: {exc}")
            _f(rep, "SUB-002", "major", f"{f.form_no}({f.title}) PDF를 만들지 못했습니다 — {exc}", basis="제출 형식")
            continue
        groups.setdefault(f.doc_type, []).append((pdf, f"{f.form_no} {f.title}".strip()))
    out: list[PackagedDoc] = []
    for doc_type, name in _FORM_FILES.items():
        parts = groups.get(doc_type)
        if not parts:
            continue
        merged = raw_pdf / "forms" / f"_{doc_type}.pdf"
        marks: list[Bookmark] = []
        with pikepdf.Pdf.new() as pdf:
            for part, label in parts:
                marks.append(Bookmark(title=label, page=len(pdf.pages)))     # 서식마다 책갈피
                with pikepdf.Pdf.open(part) as src_pdf:
                    pdf.pages.extend(src_pdf.pages)
            pdf.save(merged)
        dst = sub / name
        info = clean_pdf(merged, dst, title=f"{title} {doc_type}", bookmarks=marks)
        out.append(PackagedDoc(doc_type, project / "out" / "forms", dst, info.pages, info.size_bytes, info.fonts))
    return out


def _checklist(title: str, docs: list[PackagedDoc], rep: CheckReport, lim_mb: int, blind: bool,
               has_forms: bool = False, crossref: Path | None = None) -> str:
    total = sum(d.size_bytes for d in docs)
    lines = [f"# 제출 전 점검표 — {title}", "", f"점검 실행: {rep.run_id}", "",
             "| 문서구분(나라장터) | 파일 | 쪽수 | 용량 |", "|---|---|---|---|"]
    for d in docs:
        lines.append(f"| {d.doc_type} | {d.pdf.name} | {d.pages} | {d.size_bytes / 1024 / 1024:.2f}MB |")
    lines += ["", f"- 총 용량: {total / 1024 / 1024:.2f}MB / 상한 {lim_mb}MB",
              f"- 점검: blocker {rep.count('blocker')}, major {rep.count('major')}, minor {rep.count('minor')} "
              f"(상세: `checks/{rep.run_id}.md`)",
              f"- 블라인드 평가: {'예 — 본문·파일 정보·파일 이름에 회사 식별 표기가 없어야 합니다' if blind else '아니오'}", "",
              "## 업로드 전 확인(사람)", "",
              "- [ ] blocker 0건을 확인했다(G5)",
              "- [ ] G1~G4 승인(`rfpgen gate`)을 마치고, 이 점검표를 확인한 뒤 G5를 승인했다",
              "- [ ] 나라장터 제출 화면에서 파일마다 문서구분(정성제안서·제안요약서·발표자료·정량제안서·하도급 계획서·기타)을 맞게 지정했다",
              ("- [ ] 별지 서식 PDF의 빈칸·선택 칸(□)·서명·날인을 확인하고, 날인이 필요한 서식은 날인본으로 바꿨다(out/forms/forms.md)"
               if has_forms else "- [ ] 정량제안서·별지 서식·하도급 계획서를 공고 양식으로 따로 준비해 함께 올렸다"),
              "- [ ] 가격입찰서를 따로 제출했다(공고에 따라 제안서나 가격입찰서 중 하나라도 빠지면 입찰 무효)",
              ("- [ ] 조견표(목차·평가항목별 해당 쪽수)를 제출기한까지 시스템에 등록했다 — `submission/조견표.xlsx` "
               "(조달청 세부기준 제6조의2③, 쪽은 최종 PDF로 다시 확인)" if crossref else
               "- [ ] 조견표(목차·평가항목별 해당 쪽수)를 만들어 시스템에 등록했다(조달청 세부기준 제6조의2③)"),
              "- [ ] 임시저장 때 파일이 암호화되고 최종 제출 뒤에는 수정·재제출할 수 없음을 알고 마감 전에 여유 있게 제출했다",
              "- [ ] PDF를 열어 표·그림·글꼴이 깨지지 않았는지 쪽마다 확인했다(서버 렌더는 한글 화면과 다를 수 있음)",
              "", "확인자: ________________  일시: ________________", ""]
    return "\n".join(lines)


__all__ = ["build_package", "latest_drafts", "make_slides"]
