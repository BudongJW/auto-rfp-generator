"""처음 쓰는 사람을 위한 흐름: 한 번에 실행(rfpgen start)과 진행 상태·다음 할 일(rfpgen status).

- start: 분석 → 초안(골격 또는 LLM) → 별지 서식(HWP·HWPX 첨부가 있을 때) → 장표 → 제출 패키지(변환기가 있을 때).
  한 단계가 실패해도 다음 단계로 넘어가고, 끝에 상태와 다음 할 일을 보여 준다.
- KB 폴더는 project.yaml에 기억해 두고, 다음 명령에서 --kb를 빼면 그 폴더를 쓴다.
- KB 없이 시작하면 회사 정보 칸은 비워 둔다(예시 회사 값으로 채우지 않는다).
"""

from __future__ import annotations

import datetime as dt
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .profile import Profile

# ---------------------------------------------------------------- KB 기억

EXAMPLE_COMPANY = "(주)예시정보"        # rfpgen kb init 예시 값(그대로면 경고)


def _meta(project: Path) -> dict:
    path = Path(project) / "project.yaml"
    return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}


def remember_kb(project: Path, kb: Path | None) -> None:
    if kb is None or not (Path(project) / "project.yaml").exists():
        return
    meta = _meta(project)
    meta["kb"] = str(Path(kb).resolve())
    (Path(project) / "project.yaml").write_text(yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8")


def resolve_kb(project: Path, kb: Path | None) -> Path | None:
    """--kb가 없으면 프로젝트에 기억한 KB 폴더(있을 때만)."""
    if kb is not None:
        return kb
    saved = _meta(project).get("kb")
    return Path(saved) if saved and Path(saved).is_dir() else None


def default_project_dir(first_file: Path) -> Path:
    stem = re.sub(r"[\\/:*?\"<>|\s]+", "_", Path(first_file).stem).strip("_") or "project"
    return Path("projects") / stem[:40]


# ---------------------------------------------------------------- 상태


@dataclass
class Stage:
    key: str
    title: str
    done: bool
    detail: str
    command: str            # 이 단계를 (다시) 실행하는 명령


def _latest(paths: list[Path]) -> Path | None:
    def num(p: Path) -> int:
        m = re.search(r"v(\d+)", p.name)
        return int(m.group(1)) if m else 0
    return max(paths, key=num) if paths else None


def _show(path: str | Path) -> str:
    """현재 폴더 아래면 상대 경로, 아니면 그대로."""
    try:
        return str(Path(path).resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def project_status(project: Path) -> tuple[list[Stage], list[str]]:
    """(단계 목록, 다음 할 일). 파일만 읽는다."""
    project = Path(project)
    p = str(project)
    meta = _meta(project)
    kb_path = meta.get("kb")
    kb = _show(kb_path) if kb_path else None             # 화면에는 현재 폴더 기준 경로로
    kb_opt = f" --kb {kb}" if kb else " --kb <KB 폴더>"
    stages: list[Stage] = []
    todo: list[str] = []

    rfp_path = _latest(list(project.glob("rfp/rfp.v*.json")))
    if rfp_path:
        rfp = json.loads(rfp_path.read_text(encoding="utf-8"))
        title = (rfp.get("notice", {}).get("title") or {}).get("value") or "(사업명 못 찾음)"
        rep_path = project / "rfp" / rfp_path.name.replace("rfp.", "extraction_report.")
        errs = 0
        if rep_path.exists():
            findings = json.loads(rep_path.read_text(encoding="utf-8")).get("findings", [])
            errs = sum(1 for f in findings if f["severity"] == "error")
        detail = (f"{title} — 요구사항 {len(rfp.get('requirements', []))}건, 질의서 후보 {len(rfp.get('questions', []))}건"
                  + (f", 확인할 오류 {errs}건" if errs else ""))
        stages.append(Stage("analyze", "RFP 분석", True, detail, f"rfpgen analyze <RFP 파일> -o {p}"))
        if errs:
            todo.append(f"분석 점검의 오류 {errs}건을 확인하세요: {project / 'out' / 'analysis.md'}")
    else:
        stages.append(Stage("analyze", "RFP 분석", False, "아직 없음", f"rfpgen analyze <RFP 파일> -o {p}"))

    stages.append(Stage("kb", "회사 정보(KB)", bool(kb), kb or "연결 안 됨 — 회사 정보 칸·실적·인력이 비어 있습니다",
                        "rfpgen kb init kb"))
    if kb_path and Path(kb_path).is_dir():
        try:
            from .kb import load_kb

            if load_kb(Path(kb_path)).identity.name == EXAMPLE_COMPANY:
                todo.append(f"KB에 예시 회사 값('{EXAMPLE_COMPANY}')이 남아 있습니다 — "
                            f"{kb}의 company.yaml·CSV를 회사 값으로 바꾸세요")
        except Exception:  # noqa: BLE001 — KB 형식 오류는 kb check가 알려 준다
            todo.append(f"KB를 읽지 못했습니다 — `rfpgen kb check {kb}`로 확인하세요")

    drafts = {}
    for f in (project / "sections").glob("*.v*.json"):
        m = re.match(r"(.+)\.v(\d+)\.json$", f.name)
        if m and int(m.group(2)) > drafts.get(m.group(1), (0, None))[0]:
            drafts[m.group(1)] = (int(m.group(2)), f)
    if drafts:
        loaded = [json.loads(f.read_text(encoding="utf-8")) for _, f in drafts.values()]
        holes = sum(len(d.get("placeholders", [])) for d in loaded)
        llm = sum(1 for d in loaded if d.get("origin") == "llm")
        stages.append(Stage("draft", "본문 초안", True, f"{len(loaded)}절(LLM {llm}) — [확인 필요] {holes}곳",
                            f"rfpgen draft {p}{kb_opt}"))
        if holes:
            todo.append(f"초안의 [확인 필요] {holes}곳을 채우세요 — 스토리보드 {project / 'strategy' / 'storyboard.md'}, "
                        f"본문 {project / 'out' / 'proposal.hwpx'}")
    else:
        stages.append(Stage("draft", "본문 초안", False, "아직 없음", f"rfpgen draft {p}{kb_opt}"))

    figs = project / "out" / "figures" / "figures.json"
    if figs.exists():
        n = len(json.loads(figs.read_text(encoding="utf-8")))
        stages.append(Stage("figures", "도식", True, f"{n}개 — 고치려면 strategy/figures/<id>.json", f"rfpgen figures {p}"))

    inputs = ((meta.get("history") or [{}])[-1].get("inputs") or []) if meta.get("history") else []
    has_hwp = any(i.get("format") in ("hwp", "hwpx") for i in inputs)
    forms = project / "out" / "forms" / "forms.json"
    if forms.exists():
        rep = json.loads(forms.read_text(encoding="utf-8"))
        open_items = sum(1 for f in rep.get("forms", []) for x in f.get("findings", []) if x["severity"] in ("blocker", "major"))
        stages.append(Stage("forms", "별지 서식", True, f"{len(rep.get('forms', []))}개 — 확인할 것 {open_items}건",
                            f"rfpgen forms {p}{kb_opt}"))
        if open_items:
            todo.append(f"별지 서식의 확인할 것 {open_items}건: {project / 'out' / 'forms' / 'forms.md'}")
    elif has_hwp:
        stages.append(Stage("forms", "별지 서식", False, "HWP·HWPX 첨부가 있어 채울 수 있음", f"rfpgen forms {p}{kb_opt}"))

    slides = project / "out" / "summary.pptx"
    stages.append(Stage("slides", "요약본·발표자료", slides.exists(),
                        "out/summary.pptx, out/presentation.pptx, out/script.md" if slides.exists() else "아직 없음",
                        f"rfpgen slides {p}"))

    newest_draft = max((f.stat().st_mtime for _, f in drafts.values()), default=0.0)
    if slides.exists() and drafts and slides.stat().st_mtime < newest_draft:
        todo.append(f"초안이 요약본·발표자료보다 새롭습니다 — `rfpgen slides {p}`로 다시 만드세요")
    manifest = project / "submission" / "manifest.json"
    checks = sorted((project / "checks").glob("package-*.json"))
    if manifest.exists() and checks:
        docs = json.loads(manifest.read_text(encoding="utf-8"))
        blockers = sum(1 for f in json.loads(checks[-1].read_text(encoding="utf-8")).get("findings", [])
                       if f["severity"] == "blocker")
        stages.append(Stage("package", "제출 패키지", True, f"PDF {len(docs)}개 — 점검 blocker {blockers}건",
                            f"rfpgen package {p}{kb_opt}"))
        if blockers:
            todo.append(f"제출 전 점검 blocker {blockers}건을 해결하세요: {project / 'submission' / '제출전점검표.md'}")
        if drafts and manifest.stat().st_mtime < newest_draft:
            todo.append(f"초안이 제출 패키지보다 새롭습니다 — `rfpgen package {p}`로 다시 만드세요")
    else:
        stages.append(Stage("package", "제출 패키지", False, "아직 없음", f"rfpgen package {p}{kb_opt}"))

    try:
        from .gates import STATUS_KO, GateError, gate_status

        gates = gate_status(project)
        approved = sum(1 for g in gates if g.status == "approved")
        nxt = next((g for g in gates if g.status != "approved"), None)
        stages.append(Stage("gates", "사람 승인(G1~G5)", nxt is None,
                            f"{approved}/5 승인" + (f" — 다음: {nxt.gate} {nxt.name}({STATUS_KO[nxt.status]})" if nxt else ""),
                            f"rfpgen gate {p}"))
    except (GateError, OSError):
        nxt = None

    # 다음 할 일: 아직 안 한 첫 단계 → 품질 할 일 → 승인
    first = next((s for s in stages if not s.done and s.key not in ("gates",)), None)
    head: list[str] = []
    if first is not None:
        if first.key == "kb":
            files = " ".join(i.get("file", "") for i in inputs) or "<RFP 파일>"
            head.append("회사 정보를 만드세요: `rfpgen kb init kb`로 예시를 만든 뒤 kb 폴더의 값을 회사 값으로 바꾸고, "
                        f"`rfpgen start {files} -o {p} --kb kb`로 다시 실행하세요")
        else:
            head.append(f"{first.title}: `{first.command}`")
    if nxt is not None and rfp_path:
        todo.append(f"내용을 확인했으면 승인을 기록하세요: `rfpgen gate {p} {nxt.gate} --by <이름>`")
    return stages, head + todo


# ---------------------------------------------------------------- 한 번에 실행


@dataclass
class StepResult:
    name: str
    ok: bool
    seconds: float
    message: str = ""
    skipped: bool = False


@dataclass
class StartResult:
    project: Path
    steps: list[StepResult] = field(default_factory=list)


def run_start(files: list[Path], project: Path, profile: Profile, *, kb: Path | None = None, provider=None,
              share_kb: bool = False, date: dt.date | None = None,
              echo: Callable[[str], None] = print) -> StartResult:
    from .draft.pipeline import run_draft
    from .forms import run_forms
    from .package import build_package, make_slides
    from .pipeline import analyze
    from .render.pdf import converters_available

    res = StartResult(project=Path(project))
    total = 5

    def step(i: int, name: str, fn, *, skip: str = "") -> bool:
        if skip:
            echo(f"[{i}/{total}] {name} — 건너뜀: {skip}")
            res.steps.append(StepResult(name, True, 0.0, skip, skipped=True))
            return True
        echo(f"[{i}/{total}] {name} …")
        t = time.monotonic()
        try:
            msg = fn() or ""
        except Exception as exc:  # noqa: BLE001 — 한 단계가 실패해도 다음 단계로 넘어간다
            res.steps.append(StepResult(name, False, time.monotonic() - t, f"{type(exc).__name__}: {exc}"))
            echo(f"      실패: {exc}")
            return False
        res.steps.append(StepResult(name, True, time.monotonic() - t, msg))
        echo(f"      완료({time.monotonic() - t:.0f}초){' — ' + msg if msg else ''}")
        return True

    def do_analyze():
        r = analyze(files, project, profile, llm_provider=provider)
        remember_kb(project, kb)
        return f"요구사항 {len(r.rfp.requirements)}건, 목차 {len(r.outline.chapters)}장"

    if not step(1, "RFP 분석", do_analyze):
        return res                                     # 분석이 없으면 뒤 단계를 할 수 없다

    def do_draft():
        r = run_draft(project, profile, kb_dir=kb, provider=provider, share_kb=share_kb)
        return f"{len(r.drafts)}절, [확인 필요] {sum(len(d.placeholders) for d in r.drafts)}곳, 도식 {len(r.figures)}개"

    step(2, "본문 초안" + ("(LLM)" if provider is not None else "(작성용 골격)"), do_draft)

    hwp = [f for f in files if Path(f).suffix.lower() in (".hwp", ".hwpx", ".zip")]

    def do_forms():
        r = run_forms(project, kb_dir=kb, date=date)
        return f"서식 {len(r.forms)}개"

    step(3, "별지 서식", do_forms, skip="" if hwp else "HWP·HWPX 첨부가 없음")

    def do_slides():
        r = make_slides(project, profile)
        return f"요약본 {r.summary_slides}장, 발표자료 {r.presentation_slides}장"

    step(4, "요약본·발표자료", do_slides)

    conv = converters_available()

    def do_package():
        r = build_package(project, profile, kb_dir=kb)
        return f"PDF {len(r.docs)}개, blocker {r.check.count('blocker')}건"

    step(5, "제출 패키지(PDF)", do_package,
         skip="" if conv["hwpx"] else "PDF 변환기가 없음 — `rfpgen setup` 뒤 `rfpgen package`")
    return res


__all__ = ["Stage", "StartResult", "default_project_dir", "project_status", "remember_kb", "resolve_kb", "run_start"]
