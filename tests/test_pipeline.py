from __future__ import annotations

import json

import yaml
from openpyxl import load_workbook
from typer.testing import CliRunner

from rfpgen.cli import app
from rfpgen.profile import load_profile
from rfpgen.report.xlsx import TRACE_COLUMNS


def test_analyze_cli_end_to_end(hwpx_file, tmp_path):
    out = tmp_path / "project"
    result = CliRunner().invoke(app, ["analyze", str(hwpx_file), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert "요구사항    : 5건" in result.output
    assert "커버리지 100%" in result.output

    rfp = json.loads((out / "rfp" / "rfp.v1.json").read_text(encoding="utf-8"))
    assert rfp["notice"]["title"]["value"] == "2026년 통합민원시스템 고도화 사업"
    assert len(rfp["requirements"]) == 5
    assert rfp["guideline"]["main_page_limit"]["value"] == 100

    wb = load_workbook(out / "out" / "analysis.xlsx")
    assert wb.sheetnames == ["추적표", "평가표", "요구사항", "목차·쪽수", "작성지침", "무효·감점 사유", "평가규칙",
                             "질의서 후보", "점검 결과"]
    header = [c.value for c in wb["추적표"][1]]
    assert header == TRACE_COLUMNS
    assert header[:8] == ["요구사항 ID", "명칭", "분류", "연결 평가항목", "제안 요약", "수용 여부", "제안서 쪽", "RFP 원문 위치"]
    assert wb["추적표"].max_row == 6

    md = (out / "out" / "analysis.md").read_text(encoding="utf-8")
    assert "## 평가표" in md and "블라인드: 예" in md
    assert (out / "out" / "questions.md").exists()

    meta = yaml.safe_load((out / "project.yaml").read_text(encoding="utf-8"))
    assert meta["latest_version"] == 1 and meta["blind"] is True
    raw = out / meta["history"][0]["inputs"][0]["raw"]
    assert raw.exists() and raw.read_bytes() == hwpx_file.read_bytes()

    # 다시 돌리면 새 버전이 생기고 이전 버전은 남는다
    again = CliRunner().invoke(app, ["analyze", str(hwpx_file), "-o", str(out)])
    assert again.exit_code == 0
    assert (out / "rfp" / "rfp.v1.json").exists() and (out / "rfp" / "rfp.v2.json").exists()


def test_parse_and_profile_commands(hwpx_file):
    r = CliRunner().invoke(app, ["parse", str(hwpx_file)])
    assert r.exit_code == 0 and "제안 요청 내용" in r.output
    r = CliRunner().invoke(app, ["profile"])
    assert r.exit_code == 0 and "evaluation.tech_cutoff_pct = 85" in r.output and "[provisional]" in r.output


def test_unsupported_input(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("hello", encoding="utf-8")
    r = CliRunner().invoke(app, ["analyze", str(f), "-o", str(tmp_path / "p")])
    assert r.exit_code == 2


def test_profile_override(tmp_path):
    override = tmp_path / "org.yaml"
    override.write_text(yaml.safe_dump({"page_limits": {"main_pages": {"value": 80, "status": "user", "ref": "사내 기준"}}},
                                       allow_unicode=True), encoding="utf-8")
    p = load_profile(overrides=[override])
    pv = p.get("page_limits.main_pages")
    assert (pv.value, pv.status, pv.ref) == (80, "user", "사내 기준")
    assert pv.layer.startswith("override:")
    assert p.get("evaluation.tech_cutoff_pct").layer == "builtin"


def test_diff_between_versions(tmp_path):
    """정정공고: 배점·분량이 바뀌고 요구사항 하나가 추가되면 고위험 변경과 영향 절을 보고한다."""
    from hwpx import HwpxDocument

    from conftest import DETAILS, EVAL_QUAL, EVAL_QUAL_SPANS, GUIDE_LINES, _hwpx_table, detail_table

    def build(path, page_limit: str, extra_req: bool, func_points: str):
        doc = HwpxDocument.new()
        for d in DETAILS + ([("기능 요구사항", "SFR-003", "민원 통계", "통계를 제공한다", "- 월별 통계\n- 유형별 통계")]
                            if extra_req else []):
            rows, spans = detail_table(*d)
            _hwpx_table(doc, rows, spans)
        for line in GUIDE_LINES:
            doc.add_paragraph(line.replace("100쪽", page_limit))
        doc.add_paragraph("나. 정성적 평가(70점)")
        table = [list(r) for r in EVAL_QUAL]
        table[5][3] = func_points
        _hwpx_table(doc, table, EVAL_QUAL_SPANS)
        doc.save_to_path(str(path))
        return path

    project = tmp_path / "p"
    v1 = build(tmp_path / "제안요청서_v1.hwpx", "100쪽", False, "15")
    v2 = build(tmp_path / "제안요청서_v2.hwpx", "80쪽", True, "20")
    runner = CliRunner()
    assert runner.invoke(app, ["analyze", str(v1), "-o", str(project)]).exit_code == 0
    assert runner.invoke(app, ["analyze", str(v2), "-o", str(project)]).exit_code == 0
    assert (project / "plan" / "v1" / "trace.json").exists() and (project / "plan" / "v2" / "trace.json").exists()

    r = runner.invoke(app, ["diff", str(project)])
    assert r.exit_code == 0, r.output
    d = json.loads((project / "rfp" / "diff_v1_v2.json").read_text(encoding="utf-8"))
    changes = {(c["target"], c["key"], c["kind"]): c for c in d["changes"]}
    assert ("requirement", "SFR-003", "added") in changes
    page = changes[("guideline", "main_page_limit", "changed")]
    assert (page["old"], page["new"], page["high_risk"]) == ("100", "80", True)
    pts = changes[("eval_item", "기술 및 기능 > 기능 요구사항", "changed")]
    assert pts["high_risk"] and "15" in pts["old"] and "20" in pts["new"]
    assert any("기능 요구사항" in s for s in pts["affected_sections"])
    assert "plan.budget" in d["rerun"]
    md = (project / "out" / "diff_v1_v2.md").read_text(encoding="utf-8")
    assert "사람 확인 필요" in md


def test_diff_needs_two_versions(hwpx_file, tmp_path):
    project = tmp_path / "p"
    CliRunner().invoke(app, ["analyze", str(hwpx_file), "-o", str(project)])
    r = CliRunner().invoke(app, ["diff", str(project)])
    assert r.exit_code == 2
