"""rfpgen 명령줄 도구(M1: RFP 분석기)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Annotated

import typer

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
) -> None:
    """RFP를 분석해 평가표·요구사항·작성지침·목차·쪽수 예산·추적표·질의서 초안을 만든다."""
    profile = load_profile(overrides=profile_override or [])
    if sw is not None:
        profile = profile.merged({"outline": {"is_sw_project": {"value": sw, "status": "user", "ref": "CLI"}}}, "cli")
    try:
        result = analyze(files, out, profile)
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
    typer.echo(f"  질의서 후보 : {len(rfp.questions)}건")
    sev = Counter(f.severity for f in rep.findings)
    typer.echo(f"  점검        : 오류 {sev['error']}, 경고 {sev['warning']}, 정보 {sev['info']}")
    for f in rep.findings:
        if f.severity == "error":
            typer.secho(f"    - [{f.code}] {f.message}", fg=typer.colors.RED)
    typer.echo("\n산출물:")
    for key in ("xlsx", "analysis_md", "questions_md", "rfp", "trace"):
        typer.echo(f"  {result.outputs[key]}")


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
