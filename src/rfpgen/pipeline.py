"""M1 파이프라인: ingest(업로드) → parse → extract → plan, 산출물을 프로젝트 폴더에 쓴다(설계서 5.4절)."""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import __version__
from .extract import extract_rfp
from .parse import InputFile, UnsafeInputError, collect_inputs, detect_format, parse_document
from .plan import plan_proposal
from .profile import Profile, load_profile
from .report.markdown import analysis_markdown, questions_markdown
from .report.xlsx import write_workbook
from .schemas.docir import Document
from .schemas.plan import Outline, PageBudget, Trace
from .schemas.rfp import ExtractionReport, Rfp


@dataclass
class AnalysisResult:
    project_dir: Path
    version: int
    docs: list[Document]
    rfp: Rfp
    report: ExtractionReport
    outline: Outline
    budget: PageBudget
    trace: Trace
    skipped: list[str] = field(default_factory=list)
    outputs: dict[str, Path] = field(default_factory=dict)


def _next_version(rfp_dir: Path) -> int:
    nums = [int(m.group(1)) for p in rfp_dir.glob("rfp.v*.json") if (m := re.match(r"rfp\.v(\d+)\.json$", p.name))]
    return max(nums, default=0) + 1


def _write_json(path: Path, model) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(indent=2, exclude_none=False), encoding="utf-8")
    return path


def _store_raw(project: Path, f: InputFile) -> Path:
    ext = detect_format(f.name, f.data) or "bin"
    target = project / "raw" / f"{f.sha256}.{ext}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(f.data)
    return target


def parse_inputs(files: list[InputFile], report: ExtractionReport) -> list[Document]:
    docs: list[Document] = []
    for i, f in enumerate(files, start=1):
        try:
            docs.append(parse_document(f, f"d{i:02d}"))
        except UnsafeInputError as exc:
            report.add("PARSE-FAIL", "error", str(exc))
    return docs


def analyze(paths: list[Path], project_dir: Path, profile: Profile | None = None,
            profile_name: str = "national_negotiation_sw") -> AnalysisResult:
    profile = profile or load_profile(profile_name)
    files, skipped = collect_inputs(paths)
    pre = ExtractionReport()
    for name in skipped:
        pre.add("INPUT-SKIPPED", "info", f"지원하지 않는 형식이라 건너뜀: {name}")
    if not files:
        raise UnsafeInputError("분석할 수 있는 문서(PDF·HWP·HWPX·DOCX)가 없습니다")

    project_dir.mkdir(parents=True, exist_ok=True)
    raw_paths = {f.name: _store_raw(project_dir, f) for f in files}
    docs = parse_inputs(files, pre)
    if not docs:
        raise UnsafeInputError("모든 문서의 파싱에 실패했습니다: " + "; ".join(f.message for f in pre.findings))
    for d in docs:
        _write_json(project_dir / "docir" / f"{d.doc_id}.json", d)

    rfp, report = extract_rfp(docs, profile)
    report.findings = pre.findings + report.findings
    outline, budget, trace = plan_proposal(rfp, profile, report)

    version = _next_version(project_dir / "rfp")
    out: dict[str, Path] = {}
    out["rfp"] = _write_json(project_dir / "rfp" / f"rfp.v{version}.json", rfp)
    out["extraction_report"] = _write_json(project_dir / "rfp" / f"extraction_report.v{version}.json", report)
    for base in (project_dir / "plan" / f"v{version}", project_dir / "plan"):  # 버전별 보관 + 최신본
        out["outline"] = _write_json(base / "outline.json", outline)
        out["budget"] = _write_json(base / "budget.json", budget)
        out["trace"] = _write_json(base / "trace.json", trace)
    out["xlsx"] = project_dir / "out" / "analysis.xlsx"
    write_workbook(out["xlsx"], rfp, outline, budget, trace, report)
    out["analysis_md"] = project_dir / "out" / "analysis.md"
    out["analysis_md"].write_text(analysis_markdown(docs, rfp, outline, budget, trace, report, profile.name), encoding="utf-8")
    out["questions_md"] = project_dir / "out" / "questions.md"
    out["questions_md"].write_text(questions_markdown(rfp), encoding="utf-8")

    project_yaml = project_dir / "project.yaml"
    meta = yaml.safe_load(project_yaml.read_text(encoding="utf-8")) if project_yaml.exists() else {}
    meta = meta or {}
    meta.update({
        "generator": f"rfpgen {__version__}",
        "profile": profile.name,
        "bid_no": rfp.notice.bid_no.value if rfp.notice.bid_no else None,
        "title": rfp.notice.title.value if rfp.notice.title else None,
        "blind": bool(rfp.guideline.blind and rfp.guideline.blind.value),
        "latest_version": version,
        "gates": meta.get("gates", {"G1": None, "G2": None, "G3": None, "G4": None, "G5": None}),
    })
    history = meta.get("history", [])
    history.append({
        "version": version,
        "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "inputs": [
            {"doc_id": d.doc_id, "file": d.filename, "format": d.format, "role": d.role,
             "sha256": d.sha256, "raw": str(raw_paths[d.filename].relative_to(project_dir))}
            for d in docs
        ],
        "stats": json.loads(json.dumps(report.stats)),
    })
    meta["history"] = history
    project_yaml.write_text(yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8")
    out["project"] = project_yaml

    return AnalysisResult(project_dir, version, docs, rfp, report, outline, budget, trace, skipped, out)
