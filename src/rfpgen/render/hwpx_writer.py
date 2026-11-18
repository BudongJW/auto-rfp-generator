"""기술제안서 본문 HWPX 렌더(설계서 7.9절, 10.2절).

python-hwpx(Apache-2.0)의 서식 ID 보장(ensure_run·ensure_paragraph_format), 머리말·쪽 번호 API를 쓴다.
다음은 hwpx-docs(AGPL-3.0) 분석(docs/analysis/hwpx-rendering-tools.md 2.10·2.12절)의 측정 규칙을 따라 재구현했다.
- 제목 번호(Ⅰ. 1.)와 개조식 기호(□ ○ - ·, ※)는 자동 번호가 아니라 글자로 넣는다(추적표 번호와 항상 같게).
- 내어쓰기: 첫 줄은 left, 둘째 줄부터 left + |내어쓰기|에서 시작한다(한글 규칙). 기호 폭만큼 내어쓴다.
- 글꼴은 모든 언어(기호 포함)에 지정한다. 하나라도 빠지면 □○※ 모양이 바뀐다.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from ..schemas.draft import DraftBlock, SectionDraft
from ..schemas.plan import Outline, OutlineNode

PT = 100            # 1pt = 100 HWPUNIT
FIG_MAX_H_MM = 220  # 그림 한 장의 최대 높이(캡션·제목 자리를 남긴다)
MM = 283.465        # 1mm ≈ 283.465 HWPUNIT


def load_style(override: Path | None = None) -> dict[str, Any]:
    base = yaml.safe_load(resources.files("rfpgen.config.styles").joinpath("report.yaml").read_text(encoding="utf-8"))
    if override is not None:
        extra = yaml.safe_load(Path(override).read_text(encoding="utf-8")) or {}
        base = _deep_merge(base, extra)
    return base


def _deep_merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        out[k] = _deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


@dataclass
class _Ids:
    char: dict[str, str]
    para: dict[str, str]


class ProposalWriter:
    def __init__(self, style: dict[str, Any], *, min_body_pt: float | None = None, min_table_pt: float | None = None) -> None:
        from hwpx import HwpxDocument

        self.style = style
        self.doc = HwpxDocument.new(inherit_style=False)
        fonts = style["fonts"][style.get("render_path", "server")]
        size = dict(style["size"])
        if min_body_pt:
            for k in ("body", "note", "message"):
                size[k] = max(float(size[k]), float(min_body_pt))
        if min_table_pt:
            size["table"] = max(float(size["table"]), float(min_table_pt))
        self.size = size
        self.fonts = fonts
        self.ids = self._ensure_styles()
        self._first = True
        m = style["page"]["margin_mm"]
        page_w = 210 if style["page"].get("orientation", "portrait") == "portrait" else 297
        self.text_width = int((page_w - m["left"] - m["right"]) * MM)  # 표·상자를 본문 폭에 맞춘다

    # ---- 서식 ---------------------------------------------------------------------------
    def _run(self, role: str, font: str, *, bold: bool = False) -> str:
        return self.doc.styles.ensure_run(font=font, size=float(self.size[role]), bold=bold)

    def _para(self, *, align: str = "JUSTIFY", spacing: int, left_pt: float = 0, hang_pt: float = 0,
              before_pt: float = 0, after_pt: float = 0, keep_next: bool = False) -> str:
        margins = {"left": int(round(left_pt * PT)), "intent": -int(round(hang_pt * PT)),
                   "prev": int(round(before_pt * PT)), "next": int(round(after_pt * PT))}
        return self.doc.styles.ensure_paragraph_format(
            alignment=align, line_spacing_percent=spacing, margins=margins,
            break_setting={"keep_with_next": keep_next} if keep_next else None)

    def _ensure_styles(self) -> _Ids:
        f, sp = self.fonts, self.style["line_spacing_pct"]
        char = {
            "title": self._run("title", f["heading"], bold=True),
            "chapter": self._run("chapter", f["heading"], bold=True),
            "section": self._run("section", f["heading"], bold=True),
            "message": self._run("message", f["heading"], bold=True),
            "body": self._run("body", f["body"]),
            "note": self._run("note", f["body"]),
            "table": self._run("table", f["table"]),
            "table_head": self._run("table", f["table"], bold=True),
            "caption": self._run("table", f["table"], bold=True),
        }
        self.figure_no = 0
        para = {
            "title": self._para(align="CENTER", spacing=sp["body"], before_pt=120, after_pt=24),
            "subtitle": self._para(align="CENTER", spacing=sp["body"], after_pt=12),
            "chapter": self._para(align="LEFT", spacing=sp["body"], before_pt=18, after_pt=10, keep_next=True),
            "section": self._para(align="LEFT", spacing=sp["body"], before_pt=12, after_pt=6, keep_next=True),
            "body": self._para(spacing=sp["body"], after_pt=3),
            "table": self._para(align="LEFT", spacing=sp["table"]),
            "table_center": self._para(align="CENTER", spacing=sp["table"]),
            "figure": self._para(align="CENTER", spacing=100, before_pt=6, keep_next=True),
            "caption": self._para(align="CENTER", spacing=sp["table"], before_pt=2, after_pt=8),
        }
        for i, lv in enumerate(self.style["bullets"]):
            hang = float(self.size["body"]) * 1.25
            para[f"bullet{i}"] = self._para(spacing=sp["body"], left_pt=float(lv["left"]), hang_pt=hang, after_pt=2)
        note = self.style["note"]
        para["note"] = self._para(spacing=sp["body"], left_pt=float(note["left"]), hang_pt=float(self.size["note"]) * 1.25,
                                  after_pt=2)
        return _Ids(char=char, para=para)

    # ---- 쓰기 ---------------------------------------------------------------------------
    def para(self, text: str, role: str, char: str | None = None, *, page_break: bool = False):
        extra = {"pageBreak": "1"} if page_break else {}
        if self._first:
            # 새 문서의 첫(빈) 문단을 다시 쓴다: 쪽 설정(secPr)이 그 문단에 있다
            p = self.doc.paragraphs[0]
            p.text = text
            p.para_pr_id_ref = self.ids.para[role]
            p.char_pr_id_ref = self.ids.char[char or role]
            self._first = False
            return p
        return self.doc.add_paragraph(text, para_pr_id_ref=self.ids.para[role],
                                      char_pr_id_ref=self.ids.char[char or role], **extra)

    def table(self, header: list[str], rows: list[list[str]], *, widths: list[float] | None = None,
              fill: str | None = None) -> None:
        n_rows, n_cols = len(rows) + (1 if header else 0), max(len(header), max((len(r) for r in rows), default=0))
        if n_cols == 0:
            return
        t = self.doc.add_table(n_rows, n_cols, width=self.text_width)
        all_rows = ([header] if header else []) + rows
        for r, row in enumerate(all_rows):
            for c in range(n_cols):
                cell = t.cell(r, c)
                text = row[c] if c < len(row) else ""
                is_head = bool(header) and r == 0
                lines = text.split("\n") if text else [""]
                cell.text = lines[0]
                paras = cell.paragraphs
                paras[0].para_pr_id_ref = self.ids.para["table_center" if is_head else "table"]
                paras[0].char_pr_id_ref = self.ids.char["table_head" if is_head else "table"]
                for extra_line in lines[1:]:
                    cell.add_paragraph(extra_line, para_pr_id_ref=self.ids.para["table"], char_pr_id_ref=self.ids.char["table"])
                if is_head:
                    t.set_cell_shading(r, c, self.style["colors"]["table_header_fill"])
                elif fill:
                    t.set_cell_shading(r, c, fill)
        if widths:
            t.set_column_widths(widths)

    def message_box(self, text: str) -> None:
        """거버닝 메시지 상자(1×1 표, 음영)."""
        t = self.doc.add_table(1, 1, width=self.text_width)
        cell = t.cell(0, 0)
        cell.text = text
        cell.paragraphs[0].para_pr_id_ref = self.ids.para["table"]
        cell.paragraphs[0].char_pr_id_ref = self.ids.char["message"]
        t.set_cell_shading(0, 0, self.style["colors"]["message_fill"])

    def figure(self, b: DraftBlock, result=None) -> None:
        """도식 그림(PNG)과 캡션. 그림이 없으면 같은 자리에 자리표시 상자를 넣는다."""
        spec = b.figure
        if spec is None:
            return
        self.figure_no += 1
        text_w_mm = self.text_width / MM
        png = getattr(result, "png", None)
        if png is not None and Path(png).exists():
            w_mm = min(float(result.width_mm), text_w_mm)
            h_mm = float(result.height_mm) * w_mm / float(result.width_mm)
            if h_mm > FIG_MAX_H_MM:                     # 쪽보다 크면 줄인다(FIG-003)
                w_mm, h_mm = w_mm * FIG_MAX_H_MM / h_mm, FIG_MAX_H_MM
            result.scale = w_mm / float(result.width_mm)
            self.doc.add_picture(Path(png).read_bytes(), "png", width_mm=w_mm, height_mm=h_mm, align="CENTER",
                                 para_pr_id_ref=self.ids.para["figure"], char_pr_id_ref=self.ids.char["body"])
        else:
            t = self.doc.add_table(1, 1, width=self.text_width)
            cell = t.cell(0, 0)
            cell.text = f"[도식 자리: {spec.title} — 그림 변환 전. out/figures/{spec.id}.svg 참고]"
            cell.paragraphs[0].para_pr_id_ref = self.ids.para["table_center"]
            cell.paragraphs[0].char_pr_id_ref = self.ids.char["table"]
            t.set_cell_shading(0, 0, self.style["colors"]["table_header_fill"])
        self.para(f"[그림 {self.figure_no}] {spec.title}", "caption")

    def block(self, b: DraftBlock) -> None:
        bullets = self.style["bullets"]
        if b.kind == "bullets":
            lv = max(0, min(b.level, len(bullets) - 1))
            sym = bullets[lv]["symbol"]
            for item in b.items:
                self.para(f"{sym} {item}", f"bullet{lv}", "body")
        elif b.kind == "note":
            self.para(f"{self.style['note']['symbol']} {b.text}", "note")
        elif b.kind == "callout":
            self.message_box(b.text)
        elif b.kind == "table" and b.table is not None:
            self.table(b.table.header, b.table.rows)
        else:
            self.para(b.text, "body")

    def page_setup(self, header_text: str) -> None:
        m = self.style["page"]["margin_mm"]
        self.doc.page.set_margins(left=int(m["left"] * MM), right=int(m["right"] * MM), top=int(m["top"] * MM),
                                  bottom=int(m["bottom"] * MM), header=int(m["header"] * MM), footer=int(m["footer"] * MM))
        if header_text:
            self.doc.page.set_header(text=header_text)
        pn = self.style["footer_page_number"]
        self.doc.page.set_page_number(prefix=pn["prefix"], suffix=pn["suffix"])
        self.doc.page.set_visibility(hide_first_header=True, hide_first_footer=True)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save_to_path(str(path))


def _section_number(node: OutlineNode) -> str:
    """'Ⅲ.2' → '2.' (장 번호 아래 절은 아라비아 숫자)."""
    last = node.number.rsplit(".", 1)[-1]
    return f"{last}." if last and last[0].isdigit() else node.number


def render_proposal(path: Path, outline: Outline, drafts: list[SectionDraft], *, title: str, blind: bool,
                    style: dict[str, Any], min_body_pt: float | None = None, min_table_pt: float | None = None,
                    responses_table: bool = True, requirement_names: dict[str, str] | None = None,
                    figures: dict | None = None) -> dict[str, int]:
    """본문 HWPX를 쓰고 간단한 통계를 돌려준다. 회사 식별 정보는 쓰지 않는다(블라인드 여부와 무관).

    figures: 도식 id → 렌더 결과(diagram.FigureResult). 넣을 때 줄인 비율을 결과의 scale에 적는다.
    """
    w = ProposalWriter(style, min_body_pt=min_body_pt, min_table_pt=min_table_pt)
    names = requirement_names or {}
    by_id = {d.section_id: d for d in drafts}
    # 표지
    w.para(title, "title")
    w.para("기 술 제 안 서", "subtitle", "chapter")
    stats = {"sections": 0, "paragraphs": 0, "tables": 0, "figures": 0}
    first_chapter = True
    for ch in outline.chapters:
        nodes = ch.children or [ch]
        if not any(n.id in by_id for n in nodes):
            continue
        w.para(f"{ch.number} {ch.title}", "chapter", page_break=True if first_chapter else True)
        first_chapter = False
        for node in nodes:
            d = by_id.get(node.id)
            if d is None:
                continue
            stats["sections"] += 1
            if node is not ch:
                w.para(f"{_section_number(node)} {node.title}", "section")
            if d.head_message:
                w.message_box(d.head_message)
                stats["tables"] += 1
            for b in d.blocks:
                if b.kind == "figure":
                    w.figure(b, (figures or {}).get(b.figure.id) if b.figure else None)
                    stats["figures"] += 1
                    continue
                w.block(b)
                stats["tables" if b.kind in ("table", "callout") else "paragraphs"] += 1
            if responses_table and d.responses:
                w.para("요구사항 대응", "bullet0", "body")
                rows = [[r.req_id, names.get(r.req_id, ""), r.response, r.acceptance] for r in d.responses]
                w.table(["요구사항 ID", "명칭", "제안 내용", "수용 여부"], rows, widths=[14, 22, 52, 12])
                stats["tables"] += 1
    header = style.get("header", "{title}").format(title=title)
    w.page_setup(header)
    w.save(path)
    del blind  # 렌더에는 회사 식별 정보를 넣지 않으므로 블라인드 여부와 무관하다(점검은 check 단계)
    return stats
