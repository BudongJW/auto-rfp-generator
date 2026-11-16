"""정규화 문서 표현(DocIR).

HWP·HWPX·PDF·DOCX를 하나의 블록 목록으로 정규화한다. 요구사항 정의서와
평가표가 모두 표이므로 셀 병합 정보까지 보존하는 것이 핵심이다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

BlockKind = Literal["heading", "para", "table", "cell"]
DocFormat = Literal["hwpx", "hwp", "pdf", "docx"]
DocRole = Literal["제안요청서", "과업지시서", "입찰공고", "평가기준", "별지서식", "기타"]


class TableRef(BaseModel):
    """셀 블록이 속한 표와 그 안의 위치(0부터 시작)."""

    table_id: str
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1


class TableInfo(BaseModel):
    """표 블록의 크기."""

    rows: int
    cols: int


class Block(BaseModel):
    id: str
    kind: BlockKind
    text: str = ""
    level: int | None = None
    page: int | None = None
    numbering: str | None = None
    style: str | None = None
    parent: str | None = None
    table: TableInfo | None = None
    cell: TableRef | None = None


class Document(BaseModel):
    schema_version: str = "1"
    doc_id: str
    filename: str
    format: DocFormat
    sha256: str
    role: DocRole = "기타"
    blocks: list[Block] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def block(self, block_id: str) -> Block:
        for b in self.blocks:
            if b.id == block_id:
                return b
        raise KeyError(block_id)

    def tables(self) -> list[Block]:
        return [b for b in self.blocks if b.kind == "table"]

    def cells(self, table_id: str) -> list[Block]:
        return [b for b in self.blocks if b.kind == "cell" and b.cell and b.cell.table_id == table_id]

    def text_blocks(self) -> list[Block]:
        """표 밖의 본문 블록(제목·문단)."""
        return [b for b in self.blocks if b.kind in ("heading", "para")]
