"""요약본·발표자료 PPTX(설계서 7.7절, 7.9절, 10.3절) — python-pptx(MIT).

장표 슬롯: breadcrumb · 평가항목 태그 · 요구사항 ID 칩 · 거버닝 메시지 · 본문 · (우측 표/핵심 상자) · 하단 요약 · 쪽 번호.
슬롯 위치는 공식 표준이 없으므로 이 생성기의 자체 규칙이다(설계서 10.3절). 대본은 각 장의 발표자 노트에 넣는다.
회사 로고·이름은 넣지 않는다(블라인드 여부와 무관; 조직 템플릿 온보딩은 이후 단계).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Mm, Pt

from ..draft.tokens import PLACEHOLDER
from ..schemas.draft import SectionDraft, Storyboard
from ..schemas.plan import Outline, OutlineNode
from ..schemas.rfp import Rfp


@dataclass
class SlideSpec:
    breadcrumb: str = ""
    eval_tag: str = ""
    req_ids: list[str] = field(default_factory=list)
    head: str = ""
    bullets: list[tuple[int, str]] = field(default_factory=list)       # (단계, 글)
    table: tuple[list[str], list[list[str]]] | None = None
    side_title: str = ""
    side_points: list[str] = field(default_factory=list)
    summary: str = ""
    notes: str = ""
    kind: str = "content"                                              # cover | agenda | content
    image: str = ""                                                    # 도식 PNG(있으면 본문 오른쪽에 넣는다)
    image_title: str = ""


# ---- 내용 구성 ------------------------------------------------------------------------------


def _bullets_of(d: SectionDraft) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for b in d.blocks:
        if b.kind == "bullets":
            out += [(min(b.level, 2), i) for i in b.items]
        elif b.kind in ("para", "callout") and b.text:
            out.append((0, b.text))
    return out


def _clean(text: str) -> str:
    return PLACEHOLDER.sub("[확인 필요]", text).strip()


def _eval_tag(rfp: Rfp, node: OutlineNode) -> str:
    items = {it.id: it for it in rfp.evaluation.items()}
    names = [f"{items[i].name}({items[i].points:g}점)" if items[i].points is not None else items[i].name
             for i in node.eval_items if i in items]
    return "평가: " + ", ".join(names[:2]) if names else ""


def _figure(drafts: list[SectionDraft], figure_dir: Path | None) -> tuple[str, str]:
    """절들의 첫 도식 PNG(경로, 제목). 렌더되지 않았으면 빈 값."""
    if figure_dir is None:
        return "", ""
    for d in drafts:
        for b in d.blocks:
            if b.kind == "figure" and b.figure is not None:
                png = Path(figure_dir) / f"{b.figure.id}.png"
                if png.exists():
                    return str(png), b.figure.title
    return "", ""


def section_slide(rfp: Rfp, outline: Outline, node: OutlineNode, d: SectionDraft, plan,
                  figure_dir: Path | None = None) -> SlideSpec:
    chapter = next((c for c in outline.chapters if c is node or node in c.children), None)
    crumb = f"{chapter.number} {chapter.title}" + (f" > {node.title}" if chapter is not None and chapter is not node else "") \
        if chapter is not None else node.title
    s = SlideSpec(breadcrumb=crumb, eval_tag=_eval_tag(rfp, node), req_ids=list(node.requirements),
                  head=_clean(d.head_message), bullets=[(lv, _clean(t)) for lv, t in _bullets_of(d)])
    table = next((b.table for b in d.blocks if b.kind == "table" and b.table), None)
    if table is not None:
        s.table = (table.header, table.rows[:6])
    elif plan is not None and plan.key_points:
        s.side_title, s.side_points = "핵심 내용", [_clean(k) for k in plan.key_points[:5]]
    elif d.responses:
        s.side_title = "요구사항 대응"
        s.side_points = [f"{r.req_id} {_clean(r.response)}" for r in d.responses[:5]]
    first = next((r for r in d.responses if not PLACEHOLDER.search(r.response)), None)
    s.summary = _clean(first.response) if first else (s.side_points[0] if s.side_points else "")
    s.notes = " ".join(x for x in [s.head, *[t for lv, t in s.bullets if lv == 0][:4]] if x)
    s.image, s.image_title = _figure([d], figure_dir)
    return s


def chapter_slide(rfp: Rfp, chapter: OutlineNode, drafts: dict[str, SectionDraft],
                  figure_dir: Path | None = None) -> SlideSpec:
    nodes = chapter.children or [chapter]
    s = SlideSpec(breadcrumb=f"{chapter.number} {chapter.title}",
                  req_ids=[r for n in nodes for r in n.requirements])
    items = {it.id: it for it in rfp.evaluation.items()}
    tags = [items[i].name for n in nodes for i in n.eval_items if i in items]
    s.eval_tag = "평가: " + ", ".join(dict.fromkeys(tags)) if tags else ""
    heads = [(n, drafts[n.id]) for n in nodes if n.id in drafts]
    s.head = _clean(heads[0][1].head_message) if heads else chapter.title
    for n, d in heads:
        s.bullets.append((0, n.title))
        if d.head_message:
            s.bullets.append((1, _clean(d.head_message)))
    s.notes = " ".join(_clean(d.head_message) for _, d in heads if d.head_message)
    s.image, s.image_title = _figure([d for _, d in heads], figure_dir)
    return s


def build_specs(rfp: Rfp, outline: Outline, drafts: list[SectionDraft], storyboard: Storyboard | None, *,
                title: str, mode: str, max_slides: int | None, figure_dir: Path | None = None) -> list[SlideSpec]:
    by_id = {d.section_id: d for d in drafts}
    specs = [SlideSpec(kind="cover", head=title, notes=f"{title} 제안 발표를 시작하겠습니다.")]
    chapters = [c for c in outline.chapters if any(n.id in by_id for n in (c.children or [c]))]
    specs.append(SlideSpec(kind="agenda", head="목차", bullets=[(0, f"{c.number} {c.title}") for c in chapters],
                           notes="발표 순서입니다."))
    if mode == "presentation" and storyboard and storyboard.win_themes:
        specs.append(SlideSpec(breadcrumb="제안 핵심", head="제안의 핵심", bullets=[(0, _clean(w)) for w in storyboard.win_themes],
                               notes=" ".join(_clean(w) for w in storyboard.win_themes)))
    plans = {p.section_id: p for p in storyboard.sections} if storyboard else {}
    leaves = [n for c in chapters for n in (c.children or [c]) if n.id in by_id]
    budget = (max_slides or 10**6) - len(specs)
    if mode == "summary" and len(leaves) <= budget:
        specs += [section_slide(rfp, outline, n, by_id[n.id], plans.get(n.id), figure_dir) for n in leaves]
    else:
        specs += [chapter_slide(rfp, c, by_id, figure_dir) for c in chapters][:max(budget, 0)]
    return specs


# ---- 그리기 -------------------------------------------------------------------------------------


class DeckWriter:
    def __init__(self, style: dict[str, Any], mode: str) -> None:
        self.cfg = style["slides"]
        self.mode = self.cfg[mode]
        self.font = self.cfg["font"]
        self.pal = self.cfg["palette"]
        self.prs = Presentation()
        w, h = self.mode["size_mm"]
        self.w, self.h = float(w), float(h)
        self.prs.slide_width, self.prs.slide_height = Mm(self.w), Mm(self.h)
        cp = self.prs.core_properties
        cp.author = cp.last_modified_by = cp.comments = cp.keywords = cp.category = ""
        self.scale = self.h / 210.0
        self.page = 0

    def _font(self, run, size: float, *, bold: bool = False, color: str | None = None) -> None:
        f = run.font
        f.size, f.bold, f.name = Pt(size), bold, self.font
        if color:
            f.color.rgb = RGBColor.from_string(color)
        rpr = run._r.get_or_add_rPr()
        for tag in ("a:ea", "a:cs"):  # 한글(동아시아)·기타 글꼴도 지정해야 글꼴이 바뀌지 않는다
            el = rpr.find(qn(tag))
            if el is None:
                el = rpr.makeelement(qn(tag), {})
                rpr.append(el)
            el.set("typeface", self.font)

    def _text(self, slide, x, y, w, h, lines: list[tuple[str, float, bool, str | None]], *,
              align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
        s = self.scale
        box = slide.shapes.add_textbox(Mm(x * s), Mm(y * s), Mm(w * s), Mm(h * s))
        tf = box.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = anchor
        tf.margin_left = tf.margin_right = Mm(1)
        for i, (text, size, bold, color) in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            run = p.add_run()
            run.text = text
            self._font(run, size, bold=bold, color=color)
        return box

    def _rect(self, slide, x, y, w, h, fill: str, *, line: str | None = None, rounded: bool = False):
        s = self.scale
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
                                       Mm(x * s), Mm(y * s), Mm(w * s), Mm(h * s))
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor.from_string(fill)
        if line:
            shape.line.color.rgb = RGBColor.from_string(line)
        else:
            shape.line.fill.background()
        shape.shadow.inherit = False
        return shape

    def add(self, spec: SlideSpec, title: str) -> None:
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.page += 1
        W = self.w / self.scale  # 기준 좌표계: 높이 210mm
        pal, sizes = self.pal, self.mode["body_pt"]
        if spec.kind == "cover":
            self._rect(slide, 0, 0, W, 210, pal["dark"])
            self._text(slide, 20, 70, W - 40, 40, [(spec.head, self.mode["head_pt"] + 8, True, "FFFFFF")],
                       align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            self._text(slide, 20, 115, W - 40, 15, [("기술제안서 " + ("요약본" if self.mode is self.cfg["summary"] else "발표자료"),
                                                    sizes[0], False, pal["light"])], align=PP_ALIGN.CENTER)
        else:
            if spec.breadcrumb:
                self._text(slide, 12, 6, W * 0.62, 7, [(spec.breadcrumb, 9, False, pal["gray"])])
            if spec.eval_tag:
                tag = self._rect(slide, W - 12 - 75, 6, 75, 7, pal["main"], rounded=True)
                tf = tag.text_frame
                tf.margin_top = tf.margin_bottom = Mm(0.3)
                run = tf.paragraphs[0].add_run()
                run.text = spec.eval_tag[:40]
                tf.paragraphs[0].alignment = PP_ALIGN.CENTER
                self._font(run, 9, bold=True, color="FFFFFF")
            x = 12.0
            for rid in spec.req_ids[:8]:
                chip = self._rect(slide, x, 14.5, 25, 5.5, pal["light"], rounded=True)
                run = chip.text_frame.paragraphs[0].add_run()
                run.text = rid
                chip.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
                chip.text_frame.margin_top = chip.text_frame.margin_bottom = Mm(0)
                self._font(run, 7.5, color=pal["dark"])
                x += 26.5
            if len(spec.req_ids) > 8:
                self._text(slide, x, 14, 20, 6, [(f"+{len(spec.req_ids) - 8}", 8, True, pal["dark"])])
            self._text(slide, 12, 22, W - 24, 15, [(spec.head, self.mode["head_pt"], True, pal["dark"])], anchor=MSO_ANCHOR.MIDDLE)
            self._rect(slide, 12, 37.5, W - 24, 0.8, pal["main"])
            body_w = (W - 24) * (0.4 if spec.image else 0.62 if (spec.table or spec.side_points) else 1.0)
            lines, used = [], 0
            symbols = ["□", "○", "-"]
            for lv, text in spec.bullets:
                if used >= self.mode["max_lines"]:
                    lines.append(("…", sizes[-1], False, pal["gray"]))
                    break
                lines.append(("    " * lv + f"{symbols[lv]} {text}", sizes[lv], lv == 0, None))
                used += 1 + len(text) // 60
            if lines:
                self._text(slide, 12, 42, body_w, 135, lines)
            right_x = 12 + body_w + 5
            right_w = W - 12 - right_x
            if spec.image:
                bottom = self._picture(slide, spec.image, right_x, 42, right_w, 128)
                if spec.image_title:
                    self._text(slide, right_x, bottom + 1, right_w, 6, [(spec.image_title, 9, False, pal["gray"])],
                               align=PP_ALIGN.CENTER)
            elif spec.table:
                header, rows = spec.table
                s = self.scale
                n_rows, n_cols = len(rows) + 1, max(len(header), 1)
                gt = slide.shapes.add_table(n_rows, n_cols, Mm(right_x * s), Mm(42 * s), Mm(right_w * s),
                                            Mm(min(8 * n_rows, 120) * s)).table
                for r, row in enumerate([header] + rows):
                    for c in range(n_cols):
                        cell = gt.cell(r, c)
                        cell.text = ""
                        run = cell.text_frame.paragraphs[0].add_run()
                        run.text = _clean(row[c] if c < len(row) else "")[:60]
                        self._font(run, 9, bold=(r == 0), color="FFFFFF" if r == 0 else None)
                        cell.fill.solid()
                        cell.fill.fore_color.rgb = RGBColor.from_string(pal["main"] if r == 0 else "FFFFFF")
            elif spec.side_points:
                self._rect(slide, right_x, 42, right_w, 135, pal["light"])
                self._text(slide, right_x + 3, 45, right_w - 6, 129,
                           [(spec.side_title, sizes[1], True, pal["dark"])] + [(f"• {p}", sizes[-1], False, None)
                                                                                for p in spec.side_points])
            if spec.summary:
                self._rect(slide, 12, 182, W - 24, 13, pal["box"], line=pal["main"])
                self._text(slide, 15, 182, W - 30, 13, [("▶ " + spec.summary[:120], sizes[-1], True, pal["dark"])],
                           anchor=MSO_ANCHOR.MIDDLE)
            self._text(slide, 12, 199, W * 0.6, 6, [(title, 8, False, pal["gray"])])
            self._text(slide, W - 32, 199, 20, 6, [(str(self.page), 9, False, pal["gray"])], align=PP_ALIGN.RIGHT)
        if spec.notes:
            slide.notes_slide.notes_text_frame.text = spec.notes

    def _picture(self, slide, path: str, x: float, y: float, w: float, h: float) -> float:
        """그림을 상자(x, y, w, h — 기준 좌표계 mm) 위쪽에 비율을 지켜 놓고, 그림 아래 끝 y를 돌려준다."""
        from PIL import Image

        with Image.open(path) as im:
            ratio = im.height / im.width
        pw, ph = (w, w * ratio) if w * ratio <= h else (h / ratio, h)
        s = self.scale
        slide.shapes.add_picture(path, Mm((x + (w - pw) / 2) * s), Mm(y * s), Mm(pw * s), Mm(ph * s))
        return y + ph

    def save(self, path: Path, title: str) -> None:
        self.prs.core_properties.title = title
        path.parent.mkdir(parents=True, exist_ok=True)
        self.prs.save(str(path))


def render_deck(path: Path, specs: list[SlideSpec], *, style: dict[str, Any], mode: str, title: str) -> int:
    w = DeckWriter(style, mode)
    for spec in specs:
        w.add(spec, title)
    w.save(path, title)
    return len(specs)


def script_markdown(specs: list[SlideSpec], rfp: Rfp, drafts: list[SectionDraft], *, minutes: int | None,
                    title: str) -> str:
    """발표 대본(장별 노트)과 예상 질문. LLM 없이 스토리보드·초안·평가 질문으로 만든 초안이다."""
    per = f"{minutes / max(len(specs), 1):.1f}분" if minutes else "?"
    lines = [f"# 발표 대본 — {title}", "",
             f"> 장 {len(specs)}개, 발표 {minutes or '?'}분 기준 장당 약 {per}. 블라인드 평가라면 회사명을 말하지 않습니다.", ""]
    for i, s in enumerate(specs, start=1):
        lines += [f"## {i}. {s.head or s.breadcrumb}", "", s.notes or "(대본 없음)", ""]
    lines += ["# 예상 질문", "", "> 평가 질문과 아직 근거가 비어 있는 곳에서 뽑았습니다. 답변은 담당자가 채웁니다.", ""]
    n = 0
    for area in rfp.evaluation.areas:
        if area.kind != "정성":
            continue
        for it in area.items:
            for q in it.criteria[:1]:
                n += 1
                lines.append(f"{n}. [{it.name}] {q.rstrip('.')} — 근거를 구체적으로 설명해 주십시오.")
    weak = [d for d in drafts if d.placeholders]
    for d in weak[:10]:
        n += 1
        lines.append(f"{n}. [{d.number} {d.title}] 이 부분의 근거(실적·인력·수치)를 제시해 주십시오. "
                     f"(초안에 확인 필요 {len(d.placeholders)}곳)")
    lines.append("")
    return "\n".join(lines)
