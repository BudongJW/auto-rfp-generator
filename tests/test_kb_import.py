"""과거 제안서 가져오기(rfpgen kb import)."""

from __future__ import annotations

from typer.testing import CliRunner

from rfpgen.cli import app
from rfpgen.draft.context import relevant_content
from rfpgen.kb import init_kb, load_kb
from rfpgen.kb.importer import import_proposals
from rfpgen.schemas.plan import OutlineNode

LONG = ("○ 민원 처리 전 과정을 온라인으로 전환하려는 정책 방향에 맞춰 신청·접수·처리·통지 단계를 하나의 흐름으로 "
        "설계하고, 단계별 처리 기한과 담당 부서를 화면에 공개하여 민원인이 진행 상황을 직접 확인하도록 함")


def _past_proposal(path):
    from hwpx import HwpxDocument

    doc = HwpxDocument.new()
    doc.add_paragraph("Ⅲ. 전략 및 방법론")
    doc.add_paragraph("1. 사업 이해도")
    doc.add_paragraph("(주)예시정보는 YesiFlow를 기반으로 민원 시스템을 고도화한 경험이 있음")
    for _ in range(3):
        doc.add_paragraph(LONG)
    t = doc.add_table(2, 2)
    for (r, c), v in {(0, 0): "구분", (0, 1): "내용", (1, 0): "PM", (1, 1): "홍○○ 특급"}.items():
        t.cell(r, c).text = v
    doc.add_paragraph("2. 추진 전략")
    for _ in range(2):
        doc.add_paragraph(LONG.replace("민원", "행정"))
    doc.add_paragraph("3. 기타")
    doc.add_paragraph("짧은 절")
    doc.save_to_path(str(path))
    return path


def test_import_splits_masks_and_feeds_relevant_content(tmp_path):
    kb_dir = tmp_path / "kb"
    init_kb(kb_dir)
    src = _past_proposal(tmp_path / "2025_민원고도화_제안서.hwpx")
    res = import_proposals([src], kb_dir, won=True)
    titles = [s.title for s in res.written]
    assert titles == ["사업 이해도", "추진 전략"] and res.skipped_short >= 1       # '3. 기타'는 짧아서 건너뜀
    text = res.written[0].path.read_text(encoding="utf-8")
    assert "예시정보" not in text and "YesiFlow" not in text and "홍○○" not in text   # 회사 식별어·실명은 가림
    assert "당사는 당사를 기반으로" in text and "PM | ○○○ 특급" in text and res.masked >= 3
    assert "tags:\n- 사업이해도\n- 전략및방법론" in text and "won: true" in text

    kb = load_kb(kb_dir)
    imported = [k for k in kb.content if k.source == "2025_민원고도화_제안서.hwpx"]
    assert len(imported) == 2 and all(k.id.startswith("K-") for k in imported)
    node = OutlineNode(id="S-3-1", number="Ⅲ.1", title="사업 이해도", level=2)
    assert any(k.title == "사업 이해도" and k.source.startswith("2025") for k in relevant_content(kb, node))

    again = import_proposals([src], kb_dir)                       # 같은 파일을 다시 넣으면 덮어쓰지 않는다
    assert not again.written and len(again.skipped_existing) == 2
    assert len(import_proposals([src], kb_dir, force=True).written) == 2


def test_kb_import_cli(tmp_path):
    kb_dir = tmp_path / "kb"
    init_kb(kb_dir)
    src = _past_proposal(tmp_path / "old.hwpx")
    r = CliRunner().invoke(app, ["kb", "import", str(src), "--kb", str(kb_dir), "--lost"])
    assert r.exit_code == 0, r.output
    assert "재사용 문단 2개" in r.output and "'당사'·'○○○'로 바꿈" in r.output
    r = CliRunner().invoke(app, ["kb", "import", str(src), "--kb", str(tmp_path / "없는폴더")])
    assert r.exit_code == 1
