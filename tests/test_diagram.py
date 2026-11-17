"""도식 자동 렌더 테스트(M3): 스펙 생성, SVG 배치, 초안·HWPX·장표 연결, 사람이 고친 스펙 반영."""

from __future__ import annotations

import json
import zipfile

import pytest
from lxml import etree
from typer.testing import CliRunner

from rfpgen.cli import app
from rfpgen.diagram import BuildContext, build_figure, plan_figures, project_months, render_svg, theme_from_style
from rfpgen.diagram.svg import text_w, wrap
from rfpgen.draft.pipeline import refresh_figures, run_draft
from rfpgen.kb import init_kb, load_kb
from rfpgen.pipeline import analyze
from rfpgen.profile import load_profile
from rfpgen.render.hwpx_writer import load_style
from rfpgen.render.pdf import converters_available
from rfpgen.schemas.common import Extracted
from rfpgen.schemas.diagram import DiagramSpec
from rfpgen.schemas.kb import CompanyKB, Person
from rfpgen.schemas.rfp import Requirement, Rfp

needs_svg = pytest.mark.skipif(not converters_available()["svg"], reason="SVG→PNG 변환기(Node·Playwright)가 없습니다")
SVG_NS = "{http://www.w3.org/2000/svg}"


def _rfp(period: str | None = None, agency: str | None = None, reqs: list[tuple[str, str]] | None = None) -> Rfp:
    rfp = Rfp()
    if period:
        rfp.notice.period = Extracted[str](value=period)
    if agency:
        rfp.notice.agency = Extracted[str](value=agency)
    rfp.notice.title = Extracted[str](value="2026년 통합민원시스템 고도화 사업")
    rfp.requirements = [Requirement(id=i, prefix=i[:3], name=n, definition="감리 수검 지원" if i == "PMR-001" else "")
                        for i, n in (reqs or [])]
    return rfp


def _svg_texts(svg: str) -> str:
    root = etree.fromstring(svg.encode("utf-8"))
    return " ".join("".join(t.itertext()) for t in root.iter(f"{SVG_NS}text"))


# ---------------------------------------------------------------- 스펙

def test_project_months():
    assert project_months(_rfp("계약일로부터 8개월")) == (8, None)
    assert project_months(_rfp("2026. 3. ~ 2026. 12."))[0] == 10
    assert project_months(_rfp("착수일로부터 300일"))[0] == 10
    months, why = project_months(_rfp())
    assert months == 6 and "6개월로 가정" in why


def test_build_specs_use_only_rfp_and_kb():
    kb = CompanyKB(people=[Person(id="H-001", role="PM", grade="특급", years=18),
                           Person(id="H-002", role="개발자", grade="고급", years=9),
                           Person(id="H-003", role="개발자", grade="중급", years=5),
                           Person(id="H-004", role="품질보증", grade="고급", years=11)])
    kb.identity.name = "(주)예시정보"
    rfp = _rfp("계약일로부터 10개월", agency="비 고", reqs=[("SFR-001", "민원 신청 관리 기능"), ("SFR-002", "통계 조회"),
                                                         ("SER-001", "개인정보 암호화"), ("PMR-001", "사업관리")])
    ctx = BuildContext(rfp=rfp, kb=kb, title=rfp.notice.title.value)

    gantt = build_figure("gantt", ctx, "S-6-1", "추진 일정")
    assert gantt.months == 10 and gantt.id == "S-6-1-gantt"
    bars = [t for t in gantt.tasks if not t.milestone]
    assert bars[0].start == 0 and max(t.end for t in bars) == 10
    assert [t.label for t in gantt.tasks if t.milestone] == ["착수보고", "중간보고", "완료보고"]

    gov = build_figure("org", ctx, "S-3-3", "사업 추진 체계")
    ext = {n.label for n in gov.nodes if n.group == "external"}
    assert ext == {"발주기관", "감리"}   # 머리글('비 고')은 기관명이 아니다. 감리는 RFP에 있을 때만
    team = build_figure("org", ctx, "S-5-1", "투입 인력 및 조직")
    notes = {n.label: n.note for n in team.nodes}
    assert notes["사업관리(PM)"] == "특급 · 18년" and notes["개발자"] == "2명 (고급 1, 중급 1)"
    assert notes["품질보증(QA)"] == "고급 · 11년"
    assert not any(n.group == "external" for n in team.nodes)

    layers = build_figure("layers", ctx, "S-4-1", "목표 시스템 구성")
    names = {lay.name: lay.items for lay in layers.layers}
    assert names["업무 서비스"] == ["민원 신청 관리", "통계 조회"] and names["보안"] == ["개인정보 암호화"]
    assert any("인프라" in a for a in layers.assumptions)

    for spec in (gantt, gov, team, layers, build_figure("wbs", ctx, "S-1", "WBS"), build_figure("flow", ctx, "S-2", "방법론")):
        assert "예시정보" not in " ".join(spec.labels())               # 회사명은 넣지 않는다

    empty = build_figure("org", BuildContext(rfp=rfp, kb=CompanyKB(), title="사업"), "S-5-1", "조직")
    assert any("[확인 필요" in n.note for n in empty.nodes) and empty.assumptions


def test_project_type_templates():
    ctx = BuildContext(rfp=_rfp("12개월"), kb=CompanyKB(), title="2026년 행정정보시스템 유지관리 용역")
    assert ctx.project_type["key"] == "maintenance"
    flow = build_figure("flow", ctx, "S-1", "수행 방안")
    assert flow.nodes[1].label == "운영·유지관리"
    assert BuildContext(rfp=_rfp(), kb=CompanyKB(), title="정보화전략계획(ISP) 수립").project_type["key"] == "consulting"


# ---------------------------------------------------------------- SVG

def test_svg_layout_contains_labels_and_respects_font(tmp_path):
    style = load_style()
    theme = theme_from_style(style, min_pt=12)
    assert theme.font_px == pytest.approx(16.0)                         # RFP 표 최소 12pt를 지킨다
    kb = CompanyKB(people=[Person(id="H-001", role="PM", grade="특급", years=18)])
    ctx = BuildContext(rfp=_rfp("8개월", reqs=[("SFR-001", "민원 신청 관리"), ("SIR-001", "행정망 연계")]), kb=kb, title="사업")
    for kind, title in (("gantt", "일정"), ("org", "추진 체계"), ("wbs", "WBS"), ("flow", "방법론"), ("layers", "구성")):
        spec = build_figure(kind, ctx, "S-1", title)
        svg, w, h = render_svg(spec, theme)
        root = etree.fromstring(svg.encode("utf-8"))                    # 올바른 XML
        assert float(root.get("width")) == pytest.approx(round(theme.width), abs=1) and 40 < h < 900
        texts = _svg_texts(svg).replace(" ", "")
        for label in spec.labels()[1:]:                                 # 제목(캡션)은 그림 밖에 쓴다
            for part in label.replace("\n", " ").split():
                assert part.replace(" ", "")[:4] in texts, (kind, part)
        sizes = {float(t.get("font-size")) for t in root.iter(f"{SVG_NS}text")}
        assert min(sizes) >= theme.font_px - 0.05


def test_wrap_fits_width():
    for s in ("글로벌 독립형 시스템 구축 및 운영 환경 전환", "WEB/WAS DBMS Storage", "가" * 40):
        for line in wrap(s, 120, 14):
            assert text_w(line, 14) <= 120 + 1e-6


# ---------------------------------------------------------------- 초안·본문·장표 연결

@pytest.fixture(scope="module")
def drafted(tmp_path_factory):
    from conftest import (
        DECLARED_TABLE,
        DETAILS,
        EVAL_QUAL,
        EVAL_QUAL_SPANS,
        EVAL_QUANT,
        EVAL_QUANT_SPANS,
        GUIDE_LINES,
        SUMMARY_SPANS,
        SUMMARY_TABLE,
        _hwpx_table,
        detail_table,
    )
    from hwpx import HwpxDocument

    base = tmp_path_factory.mktemp("fig")
    doc = HwpxDocument.new()
    _hwpx_table(doc, DECLARED_TABLE, {})
    _hwpx_table(doc, SUMMARY_TABLE, SUMMARY_SPANS)
    for d in DETAILS:
        rows, spans = detail_table(*d)
        _hwpx_table(doc, rows, spans)
    for line in GUIDE_LINES:
        doc.add_paragraph(line)
    doc.add_paragraph("가. 정량적 평가(20점)")
    _hwpx_table(doc, EVAL_QUANT, EVAL_QUANT_SPANS)
    doc.add_paragraph("나. 정성적 평가(70점)")
    _hwpx_table(doc, EVAL_QUAL, EVAL_QUAL_SPANS)
    src = base / "제안요청서.hwpx"
    doc.save_to_path(str(src))
    profile = load_profile()
    project = base / "proj"
    analyze([src], project, profile)
    kb = base / "kb"
    init_kb(kb)
    res = run_draft(project, profile, kb_dir=kb)
    return project, kb, profile, res


def test_draft_places_figures(drafted):
    project, kb, profile, res = drafted
    planned = {p.section_id: p.figures for p in res.storyboard.sections if p.figures}
    assert sorted(k for v in planned.values() for k in v) == ["flow", "gantt", "layers", "org"]
    blocks = [(d.section_id, b.figure) for d in res.drafts for b in d.blocks if b.kind == "figure"]
    assert {f"{sid}-{kind}" for sid, kinds in planned.items() for kind in kinds} == {f.id for _, f in blocks}
    gantt = next(f for _, f in blocks if f.kind == "gantt")
    assert gantt.months == 8                                            # RFP '계약일로부터 8개월'
    for _, f in blocks:
        assert (project / "strategy" / "figures" / f"{f.id}.auto.json").exists()
        assert (project / "out" / "figures" / f"{f.id}.svg").exists()
    md = (project / "strategy" / "storyboard.md").read_text(encoding="utf-8")
    assert "- 도식: gantt" in md
    # 도식 속 글은 수치 근거 점검·글자 수에서 빼고, 자리표시자·블라인드 점검에는 넣는다
    d = next(d for d in res.drafts if any(b.kind == "figure" for b in d.blocks))
    fig = next(b.figure for b in d.blocks if b.kind == "figure")
    assert fig.labels()[1] in d.all_text() and fig.labels()[1] not in d.all_text(figures=False)
    rules = {f.rule for f in res.check.findings}
    assert "FIG-002" in rules                                           # 템플릿 가정은 사람에게 알린다


@needs_svg
def test_figures_rendered_into_hwpx_and_slides(drafted):
    from pptx import Presentation

    from rfpgen.package import make_slides

    project, kb, profile, res = drafted
    assert res.figures and all(f.png is not None and f.png.exists() for f in res.figures.values())
    for f in res.figures.values():
        from PIL import Image

        with Image.open(f.png) as im:
            assert abs(im.width - round(f.width_mm / 25.4 * 200)) <= 2      # 200dpi
    with zipfile.ZipFile(project / "out" / "proposal.hwpx") as zf:
        names = zf.namelist()
        assert sum(1 for n in names if n.startswith("BinData/")) == len(res.figures)
        body = zf.read("Contents/section0.xml").decode("utf-8")
    assert "[그림 1]" in body and "사업 추진 일정(안)" in body and "<hp:pic" in body
    assert "FIG-001" not in {f.rule for f in res.check.findings}
    slides = make_slides(project, profile)
    pics = [s for s in Presentation(str(slides.summary)).slides if any(sh.shape_type == 13 for sh in s.shapes)]
    assert pics                                                         # 요약본에 도식 그림


def test_render_failure_leaves_placeholder(drafted, tmp_path, monkeypatch):
    import shutil

    project = tmp_path / "nofig"
    shutil.copytree(drafted[0], project)
    monkeypatch.setenv("RFPGEN_SIDECAR_DIR", str(tmp_path / "없는-사이드카"))
    res = refresh_figures(project, load_profile(), kb_dir=drafted[1])
    assert all(f.png is None for f in res.figures.values())
    fig1 = [f for f in res.check.findings if f.rule == "FIG-001"]
    assert len(fig1) == len(res.figures)
    with zipfile.ZipFile(project / "out" / "proposal.hwpx") as zf:
        body = zf.read("Contents/section0.xml").decode("utf-8")
    assert "[도식 자리:" in body and "<hp:pic" not in body


def test_human_spec_overrides_and_cli(drafted, tmp_path):
    import shutil

    project = tmp_path / "edit"
    shutil.copytree(drafted[0], project)
    kb = drafted[1]
    auto = next((project / "strategy" / "figures").glob("*-gantt.auto.json"))
    spec = DiagramSpec.model_validate_json(auto.read_text(encoding="utf-8"))
    spec.title = "단계별 상세 일정"
    spec.tasks = spec.tasks[:2]
    (auto.parent / auto.name.replace(".auto.json", ".json")).write_text(spec.model_dump_json(), encoding="utf-8")
    # 스토리보드에서 조직도를 빼면 그 절의 조직도도 빠진다
    sb_path = project / "strategy" / "storyboard.json"
    sb = json.loads(sb_path.read_text(encoding="utf-8"))
    for sec in sb["sections"]:
        sec["figures"] = [k for k in sec.get("figures", []) if k != "org"]
    sb_path.write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    before = {p.name for p in (project / "sections").glob("*.json")}
    r = CliRunner().invoke(app, ["figures", str(project), "--kb", str(kb)])
    assert r.exit_code == 0, r.output
    assert "단계별 상세 일정" in r.output and "(human)" in r.output
    after = {p.name for p in (project / "sections").glob("*.json")}
    assert len(after) > len(before)                                     # 새 판으로 저장(이전 판은 남는다)
    from rfpgen.package import latest_drafts
    from rfpgen.schemas.plan import Outline

    outline = Outline.model_validate_json((project / "plan" / "outline.json").read_text(encoding="utf-8"))
    figs = [b.figure for d in latest_drafts(project, outline) for b in d.blocks if b.kind == "figure"]
    assert {f.kind for f in figs} == {"gantt", "flow", "layers"}
    g = next(f for f in figs if f.kind == "gantt")
    assert g.origin == "human" and g.title == "단계별 상세 일정" and len(g.tasks) == 2
    assert load_kb(kb).people                                           # KB는 건드리지 않았다


def test_plan_figures_respects_limits(drafted):
    from rfpgen.schemas.plan import Outline

    project = drafted[0]
    rfp = Rfp.model_validate_json(sorted(project.glob("rfp/rfp.v*.json"))[-1].read_text(encoding="utf-8"))
    outline = Outline.model_validate_json((project / "plan" / "outline.json").read_text(encoding="utf-8"))
    planned = plan_figures(outline, rfp)
    kinds = [k for v in planned.values() for k in v]
    assert kinds.count("gantt") <= 1 and kinds.count("org") <= 2 and kinds.count("layers") <= 1
