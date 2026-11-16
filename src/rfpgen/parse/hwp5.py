"""HWP 5.0(.hwp) 파서.

python-hwpx(Apache-2.0)의 HWP5→HWPX 변환기로 OWPML 파트를 만든 뒤 HWPX 파서로 읽는다.
암호·배포용·DRM 문서는 변환되지 않는다.
"""

from __future__ import annotations

from ..schemas.docir import Document
from .hwpx import parse_hwpx_bytes
from .safety import UnsafeInputError, check_size


def parse_hwp5_bytes(data: bytes, doc: Document) -> Document:
    check_size(data, doc.filename)
    try:
        from hwpx.hwp5.errors import Hwp5Error
        from hwpx.hwp5.package import convert, to_hwpx_bytes
    except ImportError as exc:  # pragma: no cover - 의존성 누락
        raise UnsafeInputError("python-hwpx가 설치되지 않아 HWP 파일을 읽을 수 없습니다") from exc
    try:
        converted = convert(data)
    except Hwp5Error as exc:
        # 배포용·암호 문서는 복호화하지 않는다(법률 검토 전 기본 비활성 — docs/analysis/hwpx-rendering-tools.md)
        raise UnsafeInputError(
            f"{doc.filename}: HWP 변환 실패 — {exc}. 배포용·암호 문서라면 한글에서 PDF로 저장해 올려 주세요"
        ) from exc
    report = converted.report
    unconverted = getattr(report, "unconverted", None)
    if unconverted:
        summary = ", ".join(f"{k} x{v}" for k, v in sorted(dict(unconverted).items()))
        doc.warnings.append(f"HWP→HWPX 변환에서 옮기지 못한 내용: {summary}")
    return parse_hwpx_bytes(to_hwpx_bytes(converted.files), doc)
