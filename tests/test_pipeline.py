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
    assert wb.sheetnames == ["추적표", "평가표", "요구사항", "목차·쪽수", "작성지침", "질의서 후보", "점검 결과"]
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
