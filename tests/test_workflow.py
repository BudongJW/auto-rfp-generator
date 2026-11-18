"""누구나 쓰기 쉽게: 체험 예제(sample), 한 번에 실행(start), 진행 안내(status), 설치(setup)."""

from __future__ import annotations

import os
import time

from typer.testing import CliRunner

from rfpgen.cli import app
from rfpgen.installer import run_setup
from rfpgen.kb import init_kb
from rfpgen.profile import load_profile
from rfpgen.render.pdf import converters_available
from rfpgen.sample import build_sample_rfp
from rfpgen.workflow import default_project_dir, project_status, remember_kb, resolve_kb, run_start


def test_start_runs_every_stage_and_status_guides(tmp_path):
    rfp = build_sample_rfp(tmp_path / "예제.hwpx")
    project = tmp_path / "proj"
    logs: list[str] = []
    res = run_start([rfp], project, load_profile(), echo=logs.append)
    names = [s.name for s in res.steps]
    assert names[0] == "RFP 분석" and names[2] == "별지 서식" and len(names) == 5
    assert all(s.ok for s in res.steps), [(s.name, s.message) for s in res.steps]
    assert not res.steps[2].skipped                                # HWPX 첨부라 별지를 채웠다
    assert res.steps[4].skipped is (not converters_available()["hwpx"])
    assert any("[1/5]" in line for line in logs)
    stages, todo = project_status(project)
    done = {s.key: s.done for s in stages}
    assert done["analyze"] and done["draft"] and done["forms"] and done["slides"] and not done["kb"]
    assert "rfpgen kb init kb" in todo[0] and "--kb kb" in todo[0]  # KB 없이 시작했으면 KB부터 안내
    assert any("rfpgen gate" in t and "G1" in t for t in todo)
    forms = (project / "out" / "forms" / "forms.json").read_text(encoding="utf-8")
    assert "예시정보" not in forms                                   # 예시 회사 값으로 채우지 않는다


def test_kb_is_remembered_and_example_values_warned(tmp_path):
    rfp = build_sample_rfp(tmp_path / "예제.hwpx", with_forms=False)
    project = tmp_path / "proj"
    kb = tmp_path / "kb"
    init_kb(kb)
    res = run_start([rfp], project, load_profile(), kb=kb, echo=lambda _: None)
    assert res.steps[2].skipped is False                             # HWPX면 서식이 없어도 시도한다
    assert resolve_kb(project, None) == kb.resolve()                 # 다음 명령에서 --kb 생략 가능
    assert resolve_kb(project, tmp_path / "다른") == tmp_path / "다른"
    stages, todo = project_status(project)
    assert next(s for s in stages if s.key == "kb").done
    assert any("예시 회사 값" in t for t in todo)
    # 초안이 장표·패키지보다 새로우면 다시 만들라고 알린다
    time.sleep(0.01)
    newest = max((project / "sections").glob("*.json"), key=lambda p: p.stat().st_mtime)
    future = time.time() + 5
    os.utime(newest, (future, future))
    _, todo = project_status(project)
    assert any("rfpgen slides" in t for t in todo)
    remember_kb(project, None)                                        # None은 기억을 지우지 않는다
    assert resolve_kb(project, None) == kb.resolve()


def test_default_project_dir():
    assert default_project_dir(__import__("pathlib").Path("붙임1 제안요청서(최종).hwp")).as_posix() == "projects/붙임1_제안요청서(최종)"


def _fake_sidecar(tmp_path, monkeypatch):
    sc = tmp_path / "sidecar"
    sc.mkdir()
    (sc / "package.json").write_text("{}", encoding="utf-8")
    (sc / "package-lock.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("RFPGEN_SIDECAR_DIR", str(sc))
    monkeypatch.delenv("RFPGEN_CHROMIUM_PATH", raising=False)
    import rfpgen.installer as inst

    real = inst.shutil.which
    monkeypatch.setattr(inst.shutil, "which", lambda name: f"/usr/bin/{name}" if name in ("node", "npm") else real(name))
    return inst, real


def test_setup_plan_and_missing_node(tmp_path, monkeypatch):
    inst, real = _fake_sidecar(tmp_path, monkeypatch)
    calls = []
    res = run_setup(runner=lambda cmd, cwd: calls.append(cmd) or 0)
    assert res.ok and ["npm", "ci"] in calls and ["npx", "playwright", "install", "chromium"] in calls
    calls.clear()
    res = run_setup(runner=lambda cmd, cwd: calls.append(cmd) or 0, browser=False)
    assert ["npx", "playwright", "install", "chromium"] not in calls
    monkeypatch.setattr(inst.shutil, "which", lambda name: None if name in ("node", "npm") else real(name))
    res = run_setup(runner=lambda cmd, cwd: 0)
    assert not res.ok and any("Node.js" in line for line in res.lines)


def test_cli_sample_start_status(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = CliRunner().invoke(app, ["sample"])
    assert r.exit_code == 0 and "rfpgen start" in r.output
    r = CliRunner().invoke(app, ["start", "예제_제안요청서.hwpx"])
    assert r.exit_code == 0, r.output
    assert "[5/5]" in r.output and "다음 할 일" in r.output
    r = CliRunner().invoke(app, ["status", "projects/예제_제안요청서"])
    assert r.exit_code == 0 and "RFP 분석" in r.output and "본문 초안" in r.output
    _fake_sidecar(tmp_path, monkeypatch)
    r = CliRunner().invoke(app, ["setup", "--dry-run"])
    assert "npm ci" in r.output
    r = CliRunner().invoke(app, ["--help"])
    assert "시작하기" in r.output and "단계별 작업" in r.output


def test_cli_survives_non_utf8_output(tmp_path):
    """Windows에서 출력을 파일로 돌리면 cp949·cp1252로 쓰게 되어 한글·기호에서 멈추던 문제."""
    import subprocess
    import sys
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "src"
    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONPATH": str(src)}
    r = subprocess.run([sys.executable, "-m", "rfpgen", "sample", "예제.hwpx"], cwd=tmp_path, env=env,
                       capture_output=True, timeout=120)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")[-500:]
    assert "만들었습니다" in r.stdout.decode("utf-8") and (tmp_path / "예제.hwpx").exists()
