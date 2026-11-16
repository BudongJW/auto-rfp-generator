"""사람이 G1·G2에서 검토하는 분석 요약(Markdown)과 질의서 초안."""

from __future__ import annotations

from ..schemas.docir import Document
from ..schemas.plan import Outline, PageBudget, Trace
from ..schemas.rfp import ExtractionReport, Rfp

_SEV = {"error": "🔴 오류", "warning": "🟡 경고", "info": "ℹ️ 정보"}


def _v(ex, fmt=str) -> str:
    return "—(찾지 못함)" if ex is None else fmt(ex.value)


def analysis_markdown(docs: list[Document], rfp: Rfp, outline: Outline, budget: PageBudget,
                      trace: Trace, report: ExtractionReport, profile_name: str) -> str:
    n, g, ev = rfp.notice, rfp.guideline, rfp.evaluation
    lines: list[str] = []
    add = lines.append
    add("# RFP 분석 결과")
    add("")
    add("> 이 문서는 자동 추출 결과입니다. 아래 **G1(추출 확정)·G2(설계 확정)** 항목을 원문과 대조해 확정하세요.")
    add("> 값 옆의 위치(doc:block, 쪽)는 `rfp.json`의 locator와 같습니다.")
    add("")
    add("## 입력 문서")
    add("")
    add("| ID | 파일 | 형식 | 분류 | 블록 수 | 경고 |")
    add("|---|---|---|---|---|---|")
    for d in docs:
        add(f"| {d.doc_id} | {d.filename} | {d.format} | {d.role} | {len(d.blocks)} | {'; '.join(d.warnings) or '-'} |")
    add("")
    add("## 공고 기본정보")
    add("")
    add(f"- 사업명: {_v(n.title)}")
    add(f"- 사업예산: {_v(n.budget_krw, lambda v: f'{v:,}원')}")
    add(f"- 사업기간: {_v(n.period)}")
    add(f"- 계약방법: {n.contract_method.value} (적용 프로필: `{profile_name}`)")
    ratio = ev.tech_price_ratio.value if ev.tech_price_ratio else None
    add(f"- 기술:가격 = {ratio[0]}:{ratio[1]}" if ratio else "- 기술:가격 = —(찾지 못함, 프로필 기본값 사용)")
    add("")
    add("## 작성지침")
    add("")
    add(f"- 본문 분량: {_v(g.main_page_limit, lambda v: f'{v}쪽')} / 요약본: {_v(g.summary_page_limit, lambda v: f'{v}쪽')}"
        f" / 발표자료: {_v(g.presentation_page_limit, lambda v: f'{v}쪽')}")
    add(f"- 쪽수 제외: {_v(g.count_exclusions, lambda v: ', '.join(v))}")
    add(f"- 용지·방향: {_v(g.paper)} / {_v(g.orientation)}")
    add(f"- 최소 글자 크기: 본문 {_v(g.min_font_pt, lambda v: f'{v:g}pt')} / 표 {_v(g.table_min_font_pt, lambda v: f'{v:g}pt')}")
    add(f"- 제출 형식·용량: {_v(g.file_format)} / {_v(g.total_size_limit_mb, lambda v: f'{v}MB')}")
    blind = g.blind
    add(f"- 블라인드: {'예' if blind and blind.value else '아니오' if blind and blind.confidence >= 1 else '문구 없음(확인 필요)'}")
    if g.presentation:
        p = g.presentation.value
        add(f"- 발표: {p.minutes or '?'}분, 질의응답 {p.qa_minutes or '?'}분, PM 직접 발표 {'예' if p.pm_must_present else '미기재'}")
    if g.prescribed_toc:
        prod = ", ".join(f"{c.number}.{c.title}({c.production})" for c in g.prescribed_toc.value)
        add(f"- 지정 목차: {prod}")
    if g.required_documents:
        add(f"- 별지 서식 {len(g.required_documents)}종: " + ", ".join(f"{d.form_no}({d.name[:20]})" for d in g.required_documents[:12]))
    add("")
    add("## 평가표")
    add("")
    if ev.areas:
        add("| 부문 | 구분 | 배점 | 항목(배점) |")
        add("|---|---|---|---|")
        for a in ev.areas:
            items = ", ".join(f"{it.name}({it.points:g})" if it.points is not None else it.name for it in a.items)
            add(f"| {a.name} | {a.kind} | {a.points:g} | {items} |" if a.points is not None else f"| {a.name} | {a.kind} | ? | {items} |")
        add("")
    else:
        add("평가표를 찾지 못했습니다.")
        add("")
    if ev.rules:
        kinds: dict[str, int] = {}
        for r in ev.rules:
            kinds[r.kind] = kinds.get(r.kind, 0) + 1
        add(f"평가규칙(점수 매기는 방법, 본문이 답할 대상 아님) {len(ev.rules)}건: "
            + ", ".join(f"{k} {v}" for k, v in kinds.items()) + " — `analysis.xlsx`의 평가규칙 시트")
        add("")
    add("## 입찰무효·평가제외·감점 사유")
    add("")
    stated = [c for c in rfp.compliance if c.origin == "stated"]
    suggested = [c for c in rfp.compliance if c.origin == "suggested"]
    for c in stated[:30]:
        where = f" ({c.locators[0].doc_id} p.{c.locators[0].page})" if c.locators and c.locators[0].page else ""
        add(f"- **{c.kind}**{f' [{c.related_check}]' if c.related_check else ''} {c.text[:160]}{where}")
    if len(stated) > 30:
        add(f"- … 외 {len(stated) - 30}건(`analysis.xlsx`)")
    if suggested:
        add("")
        add("원문에는 없지만 확인을 권하는 사유(G1에서 채택 여부 결정):")
        add("")
        for c in suggested:
            add(f"- {c.kind}: {c.text}")
    if rfp.eligibility:
        add("")
        add(f"입찰참가자격 {len(rfp.eligibility)}줄 — `analysis.xlsx`의 무효·감점 사유 시트")
    add("")
    add("## 요구사항")
    add("")
    by_prefix: dict[str, int] = {}
    for r in rfp.requirements:
        by_prefix[r.prefix or "?"] = by_prefix.get(r.prefix or "?", 0) + 1
    add(f"- 총 {len(rfp.requirements)}건: " + ", ".join(f"{k} {v}" for k, v in sorted(by_prefix.items())))
    declared = report.stats.get("declared_requirements")
    if declared:
        add(f"- RFP 선언 요구사항 수: {declared}건")
    grades = {k[-1]: v for k, v in report.stats.items() if k.startswith("grade_")}
    if grades:
        add("- 상세화 등급(휴리스틱 추정): " + ", ".join(f"{k} {grades[k]}" for k in "SABCD" if k in grades))
    add("")
    add(f"## 목차와 쪽수 예산 (출처: {outline.origin})")
    add("")
    add(f"본문 상한 {budget.main_page_limit}쪽({budget.main_page_limit_source}) = 고정 {budget.fixed_pages}쪽 + 배점 배분 {budget.distributable_pages}쪽 (정성 {budget.qualitative_points:g}점)")
    add("")
    add(f"쪽당 글자 수: 이론 상한 {budget.chars_per_page:,}자, 실효 {budget.effective_chars_per_page:,}자(개조식·표 비중 반영 제안값). "
        "절별 목표 글자 수는 `analysis.xlsx` 목차·쪽수 시트")
    add("")
    add("| 번호 | 제목 | 배점 | 쪽수 | 요구사항 |")
    add("|---|---|---|---|---|")
    for node in outline.walk():
        indent = "　" * (node.level - 1)
        add(f"| {node.number} | {indent}{node.title} | {node.points:g} | {node.page_budget} | {len(node.requirements)} |")
    add("")
    add(f"추적표 커버리지: {trace.coverage():.0%} ({sum(1 for r in trace.rows if r.status != 'unmapped')}/{len(trace.rows)})")
    add("")
    add("## 점검 결과")
    add("")
    if report.findings:
        for f in sorted(report.findings, key=lambda f: ["error", "warning", "info"].index(f.severity)):
            where = f" ({f.locators[0].doc_id} p.{f.locators[0].page})" if f.locators and f.locators[0].page else ""
            add(f"- {_SEV[f.severity]} `{f.code}` {f.message}{where}")
    else:
        add("- 점검 항목 없음")
    add("")
    add(f"## 질의서 후보 {len(rfp.questions)}건")
    add("")
    add("`questions.md` 참고.")
    add("")
    return "\n".join(lines)


def questions_markdown(rfp: Rfp) -> str:
    title = rfp.notice.title.value if rfp.notice.title else "(사업명 미확인)"
    lines = [f"# 질의서 초안 — {title}", "",
             "> 자동 생성 초안입니다. 질의 기간과 제출 양식은 공고를 따르세요. 중복·불필요한 질의는 삭제하세요.", ""]
    for i, q in enumerate(rfp.questions, start=1):
        where = ""
        if q.locators:
            lc = q.locators[0]
            where = f" _(원문: {lc.doc_id}{f' p.{lc.page}' if lc.page else ''})_"
        lines.append(f"{i}. **{q.target}** — {q.issue}")
        lines.append(f"   - {q.question}{where}")
    lines.append("")
    return "\n".join(lines)
