"""처음 설치(rfpgen setup): PDF·도식 변환에 필요한 Node 사이드카와 Chromium을 설치하고, 운영체제에 맞춰
LibreOffice·한글 글꼴 설치 방법을 알려 준다. 시스템 패키지(관리자 권한이 드는 것)는 직접 설치하지 않는다.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .render.pdf import playwright_version, sidecar_dir, soffice_path

GUIDES: dict[str, dict[str, str]] = {
    "node": {
        "Windows": "winget install OpenJS.NodeJS.LTS   (또는 https://nodejs.org 에서 LTS 설치)",
        "Darwin": "brew install node   (또는 https://nodejs.org 에서 LTS 설치)",
        "Linux": "https://nodejs.org 의 안내로 Node 18 이상 설치(배포판 기본 nodejs가 18보다 낮을 수 있음)",
    },
    "libreoffice": {
        "Windows": "winget install TheDocumentFoundation.LibreOffice   (또는 https://www.libreoffice.org)",
        "Darwin": "brew install --cask libreoffice   (또는 https://www.libreoffice.org)",
        "Linux": "sudo apt-get install -y libreoffice-impress",
    },
    "fonts": {
        "Windows": "Noto Sans KR·Noto Serif KR 설치: https://fonts.google.com/noto/specimen/Noto+Sans+KR",
        "Darwin": "Noto Sans KR·Noto Serif KR 설치: https://fonts.google.com/noto/specimen/Noto+Sans+KR",
        "Linux": "sudo apt-get install -y fonts-noto-cjk",
    },
}


@dataclass
class SetupResult:
    ok: bool
    lines: list[str]


def _guide(tool: str) -> str:
    system = platform.system()
    return GUIDES[tool].get(system, GUIDES[tool]["Linux"])


def _fonts_ok() -> bool | None:
    if not shutil.which("fc-list"):
        return None                       # Windows·macOS: 확인할 도구가 없다
    try:
        fams = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    return all(any(name in fams for name in (f"Noto {kind} CJK KR", f"Noto {kind} KR")) for kind in ("Sans", "Serif"))


def run_setup(*, dry_run: bool = False, browser: bool = True,
              runner: Callable[[list[str], Path], int] | None = None) -> SetupResult:
    """설치 단계를 차례로 실행한다. runner(cmd, cwd) → 종료 코드(테스트에서 바꿔 끼운다)."""
    sc = sidecar_dir()
    lines: list[str] = []
    ok = True

    def run(cmd: list[str], cwd: Path) -> bool:
        lines.append(f"$ {' '.join(cmd)}   (위치: {cwd})")
        if dry_run:
            return True
        if runner is not None:
            return runner(cmd, cwd) == 0
        exe = shutil.which(cmd[0]) or cmd[0]            # Windows의 npm.cmd·npx.cmd도 찾는다
        try:
            return subprocess.run([exe, *cmd[1:]], cwd=cwd, timeout=1800).returncode == 0
        except (OSError, subprocess.TimeoutExpired) as exc:
            lines.append(f"  실패: {exc}")
            return False

    # 1. Node 사이드카(rhwp, Playwright)
    if not (shutil.which("node") and shutil.which("npm")):
        ok = False
        lines += ["✗ Node.js(18 이상)가 없습니다 — PDF 변환·도식 그림에 필요합니다", f"  → {_guide('node')}",
                  "  설치한 뒤 `rfpgen setup`을 다시 실행하세요"]
    elif not (sc / "package.json").exists():
        ok = False
        lines.append(f"✗ 사이드카 폴더를 찾지 못했습니다: {sc} — 저장소를 통째로 내려받았는지 확인하세요(RFPGEN_SIDECAR_DIR)")
    else:
        lines.append("1) Node 사이드카 설치(rhwp·Playwright)")
        npm = ["npm", "ci"] if (sc / "package-lock.json").exists() else ["npm", "install"]
        if not run(npm, sc):
            ok = False
            lines.append("  ✗ npm 설치 실패 — 네트워크(npm 레지스트리 접속)를 확인하세요")
        elif browser and not os.environ.get("RFPGEN_CHROMIUM_PATH"):
            lines.append("2) Chromium 내려받기(Playwright)")
            if not run(["npx", "playwright", "install", "chromium"], sc):
                ok = False
                lines.append("  ✗ Chromium 설치 실패 — 리눅스는 "
                             "`sudo npx playwright install-deps chromium`이 더 필요할 수 있습니다")
        playwright_version.cache_clear()

    # 2. LibreOffice(장표 PDF)
    if soffice_path() is None:
        lines += ["! LibreOffice가 없습니다 — 요약본·발표자료 PDF 변환에 필요합니다(본문 HWPX·PDF는 없어도 됩니다)",
                  f"  → {_guide('libreoffice')}"]
    else:
        lines.append(f"✓ LibreOffice: {soffice_path()}")

    # 3. 한글 글꼴(서버 렌더)
    fonts = _fonts_ok()
    if fonts is False or fonts is None:
        lines += ["! 한글 글꼴(Noto Sans·Serif KR)을 확인하지 못했습니다" if fonts is None else
                  "! 한글 글꼴(Noto Sans·Serif CJK KR)이 없습니다 — PDF·도식 글자가 다른 글꼴로 바뀔 수 있습니다",
                  f"  → {_guide('fonts')}"]
    else:
        lines.append("✓ 한글 글꼴")
    lines.append("마지막으로 `rfpgen doctor --full`로 실제 변환까지 확인하세요")
    return SetupResult(ok=ok, lines=lines)


__all__ = ["GUIDES", "SetupResult", "run_setup"]
