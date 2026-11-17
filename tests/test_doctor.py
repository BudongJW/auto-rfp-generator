"""설치 점검(rfpgen doctor) 테스트."""

from __future__ import annotations

from typer.testing import CliRunner

from rfpgen.cli import app
from rfpgen.doctor import run_doctor
from rfpgen.render.pdf import converters_available


def test_doctor_reports_each_tool(monkeypatch):
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "RFP_ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    checks = {c.name: c for c in run_doctor()}
    assert checks["Python"].status == "ok" and checks["python-hwpx"].status == "ok"
    for name in ("Node", "@rhwp/core(사이드카)", "Playwright", "LibreOffice", "한글 글꼴(서버 렌더)"):
        assert name in checks
    api = checks["Claude API 인증"]
    assert api.status == "warn" and api.detail == "없음"


def test_doctor_never_prints_key(monkeypatch):
    monkeypatch.setenv("RFP_ANTHROPIC_API_KEY", "sk-test-비밀값")
    r = CliRunner().invoke(app, ["doctor"])
    assert r.exit_code == 0, r.output
    assert "비밀값" not in r.output and "설정됨(RFP_ANTHROPIC_API_KEY)" in r.output


def test_dedicated_key_uses_official_base_url(monkeypatch):
    from rfpgen.llm.anthropic_provider import AnthropicProvider, client_options

    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://다른-도구-게이트웨이.invalid")
    monkeypatch.delenv("RFPGEN_ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("RFP_ANTHROPIC_API_KEY", raising=False)
    assert client_options() == {}                                  # 전용 키가 없으면 SDK 기본
    monkeypatch.setenv("RFP_ANTHROPIC_API_KEY", "sk-test")
    assert client_options() == {"api_key": "sk-test", "base_url": "https://api.anthropic.com"}
    client = AnthropicProvider().client
    assert str(client.base_url).startswith("https://api.anthropic.com") and client.api_key == "sk-test"


def test_missing_sidecar_is_a_warning_not_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("RFPGEN_SIDECAR_DIR", str(tmp_path / "없음"))
    checks = {c.name: c for c in run_doctor()}
    assert checks["@rhwp/core(사이드카)"].status == "warn" and "npm install" in checks["@rhwp/core(사이드카)"].hint
    assert converters_available()["svg"] is False and converters_available()["hwpx"] is False
    r = CliRunner().invoke(app, ["doctor"])
    assert r.exit_code == 0 and "경고" in r.output
