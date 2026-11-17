"""RFP 구조화(extract) 단계: DocIR → Rfp + 추출 점검 리포트."""

from __future__ import annotations

from ..profile import Profile
from ..schemas.docir import Document
from ..schemas.rfp import ExtractionReport, Rfp
from .ambiguity import annotate_requirements, questions_from_findings
from .compliance import extract_compliance, extract_eligibility, link_compliance_severity
from .evaluation import extract_evaluation
from .guideline import extract_guideline
from .notice import extract_notice
from .requirements import RequirementExtractor

_ROLE_ORDER = {"제안요청서": 0, "평가기준": 1, "과업지시서": 2, "입찰공고": 3, "별지서식": 4, "기타": 5}


def requirement_tables(rfp: Rfp, docs: list[Document]) -> set[str]:
    """요구사항 정의서·총괄표의 표 ID(작성지침·LLM 발췌에서 제외할 표)."""
    by_id = {d.doc_id: {b.id: b for b in d.blocks} for d in docs}
    out: set[str] = set()
    for r in rfp.requirements:
        if r.origin not in ("detail_table", "summary_table"):
            continue
        for lc in r.locators:
            b = by_id.get(lc.doc_id, {}).get(lc.block_id)
            if b is not None and b.parent:
                out.add(b.parent)
    return out


def extract_rfp(docs: list[Document], profile: Profile) -> tuple[Rfp, ExtractionReport]:
    ordered = sorted(docs, key=lambda d: (_ROLE_ORDER.get(d.role, 9), d.doc_id))
    report = ExtractionReport()
    rfp = Rfp(documents=[d.doc_id for d in ordered])
    rfp.notice = extract_notice(ordered, report)
    rfp.evaluation = extract_evaluation(ordered, report)
    extractor = RequirementExtractor(profile.value("requirements.id_regex"))
    rfp.requirements = extractor.extract(ordered, report)
    req_tables = requirement_tables(rfp, ordered)
    rfp.guideline = extract_guideline(ordered, report, skip_tables=req_tables)  # type: ignore[arg-type]
    rfp.compliance = extract_compliance(ordered, profile, report, skip_tables=req_tables)  # type: ignore[arg-type]
    rfp.eligibility = extract_eligibility(ordered, report)
    link_compliance_severity(rfp)
    annotate_requirements(rfp, profile.value("ambiguity.vague_terms"), report)
    questions_from_findings(rfp, report)
    report.stats["requirements"] = len(rfp.requirements)
    report.stats["questions"] = len(rfp.questions)
    for d in ordered:
        for w in d.warnings:
            report.add("PARSE-WARN", "warning", f"{d.filename}: {w}")
    return rfp, report


__all__ = ["extract_rfp", "order_documents", "requirement_tables"]


def order_documents(docs: list[Document]) -> list[Document]:
    return sorted(docs, key=lambda d: (_ROLE_ORDER.get(d.role, 9), d.doc_id))
