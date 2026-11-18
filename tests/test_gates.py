"""사람 승인 게이트 G1~G5 테스트."""

from __future__ import annotations

import datetime as dt
import json
import shutil

import pytest
import yaml
from typer.testing import CliRunner

from rfpgen.cli import app
from rfpgen.draft.pipeline import run_draft
from rfpgen.gates import GateError, approve, gate_status, revoke
from rfpgen.kb import init_kb
from rfpgen.pipeline import analyze
from rfpgen.profile import load_profile

NOW = dt.datetime(2026, 11, 17, 9, 0, tzinfo=dt.timezone.utc)


@pytest.fixture(scope="module")
def base_project(tmp_path_factory, hwpx_file_module):
    base = tmp_path_factory.mktemp("gates")
    project = base / "proj"
    profile = load_profile()
    analyze([hwpx_file_module], project, profile)
    kb = base / "kb"
    init_kb(kb)
    run_draft(project, profile, kb_dir=kb)
    return project


@pytest.fixture(scope="module")
def hwpx_file_module(tmp_path_factory):
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
    path = tmp_path_factory.mktemp("src") / "제안요청서.hwpx"
    doc.save_to_path(str(path))
    return path


@pytest.fixture
def project(base_project, tmp_path):
    p = tmp_path / "proj"
    shutil.copytree(base_project, p)
    return p


def _status(project):
    return {s.gate: s for s in gate_status(project)}


def test_order_and_records(project):
    st = _status(project)
    assert [s.status for s in st.values()] == ["pending"] * 5
    with pytest.raises(GateError, match="앞 게이트"):
        approve(project, "G2", by="검토자")
    approve(project, "G1", by="검토자", note="평가표 확인", now=NOW)
    approve(project, "G2", by="검토자", now=NOW)
    approve(project, "G3", by="검토자", now=NOW)
    st = _status(project)
    assert [st[g].status for g in ("G1", "G2", "G3")] == ["approved"] * 3
    meta = yaml.safe_load((project / "project.yaml").read_text(encoding="utf-8"))
    rec = meta["gates"]["G1"]
    assert rec["by"] == "검토자" and rec["at"].startswith("2026-11-17T09:00") and rec["basis"]["rfp"] == "rfp.v1.json"
    assert rec["forced"] is False


def test_g4_per_section_and_stale_on_new_version(project):
    for g in ("G1", "G2", "G3"):
        approve(project, g, by="검토자")
    sections = sorted(p.name.split(".v")[0] for p in (project / "sections").glob("*.v1.json"))
    approve(project, "G4", by="작성자", sections=sections[:2])
    st = _status(project)["G4"]
    assert st.status == "partial" and f"2/{len(sections)}" in st.notes[0]
    approve(project, "G4", by="작성자")
    assert _status(project)["G4"].status == "approved"
    # 절 새 판이 나오면 재확인 필요
    src = project / "sections" / f"{sections[0]}.v1.json"
    (project / "sections" / f"{sections[0]}.v2.json").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    st = _status(project)["G4"]
    assert st.status == "stale" and sections[0] in st.notes[0]


def test_changed_basis_makes_downstream_stale(project, hwpx_file_module):
    for g in ("G1", "G2", "G3"):
        approve(project, g, by="검토자")
    # 스토리보드를 고치면 G3만 재확인
    sb = project / "strategy" / "storyboard.json"
    data = json.loads(sb.read_text(encoding="utf-8"))
    data["win_themes"] = ["고친 메시지"]
    sb.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    st = _status(project)
    assert st["G2"].status == "approved" and st["G3"].status == "stale"
    # 정정공고로 RFP 새 판이 나오면 G1부터 모두 재확인
    analyze([hwpx_file_module], project, load_profile())
    st = _status(project)
    assert st["G1"].status == "stale" and st["G2"].status == "stale" and st["G1"].fingerprint["rfp"] == "rfp.v2.json"


def test_hard_conditions_and_force(project):
    approve(project, "G1", by="검토자")
    trace_path = project / "plan" / "trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    trace["rows"][0]["sections"] = []
    trace_path.write_text(json.dumps(trace, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(GateError, match="연결되지 않은 요구사항 1건"):
        approve(project, "G2", by="검토자")
    st = approve(project, "G2", by="검토자", force=True)
    meta = yaml.safe_load((project / "project.yaml").read_text(encoding="utf-8"))
    assert st.status == "approved" and meta["gates"]["G2"]["forced"] is True
    assert "연결되지 않은 요구사항" in meta["gates"]["G2"]["forced_over"][0]
    revoke(project, "G2")
    assert _status(project)["G2"].status == "pending"


def test_g5_requires_clean_package(project):
    for g in ("G1", "G2", "G3", "G4"):
        approve(project, g, by="검토자")
    with pytest.raises(GateError, match="패키지 점검 결과가 없습니다"):
        approve(project, "G5", by="PM")
    checks = project / "checks"
    bad = {"run_id": "package-20261117T000000Z", "findings": [{"rule": "FACT-001", "severity": "blocker", "message": "x"}]}
    (checks / "package-20261117T000000Z.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(GateError, match="blocker 1건"):
        approve(project, "G5", by="PM")
    ok = {"run_id": "package-20261117T010000Z", "findings": []}
    (checks / "package-20261117T010000Z.json").write_text(json.dumps(ok), encoding="utf-8")
    assert approve(project, "G5", by="PM").status == "approved"


def test_cli_gate(project):
    r = CliRunner().invoke(app, ["gate", str(project)])
    assert r.exit_code == 0 and "G1 추출 확정" in r.output and "미승인" in r.output
    r = CliRunner().invoke(app, ["gate", str(project), "G1"])
    assert r.exit_code == 2 and "--by" in r.output
    r = CliRunner().invoke(app, ["gate", str(project), "g1", "--by", "검토자"])
    assert r.exit_code == 0, r.output
    assert "G1 추출 확정: 승인" in r.output
    r = CliRunner().invoke(app, ["gate", str(project), "G3", "--by", "검토자"])
    assert r.exit_code == 2 and "앞 게이트" in r.output
