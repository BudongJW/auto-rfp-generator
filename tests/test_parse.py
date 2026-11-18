from __future__ import annotations

import io
import zipfile

import pytest

from rfpgen.extract.common import build_grids
from rfpgen.parse import InputFile, UnsafeInputError, collect_inputs, detect_format, parse_document
from rfpgen.parse.builder import guess_heading
from rfpgen.parse.safety import parse_xml


def _cells(doc):
    return {(b.cell.row, b.cell.col): b for b in doc.blocks if b.kind == "cell"}


def test_hwpx_preserves_text_order_and_merges(hwpx_file):
    files, skipped = collect_inputs([hwpx_file])
    assert not skipped
    doc = parse_document(files[0], "d01")
    assert doc.format == "hwpx"
    assert doc.role == "제안요청서"  # 파일명으로 분류
    texts = [b.text for b in doc.blocks if b.kind in ("para", "heading")]
    assert "Ⅳ. 제안 요청 내용" in texts
    grids = build_grids(doc)
    summary = next(g for g in grids if "요구사항 명칭" in g.all_text() and g.n_cols == 3 and "SFR-002" in g.all_text())
    merged = summary.cell(1, 0)
    assert merged is not None and merged.cell.rowspan == 2
    assert summary.cell(2, 0) is merged  # 병합으로 덮인 칸은 같은 셀을 가리킨다
    assert summary.text(2, 1) == "SFR-002"


def test_heading_guess():
    assert guess_heading("Ⅲ. 기술 및 기능")[0] == 1
    assert guess_heading("2. 추진 전략")[0] == 2
    assert guess_heading("가. 정량적 평가")[0] == 3
    assert guess_heading("1. 본 사업은 민원 시스템을 고도화하는 사업이다.")[0] is None
    assert guess_heading("본문 문단입니다.", style="개요 1")[0] is None


def test_pdf_tables_with_spans(pdf_file):
    files, _ = collect_inputs([pdf_file])
    doc = parse_document(files[0], "d01")
    assert doc.format == "pdf"
    assert any("100쪽 이내" in b.text for b in doc.blocks if b.kind == "para")
    grid = next(g for g in build_grids(doc) if "배점한도" in g.all_text())
    assert grid.n_cols == 4
    area = grid.cell(2, 0)
    assert area is not None and "전략" in area.text and area.cell.rowspan == 3
    assert grid.text(3, 1) == "추진 전략"


def test_docx_vertical_merge(docx_file):
    files, _ = collect_inputs([docx_file])
    doc = parse_document(files[0], "d01")
    cells = _cells(doc)
    assert cells[(1, 0)].cell.rowspan == 2
    assert (2, 0) not in cells
    assert cells[(2, 1)].text == "SFR-002"


class _Cp949Info(zipfile.ZipInfo):
    """UTF-8 플래그 없이 CP949 바이트로 파일명을 쓰는 ZIP 항목(한국어 윈도우 압축 프로그램 재현)."""

    def _encodeFilenameFlags(self):  # noqa: N802 - zipfile 내부 메서드 이름
        return self.filename.encode("cp437"), self.flag_bits & ~0x800


def test_zip_bundle_with_cp949_names(hwpx_file, tmp_path):
    data = hwpx_file.read_bytes()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = _Cp949Info("제안요청서.hwpx".encode("cp949").decode("cp437"))
        zf.writestr(info, data)
        zf.writestr("readme.txt", b"hello")
    bundle = tmp_path / "attachments.zip"
    bundle.write_bytes(buf.getvalue())
    files, skipped = collect_inputs([bundle])
    assert [f.name for f in files] == ["제안요청서.hwpx"]
    assert skipped == ["attachments.zip/readme.txt"]


def test_zip_bomb_is_rejected(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("big.hwpx", b"\0" * (5 * 1024 * 1024))
    bundle = tmp_path / "bomb.zip"
    bundle.write_bytes(buf.getvalue())
    with pytest.raises(UnsafeInputError):
        collect_inputs([bundle])


def test_xml_entities_are_not_expanded():
    xml = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><r>&x;</r>'
    root = parse_xml(xml)
    assert "root:" not in "".join(root.itertext())


def test_unsupported_format():
    assert detect_format("a.txt", b"hello") is None
    with pytest.raises(UnsafeInputError):
        parse_document(InputFile("a.txt", b"hello"), "d01")
