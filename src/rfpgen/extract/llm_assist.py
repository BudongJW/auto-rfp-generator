"""LLM 보조 추출(설계서 7.3절 B·C).

결정적 추출이 끝난 뒤 세 과제를 돈다. 모든 결과는 인용 검증(블록 ID·원문 대조·숫자 대조)을
통과한 것만 받아들이고, method="llm"·status="proposed"로 넣어 G1에서 사람이 확정한다.

1. guideline: 결정적 패스가 비워 둔 작성지침 필드를 채우고, 이미 있는 값과 다르면 충돌로 보고한다.
2. compliance: 입찰무효·평가제외·감점 사유와 참가자격을 보강한다. 원문에 없는 권고는 따로 둔다.
3. text_requirements: 요구사항 ID 없이 문장으로만 적힌 요구사항을 찾는다(X-0001…).

compliance·text_requirements는 같은 입력으로 두 번 돌려(두 번째는 프롬프트 캐시를 읽는다), 한쪽에만
나온 항목은 불안정으로 표시한다(Yu et al. 2026: 같은 파일에서 추출 개수가 68↔51로 흔들림).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel

from .._third_party.agpl.openbidkit_yibiao import COMPLIANCE_INSTRUCTION, GUIDELINE_INSTRUCTION
from ..llm import (
    BlockIndex,
    LLMCall,
    LLMError,
    LLMGateway,
    LLMRefusal,
    keyword_excerpt,
    normalize_for_match,
    number_in_quote,
    verify_evidence,
)
from ..llm.prompts import SYSTEM, TEXT_REQUIREMENTS_INSTRUCTION
from ..profile import Profile
from ..schemas.common import Extracted, Locator
from ..schemas.docir import Block, Document
from ..schemas.rfp import ComplianceItem, ExtractionReport, Presentation, Requirement, Rfp
from .ambiguity import annotate_requirements
from .guideline import _BLIND_NEG, _EXCL, _PAPER

# ---- 응답 스키마 -------------------------------------------------------------------


class Evidence(BaseModel):
    block_id: str
    quote: str


GuidelineFieldName = Literal[
    "main_page_limit", "summary_page_limit", "presentation_page_limit", "count_exclusions", "paper",
    "orientation", "min_font_pt", "table_min_font_pt", "editor", "file_format", "total_size_limit_mb",
    "blind", "presentation_minutes", "qa_minutes", "pm_must_present",
]


class GuidelineFieldOut(BaseModel):
    field: GuidelineFieldName
    value_text: str
    evidence: list[Evidence]


class GuidelineOut(BaseModel):
    fields: list[GuidelineFieldOut]
    manual: list[str]
    notes: str


class ConditionOut(BaseModel):
    category: Literal["입찰무효", "평가제외", "감점", "불이익"]
    text: str
    consequence: str
    legal_ref_in_text: str | None
    evidence: list[Evidence]


class EligibilityOut(BaseModel):
    text: str
    evidence: list[Evidence]


class SuggestedCheckOut(BaseModel):
    text: str
    reason: str


class ComplianceOut(BaseModel):
    conditions: list[ConditionOut]
    eligibility: list[EligibilityOut]
    suggested_checks: list[SuggestedCheckOut]
    notes: str


RequirementCategory = Literal["기능", "성능", "보안", "데이터", "인터페이스", "테스트", "품질", "제약",
                              "프로젝트 관리", "프로젝트 지원", "기타"]


class TextRequirementOut(BaseModel):
    name: str
    category: RequirementCategory
    statement: str
    evidence: list[Evidence]


class TextRequirementsOut(BaseModel):
    requirements: list[TextRequirementOut]
    notes: str


# ---- 공통 ----------------------------------------------------------------------------

_GUIDE_KEYWORDS = re.compile(
    r"제안서\s*(?:작성|분량|규격|형식|제출)|작성\s*(?:요령|지침|방법)|분량|쪽\s*이내|페이지\s*이내|매\s*이내|요약\s*(?:본|제안서)"
    r"|글자\s*크기|글씨|폰트|서체|포인트|\bpt\b|용지|A4|A3|가로|세로|PDF|pdf|용량|MB|블라인드|업체\s*정보|발표\s*(?:시간|자료)"
    r"|질의\s*응답|한글\s*(?:프로그램|파일)|HWP")
_COMPLIANCE_KEYWORDS = re.compile(
    r"무효|효력이?\s*없|제외|감점|불이익|실격|부적격|탈락|참가\s*자격|입찰\s*자격|자격\s*요건|공동\s*수급|하도급|허위|블라인드|서약|확약")
_OBLIGATION = re.compile(r"하여야\s*(?:한다|함|하며|하고|할)|해야\s*(?:한다|함|하며)|할\s*것|하도록\s*(?:한다|함)|토록\s*함|하여야\s*하는")
_NOT_REQUIREMENT_CONTEXT = re.compile(r"제안서|입찰|평가위원|평가\s*(?:항목|기준|방법)|제출\s*(?:서류|기한)|낙찰|협상|계약\s*체결")


def _excerpt_context(text: str) -> str:
    return f"<excerpts>\n{text}\n</excerpts>"


def _locators(index: BlockIndex, evidence: list[Evidence], allowed: set[str]) -> tuple[list[Locator], int]:
    locs: list[Locator] = []
    rejected = 0
    for ev in evidence:
        lc = verify_evidence(index, ev.block_id, ev.quote, allowed)
        if lc is None:
            rejected += 1
        else:
            locs.append(lc)
    return locs, rejected


def _similar(a: str, b: str) -> float:
    from ..plan.outline import similarity  # 순환 import 방지

    return similarity(a, b)


class _Runner:
    def __init__(self, gateway: LLMGateway, docs: list[Document], report: ExtractionReport, profile: Profile) -> None:
        self.gateway = gateway
        self.docs = docs
        self.report = report
        self.index = BlockIndex(docs)
        self.tasks = profile.value("llm.tasks")
        self.max_chars = int(profile.value("llm.excerpt_max_chars"))

    def call(self, task: str, context: str, instruction: str, schema: type[BaseModel]):
        spec = self.tasks[task]
        results = []
        for _ in range(int(spec.get("runs", 1))):
            seen = len(self.gateway.retries)
            data, _reply = self.gateway.run(
                LLMCall(task=f"extract.{task}", system=SYSTEM, context=context, instruction=instruction,
                        schema=schema, effort=spec["effort"], max_tokens=int(spec["max_tokens"])), schema)
            for msg in self.gateway.retries[seen:]:          # 게이트웨이가 잘림 뒤 상한을 늘려 다시 보냈다
                self.report.add("LLM-RETRY", "info", msg)
            results.append(data)
        return results

    def excerpt(self, task: str, pattern, skip: set[str]):
        ex = keyword_excerpt(self.docs, pattern, max_chars=self.max_chars, skip_tables=skip)
        if ex.truncated:
            self.report.add("LLM-CONTEXT-TRUNCATED", "warning",
                            f"{task}: 발췌가 {self.max_chars:,}자를 넘어 뒷부분을 보내지 못했습니다 — llm.excerpt_max_chars를 늘리거나 문서를 나눠 넣으세요")
        return ex


# ---- 1. 작성지침 ----------------------------------------------------------------------

_NUMERIC_FIELDS = {
    "main_page_limit": (1, 1000, int), "summary_page_limit": (1, 1000, int), "presentation_page_limit": (1, 1000, int),
    "min_font_pt": (6, 30, float), "table_min_font_pt": (6, 30, float), "total_size_limit_mb": (1, 2000, int),
    "presentation_minutes": (1, 180, int), "qa_minutes": (1, 180, int),
}


def _convert_guideline(field: str, value_text: str, quote: str) -> tuple[object | None, str | None]:
    """원문 표기를 값으로 바꾸고, 근거 인용과 맞는지 확인한다. (값, 거부 사유)."""
    if field in _NUMERIC_FIELDS:
        lo, hi, cast = _NUMERIC_FIELDS[field]
        m = re.search(r"\d+(?:\.\d+)?", value_text.replace(",", ""))
        if not m:
            return None, "값에 숫자가 없음"
        n = float(m.group(0))
        if not lo <= n <= hi:
            return None, f"범위 밖({n:g})"
        if not number_in_quote(n, quote):
            return None, f"숫자 {n:g}가 인용문에 없음"
        if field == "total_size_limit_mb" and not re.search(r"MB|메가", quote, re.I):
            return None, "인용문에 용량 단위가 없음"
        if field in ("presentation_minutes", "qa_minutes") and "분" not in quote:
            return None, "인용문에 '분'이 없음"
        return cast(n), None
    if field == "count_exclusions":
        found = [w for w in _EXCL if w in quote]
        found = [w for w in found if not any(w != o and w in o for o in found)]
        return (found, None) if found and "제외" in quote else (None, "인용문에 제외 항목이 없음")
    if field == "paper":
        m = _PAPER.search(quote)
        return (m.group(1).upper(), None) if m else (None, "인용문에 용지 규격이 없음")
    if field == "orientation":
        if "가로" in quote and "세로" not in quote:
            return "landscape", None
        if "세로" in quote and "가로" not in quote:
            return "portrait", None
        return None, "인용문에서 방향을 정할 수 없음"
    if field == "file_format":
        return ("PDF", None) if re.search(r"pdf", quote, re.I) else (None, "인용문에 PDF가 없음")
    if field == "editor":
        v = value_text.strip()[:30]
        return (v, None) if v and normalize_for_match(v) in normalize_for_match(quote) else (None, "인용문에 편집기 표기가 없음")
    if field == "blind":
        if _BLIND_NEG.search(quote):
            return False, None
        if re.search(r"블라인드|업체\s*(?:명|정보)|회사\s*명|로고|식별", quote):
            return (False, None) if value_text.strip().lower() in ("false", "아니오", "no") else (True, None)
        return None, "인용문에 블라인드 관련 표현이 없음"
    if field == "pm_must_present":
        return (True, None) if re.search(r"PM|책임자", quote) and "발표" in quote else (None, "인용문에 PM 발표 요건이 없음")
    return None, "알 수 없는 필드"


def assist_guideline(run: _Runner, rfp: Rfp, skip: set[str]) -> None:
    ex = run.excerpt("guideline", _GUIDE_KEYWORDS, skip)
    if not ex.block_ids:
        return
    (out,) = run.call("guideline", _excerpt_context(ex.text), GUIDELINE_INSTRUCTION, GuidelineOut)[:1]
    g = rfp.guideline
    added, rejected = [], []
    presentation = g.presentation.value.model_copy() if g.presentation else Presentation()
    pres_locs = list(g.presentation.locators) if g.presentation else []
    pres_changed = False
    for f in out.fields:
        locs, _ = _locators(run.index, f.evidence, ex.block_ids)
        if not locs:
            rejected.append(f"{f.field}(근거 불일치)")
            continue
        value, why = _convert_guideline(f.field, f.value_text, locs[0].quote)
        if why is not None:
            rejected.append(f"{f.field}({why})")
            continue
        if f.field in ("presentation_minutes", "qa_minutes", "pm_must_present"):
            attr = {"presentation_minutes": "minutes", "qa_minutes": "qa_minutes", "pm_must_present": "pm_must_present"}[f.field]
            if getattr(presentation, attr) is None:
                setattr(presentation, attr, value)
                pres_locs.extend(locs)
                pres_changed = True
                added.append(f.field)
            elif getattr(presentation, attr) != value:
                run.report.add("LLM-GUIDE-CONFLICT", "warning",
                               f"작성지침 {f.field}: 규칙 {getattr(presentation, attr)} ↔ LLM {value} — 원문 확인 필요", locs)
            continue
        current = getattr(g, f.field)
        weak = current is not None and current.confidence < 1.0  # 예: '블라인드 문구 없음'으로 둔 기본값
        if current is None or weak:
            setattr(g, f.field, Extracted(value=value, locators=locs, method="llm", confidence=0.8,
                                          note="LLM 보조 추출 — G1에서 확인"))
            added.append(f.field)
        elif current.value != value:
            run.report.add("LLM-GUIDE-CONFLICT", "warning",
                           f"작성지침 {f.field}: 규칙 추출값 {current.value} ↔ LLM {value} — 규칙 값을 유지합니다. 원문 확인 필요",
                           current.locators[:1] + locs[:1])
    if pres_changed:
        g.presentation = Extracted(value=presentation, locators=pres_locs, method="llm", confidence=0.8)
    if added:
        run.report.add("LLM-GUIDE-ADDED", "info", f"LLM이 근거와 함께 채운 작성지침 필드: {', '.join(added)}")
        run.report.findings = [x for x in run.report.findings
                               if not (x.code == "GUIDE-PAGE-MISSING" and g.main_page_limit is not None)]
    if rejected:
        run.report.add("LLM-REJECTED", "info", f"근거 검증에서 버린 작성지침 값: {', '.join(rejected)}")
    for line in out.manual[:20]:
        run.report.add("LLM-GUIDE-MANUAL", "info", f"필드로 표현할 수 없는 작성 요건: {line[:120]}")


# ---- 2. 무효·감점 사유와 참가자격 ---------------------------------------------------------


def _match_runs(runs: list[list[tuple[str, list[Locator]]]]) -> list[tuple[int, tuple[str, list[Locator]]]]:
    """실행별 (텍스트, 근거) 목록을 합친다. 돌려주는 값은 (등장한 실행 수, 대표 항목)."""
    merged: list[tuple[int, tuple[str, list[Locator]]]] = []
    for items in runs:
        seen_this_run: set[int] = set()
        for text, locs in items:
            blocks = {lc.block_id for lc in locs}
            hit = None
            for i, (_, (t2, l2)) in enumerate(merged):
                if i in seen_this_run:
                    continue
                if blocks & {lc.block_id for lc in l2} or _similar(text, t2) >= 0.6:
                    hit = i
                    break
            if hit is None:
                merged.append((1, (text, locs)))
                seen_this_run.add(len(merged) - 1)
            else:
                n, item = merged[hit]
                merged[hit] = (n + 1, item)
                seen_this_run.add(hit)
    return merged


def assist_compliance(run: _Runner, rfp: Rfp, skip: set[str]) -> None:
    ex = run.excerpt("compliance", _COMPLIANCE_KEYWORDS, skip)
    if not ex.block_ids:
        return
    outs: list[ComplianceOut] = run.call("compliance", _excerpt_context(ex.text), COMPLIANCE_INSTRUCTION, ComplianceOut)
    n_runs = len(outs)
    rejected = 0
    cond_runs, elig_runs = [], []
    kinds: dict[str, str] = {}
    for out in outs:
        items = []
        for c in out.conditions:
            locs, bad = _locators(run.index, c.evidence, ex.block_ids)
            rejected += bad
            if locs:
                text = c.text.strip() + (f" — {c.consequence.strip()}" if c.consequence.strip() and c.consequence.strip() not in c.text else "")
                items.append((text, locs))
                kinds.setdefault(text, c.category)
        cond_runs.append(items)
        e_items = []
        for e in out.eligibility:
            locs, bad = _locators(run.index, e.evidence, ex.block_ids)
            rejected += bad
            if locs:
                e_items.append((e.text.strip(), locs))
        elig_runs.append(e_items)

    from .compliance import _related

    existing_blocks = {lc.block_id for c in rfp.compliance for lc in c.locators}
    existing_texts = [c.text for c in rfp.compliance if c.origin == "stated"]
    added, unstable = 0, []
    for count, (text, locs) in _match_runs(cond_runs):
        if {lc.block_id for lc in locs} & existing_blocks or any(_similar(text, t) >= 0.6 for t in existing_texts):
            continue
        kind = kinds.get(text, "감점")
        conf = 0.8 if count == n_runs else 0.5
        if count < n_runs:
            unstable.append(text[:40])
        rfp.compliance.append(ComplianceItem(kind=kind, text=text[:240], related_check=_related(text), origin="stated",  # type: ignore[arg-type]
                                             method="llm", confidence=conf, locators=locs[:2],
                                             note="LLM 보조 추출 — G1에서 확인"))
        added += 1
    elig_blocks = {lc.block_id for e in rfp.eligibility for lc in e.locators}
    e_added = 0
    for count, (text, locs) in _match_runs(elig_runs):
        if {lc.block_id for lc in locs} & elig_blocks:
            continue
        rfp.eligibility.append(Extracted[str](value=text[:200], locators=locs[:2], method="llm",
                                              confidence=0.8 if count == n_runs else 0.5))
        e_added += 1
    suggested_texts = [c.text for c in rfp.compliance if c.origin == "suggested"]
    s_added = 0
    for s in (outs[0].suggested_checks if outs else [])[:5]:
        if any(_similar(s.text, t) >= 0.5 for t in suggested_texts):
            continue
        rfp.compliance.append(ComplianceItem(kind="제출유의", text=s.text[:240], related_check=_related(s.text),
                                             origin="suggested", method="llm", confidence=0.5,
                                             note=f"원문 근거 없는 LLM 권고: {s.reason[:120]}"))
        s_added += 1
    run.report.add("LLM-COMPLIANCE-ADDED", "info",
                   f"LLM이 근거와 함께 보강: 무효·제외·감점 사유 {added}건, 참가자격 {e_added}줄, 권고 {s_added}건")
    if unstable:
        run.report.add("LLM-UNSTABLE", "warning",
                       f"{n_runs}회 실행 중 일부에서만 나온 무효·감점 사유 {len(unstable)}건 — 원문 확인 필요: {', '.join(unstable[:5])}")
    if rejected:
        run.report.add("LLM-REJECTED", "info", f"근거 검증에서 버린 무효·감점 사유·참가자격 근거 {rejected}건")


# ---- 3. ID 없는 서술형 요구사항 ------------------------------------------------------------

_CATEGORY_NAMES = {"기능": "기능 요구사항", "성능": "성능 요구사항", "보안": "보안 요구사항", "데이터": "데이터 요구사항",
                   "인터페이스": "인터페이스 요구사항", "테스트": "테스트 요구사항", "품질": "품질 요구사항",
                   "제약": "제약사항", "프로젝트 관리": "프로젝트 관리 요구사항", "프로젝트 지원": "프로젝트 지원 요구사항",
                   "기타": "기타"}


def _obligation_block(id_re: re.Pattern[str]) -> Callable[[Block], bool]:
    def pred(b: Block) -> bool:
        return (b.kind in ("para", "cell") and bool(_OBLIGATION.search(b.text))
                and not _NOT_REQUIREMENT_CONTEXT.search(b.text) and not id_re.search(b.text))
    return pred


def assist_text_requirements(run: _Runner, rfp: Rfp, skip: set[str], id_pattern: str, vocab) -> None:
    from .requirements import compile_id_regex

    ex = run.excerpt("text_requirements", _obligation_block(compile_id_regex(id_pattern)), skip)
    if not ex.block_ids:
        return
    outs: list[TextRequirementsOut] = run.call("text_requirements", _excerpt_context(ex.text),
                                               TEXT_REQUIREMENTS_INSTRUCTION, TextRequirementsOut)
    n_runs = len(outs)
    rejected = 0
    runs_items = []
    meta: dict[str, TextRequirementOut] = {}
    for out in outs:
        items = []
        for r in out.requirements:
            locs, bad = _locators(run.index, r.evidence, ex.block_ids)
            rejected += bad
            if locs:
                items.append((r.statement.strip(), locs))
                meta.setdefault(r.statement.strip(), r)
        runs_items.append(items)

    existing = [" ".join([r.name, r.definition, *r.details]) for r in rfp.requirements]
    used = {r.id for r in rfp.requirements}
    seq = 1
    new_ids: set[str] = set()
    unstable = []
    for count, (statement, locs) in _match_runs(runs_items):
        r = meta[statement]
        if any(_similar(statement, e) >= 0.5 or _similar(r.name, e) >= 0.8 for e in existing):
            continue  # 이미 ID가 있는 요구사항과 같은 내용
        while f"X-{seq:04d}" in used:
            seq += 1
        rid = f"X-{seq:04d}"
        used.add(rid)
        new_ids.add(rid)
        if count < n_runs:
            unstable.append(f"{rid} {r.name[:20]}")
        rfp.requirements.append(Requirement(
            id=rid, prefix="X", category=_CATEGORY_NAMES.get(r.category, r.category), name=r.name.strip()[:80],
            definition=statement[:400], origin="llm", confidence=0.8 if count == n_runs else 0.5, locators=locs[:2],
        ))
        existing.append(statement)
    if new_ids:
        annotate_requirements(rfp, vocab, run.report, only=new_ids)
        run.report.add("LLM-REQ-ADDED", "warning",
                       f"ID 없는 서술형 요구사항 {len(new_ids)}건을 X- 번호로 추가했습니다 — G1에서 채택·병합 여부를 확인하세요")
    if unstable:
        run.report.add("LLM-UNSTABLE", "warning",
                       f"{n_runs}회 실행 중 일부에서만 나온 서술형 요구사항 {len(unstable)}건: {', '.join(unstable[:8])}")
    if rejected:
        run.report.add("LLM-REJECTED", "info", f"근거 검증에서 버린 서술형 요구사항 근거 {rejected}건")


# ---- 실행 -------------------------------------------------------------------------------

TASKS = ("guideline", "compliance", "text_requirements")


def llm_assist(rfp: Rfp, docs: list[Document], profile: Profile, report: ExtractionReport, gateway: LLMGateway,
               skip_tables: set[str] | None = None, tasks: tuple[str, ...] = TASKS) -> None:
    """LLM 보조 추출을 돌린다. 과제 하나가 실패해도 결정적 결과와 다른 과제는 그대로 둔다."""
    run = _Runner(gateway, docs, report, profile)
    skip = skip_tables or set()
    steps = {
        "guideline": lambda: assist_guideline(run, rfp, skip),
        "compliance": lambda: assist_compliance(run, rfp, skip),
        "text_requirements": lambda: assist_text_requirements(
            run, rfp, skip, profile.value("requirements.id_regex"), profile.value("ambiguity.vague_terms")),
    }
    for name in tasks:
        try:
            steps[name]()
        except LLMRefusal as exc:
            report.add("LLM-REFUSAL", "warning", f"{exc} — 이 과제는 결정적 결과만 씁니다")
        except LLMError as exc:
            report.add("LLM-ERROR", "warning", f"{name}: {exc} — 이 과제는 결정적 결과만 씁니다")
            if "인증" in str(exc) or "모델을 정하지 못했" in str(exc):
                break  # 인증·모델 문제는 다른 과제에서도 똑같이 실패한다
    u = gateway.usage
    report.stats.update({
        "llm_calls": u.calls, "llm_input_tokens": u.input_tokens, "llm_output_tokens": u.output_tokens,
        "llm_cache_read_tokens": u.cache_read_input_tokens, "llm_cache_write_tokens": u.cache_creation_input_tokens,
    })
    report.stats["requirements"] = len(rfp.requirements)
    report.stats["questions"] = len(rfp.questions)
