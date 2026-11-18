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
    assert numbers("발주기관과 1:1 대응 체계, 노드 1대 장애") == ["1대"]          # 비율(1:1)은 수치가 아니다


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
    sent = " ".join(c.system + c.context + c.instruction for c in fake.calls)
    assert "123-45-67890" not in sent and "02-123-4567" not in sent      # 별지용 회사 기본정보는 보내지 않는다
    assert fake.calls[0].data_class == "internal"


# ---- RFP 개요 발췌(개요 절 맥락) ----------------------------------------------------------------


def _doc(blocks, role="제안요청서"):
    from rfpgen.schemas.docir import Document

    return Document(doc_id="d01", filename="rfp.pdf", format="pdf", sha256="0", role=role, blocks=blocks)


def test_overview_excerpt_picks_overview_chapters():
    from rfpgen.draft.context import overview_excerpt
    from rfpgen.schemas.docir import Block, TableInfo, TableRef

    def cell(i, row, col, text):
        return Block(id=f"c{i}", kind="cell", text=text, cell=TableRef(table_id="t1", row=row, col=col))

    blocks = [
        Block(id="b0", kind="heading", level=1, text="Ⅵ. 제안서 작성 안내사항 ··········· 351"),   # 목차 줄
        Block(id="b1", kind="heading", level=1, text="Ⅰ. 사업개요"),
        Block(id="b2", kind="para", text="\U000f02b1 추진배경"),
        Block(id="b3", kind="para", text="ㅇ 노후화된 업무시스템 재구축 필요"),
        Block(id="t1", kind="table", table=TableInfo(rows=2, cols=2)),
        cell(1, 0, 0, "구분"), cell(2, 0, 1, "내용"), cell(3, 1, 0, "사업기간"), cell(4, 1, 1, "16개월"),
        Block(id="b4", kind="heading", level=1, text="Ⅱ. 현황"),
        Block(id="b5", kind="para", text="ㅇ 임직원 708명"),
        Block(id="b6", kind="heading", level=1, text="Ⅴ. 제안 요청 사항"),
        Block(id="b7", kind="para", text="SFR-001 거래 처리 기능"),
    ]
    out = overview_excerpt([_doc(blocks)])
    assert out.startswith("<rfp_overview>") and "[Ⅰ. 사업개요]" in out and "[Ⅱ. 현황]" in out
    assert "사업기간 | 16개월" in out and "추진배경" in out and "\U000f02b1" not in out
    assert "SFR-001" not in out and "351" not in out                  # 요구사항 장·목차 줄은 넣지 않는다

    # 제목 판별이 없는 문서: 'Ⅰ. …' 꼴의 짧은 문단을 장으로 본다
    flat = [Block(id=f"p{i}", kind="para", text=t) for i, t in
            enumerate(["Ⅰ. 사업 개요", "○ 민원 서비스 편의성 향상이 목적", "Ⅱ. 제안 요청 내용", "○ 요구사항 문장"])]
    out = overview_excerpt([_doc(flat)])
    assert "편의성 향상이 목적" in out and "요구사항 문장" not in out
    assert overview_excerpt([_doc(flat, role="별지서식")]) == ""          # 별지 서식은 보지 않는다


def test_llm_context_carries_rfp_overview_and_requirement_list(tmp_path, profile):
    from rfpgen.sample import build_sample_rfp

    src = build_sample_rfp(tmp_path / "예제.hwpx", with_forms=False)
    project = tmp_path / "proj"
    analyze([src], project, profile)
    fake = WriterFake()
    run_draft(project, profile, provider=fake)
    ctx = next(c for c in fake.calls if c.task == "draft.section").context
    assert "발주기관: 가상시 민원봉사과" in ctx and "사업예산: 1,250,000,000원" in ctx
    assert "요구사항 목록(ID 이름):" in ctx and "SFR-002 민원 처리 현황 조회" in ctx and "PMR-001 사업 관리" in ctx
    assert "<rfp_overview>" in ctx and "첨부파일 용량 제한(10MB)" in ctx
    assert all(c.data_class == "public" for c in fake.calls)


def test_fact_check_accepts_rfp_values_and_counts(project):
    """RFP에 있는 값(사업명의 연도·예산)과 RFP에서 바로 셀 수 있는 값(요구사항 건수·배점·사업기간 안의 개월)은 근거로 본다."""
    from rfpgen.check import rfp_number_sources, supported
    from rfpgen.schemas.rfp import Rfp

    rfp = Rfp.model_validate_json(sorted(project.glob("rfp/rfp.v*.json"))[-1].read_text(encoding="utf-8"))
    src = rfp_number_sources(rfp)
    for ok in ["2026년", "5건", "2건", "8개월", "3개월", "1,250,000,000원", "12.5억", "15점"]:
        assert supported(ok, src), ok
    for bad in ["9개월", "6개", "35개", "99%", "25건"]:
        assert not supported(bad, src), bad
    assert numbers("착수 1~2개월, 6개 단계") == ["2개월", "6개"]          # '2개월'을 '2개'로 읽지 않는다


class ExpandingFake(WriterFake):
    """1차 초안은 짧게, 보강 요청에는 길게 답한다."""

    def complete(self, call, json_schema):
        reply = super().complete(call, json_schema)
        if call.task != "draft.section.expand":
            return reply
        data = json.loads(reply.text)
        data["blocks"].append({"kind": "bullets", "text": "", "level": 1, "items": ["세부 수행 절차와 검증 방법 " * 40],
                               "table_header": [], "table_rows": [], "req_refs": []})
        return ProviderReply(text=json.dumps(data, ensure_ascii=False), model="fake", stop_reason="end_turn",
                             usage=reply.usage)


def test_short_llm_section_gets_one_expansion(project, kb_dir, profile):
    fake = ExpandingFake()
    res = run_draft(project, profile, kb_dir=kb_dir, provider=fake)
    expands = [c for c in fake.calls if c.task == "draft.section.expand"]
    assert expands and all("<draft>" in c.instruction and "목표 범위" in c.instruction for c in expands)
    func = next(d for d in res.drafts if d.title == "기능 요구사항")
    assert "세부 수행 절차와 검증 방법" in func.all_text() and len(func.llm_call_ids) <= 2
    # 0이면 보강하지 않는다
    tasks = dict(profile.value("llm.tasks"))
    tasks["section"] = {**tasks["section"], "expand_below": 0}
    fake = ExpandingFake()
    run_draft(project, profile.merged({"llm": {"tasks": {"value": tasks}}}, "test"), kb_dir=kb_dir, provider=fake,
              refresh_storyboard=True)
    assert not [c for c in fake.calls if c.task == "draft.section.expand"]


class SlowFake(WriterFake):
    """동시에 몇 개가 들어오는지 잰다."""

    def __init__(self) -> None:
        import threading

        super().__init__()
        self.lock = threading.Lock()
        self.active = 0
        self.peak = 0
        self.first_alone = None

    def complete(self, call, json_schema):
        import time

        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
            if call.task == "draft.section" and self.first_alone is None:
                self.first_alone = self.active == 1
        time.sleep(0.05)
        try:
            return super().complete(call, json_schema)
        finally:
            with self.lock:
                self.active -= 1


def test_sections_run_in_parallel_after_first(project, kb_dir, profile):
    fake = SlowFake()
    res = run_draft(project, profile, kb_dir=kb_dir, provider=fake)
    assert fake.first_alone and fake.peak > 1                      # 첫 절은 혼자, 나머지는 동시에
    assert all(d.origin == "llm" for d in res.drafts)
    from rfpgen.draft.context import leaf_sections
    from rfpgen.schemas.plan import Outline

    outline = Outline.model_validate_json((project / "plan" / "outline.json").read_text(encoding="utf-8"))
    assert [d.section_id for d in res.drafts] == [n.id for n in leaf_sections(outline)]   # 결과는 목차 순서
    lines = (project / "audit" / "llm_calls.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(fake.calls) and all(json.loads(x)["status"] == "ok" for x in lines)   # 줄이 섞이지 않는다
    tasks = dict(profile.value("llm.tasks"))
    tasks["section"] = {**tasks["section"], "parallel": 1}
    fake = SlowFake()
    run_draft(project, profile.merged({"llm": {"tasks": {"value": tasks}}}, "test"), kb_dir=kb_dir, provider=fake,
              refresh_storyboard=True)
    assert fake.peak == 1


def test_data_requests_drop_rfp_content_and_merge():
    from rfpgen.draft.write import merge_requests
    from rfpgen.schemas.draft import DataRequest

    def r(sec, need):
        return DataRequest(section_id=sec, section_title=sec, need=need, reason="스토리보드가 요구하지만 KB에 없음")

    out = merge_requests([
        r("Ⅰ.1", "RFP의 사업 추진배경·목적 원문"),                 # RFP에 있는 내용은 뺀다
        r("Ⅳ.1", "SFR 99건 전체 목록과 세부 내용"),
        r("Ⅲ.3", "PMR-005·006 투입인력 요건 원문"),
        r("Ⅰ.3", "품질·보안 관련 공인 인증 보유 현황 [확인 필요]"),
        r("Ⅴ.2", "품질 관련 공인 인증 보유 여부와 인증서"),       # 같은 분류의 비슷한 요청은 묶는다
        r("Ⅲ.3", "외화증권 업무 수행 경험이 있는 투입 인력"),      # 인력(실적보다 먼저 맞춘다)
        r("Ⅱ.4", "클라우드 전환 수행 실적"),
        r("Ⅲ.1", "현행 시스템 구성도와 업무 처리 규모"),          # 발주기관에 확인할 것
        r("Ⅲ.2", "사업기간과 오픈 목표일"),
    ])
    got = [(m.category, m.need, m.sections) for m in out]
    assert got == [
        ("실적", "클라우드 전환 수행 실적", ["Ⅱ.4"]),
        ("인력", "외화증권 업무 수행 경험이 있는 투입 인력", ["Ⅲ.3"]),
        ("인증", "품질·보안 관련 공인 인증 보유 현황", ["Ⅰ.3", "Ⅴ.2"]),
        ("발주기관 확인", "현행 시스템 구성도와 업무 처리 규모", ["Ⅲ.1"]),
        ("발주기관 확인", "사업기간과 오픈 목표일", ["Ⅲ.2"]),
    ]
    assert out[2].section_title == "Ⅰ.3, Ⅴ.2" and "절 2곳" in out[2].reason
    assert "발주기관 질의" in out[3].reason
