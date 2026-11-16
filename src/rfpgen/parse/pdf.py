"""PDF 파서(pdfplumber, MIT).

쪽마다 선으로 그려진 표를 찾고, 셀 경계 좌표로 행·열 위치와 병합(span)을 복원한다.
표 밖의 줄은 간격과 글머리 기호를 기준으로 문단으로 묶는다. 텍스트 레이어가 없는
스캔 PDF는 블록이 비고 경고를 남긴다(OCR·비전 폴백은 이후 단계).
"""

from __future__ import annotations

import io
import re
from bisect import bisect_left

from ..schemas.docir import Document
from .builder import DocBuilder
from .safety import UnsafeInputError, check_size

_SNAP = 3.0  # 좌표를 같은 경계로 볼 허용 오차(pt)
_PAGE_NUMBER = re.compile(r"^[\s\-–—]*(?:\d+|[ivxIVX]+)(?:\s*/\s*\d+)?[\s\-–—]*$")
_BULLET_START = re.compile(r"^\s*(?:[□■○●◦◎◇◆▶▷►•·\-–※*]|\(?\d{1,2}[.)]|[가-하][.)]|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ][.．])")


def _snap(values: list[float]) -> list[float]:
    out: list[float] = []
    for v in sorted(values):
        if not out or v - out[-1] > _SNAP:
            out.append(v)
    return out


def _index(bounds: list[float], v: float) -> int:
    i = bisect_left(bounds, v - _SNAP)
    return min(i, max(len(bounds) - 1, 0))


def _inside(bbox, x: float, y: float) -> bool:
    x0, top, x1, bottom = bbox
    return x0 - 1 <= x <= x1 + 1 and top - 1 <= y <= bottom + 1


def _crop_text(page, x0: float, top: float, x1: float, bottom: float) -> str:
    if x1 - x0 < 1 or bottom - top < 1:
        return ""
    try:
        return page.crop((x0 + 0.5, top + 0.5, x1 - 0.5, bottom - 0.5), strict=False).extract_text() or ""
    except ValueError:
        return ""


def _table_cells(page, table):
    """표 셀 bbox들을 (row, col, rowspan, colspan, text)로 바꾼다.

    경계선 일부가 생략된 표에서는 pdfplumber가 셀을 찾지 못한 칸이 생긴다. 그런 칸은
    격자 좌표로 다시 잘라 읽어 1x1 셀로 채운다(내용 손실 방지).
    """
    boxes = [c for c in table.cells if c is not None]
    xs = _snap([c[0] for c in boxes] + [c[2] for c in boxes])
    ys = _snap([c[1] for c in boxes] + [c[3] for c in boxes])
    n_rows, n_cols = max(len(ys) - 1, 1), max(len(xs) - 1, 1)
    occupied = [[False] * n_cols for _ in range(n_rows)]
    out = []
    for x0, top, x1, bottom in sorted(boxes, key=lambda c: (round(c[1]), round(c[0]))):
        col, col_end = _index(xs, x0), _index(xs, x1)
        row, row_end = _index(ys, top), _index(ys, bottom)
        if row >= n_rows or col >= n_cols or occupied[row][col]:
            continue
        rowspan, colspan = max(row_end - row, 1), max(col_end - col, 1)
        for r in range(row, min(row + rowspan, n_rows)):
            for c in range(col, min(col + colspan, n_cols)):
                occupied[r][c] = True
        out.append((row, col, rowspan, colspan, _crop_text(page, x0, top, x1, bottom)))
    for r in range(n_rows):
        for c in range(n_cols):
            if not occupied[r][c]:
                text = _crop_text(page, xs[c], ys[r], xs[c + 1], ys[r + 1])
                if text.strip():
                    out.append((r, c, 1, 1, text))
    out.sort(key=lambda t: (t[0], t[1]))
    return out, n_rows, n_cols


def _paragraphs(lines):
    """줄을 문단으로 묶는다: 큰 간격이나 글머리 기호에서 끊는다."""
    paras: list[dict] = []
    for ln in lines:
        text = ln["text"].strip()
        if not text or _PAGE_NUMBER.match(text):
            continue
        height = max(ln["bottom"] - ln["top"], 1.0)
        if paras:
            prev = paras[-1]
            gap = ln["top"] - prev["bottom"]
            if gap <= height * 0.9 and not _BULLET_START.match(text) and len(prev["text"]) > 25:
                prev["text"] += " " + text
                prev["bottom"] = ln["bottom"]
                continue
        paras.append({"text": text, "top": ln["top"], "bottom": ln["bottom"]})
    return paras


def parse_pdf_bytes(data: bytes, doc: Document) -> Document:
    check_size(data, doc.filename)
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover
        raise UnsafeInputError("pdfplumber가 설치되지 않았습니다") from exc

    builder = DocBuilder(doc)
    empty_pages = 0
    try:
        pdf = pdfplumber.open(io.BytesIO(data))
    except Exception as exc:  # pdfminer가 던지는 다양한 예외
        raise UnsafeInputError(f"{doc.filename}: PDF를 열 수 없습니다 — {exc}") from exc
    with pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            tables = [t for t in page.find_tables() if len([c for c in t.cells if c]) >= 2]
            bboxes = [t.bbox for t in tables]
            lines = page.extract_text_lines(layout=False, strip=True, return_chars=False)
            if not lines and not tables:
                empty_pages += 1
                continue
            outside = [
                ln for ln in lines
                if not any(_inside(b, (ln["x0"] + ln["x1"]) / 2, (ln["top"] + ln["bottom"]) / 2) for b in bboxes)
            ]
            items: list[tuple[float, str, object]] = [(p["top"], "para", p) for p in _paragraphs(outside)]
            items += [(t.bbox[1], "table", t) for t in tables]
            for _, kind, obj in sorted(items, key=lambda it: it[0]):
                if kind == "para":
                    builder.text(obj["text"], page=page_no)  # type: ignore[index]
                else:
                    cells, rows, cols = _table_cells(page, obj)
                    table = builder.table(rows, cols, page=page_no)
                    made = [builder.cell(table, text, r, c, rs, cs, page=page_no) for r, c, rs, cs, text in cells]
                    builder.finish_table(table, made)
    if empty_pages:
        doc.warnings.append(f"텍스트 레이어가 없는 쪽 {empty_pages}개 — 스캔 문서일 수 있습니다(OCR 필요)")
    return doc
