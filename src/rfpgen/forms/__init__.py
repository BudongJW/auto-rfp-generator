"""별지 서식 채우기 파이프라인(설계서 7.9절 '별지 채우기', 7.10절 문서구분, M3).

analyze가 보관한 공고 첨부 원본(raw/) 중 HWPX·HWP에서 별지 서식 영역을 찾아 서식마다 따로 떼어 낸 뒤,
KB·RFP·사람이 준 값으로 빈칸을 채워 out/forms/에 쓴다. 원본 양식의 글자 모양·표 구조는 그대로 둔다.

입력
  project/raw/*.hwpx|hwp   analyze가 보관한 원본(project.yaml의 최신 history)
  kb/company.yaml          identity(상호·대표자), company(사업자등록번호·주소 …)
  kb/projects.csv …        실적·인력·인증 목록 표
  kb/private/people.csv    (선택) 인력 실명 — 서식의 성명 칸에만 쓴다
  kb/private/forms.yaml    (선택) values: {이름표: 값} — 생성기가 모르는 칸(담당자 등)
  project/forms.yaml       (선택) doc_types: {"7": 정량제안서}, skip: ["3"], include: ["13"]
출력
  out/forms/별지NN_제목.hwpx, out/forms/forms.json, out/forms/forms.md, checks/forms-*.json|md
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..schemas.draft import CheckFinding, CheckReport
from ..schemas.forms import FormDocType, FormResult, FormsReport
from ..schemas.rfp import Rfp, TocNode
from .fill import _PAST_FORM, FillContext, fill_region, norm
from .locate import FormRegion, find_regions, match_marker, unspace
from .oxml import keep_region

_KEY_IN_TEXT = re.compile(r"별지\s*(?:제\s*)?(\d{1,2})(?:\s*[-－의]\s*(\d{1,2}))?\s*호")
_DOC_TYPES: tuple[FormDocType, ...] = ("정성제안서", "정량제안서", "하도급계획서", "기타문서")
_QUANT = re.compile(r"실적|인력|기술자|경력|신용|재무|경영상태|인증|보유|정량|참여\s*인원")
# 입찰자가 내지 않는 서식(평가위원·신고자용) — 기본으로 만들지 않고 알린다. project/forms.yaml include로 되살린다
_NOT_BIDDER = re.compile(r"사전\s*접촉|평가\s*위원")


def form_key(text: str) -> str | None:
    m = _KEY_IN_TEXT.search(text or "")
    if not m:
        return None
    return str(int(m.group(1))) + (f"-{int(m.group(2))}" if m.group(2) else "")


def _latest_rfp(project: Path) -> Rfp:
    found = sorted(project.glob("rfp/rfp.v*.json"), key=lambda p: int(re.search(r"v(\d+)", p.name).group(1)))  # type: ignore[union-attr]
    if not found:
        raise FileNotFoundError(f"{project}: rfp.json이 없습니다 — 먼저 `rfpgen analyze`를 실행하세요")
    return Rfp.model_validate_json(found[-1].read_text(encoding="utf-8"))


def _toc_keys(rfp: Rfp) -> set[str]:
    keys: set[str] = set()

    def walk(nodes: list[TocNode]) -> None:
        for n in nodes:
            for ref in n.form_refs:
                if (k := form_key(ref)) is not None:
                    keys.add(k)
            walk(n.children)

    if rfp.guideline.prescribed_toc is not None:
        walk(rfp.guideline.prescribed_toc.value)
    return keys


def classify(title: str, key: str, toc_keys: set[str]) -> FormDocType:
    """나라장터 문서구분 추정. project/forms.yaml의 doc_types로 바꿀 수 있다."""
    if "하도급" in title:
        return "하도급계획서"
    if key in toc_keys:
        return "정성제안서"
    if _QUANT.search(title):
        return "정량제안서"
    return "기타문서"


def _safe(title: str) -> str:
    return re.sub(r"[\\/:*?\"<>|\s]+", "", title)[:30] or "서식"


def _hwpx_bytes(raw: Path) -> bytes:
    data = raw.read_bytes()
    if raw.suffix.lower() == ".hwp":
        from hwpx.hwp5.package import convert, to_hwpx_bytes

        return to_hwpx_bytes(convert(data).files)
    return data


@dataclass
class _Source:
    file: str                # 원래 파일 이름
    role: str
    data: bytes              # HWPX 바이트(HWP는 변환본)
    region: FormRegion


def _inputs(project: Path) -> list[dict]:
    meta = yaml.safe_load((project / "project.yaml").read_text(encoding="utf-8")) if (project / "project.yaml").exists() else {}
    history = (meta or {}).get("history") or []
    if not history:
        raise FileNotFoundError(f"{project}: project.yaml에 분석 이력이 없습니다 — 먼저 `rfpgen analyze`를 실행하세요")
    return history[-1].get("inputs") or []


def _collect(project: Path, report: FormsReport) -> list[_Source]:
    from hwpx import HwpxDocument

    best: dict[str, _Source] = {}
    for inp in _inputs(project):
        if inp.get("format") not in ("hwpx", "hwp"):
            continue
        raw = project / inp["raw"]
        try:
            data = _hwpx_bytes(raw)
            doc = HwpxDocument.open(data)
        except Exception as exc:  # noqa: BLE001 — 변환 실패는 보고만 한다
            report.findings.append(CheckFinding(rule="FORM-OPEN", severity="major", basis="별지 서식",
                                                message=f"{inp.get('file')}: 서식을 찾으려고 열지 못했습니다 — {exc}"))
            continue
        regions = find_regions([s.element for s in doc.sections])
        if not regions and inp.get("role") == "별지서식":          # 파일 하나가 서식 하나
            name = Path(inp.get("file", "서식")).stem
            key = form_key(name) or f"F{len(best) + 1}"
            paras = sum(1 for s in doc.sections for p in s.element)
            regions = [FormRegion(key, unspace(re.sub(r"^\W*별지.*?호\s*(?:서식)?\W*", "", name)) or name,
                                  0, 0, paras, 1, paras)]
        for r in regions:
            cur = best.get(r.key)
            if cur is None or r.weight > cur.region.weight:
                best[r.key] = _Source(inp.get("file", raw.name), inp.get("role", ""), data, r)
        doc.close()
    return sorted(best.values(), key=lambda s: [int(x) if x.isdigit() else 0 for x in re.split(r"[-F]", s.region.key) if x])


def _extract(src: _Source):
    """원본을 새로 열어 서식 영역만 남긴 문서와 그 구역을 돌려준다."""
    from hwpx import HwpxDocument

    doc = HwpxDocument.open(src.data)
    r = src.region
    sections = doc.sections
    keep_region(sections[r.section].element, r.start, r.end)
    sections[r.section].mark_dirty()
    for i in range(len(sections) - 1, -1, -1):
        if i != r.section:
            doc.remove_section(i)
    return doc, doc.sections[0]


def _load_overrides(kb_dir: Path | None) -> dict[str, str]:
    if kb_dir is None:
        return {}
    path = Path(kb_dir) / "private" / "forms.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {norm(str(k)): str(v) for k, v in (data.get("values") or {}).items() if v is not None}


def _project_options(project: Path) -> tuple[dict[str, FormDocType], set[str], set[str]]:
    path = project / "forms.yaml"
    if not path.exists():
        return {}, set(), set()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    types = {str(k): v for k, v in (data.get("doc_types") or {}).items() if v in _DOC_TYPES}
    return types, {str(x) for x in data.get("skip") or []}, {str(x) for x in data.get("include") or []}


def run_forms(project: Path, *, kb_dir: Path | None = None, date: dt.date | None = None) -> FormsReport:
    from ..check import report_markdown
    from ..kb import load_kb, load_private_names

    project = Path(project)
    rfp = _latest_rfp(project)
    kb = load_kb(kb_dir) if kb_dir else None
    ctx = FillContext(rfp=rfp, kb=kb, names=load_private_names(kb_dir) if kb_dir else {},
                      overrides=_load_overrides(kb_dir), date=date or dt.date.today())
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = FormsReport(run_id=f"forms-{run_id}", date=ctx.date.isoformat())
    blind = bool(rfp.guideline.blind and rfp.guideline.blind.value)
    toc_keys = _toc_keys(rfp)
    type_over, skip, include = _project_options(project)
    out_dir = project / "out" / "forms"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in [*out_dir.glob("*.hwpx"), *(out_dir / "요청용").glob("*.hwpx")]:
        old.unlink()
    if kb is None:
        report.findings.append(CheckFinding(rule="FORM-KB", severity="major", basis="별지 서식",
                                            message="KB 없이 실행했습니다 — 회사 정보·실적·인력 칸은 비어 있습니다(--kb)"))

    sources = _collect(project, report)
    for src in sources:
        r = src.region
        if r.key in skip:
            continue
        if _NOT_BIDDER.search(r.title) and r.key not in include:
            skip.add(r.key)
            report.findings.append(CheckFinding(
                rule="FORM-SKIP", severity="info", basis="별지 서식", section_id=r.form_no,
                message=f"{r.form_no}({r.title})는 평가위원·신고자가 쓰는 서식이라 만들지 않았습니다 — 필요하면 "
                        f"project/forms.yaml의 include에 '{r.key}'를 넣으세요"))
            continue
        res = FormResult(key=r.key, form_no=r.form_no, title=r.title, source_file=src.file,
                         doc_type=type_over.get(r.key) or classify(r.title, r.key, toc_keys),
                         blind=blind and r.key in toc_keys)
        doc, section = _extract(src)
        fill_region(section, ctx, res)
        num, _, sub_no = r.key.partition("-")
        target = out_dir / f"별지{num.zfill(2)}{'-' + sub_no if sub_no else ''}_{_safe(r.title)}.hwpx"
        doc.save_to_path(str(target))
        res.output = str(target.relative_to(project))
        if _PAST_FORM.search(re.sub(r"\s+", "", r.title)):
            _request_drafts(src, res, ctx, out_dir / "요청용", target.stem, project)
        report.forms.append(res)

    # 작성지침·지정 목차가 요구한 서식 중 못 찾은 것
    found = {f.key for f in report.forms} | skip
    wanted: dict[str, str] = {}
    for d in rfp.guideline.required_documents:
        if (k := form_key(d.form_no or d.name)) is not None:
            wanted.setdefault(k, d.name)
    for k in toc_keys:
        wanted.setdefault(k, "지정 목차 서식")
    for k, name in sorted(wanted.items(), key=lambda kv: int(re.sub(r"\D.*", "", kv[0]) or 0)):
        if k not in found:
            report.findings.append(CheckFinding(
                rule="FORM-MISSING", severity="minor", basis="RFP 작성지침", section_id=f"별지 제{k}호",
                message=f"별지 제{k}호({name})를 HWP·HWPX 첨부에서 찾지 못했습니다 — "
                        "PDF로만 받았다면 원본 서식을 받아 직접 작성하세요"))

    (out_dir / "forms.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "forms.md").write_text(forms_markdown(report), encoding="utf-8")
    check = CheckReport(run_id=report.run_id, findings=[*report.findings, *(f for x in report.forms for f in x.findings)])
    check.stats.update({"forms": len(report.forms), "blocker": check.count("blocker"), "major": check.count("major"),
                        "minor": check.count("minor")})
    check_dir = project / "checks"
    check_dir.mkdir(exist_ok=True)
    (check_dir / f"{check.run_id}.json").write_text(check.model_dump_json(indent=2), encoding="utf-8")
    (check_dir / f"{check.run_id}.md").write_text(report_markdown(check), encoding="utf-8")
    return report


def _request_drafts(src: _Source, res: FormResult, ctx: FillContext, out: Path, stem: str, project: Path,
                    limit: int = 20) -> None:
    """실적증명서처럼 발급기관이 확인·발급하는 서식: 제출 묶음에서 빼고, KB 실적마다 과거 사업 칸까지 채운 발급 요청용
    초안을 한 장씩 만든다(out/forms/요청용/). 계약번호·지분율·발급기관 칸은 발주기관 확인 때 채운다."""
    res.external = True
    projects = sorted(ctx.kb.projects, key=lambda p: p.end or "", reverse=True) if ctx.kb is not None else []
    if not projects:
        res.findings.append(CheckFinding(rule="FORM-REQUEST", severity="info", section_id=res.form_no, basis="별지 서식",
                                         message="발급기관이 확인·발급하는 서식이라 제출 묶음에 넣지 않습니다 — KB에 실적이 "
                                                 "없어 발급 요청용 초안도 만들지 않았습니다"))
        return
    out.mkdir(parents=True, exist_ok=True)
    for proj in projects[:limit]:
        draft = FormResult(key=res.key, form_no=res.form_no, title=res.title, source_file=res.source_file,
                           doc_type=res.doc_type)
        doc, section = _extract(src)
        fill_region(section, dataclasses.replace(ctx, record=proj), draft)
        target = out / f"{stem}_{_safe(proj.id)}.hwpx"
        doc.save_to_path(str(target))
        res.requests.append(str(target.relative_to(project)))
    more = f"(실적 {len(projects)}건 중 최근 {limit}건)" if len(projects) > limit else ""
    res.findings.append(CheckFinding(
        rule="FORM-REQUEST", severity="info", section_id=res.form_no, basis="별지 서식",
        message=f"발급기관이 확인·발급하는 서식이라 제출 묶음에 넣지 않습니다. 실적마다 사업명·기간·금액을 채운 발급 요청용 "
                f"초안 {len(res.requests)}장{more}을 out/forms/요청용/에 만들었습니다 — 계약번호·지분율·사업개요를 채워 "
                "발주기관에 보내고, 발급받은 증명서를 스캔해 정량제안서와 함께 올리세요"))


def load_forms_report(project: Path) -> FormsReport | None:
    path = Path(project) / "out" / "forms" / "forms.json"
    if not path.exists():
        return None
    return FormsReport.model_validate_json(path.read_text(encoding="utf-8"))


def forms_markdown(report: FormsReport) -> str:
    lines = [f"# 별지 서식 채우기 결과 ({report.run_id})", "", f"- 넣은 날짜: {report.date}",
             f"- 서식: {len(report.forms)}개", "", "| 서식 | 제목 | 문서구분 | 채운 칸 | 늘린 행 | 확인할 것 | 파일 |",
             "|---|---|---|---|---|---|---|"]
    for f in report.forms:
        todo = sum(1 for x in f.findings if x.severity in ("blocker", "major", "minor"))
        lines.append(f"| {f.form_no} | {f.title} | {f.doc_type}{' (블라인드)' if f.blind else ''} | {len(f.fills)} | "
                     f"{f.added_rows} | {todo} | `{f.output}` |")
    for f in report.forms:
        lines += ["", f"## {f.form_no} {f.title}", "", f"원본: {f.source_file}", ""]
        if f.fills:
            lines += ["| 위치 | 이름표 | 값 | 출처 |", "|---|---|---|---|"]
            lines += [f"| {x.where} | {x.label} | {x.value} | {x.field} |" for x in f.fills]
        else:
            lines.append("채운 칸이 없습니다.")
        if f.requests:
            lines += ["", "발급 요청용 초안:", *[f"- `{x}`" for x in f.requests]]
        if f.findings:
            lines.append("")
            lines += [f"- **{x.severity}** `{x.rule}` {x.message}" for x in f.findings]
    if report.findings:
        lines += ["", "## 서식 밖 점검", ""]
        lines += [f"- **{x.severity}** `{x.rule}` {x.message}" for x in report.findings]
    lines += ["", "서명·날인, 선택 칸(□), 증빙 첨부는 사람이 합니다. 한글에서 열어 칸이 넘치지 않았는지 확인하세요.", ""]
    return "\n".join(lines)


__all__ = ["classify", "form_key", "forms_markdown", "load_forms_report", "match_marker", "run_forms"]
