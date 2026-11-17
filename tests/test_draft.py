"""M2 초안 생성 테스트(네트워크 없음)."""

from __future__ import annotations

import json
import re
import zipfile

import pytest
from typer.testing import CliRunner

from rfpgen.cli import app
from rfpgen.draft.pipeline import run_draft
from rfpgen.draft.tokens import apply_tokens, numbers
from rfpgen.kb import check_kb, init_kb, load_kb
from rfpgen.llm import ProviderReply
from rfpgen.pipeline import analyze
from rfpgen.schemas.draft import DraftBlock, SectionDraft


@pytest.fixture
def project(hwpx_file, tmp_path, profile):
    out = tmp_path / "proj"
    analyze([hwpx_file], out, profile)
    return out


@pytest.fixture
def kb_dir(tmp_path):
    folder = tmp_path / "kb"
    init_kb(folder)
    return folder


# ---- KB와 토큰 ---------------------------------------------------------------------------


def test_kb_template_loads_and_resolves(kb_dir):
    kb = load_kb(kb_dir)
    assert kb.resolve("F-002") == "85명"
    assert kb.resolve("P-001.amount_krw") == "12.5억 원"
    assert kb.resolve("H-001.years") == "18"
    assert kb.resolve("F-999") is None
    assert "예시정보" in kb.identity.terms()
    assert check_kb(kb) == []


def test_token_substitution_and_placeholders(kb_dir):
    kb = load_kb(kb_dir)
    d = SectionDraft(section_id="S-1", number="Ⅰ.1", title="t", head_message="정규직 개발 인력 {{fact:F-002}} 보유",
                     blocks=[DraftBlock(kind="bullets", items=["실적 금액 {{kb:P-001.amount_krw}}", "없는 값 {{fact:F-999}}"])])
    apply_tokens(d, kb)
    assert d.head_message == "정규직 개발 인력 85명 보유"
    assert d.blocks[0].items[0] == "실적 금액 12.5억 원"
    assert d.unresolved_tokens == ["F-999"] and d.placeholders == ["[확인 필요: KB에 F-999 없음]"]
    assert numbers("응답 3초 이내, 동시 사용자 500명, 2단계") == ["3초", "500명"]


# ---- 오프라인(골격) ------------------------------------------------------------------------


def test_offline_draft_end_to_end(project, kb_dir, profile):
    res = run_draft(project, profile, kb_dir=kb_dir)
    assert res.storyboard.origin == "skeleton" and len(res.storyboard.win_themes) == 3
    assert all(d.origin == "skeleton" for d in res.drafts)
    # 모든 요구사항이 대응표에 들어간다(대응 방안은 [확인 필요])
    assert {r.req_id for d in res.drafts for r in d.responses} == {"SFR-001", "SFR-002", "SER-001", "PER-001", "PMR-001"}
    rules = {f.rule for f in res.check.findings if f.severity == "blocker"}
    assert {"COV-001", "FACT-001"} <= rules and "HWPX-001" not in rules
    # 자료 요청: KB에 없는 근거만
    needs = {r.need for r in res.storyboard.data_requests}
    assert "회사 일반현황(설립·인원·매출)" in needs and "유사사업 수행 실적" not in needs

    out = res.outputs["proposal"]
    from hwpx import HwpxDocument

    doc = HwpxDocument.open(str(out))
    assert not doc.validate().issues
    texts = [p.text for p in doc.paragraphs]
    assert texts[0] == "2026년 통합민원시스템 고도화 사업"
    assert "Ⅳ. 기술 및 기능" in texts and "1. 기능 요구사항" in texts
    assert any(t.startswith("□ ") for t in texts) and any(t.startswith("○ [확인 필요") for t in texts)
    # 대응표의 요구사항 ID가 본문 표에 들어 있다
    with zipfile.ZipFile(out) as zf:
        section_xml = zf.read("Contents/section0.xml").decode("utf-8")
        assert "SFR-001" in section_xml and "PMR-001" in section_xml
        everything = " ".join(zf.read(n).decode("utf-8", "ignore") for n in zf.namelist() if n.endswith((".xml", ".hpf")))
    assert "예시정보" not in everything  # 렌더에는 회사 식별 정보가 들어가지 않는다

    # 스토리보드는 사람이 고친 것을 다시 쓴다(G3)
    sb_path = project / "strategy" / "storyboard.json"
    sb = json.loads(sb_path.read_text(encoding="utf-8"))
    sb["sections"][0]["head_message"] = "사람이 쓴 거버닝 메시지"
    sb_path.write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    first = sb["sections"][0]["section_id"]
    res2 = run_draft(project, profile, kb_dir=kb_dir, sections={first})
    redrafted = next(d for d in res2.drafts if d.section_id == first)
    assert redrafted.head_message == "사람이 쓴 거버닝 메시지" and redrafted.version == 2
    assert len(res2.drafts) == len(res.drafts)  # 나머지 절은 저장본을 그대로 썼다


def test_draft_cli(project, kb_dir):
    r = CliRunner().invoke(app, ["kb", "check", str(kb_dir)])
    assert r.exit_code == 0 and "문제 없음" in r.output
    r = CliRunner().invoke(app, ["draft", str(project), "--kb", str(kb_dir)])
    assert r.exit_code == 0, r.output
    assert "절 초안" in r.output and "blocker" in r.output
    assert (project / "out" / "proposal.hwpx").exists() and (project / "out" / "trace_draft.xlsx").exists()


# ---- LLM(가짜 공급자) ------------------------------------------------------------------------


class WriterFake:
    """스토리보드와 절 초안을 흉내 낸다. 절 지시문에서 section_id와 요구사항 ID를 읽어 응답을 만든다."""

    name = "fake"

    def __init__(self, allowed=("public",)) -> None:
        self.allowed_data_classes = set(allowed)
        self.calls = []

    def complete(self, call, json_schema):
        self.calls.append(call)
        if call.task == "draft.storyboard":
            ids = re.findall(r"section_id=(S-[\d-]+)", call.context)
            data = {"win_themes": ["민원 전 과정 온라인화", "검증된 보안 체계", "안정적 전환"],
                    "sections": [{"section_id": i, "head_message": f"{i} 결론", "key_points": ["요점"],
                                  "needed_facts": ["F-002", "클라우드 전환 실적"]} for i in ids]}
        else:
            sid = re.search(r"section_id: (S-[\d-]+)", call.instruction).group(1)
            reqs = re.findall(r"^- ([A-Z]{3}-\d{3}) ", call.instruction, re.M)
            text = "정규직 개발 인력 {{fact:F-002}} 투입"
            if "기능 요구사항" in call.instruction:
                text += ", 예시정보의 검증된 프레임워크 적용, 35개 기관 구축 경험"
            data = {"head_message": f"{sid} 결론: 민원 처리 기간 단축",
                    "blocks": [{"kind": "bullets", "text": "", "level": 0, "items": ["□ 추진 방안"], "table_header": [],
                                "table_rows": [], "req_refs": reqs},
                               {"kind": "bullets", "text": "", "level": 1, "items": [text], "table_header": [],
                                "table_rows": [], "req_refs": []},
                               {"kind": "table", "text": "", "level": 0, "items": [], "table_header": ["단계", "산출물"],
                                "table_rows": [["분석", "요구사항 정의서"]], "req_refs": []}],
                    "responses": [{"req_id": r, "response": f"{r} 대응 방안 구현", "acceptance": "수용"} for r in reqs],
                    "missing_info": []}
        return ProviderReply(text=json.dumps(data, ensure_ascii=False), model="fake", stop_reason="end_turn",
                             usage={"input_tokens": 1000, "output_tokens": 300, "cache_read_input_tokens": 800})


def test_llm_draft_tokens_numbers_blind_and_coverage(project, kb_dir, profile):
    fake = WriterFake()
    res = run_draft(project, profile, kb_dir=kb_dir, provider=fake)
    assert res.storyboard.origin == "llm" and res.storyboard.win_themes[0] == "민원 전 과정 온라인화"
    assert all(d.origin == "llm" for d in res.drafts)
    # 기호는 프로그램이 붙이므로 LLM이 넣은 '□'는 지운다
    func = next(d for d in res.drafts if d.title == "기능 요구사항")
    assert func.blocks[0].items == ["추진 방안"]
    # 토큰은 KB 값으로 바뀐다
    assert "정규직 개발 인력 85명 투입" in func.all_text()
    rules = {(f.rule, f.severity) for f in res.check.findings}
    assert ("COV-001", "blocker") not in rules            # 모든 요구사항에 대응 방안이 있다
    assert ("BLD-001", "blocker") in rules                # 블라인드인데 회사명이 들어갔다
    fact2 = next(f for f in res.check.findings if f.rule == "FACT-002")
    assert "35개" in fact2.message and "85명" not in fact2.message   # KB 근거 없는 수치만
    # 자료 요청: KB ID로 답한 근거는 빠지고, 없는 것만 남는다
    needs = {r.need for r in res.storyboard.data_requests}
    assert "클라우드 전환 실적" in needs and "F-002" not in needs
    # 기본은 KB를 보내지 않는다(공개 RFP만)
    assert all(c.data_class == "public" and "<kb_catalog>" not in c.context for c in fake.calls)
    # 절 호출들의 접두부(캐시 지점)는 같다
    section_calls = [c for c in fake.calls if c.task == "draft.section"]
    assert len({c.context for c in section_calls}) == 1
    trace = json.loads((project / "plan" / "trace.json").read_text(encoding="utf-8"))
    assert all(r["status"] == "drafted" for r in trace["rows"])


def test_share_kb_respects_provider_policy(project, kb_dir, profile):
    # KB 공유를 요청했지만 공급자가 internal을 허용하지 않으면 정책 오류 → 골격으로 대신한다
    res = run_draft(project, profile, kb_dir=kb_dir, provider=WriterFake(allowed=("public",)), share_kb=True)
    assert res.storyboard.origin == "skeleton" and any("보낼 수 없습니다" in n for n in res.notes)
    # 허용하면 KB 카탈로그(ID·설명)는 가지만 값은 가지 않는다
    fake = WriterFake(allowed=("public", "internal"))
    run_draft(project, profile, kb_dir=kb_dir, provider=fake, share_kb=True, refresh_storyboard=True)
    ctx = fake.calls[0].context
    assert "<kb_catalog>" in ctx and "F-002: 정규직 개발 인력 수" in ctx
    assert "85명" not in ctx and "1250000000" not in ctx and "12.5억" not in ctx
    assert fake.calls[0].data_class == "internal"
