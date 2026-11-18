"""실제 정부 서식(조달청 협상기준 별지, HWP 5.0)으로 보는 별지 채우기 회귀 테스트.

픽스처 출처와 저작권 근거는 tests/fixtures/forms/README.md.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

import pytest
from lxml import etree

from rfpgen.forms import run_forms
from rfpgen.forms.fill import FillContext, header_like, label_like, plan_list
from rfpgen.forms.oxml import HP, build_grid, p_text, refit_line_cache, replace_span
from rfpgen.kb import init_kb
from rfpgen.parse import InputFile, parse_document
from rfpgen.pipeline import analyze
from rfpgen.profile import load_profile
from rfpgen.schemas.kb import CompanyKB, Identity
from rfpgen.schemas.rfp import Rfp

FIX = Path(__file__).parent / "fixtures" / "forms"
FIXTURES = {
    "별지13_사전접촉여부확인신고서.hwp": "52ee86eb49d578c71f276e49af29d48c99d807a04aae06fa352440a1748bd6ed",
    "별지14_소프트웨어사업하도급계획서.hwp": "65498a5988c6474093bd55a564440dc74140a1430fdbbc92df1c891a58558559",
    "별지15_수행실적총괄표.hwp": "18d8d3dd003fad21fb865593f486fc38dbf634ef708975ca062a6980001b0400",
    "별지16_수행실적증명서.hwp": "3b3f18ad814e0ccd55aa66ada455b77560834a726d8fcd3ea1a77425a533c8e2",
    "별지17_상용SW제품별하도급계획서.hwp": "e3195454093366a9220fc486bd159da517a05298eafd6b8a61d0ba73807e2d3e",
    "별지19_국산제품활용계획서.hwp": "97570bdb88d16dbff36b0b0c7f8b8efdf956b44883a97598a449f74e8bcd0b49",
    "별지21_입찰업체서약서.hwp": "dbb90e7458891c748204dbc4ad4296155a1a165557eadb290589b0d754028564",
}
DAY = dt.date(2026, 12, 1)


def _hwpx_of(name: str):
    from hwpx import HwpxDocument
    from hwpx.hwp5.package import convert, to_hwpx_bytes

    return HwpxDocument.open(to_hwpx_bytes(convert((FIX / name).read_bytes()).files))


@pytest.fixture(scope="module")
def real_forms(tmp_path_factory):
    from test_forms import _build_rfp

    base = tmp_path_factory.mktemp("realforms")
    src = _build_rfp(base / "제안요청서.hwpx")
    files = [src]
    for name in FIXTURES:
        files.append(base / name)
        shutil.copy(FIX / name, files[-1])
    project = base / "proj"
    analyze(files, project, load_profile())
    rfp_path = max(project.glob("rfp/rfp.v*.json"))
    data = json.loads(rfp_path.read_text(encoding="utf-8"))
    data["notice"]["period"] = {"value": "계약일로부터 8개월"}
    data["notice"]["agency"] = {"value": "가나시 민원과"}
    rfp_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    kb = base / "kb"
    init_kb(kb)
    (kb / "projects.csv").write_text(
        "id,name,client,start,end,amount_krw,role,tech,evidence\n"
        "P-001,통합민원시스템 구축,가나시청,2024-03,2024-12,1250000000,주관,Java,a.pdf\n"
        "P-002,행정정보 고도화,다라부,2023-02,2023-11,830000000,참여,Python,b.pdf\n", encoding="utf-8")
    rep = run_forms(project, kb_dir=kb, date=DAY)
    return project, rep


def _cells(path: Path, table: int) -> dict[tuple[int, int], str]:
    doc = parse_document(InputFile(path.name, path.read_bytes()), "d1")
    t = doc.tables()[table]
    return {(c.cell.row, c.cell.col): c.text for c in doc.cells(t.id)}


def _paras(path: Path) -> list[str]:
    from hwpx import HwpxDocument

    doc = HwpxDocument.open(str(path))
    return [p_text(p) for s in doc.sections for p in s.element.iter(f"{HP}p")]


def _form(rep, key: str):
    return next(f for f in rep.forms if f.key == key)


# ---------------------------------------------------------------- 단위

def test_fixtures_are_unchanged():
    for name, digest in FIXTURES.items():
        assert hashlib.sha256((FIX / name).read_bytes()).hexdigest() == digest, name


def test_wrapped_headers_make_a_list():
    doc = _hwpx_of("별지15_수행실적총괄표.hwp")
    tbls = [t for t in doc.sections[0].element.iter(f"{HP}tbl") if len(build_grid(t).cells) > 1]
    grid = build_grid(tbls[0])
    head = [c.text for c in grid.row_cells(0)]
    assert head[0] == "일련\n번호" and not label_like(head[0]) and header_like(head[0])
    plan = plan_list(grid, 0)
    assert plan is not None and plan.kind == "projects" and plan.data_rows == [1, 2, 3, 4, 5, 6]
    assert {f for f, _ in plan.columns.values()} == {"index", "name", "client", "amount", "end"}


def test_joint_venture_labels_resolve():
    ctx = FillContext(rfp=Rfp(), kb=CompanyKB(identity=Identity(name="(주)가나", ceo="김대표")), date=DAY)
    assert ctx.resolve("공동수급체 대  표   상  호").value == "(주)가나"
    assert ctx.resolve("(공동수급체 대표)상호").field == "identity.name"
    assert ctx.resolve("공동수급체 구성원 상호") is None          # 구성원은 다른 회사일 수 있다
    assert ctx.resolve("영업소재지").field == "company.address"
    assert ctx.resolve("제 출 처").field == "rfp.submit_to"


def test_refit_line_cache_keeps_one_line_only_when_it_fits():
    def para(text: str, width: int) -> etree._Element:
        return etree.fromstring(
            f'<hp:p xmlns:hp="{HP[1:-1]}"><hp:run charPrIDRef="4"><hp:t>{text}</hp:t></hp:run>'
            f'<hp:linesegarray><hp:lineseg textpos="0" vertpos="9400" vertsize="1200" textheight="1200" '
            f'baseline="1020" spacing="2400" horzpos="0" horzsize="{width}" flags="393216"/></hp:linesegarray></hp:p>')

    p = para(" ◦ 수  요  기  관: ", 46604)
    replace_span(p, len(p_text(p)), len(p_text(p)), "가나시 민원과")
    segs = p.findall(f"{HP}linesegarray/{HP}lineseg")
    assert p_text(p).endswith("가나시 민원과") and len(segs) == 1 and segs[0].get("horzsize") == "46604"
    narrow = para("주소: ", 6000)                               # 좁은 칸: 넘치면 캐시를 지운다
    replace_span(narrow, 4, 4, "서울특별시 가나구 가나로 1")
    assert narrow.find(f"{HP}linesegarray") is None
    two = para("a", 46604)
    two.find(f"{HP}linesegarray").append(etree.fromstring(f'<hp:lineseg xmlns:hp="{HP[1:-1]}" textpos="1"/>'))
    refit_line_cache(two)
    assert two.find(f"{HP}linesegarray") is None              # 두 줄이던 문단은 다시 배치하게 둔다


# ---------------------------------------------------------------- 통합

def test_real_forms_skip_non_bidder_form(real_forms):
    project, rep = real_forms
    assert [f.key for f in rep.forms] == ["1", "2", "4", "7", "9", "14", "15", "16", "17", "19", "21"]
    skip = [x for x in rep.findings if x.rule == "FORM-SKIP"]
    assert len(skip) == 1 and "별지 제13호" in skip[0].message and "include" in skip[0].message
    (project / "forms.yaml").write_text("include: ['13']\n", encoding="utf-8")
    try:
        again = run_forms(project, kb_dir=project.parent / "kb", date=DAY)
        assert "13" in [f.key for f in again.forms]
    finally:
        (project / "forms.yaml").unlink()
        run_forms(project, kb_dir=project.parent / "kb", date=DAY)


def test_real_form_15_list_and_summary(real_forms):
    project, rep = real_forms
    f15 = _form(rep, "15")
    cells = _cells(project / f15.output, 1)
    assert [cells[(1, c)] for c in range(6)] == ["1", "통합민원시스템 구축", "가나시청", "1,250,000", "2024.12", ""]
    assert [cells[(2, c)] for c in range(6)] == ["2", "행정정보 고도화", "다라부", "830,000", "2023.11", ""]
    assert all(cells[(3, c)] == "" for c in range(6))
    summary = _cells(project / f15.output, 2)
    assert summary[(1, 2)] == "2" and summary[(1, 3)] == "2,080,000"          # 입찰자가 제출한 납품실적
    assert summary[(2, 2)] == summary[(3, 2)] == summary[(4, 2)] == ""          # 수요기관 검토·평가 칸
    rules = {x.rule for x in f15.findings}
    assert "FORM-UNFILLED" not in rules and "FORM-OTHERS" in rules
    assert not any("2026년" in x.value for x in f15.fills)                    # 이번 사업명을 목록에 넣지 않는다


def test_real_form_16_certificate(real_forms):
    project, rep = real_forms
    f16 = _form(rep, "16")
    cells = _cells(project / f16.output, 1)
    assert cells[(0, 2)] == "(주)예시정보" and cells[(0, 7)] == "홍길동"
    assert cells[(1, 2)].startswith("서울특별시")                             # 영업소재지
    assert cells[(3, 7)] == "가나시 민원과"                                    # 제출처
    assert cells[(4, 2)] == "" and cells[(5, 2)] == ""                         # 증명받을 과거 사업명·개요
    paras = _paras(project / f16.output)
    issuer_addr = [p for p in paras if re.match(r"\s*주\s*소\s*:", p)]
    assert issuer_addr and not any("서울" in p for p in issuer_addr)            # 발급기관 주소는 비운다
    rules = {x.rule for x in f16.findings}
    assert "FORM-UNFILLED" not in rules and "FORM-LIST" not in rules
    others = " ".join(x.message for x in f16.findings if x.rule == "FORM-OTHERS")
    assert "발급부서" in others and "사업개요" in others


def test_real_forms_14_19_21_paragraphs(real_forms):
    project, rep = real_forms
    f14 = _form(rep, "14")
    cells = _cells(project / f14.output, 1)
    assert cells[(0, 6)] == "8 개월" and cells[(1, 3)] == "(주)예시정보"
    paras14 = _paras(project / f14.output)
    assert any("공동수급체" in p and p.rstrip().endswith("(주)예시정보") for p in paras14)
    assert any(p.strip() == "2026년 12월 1일" for p in paras14)                 # 서식 전체를 감싼 표 안 날짜 줄
    paras19 = _paras(project / _form(rep, "19").output)
    assert any("(공동수급체 대표)상호" in p and "(주)예시정보" in p for p in paras19)
    assert any(p.strip() == "2026년 12월 1일" for p in paras19)
    f21 = _form(rep, "21")
    paras21 = _paras(project / f21.output)
    assert any(p.startswith(" 서약자 : (주)예시정보  대표 홍길동 (인)") for p in paras21)
    assert any("△△회사" in p for p in paras21)                                # 공동수급 구성원 줄은 사람이 정한다
    assert {"FORM-JV", "FORM-SEAL"} <= {x.rule for x in f21.findings}
    assert "FORM-PLACEHOLDER" not in {x.rule for x in f21.findings}
    with zipfile.ZipFile(project / f21.output) as zf:
        xml = zf.read("Contents/section0.xml").decode("utf-8")
    at = xml.index("가나시 민원과")
    seg = xml[at:xml.index("</hp:p>", at)]
    assert seg.count("<hp:lineseg ") == 1                                       # 한 줄 캐시를 새로 써 두었다


def test_real_form_17_example_values(real_forms):
    project, rep = real_forms
    f17 = _form(rep, "17")
    ex = [x for x in f17.findings if x.rule == "FORM-EXAMPLE"]
    assert len(ex) == 1 and "19,500,000" in ex[0].message and "6곳" in ex[0].message
    cells = _cells(project / f17.output, 1)
    assert cells[(1, 4)] == "19,500,000"                                       # 지우지는 않는다
    others = [x for f in rep.forms if f.key != "17" for x in f.findings if x.rule == "FORM-EXAMPLE"]
    assert others == []                                                          # 순번·실적을 채운 표는 예시가 아니다


def test_real_form_16_request_drafts(real_forms, tmp_path):
    project, rep = real_forms
    f16 = _form(rep, "16")
    assert f16.external and [Path(x).name for x in f16.requests] == ["별지16_수행실적증명서_P-001.hwpx",
                                                                      "별지16_수행실적증명서_P-002.hwpx"]
    assert any(x.rule == "FORM-REQUEST" and "2장" in x.message for x in f16.findings)
    cells = _cells(project / f16.requests[0], 1)
    assert cells[(0, 2)] == "(주)예시정보" and cells[(3, 7)] == "가나시 민원과"          # 신청인·제출처는 그대로
    assert cells[(4, 2)] == "통합민원시스템 구축"                                         # 증명받을 과거 사업
    assert cells[(8, 3)] == "2024.03 ~ 2024.12" and cells[(8, 5)] == "1,250,000,000원" and cells[(8, 6)] == "2024.12"
    assert cells[(8, 1)] == "" and cells[(8, 7)] == ""                                   # 계약번호·지분율은 비움
    paras = _paras(project / f16.requests[0])
    assert not any(re.match(r"\s*주\s*소\s*:", p) and "서울" in p for p in paras)         # 발급기관 칸은 그대로 비움
    second = _cells(project / f16.requests[1], 1)
    assert second[(4, 2)] == "행정정보 고도화"

    # 제출 묶음에는 넣지 않는다(발급받은 증명서를 따로 올린다) — 변환기 없이 보려고 이 서식만 남긴 보고서로
    from rfpgen.package import _package_forms
    from rfpgen.schemas.draft import CheckReport
    from rfpgen.schemas.forms import FormsReport

    only = tmp_path / "proj"
    (only / "out" / "forms").mkdir(parents=True)
    (only / "out" / "forms" / "forms.json").write_text(
        FormsReport(run_id="r", date="2026-12-01", forms=[f16]).model_dump_json(), encoding="utf-8")
    notes: list[str] = []
    docs = _package_forms(only, tmp_path / "sub", tmp_path / "pdf", "사업", CheckReport(run_id="r"), notes)
    assert docs == [] and any("별지 제16호" in n and "발급받은 증명서" in n for n in notes)
