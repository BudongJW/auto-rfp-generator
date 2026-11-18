"""신뢰할 수 없는 첨부를 다룰 때의 제한값과 안전한 XML·ZIP 처리(설계서 7.2절, 12.2절)."""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass

from lxml import etree

MAX_FILE_BYTES = 200 * 1024 * 1024        # 입력 파일 하나의 최대 크기
MAX_ZIP_ENTRIES = 2_000                   # ZIP 안 파일 수
MAX_ZIP_TOTAL_BYTES = 512 * 1024 * 1024   # ZIP 해제 총 크기
MAX_ZIP_RATIO = 200                       # 압축률(해제/압축) 상한 — ZIP 폭탄 방어
MAX_XML_PART_BYTES = 64 * 1024 * 1024     # HWPX 섹션 XML 하나의 최대 크기


class UnsafeInputError(ValueError):
    """제한을 넘거나 형식이 의심스러운 입력."""


def check_size(data: bytes, name: str) -> None:
    if len(data) > MAX_FILE_BYTES:
        raise UnsafeInputError(f"{name}: 파일이 너무 큽니다({len(data):,} bytes)")


def safe_xml_parser() -> etree.XMLParser:
    """외부 엔티티·DTD·네트워크 접근을 막은 파서."""
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        huge_tree=False,
        remove_blank_text=False,
    )


def parse_xml(data: bytes) -> etree._Element:
    if len(data) > MAX_XML_PART_BYTES:
        raise UnsafeInputError("XML 파트가 너무 큽니다")
    return etree.fromstring(data, parser=safe_xml_parser())


@dataclass
class ZipMember:
    name: str
    data: bytes


def _decode_name(info: zipfile.ZipInfo) -> str:
    """UTF-8 플래그가 없는 한국어 ZIP 파일명(CP949)을 복원한다."""
    if info.flag_bits & 0x800:
        return info.filename
    try:
        return info.filename.encode("cp437").decode("cp949")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return info.filename


def open_zip(data: bytes, name: str) -> zipfile.ZipFile:
    check_size(data, name)
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise UnsafeInputError(f"{name}: ZIP 형식이 아닙니다") from exc
    infos = zf.infolist()
    if len(infos) > MAX_ZIP_ENTRIES:
        raise UnsafeInputError(f"{name}: ZIP 항목이 너무 많습니다({len(infos)})")
    total = sum(i.file_size for i in infos)
    if total > MAX_ZIP_TOTAL_BYTES:
        raise UnsafeInputError(f"{name}: ZIP 해제 크기가 너무 큽니다({total:,} bytes)")
    for i in infos:
        if i.compress_size and i.file_size / max(i.compress_size, 1) > MAX_ZIP_RATIO and i.file_size > 1024 * 1024:
            raise UnsafeInputError(f"{name}: 압축률이 비정상적입니다({i.filename})")
    return zf


def read_member(zf: zipfile.ZipFile, member: str) -> bytes:
    info = zf.getinfo(member)
    if info.file_size > MAX_XML_PART_BYTES:
        raise UnsafeInputError(f"{member}: 파트가 너무 큽니다")
    return zf.read(info)


def iter_bundle(data: bytes, name: str) -> list[ZipMember]:
    """공고 첨부 묶음 ZIP에서 파일들을 꺼낸다(디스크에 풀지 않는다)."""
    zf = open_zip(data, name)
    out: list[ZipMember] = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        decoded = _decode_name(info)
        base = decoded.replace("\\", "/").rsplit("/", 1)[-1]
        if not base or base.startswith("."):
            continue
        out.append(ZipMember(name=base, data=zf.read(info)))
    return out
