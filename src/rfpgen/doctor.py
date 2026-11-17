"""설치 점검(rfpgen doctor): 기능별로 필요한 도구가 갖춰졌는지 한 번에 본다.

- 분석·초안(HWPX)은 Python 패키지만 있으면 된다.
- PDF·도식 그림은 Node 사이드카(@rhwp/core, Playwright Chromium)가, 장표 PDF는 LibreOffice가 필요하다.
- --full이면 한글 글자가 든 작은 SVG와 HWPX를 실제로 변환해 글꼴까지 확인한다.
API 키는 있는지만 보고 값은 출력하지 않는다.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

from .render.pdf import RenderError, hwpx_to_pdf, playwright_version, sidecar_dir, svgs_to_png


@dataclass
class Check:
    name: str
    status: str            # ok | warn | fail
    detail: str
    needed_for: str
    hint: str = ""


def _run(cmd: list[str], timeout: int = 20) -> str | None:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (proc.stdout or proc.stderr).strip() if proc.returncode == 0 else None


def _pkg(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def run_doctor(full: bool = False) -> list[Check]:
    sc = sidecar_dir()
    install = f"cd {sc} && npm install && npx playwright install chromium"
    out: list[Check] = []

    py_ok = sys.version_info >= (3, 12)
    out.append(Check("Python", "ok" if py_ok else "fail", platform.python_version(), "전체", "" if py_ok else "Python 3.12 이상"))
    for pkg, need in (("python-hwpx", "HWP·HWPX 읽기·쓰기"), ("pdfplumber", "PDF 읽기"), ("python-pptx", "장표"),
                      ("pikepdf", "PDF 후처리"), ("anthropic", "LLM(선택)")):
        v = _pkg(pkg)
        out.append(Check(pkg, "ok" if v else "fail", v or "없음", need, "" if v else "uv sync"))

    node = shutil.which("node")
    node_v = _run(["node", "--version"]) if node else None
    major = int(node_v.lstrip("v").split(".")[0]) if node_v and node_v.lstrip("v")[:1].isdigit() else 0
    out.append(Check("Node", "ok" if major >= 18 else "warn", node_v or "없음", "PDF 변환·도식 그림",
                     "" if major >= 18 else "Node 18 이상 설치"))
    rhwp = sc / "node_modules" / "@rhwp" / "core" / "rhwp.js"
    out.append(Check("@rhwp/core(사이드카)", "ok" if rhwp.exists() else "warn", str(sc) if rhwp.exists() else "없음",
                     "HWPX → PDF", "" if rhwp.exists() else install))
    pw = playwright_version(str(sc))
    out.append(Check("Playwright", "ok" if pw else "warn", pw or "없음", "PDF 인쇄·도식 PNG", "" if pw else install))
    if os.environ.get("RFPGEN_CHROMIUM_PATH"):
        path = Path(os.environ["RFPGEN_CHROMIUM_PATH"])
        out.append(Check("Chromium(RFPGEN_CHROMIUM_PATH)", "ok" if path.exists() else "warn", str(path), "PDF·도식",
                         "" if path.exists() else "경로를 확인하세요"))
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    out.append(Check("LibreOffice", "ok" if soffice else "warn", soffice or "없음", "PPTX → PDF(요약본·발표자료)",
                     "" if soffice else "sudo apt-get install -y libreoffice-impress"))

    if shutil.which("fc-list"):
        fams = _run(["fc-list", ":", "family"]) or ""
        have = [f for f in ("Noto Sans CJK KR", "Noto Serif CJK KR") if f in fams]
        status = "ok" if len(have) == 2 else "warn"
        out.append(Check("한글 글꼴(서버 렌더)", status, ", ".join(have) or "없음", "PDF·도식 글자",
                         "" if status == "ok" else "sudo apt-get install -y fonts-noto-cjk"))
    else:
        out.append(Check("한글 글꼴(서버 렌더)", "warn", "확인 못 함(fc-list 없음)", "PDF·도식 글자",
                         "Noto Sans/Serif CJK KR이 설치돼 있는지 확인"))

    key = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    out.append(Check("Claude API 인증", "ok" if key else "warn", "설정됨" if key else "없음", "--llm(선택)",
                     "" if key else "ANTHROPIC_API_KEY 환경변수(없어도 골격 모드는 동작)"))

    if full:
        out += _full_checks(rhwp.exists() and bool(pw))
    return out


def _full_checks(sidecar_ok: bool) -> list[Check]:
    if not sidecar_ok:
        return [Check("실제 변환 시험", "warn", "건너뜀(사이드카 없음)", "PDF·도식")]
    checks: list[Check] = []
    with tempfile.TemporaryDirectory(prefix="rfpgen-doctor-") as tmp:
        t = Path(tmp)
        svg = t / "t.svg"
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="40" font-family="Noto Sans KR">'
                       '<rect width="100%" height="100%" fill="#fff"/><text x="10" y="26" font-size="16">한글 도식 시험</text>'
                       '</svg>', encoding="utf-8")
        try:
            info = svgs_to_png([(svg, t / "t.png")])
            checks.append(Check("도식 PNG 변환", "ok", f"{info[0]['width_px']}×{info[0]['height_px']}px", "도식 그림"))
        except RenderError as exc:
            checks.append(Check("도식 PNG 변환", "fail", str(exc)[:160], "도식 그림", "rfpgen doctor 항목을 먼저 해결"))
        try:
            from hwpx import HwpxDocument

            doc = HwpxDocument.new()
            doc.add_paragraph("한글 PDF 변환 시험")
            doc.save_to_path(str(t / "t.hwpx"))
            info = hwpx_to_pdf(t / "t.hwpx", t / "t.pdf")
            from .render.pdf import inspect_pdf

            pdf = inspect_pdf(t / "t.pdf")
            bad = [n for n, s in pdf.fonts.items() if s == "not-embedded"]
            checks.append(Check("HWPX → PDF 변환", "ok" if not bad else "warn",
                                f"{info.get('pages')}쪽, 글꼴 {len(pdf.fonts)}개 임베딩", "제출 PDF",
                                "" if not bad else "임베딩되지 않은 글꼴이 있습니다"))
        except (RenderError, OSError) as exc:
            checks.append(Check("HWPX → PDF 변환", "fail", str(exc)[:160], "제출 PDF", "rfpgen doctor 항목을 먼저 해결"))
    return checks


__all__ = ["Check", "run_doctor"]
