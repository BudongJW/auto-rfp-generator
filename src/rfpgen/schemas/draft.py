"""전략·스토리보드와 절 초안 스키마(설계서 6.6절, 7.5~7.6절)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .common import Locator
from .diagram import DiagramKind, DiagramSpec


class SectionPlan(BaseModel):
    """절 하나의 스토리보드(G3에서 사람이 고친다)."""

    section_id: str
    number: str
    title: str
    head_message: str = ""                         # 거버닝 메시지 1문장
    key_points: list[str] = Field(default_factory=list)
    eval_items: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    needed_facts: list[str] = Field(default_factory=list)   # KB에 있어야 할 근거(설명)
    page_budget: int = 0
    target_chars: list[int] = Field(default_factory=list)
    figures: list[DiagramKind] = Field(default_factory=list)  # 넣을 도식 종류(사람이 더하거나 뺀다)


class DataRequest(BaseModel):
    """자료 요청서 한 줄: 스토리보드가 요구하지만 KB에 없는 근거자료."""

    section_id: str
    section_title: str
    need: str
    reason: str = ""
    owner: str = ""
    due: str = ""
    category: str = ""                                   # 실적·인력·인증·재무·회사·기술·기타
    sections: list[str] = Field(default_factory=list)     # 같은 근거를 요구한 절들(묶은 경우)


class Storyboard(BaseModel):
    schema_version: str = "1"
    origin: Literal["skeleton", "llm", "human"] = "skeleton"
    win_themes: list[str] = Field(default_factory=list)
    sections: list[SectionPlan] = Field(default_factory=list)
    data_requests: list[DataRequest] = Field(default_factory=list)

    def plan(self, section_id: str) -> SectionPlan | None:
        return next((s for s in self.sections if s.section_id == section_id), None)


BlockKind = Literal["para", "bullets", "table", "callout", "note", "figure"]


class TableSpec(BaseModel):
    header: list[str]
    rows: list[list[str]]


class DraftBlock(BaseModel):
    kind: BlockKind
    text: str = ""
    level: int = 0                                  # bullets 깊이(□ ○ - ·)
    items: list[str] = Field(default_factory=list)
    table: TableSpec | None = None
    figure: DiagramSpec | None = None
    req_refs: list[str] = Field(default_factory=list)
    fact_refs: list[str] = Field(default_factory=list)


class RequirementResponse(BaseModel):
    req_id: str
    response: str                                   # 대응 방안 요약(대응표의 '제안 내용')
    acceptance: Literal["수용", "부분수용", "대안제시", "미정"] = "수용"


class SectionDraft(BaseModel):
    schema_version: str = "1"
    section_id: str
    number: str
    title: str
    version: int = 1
    origin: Literal["skeleton", "llm", "human"] = "skeleton"
    head_message: str = ""
    blocks: list[DraftBlock] = Field(default_factory=list)
    responses: list[RequirementResponse] = Field(default_factory=list)
    placeholders: list[str] = Field(default_factory=list)
    unresolved_tokens: list[str] = Field(default_factory=list)
    est_chars: int = 0
    rfp_refs: list[Locator] = Field(default_factory=list)
    llm_call_ids: list[str] = Field(default_factory=list)

    def all_text(self, figures: bool = True) -> str:
        """절의 모든 글. figures=False면 도식 속 글을 뺀다(수치 근거 점검·글자 수 추정용)."""
        parts = [self.title, self.head_message]
        for b in self.blocks:
            parts.append(b.text)
            parts.extend(b.items)
            if b.table:
                parts.extend(b.table.header)
                parts.extend(c for row in b.table.rows for c in row)
            if b.figure and figures:
                parts.extend(b.figure.labels())
        parts.extend(r.response for r in self.responses)
        return "\n".join(p for p in parts if p)


class CheckFinding(BaseModel):
    rule: str
    severity: Literal["blocker", "major", "minor", "info"]
    message: str
    section_id: str | None = None
    basis: str = ""                                 # 기준 출처(RFP·프로필·규칙)
    provisional: bool = False                       # 기준이 원문 미대조 값이면 심각도를 한 단계 낮췄음


class CheckReport(BaseModel):
    schema_version: str = "1"
    run_id: str
    findings: list[CheckFinding] = Field(default_factory=list)
    stats: dict[str, int | float | str] = Field(default_factory=dict)

    def count(self, severity: str) -> int:
        return sum(1 for f in self.findings if f.severity == severity)
