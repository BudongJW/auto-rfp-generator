# SPDX-License-Identifier: GPL-3.0-or-later
"""README 작동 이미지 만들기(개발용).

체험용 가상 제안요청서(rfpgen sample)로 실제 명령을 돌려 터미널 화면과 결과 문서를 PNG로 만든다.
실제 공고 원문은 쓰지 않는다.

    uv run python scripts/readme_images.py --llm              # 본문 두 절은 Claude로 작성(RFP_ANTHROPIC_API_KEY 필요)
    uv run python scripts/readme_images.py --reuse <작업 폴더>  # 앞서 쓴 초안으로 장표·PDF·이미지만 다시

필요: rfpgen setup을 마친 변환기(Node 사이드카·Chromium·LibreOffice), pdftoppm(poppler-utils),
fc-match(fontconfig), 글꼴 Noto Sans CJK KR·DejaVu Sans Mono.
"""

from __future__ import annotations

import argparse
import fcntl
import io
import os
import pty
import select
import shutil
import struct
import subprocess
import sys
import tempfile
import termios
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont
from rich.cells import cell_len
from rich.console import Console
from rich.segment import Segment
from rich.terminal_theme import SVG_EXPORT_THEME
from rich.text import Text

ROOT = Path(__file__).resolve().parents[1]
COLS = 100
RFPGEN = [sys.executable, "-m", "rfpgen"]


# ---------------------------------------------------------------- 터미널 화면


def run_tty(args: list[str], cwd: Path, rows: int = 60) -> str:
    """가상 터미널에서 실행해 색이 든 출력을 받는다."""
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, COLS, 0, 0))
    env = {**os.environ, "COLUMNS": str(COLS), "TERM": "xterm-256color", "PYTHONPATH": str(ROOT / "src")}
    proc = subprocess.Popen(args, cwd=cwd, env=env, stdin=slave, stdout=slave, stderr=slave, close_fds=True)
    os.close(slave)
    chunks: list[bytes] = []
    while True:
        try:
            ready, _, _ = select.select([master], [], [], 0.5)
        except OSError:
            break
        if ready:
            try:
                data = os.read(master, 65536)
            except OSError:
                break
            if not data:
                break
            chunks.append(data)
        elif proc.poll() is not None:
            break
    proc.wait()
    os.close(master)
    return b"".join(chunks).decode("utf-8", "replace").replace("\r\n", "\n")


def _font_file(pattern: str) -> tuple[str, int]:
    out = subprocess.run(["fc-match", "-f", "%{file}:%{index}", pattern], capture_output=True, text=True,
                         check=True).stdout
    path, _, index = out.rpartition(":")
    return path, int(index or 0)


class _Fonts:
    """칸 글꼴(라틴·상자 문자: DejaVu Sans Mono)과 넓은 글자 글꼴(한글: Noto Sans CJK KR)."""

    def __init__(self, size: int) -> None:
        def load(pattern: str, px: int = size) -> ImageFont.FreeTypeFont:
            path, index = _font_file(pattern)
            return ImageFont.truetype(path, px, index=index)

        self.mono = {False: load("DejaVu Sans Mono"), True: load("DejaVu Sans Mono:style=Bold")}
        self.cell = round(self.mono[False].getlength("M"))
        wide_px = round(2 * self.cell * 0.92)                   # 한글 한 글자가 두 칸을 거의 채우게
        self.wide = {False: load("Noto Sans CJK KR", wide_px), True: load("Noto Sans CJK KR:style=Bold", wide_px)}
        self._notdef = self._glyph("\ue000")                 # 없는 글자의 모양(.notdef)
        self._has: dict[str, bool] = {}

    def _glyph(self, ch: str) -> bytes:
        font = self.mono[False]
        im = Image.new("L", (int(font.size) * 2, int(font.size) * 2))
        ImageDraw.Draw(im).text((0, 0), ch, font=font, fill=255)
        return im.tobytes()

    def pick(self, ch: str, bold: bool) -> ImageFont.FreeTypeFont:
        if ch not in self._has:
            self._has[ch] = self._glyph(ch) != self._notdef
        return (self.mono if self._has[ch] else self.wide)[bold]


def _blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))  # type: ignore[return-value]


def terminal_png(commands: list[tuple[str, str]], out: Path, *, title: str = "rfpgen", size: int = 22) -> None:
    """(보여 줄 명령, 출력) 목록을 터미널 창 모양 PNG로. 한 글자씩 칸 격자에 놓아 한글(두 칸)이 겹치지 않는다."""
    theme = SVG_EXPORT_THEME
    console = Console(width=COLS, file=io.StringIO(), force_terminal=True, color_system="truecolor")
    lines: list[list[Segment]] = []
    for shown, output in commands:
        lines += console.render_lines(Text("$ ", style="bold green") + Text(shown, style="bold"), pad=False)
        lines += console.render_lines(Text.from_ansi(output.rstrip("\n")), pad=False)
    fonts = _Fonts(size)
    cw, lh, pad, bar = fonts.cell, round(size * 1.38), 26, 46
    width = COLS * cw + 2 * pad
    height = bar + len(lines) * lh + pad
    bg, fg = tuple(theme.background_color), tuple(theme.foreground_color)
    im = Image.new("RGB", (width + 4, height + 4), "white")
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle((2, 2, width + 1, height + 1), radius=12, fill=bg, outline="#C8CDD3")
    for i, color in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
        cx = 26 + i * 24
        draw.ellipse((cx - 7, 22 - 7, cx + 7, 22 + 7), fill=color)
    tf = fonts.pick("r", True)
    draw.text(((width - tf.getlength(title)) / 2, 22), title, font=tf, fill=_blend(bg, fg, 0.6), anchor="lm")
    for row, line in enumerate(lines):
        col, y = 0, bar + row * lh + lh / 2
        for seg in line:
            if seg.control:
                continue
            style = seg.style
            color = tuple(style.color.get_truecolor(theme)) if style and style.color else fg
            back = tuple(style.bgcolor.get_truecolor(theme, foreground=False)) if style and style.bgcolor else None
            if style and style.reverse:
                color, back = back or bg, color
            if style and style.dim:
                color = _blend(bg, color, 0.6)
            bold = bool(style and style.bold)
            for ch in seg.text:
                w = cell_len(ch)
                if w == 0:
                    continue
                x = pad + col * cw
                if back:
                    draw.rectangle((x, y - lh / 2, x + w * cw, y + lh / 2), fill=back)
                if not ch.isspace():
                    font = fonts.pick(ch, bold)
                    gx = x + (w * cw - font.getlength(ch)) / 2 if font in fonts.wide.values() else x
                    draw.text((gx, y), ch, font=font, fill=color, anchor="lm")
                col += w
    im.save(out)


# ---------------------------------------------------------------- 문서 화면


def pdf_page_png(pdf: Path, page: int, out: Path, dpi: int = 80) -> Path:
    base = out.with_suffix("")
    subprocess.run(["pdftoppm", "-r", str(dpi), "-png", "-f", str(page), "-l", str(page), "-singlefile",
                    str(pdf), str(base)], check=True)
    return base.with_suffix(".png")


def find_page(pdf: Path, needle: str, *, with_image: bool = False) -> int:
    import pdfplumber

    with pdfplumber.open(pdf) as doc:
        for i, page in enumerate(doc.pages, start=1):
            if needle in (page.extract_text() or "") and (not with_image or page.images):
                return i
    return 1


def page_text(pdf: Path, page: int) -> str:
    import pdfplumber

    with pdfplumber.open(pdf) as doc:
        return doc.pages[page - 1].extract_text() or "" if page <= len(doc.pages) else ""


def autocrop(path: Path, pad: int = 24) -> None:
    im = Image.open(path).convert("RGB")
    bbox = ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()
    if bbox:
        l, t, r, b = bbox
        im = im.crop((max(l - pad, 0), max(t - pad, 0), min(r + pad, im.width), min(b + pad, im.height)))
    im.save(path)


def frame(path: Path, border: int = 1) -> None:
    """흰 문서가 README 배경에 묻히지 않게 회색 테두리."""
    im = Image.open(path).convert("RGB")
    out = Image.new("RGB", (im.width + 2 * border, im.height + 2 * border), "#C8CDD3")
    out.paste(im, (border, border))
    out.save(path)


def side_by_side(paths: list[Path], out: Path, gap: int = 24, height: int | None = None) -> None:
    ims = [Image.open(p).convert("RGB") for p in paths]
    h = height or min(i.height for i in ims)
    ims = [i.resize((round(i.width * h / i.height), h)) for i in ims]
    canvas = Image.new("RGB", (sum(i.width for i in ims) + gap * (len(ims) - 1), h), "white")
    x = 0
    for i in ims:
        canvas.paste(i, (x, 0))
        x += i.width + gap
    canvas.save(out)


def shrink(path: Path, max_width: int = 1400) -> None:
    im = Image.open(path).convert("RGB")
    if im.width > max_width:
        im = im.resize((max_width, round(im.height * max_width / im.width)), Image.LANCZOS)
    im.quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(path, optimize=True)


# ---------------------------------------------------------------- 실행


def _rfpgen(args: list[str], cwd: Path) -> str:
    return run_tty([*RFPGEN, *args], cwd)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "images")
    ap.add_argument("--llm", action="store_true", help="본문 두 절을 Claude로 작성")
    ap.add_argument("--reuse", type=Path, help="앞서 만든 작업 폴더를 다시 쓴다(LLM 초안 유지, 장표·패키지만 다시)")
    args = ap.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    proj = "projects/예제_제안요청서"

    # 1) 터미널 화면: 늘 새 폴더에서 처음부터(오프라인)
    fresh = Path(tempfile.mkdtemp(prefix="rfpgen-readme-"))
    print(f"작업 폴더: {fresh}")
    subprocess.run([*RFPGEN, "kb", "init", "kb"], cwd=fresh, check=True, capture_output=True,
                   env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    # 회사 정보(가상): 예시 KB에 실적 한 건과 별지용 실명을 더한다
    with (fresh / "kb" / "projects.csv").open("a", encoding="utf-8") as f:
        f.write("P-002,행정정보 통합 고도화,△△부,2023-02,2023-11,830000000,참여,Python;React,실적증명서_P-002.pdf\n")
    (fresh / "kb" / "private" / "people.csv").write_text("id,name\nH-001,김예시\nH-002,이예시\n", encoding="utf-8")
    start = [("rfpgen sample", _rfpgen(["sample"], fresh)),
             ("rfpgen start 예제_제안요청서.hwpx --kb kb --date 2026-12-01",
              _rfpgen(["start", "예제_제안요청서.hwpx", "--kb", "kb", "--date", "2026-12-01"], fresh))]
    terminal_png(start, out / "terminal-start.png")
    terminal_png([("rfpgen --help", _rfpgen(["--help"], fresh))], out / "terminal-help.png")

    # 2) 결과 문서: 본문 두 절을 Claude로 쓴 폴더(--llm) 또는 앞서 만든 폴더(--reuse)
    work = args.reuse.resolve() if args.reuse else fresh
    if args.llm and not args.reuse:
        sections = ["S-3-1", "S-4-1"]                       # 사업 이해도, 기능 요구사항
        _rfpgen(["draft", proj, "--llm", *[x for s in sections for x in ("--section", s)]], work)
    if args.llm or args.reuse:
        _rfpgen(["slides", proj], work)
        _rfpgen(["package", proj], work)
    terminal_png([(f"rfpgen status {proj}", _rfpgen(["status", proj], work))], out / "terminal-status.png")

    p = work / proj
    sub = p / "submission"
    shots_dir = Path(tempfile.mkdtemp(prefix="rfpgen-shots-"))
    main_pdf = sub / "01_정성제안서.pdf"
    responses = find_page(main_pdf, "요구사항 대응")
    if "수용" not in page_text(main_pdf, responses):                # 제목만 쪽 끝에 걸리면 표가 있는 다음 쪽
        responses += 1
    pages = [find_page(main_pdf, "사업 이해도"), find_page(main_pdf, "목표 시스템 구성도", with_image=True), responses]
    shots = [pdf_page_png(main_pdf, n, shots_dir / f"proposal-{i}") for i, n in enumerate(pages)]
    for s in shots:
        frame(s)
    side_by_side(shots, out / "proposal-pages.png")

    summary, deck = sub / "02_제안요약서.pdf", sub / "03_발표자료.pdf"
    slides = [pdf_page_png(summary, find_page(summary, "> 기능 요구사항", with_image=True), shots_dir / "slide-1",
                           dpi=90),
              pdf_page_png(deck, find_page(deck, "100MB", with_image=True), shots_dir / "slide-2", dpi=90)]
    for s in slides:
        frame(s)
    side_by_side(slides, out / "slides.png")

    forms_pdf = p / "out" / "pdf" / "forms"
    for key, pattern in (("form-application", "별지01_*.pdf"), ("form-records", "별지04_*.pdf")):
        shot = pdf_page_png(next(forms_pdf.glob(pattern)), 1, shots_dir / key, dpi=130)
        autocrop(shot)
        frame(shot)
        shutil.copy(shot, out / f"{key}.png")

    for kind in ("flow", "layers", "gantt"):                 # 조직도는 예시 KB(2명)라 빈약해 뺀다
        src = next((p / "out" / "figures").glob(f"*-{kind}.png"), None)
        if src is not None:
            shutil.copy(src, out / f"figure-{kind}.png")

    for png in sorted(out.glob("*.png")):
        shrink(png)
        print(f"{png.name}  {png.stat().st_size // 1024}KB")


if __name__ == "__main__":
    main()
