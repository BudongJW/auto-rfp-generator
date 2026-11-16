"""제안서 작성지침 추출(분량·용지·글자 크기·제출 형식·용량·블라인드·발표·지정 목차·별지).

RFP의 '제안서 작성요령' 문장에서 값을 뽑고, 각 값에 원문 위치를 붙인다. 분량 문구는 있는데
숫자를 읽지 못한 경우(숫자가 이미지·도형 글자인 PDF)는 따로 보고해 사람이 G1에서 입력하게 한다.
"""

from __future__ import annotations

import re

from ..schemas.common import Extracted
from ..schemas.docir import Block, Document
from ..schemas.rfp import ExtractionReport, Presentation, RequiredDoc, TocNode, WritingGuideline
from .common import Grid, build_grids, iter_lines, loc, norm

_PAGE = re.compile(
    r"(\d{1,3})\s*(?:쪽|페이지|매|장|page|p)\s*(?:\([^)]{0,20}\))?\s*(?:이내|이하|내외|까지|를\s*초과|을\s*초과|미만)",
    re.I,
)
_PAGE_NO_NUMBER = re.compile(r"(?<!\d)\s(?:쪽|페이지|매)\s*(?:\([^)]{0,20}\))?\s*(?:이내|이하|내외)")
_FONT = re.compile(r"(\d{1,2}(?:\.\d)?)\s*(?:pt|포인트|point|p\b)", re.I)
_FONT_SIZE_WORD = re.compile(r"글자\s*(?:크기|포인트)[^0-9]{0,8}(\d{1,2}(?:\.\d)?)")
_SIZE = re.compile(r"(\d{2,4})\s*MB", re.I)
_PAPER = re.compile(r"(?<![A-Za-z0-9])(A4|A3)(?![0-9])", re.I)
_BLIND = re.compile(
    r"블라인드|업체\s*정보\s*삭제|(?:업체|회사|제안사)\s*(?:명|로고|CI)[^.]{0,30}(?:표기|기재|노출|표시)[^.]{0,15}(?:금지|불가|않|없)"
)
_PRESENT_MIN = re.compile(r"발표\s*(?:시간)?\s*(?:은|는|:)?\s*(\d{1,2})\s*분")
_QA_MIN = re.compile(r"질의\s*(?:및)?\s*응답\s*(?:시간)?\s*(?:은|는|:)?\s*(\d{1,2})\s*분")
_PM_PRESENT = re.compile(r"(?:사업\s*수행\s*책임자|사업책임자|총괄\s*책임자|\bPM\b)[^.]{0,25}(?:직접\s*)?발표")
_EDITOR = re.compile(r"(아래\s*한글|한글\s*(?:프로그램|파일|문서|\(HWP\))|\bHWP\b|MS\s*-?\s*Word|워드|파워포인트|PowerPoint|\bPPT\b)", re.I)
_FORM = re.compile(r"별지\s*(?:제\s*)?(\d{1,2})\s*호")
_EXCL = ("표지", "목차", "간지", "증빙자료", "증빙서류", "붙임자료", "붙임", "별첨", "부록")
# 작성지침 문장으로 볼 문맥(요구사항 세부내용 속 'pdf', '10페이지' 같은 잡음을 거른다)
_GUIDE_CONTEXT = re.compile(r"제안|분량|작성|편집|제출|발표|요약본|평가|글자|글씨|폰트|용지|블라인드")
_TOC_TITLE = re.compile(r"제안서\s*(?:작성\s*)?목차|목차\s*(?:구성|가이드|및\s*작성)")
_ROMAN_HEAD = re.compile(r"^\s*([ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]|(?=[IVX])X{0,3}(?:IX|IV|V?I{0,3}))\s*[.．]\s*(.+)$")
_NUM_HEAD = re.compile(r"^\s*(\d{1,2})\s*[.．)]\s*(.+)$")


def _context(line: str) -> str:
    t = norm(line)
    if "요약" in t:
        return "summary"
    if any(k in t for k in ("발표", "설명회", "PT", "프레젠테이션")):
        return "presentation"
    return "main"


def _first(cands: list[tuple[object, Block, str]], doc: Document) -> Extracted | None:
    if not cands:
        return None
    value, block, quote = cands[0]
    return Extracted(value=value, locators=[loc(doc, block, quote)])


def extract_guideline(docs: list[Document], report: ExtractionReport,
                      skip_tables: set[str] | None = None) -> WritingGuideline:
    """skip_tables: 요구사항 정의서처럼 작성지침이 아닌 표(그 셀의 문장은 읽지 않는다)."""
    g = WritingGuideline()
    skip = skip_tables or set()
    pages: dict[str, list[tuple[int, Block, str, Document]]] = {"main": [], "summary": [], "presentation": []}
    fonts_body: list[tuple[float, Block, str, Document]] = []
    fonts_table: list[tuple[float, Block, str, Document]] = []
    missing_page_numbers: list[tuple[Block, str, Document]] = []

    for doc in docs:
        for block, line in iter_lines(doc):
            if block.kind == "cell" and block.parent in skip:
                continue
            if not _GUIDE_CONTEXT.search(line):
                continue
            for m in _PAGE.finditer(line):
                n = int(m.group(1))
                if 1 <= n <= 1000:
                    pages[_context(line)].append((n, block, m.group(0), doc))
            if not _PAGE.search(line) and _PAGE_NO_NUMBER.search(line) and ("제안서" in line or "작성" in line):
                missing_page_numbers.append((block, line, doc))

            if g.count_exclusions is None and "제외" in line:
                found = [w for w in _EXCL if w in line]
                found = [w for w in found if not any(w != o and w in o for o in found)]
                if found and ("쪽" in line or "페이지" in line or "분량" in line or "매" in line):
                    g.count_exclusions = Extracted(value=found, locators=[loc(doc, block, line)])

            if any(k in line for k in ("글자", "글씨", "폰트", "크기", "포인트", "pt", "본문")):
                # '본문 13pt, 표 안 12pt'처럼 한 문장에 둘이 있으면 쉼표 단위로 나눠 판단한다
                for clause in re.split(r"[,，;]|\s및\s", line):
                    is_table = bool(re.search(r"표\s*(?:안|내|속|내부)|표의|도표", clause))
                    for m in list(_FONT.finditer(clause)) + list(_FONT_SIZE_WORD.finditer(clause)):
                        size = float(m.group(1))
                        if 6 <= size <= 30:
                            (fonts_table if is_table else fonts_body).append((size, block, m.group(0), doc))

            if (g.paper is None and _context(line) == "main" and (m := _PAPER.search(line))
                    and any(k in line for k in ("용지", "규격", "크기", "작성"))):
                g.paper = Extracted(value=m.group(1).upper(), locators=[loc(doc, block, m.group(0))])

            if (g.orientation is None and _context(line) == "main" and "제안서" in line and "작성" in line
                    and not any(k in line for k in ("별첨", "별권", "별도", "붙임"))
                    and any(k in line for k in ("방향", "용지", "편집", "형태"))):
                if "가로" in line and "세로" not in line:
                    g.orientation = Extracted(value="landscape", locators=[loc(doc, block, "가로")])
                elif "세로" in line and "가로" not in line:
                    g.orientation = Extracted(value="portrait", locators=[loc(doc, block, "세로")])

            if (g.file_format is None and re.search(r"\bpdf\b", line, re.I) and "제안" in line
                    and any(k in line for k in ("제출", "작성", "전자"))):
                g.file_format = Extracted(value="PDF", locators=[loc(doc, block, line)])

            if g.total_size_limit_mb is None and (m := _SIZE.search(line)) and "용량" in line:
                g.total_size_limit_mb = Extracted(value=int(m.group(1)), locators=[loc(doc, block, m.group(0))])

            if g.blind is None and (m := _BLIND.search(line)):
                g.blind = Extracted(value=True, locators=[loc(doc, block, m.group(0))])

            if g.editor is None and (m := _EDITOR.search(line)) and any(k in line for k in ("작성", "편집", "프로그램", "제출")):
                g.editor = Extracted(value=m.group(1), locators=[loc(doc, block, m.group(0))])

            pm = _PRESENT_MIN.search(line)
            qm = _QA_MIN.search(line)
            pmp = _PM_PRESENT.search(line)
            if pm or qm or pmp:
                cur = g.presentation.value if g.presentation else Presentation()
                locs = g.presentation.locators if g.presentation else []
                if pm and cur.minutes is None:
                    cur.minutes = int(pm.group(1))
                    locs.append(loc(doc, block, pm.group(0)))
                if qm and cur.qa_minutes is None:
                    cur.qa_minutes = int(qm.group(1))
                    locs.append(loc(doc, block, qm.group(0)))
                if pmp and cur.pm_must_present is None:
                    cur.pm_must_present = True
                    locs.append(loc(doc, block, pmp.group(0)))
                g.presentation = Extracted(value=cur, locators=locs)

    for key, attr in (("main", "main_page_limit"), ("summary", "summary_page_limit"),
                      ("presentation", "presentation_page_limit")):
        if pages[key]:
            n, block, quote, doc = pages[key][0]
            setattr(g, attr, Extracted(value=n, locators=[loc(doc, block, quote)]))
            others = sorted({c[0] for c in pages[key]} - {n})
            if others:
                report.add("GUIDE-PAGE-MULTI", "info",
                           f"{key} 분량 후보가 여러 개입니다({n}쪽 채택, 그 밖에 {others}) — 확인 필요",
                           [loc(c[3], c[1], c[2]) for c in pages[key][:3]])
    if fonts_body:
        size, block, quote, doc = min(fonts_body, key=lambda c: c[0])
        g.min_font_pt = Extracted(value=size, locators=[loc(doc, block, quote)])
    if fonts_table:
        size, block, quote, doc = min(fonts_table, key=lambda c: c[0])
        g.table_min_font_pt = Extracted(value=size, locators=[loc(doc, block, quote)])

    if g.main_page_limit is None:
        if missing_page_numbers:
            block, line, doc = missing_page_numbers[0]
            report.add("GUIDE-PAGE-UNREADABLE", "error",
                       "분량 제한 문구는 있지만 숫자를 읽지 못했습니다(이미지·도형 글자 가능성) — 원문을 보고 직접 입력하세요",
                       [loc(doc, block, line)])
        else:
            report.add("GUIDE-PAGE-MISSING", "warning", "본문 분량 제한을 찾지 못했습니다 — 프로필 기본값을 씁니다")
    if g.blind is None:
        g.blind = Extracted(value=False, confidence=0.5, note="블라인드 관련 문구 없음")
    if g.paper is None:
        report.add("GUIDE-PAPER-MISSING", "info", "용지 규격(A4 등)을 찾지 못했습니다")

    g.prescribed_toc = _prescribed_toc(docs, report)
    g.required_documents = _required_docs(docs)
    return g


def _toc_from_table(grid: Grid) -> list[TocNode]:
    chapters: list[TocNode] = []
    for r in range(grid.n_rows):
        row = grid.row_cells(r)
        if not row:
            continue
        head = row[0].text.replace("\n", " ").strip()
        m = _ROMAN_HEAD.match(head)
        if not m:
            continue
        chapter = TocNode(number=m.group(1), title=m.group(2).strip(), level=1)
        # 같은 행의 나머지 칸에서 '1. …' 형식 하위 목차를 찾는다(비고·서식 열은 무시).
        for cell in row[1:]:
            subs = []
            for line in cell.text.split("\n"):
                sm = _NUM_HEAD.match(line.strip())
                if sm:
                    subs.append(TocNode(number=sm.group(1), title=sm.group(2).strip(), level=2))
            if subs:
                chapter.children = subs
                break
        # 같은 장이 여러 행에 걸치면(세로 병합) 다음 행들의 하위 목차도 붙인다.
        if chapters and norm(chapters[-1].title) == norm(chapter.title):
            chapters[-1].children.extend(chapter.children)
        else:
            chapters.append(chapter)
    return chapters


def _toc_from_lines(blocks: list[Block]) -> list[TocNode]:
    chapters: list[TocNode] = []
    for b in blocks:
        for line in b.text.split("\n"):
            line = line.strip()
            m = _ROMAN_HEAD.match(line)
            if m:
                chapters.append(TocNode(number=m.group(1), title=m.group(2).strip(), level=1))
                continue
            sm = _NUM_HEAD.match(line)
            if sm and chapters:
                chapters[-1].children.append(TocNode(number=sm.group(1), title=sm.group(2).strip(), level=2))
    return chapters


def _prescribed_toc(docs: list[Document], report: ExtractionReport) -> Extracted[list[TocNode]] | None:
    for doc in docs:
        grids = {g.table.id: g for g in build_grids(doc)}
        blocks = doc.blocks
        for i, b in enumerate(blocks):
            if b.kind not in ("heading", "para") or not _TOC_TITLE.search(b.text) or len(b.text) > 40:
                continue
            # 제목 다음 몇 블록 안의 표 또는 문단 목록
            following = [x for x in blocks[i + 1:i + 40] if x.parent is None and x.kind != "cell"]
            for x in following[:6]:
                if x.kind == "table" and x.id in grids:
                    toc = _toc_from_table(grids[x.id])
                    if len(toc) >= 3:
                        return Extracted(value=toc, locators=[loc(doc, b), loc(doc, x, "")],
                                         note="표 형식 지정 목차")
            paras = []
            for x in following:
                if x.kind == "heading" and x.level == 1 and paras:
                    break
                if x.kind in ("para", "heading"):
                    paras.append(x)
            toc = _toc_from_lines(paras)
            if len(toc) >= 3:
                return Extracted(value=toc, locators=[loc(doc, b)], note="문단 형식 지정 목차")
    report.add("GUIDE-TOC-NONE", "info", "RFP가 지정한 제안서 목차를 찾지 못했습니다 — 평가표 기반 목차를 씁니다")
    return None


def _required_docs(docs: list[Document]) -> list[RequiredDoc]:
    out: dict[str, RequiredDoc] = {}
    for doc in docs:
        grids = build_grids(doc)
        cell_row: dict[str, tuple[Grid, int]] = {}
        for g in grids:
            for c in g.cells:
                if c.cell is not None:
                    cell_row[c.id] = (g, c.cell.row)
        for b in doc.blocks:
            if b.kind not in ("cell", "para", "heading"):
                continue
            for m in _FORM.finditer(b.text):
                no = m.group(1)
                if no in out:
                    continue
                name = ""
                if b.kind == "cell" and b.id in cell_row:
                    g, r = cell_row[b.id]
                    texts = [c.text.replace("\n", " ").strip() for c in g.row_cells(r)
                             if c is not b and not _FORM.search(c.text) and c.text.strip()]
                    name = texts[-1] if texts else ""
                    if len(texts) >= 2 and len(texts[-2]) <= 15:
                        name = f"{texts[-2]} — {texts[-1]}"
                else:
                    after = b.text[m.end():].strip(" )]」』:：-")
                    name = re.split(r"[,.\n]", after)[0][:40] if after else b.text[:40]
                out[no] = RequiredDoc(name=name[:80] or f"별지 제{no}호", form_no=f"별지 제{no}호",
                                      locators=[loc(doc, b, m.group(0))])
    return sorted(out.values(), key=lambda d: int(re.sub(r"\D", "", d.form_no or "0") or 0))
