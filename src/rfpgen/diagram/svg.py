"""도식 스펙 → SVG(설계서 7.9절 '도식').

외부 그래프 도구 없이 종류별 고정 배치로 그린다(조직도·WBS는 위→아래 나무, 절차는 화살표 단계, 일정은 막대,
시스템 구성도는 층 띠). 폭은 본문 폭에 맞추고 글자 크기는 표 글자 크기(RFP 최소 크기 이상)를 쓴다 — 그림을
줄여 넣지 않으므로 그림 속 글자도 RFP 최소 글자 크기를 지킨다. 글자 폭은 글꼴 없이 어림하므로 칸에 여유를 둔다.
"""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass
from typing import Any
from xml.sax.saxutils import escape

from ..schemas.diagram import DiagramNode, DiagramSpec

PX_PER_MM = 96 / 25.4
PX_PER_PT = 96 / 72


@dataclass
class Theme:
    width: float                     # px(96dpi)
    font_px: float
    family: str = "Noto Sans KR, Noto Sans CJK KR, Malgun Gothic, sans-serif"
    main: str = "#0055A5"
    dark: str = "#003B71"
    light: str = "#E8F1FA"
    gray: str = "#8C8C8C"
    box: str = "#F2F2F2"
    accent: str = "#F28C28"
    line: str = "#5A6B7D"
    grid: str = "#D0D7DE"

    @property
    def lh(self) -> float:
        return self.font_px * 1.3


def theme_from_style(style: dict[str, Any], min_pt: float | None = None) -> Theme:
    m = style["page"]["margin_mm"]
    page_w = 210 if style["page"].get("orientation", "portrait") == "portrait" else 297
    fig = style.get("figure") or {}
    pt = max(float(fig.get("font_pt") or style["size"]["table"]), float(min_pt or 0))
    pal = (style.get("slides") or {}).get("palette") or {}
    kw = {k: f"#{pal[k]}" for k in ("main", "dark", "light", "gray", "box", "accent") if k in pal}
    table_font = style["fonts"][style.get("render_path", "server")]["table"]
    family = fig.get("font_family") or f"{table_font}, Noto Sans CJK KR, sans-serif"
    return Theme(width=(page_w - m["left"] - m["right"]) * PX_PER_MM, font_px=pt * PX_PER_PT, family=family, **kw)


# ---------------------------------------------------------------- 글자

def char_w(c: str) -> float:
    if c == " ":
        return 0.3
    ea = unicodedata.east_asian_width(c)
    if ea in ("W", "F"):
        return 1.0
    if ea == "A":
        return 0.6
    if c.isupper() or c.isdigit():
        return 0.62
    return 0.52


def text_w(s: str, px: float) -> float:
    return sum(char_w(c) for c in s) * px


def wrap(s: str, max_w: float, px: float) -> list[str]:
    out: list[str] = []
    for para in (s or "").split("\n"):
        line = ""
        for word in para.split(" "):
            cand = f"{line} {word}" if line else word
            if text_w(cand, px) <= max_w:
                line = cand
                continue
            if line:
                out.append(line)
                line = ""
            while text_w(word, px) > max_w and len(word) > 1:      # 긴 낱말은 글자 단위로 자른다
                k = len(word)
                while k > 1 and text_w(word[:k], px) > max_w:
                    k -= 1
                out.append(word[:k])
                word = word[k:]
            line = word
        out.append(line)
    return out or [""]


# ---------------------------------------------------------------- 그리기

class Canvas:
    def __init__(self, t: Theme) -> None:
        self.t = t
        self.parts: list[str] = []

    def rect(self, x, y, w, h, *, fill="none", stroke="none", sw=1.0, rx=3.0, dash=False) -> None:
        d = ' stroke-dasharray="5 3"' if dash else ""
        self.parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx:.1f}" '
                          f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, *, stroke=None, sw=1.2, dash=False, arrow=False) -> None:
        d = ' stroke-dasharray="5 3"' if dash else ""
        a = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                          f'stroke="{stroke or self.t.line}" stroke-width="{sw}"{d}{a}/>')

    def poly(self, pts: list[tuple[float, float]], *, fill: str, stroke: str = "none") -> None:
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        self.parts.append(f'<polygon points="{p}" fill="{fill}" stroke="{stroke}"/>')

    def text(self, lines: list[str], x: float, cy: float, *, color: str = "#222222", bold: bool = False,
             anchor: str = "middle", px: float | None = None, top: float | None = None) -> None:
        """여러 줄 글. cy를 세로 가운데로 두거나 top을 위 끝으로 둔다."""
        px = px or self.t.font_px
        lh = px * 1.3
        y0 = (top if top is not None else cy - lh * len(lines) / 2) + lh / 2 + px * 0.35
        weight = ' font-weight="700"' if bold else ""
        for i, ln in enumerate(lines):
            self.parts.append(f'<text x="{x:.1f}" y="{y0 + i * lh:.1f}" text-anchor="{anchor}" fill="{color}" '
                              f'font-size="{px:.1f}"{weight} xml:space="preserve">{escape(ln)}</text>')

    def svg(self, width: float, height: float) -> str:
        t = self.t
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
                f'viewBox="0 0 {width:.0f} {height:.0f}" font-family="{escape(t.family)}">'
                f'<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{t.line}"/></marker></defs>'
                f'<rect width="100%" height="100%" fill="#FFFFFF"/>')
        return head + "".join(self.parts) + "</svg>"


@dataclass
class _Box:
    node: DiagramNode
    x: float = 0
    y: float = 0
    w: float = 0
    h: float = 0
    label: list[str] | None = None
    note: list[str] | None = None

    @property
    def cx(self) -> float:
        return self.x + self.w / 2


def _fit(box: _Box, t: Theme, w: float, pad: float = 7) -> None:
    box.w = w
    box.label = wrap(box.node.label, w - 2 * pad, t.font_px)
    box.note = wrap(box.node.note, w - 2 * pad, t.font_px) if box.node.note else []
    box.h = (len(box.label) + len(box.note)) * t.lh + 2 * pad


def _draw_box(c: Canvas, b: _Box, *, fill: str, stroke: str, color: str, note_color: str, dash: bool = False,
              align: str = "middle", bold: bool = True) -> None:
    t = c.t
    c.rect(b.x, b.y, b.w, b.h, fill=fill, stroke=stroke, sw=1.2, dash=dash)
    pad = 7
    x = b.cx if align == "middle" else b.x + pad
    c.text(b.label or [], x, 0, color=color, bold=bold, anchor=align, top=b.y + pad)
    if b.note:
        c.text(b.note, x, 0, color=note_color, anchor=align, top=b.y + pad + len(b.label or []) * t.lh)


# ---------------------------------------------------------------- 나무(조직도·WBS)

def _row(c_w: float, n: int, gap: float, max_w: float, min_w: float) -> tuple[float, int]:
    """한 줄에 n개를 놓을 때 상자 폭과 한 줄 개수."""
    per = n
    while per > 1 and (c_w - gap * (per - 1)) / per < min_w:
        per -= 1
    w = min(max_w, (c_w - gap * (per - 1)) / per)
    return w, per


def render_tree(spec: DiagramSpec, t: Theme) -> tuple[str, float, float]:
    c = Canvas(t)
    W, pad, gap = t.width, 4.0, 10.0
    nodes = spec.nodes
    kids: dict[str, list[DiagramNode]] = {}
    for n in nodes:
        if n.parent:
            kids.setdefault(n.parent, []).append(n)
    externals = [n for n in nodes if n.group == "external"]
    roots = [n for n in nodes if not n.parent and n.group != "external"]
    if not roots:
        return c.svg(W, 40), W, 40
    root = roots[0]
    supports = [n for n in kids.get(root.id, []) if n.group == "support"]
    level1 = [n for n in kids.get(root.id, []) if n.group != "support"] + roots[1:]
    y = pad
    boxes: dict[str, _Box] = {}

    # 바깥 조직(발주기관·감리) — 맨 위 줄, 점선
    if externals:
        w, _ = _row(W - 2 * pad, len(externals), gap * 3, 180, 90)
        row = [_Box(n) for n in externals]
        for b in row:
            _fit(b, t, w)
        h = max(b.h for b in row)
        total = len(row) * w + (len(row) - 1) * gap * 3
        x = (W - total) / 2
        for b in row:
            b.x, b.y, b.h = x, y, h
            x += w + gap * 3
            boxes[b.node.id] = b
            _draw_box(c, b, fill=t.box, stroke=t.gray, color=t.dark, note_color="#444444", dash=True)
        y += h + t.lh * 2 + 8

    # 뿌리(PM)와 지원 조직
    rb = _Box(root)
    _fit(rb, t, min(max(text_w(root.label, t.font_px), text_w(root.note, t.font_px)) + 30, W * 0.4))
    rb.w = max(rb.w, 140)
    _fit(rb, t, rb.w)
    rb.x, rb.y = (W - rb.w) / 2, y
    boxes[root.id] = rb
    sbs = [_Box(n) for n in supports]
    sx = rb.x + rb.w + 30
    for sb in sbs:
        _fit(sb, t, min(max(text_w(sb.node.label, t.font_px), text_w(sb.node.note, t.font_px)) + 26,
                        max(90, W - sx - pad)))
        sb.x, sb.y = sx, y
        sx += sb.w + gap
        boxes[sb.node.id] = sb
    if sbs and sbs[-1].x + sbs[-1].w > W - pad:          # 오른쪽에 자리가 없으면 뿌리를 왼쪽으로 민다
        shift = sbs[-1].x + sbs[-1].w - (W - pad)
        rb.x = max(pad, rb.x - shift)
        sx = rb.x + rb.w + 30
        for sb in sbs:
            sb.x = sx
            sx += sb.w + gap
    top_h = max([rb.h] + [b.h for b in sbs])
    for e in externals:                                   # 바깥 조직 → 뿌리 점선
        eb = boxes[e.id]
        mid = eb.y + eb.h + t.lh
        c.line(eb.cx, eb.y + eb.h, eb.cx, mid, dash=True)
        c.line(eb.cx, mid, rb.cx, mid, dash=True)
        label = next((ed.label for ed in spec.edges if ed.src == e.id and ed.dst == root.id), "")
        if label:
            lw = text_w(label, t.font_px) + 8
            lx = eb.cx + (8 if eb.cx <= rb.cx else -lw - 8)
            c.rect(lx, mid - t.lh / 2 - 1, lw, t.lh + 2, fill="#FFFFFF", rx=2)
            c.text([label], lx + lw / 2, mid, color=t.gray)
    if externals:
        c.line(rb.cx, y - t.lh - 8, rb.cx, rb.y, dash=True, arrow=True)
    _draw_box(c, rb, fill=t.dark, stroke=t.dark, color="#FFFFFF", note_color="#DCE6F1")
    for sb in sbs:
        c.line(rb.x + rb.w, rb.y + rb.h / 2, sb.x, sb.y + sb.h / 2, dash=True)
        _draw_box(c, sb, fill=t.light, stroke=t.main, color=t.dark, note_color="#333333")
    y += top_h

    # 1단계(팀·단계) — 가로, 2단계(팀원·활동) — 각 상자 아래 세로 목록
    if level1:
        w, per = _row(W - 2 * pad, len(level1), gap, 190, 84)
        rows = [level1[i:i + per] for i in range(0, len(level1), per)]
        bus_gap = t.lh * 1.2
        for r_i, members in enumerate(rows):
            row = [_Box(n) for n in members]
            for b in row:
                _fit(b, t, w)
            h = max(b.h for b in row)
            total = len(row) * w + (len(row) - 1) * gap
            x = (W - total) / 2
            bus_y = y + bus_gap
            top = bus_y + bus_gap * 0.8
            for b in row:
                b.x, b.y, b.h = x, top, h
                x += w + gap
                boxes[b.node.id] = b
            trunk_x = rb.cx if r_i == 0 else pad + 1
            c.line(trunk_x, y if r_i == 0 else y - 2, trunk_x, bus_y)
            c.line(min(row[0].cx, trunk_x), bus_y, max(row[-1].cx, trunk_x), bus_y)
            for b in row:
                c.line(b.cx, bus_y, b.cx, b.y)
                _draw_box(c, b, fill=t.main, stroke=t.main, color="#FFFFFF", note_color="#E8F1FA")
            bottom = top + h
            for b in row:                                   # 2단계 목록
                cy = b.y + b.h + 8
                last_mid = None
                for k in kids.get(b.node.id, []):
                    kb = _Box(k)
                    _fit(kb, t, b.w - 12, pad=5)
                    kb.x, kb.y = b.x + 12, cy
                    _draw_box(c, kb, fill=t.light, stroke=t.main, color="#222222", note_color="#333333", align="start",
                              bold=False)
                    last_mid = kb.y + kb.h / 2
                    c.line(b.x + 6, last_mid, kb.x, last_mid)
                    cy += kb.h + 6
                    boxes[k.id] = kb
                if last_mid is not None:
                    c.line(b.x + 6, b.y + b.h, b.x + 6, last_mid)
                bottom = max(bottom, cy)
            y = bottom
    return c.svg(W, y + pad), W, y + pad


# ---------------------------------------------------------------- 절차(화살표 단계)

def render_flow(spec: DiagramSpec, t: Theme) -> tuple[str, float, float]:
    c = Canvas(t)
    W, pad, tip, gap = t.width, 2.0, 12.0, 3.0
    n = max(len(spec.nodes), 1)
    cw = (W - 2 * pad + (n - 1) * (tip - gap)) / n
    labels = [wrap(nd.label, cw - 2 * tip - 4, t.font_px) for nd in spec.nodes]
    ch = max((len(lb) for lb in labels), default=1) * t.lh + 16
    y = pad
    for i in range(len(spec.nodes)):
        x = pad + i * (cw - tip + gap)
        left = [(x, y), (x + tip, y + ch / 2), (x, y + ch)] if i else [(x, y), (x, y + ch)]
        pts = [left[0], (x + cw - tip, y), (x + cw, y + ch / 2), (x + cw - tip, y + ch)] + left[1:][::-1]
        c.poly(pts, fill=t.main if i % 2 == 0 else t.dark)
        c.text(labels[i], x + cw / 2 + (tip / 4 if i else -tip / 4), y + ch / 2, color="#FFFFFF", bold=True)
    bullet = text_w("· ", t.font_px)

    def _items(note: str) -> list[str]:          # 내어쓰기: 둘째 줄부터 기호 폭만큼 들인다
        out: list[str] = []
        for item in (x.strip() for x in note.split("\n") if x.strip()):
            lines = wrap(item, cw - tip - 12 - bullet, t.font_px)
            out += ["· " + lines[0]] + ["  " + ln for ln in lines[1:]]
        return out

    notes = [_items(nd.note) for nd in spec.nodes]
    nh = max((len(x) for x in notes), default=0)
    if nh:
        top = y + ch + 6
        h = nh * t.lh + 12
        for i, lines in enumerate(notes):
            x = pad + i * (cw - tip + gap)
            c.rect(x + (tip / 2 if i else 0), top, cw - tip - (tip / 2 if i else 0) + tip / 2, h, fill=t.light, stroke=t.grid)
            c.text(lines, x + (tip / 2 if i else 0) + 6, 0, color="#222222", anchor="start", top=top + 6)
        y = top + h
    else:
        y += ch
    return c.svg(W, y + pad), W, y + pad


# ---------------------------------------------------------------- 일정(간트)

def render_gantt(spec: DiagramSpec, t: Theme) -> tuple[str, float, float]:
    c = Canvas(t)
    W, pad = t.width, 1.0
    months = max(spec.months, 1)
    unit = 1 if months <= 24 else math.ceil(months / 24)
    cols = math.ceil(months / unit)
    rows = [x for x in spec.tasks if not x.milestone]
    stones = [x for x in spec.tasks if x.milestone]
    label_w = min(max([text_w(x.label, t.font_px) for x in rows] + [text_w("주요 보고", t.font_px)]) + 16, W * 0.3)
    label_w = max(label_w, 84)
    col_w = (W - 2 * pad - label_w) / cols
    x0 = pad + label_w
    head_h = t.lh + 10
    y = pad
    c.rect(pad, y, label_w, head_h, fill=t.dark, rx=0)
    c.text(["구분"], pad + label_w / 2, y + head_h / 2, color="#FFFFFF", bold=True)
    step = 1 if col_w >= text_w("24", t.font_px) + 4 else 2
    for k in range(cols):
        c.rect(x0 + k * col_w, y, col_w, head_h, fill=t.main, stroke="#FFFFFF", sw=0.5, rx=0)
        if k % step == 0:
            lab = str(k * unit + 1) if unit == 1 else f"{k * unit + 1}"
            c.text([lab], x0 + (k + 0.5) * col_w, y + head_h / 2, color="#FFFFFF", bold=True)
    y += head_h
    body_top = y
    for task in rows:
        lines = wrap(task.label, label_w - 12, t.font_px)
        rh = max(len(lines) * t.lh + 8, t.lh + 12)
        c.rect(pad, y, label_w, rh, fill=t.box, stroke=t.grid, sw=0.6, rx=0)
        c.text(lines, pad + 6, y + rh / 2, anchor="start", color="#222222")
        bx = x0 + task.start / unit * col_w
        bw = max((task.end - task.start) / unit * col_w, 4)
        bh = min(rh * 0.5, t.lh)
        support = task.group in ("관리", "지원")
        c.rect(bx, y + (rh - bh) / 2, bw, bh, fill=t.light if support else t.main, stroke=t.main, sw=1, rx=2)
        y += rh
        c.line(x0, y, W - pad, y, stroke=t.grid, sw=0.6)
    if stones:
        rh = t.lh * 2 + 10
        c.rect(pad, y, label_w, rh, fill=t.box, stroke=t.grid, sw=0.6, rx=0)
        c.text(["주요 보고"], pad + 6, y + rh / 2, anchor="start", color="#222222")
        dy = y + rh * 0.32
        for s in stones:
            sx = min(max(x0 + s.start / unit * col_w, x0 + 6), W - pad - 6)
            r = t.font_px * 0.45
            c.poly([(sx, dy - r), (sx + r, dy), (sx, dy + r), (sx - r, dy)], fill=t.accent)
            tw = text_w(s.label, t.font_px)
            anchor, tx = ("middle", sx)
            if sx - tw / 2 < x0:
                anchor, tx = "start", max(sx - r, x0 + 1)
            elif sx + tw / 2 > W - pad:
                anchor, tx = "end", min(sx + r, W - pad - 1)
            c.text([s.label], tx, y + rh * 0.72, anchor=anchor, color=t.dark)
        y += rh
    for k in range(cols + 1):
        c.line(x0 + k * col_w, body_top, x0 + k * col_w, y, stroke=t.grid, sw=0.6)
    c.rect(pad, pad, W - 2 * pad, y - pad, stroke=t.gray, sw=1, rx=0)
    return c.svg(W, y + pad), W, y + pad


# ---------------------------------------------------------------- 시스템 구성도(층)

def render_layers(spec: DiagramSpec, t: Theme) -> tuple[str, float, float]:
    c = Canvas(t)
    W, pad, gap = t.width, 2.0, 6.0
    mains = [x for x in spec.layers if not x.side]
    sides = [x for x in spec.layers if x.side]
    side_w = 112.0
    main_w = W - 2 * pad - len(sides) * (side_w + gap)
    name_w = max(min(max((text_w(x.name, t.font_px) for x in mains), default=60) + 18, 110), 72)
    area_x = pad + name_w + gap
    area_w = main_w - name_w - gap
    y = pad
    for layer in mains:
        items = layer.items or [""]
        per = max(1, min(len(items), int((area_w - 8 + gap) // (90 + gap))))
        iw = (area_w - 8 - (per - 1) * gap) / per
        wrapped = [wrap(it, iw - 10, t.font_px) for it in items]
        ih = max(len(w) for w in wrapped) * t.lh + 10
        n_rows = math.ceil(len(items) / per)
        bh = n_rows * ih + (n_rows - 1) * gap + 12
        c.rect(pad, y, name_w, bh, fill=t.dark, rx=3)
        c.text(wrap(layer.name, name_w - 10, t.font_px), pad + name_w / 2, y + bh / 2, color="#FFFFFF", bold=True)
        c.rect(area_x, y, area_w, bh, fill=t.light, stroke=t.grid, rx=3)
        for k, lines in enumerate(wrapped):
            r_i, c_i = divmod(k, per)
            ix = area_x + 4 + c_i * (iw + gap)
            iy = y + 6 + r_i * (ih + gap)
            c.rect(ix, iy, iw, ih, fill="#FFFFFF", stroke=t.main, sw=1, rx=3)
            c.text(lines, ix + iw / 2, iy + ih / 2, color="#222222")
        y += bh + gap
    total_h = y - gap
    sx = pad + main_w + gap
    for layer in sides:
        c.rect(sx, pad, side_w, total_h - pad, fill=t.box, stroke=t.grid, rx=3)
        title = wrap(layer.name, side_w - 10, t.font_px)
        th = len(title) * t.lh + 10
        c.rect(sx, pad, side_w, th, fill=t.gray, rx=3)
        c.text(title, sx + side_w / 2, pad + th / 2, color="#FFFFFF", bold=True)
        iy = pad + th + 6
        for it in layer.items:
            lines = wrap(it, side_w - 18, t.font_px)
            ih = len(lines) * t.lh + 10
            c.rect(sx + 5, iy, side_w - 10, ih, fill="#FFFFFF", stroke=t.gray, rx=3)
            c.text(lines, sx + side_w / 2, iy + ih / 2, color="#222222")
            iy += ih + gap
        total_h = max(total_h, iy)
        sx += side_w + gap
    return c.svg(W, total_h + pad), W, total_h + pad


def render_svg(spec: DiagramSpec, theme: Theme) -> tuple[str, float, float]:
    """(SVG 문자열, 폭 px, 높이 px)."""
    if spec.kind in ("org", "wbs"):
        return render_tree(spec, theme)
    if spec.kind == "flow":
        return render_flow(spec, theme)
    if spec.kind == "gantt":
        return render_gantt(spec, theme)
    return render_layers(spec, theme)


__all__ = ["PX_PER_MM", "Theme", "render_svg", "text_w", "theme_from_style", "wrap"]
