"""요구사항 상세화 등급 추정, 모호 표현 표시, 발주기관 질의서 후보 생성.

상세화 등급(S~D)은 SPRi(2017)의 등급 이름을 빌린 **휴리스틱 추정**이다. 원래 등급은
기능점수 산정 가능성을 기준으로 하므로, 여기서는 세부 항목 수·수치·산출정보 유무로 근사한다.
"""

from __future__ import annotations

import re

from ..schemas.rfp import ExtractionReport, Question, Requirement, Rfp

_HAS_NUMBER = re.compile(r"\d+(?:\.\d+)?\s*(?:%|초|분|시간|건|명|개|회|TPS|tps|ms|GB|TB|MB|대|식|이상|이하|이내)")

_TEMPLATES = {
    "quantity": "'{term}' 표현의 대상 범위를 구체적으로 열거해 주시기 바랍니다.",
    "quality": "'{term}'의 판단 기준(목표 수치, 측정 방법)을 제시해 주시기 바랍니다.",
    "process": "'{term}'의 주체·시점·범위를 구체적으로 정해 주시기 바랍니다.",
    "scope": "'{term}'의 범위(현행 대비 변경 대상과 수준)를 구체적으로 제시해 주시기 바랍니다.",
    "detail": "세부 요구 내용(기능 범위, 처리 대상, 목표 수준, 산출물)을 구체적으로 제시해 주시기 바랍니다.",
}


def grade(req: Requirement) -> str:
    text = " ".join([req.definition, *req.details])
    n = len(req.details)
    numbers = bool(_HAS_NUMBER.search(text))
    outputs = bool(req.outputs)
    if n >= 5 and numbers and outputs:
        return "S"
    if n >= 3 and (numbers or outputs):
        return "A"
    if n >= 2:
        return "B"
    if n >= 1 or len(req.definition) >= 20:
        return "C"
    return "D"


def find_vague(text: str, vocab: dict[str, list[str]]) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for kind, terms in vocab.items():
        for term in terms:
            if term == "등":
                if re.search(r"[가-힣A-Za-z)]\s*등(?:\s|$|의|을|를|이|에|과|으로|\.|,)", text):
                    hits.append((kind, term))
            elif term in text:
                hits.append((kind, term))
    return hits


def annotate_requirements(rfp: Rfp, vocab: dict[str, list[str]], report: ExtractionReport) -> None:
    grades: dict[str, int] = {}
    for req in rfp.requirements:
        req.detail_grade = grade(req)  # type: ignore[assignment]
        grades[req.detail_grade] = grades.get(req.detail_grade, 0) + 1
        text = " ".join([req.definition, *req.details])
        hits = find_vague(text, vocab)
        req.ambiguities = sorted({term for _, term in hits})
        strong = [(k, t) for k, t in hits if t != "등"]
        if req.detail_grade in ("C", "D") or len(strong) >= 3:
            kind, term = (strong or hits or [("detail", "")])[0]
            if req.detail_grade in ("C", "D") and not strong:
                kind = "detail"
            issue = f"상세화 등급 {req.detail_grade}" + (f", 모호 표현 {', '.join(req.ambiguities[:4])}" if req.ambiguities else "")
            rfp.questions.append(Question(
                target=req.id,
                issue=issue,
                question=f"[{req.id} {req.name}] " + _TEMPLATES[kind].format(term=term),
                locators=req.locators[:1],
            ))
    for g, n in sorted(grades.items()):
        report.stats[f"grade_{g}"] = n


def questions_from_findings(rfp: Rfp, report: ExtractionReport) -> None:
    """추출 점검에서 나온 RFP 자체의 문제(누락·오타·분량 미기재)를 질의서 후보로 옮긴다."""
    for f in report.findings:
        if f.code == "REQ-ID-TYPO":
            rfp.questions.append(Question(target="요구사항 ID", issue="ID 오타 의심", question=f.message.split(" — ")[0]
                                          + " — 올바른 요구사항 ID를 확인해 주시기 바랍니다.", locators=f.locators))
        elif f.code == "REQ-COUNT-MISMATCH" and f.severity == "error":
            rfp.questions.append(Question(target="요구사항 총괄", issue="선언 수와 정의서 불일치",
                                          question=f.message.split(" — ")[0] + " — 누락된 요구사항 정의서를 확인해 주시기 바랍니다.",
                                          locators=f.locators))
        elif f.code == "REQ-UNKNOWN-REF":
            rfp.questions.append(Question(target="요구사항 ID", issue="정의되지 않은 참조",
                                          question=f.message.split(":")[0] + " 요구사항이 참조되지만 정의서가 없습니다. 해당 요구사항의 내용을 확인해 주시기 바랍니다.",
                                          locators=f.locators))
    g = rfp.guideline
    if g.main_page_limit is None:
        rfp.questions.append(Question(target="제안서 작성요령", issue="분량 제한 불명확",
                                      question="제안서 본문의 분량 제한(쪽수)과 쪽수 산정에서 제외되는 항목(표지·목차·간지 등)을 확인해 주시기 바랍니다."))
    if g.blind is not None and g.blind.confidence < 1.0:
        rfp.questions.append(Question(target="제안서 작성요령", issue="블라인드 평가 여부 미기재",
                                      question="제안서 평가가 블라인드 방식인지, 회사명·로고 표기 제한이 있는지 확인해 주시기 바랍니다."))
