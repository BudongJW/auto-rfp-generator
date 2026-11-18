"""별지 서식 찾기·잘라내기·채우기 테스트(M3)."""

from __future__ import annotations

import datetime as dt
import json
import zipfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from rfpgen.cli import app
from rfpgen.forms import classify, form_key, run_forms
from rfpgen.forms.fill import FillContext, fillable, plan_list
from rfpgen.forms.locate import find_regions, match_marker, unspace
from rfpgen.forms.oxml import HP, build_grid, p_text, replace_span
from rfpgen.kb import init_kb
from rfpgen.parse import InputFile, parse_document
from rfpgen.pipeline import analyze
from rfpgen.profile import load_profile
from rfpgen.render.pdf import converters_available
from rfpgen.schemas.rfp import Rfp

DAY = dt.date(2026, 11, 17)


def _build_rfp(path: Path) -> Path:
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
    doc.add_paragraph("참가신청은 별지 제1호 서식에 따라 작성하여 제출한다.")      # 본문 속 언급 — 서식 시작이 아니다
    doc.add_paragraph("[별지 제1호서식] 입찰참가신청서")                         # 서식 목록 — 내용이 없어 버린다
    doc.add_paragraph("[별지 제4호서식] 유사사업 수행실적")
    # 1호: 이름표 칸 + 날짜 줄 + 이름표-쌍점 줄
    doc.add_paragraph("[별지 제1호서식]")
    doc.add_paragraph("입 찰 참 가 신 청 서")
    _hwpx_table(doc, [["상호", "", "대표자", "      (인)"], ["사업자등록번호", "", "법인등록번호", ""],
                      ["주소", "", None, None], ["전화번호", "", "팩스번호", ""], ["입찰건명", "", None, None],
                      ["담당자", "", "설립일", "    .    .    ."]], {(2, 1): (1, 3), (4, 1): (1, 3)})
    doc.add_paragraph("위와 같이 입찰에 참가하고자 신청합니다.")
    doc.add_paragraph("2025.     .     .")
    doc.add_paragraph("신청인  상    호 :")
    doc.add_paragraph("대 표 자 :              (인)")
    doc.add_paragraph("한국○○원장 귀하")
    # 2호: 쪽 테두리용 1칸 표 안에 서식 전체
    frame = doc.add_table(1, 1)
    cell = frame.cell(0, 0)
    cell.text = "[별지 제2호서식]"
    for line in ("청 렴 서 약 서", "당사는 이 입찰에 참가하면서 다음 사항을 지킬 것을 서약합니다.",
                 "     년     월     일", "서약자  업 체 명 :", "대 표 자 :            (인)"):
        cell.add_paragraph(line)
    # 4호: 실적 목록(빈 행 1개 → 행 추가, 합계 행)
    doc.add_paragraph("[별지 제4호서식] 유사사업 수행실적")
    _hwpx_table(doc, [["순번", "사업명", "발주기관", "사업기간", "계약금액(백만원)", "참여형태"],
                      ["1", "", "", "", "", ""], ["합계", "", "", "", "", ""]], {})
    doc.add_paragraph("※ 최근 3년 이내 준공 실적만 기재")
    # 7호: 인력 목록(빈 행 3개, 인력 2명)
    doc.add_paragraph("[별지 제7호서식]")
    doc.add_paragraph("참여인력 현황")
    _hwpx_table(doc, [["성명", "역할", "등급", "경력(년)", "보유자격"], ["", "", "", "", ""], ["", "", "", "", ""],
                      ["", "", "", "", ""]], {})
    doc.add_paragraph("□ 상주  □ 비상주")
    # 9호: 하도급 — '하도급 업체'에 우리 회사 값을 넣으면 안 된다
    doc.add_paragraph("[별지 제9호서식] 하도급 계획서")
    _hwpx_table(doc, [["사업명", ""], ["하도급 부분", ""], ["하도급 업체", ""]], {})
    doc.save_to_path(str(path))
    return path


@pytest.fixture(scope="module")
def forms_project(tmp_path_factory):
    base = tmp_path_factory.mktemp("forms")
    src = _build_rfp(base / "제안요청서.hwpx")
    project = base / "proj"
    analyze([src], project, load_profile())
    kb = base / "kb"
    init_kb(kb)
    (kb / "projects.csv").write_text(
        "id,name,client,start,end,amount_krw,role,tech,evidence\n"
        "P-001,통합민원시스템 구축,가나시청,2024-03,2024-12,1250000000,주관,Java;eGovFrame,a.pdf\n"
        "P-002,행정정보 고도화,다라부,2023-02,2023-11,830000000,참여,Python,b.pdf\n", encoding="utf-8")
    (kb / "private" / "people.csv").write_text("id,name\nH-001,홍길순\n", encoding="utf-8")
    (kb / "private" / "forms.yaml").write_text("values:\n  담당자: 영업팀 김담당\n", encoding="utf-8")
    return project, kb


def _texts(path: Path) -> tuple[list[str], dict[int, list[list[str]]]]:
    doc = parse_document(InputFile(path.name, path.read_bytes()), "d1")
    paras = [b.text for b in doc.blocks if b.kind in ("para", "heading")]
    tables: dict[int, list[list[str]]] = {}
    for i, t in enumerate(doc.tables()):
        rows: dict[int, list[str]] = {}
        for c in doc.cells(t.id):
            rows.setdefault(c.cell.row, []).append(c.text)
        tables[i] = [rows[r] for r in sorted(rows)]
    return paras, tables


# ---------------------------------------------------------------- 단위

def test_marker_variants():
    assert match_marker("[별지 제1호서식]") == ("1", "")
    assert match_marker("【별지 제3호 서식】 청렴서약서") == ("3", "청렴서약서")
    assert match_marker("<서식 제2-1호> 제안서 표지") == ("2-1", "제안서 표지")
    assert match_marker("(별지 제05호 양식)") == ("5", "")
    assert match_marker("별지 제3호 서식에 따라 작성하여 제출") is None      # 본문 속 언급
    assert match_marker("1. 사업 개요") is None and match_marker("붙임 1") is None
    assert unspace("입 찰 참 가 신 청 서") == "입찰참가신청서" and unspace("유사사업  수행실적") == "유사사업 수행실적"
    assert form_key("별지 제07호") == "7" and form_key("별지 제2의3호") == "2-3"


def test_replace_span_keeps_runs():
    from lxml import etree

    p = etree.fromstring(f'<hp:p xmlns:hp="{HP[1:-1]}"><hp:run charPrIDRef="7"><hp:t>대표자 :</hp:t></hp:run>'
                         f'<hp:run charPrIDRef="9"><hp:t>         (인)</hp:t></hp:run></hp:p>')
    text = p_text(p)
    replace_span(p, len("대표자 :"), text.index("(인)"), " 홍길동  ")
    assert p_text(p) == "대표자 : 홍길동  (인)"
    runs = p.findall(f"{HP}run")
    assert runs[1].find(f"{HP}t").text.startswith(" 홍길동")      # 값은 빈칸 쪽 글자 모양(charPr 9)을 따른다
    empty = etree.fromstring(f'<hp:p xmlns:hp="{HP[1:-1]}"><hp:run charPrIDRef="3"/></hp:p>')
    replace_span(empty, 0, 0, "값")
    assert p_text(empty) == "값" and empty.find(f"{HP}run").get("charPrIDRef") == "3"


def test_fillable_and_resolver():
    assert fillable("   ")[0] and fillable("○○○")[0] and fillable("2025.   .   .")[0]
    ok, a, b = fillable("        (인)")
    assert ok and b == 8
    ok, a, b = fillable("      명")
    assert ok and b == 6
    assert not fillable("서울특별시")[0]
    from rfpgen.schemas.kb import CompanyKB, Identity

    ctx = FillContext(rfp=Rfp(), kb=CompanyKB(identity=Identity(name="(주)가나")), date=DAY,
                      overrides={"담당자": "김담당"})
    assert ctx.resolve("신청인  상    호").value == "(주)가나"
    assert ctx.resolve("업체명(상호)").field == "identity.name"
    assert ctx.resolve("하도급 업체") is None                    # 다른 회사 칸에 우리 값을 넣지 않는다
    assert ctx.resolve("담 당 자").value == "김담당" and ctx.resolve("담 당 자").source == "user"


def test_vertical_two_row_table_is_not_a_list():
    from conftest import _hwpx_table
    from hwpx import HwpxDocument

    doc = HwpxDocument.new()
    _hwpx_table(doc, [["사업명", "발주기관"], ["", ""]], {})
    _hwpx_table(doc, [["사업명", "발주기관", "계약금액"], ["", "", ""]], {})
    tbls = list(doc.sections[0].element.iter(f"{HP}tbl"))
    assert plan_list(build_grid(tbls[0]), 0) is None
    plan = plan_list(build_grid(tbls[1]), 0)
    assert plan is not None and plan.kind == "projects" and plan.data_rows == [1]


def test_find_regions_skips_index_and_references(tmp_path):
    from hwpx import HwpxDocument

    doc = HwpxDocument.open(str(_build_rfp(tmp_path / "r.hwpx")))
    regions = find_regions([s.element for s in doc.sections])
    assert [(r.key, r.title) for r in regions] == [("1", "입찰참가신청서"), ("2", "청렴서약서"), ("4", "유사사업 수행실적"),
                                                  ("7", "참여인력 현황"), ("9", "하도급 계획서")]
    assert classify("하도급 계획서", "9", set()) == "하도급계획서" and classify("참여인력 현황", "7", set()) == "정량제안서"
    assert classify("참여인력 현황", "7", {"7"}) == "정성제안서" and classify("청렴서약서", "2", set()) == "기타문서"


# ---------------------------------------------------------------- 통합

def test_run_forms_fills_and_reports(forms_project):
    project, kb = forms_project
    rep = run_forms(project, kb_dir=kb, date=DAY)
    by_key = {f.key: f for f in rep.forms}
    assert list(by_key) == ["1", "2", "4", "7", "9"]

    # 1호: 이름표 칸·서명 칸·날짜 줄·이름표-쌍점 줄
    f1 = by_key["1"]
    paras, tables = _texts(project / f1.output)
    assert paras[0] == "[별지 제1호서식]"                       # RFP 본문은 잘라냈다
    assert not any("요구사항" in p for p in paras)
    t = tables[0]
    assert t[0] == ["상호", "(주)예시정보", "대표자", "홍길동 (인)"]
    assert t[1][1] == "123-45-67890" and t[4][1] == "2026년 통합민원시스템 고도화 사업"
    assert t[5] == ["담당자", "영업팀 김담당", "설립일", "2010. 3. 2."]          # private/forms.yaml 값
    assert "2026. 11. 17." in paras
    assert any(p.startswith("신청인") and p.endswith("(주)예시정보") for p in paras)
    assert "대 표 자 : 홍길동 (인)" in paras
    rules1 = {x.rule for x in f1.findings}
    assert {"FORM-SEAL", "FORM-DATE", "FORM-PLACEHOLDER"} <= rules1 and "FORM-UNFILLED" not in rules1

    # 2호: 쪽 테두리 표 안의 날짜·서약자
    paras2, tables2 = _texts(project / by_key["2"].output)
    frame = "\n".join(c for row in tables2[0] for c in row)
    assert "2026년 11월 17일" in frame and "업 체 명 : (주)예시정보" in frame and "홍길동" in frame

    # 4호: 행을 늘려 실적 2건, 합계
    f4 = by_key["4"]
    _, t4 = _texts(project / f4.output)
    assert f4.added_rows == 1 and f4.doc_type == "정량제안서"
    assert t4[0][1] == ["1", "통합민원시스템 구축", "가나시청", "2024.03 ~ 2024.12", "1,250", "주관"]
    assert t4[0][2] == ["2", "행정정보 고도화", "다라부", "2023.02 ~ 2023.11", "830", "참여"]
    assert t4[0][3][0] == "합계" and t4[0][3][4] == "2,080"

    # 7호: 실명은 private에서, 없는 사람은 비움, 보고서에는 가림
    f7 = by_key["7"]
    _, t7 = _texts(project / f7.output)
    assert t7[0][1] == ["홍길순", "PM", "특급", "18", "정보관리기술사, PMP"]
    assert t7[0][2][0] == "" and t7[0][2][1] == "아키텍트"
    assert t7[0][3] == ["", "", "", "", ""]
    assert {"FORM-NAMES", "FORM-CHECKBOX"} <= {x.rule for x in f7.findings}
    report_text = (project / "out" / "forms" / "forms.json").read_text(encoding="utf-8") + \
        (project / "out" / "forms" / "forms.md").read_text(encoding="utf-8")
    assert "홍길순" not in report_text and "(실명" in report_text
    assert "홍길순" not in "".join(p.read_text(encoding="utf-8") for p in (project / "checks").glob("forms-*"))

    # 9호: 하도급 업체 칸은 비우고 보고
    f9 = by_key["9"]
    _, t9 = _texts(project / f9.output)
    assert t9[0][0][1] == "2026년 통합민원시스템 고도화 사업" and t9[0][2][1] == ""
    assert f9.doc_type == "하도급계획서"
    assert any(x.rule == "FORM-UNFILLED" and "하도급 업체" in x.message for x in f9.findings)

    # 저장한 서식은 python-hwpx 검증을 통과하고, 구역 설정(쪽 크기)이 남아 있다
    from hwpx import HwpxDocument

    for f in rep.forms:
        d = HwpxDocument.open(str(project / f.output))
        assert not d.validate().errors
        with zipfile.ZipFile(project / f.output) as zf:
            assert b"secPr" in zf.read("Contents/section0.xml")


def test_blind_forms_and_missing(forms_project, tmp_path):
    import shutil

    project0, kb = forms_project
    project = tmp_path / "blind"
    shutil.copytree(project0, project)
    rfp_path = sorted(project.glob("rfp/rfp.v*.json"))[-1]
    data = json.loads(rfp_path.read_text(encoding="utf-8"))
    data["guideline"]["blind"] = {"value": True}
    data["guideline"]["prescribed_toc"] = {"value": [
        {"number": "Ⅵ", "title": "투입 인력", "level": 1, "production": "별지서식", "form_refs": ["별지 제7호"]}]}
    data["guideline"]["required_documents"] = [{"name": "보안서약서", "form_no": "별지 제12호"}]
    rfp_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    rep = run_forms(project, kb_dir=kb, date=DAY)
    f7 = next(f for f in rep.forms if f.key == "7")
    assert f7.blind and f7.doc_type == "정성제안서"
    _, t7 = _texts(project / f7.output)
    assert t7[0][1][0] == "" and t7[0][1][1] == "PM"                    # 블라인드: 성명 비움
    assert any("블라인드" in x.message for x in f7.findings if x.rule == "FORM-NAMES")
    assert not next(f for f in rep.forms if f.key == "1").blind       # 입찰참가신청서는 블라인드 문서가 아니다
    missing = [x for x in rep.findings if x.rule == "FORM-MISSING"]
    assert [x.section_id for x in missing] == ["별지 제12호"]
    (project / "forms.yaml").write_text("doc_types:\n  '2': 정량제안서\nskip: ['9']\n", encoding="utf-8")
    rep2 = run_forms(project, kb_dir=kb, date=DAY)
    assert [f.key for f in rep2.forms] == ["1", "2", "4", "7"]
    assert next(f for f in rep2.forms if f.key == "2").doc_type == "정량제안서"


def test_cli_forms_without_kb(forms_project, tmp_path):
    import shutil

    project = tmp_path / "nokb"
    shutil.copytree(forms_project[0], project)
    r = CliRunner().invoke(app, ["forms", str(project), "--date", "2026-11-17"])
    assert r.exit_code == 0, r.output
    assert "별지 서식 5개" in r.output and "KB 없이" in r.output
    r = CliRunner().invoke(app, ["forms", str(project), "--date", "2026-13-01"])
    assert r.exit_code == 2


@pytest.mark.skipif(not all(converters_available().values()), reason="HWPX→PDF 변환기(rhwp 사이드카)가 없습니다")
def test_package_includes_forms(forms_project, tmp_path):
    import shutil

    from rfpgen.draft.pipeline import run_draft
    from rfpgen.package import build_package
    from rfpgen.render.pdf import inspect_pdf

    project = tmp_path / "pkg"
    shutil.copytree(forms_project[0], project)
    kb = forms_project[1]
    profile = load_profile()
    run_draft(project, profile, kb_dir=kb)
    run_forms(project, kb_dir=kb, date=DAY)
    res = build_package(project, profile, kb_dir=kb)
    names = [d.pdf.name for d in res.docs]
    assert names[0] == "01_정성제안서.pdf"
    assert {"04_정량제안서.pdf", "05_하도급계획서.pdf", "06_기타문서.pdf"} <= set(names)
    quant = next(d for d in res.docs if d.pdf.name == "04_정량제안서.pdf")
    assert quant.pages == 2                                             # 4호·7호 서식 묶음
    from rfpgen.render.pdf import read_bookmarks

    marks = read_bookmarks(quant.pdf)                                   # 서식마다 책갈피
    assert [(lv, page) for lv, _, page in marks] == [(0, 0), (0, 1)] and marks[0][1].startswith("별지 제4호")
    assert set(inspect_pdf(quant.pdf).metadata) == {"/Title"}
    assert res.check.stats.get("main_pages") is not None               # 쪽수 점검은 본문만 센다
    rules = {f.rule for f in res.check.findings}
    assert "FORM-UNFILLED" in rules                                     # 별지 점검을 이어 붙였다
    assert "날인본" in res.checklist.read_text(encoding="utf-8")
