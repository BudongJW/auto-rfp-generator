"""rfpgen 명령줄 도구(M1: RFP 분석기)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Annotated

import typer

from .diff import diff_project
from .parse import UnsafeInputError, collect_inputs, parse_document
from .pipeline import analyze
from .profile import load_profile

app = typer.Typer(add_completion=False, no_args_is_help=True,
                  help="나라장터·조달청 제안서 자동생성기 — M1 RFP 분석기")


@app.command("analyze")
def analyze_cmd(
    files: Annotated[list[Path], typer.Argument(help="RFP·공고 첨부(PDF, HWP, HWPX, DOCX, ZIP)", exists=True, dir_okay=False)],
    out: Annotated[Path, typer.Option("--out", "-o", help="프로젝트 폴더")] = Path("projects/default"),
    profile_override: Annotated[list[Path] | None, typer.Option("--profile", "-p", help="프로필 오버라이드 YAML(여러 개 가능)")] = None,
    sw: Annotated[bool | None, typer.Option("--sw/--no-sw", help="SW사업 여부(상생협력·하도급 장 자동 삽입)")] = None,
    llm: Annotated[bool, typer.Option("--llm/--no-llm", help="LLM 보조 추출(Claude API, ANTHROPIC_API_KEY 필요)")] = False,
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


@app.command("diff")
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


@app.command("parse")
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


@app.command("profile")
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
