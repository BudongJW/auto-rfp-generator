"""PDF 변환과 후처리(설계서 7.9절 PDF 경로·후처리).

- HWPX/HWP → PDF: Node 사이드카(sidecars/node/hwpx_to_pdf.mjs) — rhwp(MIT)로 쪽별 SVG, Chromium으로 벡터 PDF.
  rhwp의 쪽 나눔으로 정확한 쪽수를 얻는다. 한글 렌더와 픽셀 단위로 같다는 보장은 없다.
- PPTX → PDF: LibreOffice headless. 변환마다 별도 사용자 프로필을 써서 상태가 섞이지 않게 한다
  (docs/analysis/hwpx-rendering-tools.md 3.2절의 운영 지식).
- 후처리(pikepdf, MPL-2.0): 메타데이터(작성자·제작 도구·XMP) 정리, 쪽수·글꼴 임베딩·용량 측정.
"""

from __future__ import annotations

import functools
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


class RenderError(RuntimeError):
    pass


def sidecar_dir() -> Path:
    env = os.environ.get("RFPGEN_SIDECAR_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3] / "sidecars" / "node"


_SOFFICE_PATHS = (
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
)


def soffice_path() -> str | None:
    """LibreOffice 실행 파일: PATH(soffice, libreoffice) → Windows·macOS 기본 설치 위치 → RFPGEN_SOFFICE."""
    env = os.environ.get("RFPGEN_SOFFICE")
    if env and Path(env).exists():
        return env
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    return next((p for p in _SOFFICE_PATHS if Path(p).exists()), None)


@functools.lru_cache(maxsize=8)
def playwright_version(sc: str) -> str | None:
    """사이드카에서 쓸 수 있는 Playwright 버전(사이드카 node_modules 또는 전역). 없으면 None."""
    if not shutil.which("node"):
        return None
    local = Path(sc) / "node_modules" / "playwright" / "package.json"
    if local.exists():
        return json.loads(local.read_text(encoding="utf-8")).get("version")
    try:
        proc = subprocess.run(["node", "-e", "console.log(require('playwright/package.json').version)"],
                              cwd=sc if Path(sc).is_dir() else None, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def converters_available() -> dict[str, bool]:
    sc = sidecar_dir()
    node = bool(shutil.which("node"))
    pw = node and playwright_version(str(sc)) is not None
    return {
        "hwpx": pw and (sc / "node_modules" / "@rhwp" / "core" / "rhwp.js").exists() and (sc / "hwpx_to_pdf.mjs").exists(),
        "pptx": soffice_path() is not None,
        "svg": pw and (sc / "svg_to_png.mjs").exists(),
    }


def svgs_to_png(pairs: list[tuple[Path, Path]], *, dpi: int = 200, font_aliases: list[str] | None = None,
                timeout: int = 300) -> list[dict]:
    """도식 SVG 여러 장을 PNG로 바꾼다(Chromium 한 번 실행). 실패하면 RenderError."""
    if not pairs:
        return []
    sc = sidecar_dir()
    if not converters_available()["svg"]:
        raise RenderError(f"SVG→PNG 변환기가 없습니다 — `cd {sc} && npm install && npx playwright install chromium`"
                          "(Node 18 이상 필요, 점검: rfpgen doctor)")
    cmd = ["node", str(sc / "svg_to_png.mjs"), "--dpi", str(dpi)]
    for alias in font_aliases or []:
        cmd += ["--font-alias", alias]
    for src, dst in pairs:
        dst.parent.mkdir(parents=True, exist_ok=True)
        cmd += [str(src), str(dst)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RenderError(f"SVG→PNG 변환 실패: {exc}") from exc
    if proc.returncode != 0 or not all(dst.exists() for _, dst in pairs):
        raise RenderError(f"SVG→PNG 변환 실패: {proc.stderr.strip()[-500:]}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def hwpx_to_pdf(src: Path, dst: Path, *, font_aliases: list[str] | None = None, timeout: int = 600) -> dict:
    sc = sidecar_dir()
    script = sc / "hwpx_to_pdf.mjs"
    if not converters_available()["hwpx"]:
        raise RenderError(f"HWPX→PDF 변환기가 없습니다 — `cd {sc} && npm install && npx playwright install chromium`"
                          "(Node 18 이상 필요, 점검: rfpgen doctor)")
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["node", str(script), str(src), str(dst)]
    for alias in font_aliases or []:
        cmd += ["--font-alias", alias]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0 or not dst.exists():
        raise RenderError(f"HWPX→PDF 변환 실패: {proc.stderr.strip()[-500:]}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def pptx_to_pdf(src: Path, dst: Path, *, timeout: int = 600) -> None:
    if not converters_available()["pptx"]:
        raise RenderError("PPTX→PDF 변환기(LibreOffice soffice)가 없습니다")
    dst.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rfpgen-lo-") as tmp:
        profile = Path(tmp) / "profile"
        out_dir = Path(tmp) / "out"
        env = {**os.environ, "HOME": tmp, "XDG_CACHE_HOME": str(Path(tmp) / "cache")}
        cmd = [soffice_path() or "soffice", f"-env:UserInstallation={profile.as_uri()}", "--headless", "--norestore",
               "--convert-to", "pdf", "--outdir", str(out_dir), str(src)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        produced = out_dir / (src.stem + ".pdf")
        if proc.returncode != 0 or not produced.exists():
            raise RenderError(f"PPTX→PDF 변환 실패: {(proc.stderr or proc.stdout).strip()[-500:]}")
        shutil.move(str(produced), dst)


@dataclass
class PdfInfo:
    path: Path
    pages: int
    size_bytes: int
    fonts: dict[str, str] = field(default_factory=dict)      # 이름 → embedded | type3 | not-embedded
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def unembedded_fonts(self) -> list[str]:
        return [n for n, s in self.fonts.items() if s == "not-embedded"]


def _font_status(font) -> tuple[str, str]:
    subtype = str(font.get("/Subtype", ""))
    name = str(font.get("/BaseFont", "")) or str(font.get("/Name", "")) or subtype
    if subtype == "/Type3":
        return name or "Type3", "type3"
    desc = font.get("/FontDescriptor")
    if desc is None and font.get("/DescendantFonts") is not None:
        desc = font.DescendantFonts[0].get("/FontDescriptor")
    embedded = desc is not None and any(k in desc for k in ("/FontFile", "/FontFile2", "/FontFile3"))
    return name, "embedded" if embedded else "not-embedded"


def inspect_pdf(path: Path) -> PdfInfo:
    import pikepdf

    with pikepdf.open(path) as pdf:
        fonts: dict[str, str] = {}
        for page in pdf.pages:
            res = page.obj.get("/Resources")
            if res is None or res.get("/Font") is None:
                continue
            for _, font in res.Font.items():
                name, status = _font_status(font)
                if fonts.get(name) != "not-embedded":
                    fonts[name] = status
        meta = {str(k): str(v) for k, v in pdf.docinfo.items()} if pdf.docinfo is not None else {}
        return PdfInfo(path=path, pages=len(pdf.pages), size_bytes=path.stat().st_size, fonts=fonts, metadata=meta)


@dataclass
class Bookmark:
    """PDF 책갈피(목차). page는 0부터, level 0이 장."""

    title: str
    page: int
    level: int = 0


def _norm(text: str) -> str:
    return re.sub(r"[\s·ㆍ]+", "", text)


def find_heading_pages(pdf: Path, headings: list[tuple[str, int]]) -> list[Bookmark]:
    """(제목, 단계) 목록을 PDF에서 차례로 찾아 책갈피로 만든다. 제목은 줄 머리에 있어야 하고(본문 속 언급은 건너뜀),
    앞 제목을 찾은 쪽부터 뒤로만 찾는다. 못 찾은 제목은 뺀다."""
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf))
    try:
        pages = []
        for i in range(len(doc)):
            tp = doc[i].get_textpage()
            pages.append([_norm(line) for line in tp.get_text_range().splitlines() if line.strip()])
            tp.close()
    finally:
        doc.close()
    out: list[Bookmark] = []
    start = 0
    for title, level in headings:
        key = _norm(title)
        if not key:
            continue
        # 줄 전체가 제목인 쪽을 먼저 찾고, 없으면(긴 제목이 줄바꿈된 경우) 줄 머리로 찾는다
        hit = next((i for i in range(start, len(pages)) if key in pages[i]), None)
        if hit is None:
            hit = next((i for i in range(start, len(pages)) if any(ln.startswith(key) for ln in pages[i])), None)
        if hit is not None:
            out.append(Bookmark(title=" ".join(title.split()), page=hit, level=level))
            start = hit
    return out


def _set_outline(pdf, bookmarks: list[Bookmark]) -> None:
    import pikepdf

    with pdf.open_outline() as outline:
        outline.root.clear()
        stack: list[tuple[int, pikepdf.OutlineItem]] = []
        for b in bookmarks:
            if not 0 <= b.page < len(pdf.pages):
                continue
            item = pikepdf.OutlineItem(b.title, b.page)
            while stack and stack[-1][0] >= b.level:
                stack.pop()
            (stack[-1][1].children if stack else outline.root).append(item)
            stack.append((b.level, item))
    if bookmarks:
        pdf.Root.PageMode = pikepdf.Name.UseOutlines        # 열면 책갈피 창이 보이게


def clean_pdf(src: Path, dst: Path, *, title: str = "", bookmarks: list[Bookmark] | None = None) -> PdfInfo:
    """작성자·제작 도구·XMP를 지우고 제목만 남긴다(블라인드 평가에서 파일 정보 노출 방지, BLD-003).
    bookmarks를 주면 책갈피(장·절, 서식별)를 넣는다."""
    import pikepdf

    dst.parent.mkdir(parents=True, exist_ok=True)
    with pikepdf.open(src) as pdf:
        for key in list(pdf.docinfo.keys()):
            del pdf.docinfo[key]
        if title:
            pdf.docinfo["/Title"] = title
        if "/Metadata" in pdf.Root:
            del pdf.Root.Metadata
        if bookmarks:
            _set_outline(pdf, bookmarks)
        pdf.save(dst, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
    return inspect_pdf(dst)


def read_bookmarks(path: Path) -> list[tuple[int, str, int]]:
    """(단계, 제목, 쪽 0부터) — 점검·테스트용."""
    import pikepdf

    out: list[tuple[int, str, int]] = []
    with pikepdf.open(path) as pdf:
        pages = {p.objgen: i for i, p in enumerate(pdf.pages)}
        with pdf.open_outline() as outline:
            def walk(items, level):
                for it in items:
                    dest = it.destination
                    page = pages.get(dest[0].objgen, -1) if dest is not None and len(dest) else -1
                    out.append((level, str(it.title), page))
                    walk(it.children, level + 1)
            walk(outline.root, 0)
    return out


__all__ = ["Bookmark", "PdfInfo", "RenderError", "clean_pdf", "converters_available", "find_heading_pages", "hwpx_to_pdf",
           "inspect_pdf", "pptx_to_pdf", "read_bookmarks", "sidecar_dir", "svgs_to_png"]
