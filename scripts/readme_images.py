# SPDX-License-Identifier: GPL-3.0-or-later
"""README 작동 이미지 만들기(개발용).

체험용 가상 제안요청서(rfpgen sample)로 실제 명령을 돌려 터미널 화면과 결과 문서를 PNG로 만든다.
실제 공고 원문은 쓰지 않는다.

    uv run python scripts/readme_images.py            # 골격 초안
    uv run python scripts/readme_images.py --llm      # 본문 두 절은 Claude로 작성(RFP_ANTHROPIC_API_KEY 필요)

필요: rfpgen setup을 마친 변환기(Node 사이드카·Chromium·LibreOffice), pdftoppm(poppler-utils), Noto CJK 글꼴.
"""

from __future__ import annotations

import argparse
import fcntl
import io
import os
import pty
import re
import select
import shutil
import struct
import subprocess
import sys
import tempfile
import termios
from pathlib import Path

from PIL import Image, ImageChops
from rich.console import Console
from rich.text import Text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rfpgen.render.pdf import svgs_to_png  # noqa: E402

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


def terminal_svg(commands: list[tuple[str, str]], title: str) -> str:
    """(보여 줄 명령, 출력) 목록을 터미널 창 모양 SVG로."""
    console = Console(record=True, width=COLS, file=io.StringIO(), force_terminal=True, color_system="truecolor")
    for shown, output in commands:
        console.print(Text("$ ", style="bold green") + Text(shown, style="bold"))
        console.print(Text.from_ansi(output.rstrip("\n")))
    svg = console.export_svg(title=title, font_aspect_ratio=0.5)
    svg = re.sub(r"@font-face\s*\{[^}]*\}", "", svg)                      # 외부 글꼴을 받지 않는다
    return svg.replace("Fira Code", "Noto Sans Mono CJK KR")


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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "images")
    ap.add_argument("--llm", action="store_true", help="본문 두 절을 Claude로 작성")
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="rfpgen-readme-"))
    proj = "projects/예제_제안요청서"
    print(f"작업 폴더: {work}")

    # 회사 정보(가상): 예시 KB에 실적 한 건과 별지용 실명을 더한다
    subprocess.run([*RFPGEN, "kb", "init", "kb"], cwd=work, check=True, capture_output=True,
                   env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    (work / "kb" / "projects.csv").open("a", encoding="utf-8").write(
        "P-002,행정정보 통합 고도화,△△부,2023-02,2023-11,830000000,참여,Python;React,실적증명서_P-002.pdf\n")
    (work / "kb" / "private" / "people.csv").write_text("id,name\nH-001,김예시\nH-002,이예시\n", encoding="utf-8")

    screens: dict[str, list[tuple[str, str]]] = {"start": [], "help": [], "status": []}
    screens["help"].append(("rfpgen --help", run_tty([*RFPGEN, "--help"], work)))
    screens["start"].append(("rfpgen sample", run_tty([*RFPGEN, "sample"], work)))
    screens["start"].append(("rfpgen start 예제_제안요청서.hwpx --kb kb --date 2026-12-01",
                             run_tty([*RFPGEN, "start", "예제_제안요청서.hwpx", "--kb", "kb", "--date", "2026-12-01"],
                                     work)))
    if args.llm:
        sections = ["S-3-1", "S-4-1"]                       # 사업 이해도, 기능 요구사항
        run_tty([*RFPGEN, "draft", proj, "--llm", *[x for s in sections for x in ("--section", s)]], work)
        run_tty([*RFPGEN, "slides", proj], work)
        run_tty([*RFPGEN, "package", proj], work)
    screens["status"].append((f"rfpgen status {proj}", run_tty([*RFPGEN, "status", proj], work)))

    svgs = []
    for name, cmds in screens.items():
        svg = work / f"term-{name}.svg"
        svg.write_text(terminal_svg(cmds, title="rfpgen"), encoding="utf-8")
        svgs.append((svg, out / f"terminal-{name}.png"))
    svgs_to_png(svgs, dpi=144)

    p = work / proj
    sub = p / "submission"
    main_pdf = sub / "01_정성제안서.pdf"
    pages = {
        "proposal-section": find_page(main_pdf, "사업 이해도"),
        "proposal-figure": find_page(main_pdf, "목표 시스템 구성도", with_image=True),
        "proposal-responses": find_page(main_pdf, "요구사항 대응"),
    }
    shots: dict[str, Path] = {}
    for name, page in pages.items():
        shots[name] = pdf_page_png(main_pdf, page, work / name)
    shots["slide-summary"] = pdf_page_png(sub / "02_제안요약서.pdf", find_page(sub / "02_제안요약서.pdf", "기능 요구사항 >"),
                                          work / "slide-summary", dpi=60)
    shots["slide-presentation"] = pdf_page_png(sub / "03_발표자료.pdf", find_page(sub / "03_발표자료.pdf", "사업 추진 일정"),
                                               work / "slide-presentation", dpi=60)
    forms_pdf = p / "out" / "pdf" / "forms"
    shots["form-application"] = pdf_page_png(next(forms_pdf.glob("별지01_*.pdf")), 1, work / "form-application", dpi=100)
    shots["form-records"] = pdf_page_png(next(forms_pdf.glob("별지04_*.pdf")), 1, work / "form-records", dpi=100)
    for key in ("form-application", "form-records"):
        autocrop(shots[key])

    for name in ("proposal-section", "proposal-figure", "proposal-responses"):
        frame(shots[name])
    side_by_side([shots["proposal-section"], shots["proposal-figure"], shots["proposal-responses"]],
                 out / "proposal-pages.png")
    for key in ("slide-summary", "slide-presentation"):
        frame(shots[key])
    side_by_side([shots["slide-summary"], shots["slide-presentation"]], out / "slides.png")
    for key in ("form-application", "form-records"):
        frame(shots[key])
        shutil.copy(shots[key], out / f"{key}.png")

    figs = p / "out" / "figures"
    order = ["gantt", "org", "layers", "flow"]
    pngs = sorted(figs.glob("*.png"), key=lambda f: next((i for i, k in enumerate(order) if f.stem.endswith(k)), 9))
    for f in pngs[:3]:
        shutil.copy(f, out / f"figure-{f.stem.rsplit('-', 1)[-1]}.png")

    for png in out.glob("*.png"):
        shrink(png)
        print(f"{png.relative_to(ROOT)}  {png.stat().st_size // 1024}KB")


if __name__ == "__main__":
    main()
