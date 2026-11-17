"""LLM 보조 추출 테스트. 네트워크를 쓰지 않는다: 가짜 공급자와 가짜 SDK 클라이언트만 쓴다."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from rfpgen.extract import extract_rfp, requirement_tables
from rfpgen.extract.llm_assist import llm_assist
from rfpgen.llm import (
    LLMCall,
    LLMError,
    LLMGateway,
    LLMInvalidOutput,
    LLMPolicyError,
    ProviderReply,
    keyword_excerpt,
    strict_schema,
)
from rfpgen.llm.anthropic_provider import FALLBACK_BETA, AnthropicProvider


class FakeProvider:
    """과제 이름별로 미리 정한 JSON(실행 순서대로)을 돌려준다."""

    name = "fake"
    allowed_data_classes = {"public"}

    def __init__(self, responses: dict[str, list]) -> None:
        self.responses = responses
        self.calls: list[LLMCall] = []

    def complete(self, call, json_schema):
        self.calls.append(call)
        key = call.task.split(".", 1)[1]
        n = sum(1 for c in self.calls if c.task == call.task) - 1
        outs = self.responses.get(key, [{}])
        data = outs[min(n, len(outs) - 1)]
        if isinstance(data, Exception):
            raise data
        if data == "REFUSE":
            return ProviderReply(text="", model="fake", stop_reason="refusal", refusal_category="cyber")
        return ProviderReply(text=json.dumps(data, ensure_ascii=False), model="fake-model", stop_reason="end_turn",
                             usage={"input_tokens": 100, "output_tokens": 40,
                                    "cache_read_input_tokens": 90 if n else 0, "cache_creation_input_tokens": 0 if n else 90})


def _bid(doc, needle: str) -> str:
    return next(b.id for b in doc.blocks if needle in b.text)


def _run(doc, profile, responses, tasks=("guideline", "compliance", "text_requirements"), audit=None):
    rfp, report = extract_rfp([doc], profile)
    provider = FakeProvider(responses)
    gateway = LLMGateway(provider, audit_path=audit)
    llm_assist(rfp, [doc], profile, report, gateway, skip_tables=requirement_tables(rfp, [doc]), tasks=tasks)
    return rfp, report, provider


def _codes(report):
    return [f.code for f in report.findings]


# ---- 스키마·게이트웨이 -------------------------------------------------------------------


def test_strict_schema_closes_every_object():
    from rfpgen.extract.llm_assist import ComplianceOut, GuidelineOut, TextRequirementsOut

    for model in (ComplianceOut, GuidelineOut, TextRequirementsOut):
        schema = strict_schema(model)

        def walk(node):
            if isinstance(node, dict):
                assert "title" not in node and "default" not in node
                if node.get("type") == "object":
                    assert node["additionalProperties"] is False
                    assert set(node["required"]) == set(node["properties"])
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(schema)


def test_gateway_validation_policy_and_audit(tmp_path):
    from rfpgen.extract.llm_assist import TextRequirementsOut

    audit = tmp_path / "audit.jsonl"

    class P(FakeProvider):
        def complete(self, call, json_schema):
            if call.task == "bad":
                return ProviderReply(text="{not json", model="m", stop_reason="end_turn")
            if call.task == "cut":
                return ProviderReply(text='{"requirements": [', model="m", stop_reason="max_tokens")
            return ProviderReply(text='{"requirements": [], "notes": ""}', model="m", stop_reason="end_turn",
                                 usage={"input_tokens": 7, "output_tokens": 3})

    gw = LLMGateway(P({}), audit_path=audit)
    call = LLMCall(task="ok", system="s", context="c", instruction="i", schema=TextRequirementsOut)
    data, _ = gw.run(call, TextRequirementsOut)
    assert data.requirements == []
    with pytest.raises(LLMInvalidOutput):
        gw.run(LLMCall(task="bad", system="s", context="c", instruction="i", schema=TextRequirementsOut), TextRequirementsOut)
    with pytest.raises(LLMInvalidOutput):
        gw.run(LLMCall(task="cut", system="s", context="c", instruction="i", schema=TextRequirementsOut), TextRequirementsOut)
    with pytest.raises(LLMPolicyError):
        gw.run(LLMCall(task="kb", system="s", context="c", instruction="i", schema=TextRequirementsOut,
                       data_class="confidential"), TextRequirementsOut)
    lines = [json.loads(x) for x in audit.read_text(encoding="utf-8").splitlines()]
    assert [x["status"] for x in lines] == ["ok", "invalid", "truncated"]
    assert lines[0]["usage"]["input_tokens"] == 7 and "input_sha256_16" in lines[0]
    assert gw.usage.calls == 3 and gw.usage.input_tokens == 7


def test_excerpt_includes_only_keyword_windows(maker):
    import re

    m = maker()
    for i in range(10):
        m.p(f"문단 {i} 일반 설명입니다")
    m.p("○ 제안서 본문은 100쪽 이내로 작성")
    ex = keyword_excerpt([m.doc], re.compile(r"쪽\s*이내"), radius=1)
    assert ex.hits == 1 and len(ex.block_ids) == 2  # 앞 블록 1개 + 걸린 블록(마지막이라 뒤 없음)
    assert "[d01:b00011]" in ex.text and "문단 0" not in ex.text


# ---- 1. 작성지침 -------------------------------------------------------------------------


def test_guideline_fills_gaps_only_with_verified_numbers(maker, profile):
    m = maker()
    m.p("ㅇ 제안서 지 규격의 전자문서(pdf)로 작성하며 페이지 (단면기준) 이내로 작성(표지, 간지 제외)")
    m.p("ㅇ 제안서 본문 글씨는 12 이상(표 안은 10 이상)으로 작성")
    m.p("ㅇ 제안서에는 제안사 명칭과 로고를 표시하지 아니함")
    m.p("ㅇ 제안서는 A4 용지 세로 방향으로 작성")
    m.p("ㅇ 발표자료는 A3 용지로 출력하여 별도 제출")
    d = m.doc
    responses = {"guideline": [{"fields": [
        # 숫자가 도형 글자라 원문에 없음 → LLM이 '관행 값'을 넣어도 버린다
        {"field": "main_page_limit", "value_text": "100쪽", "evidence": [
            {"block_id": _bid(d, "페이지 (단면기준)"), "quote": "페이지 (단면기준) 이내로 작성"}]},
        {"field": "min_font_pt", "value_text": "12 이상", "evidence": [
            {"block_id": _bid(d, "글씨는 12"), "quote": "본문 글씨는 12 이상"}]},
        {"field": "blind", "value_text": "true", "evidence": [
            {"block_id": _bid(d, "로고를"), "quote": "제안사 명칭과 로고를 표시하지 아니함"}]},
        # 근거 블록이 엉뚱함 → 버린다
        {"field": "total_size_limit_mb", "value_text": "300MB", "evidence": [
            {"block_id": _bid(d, "로고를"), "quote": "총 용량은 300MB"}]},
        # 규칙 추출값(A4)과 다름 → 충돌 보고, 규칙 값 유지
        {"field": "paper", "value_text": "A3", "evidence": [
            {"block_id": _bid(d, "A3 용지"), "quote": "발표자료는 A3 용지로 출력"}]},
    ], "manual": ["쪽 번호는 하단 중앙에 표기"], "notes": ""}]}
    rfp, report, provider = _run(d, profile, responses, tasks=("guideline",))
    g = rfp.guideline
    assert g.main_page_limit is None and "GUIDE-PAGE-UNREADABLE" in _codes(report)
    assert g.min_font_pt.value == 12 and g.min_font_pt.method == "llm" and g.min_font_pt.status == "proposed"
    assert g.blind.value is True and g.blind.method == "llm"
    assert g.total_size_limit_mb is None
    assert g.paper.value == "A4" and g.paper.method == "rule"
    assert "LLM-GUIDE-CONFLICT" in _codes(report)
    rejected = next(f.message for f in report.findings if f.code == "LLM-REJECTED")
    assert "main_page_limit(숫자 100가 인용문에 없음)" in rejected and "total_size_limit_mb(근거 불일치)" in rejected
    assert "LLM-GUIDE-MANUAL" in _codes(report)
    call = provider.calls[0]
    assert call.effort == "medium" and call.context.startswith("<excerpts>")
    assert "OpenBidKit" not in call.instruction  # 지시문에는 귀속 문구가 아니라 작업 설명만 들어간다


# ---- 2. 무효·감점 사유 -------------------------------------------------------------------


def test_compliance_two_runs_dedupe_and_instability(maker, profile):
    m = maker()
    m.p("1. 입찰참가자격")
    m.p("○ 소프트웨어사업자(컴퓨터관련서비스사업)로 신고한 자")
    m.p("2. 유의사항")
    m.p("○ 제출서류를 기한 내 제출하지 않은 경우 입찰은 무효로 한다")
    m.p("○ 제안서에 기재한 핵심 인력을 발주기관 승인 없이 교체하면 협상 순위를 박탈함")
    m.p("○ 제안서 기재 내용이 사실과 다르게 판명되면 낙찰을 취소할 수 있음")
    d = m.doc
    swap = {"block_id": _bid(d, "협상 순위를 박탈"), "quote": "협상 순위를 박탈함"}
    void = {"block_id": _bid(d, "입찰은 무효"), "quote": "입찰은 무효로 한다"}
    false = {"block_id": _bid(d, "사실과 다르게"), "quote": "사실과 다르게 판명되면 낙찰을 취소"}
    run1 = {"conditions": [
        {"category": "평가제외", "text": "핵심 인력 무단 교체 시 협상 순위 박탈", "consequence": "협상 순위 박탈",
         "legal_ref_in_text": None, "evidence": [swap]},
        {"category": "입찰무효", "text": "제출서류 기한 내 미제출 시 입찰 무효", "consequence": "입찰 무효",
         "legal_ref_in_text": None, "evidence": [void]},
        {"category": "감점", "text": "지어낸 조건", "consequence": "감점", "legal_ref_in_text": "국가계약법 제99조",
         "evidence": [{"block_id": _bid(d, "협상 순위를 박탈"), "quote": "원문에 없는 문장"}]},
    ], "eligibility": [{"text": "소프트웨어사업자로 신고한 자",
                        "evidence": [{"block_id": _bid(d, "소프트웨어사업자"), "quote": "소프트웨어사업자(컴퓨터관련서비스사업)로 신고한 자"}]}],
        "suggested_checks": [{"text": "핵심 인력 교체 승인 절차와 대체 인력 요건을 확인", "reason": "교체 시 협상 순위 박탈 규정이 있음"}],
        "notes": ""}
    run2 = {"conditions": [
        {"category": "평가제외", "text": "핵심 인력을 승인 없이 교체하면 협상 순위 박탈", "consequence": "",
         "legal_ref_in_text": None, "evidence": [swap]},
        {"category": "입찰무효", "text": "허위 판명 시 낙찰 취소", "consequence": "낙찰 취소",
         "legal_ref_in_text": None, "evidence": [false]},
    ], "eligibility": [], "suggested_checks": [], "notes": ""}
    rfp, report, provider = _run(d, profile, {"compliance": [run1, run2]}, tasks=("compliance",))
    llm_items = [c for c in rfp.compliance if c.method == "llm" and c.origin == "stated"]
    texts = {c.text.split(" — ")[0]: c for c in llm_items}
    assert texts["핵심 인력 무단 교체 시 협상 순위 박탈"].confidence == 0.8   # 두 번 모두 나옴
    assert texts["허위 판명 시 낙찰 취소"].confidence == 0.5                 # 한 번만 나옴 → 불안정
    assert not any("기한 내 미제출" in t for t in texts)                     # 규칙 추출과 같은 블록 → 중복 제거
    assert not any("지어낸" in t for t in texts)                             # 인용 불일치 → 버림
    assert "LLM-UNSTABLE" in _codes(report)
    suggested = [c for c in rfp.compliance if c.origin == "suggested" and c.method == "llm"]
    assert len(suggested) == 1 and suggested[0].status == "proposed" and not suggested[0].locators
    assert len(provider.calls) == 2 and provider.calls[0].context == provider.calls[1].context  # 2회차는 캐시 적중 대상


# ---- 3. 서술형 요구사항 --------------------------------------------------------------------


def test_text_requirements_added_with_ids_and_dedupe(maker, profile):
    m = maker()
    m.table([["요구사항 고유번호", "SFR-001"], ["요구사항 명칭", "민원 신청 관리"],
             ["정의", "온라인 민원 신청 기능을 구축하여야 한다"]])
    m.p("○ 계약상대자는 기존 민원 데이터 전체를 신규 시스템으로 이관하여야 한다")
    m.p("○ 신규 시스템은 웹 접근성 품질인증 기준을 준수하여야 한다")
    m.p("○ 제안서는 PDF로 제출하여야 한다")
    d = m.doc
    migrate = {"block_id": _bid(d, "이관하여야"), "quote": "기존 민원 데이터 전체를 신규 시스템으로 이관하여야 한다"}
    a11y = {"block_id": _bid(d, "웹 접근성"), "quote": "웹 접근성 품질인증 기준을 준수하여야 한다"}
    run1 = {"requirements": [
        {"name": "민원 데이터 이관", "category": "데이터", "statement": "기존 민원 데이터 전체를 신규 시스템으로 이관",
         "evidence": [migrate]},
        {"name": "웹 접근성 준수", "category": "품질", "statement": "웹 접근성 품질인증 기준 준수", "evidence": [a11y]},
    ], "notes": ""}
    run2 = {"requirements": [
        {"name": "데이터 이관", "category": "데이터", "statement": "기존 민원 데이터를 신규 시스템으로 이관",
         "evidence": [migrate]},
    ], "notes": ""}
    tasks = dict(profile.value("llm.tasks"))
    tasks["text_requirements"] = {**tasks["text_requirements"], "runs": 2}   # 두 번 돌려 흔들림 표시(기본은 1회)
    twice = profile.merged({"llm": {"tasks": {"value": tasks, "status": "user", "ref": "test"}}}, "test")
    rfp, report, provider = _run(d, twice, {"text_requirements": [run1, run2]}, tasks=("text_requirements",))
    new = {r.id: r for r in rfp.requirements if r.origin == "llm"}
    assert list(new) == ["X-0001", "X-0002"]
    assert new["X-0001"].name == "민원 데이터 이관" and new["X-0001"].category == "데이터 요구사항"
    assert new["X-0001"].confidence == 0.8 and new["X-0002"].confidence == 0.5
    assert new["X-0001"].detail_grade is not None  # 새 요구사항에도 상세화 등급·질의서 후보를 만든다
    assert "LLM-REQ-ADDED" in _codes(report) and "LLM-UNSTABLE" in _codes(report)
    ctx = provider.calls[0].context
    assert "이관하여야" in ctx
    assert "SFR-001" not in ctx  # 요구사항 정의서 표는 보내지 않는다
    # 제안서 작성 지시는 발췌의 '걸린 줄'이 아니다(앞뒤 문맥 줄로만 들어갈 수 있다)
    from rfpgen.extract.llm_assist import _obligation_block
    from rfpgen.extract.requirements import compile_id_regex

    pred = _obligation_block(compile_id_regex(profile.value("requirements.id_regex")))
    hits = [b.text for b in d.blocks if pred(b) and b.kind == "para"]  # 요구사항 표 셀은 발췌 단계에서 제외된다
    assert len(hits) == 2 and not any("PDF" in t for t in hits)


def test_truncated_output_retried_once_with_larger_limit(maker, profile):
    m = maker()
    m.p("○ 계약상대자는 기존 민원 데이터 전체를 신규 시스템으로 이관하여야 한다")
    d = m.doc
    ok = {"requirements": [{"name": "민원 데이터 이관", "category": "데이터", "statement": "기존 민원 데이터 이관",
                            "evidence": [{"block_id": _bid(d, "이관하여야"),
                                          "quote": "기존 민원 데이터 전체를 신규 시스템으로 이관하여야 한다"}]}], "notes": ""}

    class Truncating(FakeProvider):
        def complete(self, call, json_schema):
            if call.max_tokens < 100_000:                  # 첫 요청은 잘린다
                self.calls.append(call)
                return ProviderReply(text='{"requirements": [', model="m", stop_reason="max_tokens")
            return super().complete(call, json_schema)

    rfp, report = extract_rfp([d], profile)
    provider = Truncating({"text_requirements": [ok]})
    llm_assist(rfp, [d], profile, report, LLMGateway(provider), skip_tables=set(), tasks=("text_requirements",))
    limits = [c.max_tokens for c in provider.calls]
    assert limits == [64000, 128000]
    assert "LLM-RETRY" in _codes(report) and any(r.origin == "llm" for r in rfp.requirements)


# ---- 실패 처리 ---------------------------------------------------------------------------


def test_refusal_and_auth_error_keep_deterministic_results(rfp_doc, profile):
    rfp, report, _ = _run(rfp_doc, profile, {"guideline": ["REFUSE"],
                                             "compliance": [LLMError("compliance: 인증 실패 — API 키를 확인하세요")]})
    codes = _codes(report)
    assert "LLM-REFUSAL" in codes and "LLM-ERROR" in codes
    assert report.stats["llm_calls"] == 1  # 인증 오류 뒤 남은 과제는 건너뛴다
    assert rfp.guideline.main_page_limit.value == 100 and len(rfp.requirements) == 5


def test_pipeline_with_llm_provider(hwpx_file, tmp_path, profile):
    from rfpgen.pipeline import analyze

    result = analyze([hwpx_file], tmp_path / "p", profile, llm_provider=FakeProvider({
        "guideline": [{"fields": [], "manual": [], "notes": ""}],
        "compliance": [{"conditions": [], "eligibility": [], "suggested_checks": [], "notes": ""}],
        "text_requirements": [{"requirements": [], "notes": ""}],
    }))
    audit = tmp_path / "p" / "audit" / "llm_calls.jsonl"
    assert audit.exists() and len(audit.read_text(encoding="utf-8").splitlines()) == result.report.stats["llm_calls"]
    md = (tmp_path / "p" / "out" / "analysis.md").read_text(encoding="utf-8")
    assert "## LLM 보조 추출" in md


# ---- Claude API 요청 형태 ---------------------------------------------------------------


class _Stream:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self.message


class _FakeClient:
    def __init__(self, behaviors, models=None):
        self.requests: list[dict] = []
        self._behaviors = list(behaviors)

        def stream(**kwargs):
            self.requests.append(kwargs)
            b = self._behaviors.pop(0)
            if isinstance(b, Exception):
                raise b
            return _Stream(b)

        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=stream))
        self.models = SimpleNamespace(list=lambda: models or [])


def _message(text: str, stop: str = "end_turn"):
    usage = SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=0,
                            cache_creation_input_tokens=10, iterations=[])
    return SimpleNamespace(content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
                           usage=usage, stop_reason=stop, stop_details=None, model="resolved-model")


def _call():
    from rfpgen.extract.llm_assist import TextRequirementsOut

    return LLMCall(task="extract.text_requirements", system="SYS", context="<excerpts>x</excerpts>", instruction="DO",
                   schema=TextRequirementsOut, effort="high", max_tokens=1234)


def test_anthropic_request_shape_and_model_resolution(monkeypatch):
    monkeypatch.delenv("RFPGEN_LLM_MODEL", raising=False)
    models = [SimpleNamespace(id="claude-opus-older", created_at="2026-01-01T00:00:00Z"),
              SimpleNamespace(id="claude-opus-newer", created_at="2026-06-01T00:00:00Z"),
              SimpleNamespace(id="claude-other-newest", created_at="2026-09-01T00:00:00Z")]
    client = _FakeClient([_message('{"requirements": [], "notes": ""}')], models)
    provider = AnthropicProvider(client=client)
    reply = provider.complete(_call(), strict_schema(_call().schema))
    assert reply.text.startswith('{"requirements"') and reply.usage["cache_creation_input_tokens"] == 10
    req = client.requests[0]
    assert req["model"] == "claude-opus-newer"  # 가장 최근 Opus 계열
    assert req["max_tokens"] == 1234
    assert req["system"][0]["cache_control"] == {"type": "ephemeral"}
    content = req["messages"][0]["content"]
    assert content[0]["text"].startswith("<excerpts>") and content[0]["cache_control"] == {"type": "ephemeral"}
    assert content[1] == {"type": "text", "text": "DO"}  # 가변 지시는 캐시 지점 뒤
    assert req["output_config"]["effort"] == "high"
    assert req["output_config"]["format"]["type"] == "json_schema"
    assert req["betas"] == [FALLBACK_BETA] and req["fallbacks"] == "default"
    assert "thinking" not in req and "temperature" not in req


def test_anthropic_retries_without_fallbacks_when_rejected(monkeypatch):
    import anthropic
    import httpx2

    monkeypatch.setenv("RFPGEN_LLM_MODEL", "env-model")
    resp = httpx2.Response(400, request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    err = anthropic.BadRequestError("fallbacks is not supported for this model", response=resp, body=None)
    client = _FakeClient([err, _message('{"requirements": [], "notes": ""}')])
    provider = AnthropicProvider(client=client)
    provider.complete(_call(), {})
    assert [r["model"] for r in client.requests] == ["env-model", "env-model"]
    assert "fallbacks" in client.requests[0] and "fallbacks" not in client.requests[1]


def test_anthropic_without_credentials_reports_cleanly(monkeypatch):
    def boom(**kwargs):
        raise TypeError("Could not resolve authentication method")

    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(stream=boom)), models=SimpleNamespace(list=lambda: []))
    provider = AnthropicProvider(model="m", client=client)
    with pytest.raises(LLMError, match="인증 정보가 없습니다"):
        provider.complete(_call(), {})


def test_cli_llm_flag_degrades_gracefully(hwpx_file, tmp_path, monkeypatch):
    """인증 정보가 없으면 LLM 과제만 건너뛰고 결정적 결과는 그대로 낸다(실제 API 호출 없음)."""
    from typer.testing import CliRunner

    from rfpgen.cli import app

    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))  # 디스크의 로그인 프로필을 쓰지 않게
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:9")  # 만에 하나 인증되더라도 외부로 나가지 않게
    monkeypatch.setenv("RFPGEN_LLM_MODEL", "test-model")
    r = CliRunner().invoke(app, ["analyze", str(hwpx_file), "-o", str(tmp_path / "p"), "--llm"])
    assert r.exit_code == 0, r.output
    assert "LLM-ERROR" in r.output and "요구사항    : 5건" in r.output


def test_cost_estimate_from_audit(tmp_path):
    import json

    from rfpgen.llm.cost import audit_lines, estimate
    from rfpgen.profile import load_profile

    pricing = load_profile().value("llm.pricing_usd_per_mtok")
    audit = tmp_path / "llm_calls.jsonl"
    rows = [
        {"model": "claude-opus-5-5", "usage": {"input_tokens": 100_000, "output_tokens": 10_000,
                                               "cache_read_input_tokens": 50_000, "cache_creation_input_tokens": 20_000}},
        {"model": "claude-opus-5-5-preview", "usage": {"input_tokens": 1_000_000, "output_tokens": 0}},  # 접두어로 단가
        {"model": "어떤-모델", "usage": {"input_tokens": 1}},
        {"model": "claude-opus-5-5", "error": "실패", "usage": {}},
    ]
    audit.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    est = estimate(audit, pricing)
    first = (100_000 * 4 + 10_000 * 20 + 50_000 * 0.2 + 20_000 * 5) / 1_000_000
    assert est.calls == 3 and est.unpriced == ["어떤-모델"]
    assert abs(est.usd - (first + 4.0)) < 1e-9
    assert estimate(audit, pricing, since_line=1).usd == 4.0 and audit_lines(audit) == 4
