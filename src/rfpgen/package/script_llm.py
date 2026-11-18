"""발표 대본·예상 질문 답변(LLM, 선택).

장표의 제목·본문과 절 초안을 보고 장마다 말할 대본과, 평가위원이 물을 만한 질문의 답변 초안을 쓴다.
절 초안에는 회사 내용이 들어 있으므로 사용자가 --llm-share-kb로 허용할 때만 보낸다(data_class=internal).
KB 값(인원·금액·경력 등)은 보내기 전에 토큰({{fact:F-001}}, {{kb:H-001.years}})으로 되돌리고, 받은 글에서
다시 값으로 바꾼다 — 값 자체는 보내지 않는다(설계서 8.3절).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import BaseModel

from ..draft.tokens import PLACEHOLDER, substitute
from ..llm import LLMCall, LLMGateway
from ..llm.prompts import SYSTEM_WRITER
from ..profile import Profile
from ..render.slides import SlideSpec
from ..schemas.draft import SectionDraft
from ..schemas.kb import CompanyKB
from ..schemas.rfp import Rfp

SPEECH_CHARS_PER_MIN = 300          # 발표 속도(공백 뺀 한국어 글자, 분당) — 대본 길이 목표에 쓴다

SCRIPT_INSTRUCTION = """\
이 작업은 기술제안서 발표 대본과 예상 질문 답변을 쓰는 것입니다. <slides>는 발표자료 장표의 번호·제목·본문이고, \
<sections>는 제안서 본문 절 초안의 요지입니다. 장표마다 발표자(사업수행책임자)가 그 장을 넘기며 말할 대본을 \
<slides>에 적힌 목표 길이에 맞춰 씁니다. 장표 글을 그대로 읽지 말고, 평가위원이 그 장에서 확인하려는 평가 질문에 \
답하는 순서로 말하듯이 씁니다. 블라인드 평가이면 회사 이름을 말하지 않고 "당사"라고 합니다.

그다음 평가위원이 물을 만한 질문을 열 개 안팎으로 고르고 답변 초안을 씁니다. 질문은 <evaluation>의 평가 질문과 \
본문에서 근거가 약한 곳(<sections>의 [확인 필요])에서 고르고, 답변은 <sections>의 내용만 근거로 씁니다. \
수치는 지어내지 않으며, 토큰({{fact:…}}, {{kb:…}})은 그대로 옮기고, 근거가 없으면 [확인 필요: 무엇]을 남깁니다. \
basis에는 답변의 근거가 된 절 번호를 적습니다.
"""


class SlideScriptOut(BaseModel):
    index: int
    script: str


class QaOut(BaseModel):
    question: str
    answer: str
    basis: str


class ScriptOut(BaseModel):
    slides: list[SlideScriptOut]
    qa: list[QaOut]


@dataclass
class ScriptResult:
    notes: dict[int, str]               # 장 번호(1부터) → 대본
    qa: list[QaOut]


def _kb_values(kb: CompanyKB) -> list[tuple[str, str]]:
    """(값, 토큰) — 긴 값부터. 숫자만 있는 값은 앞뒤가 숫자가 아닐 때만 바꾼다(mask_kb_values)."""
    pairs: list[tuple[str, str]] = []
    keys = [("fact", f.id) for f in kb.facts]
    keys += [("kb", f"{p.id}.{fld}") for p in kb.projects for fld in ("amount_krw", "start", "end")]
    keys += [("kb", f"{h.id}.years") for h in kb.people]
    for kind, key in keys:
        value = kb.resolve(key)
        if value and len(value.strip()) >= 1:
            pairs.append((value.strip(), f"{{{{{kind}:{key}}}}}"))
    return sorted(pairs, key=lambda p: -len(p[0]))


def mask_kb_values(text: str, kb: CompanyKB) -> str:
    """본문에 들어간 KB 값을 토큰으로 되돌린다(값을 LLM으로 보내지 않기 위해)."""
    for value, token in _kb_values(kb):
        text = re.sub(r"(?<![\d.,])" + re.escape(value) + r"(?![\d.,])", token, text)
    return text


def _slides_text(specs: list[SlideSpec], minutes: int | None, kb: CompanyKB) -> str:
    per = int(minutes * SPEECH_CHARS_PER_MIN / max(len(specs), 1)) if minutes else 400
    lines = ["<slides>", f"발표 시간: {minutes or '미정'}분, 장 {len(specs)}개 — 장당 대본 목표 약 {per}자"]
    for i, s in enumerate(specs, start=1):
        body = " / ".join(t for _, t in s.bullets[:8])
        lines.append(f"[{i}] {mask_kb_values(s.head or s.breadcrumb, kb)} | {mask_kb_values(body, kb)[:600]}")
    lines.append("</slides>")
    return "\n".join(lines)


def _sections_text(drafts: list[SectionDraft], kb: CompanyKB) -> str:
    lines = ["<sections>"]
    for d in drafts:
        head = mask_kb_values(d.head_message, kb)
        points = [mask_kb_values(" ".join(b.items) or b.text, kb) for b in d.blocks if b.kind in ("bullets", "para")][:6]
        gaps = sorted({mask_kb_values(p, kb) for p in PLACEHOLDER.findall(d.all_text())})[:5]
        lines.append(f"{d.number} {d.title}: {head} | 요점: {' / '.join(x[:160] for x in points)}"
                     + (f" | 근거 부족: {', '.join(gaps)}" if gaps else ""))
    lines.append("</sections>")
    return "\n".join(lines)


def _evaluation_text(rfp: Rfp, blind: bool) -> str:
    lines = ["<evaluation>", f"블라인드 평가: {'예' if blind else '아니오'}"]
    for a in rfp.evaluation.areas:
        if a.kind != "정성":
            continue
        for it in a.items:
            lines.append(f"- {a.name} > {it.name}({it.points:g}점): {' / '.join(it.criteria[:3])}"
                         if it.points is not None else f"- {a.name} > {it.name}: {' / '.join(it.criteria[:3])}")
    lines.append("</evaluation>")
    return "\n".join(lines)


def llm_script(specs: list[SlideSpec], rfp: Rfp, drafts: list[SectionDraft], kb: CompanyKB, gateway: LLMGateway,
               profile: Profile, *, minutes: int | None, blind: bool) -> ScriptResult:
    spec = profile.value("llm.tasks").get("script", {"effort": "medium", "max_tokens": 32000})
    context = _evaluation_text(rfp, blind) + "\n" + _sections_text(drafts, kb)
    instruction = _slides_text(specs, minutes, kb) + "\n\n" + SCRIPT_INSTRUCTION
    out, _ = gateway.run(LLMCall(task="draft.script", system=SYSTEM_WRITER, context=context, instruction=instruction,
                                 schema=ScriptOut, effort=spec["effort"], max_tokens=int(spec["max_tokens"]),
                                 data_class="internal"), ScriptOut)
    unresolved: list[str] = []
    notes = {s.index: substitute(s.script.strip(), kb, unresolved) for s in out.slides
             if 1 <= s.index <= len(specs) and s.script.strip()}
    qa = [QaOut(question=q.question.strip(), answer=substitute(q.answer.strip(), kb, unresolved), basis=q.basis.strip())
          for q in out.qa if q.question.strip()]
    return ScriptResult(notes=notes, qa=qa)


def script_markdown_llm(specs: list[SlideSpec], result: ScriptResult, *, minutes: int | None, title: str) -> str:
    per = f"{minutes / max(len(specs), 1):.1f}분" if minutes else "?"
    lines = [f"# 발표 대본 — {title}", "",
             f"> 장 {len(specs)}개, 발표 {minutes or '?'}분 기준 장당 약 {per}. Claude가 쓴 초안입니다 — 발표자가 "
             "자기 말투로 고치고, [확인 필요]를 채운 뒤 시간을 재 보세요.", ""]
    for i, s in enumerate(specs, start=1):
        lines += [f"## {i}. {s.head or s.breadcrumb}", "", result.notes.get(i) or s.notes or "(대본 없음)", ""]
    lines += ["# 예상 질문과 답변 초안", "", "> 답변은 본문 초안만 근거로 썼습니다. 근거(절)를 확인하고 담당자가 다듬으세요.", ""]
    for n, q in enumerate(result.qa, start=1):
        lines += [f"{n}. **{q.question}**", f"   - {q.answer}" + (f" _(근거: {q.basis})_" if q.basis else ""), ""]
    return "\n".join(lines)


__all__ = ["ScriptOut", "ScriptResult", "llm_script", "mask_kb_values", "script_markdown_llm"]
