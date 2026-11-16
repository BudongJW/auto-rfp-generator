"""계획 산출물: 목차, 쪽수 예산, 추적표(설계서 6.4절)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .common import Locator

OutlineOrigin = Literal["prescribed", "eval_table", "default_template", "fixed", "human"]


class OutlineNode(BaseModel):
    id: str
    number: str
    title: str
    level: int
    canonical: str | None = None
    eval_items: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    points: float = 0.0
    page_budget: int = 0
    checklist: list[str] = Field(default_factory=list)
    origin: OutlineOrigin = "default_template"
    children: list[OutlineNode] = Field(default_factory=list)

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()


class Outline(BaseModel):
    schema_version: str = "1"
    origin: OutlineOrigin
    chapters: list[OutlineNode] = Field(default_factory=list)

    def walk(self):
        for ch in self.chapters:
            yield from ch.walk()

    def node(self, node_id: str) -> OutlineNode | None:
        for n in self.walk():
            if n.id == node_id:
                return n
        return None


class BudgetLine(BaseModel):
    node_id: str
    number: str
    title: str
    points: float
    raw: float
    pages: int


class PageBudget(BaseModel):
    schema_version: str = "1"
    main_page_limit: int
    main_page_limit_source: str
    fixed_pages: int
    distributable_pages: int
    qualitative_points: float
    lines: list[BudgetLine] = Field(default_factory=list)


class TraceRow(BaseModel):
    req_id: str
    req_name: str
    category: str
    eval_item: str | None = None
    sections: list[str] = Field(default_factory=list)
    summary: str = ""
    acceptance: Literal["수용", "부분수용", "대안제시", "미정"] = "미정"
    pages: list[int] = Field(default_factory=list)
    rfp_locators: list[Locator] = Field(default_factory=list)
    status: Literal["unmapped", "mapped", "drafted", "verified"] = "unmapped"
    mapping_reason: str = ""


class Trace(BaseModel):
    schema_version: str = "1"
    rows: list[TraceRow] = Field(default_factory=list)

    def coverage(self) -> float:
        if not self.rows:
            return 0.0
        return sum(1 for r in self.rows if r.status != "unmapped") / len(self.rows)
