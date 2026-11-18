"""릴리스 준비: 버전·변경 기록이 맞는지(태그를 올리기 전에 CI에서 걸리게)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from typer.testing import CliRunner

from rfpgen import __version__
from rfpgen.cli import app

_SPEC = importlib.util.spec_from_file_location("release_notes", Path(__file__).parents[1] / "scripts" / "release_notes.py")
rn = importlib.util.module_from_spec(_SPEC)  # type: ignore[arg-type]
_SPEC.loader.exec_module(rn)  # type: ignore[union-attr]


def test_versions_and_changelog_agree():
    project, package = rn.versions()
    assert project == package == __version__
    assert rn.check(f"v{project}") == []
    assert rn.check(f"v{project}-rc.1") == []
    assert rn.check("v9.9.9") and rn.check("release-1")


def test_release_notes():
    notes = rn.notes(f"v{__version__}")
    assert "### 분석" in notes and "## 설치" in notes and f"rfpgen-{__version__}-py3-none-any.whl" in notes
    assert "사전 릴리스" not in notes and "사전 릴리스" in rn.notes(f"v{__version__}-rc.1")
    text = "## [0.2.0] - x\n\n새 것\n\n## [0.1.0] - y\n\n옛 것\n\n[0.2.0]: https://e\n"
    assert rn.changelog_section("0.2.0", text) == "새 것" and rn.changelog_section("0.1.0", text) == "옛 것"
    assert rn.changelog_section("0.3.0", text) == ""


def test_cli_version():
    r = CliRunner().invoke(app, ["--version"])
    assert r.exit_code == 0 and r.output.strip() == f"rfpgen {__version__}"
