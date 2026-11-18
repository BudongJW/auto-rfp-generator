"""과거 제안서 가져오기(rfpgen kb import): HWP·HWPX·PDF·DOCX 제안서를 절 단위로 잘라 KB의 content/*.md로 넣는다.

- 절은 파서가 판별한 제목(장 'Ⅲ.'·절 '1.')으로 나눈다. 제목이 없으면 'Ⅰ. …'·'1. …' 꼴의 짧은 문단을 쓴다.
- 쪽마다 되풀이되는 머리말·꼬리말 줄은 뺀다.
- 블라인드 대비: KB company.yaml의 회사 식별어(상호·영문명·제품명 등)는 '당사'로, private/people.csv의 실명은
  '○○○'로 바꿔 적는다. 바꾼 횟수를 보고한다(원본 파일은 건드리지 않는다).
- 너무 짧은 절은 건너뛰고, 긴 절은 문단 경계에서 나눈다. 같은 이름의 파일이 있으면 덮어쓰지 않는다(--force 제외).

가져온 문단은 회사 내부 자료다. LLM에는 `--llm-share-kb`를 줄 때만 보낸다(제목·태그는 KB 카탈로그로, 본문은
관련 절에 한해).
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..draft.context import PRIVATE_USE, render_blocks
from ..parse import UnsafeInputError, collect_inputs, parse_document
from ..schemas.docir import Block, Document
from . import load_kb, load_private_names

SECTION_NUM = re.compile(r"^\s*(?:(?:[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]|[IVX]{1,4}|\d{1,2}(?:\.\d{1,2})*)\s*[.)]\s*|\d{1,2}\s+(?=[가-힣A-Za-z]))")
SUBSECTION = re.compile(r"^\s*\d{1,2}(?:\.\d{1,2})*[.)]?\s+[가-힣A-Za-z]")       # '1 추진 목표'(PDF에서 점이 빠진 절 번호)
TOC_LEADER = re.compile(r"[·.…]{4,}\s*\d*\s*$")


@dataclass
class ImportedSection:
    path: Path
    title: str
    chars: int
    masked: int


@dataclass
class ImportResult:
    written: list[ImportedSection] = field(default_factory=list)
    skipped_short: int = 0
    skipped_existing: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def masked(self) -> int:
        return sum(s.masked for s in self.written)


def _title(text: str) -> str:
    return SECTION_NUM.sub("", " ".join(text.split())).strip(" .")


def _tag(text: str) -> str:
    return re.sub(r"[\s·ㆍ,./()\[\]]+", "", _title(text))


def _slug(text: str, limit: int = 30) -> str:
    s = re.sub(r"[^\w가-힣]+", "_", text).strip("_")
    return s[:limit] or "절"


def _boundaries(doc: Document) -> list[int]:
    """절이 시작하는 블록 위치(장·절 제목). 제목 판별이 없으면 번호 붙은 짧은 문단."""
    heads = [i for i, b in enumerate(doc.blocks)
             if b.kind == "heading" and (b.level or 1) <= 2 and not TOC_LEADER.search(b.text)]
    if any((doc.blocks[i].level or 1) == 2 for i in heads):
        return heads
    # 절 제목을 판별하지 못한 문서(장만 있거나 제목이 전혀 없음): 번호 붙은 짧은 문단을 절로 본다
    subs = [i for i, b in enumerate(doc.blocks)
            if b.kind == "para" and len(b.text.strip()) <= 30 and (SUBSECTION.match(b.text) or SECTION_NUM.match(b.text))
            and not TOC_LEADER.search(b.text)]
    return sorted(set(heads) | set(subs))


def _repeated_lines(doc: Document) -> set[str]:
    """여러 쪽에 되풀이되는 짧은 줄(머리말·꼬리말·사업명 띠)."""
    pages: dict[str, set[int]] = {}
    for b in doc.blocks:
        t = " ".join(b.text.split())
        if b.kind in ("para", "heading") and t and len(t) <= 60 and b.page is not None:
            pages.setdefault(t, set()).add(b.page)
    return {t for t, ps in pages.items() if len(ps) >= 3}


def _mask(text: str, terms: list[str], names: list[str]) -> tuple[str, int]:
    n = 0
    for term in terms:                                   # 긴 것부터(terms()가 길이순)
        text, k = re.subn(re.escape(term), "당사", text)
        n += k
    for name in names:
        text, k = re.subn(re.escape(name), "○○○", text)
        n += k
    return text, n


def _split(lines: list[str], max_chars: int) -> list[list[str]]:
    parts, cur, size = [], [], 0
    for line in lines:
        if cur and size + len(line) > max_chars:
            parts.append(cur)
            cur, size = [], 0
        cur.append(line)
        size += len(line) + 1
    if cur:
        parts.append(cur)
    return parts


def sections_of(doc: Document) -> list[tuple[str, str, list[str]]]:
    """(장 제목, 절 제목, 본문 줄) 목록."""
    bounds = _boundaries(doc)
    noise = _repeated_lines(doc)
    out: list[tuple[str, str, list[str]]] = []
    chapter = ""
    for k, start in enumerate(bounds):
        head: Block = doc.blocks[start]
        end = bounds[k + 1] if k + 1 < len(bounds) else len(doc.blocks)
        if head.kind == "heading" and (head.level or 1) == 1:
            chapter = _title(head.text)                  # 장 제목은 아래 절들의 태그가 된다
        body = []
        for line in render_blocks(doc.blocks[start + 1:end]):
            line = PRIVATE_USE.sub("", line).strip()
            if line and line not in noise:
                body.append(line)
        out.append((chapter, _title(head.text), body))
    return out


def import_proposals(paths: list[Path], kb_dir: Path, *, won: bool | None = None, min_chars: int = 200,
                     max_chars: int = 4000, force: bool = False) -> ImportResult:
    kb_dir = Path(kb_dir)
    kb = load_kb(kb_dir)
    terms = kb.identity.terms()
    names = sorted({n for n in load_private_names(kb_dir).values() if len(n.strip()) >= 2}, key=len, reverse=True)
    out_dir = kb_dir / "content"
    out_dir.mkdir(parents=True, exist_ok=True)
    res = ImportResult()
    files, skipped = collect_inputs(paths)
    res.errors += [f"{s}: 지원하지 않는 형식이라 건너뜀" for s in skipped]
    for n, f in enumerate(files, start=1):
        try:
            doc = parse_document(f, f"p{n:02d}")
        except (UnsafeInputError, ValueError, OSError) as exc:
            res.errors.append(f"{f.name}: {exc}")
            continue
        source = Path(f.name).stem
        seq = Counter()
        for chapter, title, body in sections_of(doc):
            text = "\n".join(body)
            if len(text) < min_chars or not title:
                res.skipped_short += 1
                continue
            parts = _split(body, max_chars)
            for i, part in enumerate(parts, start=1):
                part_title = title + (f" ({i}/{len(parts)})" if len(parts) > 1 else "")
                masked_text, n_masked = _mask("\n".join(part), terms, names)
                masked_title, n_title = _mask(part_title, terms, names)
                seq[source] += 1
                path = out_dir / f"{_slug(source, 24)}_{seq[source]:02d}_{_slug(title)}.md"
                if path.exists() and not force:
                    res.skipped_existing.append(path)
                    continue
                key = hashlib.sha1(f"{source}|{seq[source]}|{title}".encode()).hexdigest()[:6]
                tags = [t for t in dict.fromkeys([_tag(title), _tag(chapter)]) if t]
                meta = {"id": f"K-{key}", "title": masked_title, "tags": tags, "source": _mask(f.name, terms, names)[0]}
                if won is not None:
                    meta["won"] = won
                front = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
                path.write_text(f"---\n{front}\n---\n{masked_text}\n", encoding="utf-8")
                res.written.append(ImportedSection(path=path, title=masked_title, chars=len(masked_text),
                                                   masked=n_masked + n_title))
    return res


__all__ = ["ImportResult", "ImportedSection", "import_proposals", "sections_of"]
