"""RFP 구조화 스키마(설계서 6.3절)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .common import Extracted, Locator, Status

ContractMethod = Literal[
    "협상계약", "경쟁적대화", "규격가격동시", "디지털서비스카탈로그", "미확인"
]
EvalKind = Literal["정량", "정성", "미정"]
DetailGrade = Literal["S", "A", "B", "C", "D"]


class Notice(BaseModel):
    bid_no: Extracted[str] | None = None
    title: Extracted[str] | None = None
    agency: Extracted[str] | None = None
    budget_krw: Extracted[int] | None = None
    period: Extracted[str] | None = None
    contract_method: Extracted[ContractMethod] = Field(
        default_factory=lambda: Extracted[ContractMethod](value="미확인", confidence=0.0)
    )


class EvalItem(BaseModel):
    id: str
    name: str
    kind: EvalKind = "미정"
    points: float | None = None
    criteria: list[str] = Field(default_factory=list)
    locators: list[Locator] = Field(default_factory=list)


class EvalArea(BaseModel):
    id: str
    name: str
    kind: EvalKind = "미정"
    points: float | None = None
    items: list[EvalItem] = Field(default_factory=list)
    locators: list[Locator] = Field(default_factory=list)


EvalRuleKind = Literal["감점", "가점", "등급", "산식", "기타"]


class EvalRule(BaseModel):
    """평가 규칙: 제안서가 '답할 대상'이 아니라 점수를 매기는 방법(등급 정의·감점·가점·산식).

    OpenBidKit_Yibiao(AGPL-3.0)의 '평가항목/평가요구 분리' 방식을 한국 평가표 용어로 재구현했다.
    """

    kind: EvalRuleKind
    text: str
    item_id: str | None = None
    locators: list[Locator] = Field(default_factory=list)


class EvaluationTable(BaseModel):
    tech_price_ratio: Extracted[list[int]] | None = None
    areas: list[EvalArea] = Field(default_factory=list)
    rules: list[EvalRule] = Field(default_factory=list)
    declared_totals: list[float] = Field(default_factory=list)
    source_tables: list[str] = Field(default_factory=list)

    def items(self) -> list[EvalItem]:
        return [it for a in self.areas for it in a.items]

    def qualitative_items(self) -> list[EvalItem]:
        return [it for it in self.items() if it.kind == "정성"]


class Requirement(BaseModel):
    id: str
    confidence: float = 1.0
    prefix: str | None = None
    category: str = ""
    name: str = ""
    definition: str = ""
    details: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    source: str = ""
    detail_grade: DetailGrade | None = None
    ambiguities: list[str] = Field(default_factory=list)
    origin: Literal["detail_table", "summary_table", "text_rule", "llm", "human"] = "detail_table"
    locators: list[Locator] = Field(default_factory=list)


TocProduction = Literal["자유서식", "별지서식", "대응표", "증빙첨부", "미정"]


class TocNode(BaseModel):
    number: str
    title: str
    level: int
    production: TocProduction = "미정"
    form_refs: list[str] = Field(default_factory=list)
    children: list[TocNode] = Field(default_factory=list)


class Presentation(BaseModel):
    minutes: int | None = None
    qa_minutes: int | None = None
    pm_must_present: bool | None = None


class RequiredDoc(BaseModel):
    name: str
    form_no: str | None = None
    locators: list[Locator] = Field(default_factory=list)


class WritingGuideline(BaseModel):
    prescribed_toc: Extracted[list[TocNode]] | None = None
    main_page_limit: Extracted[int] | None = None
    summary_page_limit: Extracted[int] | None = None
    presentation_page_limit: Extracted[int] | None = None
    count_exclusions: Extracted[list[str]] | None = None
    paper: Extracted[str] | None = None
    orientation: Extracted[str] | None = None
    min_font_pt: Extracted[float] | None = None
    table_min_font_pt: Extracted[float] | None = None
    editor: Extracted[str] | None = None
    file_format: Extracted[str] | None = None
    total_size_limit_mb: Extracted[int] | None = None
    blind: Extracted[bool] | None = None
    presentation: Extracted[Presentation] | None = None
    required_documents: list[RequiredDoc] = Field(default_factory=list)


ComplianceKind = Literal["입찰무효", "평가제외", "감점", "불이익", "제출유의"]


class ComplianceItem(BaseModel):
    """입찰무효·평가(협상) 제외·감점·불이익 사유와 제출 유의사항.

    origin=stated는 RFP 원문에 적힌 것, suggested는 원문에 없지만 경험상 확인을 권하는 것(G1에서 채택).
    related_check는 제출 전 점검 규칙(설계서 7.8절) 접두어로, 그 규칙의 심각도 근거가 된다.
    """

    kind: ComplianceKind
    text: str
    related_check: str | None = None
    origin: Literal["stated", "suggested"] = "stated"
    method: Literal["rule", "llm", "profile", "human"] = "rule"
    confidence: float = 1.0
    status: Status = "proposed"
    note: str | None = None
    locators: list[Locator] = Field(default_factory=list)


class Question(BaseModel):
    """발주기관 질의서 후보."""

    target: str
    issue: str
    question: str
    locators: list[Locator] = Field(default_factory=list)


class Rfp(BaseModel):
    schema_version: str = "1"
    documents: list[str] = Field(default_factory=list)
    notice: Notice = Field(default_factory=Notice)
    evaluation: EvaluationTable = Field(default_factory=EvaluationTable)
    requirements: list[Requirement] = Field(default_factory=list)
    guideline: WritingGuideline = Field(default_factory=WritingGuideline)
    compliance: list[ComplianceItem] = Field(default_factory=list)
    eligibility: list[Extracted[str]] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)

    def requirement(self, req_id: str) -> Requirement | None:
        for r in self.requirements:
            if r.id == req_id:
                return r
        return None


class Finding(BaseModel):
    """추출 점검 결과(사람이 G1에서 확인할 항목)."""

    code: str
    severity: Literal["error", "warning", "info"]
    message: str
    locators: list[Locator] = Field(default_factory=list)


class ExtractionReport(BaseModel):
    schema_version: str = "1"
    findings: list[Finding] = Field(default_factory=list)
    stats: dict[str, int | float | str] = Field(default_factory=dict)

    def add(self, code: str, severity: str, message: str, locators: list[Locator] | None = None) -> None:
        self.findings.append(
            Finding(code=code, severity=severity, message=message, locators=locators or [])  # type: ignore[arg-type]
        )
