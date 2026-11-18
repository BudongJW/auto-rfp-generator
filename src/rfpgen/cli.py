"""rfpgen 명령줄 도구."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Annotated

import typer

from .diff import diff_project
from .parse import UnsafeInputError, collect_inputs, parse_document
from .pipeline import analyze
from .profile import load_profile
from .workflow import remember_kb, resolve_kb

app = typer.Typer(add_completion=False, no_args_is_help=True, help=(
    "나라장터·조달청 기술제안서 작성 작업대.\n\n"
    "처음이면: rfpgen setup → rfpgen start 제안요청서.hwp 공고문.pdf → rfpgen status 프로젝트폴더"))

START, STEPS, TOOLS = "시작하기", "단계별 작업", "도구"


def _utf8_output() -> None:
    """출력을 파일·파이프로 보낼 때 Windows 기본 인코딩(cp949·cp1252)은 '✓' 같은 기호를 못 써서 멈춘다.
    UTF-8이 아니면 UTF-8로 바꾼다(콘솔 창에 바로 쓸 때는 Python이 이미 UTF-8로 쓴다)."""
    import sys

    for stream in (sys.stdout, sys.stderr):
        enc = (getattr(stream, "encoding", None) or "").lower().replace("-", "").replace("_", "")
        if enc not in ("utf8", "utf8sig") and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


@app.callback()
def _main() -> None:
    _utf8_output()


@app.command("setup", rich_help_panel=START)
def setup_cmd(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="실행할 명령만 보여 줌")] = False,
    no_browser: Annotated[bool, typer.Option("--no-browser", help="Chromium 내려받기를 건너뜀(이미 있는 Chrome을 쓸 때)")] = False,
) -> None:
    """처음 한 번: PDF·도식 변환용 Node 사이드카와 Chromium을 설치하고, LibreOffice·한글 글꼴 설치 방법을 알려 준다."""
    from .installer import run_setup

    res = run_setup(dry_run=dry_run, browser=not no_browser)
    for line in res.lines:
        color = typer.colors.RED if line.lstrip().startswith("✗") else typer.colors.YELLOW if line.startswith("!") else None
        typer.secho(line, fg=color)
    if not res.ok:
        raise typer.Exit(code=1)


@app.command("sample", rich_help_panel=START)
def sample_cmd(
    output: Annotated[Path, typer.Argument(help="만들 파일")] = Path("예제_제안요청서.hwpx"),
) -> None:
    """체험용 가상 제안요청서(HWPX)를 만든다 — 실제 RFP 없이 `rfpgen start`를 해 볼 수 있다."""
    from .sample import build_sample_rfp

    path = build_sample_rfp(output)
    typer.echo(f"만들었습니다: {path}")
    typer.echo(f"다음: rfpgen start {path}")


@app.command("start", rich_help_panel=START)
def start_cmd(
    files: Annotated[list[Path], typer.Argument(help="RFP·공고 첨부(HWP, HWPX, PDF, DOCX, ZIP)", exists=True, dir_okay=False)],
    out: Annotated[Path | None, typer.Option("--out", "-o", help="프로젝트 폴더(기본: projects/<첫 파일 이름>)")] = None,
    kb: Annotated[Path | None, typer.Option("--kb", help="회사 KB 폴더(없으면 회사 정보 칸은 비워 둠)")] = None,
    llm: Annotated[bool, typer.Option("--llm/--no-llm", help="Claude API로 보조 분석·초안 작성(RFP_ANTHROPIC_API_KEY 필요)")] = False,
    llm_model: Annotated[str | None, typer.Option("--llm-model")] = None,
    date: Annotated[str | None, typer.Option("--date", help="별지 날짜 칸(YYYY-MM-DD, 기본: 오늘)")] = None,
    profile_override: Annotated[list[Path] | None, typer.Option("--profile", "-p")] = None,
) -> None:
    """한 번에 실행: 분석 → 초안 → 별지 서식 → 요약본·발표자료 → 제출 패키지. 끝나면 다음 할 일을 알려 준다."""
    import datetime as dt

    from .workflow import default_project_dir, run_start

    project = out or default_project_dir(files[0])
    provider = None
    if llm:
        from .llm.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider(model=llm_model)
    try:
        day = dt.date.fromisoformat(date) if date else None
    except ValueError as exc:
        typer.secho(f"오류: 날짜 형식이 틀렸습니다(YYYY-MM-DD): {date}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    typer.secho(f"프로젝트: {project}" + (f"  KB: {kb}" if kb else "  (KB 없음 — 회사 정보 칸은 비워 둡니다)"), bold=True)
    res = run_start(files, project, load_profile(overrides=profile_override or []), kb=kb, provider=provider,
                    date=day, echo=typer.echo)
    _echo_status(project)
    if not res.steps or not res.steps[0].ok:
        raise typer.Exit(code=1)


@app.command("status", rich_help_panel=START)
def status_cmd(project: Annotated[Path, typer.Argument(help="프로젝트 폴더", exists=True, file_okay=False)]) -> None:
    """지금 어디까지 했고 다음에 무엇을 하면 되는지 보여 준다."""
    _echo_status(project)


def _pad(text: str, width: int) -> str:
    """한글(전각)을 두 칸으로 세어 오른쪽을 채운다."""
    import unicodedata

    used = sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in text)
    return text + " " * max(width - used, 1)


def _echo_status(project: Path) -> None:
    from .workflow import project_status

    stages, todo = project_status(project)
    typer.secho(f"\n진행 상태 — {project}", bold=True)
    for st in stages:
        mark, color = ("✓", typer.colors.GREEN) if st.done else ("·", None)
        typer.secho(f"  {mark} {_pad(st.title, 18)} {st.detail}", fg=color)
    if todo:
        typer.secho("\n다음 할 일", bold=True)
        for i, t in enumerate(todo, start=1):
            typer.echo(f"  {i}. {t}")


@app.command("analyze", rich_help_panel=STEPS)
def analyze_cmd(
    files: Annotated[list[Path], typer.Argument(help="RFP·공고 첨부(PDF, HWP, HWPX, DOCX, ZIP)", exists=True, dir_okay=False)],
    out: Annotated[Path, typer.Option("--out", "-o", help="프로젝트 폴더")] = Path("projects/default"),
    profile_override: Annotated[list[Path] | None, typer.Option("--profile", "-p", help="프로필 오버라이드 YAML(여러 개 가능)")] = None,
    sw: Annotated[bool | None, typer.Option("--sw/--no-sw", help="SW사업 여부(상생협력·하도급 장 자동 삽입)")] = None,
    llm: Annotated[bool, typer.Option("--llm/--no-llm", help="LLM 보조 추출(Claude API, RFP_ANTHROPIC_API_KEY 또는 ANTHROPIC_API_KEY 필요)")] = False,
    llm_model: Annotated[str | None, typer.Option("--llm-model", help="모델 ID(기본: RFPGEN_LLM_MODEL 또는 최신 Opus 계열)")] = None,
) -> None:
    """RFP를 분석해 평가표·요구사항·작성지침·목차·쪽수 예산·추적표·질의서 초안을 만든다."""
    profile = load_profile(overrides=profile_override or [])
    provider = None
    if llm:
        from .llm.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider(model=llm_model)
    if sw is not None:
        profile = profile.merged({"outline": {"is_sw_project": {"value": sw, "status": "user", "ref": "CLI"}}}, "cli")
    audit_before = _audit_before(out)
    try:
        result = analyze(files, out, profile, llm_provider=provider)
    except UnsafeInputError as exc:
        typer.secho(f"오류: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    rfp, rep = result.rfp, result.report
    n = rfp.notice
    typer.secho(f"\n분석 완료 — v{result.version}  ({result.project_dir})", bold=True)
    typer.echo(f"  사업명      : {n.title.value if n.title else '(찾지 못함)'}")
    typer.echo(f"  계약방법    : {n.contract_method.value}")
    ev = rfp.evaluation
    typer.echo(f"  평가표      : 부문 {len(ev.areas)}개, 항목 {len(ev.items())}개, 합계 {rep.stats.get('eval_total_points', 0):g}점")
    declared = rep.stats.get("declared_requirements")
    typer.echo(f"  요구사항    : {len(rfp.requirements)}건" + (f" (RFP 선언 {declared}건)" if declared else ""))
    typer.echo(f"  목차        : {result.outline.origin}, 장 {len(result.outline.chapters)}개")
    typer.echo(f"  쪽수 예산   : {result.budget.main_page_limit}쪽 ({result.budget.main_page_limit_source})")
    typer.echo(f"  추적표      : 커버리지 {result.trace.coverage():.0%}")
    stated = sum(1 for c in rfp.compliance if c.origin == "stated")
    typer.echo(f"  무효·감점   : 원문 {stated}건, 권고 {len(rfp.compliance) - stated}건 / 평가규칙 {len(ev.rules)}건")
    typer.echo(f"  질의서 후보 : {len(rfp.questions)}건")
    if llm:
        st = rep.stats
        typer.echo(f"  LLM 보조    : 호출 {st.get('llm_calls', 0)}회, 입력 {st.get('llm_input_tokens', 0):,} / 캐시 읽기 "
                   f"{st.get('llm_cache_read_tokens', 0):,} / 출력 {st.get('llm_output_tokens', 0):,} 토큰"
                   f" (기록: {result.project_dir / 'audit' / 'llm_calls.jsonl'})")
        _echo_cost(result.project_dir, profile, audit_before)
        for f in rep.findings:
            if f.code in ("LLM-ERROR", "LLM-REFUSAL"):
                typer.secho(f"    - [{f.code}] {f.message}", fg=typer.colors.YELLOW)
    sev = Counter(f.severity for f in rep.findings)
    typer.echo(f"  점검        : 오류 {sev['error']}, 경고 {sev['warning']}, 정보 {sev['info']}")
    for f in rep.findings:
        if f.severity == "error":
            typer.secho(f"    - [{f.code}] {f.message}", fg=typer.colors.RED)
    typer.echo("\n산출물:")
    for key in ("xlsx", "analysis_md", "questions_md", "rfp", "trace"):
        typer.echo(f"  {result.outputs[key]}")


kb_app = typer.Typer(no_args_is_help=True, help="회사 지식베이스(KB) — 실적·인력·인증·수치·재사용 문단")
app.add_typer(kb_app, name="kb", rich_help_panel=STEPS)


@kb_app.command("init")
def kb_init_cmd(folder: Annotated[Path, typer.Argument(help="만들 KB 폴더")]) -> None:
    """예시 KB 폴더(company.yaml, projects.csv, people.csv, certifications.csv, content/)를 만든다."""
    from .kb import init_kb

    made = init_kb(folder)
    typer.echo(f"{folder}: 파일 {len(made)}개를 만들었습니다(이미 있는 파일은 그대로 둠)")
    for p in made:
        typer.echo(f"  {p}")


@kb_app.command("check")
def kb_check_cmd(folder: Annotated[Path, typer.Argument(exists=True, file_okay=False)]) -> None:
    """KB를 읽고 ID 중복, 설명 속 숫자, 유효기간 만료, 블라인드 사전 누락을 점검한다."""
    from .kb import check_kb, load_kb

    kb = load_kb(folder)
    typer.echo(f"fact {len(kb.facts)} · 실적 {len(kb.projects)} · 인력 {len(kb.people)} · 인증 {len(kb.certifications)} · "
               f"재사용 문단 {len(kb.content)}")
    warnings = check_kb(kb)
    for w in warnings:
        typer.secho(f"  경고: {w}", fg=typer.colors.YELLOW)
    if not warnings:
        typer.secho("  문제 없음", fg=typer.colors.GREEN)


@app.command("draft", rich_help_panel=STEPS)
def draft_cmd(
    project: Annotated[Path, typer.Argument(help="analyze로 만든 프로젝트 폴더", exists=True, file_okay=False)],
    kb: Annotated[Path | None, typer.Option("--kb", help="회사 KB 폴더(생략하면 이 프로젝트에 지난번 쓴 폴더)")] = None,
    llm: Annotated[bool, typer.Option("--llm/--no-llm", help="LLM으로 스토리보드·본문 생성(없으면 작성용 골격)")] = False,
    llm_model: Annotated[str | None, typer.Option("--llm-model")] = None,
    llm_share_kb: Annotated[bool, typer.Option("--llm-share-kb", help="KB의 ID·설명·재사용 문단을 LLM에 보냄(값은 보내지 않음)")] = False,
    section: Annotated[list[str] | None, typer.Option("--section", help="이 절만 다시 씀(예: S-3-1, 여러 번 가능)")] = None,
    refresh_storyboard: Annotated[bool, typer.Option("--refresh-storyboard", help="기존 storyboard.json을 무시하고 새로 만듦")] = False,
    style: Annotated[Path | None, typer.Option("--style", help="스타일 YAML(기본: 보고서체)")] = None,
    profile_override: Annotated[list[Path] | None, typer.Option("--profile", "-p")] = None,
) -> None:
    """스토리보드와 절 초안을 만들고 본문 HWPX(out/proposal.hwpx)와 제출 전 점검 리포트를 낸다."""
    from .draft.pipeline import run_draft

    profile = load_profile(overrides=profile_override or [])
    provider = None
    if llm:
        from .llm.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider(model=llm_model, share_internal=llm_share_kb)
    audit_before = _audit_before(project)
    try:
        kb = resolve_kb(project, kb)
        res = run_draft(project, profile, kb_dir=kb, provider=provider, share_kb=llm_share_kb,
                        sections=set(section) if section else None, refresh_storyboard=refresh_storyboard, style_path=style)
    except FileNotFoundError as exc:
        typer.secho(f"오류: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    remember_kb(project, kb)
    origins = Counter(d.origin for d in res.drafts)
    rep = res.check
    typer.secho(f"\n초안 완료 — {res.project}", bold=True)
    typer.echo(f"  스토리보드  : {res.storyboard.origin}, win theme {len(res.storyboard.win_themes)}개, "
               f"자료 요청 {len(res.storyboard.data_requests)}건")
    typer.echo(f"  절 초안     : {len(res.drafts)}개 (" + ", ".join(f"{k} {v}" for k, v in origins.items()) + ")")
    typer.echo(f"  확인 필요   : {sum(len(d.placeholders) for d in res.drafts)}곳")
    typer.echo(f"  추정 쪽수   : {rep.stats.get('estimated_pages')}쪽")
    _echo_figures(res.figures)
    typer.echo(f"  점검        : blocker {rep.count('blocker')}, major {rep.count('major')}, minor {rep.count('minor')}")
    if res.llm_usage:
        u = res.llm_usage
        typer.echo(f"  LLM         : 호출 {u.get('calls', 0)}회, 입력 {u.get('input_tokens', 0):,} / 캐시 읽기 "
                   f"{u.get('cache_read_input_tokens', 0):,} / 출력 {u.get('output_tokens', 0):,} 토큰")
        _echo_cost(project, profile, audit_before)
    for n in res.notes:
        typer.secho(f"  - {n}", fg=typer.colors.YELLOW)
    typer.echo("\n산출물:")
    for key in ("proposal", "storyboard_md", "trace_xlsx", "check_md"):
        typer.echo(f"  {res.outputs[key]}")


def _echo_cost(project: Path, profile, since_line: int) -> None:
    from .llm.cost import estimate

    est = estimate(project / "audit" / "llm_calls.jsonl", profile.value("llm.pricing_usd_per_mtok") or {},
                   since_line=since_line)
    if est.calls and est.by_model:
        extra = f", 단가 없는 모델: {', '.join(est.unpriced)}" if est.unpriced else ""
        typer.echo(f"  추정 비용   : 약 ${est.usd:.2f} (프로필 단가 기준, 실제 청구는 Console 확인{extra})")
    elif est.calls:
        typer.echo("  추정 비용   : 단가 미설정 — 프로필 llm.pricing_usd_per_mtok에 모델별 단가를 넣으면 보여 줍니다")


def _audit_before(project: Path) -> int:
    from .llm.cost import audit_lines

    return audit_lines(project / "audit" / "llm_calls.jsonl")


def _echo_figures(figs: dict) -> None:
    if not figs:
        return
    done = sum(1 for f in figs.values() if f.png is not None)
    typer.echo(f"  도식        : {len(figs)}개(그림 변환 {done}개) — " + ", ".join(f.title for f in list(figs.values())[:5]))
    if done < len(figs):
        err = next(f.error for f in figs.values() if f.png is None)
        typer.secho(f"    그림 변환 실패 — 자리표시 상자를 넣었습니다: {err[:120]}", fg=typer.colors.YELLOW)


@app.command("figures", rich_help_panel=STEPS)
def figures_cmd(
    project: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    kb: Annotated[Path | None, typer.Option("--kb", help="회사 KB 폴더(생략하면 지난번 폴더)")] = None,
    style: Annotated[Path | None, typer.Option("--style")] = None,
    profile_override: Annotated[list[Path] | None, typer.Option("--profile", "-p")] = None,
) -> None:
    """절 초안은 그대로 두고 도식만 다시 만든다(strategy/figures/<id>.json으로 고친 스펙 반영, LLM 호출 없음)."""
    from .draft.pipeline import refresh_figures

    try:
        res = refresh_figures(project, load_profile(overrides=profile_override or []), kb_dir=resolve_kb(project, kb),
                              style_path=style)
    except FileNotFoundError as exc:
        typer.secho(f"오류: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    typer.secho(f"\n도식 다시 만듦 — {project / 'out' / 'figures'}", bold=True)
    for f in res.figures.values():
        mark = "그림" if f.png is not None else "자리표시"
        typer.echo(f"  {f.id:18s} {f.title[:24]:24s} {f.width_mm:5.0f}×{f.height_mm:3.0f}mm {mark} ({f.origin})")
    typer.echo("  고치려면 strategy/figures/<id>.auto.json을 <id>.json으로 복사해 고친 뒤 다시 실행하세요")
    typer.echo(f"  본문: {res.outputs['proposal']}  점검: {res.outputs['check_md']}")


@app.command("slides", rich_help_panel=STEPS)
def slides_cmd(
    project: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    style: Annotated[Path | None, typer.Option("--style")] = None,
    profile_override: Annotated[list[Path] | None, typer.Option("--profile", "-p")] = None,
) -> None:
    """최신 절 초안으로 요약본(A4 가로)·발표자료(16:9) PPTX와 발표 대본·예상 질문을 만든다."""
    from .package import make_slides

    try:
        res = make_slides(project, load_profile(overrides=profile_override or []), style_path=style)
    except FileNotFoundError as exc:
        typer.secho(f"오류: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(f"요약본 {res.summary_slides}장: {res.summary}")
    typer.echo(f"발표자료 {res.presentation_slides}장: {res.presentation}")
    typer.echo(f"대본·예상 질문: {res.script}")


@app.command("package", rich_help_panel=STEPS)
def package_cmd(
    project: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    kb: Annotated[Path | None, typer.Option("--kb", help="블라인드 점검용 회사 KB 폴더(생략하면 지난번 폴더)")] = None,
    profile_override: Annotated[list[Path] | None, typer.Option("--profile", "-p")] = None,
) -> None:
    """HWPX·PPTX를 PDF로 바꾸고 파일 정보를 정리해 submission/에 모은 뒤 쪽수·용량·글꼴·블라인드를 점검한다."""
    from .package import build_package

    try:
        kb = resolve_kb(project, kb)
        res = build_package(project, load_profile(overrides=profile_override or []), kb_dir=kb)
    except FileNotFoundError as exc:
        typer.secho(f"오류: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    typer.secho(f"\n제출 패키지 — {project / 'submission'}", bold=True)
    for d in res.docs:
        typer.echo(f"  {d.doc_type:6s} {d.pdf.name:20s} {d.pages:4d}쪽 {d.size_bytes / 1024 / 1024:6.2f}MB")
    rep = res.check
    typer.echo(f"  총 용량 {rep.stats.get('total_mb')}MB · 점검 blocker {rep.count('blocker')}, major {rep.count('major')}, "
               f"minor {rep.count('minor')}")
    for n in res.notes:
        typer.secho(f"  - {n}", fg=typer.colors.YELLOW)
    typer.echo(f"  제출 전 점검표: {res.checklist}")


@app.command("forms", rich_help_panel=STEPS)
def forms_cmd(
    project: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    kb: Annotated[Path | None, typer.Option("--kb", help="회사 KB 폴더(생략하면 지난번 폴더)")] = None,
    date: Annotated[str | None, typer.Option("--date", help="서식 날짜 칸에 넣을 날짜(YYYY-MM-DD, 기본: 오늘)")] = None,
) -> None:
    """공고 첨부(HWPX·HWP)의 별지 서식을 서식별로 떼어 내 빈칸을 KB·RFP 값으로 채운다(out/forms/)."""
    import datetime as dt

    from .forms import run_forms

    try:
        day = dt.date.fromisoformat(date) if date else None
        kb = resolve_kb(project, kb)
        rep = run_forms(project, kb_dir=kb, date=day)
        remember_kb(project, kb)
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(f"오류: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    typer.secho(f"\n별지 서식 {len(rep.forms)}개 — {project / 'out' / 'forms'}", bold=True)
    for f in rep.forms:
        todo = sum(1 for x in f.findings if x.severity in ("blocker", "major", "minor"))
        typer.echo(f"  {f.form_no:10s} {f.title[:20]:20s} {f.doc_type:6s} 채운 칸 {len(f.fills):3d} · 확인할 것 {todo:2d}"
                   f"{' · 블라인드' if f.blind else ''}")
    for x in rep.findings:
        typer.secho(f"  - [{x.severity}] {x.message}", fg=typer.colors.YELLOW)
    if not rep.forms:
        typer.secho("  HWP·HWPX 첨부에서 별지 서식을 찾지 못했습니다", fg=typer.colors.YELLOW)
    typer.echo(f"  결과: {project / 'out' / 'forms' / 'forms.md'}")


@app.command("gate", rich_help_panel=STEPS)
def gate_cmd(
    project: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    gate: Annotated[str | None, typer.Argument(help="G1~G5(없으면 상태만 보여 줌)")] = None,
    by: Annotated[str | None, typer.Option("--by", help="승인자 이름(project.yaml에만 기록)")] = None,
    note: Annotated[str, typer.Option("--note", help="승인 메모")] = "",
    section: Annotated[list[str] | None, typer.Option("--section", help="G4: 이 절만 승인(여러 번 가능)")] = None,
    force: Annotated[bool, typer.Option("--force", help="승인 조건을 건너뜀(기록에 남음)")] = False,
    revoke: Annotated[bool, typer.Option("--revoke", help="승인 취소")] = False,
) -> None:
    """사람 승인 게이트 G1~G5: 상태를 보거나 승인·취소한다. 근거 산출물이 바뀌면 승인은 '재확인 필요'가 된다."""
    from .gates import STATUS_KO, GateError, approve, gate_status
    from .gates import revoke as revoke_gate

    try:
        if gate and revoke:
            revoke_gate(project, gate)
            typer.echo(f"{gate.upper()} 승인을 취소했습니다")
        elif gate:
            if not by:
                typer.secho("승인하려면 --by로 승인자를 적어 주세요(취소는 --revoke)", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=2)
            st = approve(project, gate, by=by, note=note, sections=section, force=force)
            typer.secho(f"{st.gate} {st.name}: {STATUS_KO[st.status]}", bold=True)
        states = gate_status(project)
    except GateError as exc:
        typer.secho(f"오류: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    color = {"approved": typer.colors.GREEN, "stale": typer.colors.YELLOW, "partial": typer.colors.YELLOW,
             "pending": None}
    for s in states:
        who = f" — {s.record.get('by')} {str(s.record.get('at', ''))[:16]}" if s.record else ""
        forced = " (강제)" if s.record and s.record.get("forced") else ""
        typer.secho(f"  {s.gate} {s.name:6s} {STATUS_KO[s.status]}{who}{forced}", fg=color[s.status])
        for msg in s.problems + s.notes:
            typer.echo(f"      - {msg}")


@app.command("diff", rich_help_panel=TOOLS)
def diff_cmd(
    project: Annotated[Path, typer.Argument(help="프로젝트 폴더", exists=True, file_okay=False)],
    from_version: Annotated[int | None, typer.Option("--from", help="비교 기준 버전(기본: 직전)")] = None,
    to_version: Annotated[int | None, typer.Option("--to", help="비교 대상 버전(기본: 최신)")] = None,
) -> None:
    """두 RFP 버전(사전규격·본공고·정정공고)을 항목 단위로 비교하고 영향받는 절과 재실행 단계를 보여 준다."""
    try:
        d, json_path, md_path = diff_project(project, from_version, to_version)
    except ValueError as exc:
        typer.secho(f"오류: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    typer.secho(f"v{d.from_version} → v{d.to_version}: 변경 {len(d.changes)}건, 확인 필요 {len(d.confirmations())}건", bold=True)
    for c in d.confirmations()[:20]:
        typer.secho(f"  ! [{c.target}] {c.key} {c.field or ''} {c.kind}: {(c.old or '')[:40]!r} → {(c.new or '')[:40]!r}",
                    fg=typer.colors.YELLOW)
    if d.rerun:
        typer.echo("  다시 돌릴 단계: " + ", ".join(d.rerun))
    typer.echo(f"\n산출물:\n  {md_path}\n  {json_path}")


@app.command("parse", rich_help_panel=TOOLS)
def parse_cmd(
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    as_json: Annotated[bool, typer.Option("--json", help="DocIR 전체를 JSON으로 출력")] = False,
) -> None:
    """문서 하나를 DocIR로 정규화해 요약(또는 JSON)을 출력한다."""
    files, skipped = collect_inputs([file])
    if not files:
        typer.secho(f"지원하지 않는 형식: {', '.join(skipped)}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)
    for i, f in enumerate(files, start=1):
        try:
            doc = parse_document(f, f"d{i:02d}")
        except UnsafeInputError as exc:
            typer.secho(f"오류: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2) from exc
        if as_json:
            typer.echo(doc.model_dump_json(indent=1))
            continue
        kinds = Counter(b.kind for b in doc.blocks)
        typer.echo(f"{doc.doc_id} {doc.filename} [{doc.format}, {doc.role}] 블록 {len(doc.blocks)}: {dict(kinds)}")
        for w in doc.warnings:
            typer.secho(f"  경고: {w}", fg=typer.colors.YELLOW)
        for b in doc.blocks:
            if b.kind == "heading":
                typer.echo(f"  {'  ' * ((b.level or 1) - 1)}{b.text[:70]}" + (f"  (p.{b.page})" if b.page else ""))


@app.command("doctor", rich_help_panel=START)
def doctor_cmd(
    full: Annotated[bool, typer.Option("--full", help="한글 글자가 든 SVG·HWPX를 실제로 변환해 본다(수 초)")] = False,
) -> None:
    """설치 점검: 기능별로 필요한 도구(Python 패키지, Node 사이드카, Playwright, LibreOffice, 한글 글꼴)를 확인한다."""
    from .doctor import run_doctor

    checks = run_doctor(full=full)
    mark = {"ok": ("✓", typer.colors.GREEN), "warn": ("!", typer.colors.YELLOW), "fail": ("✗", typer.colors.RED)}
    for c in checks:
        sym, color = mark[c.status]
        typer.secho(f"  {sym} {c.name:28s} {c.detail[:60]:60s} [{c.needed_for}]", fg=color)
        if c.hint:
            typer.echo(f"      → {c.hint}")
    fails = [c for c in checks if c.status == "fail"]
    warns = [c for c in checks if c.status == "warn"]
    typer.echo(f"\n결과: 실패 {len(fails)}, 경고 {len(warns)} — 경고 항목의 기능만 쓸 수 없고 나머지는 동작합니다")
    if fails:
        raise typer.Exit(code=1)


@app.command("profile", rich_help_panel=TOOLS)
def profile_cmd(
    profile_override: Annotated[list[Path] | None, typer.Option("--profile", "-p")] = None,
) -> None:
    """프로필 값을 상태(verified/provisional/user)와 출처와 함께 보여 준다."""
    profile = load_profile(overrides=profile_override or [])
    typer.secho(f"{profile.name} — {profile.description}", bold=True)
    for key, pv in profile.items():
        color = {"verified": typer.colors.GREEN, "provisional": typer.colors.YELLOW}.get(pv.status)
        value = str(pv.value)
        typer.secho(f"  {key} = {value[:80]}{'…' if len(value) > 80 else ''}", fg=color)
        typer.echo(f"      [{pv.status}] {pv.ref}  ({pv.layer})")


if __name__ == "__main__":  # pragma: no cover
    app()
