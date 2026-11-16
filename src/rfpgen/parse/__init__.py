"""문서 정규화(parse) 단계: 원본 첨부 → DocIR."""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from ..schemas.docir import Document
from .docx import parse_docx_bytes
from .hwp5 import parse_hwp5_bytes
from .hwpx import parse_hwpx_bytes
from .pdf import parse_pdf_bytes
from .safety import UnsafeInputError, check_size, iter_bundle

__all__ = ["InputFile", "UnsafeInputError", "collect_inputs", "detect_format", "parse_document"]

_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


@dataclass
class InputFile:
    name: str
    data: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


def detect_format(name: str, data: bytes) -> str | None:
    """확장자와 파일 서명으로 포맷을 판별한다. 지원하지 않으면 None."""
    ext = Path(name).suffix.lower()
    if data.startswith(b"%PDF"):
        return "pdf"
    if data.startswith(_OLE_MAGIC):
        return "hwp" if ext in (".hwp", "") else None
    if data.startswith(b"PK"):
        if ext in (".hwpx", ".docx", ".zip"):
            return ext[1:]
        # 확장자가 없거나 다르면 패키지 안의 항목으로 판별한다
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                names = set(zf.namelist())
                if "mimetype" in names and zf.read("mimetype")[:40].startswith(b"application/hwp+zip"):
                    return "hwpx"
                if "word/document.xml" in names:
                    return "docx"
                return "zip"
        except zipfile.BadZipFile:
            return None
    return None


def collect_inputs(paths: list[Path]) -> tuple[list[InputFile], list[str]]:
    """경로 목록을 읽고 ZIP 묶음은 풀어서 지원 포맷 파일만 돌려준다."""
    files: list[InputFile] = []
    skipped: list[str] = []
    for path in paths:
        data = path.read_bytes()
        check_size(data, path.name)
        fmt = detect_format(path.name, data)
        if fmt == "zip":
            for member in iter_bundle(data, path.name):
                if detect_format(member.name, member.data) in ("pdf", "hwp", "hwpx", "docx"):
                    files.append(InputFile(member.name, member.data))
                else:
                    skipped.append(f"{path.name}/{member.name}")
        elif fmt:
            files.append(InputFile(path.name, data))
        else:
            skipped.append(path.name)
    return files, skipped


_ROLE_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("제안요청서", re.compile(r"제안\s*요청서|RFP", re.I)),
    ("과업지시서", re.compile(r"과업\s*(지시|내용)서")),
    ("평가기준", re.compile(r"평가\s*(기준|방법|항목)|낙찰자\s*결정")),
    ("입찰공고", re.compile(r"(입찰|긴급|재)?\s*공고(문|서)?")),
    ("별지서식", re.compile(r"별지|서식|양식")),
]


def _classify(doc: Document) -> None:
    head = " ".join(b.text for b in doc.blocks[:15])
    for role, pattern in _ROLE_RULES:
        if pattern.search(doc.filename):
            doc.role = role  # type: ignore[assignment]
            return
    for role, pattern in _ROLE_RULES:
        if pattern.search(head):
            doc.role = role  # type: ignore[assignment]
            return


_PARSERS = {
    "hwpx": parse_hwpx_bytes,
    "hwp": parse_hwp5_bytes,
    "pdf": parse_pdf_bytes,
    "docx": parse_docx_bytes,
}


def parse_document(file: InputFile, doc_id: str) -> Document:
    fmt = detect_format(file.name, file.data)
    if fmt not in _PARSERS:
        raise UnsafeInputError(f"{file.name}: 지원하지 않는 형식입니다")
    doc = Document(doc_id=doc_id, filename=file.name, format=fmt, sha256=file.sha256)  # type: ignore[arg-type]
    _PARSERS[fmt](file.data, doc)
    _classify(doc)
    return doc
