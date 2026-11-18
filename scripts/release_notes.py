# SPDX-License-Identifier: GPL-3.0-or-later
"""릴리스 도우미: 태그와 버전이 맞는지 보고, CHANGELOG.md의 해당 절로 GitHub 릴리스 노트를 만든다.

    python scripts/release_notes.py --check v0.1.0     # 태그·pyproject·__version__·CHANGELOG가 맞는지
    python scripts/release_notes.py v0.1.0 > notes.md  # 릴리스 노트(변경 기록 + 설치 방법)

태그는 v<버전> 또는 사전 릴리스 v<버전>-rc.N 꼴이다. .github/workflows/release.yml이 쓴다.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "BudongJW/auto-rfp-generator"
_TAG = re.compile(r"^v(?P<version>\d+\.\d+\.\d+)(?P<pre>-(?:rc|beta|alpha)\.\d+)?$")


def versions() -> tuple[str, str]:
    """(pyproject 버전, 패키지 __version__)."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    m = re.search(r'__version__\s*=\s*"([^"]+)"', (ROOT / "src" / "rfpgen" / "__init__.py").read_text(encoding="utf-8"))
    return project, m.group(1) if m else ""


def changelog_section(version: str, text: str | None = None) -> str:
    """CHANGELOG.md의 '## [버전]' 절 본문(제목 줄 제외). 없으면 빈 문자열."""
    text = text if text is not None else (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(?P<body>.*?)(?=^## \[|^\[[^\]]+\]:|\Z)", text, re.M | re.S)
    return m.group("body").strip() if m else ""


def check(tag: str) -> list[str]:
    """문제 목록(비면 통과)."""
    problems: list[str] = []
    m = _TAG.match(tag)
    if not m:
        return [f"태그 '{tag}'가 v<버전> 또는 v<버전>-rc.N 꼴이 아닙니다"]
    project, package = versions()
    if m.group("version") != project:
        problems.append(f"태그 버전 {m.group('version')}과 pyproject.toml 버전 {project}가 다릅니다")
    if package != project:
        problems.append(f"src/rfpgen/__init__.py의 __version__ {package}과 pyproject.toml 버전 {project}가 다릅니다")
    if not changelog_section(project):
        problems.append(f"CHANGELOG.md에 '## [{project}]' 절이 없습니다")
    return problems


def notes(tag: str) -> str:
    version = _TAG.match(tag).group("version")  # type: ignore[union-attr]
    wheel = f"rfpgen-{version}-py3-none-any.whl"
    pre = "\n> 사전 릴리스입니다. 다음 정식 버전 전에 명령·파일 형식이 바뀔 수 있습니다.\n" if "-" in tag else ""
    return f"""{pre}
{changelog_section(version)}

## 설치

**전체 기능(PDF 변환 포함)** — 아래 'Source code' 압축을 풀거나 저장소를 받은 뒤 [README](https://github.com/{REPO}/blob/{tag}/README.md)의 설치 순서를 따르세요.

```bash
uv sync
uv run rfpgen setup
```

**분석·초안·서식만** — 휠 파일을 받아 설치하면 `rfpgen` 명령이 생깁니다(PDF 단계는 건너뜀).

```bash
uv tool install ./{wheel}
rfpgen --version
```

변경 기록 전체: [CHANGELOG.md](https://github.com/{REPO}/blob/{tag}/CHANGELOG.md)
""".lstrip()


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "--check":
        problems = check(argv[1])
        for p in problems:
            print(f"✗ {p}", file=sys.stderr)
        if not problems:
            print(f"✓ {argv[1]}: 태그·버전·변경 기록이 맞습니다")
        return 1 if problems else 0
    if len(argv) == 1 and _TAG.match(argv[0]):
        sys.stdout.write(notes(argv[0]))
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
