"""도식 자동 렌더(설계서 7.9절 '도식', M3).

흐름: 스토리보드의 절별 도식 종류(SectionPlan.figures) → 스펙(build.py, 사람이 고친 strategy/figures/<id>.json 우선)
→ 절 초안의 figure 블록 → SVG(svg.py) → PNG 200dpi(Node 사이드카, Chromium) → HWPX 본문·PPTX 장표.

PNG를 만들지 못하면(변환기 없음) 본문에는 도식 자리표시자 상자를 넣고 FIG-001로 알린다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..schemas.diagram import DiagramSpec
from ..schemas.draft import DraftBlock, SectionDraft, Storyboard
from .build import BuildContext, build_figure, load_templates, plan_figures, project_months
from .svg import PX_PER_MM, Theme, render_svg, theme_from_style


@dataclass
class FigureResult:
    id: str
    section_id: str
    title: str
    svg: Path
    png: Path | None
    width_mm: float
    height_mm: float
    error: str = ""
    assumptions: list[str] = field(default_factory=list)
    origin: str = "auto"
    scale: float = 1.0          # 본문에 넣을 때 줄인 비율(쪽 높이를 넘으면 < 1)


def spec_paths(project: Path, fig_id: str) -> tuple[Path, Path]:
    """(사람이 고친 스펙, 자동 스펙) 경로."""
    d = Path(project) / "strategy" / "figures"
    return d / f"{fig_id}.json", d / f"{fig_id}.auto.json"


def resolve_spec(project: Path, ctx: BuildContext, section_id: str, section_title: str, kind: str) -> DiagramSpec:
    """사람이 고친 strategy/figures/<id>.json이 있으면 그것을, 없으면 자동 스펙을 만들어 <id>.auto.json으로 남긴다."""
    fig_id = f"{section_id}-{kind}"
    human, auto = spec_paths(project, fig_id)
    if human.exists():
        spec = DiagramSpec.model_validate_json(human.read_text(encoding="utf-8"))
        spec.id, spec.origin = fig_id, "human"
        return spec
    spec = build_figure(kind, ctx, section_id, section_title)
    auto.parent.mkdir(parents=True, exist_ok=True)
    auto.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    return spec


def attach_figures(drafts: list[SectionDraft], storyboard: Storyboard, ctx: BuildContext, project: Path) -> None:
    """초안의 figure 블록을 스토리보드 계획대로 다시 넣는다(위치: 앞쪽 두 블록 뒤)."""
    for d in drafts:
        plan = storyboard.plan(d.section_id)
        kinds = list(plan.figures) if plan else []
        d.blocks = [b for b in d.blocks if b.kind != "figure"]
        pos = min(2, len(d.blocks))
        for kind in kinds:
            spec = resolve_spec(project, ctx, d.section_id, d.title, kind)
            d.blocks.insert(pos, DraftBlock(kind="figure", figure=spec))
            pos += 1


def render_figures(specs: list[DiagramSpec], out_dir: Path, theme: Theme, *, dpi: int = 200) -> dict[str, FigureResult]:
    """SVG를 쓰고 PNG로 바꾼다. 변환기가 없거나 실패하면 png=None과 사유를 돌려준다."""
    from ..render.pdf import RenderError, svgs_to_png

    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, FigureResult] = {}
    pairs: list[tuple[Path, Path]] = []
    for spec in specs:
        svg, w, h = render_svg(spec, theme)
        svg_path = out_dir / f"{spec.id}.svg"
        svg_path.write_text(svg, encoding="utf-8")
        png = out_dir / f"{spec.id}.png"
        if png.exists():
            png.unlink()
        pairs.append((svg_path, png))
        results[spec.id] = FigureResult(id=spec.id, section_id=spec.id.rsplit("-", 1)[0], title=spec.title, svg=svg_path,
                                        png=png, width_mm=w / PX_PER_MM, height_mm=h / PX_PER_MM,
                                        assumptions=list(spec.assumptions), origin=spec.origin)
    try:
        svgs_to_png(pairs, dpi=dpi)
    except RenderError as exc:
        for r in results.values():
            r.png, r.error = None, str(exc)
    (out_dir / "figures.json").write_text(json.dumps(
        [{"id": r.id, "title": r.title, "svg": r.svg.name, "png": r.png.name if r.png else None,
          "size_mm": [round(r.width_mm, 1), round(r.height_mm, 1)], "origin": r.origin, "error": r.error}
         for r in results.values()], ensure_ascii=False, indent=2), encoding="utf-8")
    return results


def figure_specs(drafts: list[SectionDraft]) -> list[DiagramSpec]:
    return [b.figure for d in drafts for b in d.blocks if b.kind == "figure" and b.figure is not None]


__all__ = ["BuildContext", "FigureResult", "Theme", "attach_figures", "build_figure", "figure_specs", "load_templates",
           "plan_figures", "project_months", "render_figures", "render_svg", "resolve_spec", "spec_paths",
           "theme_from_style"]
